# ADR-006 — C1–C5 are a third m3 head; m4 owns thresholds and the slice repair; stage 1 is one global threshold

- **Status:** accepted
- **Date:** 2026-09-14
- **Decided by:** project owner (design gaps found in the handover-readiness audit)
- **Scope:** `modules/m3_encoder/spec.md`, `modules/m4_implicit/spec.md`, `modules/m1_lexicon/spec.md`, `decision/thresholds.yaml`

## Context

1. m4's spec made it write `C1`–`C5` content scores but named no model that
   produces them. Its contract said it read "M3's published scores" from
   `ctx.signals["m3_encoder"]`, while m3 publishes only `raw_score`, `norm_score`
   and `artifact` there.
2. m4's spec said stage 1 is "a single adapted parameter, no lexicon lookup at
   inference time", while `thresholds.yaml` already carried the signal-conditioned
   `threshold_when: m1_lexicon.lexicon_hit` on `binary_offensive`. The measured
   result (lexicon-free recall 0.5180 -> 0.6367) came from the first design.

## Decision

1. **C1–C5 come from a third head on m3's encoder.** m4 owns the thresholds and
   the slice repair, not a model. Reason: a fourth standalone model means a fourth
   encoder pass on CPU.
2. **m4 reads what m3 actually publishes, nothing more:** `raw_score`,
   `norm_score`, `artifact`.
3. **Stage 1 keeps the single global cost-derived threshold, exactly as
   measured.** The signal-conditioned `threshold_when` becomes **stage 1b**: a
   variant measured against stage 1 at equal coverage before it replaces it.

## How it is applied

- m3 spec: three heads; `C1`–`C5` in m3's content contract.
- m4 spec: no content scores; deliverables are the `C1`–`C5` and
  `binary_offensive` rows and the slice repair; stage 1b described; the
  open-question note removed. Stage 2 retrains m3's encoder, so its artifact is an
  m3 artifact under m3's artifact discipline.
- `thresholds.yaml`: `binary_offensive` has one scalar threshold (stage 1);
  `threshold_when` removed from it, with a comment describing stage 1b.
- m1 spec: `lexicon_hit` defines the slice split and is what stage 1b resolves
  against.

## Consequences, open for the owner

- **m4's runtime role.** m4 is still a registered pipeline module declared as a
  stub, and every stub degrades the result (fail closed), so no verdict can be
  clean while m4 is a stub. With no scores to emit, m4 would either become a
  non-stub module that emits nothing, or leave `PIPELINE_ORDER`. Its `provides`
  still says `content` because every module's unit tests require a non-empty
  `provides`.
- **m4 measurement.** The harness predicts from content, form, guards and target;
  it does not read `binary_offensive`. m4's slice repair cannot be scored by
  `python -m modules.m4_implicit.eval` as it stands.
- **Artifact entanglement.** Stage 2 retrains m3's encoder, which now also
  carries families A and B. Per m3's artifact discipline, a new m3 artifact forces
  re-derivation of every m3 threshold - the coupling ADR-003 removed for D1.

## Amendment — m4 is a non-stub module that emits nothing yet (2026-09-14)

- **Decided by:** project owner

**Decision.** m4 stays in `PIPELINE_ORDER` as a non-stub module that returns an
empty `ModuleOutput`. `provides` stays `content`.

**Reason.** A stub there makes every verdict `review`, which hides the fail-closed
behaviour the project wants to demonstrate: the verdict should be `review`
because a module that should have scored is unfinished, not because m4, which has
nothing to score, is labelled a stub.

**Consequences.** m4 no longer appears in `signals.pipeline.degraded`. m1, m2, m3,
m5 and m6 are still stubs, so verdicts stay `review` until they are implemented.
Left open for the module owners (recorded in `docs/HANDOVER.md`): stage 2
re-coupling m3's thresholds, and m4's slice repair not being measurable by its own
eval.

## Amendment — m4 publishes what stage 1 runs on (2026-09-19)

- **Decided by:** project owner (requested 2026-09-19: m4 must read its contract inputs and publish
  a real runtime signal; this design approved the same day)

**Change.** `m4_implicit` 0.1.0 -> 0.2.0. m4 now reads what its contract names (m4 spec §5,
decision 2 above) - `ctx.signals["m3_encoder"]` `raw_score`, `norm_score`, `artifact` - and
publishes, in its own signals:

| signal | value |
|---|---|
| `stage` | `1`, the stage in force (1b measured and not adopted; 2 blocked) |
| `stage1_input` | `m3_encoder.raw_score`, what the `binary_offensive` row thresholds |
| `stage1_input_present` | whether m3 published a finite `raw_score` on this post |
| `m3_artifact` | the artifact id m3 published, or null |
| `stage1_derived_for` | `m3-berturk-pytorch-fp32-epoch1`, the artifact the stage-1 threshold was derived on |
| `stage1_artifact_match` | whether the two ids agree (null without an artifact) |
| `norm_minus_raw` | `norm_score - raw_score` (null without both): the channel disagreement of spec §4 |

Notes, beside the unchanged `C1–C5 not implemented yet`: "stage 1 had no input" when m3
published no usable `raw_score`, and a named mismatch note when the artifact is not the one the
threshold was derived for (a multi-head artifact installed through `NSOSYAL_M3_ARTIFACT` today).

**What does not change.** m4 emits no content score, guard or target and still thresholds
nothing (CLAUDE.md rule 4): whether a gap is large, or a score high, is not m4's to say. No
decision-layer row reads the new signals; `binary_offensive` still reads `m3_encoder.raw_score`
directly, with the same threshold and action. A mismatch is a note, not a degradation: whether
an underived threshold should degrade the result is left to the owner. `tests/test_signal_interfaces.py`
pins `stage1_input` and `stage1_derived_for` to `decision/thresholds.yaml` and `artifacts/MANIFEST.md`.

**Consequence.** m4's version enters `artifact_hash`, so the frozen contract example is stale until
the owner instructs `python -m pipeline.contract_example --write` (ADR-003 amendments).

## Amendment — stage 1 is tied to the rule-v4 artifact (2026-09-19, same day)

- **Decided by:** project owner (the 0.2.0 amendment above approved; rule-v4 made the deployed m3
  artifact and its binary threshold derived in the same task)

**Change.** `m4_implicit` 0.2.0 -> 0.3.0. `stage1_derived_for` is now
`m3-berturk-multihead-a-rule-v4-20260918-163728`, the artifact the runtime deploys and the one the
`binary_offensive` threshold in `decision/thresholds.yaml` was derived on
(`protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md`). A new signal,
`stage1_protocol`, names that derivation record: m4 publishes the threshold's provenance, never the
number (the decision layer publishes it in `signals.decision.binary_offensive`). The old threshold
0.320188 belongs to `m3-berturk-pytorch-fp32-epoch1`; selecting that baseline explicitly now makes m4
note the mismatch. C1–C5 remain not trained.

## Amendment — the stage-1 comparator follows its derivation (2026-09-19)

- **Decided by:** project owner

`decision/fusion.py::apply_binary_offensive` flags `binary_offensive` iff `score > t`, the rule both stage-1
derivations were fitted with (`protocols/threshold_derivation_binary_offensive_stage1.md` and its rule-v4
counterpart, study rule C12-3). It replaces the 2026-09-15 decision to keep `>=` for this row. Content-code rows
and guards keep `>=`. With the rule-v4 threshold the only affected frozen-dev row is CAL row 46164, which scores
exactly t and is no longer flagged.
