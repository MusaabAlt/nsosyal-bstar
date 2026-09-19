# Threshold derivation protocol - binary_offensive (stage 1) for the rule-v4 artifact

Filled from `protocols/templates/threshold_derivation.md`. It applies, unchanged, the methodology of
`protocols/threshold_derivation_binary_offensive_stage1.md` (the baseline derivation, 2026-09-15) to
the artifact the runtime now deploys. Sections 1-4 were written BEFORE any rule-v4 score was
computed; section 5 records the run. Nothing was derived on test: the official test set was not
opened.

## 1. Scope
- Category: `binary_offensive`, stage 1 (ADR-006): one global threshold, no lexicon lookup at
  inference, raw channel only (no threshold is derived for `norm_score`; owner decision 2026-09-15).
- Score: `m3_encoder@0.3.0` `signals.raw_score` = p(OFF) of the binary head of
  **`m3-berturk-multihead-a-rule-v4-20260918-163728`**, weights sha256
  `dc7fe3062b33938ccbb78b632947bf254ad72e60104e163c64830bb95f0d0b76` (pinned in
  `modules/m3_encoder/module.py`; refused otherwise).
- The previous threshold **0.320188 belongs to `m3-berturk-pytorch-fp32-epoch1`** (the binary
  baseline) and is not reused: a threshold is valid only for the artifact it was derived on
  (artifacts/MANIFEST.md, m3 spec §5).
- thresholds.yaml artifact id before -> after: `thresholds-v0.1.0` -> `thresholds-v0.2.0` (status
  `derived`, covering `binary_offensive` only; every other number stays a placeholder).

## 2. Data (dev only)
- Dev split `diagnosis/data/splits/split_seed42.json` (sha256 `73a323b9…d7f2`, hashed, never read; dev
  fingerprint `034415af…`, 4,764 rows).
- Texts and gold (OFF / NOT): `diagnosis/results/01_baseline_berturk/dev_predictions.csv` (sha256
  `a2f5bddf…6346`), columns `row_id`, `text`, `gold` - the same rows the baseline derivation used.
- CAL / EVAL halves: `diagnosis/results/04_calibration/cal_eval_split.json` (sha256 `6d1e3ed7…f899`),
  2,382 rows each; EVAL = 460 OFF / 1,922 NOT. The threshold is fitted on CAL only; EVAL is read once.
