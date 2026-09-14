"""Result dataclasses. Standard library only.

OWNERSHIP SPLIT - the most important rule in this file:

    A module fills           code / score / source (/ evidence / span).
    The decision layer fills threshold / fired (/ active / suppressed).

A module that sets `threshold` or `fired` violates CLAUDE.md rule 4; the
pipeline strips those values and records the violation in `notes`. Keeping
the split in the data type (rather than in reviewer memory) means a stored
result can be re-thresholded offline without re-running any model.

Spans are always [start, end) offsets into the ORIGINAL text.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any

from contracts.codes import Action, ContentCode, FormCode, GuardCode, TargetType

Span = tuple[int, int]


@dataclass
class FormPattern:
    """One observed obfuscation pattern (Axis 2). Filled by a module."""

    code: FormCode
    confidence: float
    evidence: str
    span: Span | None = None
    source: str = ""  # module that observed it


@dataclass
class FormResult:
    patterns: list[FormPattern] = field(default_factory=list)
    # Decision layer only: codes whose best confidence clears form.min_confidence.
    active: list[FormCode] = field(default_factory=list)

    def codes(self) -> list[FormCode]:
        """All observed codes, unthresholded, in first-seen order."""
        return list(dict.fromkeys(p.code for p in self.patterns))


@dataclass
class ContentScore:
    """Axis 1 score.

    Module fills: code, score, source ("<module>@<channel>", channel being
    raw | normalized), span. Decision layer fills: threshold, fired.

    `span` is the exact substring of the ORIGINAL text that triggered the
    score. Guards are scoped by it (ADR-001): without it a same-module guard
    elsewhere in the post can suppress this score.
    """

    code: ContentCode
    score: float
    source: str
    span: Span | None = None  # ADR-001
    threshold: float | None = None  # decision layer only
    fired: bool | None = None  # decision layer only; None = not decided yet


@dataclass
class TargetResult:
    """Axis 3. Filled by a module."""

    type: TargetType = TargetType.NONE
    confidence: float = 0.0
    evidence: str = ""
    span: Span | None = None
    source: str = ""


@dataclass
class GuardResult:
    """Negative-control evidence.

    Module fills: code, score, source, evidence, span. Decision layer fills:
    threshold, active, suppressed.

    ADR-001: a guard only ever suppresses content scores produced by its own
    `source` module, and when both sides carry a span, only overlapping ones.
    A guard with an empty source suppresses nothing.
    """

    code: GuardCode
    score: float
    source: str = ""  # module that raised the guard ("<module>" or "<module>@<channel>")
    evidence: str = ""
    span: Span | None = None  # ADR-001: exact substring of the ORIGINAL text that triggered it
    threshold: float | None = None  # decision layer only
    active: bool | None = None  # decision layer only
    suppressed: list[ContentCode] = field(default_factory=list)  # decision layer only


@dataclass
class ThreadSignal:
    """Axis 4. Repetition is a thread-level fact and lives ONLY here."""

    thread_id: str | None = None
    repeat_count: int = 0
    window_posts: int = 0
    same_target: bool | None = None
    source: str = ""
    threshold: int | None = None  # decision layer only
    fired: bool | None = None  # decision layer only


@dataclass
class AnalysisResult:
    text: str
    verdict: Action | None = None
    form: FormResult = field(default_factory=FormResult)
    content: list[ContentScore] = field(default_factory=list)
    target: TargetResult | None = None
    guards: list[GuardResult] = field(default_factory=list)
    thread: ThreadSignal | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    latency_ms: float = 0.0
    per_module_ms: dict[str, float] = field(default_factory=dict)
    fast_path: bool = False
    trace_id: str = ""
    artifact_hash: str = ""
    notes: list[str] = field(default_factory=list)

    def fired(self) -> list[ContentScore]:
        """Content scores the decision layer marked as fired, highest first."""
        return sorted((s for s in self.content if s.fired), key=lambda s: s.score, reverse=True)

    def top(self) -> ContentScore | None:
        """Highest-scoring non-CLEAN content score regardless of firing."""
        candidates = [s for s in self.content if s.code is not ContentCode.CLEAN]
        return max(candidates, key=lambda s: s.score, default=None)

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def to_jsonable(obj: Any) -> Any:
    """Convert dataclasses / enums / tuples into plain JSON-compatible values."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {(k.value if isinstance(k, Enum) else str(k)): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in obj]
    return obj
