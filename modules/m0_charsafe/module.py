"""m0_charsafe - character-level safety layer (REFERENCE MODULE).

Catches:
  * invisible characters (Unicode Cf / Cc) and invisible filler letters
    (Hangul fillers U+3164/U+115F/U+1160/U+FFA0, braille blank U+2800) -> ZERO_WIDTH
  * combining-mark stuffing (U+0336 after every letter of "aptal") on Latin letters -> ZERO_WIDTH; decomposed
    letters ("s" + U+0327) are canonically composed ("ş") and recorded
  * styled Latin letters -> HOMOGLYPH: fullwidth ("ａｐｔａｌ"), mathematical
    alphanumerics (bold/italic/script... U+1D400-U+1D7FF), circled (U+24B6-U+24E9),
    squared / negative circled / negative squared capitals (U+1F130-U+1F189),
    parenthesized letters, superscript and subscript letters, small capitals
    (U+1D00 block and friends), and regional indicator letters that do not form flags
  * cross-script homoglyphs (Cyrillic/Greek lookalikes inside Latin words) -> HOMOGLYPH
  * the Turkish I problem: 'I' lowercases to 'ı', 'İ' to 'i' -> DOTLESS_I evidence

Deliberately does NOT:
  * de-obfuscate leet, spacing, repeats, deasciified text (m2_deobf, parallel channel)
  * guess that an ASCII 'I' was meant as 'İ' ("Istanbul" -> "ıstanbul"). That is
    DEASCII, an interpretation, and interpretations belong to m2's parallel channel.
  * apply NFKC. NFKC folds fullwidth forms but also rewrites ligatures,
    superscripts and compatibility digits; that is normalization, not safety.
    Styled Latin is mapped by an explicit per-character table instead, and
    superscript/subscript DIGITS ("m²") are never mapped.
  * touch flags: a regional-indicator run made only of valid region pairs is left
    as flags - so a word spelled only from valid flag pairs passes (known gap).
  * strip combining marks from non-Latin letters (Arabic, Hebrew, Devanagari...
    need them), or fullwidth punctuation (ordinary in CJK text).
  * normalise accents ("áptal" -> "aptal"): accent normalisation belongs to m2
    (spec.md §2); m0 only composes canonically equivalent sequences.
  * score content, detect targets, or decide anything.

Output: `charsafe_text`, `form` (one FormPattern per transformation run, spans in
ORIGINAL offsets) and signals: `charsafe_changed` (True when any FormPattern was
emitted), `invisible_removed`, `homoglyphs_mapped`, `offsets_identity` (True when
every charsafe character sits at its original index) and the internal `_offsets`
(original index of every charsafe character). `_offsets` grows with the post, so
it is internal: downstream modules read it through ctx.signals, the pipeline
keeps it out of the response.

Plain case folding of letters other than I/İ emits no pattern: capitalization
is not obfuscation and there is no FormCode for it. Only folds where Turkish
and default Unicode rules diverge are recorded.
"""
from __future__ import annotations

import unicodedata

from contracts.codes import FormCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import FormPattern, FormResult

SOURCE = ModuleName.M0_CHARSAFE.value

# Layout controls are Cc but carry structure (line breaks separate quoted text
# from replies, which downstream readers of the raw text rely on). Deleting them would also
# glue words together and CREATE collisions ("kerpic\nsikke" -> "kerpicsikke").
LAYOUT_CONTROLS = frozenset("\t\n\r")

ZWJ = "\u200d"
COMBINING_DOT_ABOVE = "\u0307"
VARIATION_SELECTOR_15 = "\ufe0e"
VARIATION_SELECTOR_16 = "\ufe0f"
BOM = "\ufeff"

# Letters (category Lo/So) that render as nothing. They are not Cf, so a
# category test misses them, and they are a known way to split a word invisibly.
INVISIBLE_FILLERS = frozenset("\u115f\u1160\u3164\uffa0\u2800")

# Fullwidth forms of ASCII letters and digits. Mapped explicitly (not NFKC):
# one meaning each, no language uses them as distinct letters. Fullwidth
# punctuation is left alone because it is ordinary in CJK text.
FULLWIDTH_OFFSET = 0xFEE0
FULLWIDTH_RANGES = ((0xFF10, 0xFF19), (0xFF21, 0xFF3A), (0xFF41, 0xFF5A))

