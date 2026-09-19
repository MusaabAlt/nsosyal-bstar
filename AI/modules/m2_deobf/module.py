"""m2_deobf - parallel de-obfuscation channel (spec.md; README.md for resources and licences).

Catches (a SECOND representation, `normalized_text`; the original is never touched):
  * tier 1, character rules, always on, no dictionary:
      LEET         digit / symbol standing for a letter inside a word ("s4l4k")
      REPEAT       a letter stretched to three or more copies ("saaalaaak")
      SPACED       letters separated by single spaces ("s a l a k")
      PUNCT_SPLIT  letters separated by one punctuation character ("s.a.l.a.k"; never "*")
      HOMOGLYPH    a non-Turkish accent on a Latin vowel ("áptal"; reported under HOMOGLYPH because
                   the frozen contract has no accent code, with source m2_deobf)
      PHONETIC     q / w / x, letters Turkish does not use, for k / v / ks ("siqtir")
  * tier 2, morphology-backed, disable-able (spec §5):
      DEASCII      Turkish letters restored on a token that is NOT a legal Turkish word while
                   exactly ONE Turkish-lettered candidate IS ("serefsiz" -> "şerefsiz"), validated
                   by zeyrek's word-level analyser; zero or several legal candidates -> untouched.
                   The declared ambiguities (spec §9: sık/sik, kanı/kani, kısmet/kismet) are never
                   resolved, whatever the lexicon says
      SUFFIX_ON_MASKED  a word with a masked letter inside it ("s*ktir"): reported, not altered
  * every transformation emits a FormPattern whose span is the affected token in the ORIGINAL
    text and whose evidence is exactly text[start:end] (spec §9), plus signals["repairs"] with
    the before / after surfaces, and signals["_offsets"] mapping every character of
    normalized_text to its original index (ADR-008)

Deliberately does NOT:
  * repair anything inside a protected token: URLs, e-mails, @mentions, #hashtags, tokens mixing
    digits and letters in brand style (3M, COVID-19), tokens capitalised in the original text
    away from a sentence start (proper nouns, Turkcell'in, Ayşe'yi), digit-only tokens (numbers,
    phone and IBAN shapes). The protection pass runs first (spec §5)
  * resolve sık/sik, kanı/kani or kısmet/kismet by rule (spec §3, §4, §7)
  * handle ABBREV, VOWEL_DROP, WORD_MERGE, CHAR_DROP, DIALECT or EMOJI_SUB: declared unhandled in
    v1 (README.md), they need lexicons the repository does not have
  * touch invisible characters, homoglyphs or Turkish casing (m0, upstream) or accents Turkish
    itself uses (â î û)
  * emit content scores, read or apply any threshold, or replace ctx.text (spec §6, §7)
  * use zeyrek's sentence API (it downloads NLTK data): only the word-level parser, offline
"""
from __future__ import annotations

import itertools
import logging
import re
from dataclasses import dataclass

from contracts.codes import FormCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import FormPattern, FormResult, Span

SOURCE = ModuleName.M2_DEOBF.value

# terlik 0.1.0 LEET_MAP (MIT, badursun/terlik), copied as data: terlik itself is m1's tool and
# its normaliser is a blind whole-string rewrite that cannot produce spans (README.md).
LEET_MAP = {"0": "o", "1": "i", "2": "i", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
            "@": "a", "$": "s", "!": "i"}
PHONETIC_MAP = {"q": "k", "w": "v", "x": "ks"}
# Non-Turkish accents on Latin vowels -> base letter. Turkish letters (â î û ö ü) are NOT keys.
ACCENT_MAP = {"á": "a", "à": "a", "ã": "a", "ä": "a", "å": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
              "í": "i", "ì": "i", "ï": "i", "ó": "o", "ò": "o", "õ": "o", "ú": "u", "ù": "u", "ý": "y", "ñ": "n"}
TURKISH_LETTERS = frozenset("abcçdefgğhıijklmnoöprsştuüvyzâîû")
DEASCII_MAP = {"c": "ç", "g": "ğ", "i": "ı", "o": "ö", "s": "ş", "u": "ü"}
# Declared ambiguities (spec §9): neither reading is chosen, ever.
AMBIGUOUS_DEASCII = frozenset({"sik", "sık", "kani", "kanı", "kismet", "kısmet"})
PUNCT_SEPARATORS = ".-_,/+|"           # "*" excluded: it masks a letter (spec §4)
MASK_CHARS = "*#"
MAX_TIER2_TOKENS = 12                  # latency guard: tokens analysed per post; the rest is noted
MAX_DEASCII_POSITIONS = 6              # 2^6 candidates at most per token

