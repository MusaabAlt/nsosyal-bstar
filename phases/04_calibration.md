# Phase 04 — calibration and risk–coverage (selective prediction)

Opened 16 Aug 2026. Read-only with respect to models: **no retraining, no
forward pass.** Everything is computed from prediction dumps already on disk.

Evaluation is on the frozen dev split, fingerprint `034415af3a23b388`. The
official Çöltekin test set stays untouched; `load_coltekin_test()` is not called
anywhere in this phase.

## The question

Phase 01 measured a 33pp recall gap. Phase 02 explained it: the model detects
offensive **vocabulary** rather than offensive **acts**. Phase 03 tried to close
it by construction and failed. Phase 04 asks a different question — not "can the
model be made better", but **"does the model know when it is wrong?"** If it
does, a confidence threshold turns a known weakness into a routing rule, and the
weakness becomes a review-queue policy rather than an unhandled error.

## Inputs

| Source | Rows | Columns used |
|---|---|---|
| `results/01_baseline_berturk/dev_predictions.csv` | 4,764 | `row_id, gold, pred, confidence, slice` |
| `results/03_defense/run_1a1b_d/dev_predictions.csv` | 4,764 | same |

`confidence` is **P(OFF)**, not max-class probability. Decision confidence is
derived as `max(p, 1-p)`.

---

## Pre-registration

Written and committed **before any calibration number exists**. Not to be
revised after seeing results.

### C4-1 — the calibration split

Temperature is fit on one half of dev and evaluated on the other. Fitting and
evaluating a calibration parameter on the same rows reports the fit, not the
calibration.

Dev's 4,764 rows are split **stratified by gold label, seed 42, 50/50** using
`data_io.stratified_split` — the same sort-by-id-then-shuffle discipline as
every other split in this project, so it does not depend on file order. This
yields **CAL** (temperature fitting, threshold selection) and **EVAL** (every
reported number).

Both variants use the *same* CAL/EVAL partition, because their prediction files
cover identical rows; this keeps raw and `+1a+1b+D` comparable row-for-row.

### C4-2 — ECE definition, fixed before results

Confidence is `max(p, 1-p)` ∈ [0.5, 1.0]. **15 equal-width bins.**

```
ECE = Σ_b (n_b / N) · |accuracy_b − mean_confidence_b|
MCE = max_b |accuracy_b − mean_confidence_b|
```

ECE is known to be sensitive to bin count, so **10 and 20 bins are reported
alongside 15** as a sensitivity check. 15 is the headline; the others exist so a
reader can see whether the conclusion depends on the choice. Per-bin counts,
accuracies and mean confidences are emitted in full — that table *is* the
reliability diagram, in numbers rather than pixels.

### C4-3 — risk–coverage is invariant to temperature (prediction, then check)

Temperature scaling maps `p = σ(z)` to `σ(z/T)` with `T > 0`. This is strictly
monotonic in `z`, and decision confidence `max(p, 1-p) = σ(|z|/T)` is strictly
monotonic in `|z|`. **The ranking of rows by confidence is therefore unchanged,
so the risk–coverage curve is identical before and after temperature scaling.**

This is registered as a prediction and verified numerically as a self-check. It
matters for how the result is stated: calibration changes *what threshold value*
achieves a target error rate, not *which rows* get deferred. Any claim that
calibration "improved selective prediction" would be false, and this constraint
exists so that claim cannot be made by accident.

### C4-4 — operating points: threshold on CAL, metrics on EVAL

A threshold chosen at the target coverage quantile *of the rows it is then
scored on* is optimistic. So: the threshold for a target coverage is taken from
**CAL**, applied unchanged to **EVAL**, and all reported metrics and bootstrap
CIs come from EVAL. Realised EVAL coverage will differ slightly from the target
— that difference is reported rather than tuned away.

The descriptive risk–coverage *curve* (deliverable 2) is computed on full dev,
since no parameter is fit to produce it.

### C4-5 — stated limitation: the dumps are rounded

`confidence` is stored at 6 decimal places. Saturated rows (`0.000000` /
`1.000000`) cannot be inverted to a finite logit and are clipped to
`[5e-7, 1 − 5e-7]`, half the rounding grid. This **compresses the extreme logit
tail and biases the fitted temperature toward 1** — the most confident rows are
recorded as less confident than the model actually was.

The count of saturated rows is reported so the size of the effect is visible.
Removing this limitation requires the raw logits, which requires a forward pass,
which is outside this phase's "no retraining, work from the existing dumps"
scope. **Stated, not mitigated.**

### C4-6 — deferral analysis reported regardless of sign

For each operating point, report by slice: deferral rate, error rate among
deferred vs auto-resolved rows, and

```
capture lift = (share of all errors that land in the deferred set)
             / (share of all rows that land in the deferred set)
```

Lift > 1 means deferral is better than random at catching errors. The
`lexicon_free` share of deferrals is reported against the `lexicon_free` share
of dev (87.1%, 4,150/4,764) — a deferral set that is 87% `lexicon_free` is not
selective, it is just proportional, and the comparison is what distinguishes the
two. **A null is a result and gets reported as one.**

### C4-7 — the defense variant

The same full analysis is run for `+1a+1b+D`. Phase 03 showed it did not help
accuracy. Whether it helped *calibration* is a separate, unasked question, and a
null answer is reported as a null.

---

## Out of scope

| Not doing | Why |
|---|---|
| Retraining, or any forward pass | phase constraint: work from the existing dumps |
| Threshold tuning to maximise a metric | operating points are declared, not optimised |
| Platt scaling, isotonic, vector scaling | one calibration method, pre-registered; a method bake-off is a different phase |
| Touching the official test set | phase 05 only |
| Re-deriving slices | `slice` column is the frozen Day 1 tagging, carried in the dump |