# Styled Latin with a single-letter compatibility decomposition. Folded one
# character at a time with NFKC, and only when the result is one Latin/Turkish
# letter or digit - never NFKC over the whole text (see "does NOT" above).
STYLED_NFKC_RANGES = ((0x1D400, 0x1D7FF, "mathematical"), (0x24B6, 0x24E9, "circled"),
                      (0x1F130, 0x1F149, "squared"))

# Superscript and subscript Latin LETTERS. Folded with NFKC one character at a
# time, letters only: superscript DIGITS stay ("m²", "10³" are ordinary
# text, and folding them is normalization, not safety). The ranges also hold IPA
# modifier letters; those fold to non-ASCII and are left alone.
SUPERSCRIPT_NFKC_RANGES = ((0x02B0, 0x02FF), (0x1D2C, 0x1D6A), (0x1D9B, 0x1DBF), (0x2070, 0x209C),
                           (0x2C7C, 0x2C7D))

# Enclosed Latin letters NFKC does not fold to one letter (negative circled and
# negative squared have no decomposition; parenthesized fold to "(a)"). Mapped by
# offset: (first code point, last code point, letter at first, style).
ENCLOSED_OFFSET_RANGES = (
    (0x249C, 0x24B5, "a", "parenthesized"),
    (0x1F110, 0x1F129, "A", "parenthesized"),
    (0x1F150, 0x1F169, "A", "negative circled"),
    (0x1F170, 0x1F189, "A", "negative squared"),
)

# Regional indicators render as boxed letters, but a pair of them is also a flag
# (TR = the Turkish flag), which is ordinary in Turkish posts and must stay
# untouched. A run is read in pairs from its start, as renderers do; it is mapped
# to letters unless it is an even-length run of valid region codes (ISO 3166-1
# alpha-2 plus the Unicode/CLDR extras). Known gap, accepted: a word spelled only
# from valid flag pairs passes, because it is indistinguishable from a row of flags.
REGIONAL_INDICATOR_A = 0x1F1E6
REGIONAL_INDICATOR_Z = 0x1F1FF
FLAG_REGIONS = frozenset("""
AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV
BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES
ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE
IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY
MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU
NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM
SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE
VG VI VN VU WF WS YE YT ZA ZM ZW
AC CP DG EA EU IC TA UN XK
""".split())

# Small capitals have no decomposition, so they need a table. Small capital I
# maps to capital I, which the Turkish casing pass then folds to dotless i.
SMALL_CAPITALS: dict[str, str] = {"\u1d00": "a", "\u0299": "b", "\u1d04": "c", "\u1d05": "d", "\u1d07": "e", "\ua730": "f", "\u0262": "g", "\u029c": "h", "\u026a": "I", "\u1d0a": "j", "\u1d0b": "k", "\u029f": "l", "\u1d0d": "m", "\u0274": "n", "\u1d0f": "o", "\u1d18": "p", "\u0280": "r", "\ua731": "s", "\u1d1b": "t", "\u1d1c": "u", "\u1d20": "v", "\u1d21": "w", "\u028f": "y", "\u1d22": "z"}

TURKISH_LETTERS = frozenset("çğıöşüÇĞİÖŞÜâîûÂÎÛ")


def _build_styled_latin() -> dict[str, tuple[str, str]]:
    """styled character -> (plain character, style), built once at import so the
    per-character check is one dict lookup (the per-character range scan made
    long posts slow)."""
    table: dict[str, tuple[str, str]] = {}
    for lo, hi in FULLWIDTH_RANGES:
        for cp in range(lo, hi + 1):
            table[chr(cp)] = (chr(cp - FULLWIDTH_OFFSET), "fullwidth")
    for lo, hi, style in STYLED_NFKC_RANGES:
        for cp in range(lo, hi + 1):
            folded = unicodedata.normalize("NFKC", chr(cp))
            # Mathematical Greek folds to Greek, not Latin: leave it alone.
            if len(folded) == 1 and ((folded.isascii() and folded.isalnum()) or folded in TURKISH_LETTERS):
                table[chr(cp)] = (folded, style)
    for lo, hi in SUPERSCRIPT_NFKC_RANGES:
        for cp in range(lo, hi + 1):
            folded = unicodedata.normalize("NFKC", chr(cp))
            if len(folded) == 1 and folded.isascii() and folded.isalpha():
                style = "subscript" if "SUBSCRIPT" in unicodedata.name(chr(cp), "") else "superscript"
                table[chr(cp)] = (folded, style)
    for lo, hi, first, style in ENCLOSED_OFFSET_RANGES:
        for cp in range(lo, hi + 1):
            table[chr(cp)] = (chr(ord(first) + cp - lo), style)
    for ch, plain in SMALL_CAPITALS.items():
        table[ch] = (plain, "small capital")
    return table


