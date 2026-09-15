"""m1_lexicon - lexicon profanity signal, independent of the neural model.

Catches:
  * explicit profane roots with legal Turkish suffixes ("aptallar", "siktiler"),
    via `terlik` 0.1.0 in balanced mode (spec.md §4.3): its suffix engine accepts a
    root only when what follows is a suffix it knows, and it tolerates leet,
    separators and repetition ("g0t", "s i k")
  * the same on the normalized channel from m2, reported separately (spec.md §3)
  * substring collisions: a root found inside a word the boundary test rejected
    ("sik" in "psikoloji", "am" in "amca") -> SUBSTRING_COLLISION on that word
  * NON_HUMAN_TARGET on each of its own family-A matches when m6 publishes
    target_type non_human (ADR-005)

Deliberately does NOT:
  * search free substrings. A root inside a longer word is a collision, never a
    match; this is the single most common failure of Turkish filters (spec.md §5)
  * define the evaluation slice. The study's lexicon_hit / lexicon_free split is
    frozen in eval/frozen/study_slice_dev.json; this module is the runtime signal
  * use karaliste (spec.md §5: historical comparison point only)
  * produce A4 or HOMONYM yet: the sacred-concept extension and its homonym rules
    are not built (spec.md §4.3, §8)
  * guess a target: A1 is only the family-A carrier, fusion assigns A1/A2/A3

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

WORD = re.compile(r"\w+", re.UNICODE)


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
    version = "0.1.0"
    provides = frozenset({"content", "guards"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # spec.md §3: every match and every guard carries the span of the triggering substring.
    emits_spans = True

    def _load(self) -> None:
        try:
            from terlik import Terlik
            from terlik.types import TerlikOptions
        except ImportError as exc:
            raise RuntimeError("terlik is not installed: pip install -r modules/m1_lexicon/requirements.txt") from exc
        self._engine = Terlik(TerlikOptions(mode="balanced"))
        # Compile the patterns now (class-level cache inside terlik), not on the first post.
        self._engine.get_matches("warmup")
        self._roots = sorted({fold(root) for root in self._engine.get_patterns()}, key=len, reverse=True)

    def _run(self, ctx: Context) -> ModuleOutput:
        raw_text = ctx.best_text(RAW)
        channels: dict[str, str] = {RAW: raw_text}
        if ctx.normalized_text is not None:
            channels[NORMALIZED] = ctx.normalized_text

        raw_map = self._raw_offsets(ctx, raw_text)
        notes: list[str] = []
        content: list[ContentScore] = []
        collisions: dict[Span, str] = {}
        hit = {RAW: False, NORMALIZED: False}
        roots: set[str] = set()

        for channel, text in channels.items():
            result = self._scan(text)
            hit[channel] = bool(result.hits)
            roots.update(root for root, _ in result.hits)
            offsets = raw_map if len(text) == len(raw_text) else None
            if offsets is None and (result.hits or result.collisions):
                # No offset map for this channel (m2 publishes none): the flag stands,
                # but a score without a span would be dropped, so none is emitted.
                notes.append(f"{channel}: {len(result.hits)} match(es), {len(result.collisions)} collision(s) "
                             "without a map to original offsets; flag reported, no span items emitted")
                continue
            seen: set[Span] = set()
            for _, span in result.hits:
                original = self._to_original(ctx.text, offsets, span)
                if original not in seen:
                    seen.add(original)
                    content.append(ContentScore(code=ContentCode.A1, score=1.0,
                                                source=f"{SOURCE}@{channel}", span=original))
            for evidence, span in result.collisions:
                collisions.setdefault(self._to_original(ctx.text, offsets, span), f"{channel}: {evidence}")

        guards = [GuardResult(code=GuardCode.SUBSTRING_COLLISION, score=1.0, source=SOURCE,
                              evidence=evidence, span=span)
                  for span, evidence in sorted(collisions.items())]
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
            },
            notes=notes,
        )

    # -- matching ------------------------------------------------------------
    def _scan(self, text: str) -> ChannelResult:
        lowered = tr_lower(text)
        hits: list[tuple[str, Span]] = []
        collisions: list[tuple[str, Span]] = []
        for match in self._engine.get_matches(lowered):
            span = (match.index, match.index + len(match.word))
            word = fold(match.word)
            clean = next((c for c in CLEAN_PREFIXES if word.startswith(c) and len(c) > len(match.root)), None)
            if clean is None:
                hits.append((match.root, span))
            else:
                collisions.append((f"{match.root} in {match.word} (clean word {clean})", span))
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
