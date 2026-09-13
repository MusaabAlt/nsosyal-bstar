# Threshold derivation protocol - <category or guard>

Fill one copy per derivation. Output: a reviewed change to
`decision/thresholds.yaml` + a MANIFEST.md entry. Never derive on test.

## 1. Scope
- Categories / guards: 
- Modules whose scores are thresholded (name@version): 
- thresholds.yaml artifact id before -> after: 

## 2. Data
- Dev split id and hash: 
- Items per class (positives / negatives): 
- Calibration fold (if separate from selection fold): 

## 3. Objective (decided BEFORE looking at curves)
- Operating point rule (e.g. max recall s.t. FPR <= x, or precision CI lower bound >= y): 
- Budgets that must hold: clean_to_dirty_flip_rate, fpr_increase_on_clean, latency_p95_ms

## 4. Procedure
- Score source: `eval/results/<module>.json` from commit: 
- Sweep grid: 
- Bootstrap: n_boot, seed, CI level: 

## 5. Result
| code | old | new | recall [CI] | precision [CI] | FPR [CI] | traps |
|---|---|---|---|---|---|---|
| | | | | | | |

## 6. Sign-off
- Policy (actions) reviewed by: 
- Numbers reviewed by: 
- Date: 
