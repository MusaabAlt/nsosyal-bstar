# ADR-005 — Family A is assigned from the target; NON_HUMAN_TARGET moves to m1

- **Status:** accepted
- **Date:** 2026-09-14
- **Decided by:** project owner (design gaps found in the handover-readiness audit)
- **Scope:** `modules/m1_lexicon/spec.md`, `modules/m3_encoder/spec.md`, `modules/m6_target/spec.md`, `decision/fusion.py`, `decision/thresholds.yaml`, `modules/registry.py`

## Context

`A1`, `A2` and `A3` differ only by target: untargeted, individual, group. m3's
spec already said m3 cannot tell them apart, and m6's spec said its target
"upgrades A1 to A2 or A3" - but no code combined the two. m1 and m3 were each
told to emit per-code A scores they had no way to separate.

Separately, m6 was the producer of `NON_HUMAN_TARGET`, configured to suppress
`A2, B1, B2`. Under ADR-001 a guard only suppresses scores from its own module,
and m6 produces only `B4`: the guard could never suppress anything.

## Decision

1. **m3 emits a single "profanity present" score, not A1/A2/A3.** The decision
   layer assigns the final code by combining it with m6's target: no target ->
   `A1`, individual -> `A2`, group -> `A3`. `A4` stays with m1: it is
   concept-based, not target-based.
2. **`NON_HUMAN_TARGET` moves to m1.** m1 produces the A-family scores, so under
   ADR-001 scoping it can suppress them. m6 keeps producing the target; m1 reads
   it. No contract change.

## How it is applied

- **Carrier code.** `ContentScore.code` must be a `ContentCode` and the frozen
  contract has no generic "family A" code, so the "profanity present" score is
  emitted on `A1`, which carries it until the decision layer assigns the final
  code. Modules never emit `A2`/`A3`; if one does, the decision layer recodes it
  from the target anyway and notes it.
- **Where.** `decision/fusion.py::resolve_family_a` runs right after the reset
  and before any threshold, so `A2`/`A3` thresholds and actions apply to the
  assigned code. `fast_path_hit` uses the same assignment. The record is written
  to `signals.decision.family_a` (target seen, confidence, target used, code).
- **Config.** `thresholds.yaml` `family_a.by_target` maps every `TargetType`;
  `family_a.target_min_confidence` is the confidence below which a target counts
  as none (a placeholder, like every other threshold - a module never thresholds).
- **m1 reads m6.** m6 publishes `signals["target_type"]` and
  `signals["target_confidence"]`. m1 raises `NON_HUMAN_TARGET` on each of its own
  family-A matches when the published type is `non_human`, with score = m6's
  target confidence and span = that match's span, so ADR-001 span overlap holds.
  `modules/registry.py` now runs m6 before m1, which m1 needs to read m6's
  signals; m6 reads only `ctx.text`, so the move costs nothing.
- **Guard config.** `NON_HUMAN_TARGET` suppresses `[A1, A2, A3]` - the codes m1
  produces that are target-assigned. `A4` is not listed.

## Not decided by the owner (placeholders, flagged)

- `family_a.by_target.non_human` is set to `A1`, so that m1's `NON_HUMAN_TARGET`
  guard can suppress it, matching the annotation guideline row "insult at a film /
  the weather -> CLEAN + NON_HUMAN_TARGET". The owner mapped none, individual and
  group only.
- `family_a.target_min_confidence` has a placeholder value.

## Consequences

- m6 no longer provides `guards`; its skipped guard test became a target test,
  and an equivalent skipped test moved to m1.
- Profanity detected only by m3 (no m1 match) at a non-human target is not
  suppressed: m1's guard cannot suppress m3's scores under ADR-001. It is decided
  as `by_target.non_human`. The same holds for `B1`/`B2` at a non-human target,
  which the old m6 configuration listed but could never actually suppress.
- The contract example in `contracts/fixtures/` changes (registry order,
  `signals.decision.family_a`, config hash) and needs an explicit instruction to
  regenerate.

## Amendment — non-human mapping confirmed (2026-09-14)

- **Decided by:** project owner

`family_a.by_target.non_human` stays `A1`: confirmed by the owner, no longer a
placeholder. `family_a.target_min_confidence` stays a marked placeholder, to be
derived on dev like every other threshold.

Left open for the module owners (recorded in `docs/HANDOVER.md`): m3 scores at a
non-human target are not suppressed, because m1's guard cannot suppress another
module's scores under ADR-001.
