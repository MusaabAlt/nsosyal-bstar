# Threshold derivation protocol - binary_offensive (stage 1)

Filled from `protocols/templates/threshold_derivation.md`. Output: the reviewed change
to `decision/thresholds.yaml` and the MANIFEST.md entries in the same commit. Nothing
was derived on test: the official test set was not opened.

## 1. Scope
- Categories / guards: `binary_offensive`, stage 1 (ADR-006): one global threshold, no
  lexicon lookup at inference. The study calls this system **S1b**; in this repository
  "stage 1b" means the lexicon-conditioned variant, which is NOT what this is.
- Modules whose scores are thresholded (name@version): `m3_encoder@0.1.0`,
  `signals.raw_score` only, artifact `m3-berturk-pytorch-fp32-epoch1`
  (sha256 `43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca`).
  No threshold on `norm_score`: none was derived (owner decision, 2026-09-15).
- thresholds.yaml artifact id before -> after: `thresholds-v0.0.0-placeholder` ->
  `thresholds-v0.1.0` (status `derived`, covering `binary_offensive` only).

## 2. Data
- Dev split id and hash: `diagnosis/data/splits/split_seed42.json`, sha256
  `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2`, dev fingerprint
  `034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4` (4,764 rows).
- Calibration fold: `diagnosis/results/04_calibration/cal_eval_split.json` (sha256
  `6d1e3ed7…f899`), CAL half n = 2,382 (threshold fitted), EVAL half n = 2,382 (reported).
- Items per class, EVAL half: 460 OFF / 1,922 NOT.
- Scores: epoch-1 baseline p(OFF) on raw text, `diagnosis/results/01_baseline_berturk/dev_predictions.csv`
  (sha256 `a2f5bddf…6346`, confidences rounded to 6 decimals).

## 3. Objective (decided BEFORE looking at curves)
- Operating point rule (pre-registered, `diagnosis/phases/12_threshold_policy.md`, C12-3/C12-4):
  minimise Cost(r) = (FP + r·FN) / N on CAL, with **r = 3** (a false negative costs three
  false positives), candidate thresholds = the distinct observed CAL scores, decision rule
  `flag iff score > t`, ties broken toward the lower t. r = 3 is policy, adopted by the
  project owner on 2026-09-15.
- Budgets that must hold: `clean_to_dirty_flip_rate` 0.0 (within 0.01), pipeline
  `latency_p95_ms` and `module_latency_p95_ms` as reported by `scripts/check.sh` in the
  commit that adopts this threshold.

## 4. Procedure
- Score source: study phase 12, `diagnosis/results/12_threshold_policy/metrics.json`
  (run `12_threshold_policy`, 2026-08-19, git `2b4391bf`), `thresholds_fitted_on_CAL.S1b`.
- Artifact equivalence check (2026-09-15, this repository): `m3_encoder` scored all 4,764
  frozen dev rows through `EncoderModule.process` (CPU, torch 2.11.0+cpu, transformers
  5.15.0). Against `dev_predictions.csv`: confusion at 0.5 = tn 3631 / fp 213 / fn 285 /
  tp 635 (identical), **0 label flips**, max |Δp| = 2.25e-06 (row 34191; includes the CSV's
  6-decimal rounding), 0 module errors, 2 rows truncated at 128 tokens.
- Sweep grid: every distinct CAL score (C12-3). Bootstrap for threshold stability
  (C12-9): n_boot 10,000, seed 42.

## 5. Result
| code | old | new | recall [CI] | precision [CI] | FPR [CI] | traps |
|---|---|---|---|---|---|---|
| binary_offensive (raw) | 0.50 placeholder | **0.320188** | OFF-recall 0.7457 (EVAL, r = 3; descriptive, no CI pre-registered) | 0.6509 (EVAL) | 184 / 1,922 = 0.0957 (EVAL) | 0 regressions (check.sh) |

EVAL confusion at t = 0.320188: tp 343 / fp 184 / fn 117 / tn 1,738, cost 0.2246, 527 rows
flagged (`metrics.json#primary.S1b`). Verdict of the pre-registered comparison:
`SINGLE-THRESHOLD-SUFFICIENT` (the slice-conditional S2 was not better).

**Tie row.** The threshold is itself an observed CAL score: dev row **29308** (CAL half,
gold NOT, study pred NOT, slice `lexicon_free`) has confidence `0.320188` in the CSV. The
study's rule `score > t` does not flag it; `decision/fusion.py` flags at `score >= t`, so on
the rounded value the two rules disagree on this one row. At full precision m3 scores it
**0.32018762826919556**, below 0.320188, so it is not flagged under either rule at runtime.
`fusion.py` is unchanged (owner decision, 2026-09-15). Any other text scoring exactly
0.320188 would be flagged by fusion and not by the study rule.

## 6. Sign-off
- Policy (actions) reviewed by: Musaab — `action: review` unchanged (placeholder policy).
- Numbers reviewed by: Musaab — conditions adopted as stated (CAL half, r = 3, epoch-1
  FP32 on raw text, raw channel only).
- Date: 2026-09-15
