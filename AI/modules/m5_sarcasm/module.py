"""m5_sarcasm - degrading sarcasm (D1). STAGE 1: a deterministic, high-precision rule detector.

Owner-approved amendment to the entry gate (protocols/m5_stage1_deterministic_protocol.md, M5-S1;
ADR-003 amendment 2026-09-19). This is NOT a trained model and NOT benchmarked: no sarcasm or D1
corpus exists (docs/blockers/m5_sarcasm_corpus_gate.md). The neural m5 of spec §6 is Stage 2 and
untouched (training/m5_sarcasm/).

Catches (D1 = contempt toward a person delivered through a literally positive element, spec §1, §5),
only when the raw text carries an explicit marker of the inversion AND the addressee is the target:
  * R1_SCARE_QUOTE            scare-quoted praise aimed at the addressee ("Bu kadar 'derin' bir yorum
                              yapman etkileyici.")
  * R2_CLAUSE_FINAL_TABII     praise of the addressee closed by an ironic "tabii" ("Çok zekisin tabii.")
  * R3_CONGRATULATED_FAILURE  a congratulation formula + a second-person past verb of failure
                              ("Aferin sana, yine her şeyi berbat ettin.")
  * R4_IRONY_MARK             praise of the addressee marked "(!)" (TDK irony mark: "Çok akıllısın (!)")
Output: one ContentScore(D1, 1.0, "m5_sarcasm@raw", span=evidence). 1.0 means "a deterministic
Stage-1 rule is satisfied"; it is not a probability. Signals: stage, detector, rules_version,
matched_rules, excluded (what was found and withheld, and why), precedence_checked.

Deliberately does NOT:
  * fire on praise, punctuation, emoji or offensiveness alone - every rule is a conjunction
  * fire without a second-person anchor: sarcasm at a bus, the weather or a program is the spec §8
    control set (X_NO_PERSON), and third-person sarcasm is a documented Stage-1 miss
  * fire on quoted or reported sarcasm (X_REPORTED), a word being discussed (X_MENTION), negated
    praise (X_NEGATED) or a question (X_QUESTION)
  * emit D1 when m1 published lexicon_hit: explicit content wins (spec §3, X_EXPLICIT_CONTENT)
  * read the normalized channel (spec §7, §11) or m6: the person anchor is part of each rule
  * separate sincere from sarcastic praise without a marker ("Zekânı hayranlıkla izliyorum,
    gerçekten." is a known miss - spec §3's hardest negative)
  * apply a threshold (decision/thresholds.yaml, D1 row: placeholder policy)
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from contracts.codes import ContentCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore

RULES_VERSION = "m5-s1-1.0.0"   # changes with every rule or lexicon edit (protocol §10)
SOURCE = f"{ModuleName.M5_SARCASM.value}@raw"
M1 = ModuleName.M1_LEXICON.value
MAX_EXCLUDED = 5                # audit records kept in signals; the rest are counted in a note

R1, R2, R3, R4 = "R1_SCARE_QUOTE", "R2_CLAUSE_FINAL_TABII", "R3_CONGRATULATED_FAILURE", "R4_IRONY_MARK"
X_REPORTED, X_MENTION, X_NEGATED = "X_REPORTED", "X_MENTION", "X_NEGATED"
X_QUESTION, X_NO_PERSON, X_EXPLICIT = "X_QUESTION", "X_NO_PERSON", "X_EXPLICIT_CONTENT"

# -- lexicons (protocol §4; every entry is folded: Turkish lowercase, â/î/û read as a/i/u) ------------
PERSON_PRAISE = frozenset({
    "zeki", "akıllı", "deha", "bilge", "bilgili", "uzman", "profesör", "filozof", "entelektüel", "yetenekli",
    "başarılı", "çalışkan", "kibar", "nazik", "centilmen", "kahraman", "derin", "parlak", "mantıklı"})
GENERAL_PRAISE = frozenset({
    "harika", "mükemmel", "muhteşem", "süper", "müthiş", "şahane", "enfes", "etkileyici", "olağanüstü",
    "fevkalade"})
# Longest first, in a fixed order: a shorter stem never shadows a longer one and the result is deterministic.
PRAISE = tuple(sorted(PERSON_PRAISE | GENERAL_PRAISE, key=lambda stem: (-len(stem), stem)))
# Protocol §4.2: the only endings a praise word may carry. No prefix matching ("süpermarket").
PRAISE_ENDING = re.compile(r"(?:y?s[ıiuü]n(?:[ıiuü]z)?|y?[ıiuü][mz]|[dt][ıiuü]r|y?d[ıiuü]|y?m[ıiuü]ş|[cç][ae])?")
COPULA_2P = re.compile(r"y?s[ıiuü]n(?:[ıiuü]z)?")

PRONOUNS_2P = frozenset({"sen", "sana", "seni", "senin", "senden", "sende",
                         "siz", "size", "sizi", "sizin", "sizden", "sizde"})
PAST_2P = re.compile(r"[dt][ıiuü]n(?:[ıiuü]z)?$")
# A bare "-sın" is not enough: the third-person imperative ("olsun", "gelsin") ends the same way.
PRESENT_2P = re.compile(r"(?:yor|[ıiuüae]r|[ae]c[ae]k|m[ae]l[ıi])s[ıiuü]n(?:[ıiuü]z)?$")
VERBAL_NOUN_2P = re.compile(r"m[ae]n$")
NOT_2P = frozenset({"kadın", "aydın", "odun", "altın", "metin", "çetin", "kesin", "ersin", "tersin",
                    "zaman", "kahraman", "düşman", "orman", "liman", "duman", "roman", "yaman", "ferman"})
MIN_PAST_2P_LEN = 5             # "dün", "adın": too short to read as a second-person past verb

TABII = frozenset({"tabii", "tabi"})
CONGRATULATIONS = (("tebrik", "ederim"), ("helal", "olsun"), ("ne", "güzel"), ("aferin",), ("bravo",),
                   ("tebrikler",), ("harika",), ("süper",), ("mükemmel",), ("muhteşem",), ("şahane",))
CONGRATULATION_TAIL = frozenset({"sana", "size", "ya", "be", "valla", "vallahi"})
INTERJECTIONS = frozenset({"vay", "oh", "ooo", "oo", "hey"})
# Protocol §4.1: second-person past forms only; verbs that are also praise are deliberately absent.
FAILURE_2P = re.compile(
    r"\b(?:berbat\s+ett|rezil\s+ett|rezil\s+old|batırd|beceremed|başaramad|yapamad|çuvallad|geç\s+kald|"
    r"unutt|kaçırd)[ıiuü]n(?:[ıiuü]z)?\b")
REPORTING = frozenset({"dedi", "demiş", "diyor", "der", "diye", "dediği", "söyledi", "söylemiş", "yazdı",
                       "yazmış", "diyen", "deyip", "dediler", "demişti"})
MENTION = frozenset({"kelimesi", "sözcüğü", "kelimesini", "sözcüğünü"})
QUOTE_PAIRS = {"'": "'’", '"': '"”', "‘": "’", "“": "”", "«": "»", "‹": "›"}
MAX_SCARE_QUOTE_WORDS = 2       # longer quoted segments are quotations, not scare quotes
REPORTING_WINDOW = 2            # words after a closing quote searched for a reporting verb
NEGATION_WINDOW = 2             # words after a praise word searched for "değil"

WORD = re.compile(r"[a-zçğıöşü]+")
SENTENCE_END = re.compile(r"[.!?…\n]+")
CLAUSE_END = re.compile(r"[.!?…\n,;:]+")
IRONY_MARK = re.compile(r"\(\s*!\s*\)")
_FOLD = {"I": "ı", "İ": "i", "Â": "a", "â": "a", "Î": "i", "î": "i", "Û": "u", "û": "u"}


def fold(text: str) -> str:
    """Turkish-aware lowercase, one character for one character, so offsets stay offsets into ctx.text."""
    out = []
    for ch in text:
        mapped = _FOLD.get(ch)
        if mapped is None:
            low = ch.lower()
            mapped = low if len(low) == 1 else ch
        out.append(mapped)
    return "".join(out)


@dataclass(frozen=True)
class Word:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Quote:
    start: int          # offset of the opening quote character
    end: int            # offset just after the closing quote character
    words: tuple[Word, ...]
    reported: bool      # a quotation (3+ words, or followed by a reporting verb): reported speech
    mention: bool       # followed by "kelimesi" and the like: a word being discussed


@dataclass(frozen=True)
class Candidate:
    rule: str
    span: tuple[int, int]
    cue: str
    exclusion: str | None


def praise_stem(word: str) -> str | None:
    """The praise stem `word` is built on (protocol §4.2), or None."""
    for stem in PRAISE:
        if word.startswith(stem) and PRAISE_ENDING.fullmatch(word[len(stem):]):
            return stem
    return None


def is_person_anchor(words: list[Word], i: int) -> bool:
    """Protocol §4: is words[i] evidence that the addressee (second person) is the target?"""
    w = words[i].text
    if w in PRONOUNS_2P:
        return True
    if w in NOT_2P:
        return False
    stem = praise_stem(w)
    if stem is not None:
        return w != stem and bool(COPULA_2P.fullmatch(w[len(stem):]))
    if len(w) >= MIN_PAST_2P_LEN and PAST_2P.search(w):
        return True
    if PRESENT_2P.search(w):
        return True
    following = words[i + 1].text if i + 1 < len(words) else ""
    return bool(VERBAL_NOUN_2P.search(w)) and praise_stem(following) is not None


def segments(folded: str, end: re.Pattern[str]) -> list[tuple[int, int, str]]:
    """(start, end, terminator) of each sentence or clause; the "(!)" irony mark ends neither."""
    masked = IRONY_MARK.sub(lambda m: " " * len(m.group()), folded)
    out, start = [], 0
    for m in end.finditer(masked):
        out.append((start, m.start(), m.group()))
        start = m.end()
    out.append((start, len(folded), ""))
    return [s for s in out if s[0] < s[1]]


def find_quotes(folded: str, words: list[Word]) -> list[Quote]:
    """Quoted segments. An opening quote follows a non-letter (so "Ahmet'e" holds none); the closing
    quote is the next matching character on the same line, right after a non-space."""
    quotes, i = [], 0
    while i < len(folded):
        closers = QUOTE_PAIRS.get(folded[i])
        if closers is None or (i and folded[i - 1].isalnum()):
            i += 1
            continue
        j = i + 1
        while j < len(folded) and folded[j] not in closers and folded[j] != "\n":
            j += 1
        if j == len(folded) or folded[j] == "\n" or j == i + 1 or folded[j - 1].isspace():
            i += 1
            continue
        inside = tuple(w for w in words if i < w.start and w.end <= j)
        following = [w.text for w in words if w.start > j][:REPORTING_WINDOW]
        reported = len(inside) > MAX_SCARE_QUOTE_WORDS or any(w in REPORTING for w in following)
        quotes.append(Quote(i, j + 1, inside, reported, bool(following) and following[0] in MENTION))
        i = j + 1
    return quotes


class SarcasmModule(BaseModule):
    name = ModuleName.M5_SARCASM
    version = "1.0.0"
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans. D1 is a post-level
    # code (spec §3); the span on a D1 score is evidence for audit, not a scope for a guard.
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        folded = fold(ctx.text or "")
        words = [Word(m.group(), m.start(), m.end()) for m in WORD.finditer(folded)]
        candidates = self._candidates(folded, words, find_quotes(folded, words))

        notes: list[str] = []
        published = ctx.signals.get(M1)
        lexicon_hit = published.get("lexicon_hit") if isinstance(published, Mapping) else None
        precedence_checked = isinstance(lexicon_hit, bool)
        satisfied = [c for c in candidates if c.exclusion is None]
        if satisfied and not precedence_checked:
            notes.append(f"precedence not checked: {M1} published no lexicon_hit (spec §3)")
        if satisfied and lexicon_hit is True:
            notes.append(f"D1 withheld: {M1} found explicit content, which takes precedence (spec §3)")
            candidates = [Candidate(c.rule, c.span, c.cue, X_EXPLICIT) if c.exclusion is None else c
                          for c in candidates]
            satisfied = []

        excluded = [c for c in candidates if c.exclusion is not None]
        if overflow := excluded[MAX_EXCLUDED:]:
            notes.append(f"{len(overflow)} more excluded construction(s) not listed")
        content = ([ContentScore(code=ContentCode.D1, score=1.0, source=SOURCE, span=satisfied[0].span)]
                   if satisfied else [])
        signals = {
            "stage": 1,
            "detector": "deterministic",
            "rules_version": RULES_VERSION,
            "matched_rules": sorted({c.rule for c in satisfied}),
            "excluded": [{"rule": c.rule, "reason": c.exclusion, "span": list(c.span)}
                         for c in excluded[:MAX_EXCLUDED]],
            "precedence_checked": precedence_checked,
        }
        return ModuleOutput(content=content, signals=signals, notes=notes)

    # -- rules (protocol §4) and exclusions (protocol §5) ------------------------------------------------
    @staticmethod
    def _candidates(folded: str, words: list[Word], quotes: list[Quote]) -> list[Candidate]:
        found: list[Candidate] = []
        sentences = segments(folded, SENTENCE_END)

        def within(start: int, end: int) -> list[int]:
            return [i for i, w in enumerate(words) if start <= w.start and w.end <= end]

        def anchored(indexes: list[int]) -> bool:
            return any(is_person_anchor(words, i) for i in indexes)

        def reported(span: tuple[int, int], sentence_end: int) -> bool:
            """Inside a quotation, or a reporting verb later in the same sentence (spec §11)."""
            if any(q.reported and q.start <= span[0] and span[1] <= q.end for q in quotes):
                return True
            return any(w.text in REPORTING for w in words if span[1] <= w.start and w.end <= sentence_end)

        def negated(i: int) -> bool:
            return any(w.text.startswith("değil") for w in words[i + 1:i + 1 + NEGATION_WINDOW])

        def trim(seq: list[int]) -> list[int]:
            seq = seq[1:] if seq and words[seq[0]].text in INTERJECTIONS else seq
            return seq[:-1] if seq and words[seq[-1]].text in CONGRATULATION_TAIL else seq

        def formula(part: list[int]) -> tuple[int, int] | None:
            """The span of `part` when its words are exactly one congratulation formula."""
            texts = tuple(words[i].text for i in part)
            return (words[part[0]].start, words[part[-1]].end) if texts in CONGRATULATIONS else None

        def congratulation(idx: list[int], previous: list[int]) -> tuple[int, int] | None:
            """A congratulation formula at the start or the end of the sentence, or a sentence of
            its own right before it (protocol §4, R3)."""
            opening = idx[1:] if idx and words[idx[0]].text in INTERJECTIONS else idx
            closing = trim(idx)
            for n in sorted({len(f) for f in CONGRATULATIONS}, reverse=True):
                if (span := formula(opening[:n]) or formula(closing[-n:])) is not None:
                    return span
            return formula(trim(previous)) if previous else None

        previous: list[int] = []
        for s_start, s_end, _ in sentences:
            idx = within(s_start, s_end)
            # R1: scare-quoted praise aimed at the addressee.
            for q in quotes:
                if not s_start <= q.start < s_end or not q.words or len(q.words) > MAX_SCARE_QUOTE_WORDS:
                    continue
                stem = praise_stem(q.words[0].text)
                if stem is None:
                    continue
                span = (q.start, q.end)
                exclusion = (X_REPORTED if reported(span, s_end) else X_MENTION if q.mention
                             else X_NEGATED if negated(words.index(q.words[-1]))
                             else None if anchored(idx) else X_NO_PERSON)
                found.append(Candidate(R1, span, stem, exclusion))
            # R3: a congratulation formula and a second-person past verb of failure.
            for m in FAILURE_2P.finditer(folded, s_start, s_end):
                opener = congratulation(idx, previous)
                if opener is None:
                    continue
                span = (min(opener[0], m.start()), max(opener[1], m.end()))
                exclusion = X_REPORTED if reported((m.start(), m.end()), s_end) else None
                found.append(Candidate(R3, span, folded[opener[0]:opener[1]], exclusion))
            # R4: praise of the addressee marked "(!)".
            for m in IRONY_MARK.finditer(folded, s_start, s_end):
                before = [i for i in idx if words[i].end <= m.start()]
                if not before or folded[words[before[-1]].end:m.start()].strip():
                    continue
                stem = praise_stem(words[before[-1]].text)
                if stem is None:
                    continue
                span = (words[before[-1]].start, m.end())
                exclusion = (X_REPORTED if reported(span, s_end) else X_NEGATED if negated(before[-1])
                             else None if anchored(idx) else X_NO_PERSON)
                found.append(Candidate(R4, span, stem, exclusion))
            previous = idx

        # R2: a clause that ends in "tabii" / "tabi" (optionally + "ki") and praises the addressee.
        for c_start, c_end, terminator in segments(folded, CLAUSE_END):
            idx = within(c_start, c_end)
            tail = [words[i].text for i in idx[-2:]]
            if not tail or not (tail[-1] in TABII or (len(tail) == 2 and tail[1] == "ki" and tail[0] in TABII)):
                continue
            praised = [i for i in idx if praise_stem(words[i].text) is not None]
            if not praised:
                continue
            span = (words[idx[0]].start, words[idx[-1]].end)
            sentence_end = next((e for s, e, _ in sentences if s <= c_start <= e), c_end)
            exclusion = (X_REPORTED if reported(span, sentence_end) else X_QUESTION if "?" in terminator
                         else X_NEGATED if any(negated(i) for i in praised)
                         else None if anchored(idx) else X_NO_PERSON)
            found.append(Candidate(R2, span, praise_stem(words[praised[0]].text) or "", exclusion))
        return sorted(found, key=lambda c: (c.span, c.rule))
