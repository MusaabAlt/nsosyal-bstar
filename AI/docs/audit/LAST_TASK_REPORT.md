# NSosyal backend: final deployment report for the TEKNOFEST demo (2026-09-19)

Committed version, written just before the commit. The version written after the push adds the commit SHA
and the push verification; it lives in the working tree only, because a commit cannot contain its own SHA.

## 1. Owner-accepted DEMO exception (exact scope)

**KNOWN DEMO LIMITATION / OWNER-ACCEPTED DEMO EXCEPTION**, accepted by the project owner on 2026-09-19 for the
**TEKNOFEST demo version only**. This is **not** approval for production deployment.

| item | value |
|---|---|
| budget | `clean_to_dirty_flip_rate` = 1 / 35 = 0.02857142857142857 |
| placeholder limit | 0.01 |
| result | **FAIL**: the 1 % budget did not pass |
| known false positive | "SİKKE" (`trap-030`): the Rule-v4 A head scores its normalized form "sikke" 0.9526 |
| threshold | the Rule-v4 threshold 0.445857971906662 stays in `decision/thresholds.yaml` for the demo build |

Recorded in `protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md` §7.2, in the `thresholds.yaml`
comment and in `docs/audit/PROJECT_COMPLETION_STATUS.md`. Model, thresholds, detection rules, tests and
runtime behaviour were not changed by this decision.

## 2. Final M0–M6 status

| module | version | runtime | secondary |
|---|---|---|---|
| M0 | 0.2.0 | ACTIVE | — |
| M1 | 0.3.0 | ACTIVE | A4 not built |
| M2 | 0.1.2 | ACTIVE | advanced transforms PARTIAL |
| M3 | 0.3.0 | ACTIVE — Rule-v4 binary + A | B and C heads NOT TRAINED |
| M4 | 0.3.0 | ACTIVE — Stage 1 (Rule-v4 threshold, `score > t`) | C1–C5 NOT TRAINED |
| M5 | 1.0.0 | ACTIVE — Stage 1 deterministic | not a trained model, not benchmarked |
| M6 | 0.1.0 | ACTIVE | known v1 bugs |

## 3–5. Tests, scenarios, contract

- **Full suite:** 492 tests: 492 passed, 0 failed, 0 skipped.
- **Scenarios:** 38 scenarios: 35 PASS, 0 FAIL, 3 FAIL (KNOWN_LIMITATION), 0 BLOCKED.
- **Contract:** `pipeline.contract_example --check` exit 0.

## 6. Rule-v4 artifact

- **ID:** `m3-berturk-multihead-a-rule-v4-20260918-163728`.
- **Weights SHA256:** `dc7fe3062b33938ccbb78b632947bf254ad72e60104e163c64830bb95f0d0b76`, verified. The runtime pins it.
- **In git:** no. It is git-ignored and not in GitHub (see the developer instructions in the post-push report).
