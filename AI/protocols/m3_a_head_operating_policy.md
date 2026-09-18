# M3 A-head operating policy — pre-registration **A-OP-1**

Owner decision, 2026-09-18. Recorded BEFORE any A-head threshold curve exists for this candidate:
no score of the A head has been examined across candidate thresholds, on the 500-row reference or
anywhere else, and none will be under this policy.

## 1. Scope

| | |
|---|---|
| candidate | `m3-berturk-multihead-a-rule-v3-20260918-074806` |
| weights.pt sha256 | `41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145` |
| trained at | `dba863233a354273415f68845f82e799a00dab70` (pseudo-label rule v3) |
| head | A (`A1` carrier, sigmoid, one output) |
| run record | `docs/training/runs/m3-berturk-multihead-a-rule-v3-20260918-074806.md` |

A-OP-1 applies to this candidate only. Any other artifact needs its own, versioned decision.

## 2. Decision

**The A-head operating threshold for this candidate is FIXED at 0.50.** It is a versioned policy
decision, not a threshold found by searching the evaluation reference. It is not derived,
optimised, tuned or validated on the 500-row AI-assisted, human-adjudicated dev reference, on the
pseudo-labels, or on the test set.

Reasons (owner):

1. The evaluation reference has only 39 positive rows; a threshold fitted on it would be decided
   by one or two rows and would be unstable.
2. 0.50 is already the reporting point of every A-head number recorded for this candidate.
3. Therefore the reported evaluation stays directly representative of the chosen operating point
   instead of becoming a tuned, optimistic result on the rows it was tuned on.

Because nothing is estimated, there is **no instability fallback**: there is no threshold whose
bootstrap spread could be too wide.

## 3. What the reported numbers mean under A-OP-1

The A-head evaluation recorded at export (`dev_eval.json` → `a`, reference kind
`ai-assisted-human-adjudicated`, 500 dev rows, reporting point 0.5) IS the operating-point
evaluation. It remains an evaluation against an AI-assisted, human-adjudicated reference, not a
human oracle, with 39 positives:

| tp | fp | fn | tn | precision [95% CI] | recall [95% CI] | F1 [95% CI] | FPR [95% CI] |
|---|---|---|---|---|---|---|---|
| 32 | 1 | 7 | 460 | 0.970 [0.889, 1.000] | 0.821 [0.690, 0.930] | 0.889 [0.800, 0.957] | 0.0022 [0.000, 0.0067] |

The recall interval is wide; A-OP-1 does not narrow it and makes no claim beyond it.

## 4. M3-A and M1-A1: complement, not replacement

- **M1 stays.** `m1_lexicon` remains the deterministic lexical detector. It is not removed,
  replaced or down-weighted. It emits every terlik match on the `A1` carrier with score 1.0.
- **M3 A complements M1.** The M3 A head may ADDITIONALLY emit `A1` where the learned model detects
  profanity that M1 misses (obfuscation M1 does not resolve, spellings outside the lexicon).
- **One carrier, the existing thresholds.** In the current architecture both publish on the
  existing `A1` carrier (`m1_lexicon@raw|normalized`, `m3_encoder@raw|normalized`). The decision
  layer recodes every family-A score to `A1` / `A2` / `A3` from m6's target (ADR-005,
  `decision/fusion.py::resolve_family_a`) and applies that code's `categories` threshold. All three
  are 0.50 in `decision/thresholds.yaml` today, so M3 A meets exactly 0.50 whatever the target.
  Changing any of those three values changes A-OP-1 and needs a new pre-registration.
- **A 0.50 threshold never suppresses an M1 hit**: M1's score is 1.0.
- `decision/thresholds.yaml` is NOT edited by this pre-registration. Its `A1` / `A2` / `A3`
  entries still carry the comment `PLACEHOLDER - derive on dev`; the comments are replaced by a
  citation of A-OP-1 in the commit that promotes this artifact, not before (promotion also needs
  the artifact-specific `binary_offensive` threshold, §6).

## 5. A known gap this policy does not close

The A head's target (rule v3) is narrow: an explicit obscene or profane lexical root. M1's `A1`
is broad: it fires on all 147 terlik roots, including the 130 roots rule v3 EXCLUDES (ordinary
insults such as `aptal`, `salak`, `gerizekalı`, and `kahpe`, `sürtük`, `kaltak`, `kancık`,
`kevaşe`). So, in production, the `A1` / `A2` / `A3` "küfür" code is also given to ordinary
insults. The architecture has no separate generic-insult signal today: `B1` ("degradation") is the
semantic home, but the B head is untrained (`BLOCKED_BY_DATA`) and M1 emits no B code. The M3
binary head (`binary_offensive`) scores offensiveness in general. This is recorded as an open
architecture question for the owner; A-OP-1 changes no semantics.

## 6. What A-OP-1 does not do

- It does not promote the artifact, activate it, or change `decision/thresholds.yaml`.
- It does not derive the artifact-specific `binary_offensive` threshold: that is derived
  separately, on the frozen dev split's CAL half, under the pre-registered r = 3 cost rule
  (`protocols/threshold_derivation_binary_offensive_stage1.md`).
- It does not touch the test set.

## 7. What would reopen it

A new evaluation reference with enough positives to support a derived operating point, a new
artifact, or an owner decision to adopt a derived policy (for example a minimum-precision or an
FPR-cap rule) — each as a new, versioned pre-registration (A-OP-2), written before any curve is
inspected.
