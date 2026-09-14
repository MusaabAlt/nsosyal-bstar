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
