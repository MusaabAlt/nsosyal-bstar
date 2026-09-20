"""The out-of-band `normalization` object of the Go contract.

The frozen AnalysisResult deliberately carries no de-obfuscated text
(HANDOVER decision 17/21: it grows with the post and trace_id is enough for
auditability), so m2's recovered text travels beside the result instead:

    {"text": "<normalized_text>",
     "changes": [{"code", "from_span", "to_span", "from", "to"}]}

Shape and field meanings: backend/docs/inference-contract.md. The panel's
Canlı Analiz page renders `text` in the normalization strip and counts the
changes ("4 karakter kaldırıldı"); `to_span` is what tells the two apart, so
it is derived here, never guessed.

Nothing in this file decides, scores or rewrites anything: it reads what
m2_deobf already published (`normalized_text`, the internal `_repairs` and
`_offsets` of ADR-008) and re-expresses it in the wire shape.
"""
from __future__ import annotations

from typing import Any

M2 = "m2_deobf"


def _to_span(offsets: list[int] | None, start: int, end: int) -> list[int] | None:
    """The run of normalized indices whose source character lies in [start, end).

    `offsets[i]` is the ORIGINAL index of normalized_text[i] (ADR-008). None
    when m2 published no offset map - m0's offsets were unavailable, so it
    emitted no spans either and the repair is dropped before this is called.
    """
    if not offsets:
        return None
    hits = [i for i, source in enumerate(offsets) if start <= source < end]
    if not hits:
        return None  # every character of the span disappeared: a removal
    return [hits[0], hits[-1] + 1]


def build(normalized_text: str | None, signals: dict[str, Any]) -> dict[str, Any] | None:
    """The `normalization` object for one analysis, or None when m2 did not run.

    `signals` is the RAW signal mapping from `Pipeline.analyze_with_internals`
    (internal keys included), not the public one in the response.
    """
    if normalized_text is None:
        return None
    m2 = signals.get(M2) or {}
    if not isinstance(m2, dict):
        return None
    offsets = m2.get("_offsets")
    changes: list[dict[str, Any]] = []
    for repair in m2.get("_repairs") or []:
        span = repair.get("span")
        # A repair without a span cannot be placed in the original text, and
        # from_span is required by the contract. m2 drops spans only when m0's
        # offset map was unavailable, in which case it publishes no _offsets
        # either and nothing here can be placed.
        if not span:
            continue
        start, end = int(span[0]), int(span[1])
        after = repair.get("after", "")
        changes.append({
            "code": repair.get("code"),
            "from_span": [start, end],
            # null when the characters were removed (contract), which is exactly
            # when the repair produced no normalized characters.
            "to_span": _to_span(offsets, start, end) if after != "" else None,
            "from": repair.get("before", ""),
            "to": after,
        })
    return {"text": normalized_text, "changes": changes}