- Not read: the official test set, the 500-row AI-assisted A-head reference and every annotation
  file (the binary head's gold is the corpus OFF / NOT label).
- Caveat recorded before the run: the rule-v4 trainer chose its checkpoint on DEV binary macro-F1
  (`docs/training/m3_rule_v4_handoff.md`), so dev is not untouched by this artifact; the baseline
  derivation had the same property (the study's epoch-1 `best.pt` was chosen on dev).

## 3. Objective (unchanged, decided before any rule-v4 score)
- Minimise Cost(r) = (FP + r·FN) / N on CAL with **r = 3**; candidate thresholds = the distinct
  observed CAL scores; decision rule `flag iff score > t`; ties toward the lower t.
- Methodology check before any rule-v4 number: the same code refitted on the study's own baseline
  scores must reproduce t = 0.320188 and EVAL tp 343 / fp 184 / fn 117 / tn 1,738; otherwise stop.
- Stability (C12-9): bootstrap of the CAL fit, n_boot 10,000, seed 42.
- Deployment condition (base protocol §3): the budgets hold with the new threshold -
  `clean_to_dirty_flip_rate` within 0.01 and the latency budgets as reported by `python -m
  eval.run_all`. If they do not hold, the number is recorded and NOT written to thresholds.yaml.

## 4. Procedure

    cd AI
    python -m eval.m3_rule_v4_binary_threshold --r 3 --n-boot 10000 --seed 42 \
        --out eval/results/m3_rule_v4_binary_threshold.json \
        --scores-cache eval/results/m3_rule_v4_dev_scores.json

Scores come from the deployed runtime itself (`EncoderModule()` with no override, raw channel =
the CSV text), exactly as the 2026-09-15 artifact-equivalence check scored the baseline. The script
refuses to run if the loaded artifact is not rule-v4 with the pinned weights.

## 5. Result (run 2026-09-19, `eval/results/m3_rule_v4_binary_threshold.json`, git-ignored)

- Artifact verified before the run: `heads.json` artifact_id `m3-berturk-multihead-a-rule-v4-20260918-163728`,
  `weights.pt` sha256 `dc7fe3062b33938ccbb78b632947bf254ad72e60104e163c64830bb95f0d0b76` (computed = listed =
  expected); every file of `sha256.txt` verified; heads trained: binary, A (B, C not trained); label sources =
  the rule-v4 digests `0bfbd731…04f2` / `50a94ba5…a0dd`. Loaded by `m3_encoder` 0.3.0 with no override.
- Methodology check: PASSED (baseline refit t = 0.320188, EVAL tp 343 / fp 184 / fn 117 / tn 1,738).
- Scoring: all 4,764 dev rows through the deployed runtime, 0 failures, 512.9 s on CPU.

| item | value |
|---|---|
| **threshold (CAL fit, r = 3, `score > t`)** | **0.445857971906662** |
| CAL (n 2,382) | tp 362 / fp 168 / fn 98 / tn 1,754; precision 0.6830188679245283, recall 0.7869565217391304, FPR 0.08740894901144641, cost 0.19395465994962216 |
| **EVAL (n 2,382, read once)** | **tp 327 / fp 140 / fn 133 / tn 1,782** |
| EVAL precision | 0.7002141327623126 |
| EVAL recall | 0.7108695652173913 |
| EVAL F1 (OFF) | 0.7055016181229773 |
| EVAL macro-F1 | 0.8171761413523408 |
| EVAL FPR | 0.07284079084287201 (140 / 1,922) |
| EVAL cost (FP + 3·FN) / N | 0.22628043660789252 |
| EVAL rows scoring exactly t | 0 |
| stability (CAL bootstrap, 10,000, seed 42) | t 95 % interval [0.2959098815917969, 0.49956172704696655], median 0.4542647898197174 |

EVAL confusion at t = 0.445857971906662: tp 327 / fp 140 / fn 133 / tn 1,782, 467 rows flagged.

**Tie row.** The threshold is itself a CAL score: dev row **46164** (CAL half, gold NOT) scores exactly
**0.445857971906662**. The rule of §3, `score > t`, does not flag it. When this run was made,
`decision/fusion.py` flagged `binary_offensive` at `score >= t`, so the runtime would have flagged it; that
difference is resolved by amendment §7.1 (the runtime now uses `score > t`).

**Recorded, not acted on.**
- The threshold is unstable under resampling: its bootstrap interval spans 0.30-0.50. No instability rule
  was pre-registered for this row (the base protocol has none), so the CAL fit stands; the width is
  reported, not hidden.
- Descriptive only, never used for selection: on EVAL, the old baseline threshold 0.320188 applied to
  rule-v4 scores gives tp 361 / fp 222 / fn 99 / tn 1,700, cost 0.21788413098236775 (lower than the fitted
  threshold's 0.22628043660789252), precision 0.6192109777015438, recall 0.7847826086956522. The protocol
  selects on CAL only; choosing on EVAL would be tuning on the evaluation half.
- dev is not untouched by this artifact (its checkpoint was chosen on dev binary macro-F1, §2).

**Deployment condition (§3): NOT MET - KNOWN DEMO LIMITATION / OWNER-ACCEPTED DEMO EXCEPTION (TEKNOFEST demo only, §7.2).**
`eval.harness.pipeline_budget_report`
(the budget step of `eval.run_all`), run with the new threshold in place, the deployed modules
(m3 0.3.0 rule-v4, m4 0.3.0, m5 1.0.0) and 20 latency repeats (`scripts/check.sh` allows `LATENCY_REPEATS`):

| budget | value | budget (placeholder) | result |
|---|---|---|---|
| `clean_to_dirty_flip_rate` | 0.02857142857142857 (1 / 35: `trap-030` "SİKKE") | 0.01 | **FAIL** |
| pipeline latency p95 | 191.62870000582188 ms (p50 107.265800004825 ms; 414 texts x 20 = 8,280 runs) | 250 ms | pass |
| module latency, clean fixtures | every module within its band (m3 fixture p95 51.747 ms vs 80 ms) | per module | pass |
| binary_offensive on traps (reported, not budgeted) | fires on trap-002, -008, -017, -032, -035 (5 / 35); none flipped by the channel | - | recorded |

The failing flip is a content code, not the binary threshold: m2 normalizes "SİKKE" (a coin) to "sikke" and
the rule-v4 **A head** scores the normalized channel 0.9526, so family A fires only with the channel on.
The flip-rate budget does not read `binary_offensive` at all, so no choice of this threshold changes it,
and reverting to 0.320188 would apply a threshold derived for another artifact.
**Status: owner-accepted for the TEKNOFEST demo version only (§7.2, 2026-09-19).** The budget still FAILS:
0.02857142857142857 > 0.01; it is not reported as passed. The "sikke" false positive is a known limitation of
the rule-v4 A head. Neither the model, the threshold nor the budget (a placeholder) was changed to make the
budget pass.

## 6. Sign-off
- Policy (actions): `binary_offensive.action: review` unchanged (placeholder policy).
- Numbers: derived by the procedure above on 2026-09-19.
- Deployment: the flip-rate budget failed (§5); owner-accepted as a DEMO exception only (§7.2, 2026-09-19).
  Not approved for production deployment.

## 7. Amendments after the run (§1-§5 method and numbers unchanged)

### 7.1 Comparator (2026-09-19, owner decision)

`decision/fusion.py::apply_binary_offensive` now flags `binary_offensive` iff `score > t`, the rule of §3 under
which the threshold was derived; it replaces the 2026-09-15 decision to keep `>=` there. No contract required
`>=` (checked: `contracts/` states no comparator). Content-code rows and guards keep `>=` (no derivation defines
them otherwise). Effect of the change: only a score exactly equal to 0.445857971906662 changes state; on the
frozen dev split that is row 46164 alone (CAL half), now not flagged, as the §5 CAL numbers already assumed.
No EVAL number changes (0 EVAL rows at t) and nothing in §3 or §5 was re-fitted.

### 7.2 Flip-rate budget: owner-accepted DEMO exception (2026-09-19, owner decision)

The project owner explicitly accepted the failed `clean_to_dirty_flip_rate` budget **for the TEKNOFEST demo
version only**:

| item | value |
|---|---|
| budget | `clean_to_dirty_flip_rate` = 1 / 35 = 0.02857142857142857 |
| placeholder limit | 0.01 |
| result | **FAIL** (the 1 % budget did NOT pass) |
| cause | known false positive "SİKKE" (`trap-030`): the rule-v4 A head scores its normalized form "sikke" 0.9526 |
| classification | **KNOWN DEMO LIMITATION / OWNER-ACCEPTED DEMO EXCEPTION** |
| scope | TEKNOFEST demo build only. NOT approval for production deployment |
| consequence | the rule-v4 threshold 0.445857971906662 may remain in `decision/thresholds.yaml` for the demo build, although §3 says a failed budget keeps the number out; this acceptance is the recorded exception to §3 for the demo |

Nothing else changes: model, threshold, budget value, detection rules, tests and runtime behaviour are as they
were before this decision. A production deployment needs the budget met or a separate owner decision.