STYLED_LATIN = _build_styled_latin()
REGIONAL_INDICATORS = frozenset(chr(cp) for cp in range(REGIONAL_INDICATOR_A, REGIONAL_INDICATOR_Z + 1))
# Everything the styled-Latin pass may rewrite: one set lookup per character.
STYLED_CANDIDATES = frozenset(STYLED_LATIN) | REGIONAL_INDICATORS

# Deliberately SMALL. A large confusables table (e.g. the full Unicode
# confusables.txt) maps legitimate letters of other languages and, worse, some
# Turkish ones; every entry here is a visual twin of an ASCII letter. Turkish
# letters are never keys - 'ı' is a letter, not a homoglyph of 'i'.
CONFUSABLES: dict[str, str] = {
    # Cyrillic lowercase
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c",
    "\u0443": "y", "\u0445": "x", "\u0456": "i", "\u0458": "j", "\u0455": "s",
    "\u0501": "d", "\u04cf": "l", "\u04bb": "h", "\u051b": "q", "\u051d": "w",
    # Cyrillic uppercase
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K", "\u041c": "M",
    "\u041d": "H", "\u041e": "O", "\u0420": "P", "\u0421": "C", "\u0422": "T",
    "\u0425": "X", "\u0406": "I", "\u0408": "J", "\u0405": "S", "\u0423": "Y",
    # Greek lowercase
    "\u03bf": "o", "\u03b1": "a", "\u03bd": "v", "\u03c1": "p", "\u03b9": "i",
    # Greek uppercase
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u0396": "Z", "\u0397": "H",
    "\u0399": "I", "\u039a": "K", "\u039c": "M", "\u039d": "N", "\u039f": "O",
    "\u03a1": "P", "\u03a4": "T", "\u03a5": "Y", "\u03a7": "X",
    # Latin lookalikes outside the Turkish alphabet
    "\u0251": "a", "\u0261": "g",
}

# Confidence values are evidence strength, not thresholds. Whether a pattern
# counts is decided by form.min_confidence in decision/thresholds.yaml.
CONF_INVISIBLE_INSIDE_WORD = 0.95  # splitting a word is the whole point of the attack
CONF_INVISIBLE_BOUNDARY = 0.40  # bidi marks / copy-paste debris also land here
CONF_INVISIBLE_LEADING_BOM = 0.05  # encoding artifact, recorded for traceability
CONF_HOMOGLYPH_MIXED_SCRIPT = 0.90  # Latin and lookalike in one token: no honest reason
CONF_HOMOGLYPH_ALL_LOOKALIKE = 0.60  # could be a genuine short foreign word
CONF_CASING_INNER = 0.90  # "sIk": capital I inside a lowercase word
CONF_CASING_ORDINARY = 0.10  # "SIKINTI", "Istanbul": normal capitalization
CONF_COMBINING_STUFFING = 0.90  # marks on Latin letters that compose to nothing
CONF_CANONICAL_COMPOSITION = 0.05  # decomposed input (e.g. macOS), not an attack
CONF_STYLED_LATIN = 0.80  # no Turkish text needs fullwidth, mathematical, enclosed, superscript or small-capital Latin

# Marks that belong to emoji sequences (text/emoji presentation, keycap).
EMOJI_MARKS = frozenset((chr(0xFE0E), chr(0xFE0F), chr(0x20E3)))

Item = tuple[int, int, str]  # (orig_start, orig_end, char)


