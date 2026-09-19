"""m1_lexicon - lexicon signal, independent of the neural model.

Catches:
  * every root of terlik's Turkish dictionary with legal Turkish suffixes ("aptallar",
    "siktiler"), via `terlik` 0.1.0 in balanced mode (spec.md §4.3): its suffix engine accepts a
    root only when what follows is a suffix it knows, and it tolerates leet,
    separators and repetition ("g0t", "s i k")
  * ROUTES each matched root to the content code whose contract meaning fits
    (protocols/m1_runtime_routing_protocol.md, M1-ROUTE-1): the 17 explicit obscene / profane
    roots of pseudo-label rule v3 on the family-A carrier (A1); ordinary insults on B1
    (degradation); threats on B2; curses / exclusion on B3; topic or neutral vocabulary on no
    content code at all - still a match, a hit and a matched root
  * the same on the normalized channel from m2, reported separately (spec.md §3)
  * substring collisions: a root found inside a word the boundary test rejected
    ("sik" in "psikoloji", "am" in "amca") -> SUBSTRING_COLLISION on that word
  * NON_HUMAN_TARGET on each of its own content scores when m6 publishes target_type
    non_human (ADR-005); thresholds.yaml decides which codes it may suppress
  * every match in the private `_matches` signal (root, channel, span, route), including the
    matches that emit no content code, for the pseudo-label generator
  * accepts a match of one of the 17 family-A roots only when it is a real word of that root
    (protocols/m1_positive_matching_precision_protocol.md, M1-PREC-1, pseudo-label rule v4): not a
    digit token ("59", "6-7"), not a unit or brand ("4k", "GOT7"), not a clean word behind
    punctuation ("(Amin)", "sıkı."), not the tail of an apostrophe or masked word ("Bel'am",
    "ta*ak"), not letters harvested across words ("A mı", "T A M A M"), not an ordinary Turkish word
    folded into the root ("sıkıldım", "şike", "öç"), not an unrelated "am" word ("amacı", "I am"),
    not a stable clean form ("AK Parti", "GT", "pc", "book"); a masked letter may complete a
    family-A root ("ta*ak" -> taşak)

Deliberately does NOT:
  * search free substrings. A root inside a longer word is a collision, never a
    match; this is the single most common failure of Turkish filters (spec.md §5)
  * define the evaluation slice. The study's lexicon_hit / lexicon_free split is
    frozen in eval/frozen/study_slice_dev.json; this module is the runtime signal
  * use karaliste (spec.md §5: historical comparison point only)
  * produce A4 or HOMONYM yet: the sacred-concept extension and its homonym rules
    are not built (spec.md §4.3, §8)
  * guess a target: A1 is only the family-A carrier, fusion assigns A1/A2/A3; B1 / B2 / B3
    are not target-assigned
  * put an ordinary insult on the family-A carrier: family A is the rule-v3 POSITIVE set only

Turkish casing: text is lowercased Turkish-style (I -> ı, İ -> i) before terlik
sees it. terlik's own folding maps I -> i, which turns "SIKINTI" (sıkıntı) into a
profane root - the most common silent bug in Turkish NLP.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from contracts.codes import ContentCode, GuardCode, ModuleName, TargetType
from contracts.module_api import NORMALIZED, RAW, BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult, Span

SOURCE = ModuleName.M1_LEXICON.value
ENGINE = "terlik 0.1.0 balanced"

# Same letter folding terlik applies before matching (terlik/lang/tr/config.py
# char_map), so a collision is detected in the space the matcher works in:
# "goturmek" typed without Turkish letters still collides with "göt".
FOLD = str.maketrans("çğıöşü", "cgiosu")

# Clean words that begin with a terlik root and that terlik 0.1.0's suffix engine
# reads as root + suffix. A match whose word begins with one of these, where the
# clean word is longer than the matched root, is a collision, not a match.
#   amca    - "uncle": terlik reads am + ca (spec.md §4.1 names it)
#   sikinti - sıkıntı typed without Turkish letters; terlik whitelists only the
#             Turkish-lettered spelling
# Not passed as terlik's `whitelist` option: a custom whitelist disables terlik's
# per-process pattern cache and costs ~7 s on every construction.
CLEAN_PREFIXES = ("amca", "sikinti")

# Clean WHOLE words that terlik 0.1.0 reads as root + suffix, where a prefix rule would be wrong.
#   amin / âmin - "amen": terlik reads am + in (its whitelist holds the English "amen" only), so
#                 prayer language ("Allah kabul etsin, amin") fired the obscene root `am`.
# Matched on the Turkish-lowercased, UNFOLDED surface of the whole match, elongation allowed
# ("amiiin"). Deliberately NOT a CLEAN_PREFIXES entry: folding maps ı -> i, so the prefix "amin"
# would also swallow "amına koyim" / "aminakoyim". And deliberately dotted-i only: "amın" (dotless)
# is the genitive of the obscene root and stays a match. "amîn" (circumflex i) is the same prayer word
# (M1-PREC-1 R7, 0.3.0).
CLEAN_WORDS = {"amin": re.compile(r"[aâ]+m+[iî]+n+")}

WORD = re.compile(r"\w+", re.UNICODE)

# -- runtime routing (protocols/m1_runtime_routing_protocol.md, M1-ROUTE-1) --------------------
# Data, copied from the protocol's ROUTE_* lines; tests/test_m1_lexicon_labels.py checks that
# they equal the protocol, that ROUTE_A equals the frozen rule-v3 POSITIVE set, and that the five
# sets partition the pinned terlik dictionary. m1 refuses to load if terlik holds a root the table
# does not route: an unrouted root would otherwise be silently dropped or silently called profanity.
ROUTE_A = frozenset({
    "am", "amcı", "amk", "bok", "gavat", "göt", "hassiktir", "orospu", "oç", "pezevenk", "piç", "sakso", "sg",
    "sik", "sktrgt", "taşak", "yarrak"})
ROUTE_B1 = frozenset({
    "ahlaksız", "ahmak", "akılsız", "alçak", "alık", "andaval", "aptal", "arsız", "avanak", "ağzıbozuk",
    "aşağılık", "aşifte", "baldırıçıplak", "beyinamip", "beyinsiz", "budala", "dalkavuk", "dallama", "dangalak",
    "dangoz", "densiz", "denyo", "domuz", "dümenci", "dürzü", "edepsiz", "embesil", "enayi", "ezik", "eşek",
    "eşoğlueşek", "fahişe", "fırıldak", "gerizekalı", "gerzek", "görgüsüz", "hayasız", "haysiyetsiz", "hergele",
    "hödük", "hımbıl", "hınzır", "ibne", "ikiyüzlü", "kafasız", "kahpe", "kalleş", "kaltak", "kalınkafalı",
    "kancık", "kansız", "karaktersiz", "kepaze", "kevaşe", "kötüniyetli", "küstah", "kıro", "kıtakıllı",
    "madrabaz", "maganda", "magat", "mal", "mankafa", "manyak", "maymun", "müptezel", "namussuz", "nankör",
    "onursuz", "oğlancı", "pislik", "puşt", "rezil", "sahtekar", "salak", "saloz", "sersem", "serseri", "soysuz",
    "sürtük", "terbiyesiz", "ukala", "utanmaz", "vefasız", "yalaka", "yarımakıllı", "yavşak", "yobaz",
    "yüzkarası", "yüzsüz", "zonta", "zugar", "zukkafa", "çomar", "çüş", "öküz", "üçkağıtçı", "şapşal",
    "şarlatan", "şerefsiz"})
ROUTE_B2 = frozenset({
    "boğazınıkeserim", "canınıalırım", "ensenibulurum", "gömerler", "kafanıkırarım", "mezarınıkazarım",
    "öldürücem"})
ROUTE_B3 = frozenset({
    "allahbelanıversin", "asılası", "belanıbulurum", "cehenneme", "defol", "geber", "gömülesi", "kesilesi",
    "yakılası"})
ROUTE_NONE = frozenset({
    "dingil", "dolandırıcı", "döl", "fuhuş", "glk", "hapiyedin", "kalpazan", "kaybol", "kaşar", "kerhane", "meme",
    "tabanvansen", "tokmakçı", "yıkık"})
ROUTE_CLASSES: dict[str, tuple[frozenset[str], ContentCode | None]] = {
    "A": (ROUTE_A, ContentCode.A1), "B1": (ROUTE_B1, ContentCode.B1), "B2": (ROUTE_B2, ContentCode.B2),
    "B3": (ROUTE_B3, ContentCode.B3), "NONE": (ROUTE_NONE, None)}
ROUTE_OF: dict[str, str] = {root: name for name, (roots, _) in ROUTE_CLASSES.items() for root in roots}
# The rule-v3 EXCLUDED set: the only roots the M1-ROUTE-1 §5 match fixes may touch.
EXCLUDED_ROOTS = ROUTE_B1 | ROUTE_B2 | ROUTE_B3 | ROUTE_NONE

# M1-ROUTE-1 §5.1: "allık" (blush) is a clean word that terlik's repetition tolerance reads as
# the EXCLUDED root "alık". Whole match, Turkish-lowercased, unfolded; scoped to that root.
EXCLUDED_CLEAN_WORDS: dict[str, dict[str, re.Pattern[str]]] = {"alık": {"allık": re.compile(r"a+l{2,}[ıi]+k+")}}

# M1-ROUTE-1.1 (amendment (a)): EXCLUDED compound roots whose STANDARD spelling has a word boundary,
# with their components. A whitespace-split match is kept when every token but the last IS its
# component and the last token begins with the last component ("geri zekalısın"). Root-specific:
# a split anywhere else, or on any other root, is still rejected ("Ali Kınık" is not "alık").
# Copied from the protocol's COMPOUND line; tests/test_m1_lexicon_labels.py pins the two together.
COMPOUND_ROOTS: dict[str, tuple[str, ...]] = {
    "gerizekalı": ("geri", "zekalı"), "kötüniyetli": ("kötü", "niyetli"), "üçkağıtçı": ("üç", "kağıtçı"),
    "kalınkafalı": ("kalın", "kafalı"), "yarımakıllı": ("yarım", "akıllı"), "kıtakıllı": ("kıt", "akıllı"),
    "yüzkarası": ("yüz", "karası"), "ağzıbozuk": ("ağzı", "bozuk"), "baldırıçıplak": ("baldırı", "çıplak"),
    "beyinamip": ("beyin", "amip"), "eşoğlueşek": ("eş", "oğlu", "eşek")}
SPLIT_REASON = "split across words, not the bare root"
TRAILING_PUNCT = re.compile(r"[^\w\s]+$", re.UNICODE)

# -- POSITIVE-root matching precision (M1-PREC-1, pseudo-label rule v4) --------------------------
# protocols/m1_positive_matching_precision_protocol.md, rules R1-R9, applied to matches of the ROUTE_A
# roots only. Data copied from the protocol's PREC_* lines; test_unit.py pins them to the protocol and
# runs its ACCEPT_* lists. EXCLUDED-root matching (M1-ROUTE-1 §5, M1-ROUTE-1.1) is not touched.
PREC_EDGE_KEPT = frozenset("@$")                   # terlik's leet letters: never removed, anywhere
PREC_EDGE_KEPT_LEADING = frozenset("!")            # leet i at a word start; a word-FINAL "!" is punctuation
PREC_IN_WORD = frozenset("*+!")                    # masks / leet: never a word boundary inside a word
PREC_IN_WORD_BETWEEN_LETTERS = frozenset(".-_'’‘")   # a.q, o.ç, g.t, taşAK'larını
PREC_APOSTROPHES = frozenset("'’‘")
PREC_MASKS = frozenset("*+")
PREC_CROSS_WORD = frozenset("&")
# R6: the family-A roots whose Turkish-letter spelling is an ordinary Turkish stem (sık, şık, şike, öç).
PREC_TURKISH_STEMS: dict[str, tuple[str, ...]] = {"sik": ("sık", "şık", "şik"), "oç": ("öç", "öc")}
PREC_BACK_VOWELS = frozenset("aıou")
PREC_HARMONY_BREAK_VOWELS = frozenset("eöü")
PREC_INVARIANT_SUFFIXES = ("ken",)
# R7: "am", its case / possessive inflections and the amcık forms, on a letters-only word.
PREC_AM_FORMS = re.compile(r"am(?:c[ıiu]k\w*|c[ıi]|dan|da|la|lar\w*|[ıi](?:n(?:[ıiae]|d[ae]n?|[ıi]n|[ıi]z\w*)?"
                           r"|m(?:[ıiae]|d[ae]n?|la|[ıi]z\w*)?|yla)?)?")
# R8: (root, form, space the pattern reads, pattern). "ananı" is built in _load from terlik's suffixes.
#   lower  = the word Turkish-lowercased; folded = lowered and folded; cased = the word as written
PREC_CLEAN_FORMS: tuple[tuple[str, str, str, re.Pattern[str] | None], ...] = (
    ("amk", "ak", "lower", re.compile(r"a+[._-]?k+")),      # "white", the AK party: never amk (owner)
    ("amk", "ananı", "folded", None),                       # "your mother": not an obscene root (owner)
    ("göt", "gt", "lower", re.compile(r"g+t+")),            # Twitter "follow back"; g.t / g*t stay
    ("göt", "gta", "lower", re.compile(r"gta")),            # game title
    ("göt", "GOT", "cased", re.compile(r"GOT")),            # all-capitals title; lowercase got stays (owner)
    ("piç", "pc", "lower", re.compile(r"pc")),              # computer
    ("bok", "book", "lower", re.compile(r"book")),          # English
)
PREC_MASK = "*"                                    # R9: one asterisk = one hidden letter
SPACED_RUN = re.compile(r"(?<!\S)\S(?: \S)+(?!\S)")   # R5: single characters, ONE space apart
LETTERS_ONLY = re.compile(r"[^\W\d_]+")
APOSTROPHE_IN_WORD = re.compile(r"[^\W\d_][" + "".join(sorted(PREC_APOSTROPHES)) + r"][^\W\d_]")


def tr_lower(text: str) -> str:
    """Turkish lowercasing that keeps every index: I -> ı, İ -> i, then per-char
    lower(). A character whose lowercase is longer than one character is kept as
    it is, so offsets into the lowered text are offsets into the input."""
    out = []
    for ch in text:
        if ch == "I":
            out.append("ı")
        elif ch == "İ":
            out.append("i")
        else:
            low = ch.lower()
            out.append(low if len(low) == 1 else ch)
    return "".join(out)


def fold(text: str) -> str:
    return text.translate(FOLD)


@dataclass
class ChannelResult:
    hits: list[tuple[str, Span]]          # (root, span in channel text)
    collisions: list[tuple[str, Span]]    # (evidence, span in channel text)


class LexiconModule(BaseModule):
    name = ModuleName.M1_LEXICON
    version = "0.3.0"    # 0.3.0: M1-PREC-1 - POSITIVE-root matching precision (rule v4, R1-R9); amîn is amen
    #                      0.2.1: M1-ROUTE-1.1 - compound-root word boundaries; punctuation cut (EXCLUDED roots)
    #                      0.2.0: per-root routing A1 / B1 / B2 / B3 / none (M1-ROUTE-1), private `_matches`,
    #                      HOMONYM on mal / domuz compounds, EXCLUDED-root fixes (allık, split across words)
    #                      0.1.2: collision evidence lists roots in a fixed order, not set order
    #                      0.1.1: "amin" / "âmin" (amen) is a clean whole word, not am + in
    provides = frozenset({"content", "guards"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # spec.md §3: every match and every guard carries the span of the triggering substring.
    emits_spans = True

    def _load(self) -> None:
        try:
            from terlik import Terlik
            from terlik.normalizer import normalize
            from terlik.types import TerlikOptions
        except ImportError as exc:
            raise RuntimeError("terlik is not installed: pip install -r modules/m1_lexicon/requirements.txt") from exc
        from terlik.lang.tr.config import config as tr_config
        self._normalize = normalize
        self._engine = Terlik(TerlikOptions(mode="balanced"))
        # M1-PREC-1: terlik's own pattern per root, its whitelist and its suffixes decide "a whole word
        # of the root"; every spelling (root + variants) of a family-A root is a masked-root template.
        self._patterns = self._engine.get_patterns()
        self._whitelist = {w.lower() for w in tr_config.dictionary.whitelist}
        suffixes = sorted({fold(tr_lower(s)) for s in tr_config.dictionary.suffixes}, key=lambda s: (-len(s), s))
        self._anani = re.compile(r"anani(?:" + "|".join(map(re.escape, suffixes)) + r"){0,2}")
        self._spellings = {e.root: sorted({tr_lower(w) for w in [e.root, *e.variants]})
                           for e in tr_config.dictionary.entries if e.root in ROUTE_A}
        unrouted = set(self._engine.get_patterns()) - set(ROUTE_OF)
        if unrouted:
            raise RuntimeError(f"terlik roots with no M1-ROUTE-1 route {sorted(unrouted)}: "
                               "protocols/m1_runtime_routing_protocol.md must route every dictionary root")
        # Compile the patterns now (class-level cache inside terlik), not on the first post.
        self._engine.get_matches("warmup")
        # Longest first, then alphabetical. Sorting on length alone kept equal-length roots in SET
        # order, which follows PYTHONHASHSEED: "hocam" was reported as "am/oc" or "oc/am" depending on
        # the process, so the derived label files were not byte-reproducible (labels were unaffected).
        self._roots = sorted({fold(root) for root in self._engine.get_patterns()}, key=lambda root: (-len(root), root))

    def _run(self, ctx: Context) -> ModuleOutput:
        raw_text = ctx.best_text(RAW)
        channels: dict[str, str] = {RAW: raw_text}
        if ctx.normalized_text is not None:
            channels[NORMALIZED] = ctx.normalized_text

        raw_map = self._raw_offsets(ctx, raw_text)
        notes: list[str] = []
        content: list[ContentScore] = []
        matches: list[dict[str, Any]] = []        # every match, whatever its route (private `_matches`)
        match_spans: list[Span] = []              # one per (channel, original span): homonym context
        collisions: dict[Span, str] = {}
        hit = {RAW: False, NORMALIZED: False}
        roots: set[str] = set()

        for channel, text in channels.items():
            offsets = raw_map if channel == RAW else self._normalized_offsets(ctx, text, raw_text, raw_map)
            result = self._scan(text, self._original_view(ctx.text, text, offsets))
            hit[channel] = bool(result.hits)
            roots.update(root for root, _ in result.hits)
            if offsets is None and (result.hits or result.collisions):
                # No offset map for this channel (m2 published none and the lengths differ): the
                # flag stands, but a score without a span would be dropped, so none is emitted.
                notes.append(f"{channel}: {len(result.hits)} match(es), {len(result.collisions)} collision(s) "
                             "without a map to original offsets; flag reported, no span items emitted")
                continue
            seen_spans: set[Span] = set()
            seen: set[tuple[str, Span]] = set()
            emitted: set[tuple[ContentCode, Span]] = set()
            for root, span in result.hits:
                original = self._to_original(ctx.text, offsets, span)
                if original not in seen_spans:
                    seen_spans.add(original)
                    match_spans.append(original)
                if (root, original) in seen:
                    continue
                seen.add((root, original))
                route = ROUTE_OF[root]
                matches.append({"root": root, "channel": channel, "span": list(original), "route": route})
                code = ROUTE_CLASSES[route][1]
                if code is None or (code, original) in emitted:
                    continue                      # NONE: a real match that is not itself abusive
                emitted.add((code, original))
                content.append(ContentScore(code=code, score=1.0, source=f"{SOURCE}@{channel}", span=original))
            for evidence, span in result.collisions:
                collisions.setdefault(self._to_original(ctx.text, offsets, span), f"{channel}: {evidence}")

        guards = [GuardResult(code=GuardCode.SUBSTRING_COLLISION, score=1.0, source=SOURCE,
                              evidence=evidence, span=span)
                  for span, evidence in sorted(collisions.items())]
        guards += self._homonym_guards(ctx.text, match_spans)
        guards += self._non_human_guards(ctx, content, notes)

        return ModuleOutput(
            content=content,
            guards=guards,
            signals={
                "lexicon_hit": hit[RAW] or hit[NORMALIZED],
                "lexicon_hit_raw": hit[RAW],
                "lexicon_hit_norm": hit[NORMALIZED],
                "matched_roots": sorted(roots),
                "engine": ENGINE,
                # Private (pipeline.run.public_signals keeps "_" keys out of the response): every
                # match with its original span, including routes that emit no content code. The
                # pseudo-label generator reads the matches from here, never from content scores.
                "_matches": matches,
            },
            notes=notes,
        )

    def _original_view(self, original: str, text: str, offsets: list[int] | None) -> Any:
        """span in the channel text -> the ORIGINAL text it stands for (M1-PREC-1: R1, R2 and the cased
        R8 form read the original evidence - m0 lowercases, m2 repairs leet). Without an offset map, the
        channel text itself."""
        if offsets is None:
            return lambda span: text[span[0]:span[1]]
        return lambda span: original[slice(*self._to_original(original, offsets, span))] if span[0] < span[1] else ""

    # -- homonyms (spec §3, §7) ------------------------------------------------
    # A matched ROOT whose standalone surface is also an innocent word in a declared context.
    # Data: surface -> (regex over the text BEFORE the match or None, regex over the text AFTER it
    # or None, reason, lowered). `lowered`: the context is Turkish-lowercased first (tr_lower), so a
    # pattern written in lowercase Turkish letters also reads "MAL VARLIĞI". Sources in README.md.
    # The guard is scoped by span (ADR-001): it suppresses only that match, and only the codes
    # thresholds.yaml lists for HOMONYM.
    _AM = re.compile(r"(\d{1,2}(?:[:.]\d{2})?\s*$)|(^\s*[/\-]\s*pm\b)|(\bpm\s*[/\-]\s*$)", re.IGNORECASE)
    HOMONYMS: dict[str, tuple[re.Pattern[str] | None, re.Pattern[str] | None, str, bool]] = {
        # "am" as the time-of-day abbreviation: "10 am", "10:30 am", "am/pm", "am-pm" (both sides, as before)
        "am": (_AM, _AM, "time abbreviation (am/pm)", False),
        # M1-ROUTE-1 §4: "mal" as property / goods in a closed set of compounds. "mal", "mal mısın",
        # "mal gibi" keep firing: only the next word decides, and only from this list.
        "mal": (None, re.compile(r"^\s+(?:varl[ıi]|sahib|m[üu]lk|beyan|bildirim|m[üu]d[üu]r|ve\s+hizmet)"),
                "property / goods compound (mal varlığı, mal sahibi, mal mülk, ...)", True),
        # M1-ROUTE-1 §4: the food and disease compounds only; "domuz herif" keeps firing.
        "domuz": (None, re.compile(r"^\s+(?:eti|et|gribi)(?!\w)"), "food / disease compound (domuz eti, domuz gribi)",
                  True),
    }

    def _homonym_guards(self, text: str, spans: list[Span]) -> list[GuardResult]:
        guards: list[GuardResult] = []
        for start, end in spans:
            surface = tr_lower(text[start:end])
            entry = self.HOMONYMS.get(surface)
            if entry is None:
                continue
            before_rx, after_rx, reason, lowered = entry
            before, after = text[max(0, start - 12):start], text[end:end + 12]
            if lowered:
                before, after = tr_lower(before), tr_lower(after)
            if (before_rx is not None and before_rx.search(before)) or (after_rx is not None and after_rx.search(after)):
                guards.append(GuardResult(code=GuardCode.HOMONYM, score=1.0, source=SOURCE,
                                          evidence=f"'{text[start:end]}': {reason}", span=(start, end)))
        return guards

    # -- matching ------------------------------------------------------------
    def _tighten(self, match: Any) -> str:
        """terlik's separator tolerance lets a match run over a following space-separated word
        that reads as a suffix ("salak mısın" is one match) and lets "s a l a k" also yield a
        nested "a k". The span must be the matched word (spec §8), so a match containing a space
        is cut back to the shortest token-boundary prefix that terlik still matches with the
        same root ("s a l a k" stays whole, "salak mısın" becomes "salak")."""
        word = match.word
        if " " not in word.strip():
            return word
        parts = word.split(" ")
        for k in range(1, len(parts)):
            prefix = " ".join(parts[:k])
            if any(m.root == match.root and m.index == 0 and m.word == prefix for m in self._engine.get_matches(prefix)):
                return prefix
        return word

    def _letters(self, text: str) -> str:
        """The letters of `text` in terlik's own matching space (Turkish lowercase, folded, leet
        mapped), every non-letter removed and every run of one letter collapsed to one."""
        return re.sub(r"(.)\1+", r"\1", re.sub(r"[^a-z]", "", self._normalize(text)))

    def _excluded_rejection(self, root: str, matched: str) -> str | None:
        """Why an EXCLUDED-root match is not a hit (M1-ROUTE-1 §5), or None. POSITIVE roots: None.
        terlik's separator tolerance can join letters across a word boundary and take the rest
        as a suffix ("Ali Kınık" -> alık + ınık). A whitespace-split match is kept only when its
        letters ARE the root ("a l ı k", "sal ak"); split AND inflected is rejected."""
        if root not in EXCLUDED_ROOTS:
            return None
        stripped = matched.strip()
        clean = next((c for c, rx in EXCLUDED_CLEAN_WORDS.get(root, {}).items() if rx.fullmatch(stripped)), None)
        if clean is not None:
            return f"clean word {clean}"
        if any(ch.isspace() for ch in stripped) and self._letters(stripped) != self._letters(root) \
                and not self._compound_boundary(root, stripped):
            return SPLIT_REASON
        return None

    def _compound_boundary(self, root: str, matched: str) -> bool:
        """M1-ROUTE-1.1 §1: the split falls exactly on a listed compound root's component boundary,
        with suffix material on the final component only."""
        components = COMPOUND_ROOTS.get(root)
        tokens = matched.split()
        if components is None or len(tokens) != len(components):
            return False
        heads = all(self._letters(t) == self._letters(c) for t, c in zip(tokens[:-1], components[:-1]))
        return heads and self._letters(tokens[-1]).startswith(self._letters(components[-1]))

    def _punctuation_cut(self, root: str, matched: str) -> int | None:
        """M1-ROUTE-1.1 §2: length of the leading word(s) of a split EXCLUDED match that terlik matches
        WHOLE with the same root once trailing punctuation is removed ("eşşek,  at'ı" -> "eşşek"),
        or None. m1's tightening already tried each prefix WITH its punctuation; this only removes the
        punctuation, so it can never add a match or lengthen a span."""
        parts = matched.split(" ")
        for k in range(1, len(parts)):
            prefix = " ".join(parts[:k])
            bare = TRAILING_PUNCT.sub("", prefix)
            if bare == prefix or not bare.strip():
                continue
            if any(m.root == root and m.index == 0 and m.word == bare for m in self._engine.get_matches(bare)):
                return len(bare)
        return None

    # -- POSITIVE-root precision (M1-PREC-1, rule v4) --------------------------------------------
    # One judgement per terlik candidate of a family-A root: R1 -> R5 -> R3 -> R4 -> R2 -> R6 -> R7 -> R8
    # (protocol §4). A rejection names its rule: "rule-v4 R<n>: <reason>".
    @staticmethod
    def _strip_edges(text: str, span: Span) -> Span:
        """R3 (a): drop edge punctuation. Kept at an edge: letters, digits, @ and $ (leet letters), and a
        LEADING "!" (leet i); removed: quotes, brackets, . , : ; ? …, a word-final "!", the hashtag "#",
        "*" / "+" at an edge, emoji and every other symbol. Whitespace is removed too (spaced runs)."""
        start, end = span
        while start < end and not text[start].isalnum() and text[start] not in PREC_EDGE_KEPT \
                and text[start] not in PREC_EDGE_KEPT_LEADING:
            start += 1
        while end > start and not text[end - 1].isalnum() and text[end - 1] not in PREC_EDGE_KEPT:
            end -= 1
        return start, end

    @staticmethod
    def _pieces(text: str, span: Span) -> list[Span]:
        """R3 (c): the words glued inside one segment. Split at every character that is not
        alphanumeric, not @ $ * + !, and not a run of . - _ or apostrophes standing between two
        letters (a.q, g..t, taşAK'larını stay whole)."""
        start, end = span
        pieces: list[Span] = []
        piece_start, i = start, start
        while i < end:
            ch = text[i]
            if ch.isalnum() or ch in PREC_EDGE_KEPT or ch in PREC_IN_WORD:
                i += 1
                continue
            j = i
            while j < end and text[j] in PREC_IN_WORD_BETWEEN_LETTERS:
                j += 1
            if j > i and i > start and j < end and text[i - 1].isalpha() and text[j].isalpha():
                i = j                                   # a joiner run between two letters: inside the word
                continue
            if piece_start < i:
                pieces.append((piece_start, i))
            i = max(j, i + 1)
            piece_start = i
        if piece_start < end:
            pieces.append((piece_start, end))
        return pieces

    def _whole_word(self, root: str, word: str) -> str | None:
        """Why `word` is not a whole word of `root` (protocol §2), or None: terlik's own pattern for the
        root must match ALL of it, Turkish-lowercased or through terlik's normalizer; not a terlik
        whitelist word; not one of m1's clean words (amca, sikinti, amin)."""
        lowered = tr_lower(word)
        normalized = self._normalize(word)
        if lowered in self._whitelist or normalized in self._whitelist or word.lower() in self._whitelist:
            return f"terlik whitelist word {lowered}"
        pattern = self._patterns[root]
        if not (pattern.fullmatch(lowered) or pattern.fullmatch(normalized)):
            return "not a word of the root"
        folded = fold(lowered)
        clean = next((c for c in CLEAN_PREFIXES if folded.startswith(c) and len(c) > len(root)), None)
        if clean is None:
            clean = next((c for c, rx in CLEAN_WORDS.items() if rx.fullmatch(lowered)), None)
        return None if clean is None else f"clean word {clean}"

    def _words_of(self, root: str, text: str, span: Span) -> tuple[list[Span], str | None]:
        """R3: the word(s) of a candidate - edge-stripped, a whole word of the root, or the glued
        pieces of a segment that are - with the rejection reason when there is none."""
        start, end = self._strip_edges(text, span)
        if start >= end:
            return [], "rule-v4 R3: no word left after edge punctuation"
        reason = self._whole_word(root, text[start:end])
        if reason is None:
            return [(start, end)], None
        words = []
        for piece in self._pieces(text, (start, end)):
            if piece == (start, end):
                continue
            p_start, p_end = self._strip_edges(text, piece)
            if p_start < p_end and self._whole_word(root, text[p_start:p_end]) is None:
                words.append((p_start, p_end))
        return words, (None if words else f"rule-v4 R3: {reason}")

    @staticmethod
    def _tail_of_a_longer_word(text: str, span: Span) -> str | None:
        """R4 (a): a word right after an apostrophe or a mask that follows a letter is a tail."""
        start = span[0]
        if start > 1 and (text[start - 1] in PREC_APOSTROPHES or text[start - 1] in PREC_MASKS) \
                and text[start - 2].isalpha():
            return "rule-v4 R4: tail of an apostrophe or masked word"
        return None

    @staticmethod
    def _after_english_i(text: str, start: int) -> bool:
        """A lone I / i token, then whitespace, right before `start` (R7: "I am")."""
        i = start
        while i > 0 and text[i - 1].isspace():
            i -= 1
        return i < start and i >= 1 and text[i - 1] in "Iiİı" and (i == 1 or text[i - 2].isspace())

    def _word_rules(self, root: str, word: str, evidence: str, text: str, start: int) -> str | None:
        """R2, R6, R7, R8 on one word. `evidence` is the original text the word stands for (R2, cased R8)."""
        if any(s and (s[0].isdigit() or s[-1].isdigit()) for s in (word, evidence)):
            return "rule-v4 R2: digit at the word edge"
        lowered = tr_lower(word)
        stems = PREC_TURKISH_STEMS.get(root)
        if stems:
            letters = re.sub(r"(.)\1+", r"\1", "".join(ch for ch in lowered if ch not in PREC_IN_WORD_BETWEEN_LETTERS))
            stem = next((s for s in stems if letters.startswith(s)), None)
            if stem is not None:
                rest = letters[len(stem):]
                for suffix in PREC_INVARIANT_SUFFIXES:
                    rest = rest.replace(suffix, "")
                back_stem = any(v in PREC_BACK_VOWELS for v in stem)
                if not (back_stem and any(v in PREC_HARMONY_BREAK_VOWELS for v in rest)):
                    return f"rule-v4 R6: Turkish spelling {stem}, a different word"
        if root == "am":
            plain = lowered.replace("â", "a").replace("î", "i")
            if LETTERS_ONLY.fullmatch(plain):
                if plain == "am" and self._after_english_i(text, start):
                    return "rule-v4 R7: English 'I am'"
                if not PREC_AM_FORMS.fullmatch(plain):
                    return f"rule-v4 R7: not an obscene am form ({plain})"
        for form_root, form, space, pattern in PREC_CLEAN_FORMS:
            if form_root != root:
                continue
            target = evidence if space == "cased" else fold(lowered) if space == "folded" else lowered
            if (pattern or self._anani).fullmatch(target):
                return f"rule-v4 R8: clean form {form}"
        return None

    def _valid_word(self, root: str, word: str, evidence: str, text: str, start: int) -> str | None:
        """R4 (b), then R2, R6, R7, R8, on a whole word of the root: why it is not a valid word, or None."""
        apostrophe = APOSTROPHE_IN_WORD.search(word)
        if apostrophe is not None:
            head = word[:apostrophe.start() + 1]
            if self._whole_word(root, head) is not None or self._word_rules(root, head, head, text, start) is not None:
                return "rule-v4 R4: the root is not before the apostrophe"
        return self._word_rules(root, word, evidence, text, start)

    def _judge_word(self, root: str, text: str, span: Span, original: Any) -> str | None:
        """R4 (a) and _valid_word on one word span (already a whole word of the root)."""
        return self._tail_of_a_longer_word(text, span) or \
            self._valid_word(root, text[span[0]:span[1]], original(span), text, span[0])

    def _spaced_run(self, text: str, span: Span) -> Span | None:
        """R5 (b): the spaced run (single characters, ONE space apart) that holds the candidate."""
        for run in SPACED_RUN.finditer(text):
            if run.start() <= span[0] and span[1] <= run.end():
                return run.span()
        return None

    def _positive_cut(self, root: str, text: str, span: Span, original: Any) -> Span | None:
        """R5 (a): the first whitespace-token prefix that ends in punctuation and, without it, is a
        valid word of the root (M1-ROUTE-1.1 §2's cut, for POSITIVE roots). Never lengthens a span."""
        start, end = span
        parts = text[start:end].split(" ")
        for k in range(1, len(parts)):
            prefix = " ".join(parts[:k])
            bare = TRAILING_PUNCT.sub("", prefix)
            if bare == prefix or not bare.strip() or any(ch.isspace() for ch in bare):
                continue
            words, _ = self._words_of(root, text, (start, start + len(bare)))
            if len(words) == 1 and self._judge_word(root, text, words[0], original) is None:
                return words[0]
        return None

    def _judge_positive(self, root: str, text: str, span: Span, original: Any) -> tuple[list[Span], str | None]:
        """The hit span(s) M1-PREC-1 keeps for one candidate of a family-A root, or the rejection."""
        surface = text[span[0]:span[1]]
        if not any(ch.isalpha() for ch in original(span)):
            return [], "rule-v4 R1: no letter"
        if any(ch.isspace() or ch in PREC_CROSS_WORD for ch in surface):
            cut = self._positive_cut(root, text, span, original)
            if cut is not None:
                return [cut], None
            run = self._spaced_run(text, span)
            if run is None:
                return [], "rule-v4 R5: split across words"
            run = self._strip_edges(text, run)
            joined = text[run[0]:run[1]].replace(" ", "")
            reason = self._whole_word(root, joined) if joined else "empty"
            if reason is not None:
                return [], f"rule-v4 R5: spaced run {joined} is not a word of the root ({reason})"
            reason = self._valid_word(root, joined, original(run).replace(" ", ""), text, run[0])
            return ([run], None) if reason is None else ([], f"{reason} (spaced run {joined})")
        words, reason = self._words_of(root, text, span)
        kept = []
        for word in words:
            reason = self._judge_word(root, text, word, original)
            if reason is None:
                kept.append(word)
        return kept, (None if kept else reason)

    def _masked_hits(self, text: str, lowered: str, taken: list[Span], original: Any) -> list[tuple[str, Span]]:
        """R9: a token whose asterisk(s) complete a spelling of a family-A root. One asterisk is one
        hidden letter; the writer's other letters are kept; the rebuilt word must be a valid word."""
        hits: list[tuple[str, Span]] = []
        for token in re.finditer(r"\S+", text):
            if PREC_MASK not in token.group():
                continue
            start, end = self._strip_edges(text, token.span())
            word = lowered[start:end]
            if not any(0 < i < len(word) - 1 and word[i - 1].isalnum() and word[i + 1].isalnum()
                       for i, ch in enumerate(word) if ch == PREC_MASK):
                continue
            if any(s < end and start < e for s, e in taken):
                continue
            last_mask = word.rindex(PREC_MASK)
            for root in sorted(ROUTE_A):
                for spelling in self._spellings.get(root, ()):
                    n = len(spelling)
                    if n <= last_mask or n > len(word):
                        continue
                    if not all(c == PREC_MASK or fold(c) == fold(s) for c, s in zip(word, spelling)):
                        continue
                    rebuilt = "".join(s if c == PREC_MASK else c for c, s in zip(word, spelling)) + word[n:]
                    if self._whole_word(root, rebuilt) is None and \
                            self._valid_word(root, rebuilt, original((start, end)), text, start) is None:
                        hits.append((root, (start, end)))
                        break
                else:
                    continue
                break
        return hits

    def _scan(self, text: str, original: Any = None) -> ChannelResult:
        """terlik's matches on one channel text, judged. `original`: channel span -> the original text it
        stands for (M1-PREC-1 reads the original evidence for R1, R2 and the cased R8 form)."""
        original = original or (lambda span: text[span[0]:span[1]])
        lowered = tr_lower(text)
        candidates: list[tuple[str, Span]] = []
        collisions: list[tuple[str, Span]] = []
        for match in self._engine.get_matches(lowered):
            matched = self._tighten(match)
            span = (match.index, match.index + len(matched))
            word = fold(matched)
            clean = next((c for c in CLEAN_PREFIXES if word.startswith(c) and len(c) > len(match.root)), None)
            if clean is None:
                clean = next((c for c, rx in CLEAN_WORDS.items() if rx.fullmatch(matched.strip())), None)
            if clean is None:
                candidates.append((match.root, span))
            else:
                collisions.append((f"{match.root} in {matched} (clean word {clean})", span))

        # A hit strictly inside another hit's span is an artefact of separator tolerance
        # ("a k" inside "s a l a k"): the enclosing match is the word, the inner one is not.
        def nested(hit: tuple[str, Span], pool: list[tuple[str, Span]]) -> bool:
            return any(o[1][0] <= hit[1][0] and hit[1][1] <= o[1][1] and o[1] != hit[1] for o in pool)

        # EXCLUDED roots: exactly as before M1-PREC-1 - nested against every terlik candidate.
        excluded = [c for c in candidates if c[0] not in ROUTE_A]
        excluded_hits = [c for c in excluded if not nested(c, candidates)]

        # POSITIVE roots (M1-PREC-1 §4): judged BEFORE the nested-hit filter, so a rejected glued
        # segment ("[piç(3)") does not hide the valid word inside it ("piç").
        positive_kept: list[tuple[str, Span]] = []
        rejected: list[tuple[str, Span, str]] = []
        for root, span in (c for c in candidates if c[0] in ROUTE_A and not nested(c, excluded)):
            spans, reason = self._judge_positive(root, text, span, original)
            positive_kept += [(root, s) for s in spans if (root, s) not in positive_kept]
            if not spans:
                rejected.append((root, span, reason or "rule-v4"))
        taken = [s for _, s in positive_kept] + [s for _, s in excluded]
        positive_kept += [h for h in self._masked_hits(text, lowered, taken, original) if h not in positive_kept]
        positive_kept = [h for h in positive_kept if not nested(h, positive_kept + excluded)]
        for root, span, reason in rejected:
            evidence = f"{root} in {lowered[span[0]:span[1]].strip()} ({reason})"
            if not any(s < span[1] and span[0] < e for _, (s, e) in positive_kept) \
                    and (evidence, span) not in collisions:
                collisions.append((evidence, span))

        # M1-ROUTE-1 §5 / M1-ROUTE-1.1: fixes for rule-v3 EXCLUDED roots only, unchanged.
        kept: list[tuple[str, Span]] = []
        for root, span in excluded_hits:
            matched = lowered[span[0]:span[1]]
            reason = self._excluded_rejection(root, matched)
            cut = self._punctuation_cut(root, matched) if reason == SPLIT_REASON else None
            if reason is None:
                kept.append((root, span))
            elif cut is not None:
                kept.append((root, (span[0], span[0] + cut)))      # M1-ROUTE-1.1 §2: the complete word only
            else:
                collisions.append((f"{root} in {matched.strip()} ({reason})", span))
        hits = sorted(positive_kept + kept, key=lambda h: (h[1][0], h[1][1], h[0]))
        for token in WORD.finditer(lowered):
            span = token.span()
            if any(s < span[1] and span[0] < e for _, (s, e) in hits + collisions):
                continue  # already a match, or already reported as a collision
            folded = fold(token.group())
            inside = [root for root in self._roots if root in folded]
            if inside:
                collisions.append((f"{'/'.join(inside)} in {token.group()}", span))
        return ChannelResult(hits=hits, collisions=collisions)

    # -- offsets -------------------------------------------------------------
    @staticmethod
    def _raw_offsets(ctx: Context, raw_text: str) -> list[int] | None:
        """Original index of every character of the raw channel text."""
        if ctx.charsafe_text is None or raw_text == ctx.text:
            return list(range(len(raw_text)))
        m0 = ctx.signals.get(ModuleName.M0_CHARSAFE.value, {})
        offsets = m0.get("_offsets") if hasattr(m0, "get") else None
        if offsets is not None and len(offsets) == len(raw_text):
            return list(offsets)
        if len(raw_text) == len(ctx.text):
            return list(range(len(raw_text)))
        return None

    @staticmethod
    def _normalized_offsets(ctx: Context, text: str, raw_text: str, raw_map: list[int] | None) -> list[int] | None:
        """Original index of every character of the normalized channel text (ADR-008): m2
        publishes `_offsets` in m0's convention. Without it, the same-length fallback keeps the
        pre-ADR-008 behaviour; a length-changing repair without a map stays flag-only."""
        m2 = ctx.signals.get(ModuleName.M2_DEOBF.value, {})
        offsets = m2.get("_offsets") if hasattr(m2, "get") else None
        if offsets is not None and len(offsets) == len(text):
            return [int(o) for o in offsets]
        if raw_map is not None and len(text) == len(raw_text):
            return raw_map
        return None

    @staticmethod
    def _to_original(text: str, offsets: list[int] | None, span: Span) -> Span:
        start, end = span
        assert offsets is not None
        original_start = offsets[start]
        original_end = offsets[end - 1] + 1
        # A composed character in the channel text may stand for a base letter plus
        # combining marks in the original: keep the marks inside the span.
        while original_end < len(text) and unicodedata.combining(text[original_end]):
            original_end += 1
        return (original_start, original_end)

    # -- guards --------------------------------------------------------------
    @staticmethod
    def _non_human_guards(ctx: Context, content: list[ContentScore], notes: list[str]) -> list[GuardResult]:
        target: Any = ctx.signals.get(ModuleName.M6_TARGET.value)
        if not content or not hasattr(target, "get") or target.get("target_type") != TargetType.NON_HUMAN.value:
            return []
        confidence = target.get("target_confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            notes.append(f"m6_target target_confidence {confidence!r} is not a number; NON_HUMAN_TARGET not raised")
            return []
        spans = sorted({score.span for score in content if score.span is not None})
        return [GuardResult(code=GuardCode.NON_HUMAN_TARGET, score=float(confidence), source=SOURCE,
                            evidence="m6_target: non_human", span=span) for span in spans]
