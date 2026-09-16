"""What the AI can detect today, and which module produces it.

The Kategoriler page and the "N kategoriden M'i değerlendirildi" line show
only these, so update this list in the same change that makes a module
produce a new code (or stop producing one).

Kept here, outside the modules, on purpose: a module declares what fields it
provides, not which content codes its current implementation emits, and module
code belongs to its owner.

Checked against the code on 2026-09-16:
  * m1_lexicon 0.1.0 emits A1 (terlik matches, raw and normalized channels).
    A4 and HOMONYM are not built (module docstring).
  * m3_encoder 0.1.0 emits no content code; it publishes raw_score, which the
    decision layer turns into signals.decision.binary_offensive.
  * m2, m5, m6 are stubs; m4 emits nothing (C1-C5 wait for m3's C head).
"""
from __future__ import annotations

# "binary_offensive" is not a ContentCode: it is the decision layer's
# channel-level offensive score (decision/thresholds.yaml `binary_offensive`).
BINARY_OFFENSIVE = "binary_offensive"

CAPABILITIES: tuple[dict[str, str], ...] = (
    {"code": "A1", "module": "m1_lexicon"},
    {"code": BINARY_OFFENSIVE, "module": "m3_encoder"},
)
