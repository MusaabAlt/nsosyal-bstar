"""m4_implicit - implicit abuse (C1-C5). Stage 1 is in force; C1-C5 are not built.

NOT a stub (owner decision, ADR-006 amendment). m4 owns the stage-1 slice repair: ONE global
cost-derived threshold on m3's raw binary offensive score - the `binary_offensive` row of
decision/thresholds.yaml (spec.md §4, ADR-006), derived for the deployed m3 artifact (rule-v4) in
protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md. The decision layer applies that
threshold; m4 never does (CLAUDE.md rule 4). At inference m4 reads exactly what its contract
names (spec.md §5), `ctx.signals["m3_encoder"]` - raw_score, norm_score, artifact - and publishes
what stage 1 runs on, so every result shows m4's part of the decision (ADR-006 amendment,
2026-09-19):

Catches (signals only, no content scores):
  * `stage`: the stage in force, 1. Stage 1b was measured and not adopted
    (protocols/m4_stage1b_protocol.md); stage 2 is blocked on its precision budget and its
    labelled slice (docs/training/m4_stage2.md).
  * `stage1_input` / `stage1_input_present`: the m3 signal the stage-1 row thresholds, and whether
    m3 published a finite value for it on this post. Absent -> a note: stage 1 had no input.
  * `m3_artifact` / `stage1_derived_for` / `stage1_artifact_match`: whether the m3 artifact that
    produced the score is the one the stage-1 threshold was derived on. A mismatch is noted: the
    decision layer would then apply a threshold that was never derived for that artifact.
  * `stage1_protocol`: the derivation record of that threshold (threshold provenance; the number
    itself is the decision layer's, in signals.decision.binary_offensive).
  * `norm_minus_raw`: norm_score - raw_score, the disagreement between the two channels (spec.md
    §4: the first of stage 2's two mining signals). Positive when the de-obfuscated channel scores
    the post as more offensive than the original text does; None without a norm_score.
  * one plain note, NOTE_C_FAMILY: C1-C5 are not covered. They come from m3's C head (ADR-006),
    which is not trained: no C-labelled slice exists (docs/blockers/m3_head_labels.md).

Deliberately does NOT: score content (C1-C5 are m3's), read m1 (stage 1b's lexicon condition is
not in force), apply or compare against any threshold - including whether a channel gap is
"large" - or decide anything.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput

# Plain information, not a failure: m4 is not a stub and this note degrades nothing.
NOTE_C_FAMILY = "C1–C5 not implemented yet"

M3 = ModuleName.M3_ENCODER.value
STAGE = 1
# What the stage-1 row reads (decision/thresholds.yaml binary_offensive.channels.raw) and the
# artifact it was derived on (its derived_on); tests/test_signal_interfaces.py pins both to the config.
STAGE1_INPUT = f"{M3}.raw_score"
STAGE1_DERIVED_FOR = "m3-berturk-multihead-a-rule-v4-20260918-163728"
STAGE1_PROTOCOL = "protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md"


def _score(payload: Mapping[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


class ImplicitModule(BaseModule):
    name = ModuleName.M4_IMPLICIT
    version = "0.3.0"
    # Kept as declared (owner decision): m4 emits no content scores today (ADR-006).
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # implicit abuse is scored on the whole post, not a substring.
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        published = ctx.signals.get(M3)
        m3 = published if isinstance(published, Mapping) else {}
        raw, norm = _score(m3, "raw_score"), _score(m3, "norm_score")
        artifact = m3.get("artifact") if isinstance(m3.get("artifact"), str) else None
        match = None if artifact is None else artifact == STAGE1_DERIVED_FOR
        notes = [NOTE_C_FAMILY]
        if raw is None:
            notes.append(f"stage 1 had no input: {M3} published no raw_score")
        if match is False:
            notes.append(f"stage 1: binary_offensive was derived for {STAGE1_DERIVED_FOR}; this score comes "
                         f"from {artifact}, for which no binary_offensive threshold was derived")
        signals = {
            "stage": STAGE,
            "stage1_input": STAGE1_INPUT,
            "stage1_input_present": raw is not None,
            "m3_artifact": artifact,
            "stage1_derived_for": STAGE1_DERIVED_FOR,
            "stage1_protocol": STAGE1_PROTOCOL,
            "stage1_artifact_match": match,
            "norm_minus_raw": None if raw is None or norm is None else norm - raw,
        }
        return ModuleOutput(signals=signals, notes=notes)