# Evidence strength, never thresholds (form.min_confidence decides in thresholds.yaml).
CONF_SPACED = 0.85
CONF_PUNCT_SPLIT = 0.85
CONF_LEET = 0.75
CONF_REPEAT = 0.70
CONF_PHONETIC = 0.60
CONF_ACCENT = 0.60
CONF_DEASCII = 0.55
CONF_MASKED = 0.70

WORD_RE = re.compile(r"\w+", re.UNICODE)
URL_RE = re.compile(r"^(https?://|www\.)|\.[a-z]{2,4}(/|$)", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[a-z]{2,}$", re.IGNORECASE)
PUNCT_SPLIT_RE = re.compile(r"^([^\W\d_])(([.\-_,/+|])[^\W\d_])(?:\3[^\W\d_])+\3?$", re.UNICODE)
MASKED_RE = re.compile(r"^[^\W\d_]+[*#]+[^\W\d_]+$", re.UNICODE)

Item = tuple[int, str]  # (original index, character)


@dataclass
class Repair:
    code: FormCode
    confidence: float
    span: Span
    before: str
    after: str


@dataclass
class Token:
    start: int          # index into items (inclusive)
    end: int            # index into items (exclusive)
    protected: bool = False
    reason: str = ""


def _is_letter(ch: str) -> bool:
    return ch.isalpha()


def _leet_can_follow_bang(nxt: str) -> bool:
    """True when the character after an "!" keeps the word going: a letter, or another leet symbol
    that is not itself an "!". End of token, "!!" and "!?" all mean the "!" is punctuation."""
    return nxt.isalpha() or (nxt in LEET_MAP and nxt != "!")


class DeobfModule(BaseModule):
    name = ModuleName.M2_DEOBF
    version = "0.1.2"    # 0.1.2: a word-final "!" is punctuation, never a leet "i" ("Amin!" is not "amini")
    #                      0.1.1: tier-2 latency guard made history-independent (charged per post, not per cache miss)
    provides = frozenset({"normalized_text", "form"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # emits no content scores or guards (its form patterns carry spans when a map exists).
    emits_spans = False

    def __init__(self, tier2: bool = True) -> None:
        super().__init__()
        self._tier2_wanted = tier2
        self._analyzer = None
        self._tier2_note: str | None = None
        self._parse_cache: dict[str, bool] = {}   # speed only: NEVER allowed to change an output
        self._charged: list[str] = []            # distinct words looked up for THIS post (the latency guard's unit)
        self._charged_set: set[str] = set()

    # -- load -----------------------------------------------------------------
    def _load(self) -> None:
        if not self._tier2_wanted:
            self._tier2_note = "tier 2 disabled by configuration"
            return
        try:
            logging.getLogger("zeyrek").setLevel(logging.ERROR)   # its analyser logs every path at WARNING
            from zeyrek.morphology import MorphAnalyzer
            self._analyzer = MorphAnalyzer()
            self._is_word("merhaba")                                # warm the lexicon
        except Exception as exc:  # tier 2 is optional by design (spec §5): tier 1 stays
            self._analyzer = None
            self._tier2_note = f"tier 2 disabled: zeyrek unavailable ({type(exc).__name__}: {exc})"

    @property
    def tier2_enabled(self) -> bool:
        """True when the morphology analyser loaded and tier 2 runs (spec §5: disable-able)."""
        return self._analyzer is not None

    # -- run ------------------------------------------------------------------
    def _run(self, ctx: Context) -> ModuleOutput:
        text = ctx.text
        source_text = ctx.charsafe_text if ctx.charsafe_text is not None else text
        notes: list[str] = []
        if self._tier2_note:
            notes.append(self._tier2_note)
        items, mapped = self._initial_items(ctx, source_text)
        if not mapped:
            notes.append("no offset map to the original text (m0 signals absent and lengths differ); "
                         "patterns carry no span and _offsets is not published")
        tokens = self._tokens(items)
        self._protect(text, items, tokens, mapped)
        all_repairs: list[Repair] = []

        items = self._spaced(text, items, tokens, all_repairs)
        tokens = self._tokens(items)
        self._protect(text, items, tokens, mapped)     # recompute after merging; protection is per token
        # Right to left: a repair may shrink or grow its token, which shifts every index after it;
        # the tokens after it are already done, the ones before it are untouched.
        for token in reversed(tokens):
            if not token.protected:
                items = self._repair_token(text, items, token, all_repairs)
        if self._analyzer is not None:
            items = self._tier2(text, items, mapped, all_repairs, notes)
        all_repairs.sort(key=lambda r: r.span)

        normalized = "".join(ch for _, ch in items)
        offsets = [idx for idx, _ in items]
        patterns = [FormPattern(code=r.code, confidence=r.confidence,
                                evidence=(text[r.span[0]:r.span[1]] if mapped else f"{r.before!r} -> {r.after!r}"),
                                span=r.span if mapped else None, source=SOURCE) for r in all_repairs]
        counts: dict[str, int] = {}
        for r in all_repairs:
            counts[r.code.value] = counts.get(r.code.value, 0) + 1
        signals = {
            # Public keys are fixed-size facts (decision #21: the response never grows with the post;
            # form.patterns already carries every repair by contract). Everything that scales with the
            # post - the per-repair list, counts - is internal ("_"-prefixed): later modules and the
            # demo read it through ctx.signals, the response does not carry it.
            "changed": normalized != source_text,
            "codes": sorted(counts),
            "tier2_enabled": self._analyzer is not None,
            "_repairs": [{"code": r.code.value, "span": list(r.span) if mapped else None, "before": r.before,
                          "after": r.after} for r in all_repairs],
            "_repair_counts": counts,
            "_protected_tokens": sum(1 for t in tokens if t.protected),
            "_analyser_calls": len(self._charged),
        }
        if mapped:
            signals["_offsets"] = offsets
            signals["offsets_identity"] = all(i == o for i, o in enumerate(offsets)) and normalized == text
        return ModuleOutput(normalized_text=normalized, form=FormResult(patterns=patterns), signals=signals, notes=notes)

    # -- representation -------------------------------------------------------
    @staticmethod
    def _initial_items(ctx: Context, source_text: str) -> tuple[list[Item], bool]:
        """Characters of the input channel with their ORIGINAL indices (through m0's map)."""
        if ctx.charsafe_text is None or source_text == ctx.text:
            return [(i, ch) for i, ch in enumerate(source_text)], True
        m0 = ctx.signals.get(ModuleName.M0_CHARSAFE.value, {})
        offsets = m0.get("_offsets") if hasattr(m0, "get") else None
        if offsets is not None and len(offsets) == len(source_text):
            return [(int(o), ch) for o, ch in zip(offsets, source_text)], True
        if len(source_text) == len(ctx.text):
            return [(i, ch) for i, ch in enumerate(source_text)], True
        return [(i, ch) for i, ch in enumerate(source_text)], False

    @staticmethod
    def _tokens(items: list[Item]) -> list[Token]:
        tokens: list[Token] = []
        start = None
        for k, (_, ch) in enumerate(items):
            if ch.isspace():
                if start is not None:
                    tokens.append(Token(start, k))
                    start = None
            elif start is None:
                start = k
        if start is not None:
            tokens.append(Token(start, len(items)))
        return tokens

    @staticmethod
    def _surface(items: list[Item], token: Token) -> str:
        return "".join(ch for _, ch in items[token.start:token.end])

    @staticmethod
    def _span(items: list[Item], start: int, end: int) -> Span:
        return (items[start][0], items[end - 1][0] + 1)

    # -- protection pass (spec §5) --------------------------------------------
    def _protect(self, text: str, items: list[Item], tokens: list[Token], mapped: bool) -> None:
        sentence_start = True
        for token in tokens:
            surface = self._surface(items, token)
            original = text[self._span(items, token.start, token.end)[0]:self._span(items, token.start, token.end)[1]] \
                if mapped else surface
            reason = self._protection_reason(original, surface, sentence_start)
            token.protected = reason != ""
            token.reason = reason
            sentence_start = original[-1:] in ".!?…" if original else sentence_start

    @staticmethod
    def _protection_reason(original: str, surface: str, sentence_start: bool) -> str:
        if not any(_is_letter(c) for c in surface):
            return "no letters"                      # numbers, phone / IBAN shapes, punctuation runs
        if original.startswith("@") or original.startswith("#"):
            return "mention or hashtag"
        if URL_RE.search(original) or EMAIL_RE.match(original):
            return "url or e-mail"
        letters = [c for c in original if c.isalpha()]
        has_digit = any(c.isdigit() for c in original)
        if has_digit and any(c.isupper() for c in letters):
            return "brand-style token"               # 3M, COVID-19, TeknoFest2026
        if "'" in original or "’" in original:
            head = original.split("'")[0].split("’")[0]
            if head[:1].isupper():
                return "apostrophe-suffixed proper noun"   # Turkcell'in, Ayşe'yi
        if original[:1].isupper() and not sentence_start and len(letters) > 1 and not original.isupper():
            return "capitalised proper noun"
        if "-" in original and any(c.isupper() for c in letters[1:]):
            return "hyphenated acronym"              # Ar-Ge
        return ""

    # -- tier 1 ---------------------------------------------------------------
    def _spaced(self, text: str, items: list[Item], tokens: list[Token], repairs: list[Repair]) -> list[Item]:
        """Three or more single-letter unprotected tokens separated by one space become one token."""
        drop: set[int] = set()
        run: list[Token] = []

        def flush() -> None:
            if len(run) >= 3:
                for a, b in zip(run, run[1:]):
                    drop.update(range(a.end, b.start))
                first, last = run[0], run[-1]
                span = self._span(items, first.start, last.end)
                before = "".join(ch for _, ch in items[first.start:last.end])
                after = "".join(items[t.start][1] for t in run)
                repairs.append(Repair(FormCode.SPACED, CONF_SPACED, span, before, after))
            run.clear()

        for token in tokens:
            single = (token.end - token.start == 1 and _is_letter(items[token.start][1]) and not token.protected)
            if single and run and token.start - run[-1].end == 1 and items[run[-1].end][1] == " ":
                run.append(token)
            else:
                flush()
                if single:
                    run.append(token)
        flush()
        if not drop:
            return items
        return [it for k, it in enumerate(items) if k not in drop]

    def _repair_token(self, text: str, items: list[Item], token: Token, repairs: list[Repair]) -> list[Item]:
        chunk = items[token.start:token.end]
        span = self._span(items, token.start, token.end)
        before = "".join(ch for _, ch in chunk)
        surface = before

        # PUNCT_SPLIT: s.a.l.a.k -> salak (same separator between every letter)
        m = PUNCT_SPLIT_RE.match(surface)
        if m:
            sep = m.group(3)
            chunk = [(i, ch) for i, ch in chunk if ch != sep]
            repairs.append(Repair(FormCode.PUNCT_SPLIT, CONF_PUNCT_SPLIT, span, surface, "".join(c for _, c in chunk)))
            surface = "".join(c for _, c in chunk)

        # LEET: only where the mapped characters sit among letters of a real word shape.
        # An "!" that nothing letter-like follows closes the word: it is an exclamation mark, never a
        # leet "i". Mapping it turned the prayer word "Amin!" into "amini", which m1 then read as the
        # obscene root am + ini (0.1.2). A word-internal "!" ("s!ktir", "am!na") is still leet.
        letters = [c for c in surface if _is_letter(c)]
        leet = [k for k, (_, c) in enumerate(chunk)
                if c in LEET_MAP and (c != "!" or _leet_can_follow_bang(surface[k + 1:k + 2]))]
        if leet and len(letters) >= 2 and len(leet) <= len(letters) and "'" not in surface and "’" not in surface \
                and all(surface[k - 1:k].isalpha() or surface[k + 1:k + 2].isalpha() for k in leet):
            positions = set(leet)
            chunk = [(i, LEET_MAP[c]) if k in positions else (i, c) for k, (i, c) in enumerate(chunk)]
            after = "".join(c for _, c in chunk)
            repairs.append(Repair(FormCode.LEET, CONF_LEET, span, surface, after))
            surface = after

        # REPEAT: a run of three or more identical letters folds to ONE letter. Turkish has
        # legitimate doubles ("anne", "elli"), never triples, so a double is left alone.
        folded: list[Item] = []
        for c, group in itertools.groupby(chunk, key=lambda it: it[1]):
            run = list(group)
            folded.extend(run[:1] if _is_letter(c) and len(run) >= 3 else run)
        if len(folded) != len(chunk):
            after = "".join(c for _, c in folded)
            repairs.append(Repair(FormCode.REPEAT, CONF_REPEAT, span, surface, after))
            chunk, surface = folded, after

        # PHONETIC: q / w / x inside an otherwise Turkish-lettered word
        if any(c in PHONETIC_MAP for _, c in chunk) and all(c in TURKISH_LETTERS or c in PHONETIC_MAP or not _is_letter(c)
                                                            for _, c in chunk):
            rebuilt: list[Item] = []
            for i, c in chunk:
                if c in PHONETIC_MAP:
                    rebuilt.extend((i, r) for r in PHONETIC_MAP[c])
                else:
                    rebuilt.append((i, c))
            after = "".join(c for _, c in rebuilt)
            repairs.append(Repair(FormCode.PHONETIC, CONF_PHONETIC, span, surface, after))
            chunk, surface = rebuilt, after

        # accent normalisation (HOMOGLYPH): áptal -> aptal
        if any(c in ACCENT_MAP for _, c in chunk):
            chunk = [(i, ACCENT_MAP.get(c, c)) for i, c in chunk]
            after = "".join(c for _, c in chunk)
            repairs.append(Repair(FormCode.HOMOGLYPH, CONF_ACCENT, span, surface, after))
            surface = after

        if surface == before:
            return items
        return items[:token.start] + chunk + items[token.end:]

    # -- tier 2 ---------------------------------------------------------------
    def _is_word(self, word: str) -> bool:
        """Legal Turkish word form per the analyser; cached across posts because the same surface
        recurs and the analyser costs milliseconds per call. The latency guard is charged once per
        DISTINCT word looked up in the current post, whether or not the cross-post cache already
        holds it: a guard that counted cache misses made a post's repairs depend on the posts
        processed before it (found by the derived-labels determinism check, 2026-09-18)."""
        if word not in self._charged_set:
            self._charged_set.add(word)
            self._charged.append(word)
        cached = self._parse_cache.get(word)
        if cached is None:
            try:
                cached = bool(self._analyzer._parse(word))
            except Exception:
                cached = False
            self._parse_cache[word] = cached
        return cached

    def _tier2(self, text: str, items: list[Item], mapped: bool, repairs: list[Repair],
               notes: list[str]) -> list[Item]:
        tokens = self._tokens(items)
        self._protect(text, items, tokens, mapped)
        self._charged = []                # distinct words looked up for THIS post; the latency guard counts these
        self._charged_set: set[str] = set()
        capped = False
        for token in tokens:
            if token.protected:
                continue
            surface = self._surface(items, token)
            span = self._span(items, token.start, token.end)
            if MASKED_RE.match(surface):
                repairs.append(Repair(FormCode.SUFFIX_ON_MASKED, CONF_MASKED, span, surface, surface))
                continue
            if not surface.isalpha() or len(surface) < 3 or surface in AMBIGUOUS_DEASCII:
                continue
            positions = [k for k, c in enumerate(surface) if c in DEASCII_MAP][:MAX_DEASCII_POSITIONS]
            if not positions:
                continue
            if len(self._charged) >= MAX_TIER2_TOKENS and surface not in self._charged_set:
                capped = True             # a surface already charged in THIS post still repairs; new work stops
                continue
            if self._is_word(surface):
                continue
            candidates = []
            for mask in range(1, 1 << len(positions)):
                chars = list(surface)
                for bit, k in enumerate(positions):
                    if mask >> bit & 1:
                        chars[k] = DEASCII_MAP[chars[k]]
                cand = "".join(chars)
                if cand in AMBIGUOUS_DEASCII:
                    candidates = []           # a candidate reading is a declared ambiguity: leave it
                    break
                if self._is_word(cand):
                    candidates.append(cand)
                    if len(candidates) > 1:
                        break
            if len(candidates) != 1:
                continue
            after = candidates[0]
            chunk = [(i, a) for (i, _), a in zip(items[token.start:token.end], after)]
            items = items[:token.start] + chunk + items[token.end:]
            repairs.append(Repair(FormCode.DEASCII, CONF_DEASCII, span, surface, after))
        if capped:
            notes.append(f"tier 2 analysed the first {MAX_TIER2_TOKENS} candidate tokens only (latency guard)")
        return items