def _is_latin(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ch in TURKISH_LETTERS


def _is_emoji_part(ch: str) -> bool:
    return bool(ch) and (unicodedata.category(ch) in ("So", "Sk") or ch == VARIATION_SELECTOR_16)


def _is_invisible(ch: str) -> bool:
    if ch in INVISIBLE_FILLERS:
        return True
    return unicodedata.category(ch) in ("Cf", "Cc") and ch not in LAYOUT_CONTROLS


def _char_name(ch: str) -> str:
    return f"U+{ord(ch):04X} {unicodedata.name(ch, '<control>')}"


def _snippet(text: str, start: int, end: int, width: int = 8) -> str:
    return f"{text[max(0, start - width):start]}|{text[end:end + width]}"


def _tokens(items: list[Item]) -> list[list[int]]:
    """Whitespace-separated tokens as lists of indices into `items`."""
    tokens: list[list[int]] = []
    current: list[int] = []
    for idx, (_, _, ch) in enumerate(items):
        if ch.isspace():
            if current:
                tokens.append(current)
                current = []
        else:
            current.append(idx)
    if current:
        tokens.append(current)
    return tokens


class CharSafeModule(BaseModule):
    name = ModuleName.M0_CHARSAFE
    version = "0.2.0"
    provides = frozenset({"charsafe_text", "form"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # emits no content scores or guards (its form patterns always carry spans).
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        text = ctx.text  # read only; we build a new string, never edit this one
        patterns: list[FormPattern] = []

        items = self._strip_invisible(text, patterns)
        items = self._handle_combining_marks(items, patterns)
        homoglyphs = self._map_styled_latin(items, patterns)
        homoglyphs += self._map_confusables(text, items, patterns)
        items = self._turkish_lower(text, items, patterns)

        charsafe = "".join(ch for _, _, ch in items)
        offsets = [start for start, _, _ in items]
        return ModuleOutput(
            charsafe_text=charsafe,
            form=FormResult(patterns=patterns),
            signals={
                "_offsets": offsets,
                "offsets_identity": all(index == start for index, start in enumerate(offsets)),
                "invisible_removed": sum(p.span[1] - p.span[0] for p in patterns
                                         if p.code is FormCode.ZERO_WIDTH and p.span),
                "homoglyphs_mapped": homoglyphs,
                "charsafe_changed": bool(patterns),
            },
        )

    # -- pass 1 -------------------------------------------------------------
    def _strip_invisible(self, text: str, patterns: list[FormPattern]) -> list[Item]:
        items: list[Item] = []
        i, n = 0, len(text)
        while i < n:
            if not _is_invisible(text[i]):
                items.append((i, i + 1, text[i]))
                i += 1
                continue
            j = i
            while j < n and _is_invisible(text[j]):
                j += 1
            run = text[i:j]
            prev = text[i - 1] if i > 0 else ""
            nxt = text[j] if j < n else ""

            # A ZWJ between emoji parts builds one glyph (family, flame heart).
            # Stripping it is harmless but reporting it would put ZERO_WIDTH on
            # every post with a compound emoji, so it is kept and not reported.
            if run == ZWJ and _is_emoji_part(prev) and _is_emoji_part(nxt):
                items.append((i, j, run))
                i = j
                continue

            if run == BOM and i == 0:
                confidence, where = CONF_INVISIBLE_LEADING_BOM, "leading BOM (encoding artifact)"
            elif prev.isalpha() and nxt.isalpha():
                confidence, where = CONF_INVISIBLE_INSIDE_WORD, "inside word"
            else:
                confidence, where = CONF_INVISIBLE_BOUNDARY, "at word boundary"
            names = ", ".join(dict.fromkeys(_char_name(c) for c in run))
            patterns.append(FormPattern(
                code=FormCode.ZERO_WIDTH,
                confidence=confidence,
                evidence=f"removed {len(run)}x [{names}] {where}: '{_snippet(text, i, j)}'",
                span=(i, j),
                source=SOURCE,
            ))
            i = j
        return items

    # -- pass 1b ------------------------------------------------------------
    def _handle_combining_marks(self, items: list[Item], patterns: list[FormPattern]) -> list[Item]:
        """Compose decomposed letters; strip marks stuffed onto Latin letters.

        Marks are only stripped when the letter they sit on is Latin (or a
        lookalike, or not a letter at all). Arabic, Hebrew, Devanagari and many
        other scripts need their combining marks, so those are left alone.
        """
        out: list[Item] = []
        composed: list[tuple[Item, str]] = []
        stripped: list[Item] = []
        last_base = ""
        for item in items:
            start, end, ch = item
            if unicodedata.category(ch) not in ("Mn", "Me"):
                out.append(item)
                last_base = ch
                continue
            prev = out[-1][2] if out else ""
            if ch == COMBINING_DOT_ABOVE and prev in ("I", "i"):
                # Decomposed İ: the casing pass turns it into 'i'.
                out.append(item)
                continue
            if ch in EMOJI_MARKS and last_base and not last_base.isalpha():
                out.append(item)
                continue
            if prev and prev.isalpha():
                nfc = unicodedata.normalize("NFC", prev + ch)
                if len(nfc) == 1:
                    # Canonical composition is lossless ("s" + U+0327 -> "ş").
                    out[-1] = (out[-1][0], end, nfc)
                    composed.append((item, nfc))
                    continue
            if last_base.isalpha() and not _is_latin(last_base) and last_base not in CONFUSABLES:
                out.append(item)
                continue
            stripped.append(item)

        if composed:
            patterns.append(FormPattern(
                code=FormCode.ZERO_WIDTH,
                confidence=CONF_CANONICAL_COMPOSITION,
                evidence=f"composed {len(composed)} decomposed letter(s) -> "
                         f"{''.join(c for _, c in composed)} (canonical composition, lossless)",
                span=(min(i[0] for i, _ in composed), max(i[1] for i, _ in composed)),
                source=SOURCE,
            ))
        if stripped:
            names = ", ".join(dict.fromkeys(_char_name(ch) for _, _, ch in stripped))
            patterns.append(FormPattern(
                code=FormCode.ZERO_WIDTH,
                confidence=CONF_COMBINING_STUFFING,
                evidence=f"removed {len(stripped)} combining mark(s) [{names}] stuffed onto Latin letters",
                span=(min(i[0] for i in stripped), max(i[1] for i in stripped)),
                source=SOURCE,
            ))
        return out

    # -- pass 1c ------------------------------------------------------------
    @staticmethod
    def _regional_indicator_hits(items: list[Item], token: range) -> dict[int, tuple[str, str]]:
        """Regional indicators in `token` that spell letters rather than flags."""
        hits: dict[int, tuple[str, str]] = {}
        run: list[int] = []
        for k in [*token, None]:
            if k is not None and items[k][2] in REGIONAL_INDICATORS:
                run.append(k)
                continue
            if run:
                letters = "".join(chr(ord("A") + ord(items[r][2]) - REGIONAL_INDICATOR_A) for r in run)
                pairs = [letters[i:i + 2] for i in range(0, len(letters), 2)]
                if not all(pair in FLAG_REGIONS for pair in pairs):  # an odd tail is never a region
                    hits.update((r, (letter, "regional indicator")) for r, letter in zip(run, letters))
                run = []
        return hits

    def _map_styled_latin(self, items: list[Item], patterns: list[FormPattern]) -> int:
        # Cheap exit: ordinary text has no candidate and is never tokenized by this pass.
        candidates = [k for k, item in enumerate(items) if item[2] in STYLED_CANDIDATES]
        mapped = 0
        covered_until: int | None = None  # last index of the token already handled
        for c in candidates:
            if covered_until is not None and c <= covered_until:
                continue
            # The whitespace-separated token around the candidate, as _tokens() would cut it.
            lo = c
            while lo > 0 and not items[lo - 1][2].isspace():
                lo -= 1
            hi = c
            while hi + 1 < len(items) and not items[hi + 1][2].isspace():
                hi += 1
            covered_until = hi
            token = range(lo, hi + 1)
            styled = {k: STYLED_LATIN[items[k][2]] for k in token if items[k][2] in STYLED_LATIN}
            if any(items[k][2] in REGIONAL_INDICATORS for k in token):
                styled.update(self._regional_indicator_hits(items, token))
            if not styled:
                continue  # the token holds only flags
            before = "".join(items[k][2] for k in token)
            for k, (plain, _) in styled.items():
                start, end, _ = items[k]
                items[k] = (start, end, plain)
            after = "".join(items[k][2] for k in token)
            styles = ", ".join(dict.fromkeys(styled[k][1] for k in sorted(styled)))
            patterns.append(FormPattern(
                code=FormCode.HOMOGLYPH,
                confidence=CONF_STYLED_LATIN,
                evidence=f"'{before}' -> '{after}' ({len(styled)} styled Latin character(s): {styles})",
                span=(items[token[0]][0], items[token[-1]][1]),
                source=SOURCE,
            ))
            mapped += len(styled)
        return mapped

    # -- pass 2 -------------------------------------------------------------
    def _map_confusables(self, text: str, items: list[Item], patterns: list[FormPattern]) -> int:
        # Guard 1: only run when a non-ASCII, non-Turkish letter exists at all.
        # Pure ASCII/Turkish text cannot contain a confusable by construction,
        # so this is a speed win AND a guarantee that m0 never rewrites the
        # letters of ordinary Turkish text.
        if not any(ch.isalpha() and not ch.isascii() and ch not in TURKISH_LETTERS
                   for _, _, ch in items):
            return 0

        mapped = 0
        for token in _tokens(items):
            letters = [items[k][2] for k in token if items[k][2].isalpha()]
            if not any(ch in CONFUSABLES for ch in letters):
                continue
            has_latin = any(_is_latin(ch) for ch in letters)
            foreign = [ch for ch in letters if not _is_latin(ch)]
            # Guard 2: a token written entirely in another script is a foreign
            # word ("мир"), not an attack. Map only when the token mixes in
            # Latin letters, or when EVERY foreign letter is a lookalike (a
            # Latin word spelled with twins). Genuine Russian words almost
            # always contain a letter with no Latin twin.
            if not has_latin and not all(ch in CONFUSABLES for ch in foreign):
                continue
            before = "".join(items[k][2] for k in token)
            for k in token:
                start, end, ch = items[k]
                if ch in CONFUSABLES:
                    items[k] = (start, end, CONFUSABLES[ch])
                    mapped += 1
            after = "".join(items[k][2] for k in token)
            first, last = items[token[0]][0], items[token[-1]][1]
            patterns.append(FormPattern(
                code=FormCode.HOMOGLYPH,
                confidence=CONF_HOMOGLYPH_MIXED_SCRIPT if has_latin else CONF_HOMOGLYPH_ALL_LOOKALIKE,
                evidence=f"'{before}' -> '{after}' "
                         f"({'mixed script' if has_latin else 'all letters are lookalikes'}; "
                         f"{', '.join(dict.fromkeys(_char_name(c) for c in before if c in CONFUSABLES))})",
                span=(first, last),
                source=SOURCE,
            ))
        return mapped

    # -- pass 3 -------------------------------------------------------------
    def _turkish_lower(self, text: str, items: list[Item], patterns: list[FormPattern]) -> list[Item]:
        # str.lower() is wrong for Turkish in both directions: 'I' -> 'i' turns
        # "SIKINTI" into "sikinti" (a profanity-prefix collision) and 'İ' ->
        # 'i' + U+0307 leaves a stray combining dot that breaks every lexicon
        # lookup. So I and İ are handled explicitly before generic lowering.
        out: list[Item] = []
        before: list[str] = []  # character each output item was folded from
        k, n = 0, len(items)
        while k < n:
            start, end, ch = items[k]
            nxt = items[k + 1][2] if k + 1 < n else ""
            if ch in ("I", "i") and nxt == COMBINING_DOT_ABOVE:
                # Decomposed İ, or the residue of a non-Turkish lower("İ").
                out.append((start, items[k + 1][1], "i"))
                before.append(ch + nxt)
                k += 2
                continue
            if ch == "I":
                low = "ı"
            elif ch == "İ":
                low = "i"
            else:
                low = ch.lower()
                if len(low) != 1:  # never let casing change the offset map
                    low = ch
            out.append((start, end, low))
            before.append(ch)
            k += 1

        # Evidence pass: one pattern per token where Turkish rules diverged.
        for token in _tokens(out):
            first, last = out[token[0]][0], out[token[-1]][1]
            original = text[first:last]
            folded_from = "".join(before[k] for k in token)
            if not any(c in "Iİ" or c == COMBINING_DOT_ABOVE for c in folded_from):
                continue
            letters = [c for c in folded_from if c.isalpha()]
            inner = any(c in "Iİ" for c in letters[1:]) and any(c.islower() for c in letters)
            patterns.append(FormPattern(
                code=FormCode.DOTLESS_I,
                confidence=CONF_CASING_INNER if inner else CONF_CASING_ORDINARY,
                evidence=f"'{original}' -> '{''.join(out[k][2] for k in token)}' (Turkish casing I->ı, İ->i; "
                         f"{'capital I inside a lowercase word' if inner else 'ordinary capitalization'})",
                span=(first, last),
                source=SOURCE,
            ))
        return out
