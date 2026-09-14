"""m0_charsafe - character-level safety layer (REFERENCE MODULE).

Catches:
  * invisible characters (Unicode Cf / Cc) and invisible filler letters
    (Hangul fillers U+3164/U+115F/U+1160/U+FFA0, braille blank U+2800) -> ZERO_WIDTH
  * combining-mark stuffing (U+0336 after every letter of "aptal") on Latin letters -> ZERO_WIDTH; decomposed
    letters ("s" + U+0327) are canonically composed ("ş") and recorded
  * fullwidth Latin letters and digits ("ａｐｔａｌ") -> HOMOGLYPH
  * cross-script homoglyphs (Cyrillic/Greek lookalikes inside Latin words) -> HOMOGLYPH
  * the Turkish I problem: 'I' lowercases to 'ı', 'İ' to 'i' -> DOTLESS_I evidence

Deliberately does NOT:
  * de-obfuscate leet, spacing, repeats, deasciified text (m2_deobf, parallel channel)
  * guess that an ASCII 'I' was meant as 'İ' ("Istanbul" -> "ıstanbul"). That is
    DEASCII, an interpretation, and interpretations belong to m2's parallel channel.
  * apply NFKC. NFKC folds fullwidth forms but also rewrites ligatures,
    superscripts and compatibility digits; that is normalization, not safety.
    Fullwidth Latin is mapped by an explicit table instead.
  * strip combining marks from non-Latin letters (Arabic, Hebrew, Devanagari...
    need them), or fullwidth punctuation (ordinary in CJK text).
  * score content, detect targets, or decide anything.

Output: `charsafe_text`, `form` (one FormPattern per transformation run, spans in
ORIGINAL offsets) and signals: `offsets` (the original index of every charsafe
character, so downstream spans can be reported on the input), `charsafe_changed`
(True when any FormPattern was emitted), `invisible_removed`, `homoglyphs_mapped`.

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
# from replies - QUOTE_COUNTERSPEECH depends on it). Deleting them would also
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

TURKISH_LETTERS = frozenset("çğıöşüÇĞİÖŞÜâîûÂÎÛ")

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
CONF_FULLWIDTH = 0.80  # no Turkish text needs fullwidth Latin

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
    version = "0.1.0"
    provides = frozenset({"charsafe_text", "form"})

    def _run(self, ctx: Context) -> ModuleOutput:
        text = ctx.text  # read only; we build a new string, never edit this one
        patterns: list[FormPattern] = []

        items = self._strip_invisible(text, patterns)
        items = self._handle_combining_marks(items, patterns)
        homoglyphs = self._map_fullwidth(items, patterns)
        homoglyphs += self._map_confusables(text, items, patterns)
        items = self._turkish_lower(text, items, patterns)

        charsafe = "".join(ch for _, _, ch in items)
        return ModuleOutput(
            charsafe_text=charsafe,
            form=FormResult(patterns=patterns),
            signals={
                "offsets": [start for start, _, _ in items],
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
    def _map_fullwidth(self, items: list[Item], patterns: list[FormPattern]) -> int:
        mapped = 0
        for token in _tokens(items):
            wide = [k for k in token if any(lo <= ord(items[k][2]) <= hi for lo, hi in FULLWIDTH_RANGES)]
            if not wide:
                continue
            before = "".join(items[k][2] for k in token)
            for k in wide:
                start, end, ch = items[k]
                items[k] = (start, end, chr(ord(ch) - FULLWIDTH_OFFSET))
            after = "".join(items[k][2] for k in token)
            patterns.append(FormPattern(
                code=FormCode.HOMOGLYPH,
                confidence=CONF_FULLWIDTH,
                evidence=f"'{before}' -> '{after}' ({len(wide)} fullwidth Latin letter/digit(s))",
                span=(items[token[0]][0], items[token[-1]][1]),
                source=SOURCE,
            ))
            mapped += len(wide)
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
