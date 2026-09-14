# Experiment protocol - <module> - <short name>

Write sections 1-4 BEFORE running anything.

## 1. Hypothesis
- Change: 
- Expected effect (metric, direction, size): 

## 2. Setup
- Module version / commit: 
- Artifacts (MANIFEST ids): 
- Dev fixture + hash: 
- Baseline result file: `eval/results/<module>.json` @ commit 

## 3. Success criteria
- Primary metric and minimum improvement (CI must exclude 0): 
- Guard rails: zero trap regressions; latency p95 within budget; FPR increase on clean <= budget

## 4. Ablations planned
- 

## 5. Results
| run | recall [CI] | precision [CI] | FPR [CI] | traps | p95 ms |
|---|---|---|---|---|---|
| baseline | | | | | |
| change | | | | | |

## 6. Decision
- Accept / reject, and why: 
