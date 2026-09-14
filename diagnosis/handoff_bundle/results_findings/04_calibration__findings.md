# Phase 04 — calibration and risk–coverage

Frozen dev split, fingerprint `034415af3a23b388`, 4,764 rows. No retraining and
no forward pass: everything below is computed from the phase 01/03 prediction
dumps. Official Çöltekin test set untouched.

Protocol pre-registered in `phases/04_calibration.md` (C4-1…C4-8) and committed
as `ab225ad`, before any number here existed. CAL/EVAL = 2,382/2,382, stratified
by gold label, seed 42. Temperature fit on CAL; every reported metric from EVAL,
except the descriptive risk–coverage curve, which fits no parameter and is
computed on full dev.

The phase 01 dump was verified **identical** to the phase 03 `run_raw` dump
before anything was measured.

---

## Headline

**The raw model is already well calibrated (T = 0.9948, ECE 0.0205), so
temperature scaling buys almost nothing — and the defense variant is badly
miscalibrated (T = 1.9732, ECE 0.0786), which is a real cost phase 03 could not
see.** Selective prediction works well on both, but **not** for the reason the
phase 02 diagnosis suggested: deferral is strongly error-selective and almost
perfectly slice-blind.

---

## 1. Calibration

| | raw | +1a+1b+D |
|---|---:|---:|
| fitted temperature (CAL) | **0.9948** | **1.9732** |
| NLL before → after | 0.2616 → 0.2616 | 0.3831 → 0.2914 |
| direction | overconfident | overconfident |
| signed gap (acc − conf) | −0.0091 | −0.0739 |
| ECE, 10 bins, before → after | 0.0162 → 0.0154 | 0.0773 → 0.0296 |
| **ECE, 15 bins, before → after** | **0.0205 → 0.0191** | **0.0786 → 0.0270** |
| ECE, 20 bins, before → after | 0.0206 → 0.0211 | 0.0784 → 0.0313 |
| MCE, 15 bins, before → after | 0.1184 → 0.1230 | 0.3487 → 0.2056 |
| saturated (6dp) rows | 0 / 4,764 | 0 / 4,764 |

**Raw BERTurk needs no calibration.** T = 0.9948 is within half a percent of the
identity, the NLL does not move to four decimals, and ECE falls only 0.0205 →
0.0191. At 20 bins it rises slightly (0.0206 → 0.0211) — which is what a no-op
transform plus bin noise looks like, and is reported rather than hidden behind
the 15-bin headline. The model is *marginally* overconfident (signed gap
−0.0091); the miscalibration is real but operationally negligible.

**The defense variant is a different story.** T = 1.9732 says its logits need to
be roughly halved. Its ECE is **3.8× the raw model's** (0.0786 vs 0.0205). The
reliability table shows exactly where: it puts **1,958 of 2,382 EVAL rows in the
top confidence bin** at mean confidence 0.9943 while being right only 93.72% of
the time, and its worst bin is off by 0.3487.

Temperature scaling repairs most of that (0.0786 → 0.0270, MCE 0.3487 → 0.2056)
but does not reach raw's uncalibrated 0.0205.

**This is a cost of the defense that phase 03 could not have detected.** Phase 03
measured accuracy, which barely moved (macro-F1 0.8271 → 0.8202). Confidence
quality moved a great deal, in the wrong direction. The augmentation made the
model *more certain* without making it more correct — consistent with training
on 1,146 upsampled `[MASK]` rows and ~2,000 templated fragments, which add
repetition rather than evidence.

**Answer to deliverable 5: no, the defense did not help calibration. It hurt it,
substantially, and temperature scaling only partly undoes the damage.**

---

## 2. Risk–coverage

Verified numerically that the curve is **invariant to temperature** (max abs
difference `0.00e+00`, C4-3). Calibration changes what threshold *value* buys a
given coverage; it cannot change *which* rows are deferred, because temperature
is monotonic. No claim that calibration improved selective prediction is
available, and none is made.

**raw BERTurk** (full dev)

| coverage | n auto | deferred | macro-F1 | error | OFF-recall | threshold |
|---:|---:|---:|---:|---:|---:|---:|
| 100.0% | 4,764 | 0 | 0.8271 | 10.45% | 0.6902 | 0.5016 |
| 95.0% | 4,526 | 238 | 0.8467 | 8.79% | 0.7010 | 0.5930 |
| 90.0% | 4,288 | 476 | 0.8621 | 7.39% | 0.7143 | 0.6720 |
| 85.0% | 4,049 | 715 | 0.8714 | 6.45% | 0.7239 | 0.7528 |
| 80.0% | 3,811 | 953 | 0.8927 | 5.12% | 0.7584 | 0.8111 |
| 75.0% | 3,573 | 1,191 | 0.9070 | 4.09% | 0.7721 | 0.8552 |
| 70.0% | 3,335 | 1,429 | 0.9222 | 3.21% | 0.8058 | 0.8892 |
| 65.0% | 3,097 | 1,667 | 0.9252 | 2.97% | 0.8108 | 0.9168 |
| 60.0% | 2,858 | 1,906 | 0.9354 | 2.52% | 0.8343 | 0.9358 |
| 55.0% | 2,620 | 2,144 | 0.9438 | 2.18% | 0.8477 | 0.9494 |
| 50.0% | 2,382 | 2,382 | 0.9497 | 1.93% | 0.8630 | 0.9602 |

**+1a+1b+D** (full dev)

| coverage | macro-F1 | error | OFF-recall |
|---:|---:|---:|---:|
| 100.0% | 0.8202 | 11.04% | 0.6946 |
| 95.0% | 0.8341 | 9.59% | 0.7067 |
| 90.0% | 0.8539 | 7.91% | 0.7291 |
| 85.0% | 0.8684 | 6.74% | 0.7536 |
| 80.0% | 0.8836 | 5.83% | 0.7791 |
| 75.0% | 0.8952 | 5.09% | 0.7950 |
| 70.0% | 0.9038 | 4.62% | 0.8067 |
| 65.0% | 0.9197 | 3.84% | 0.8394 |
| 60.0% | 0.9261 | 3.53% | 0.8586 |
| 55.0% | 0.9324 | 3.24% | 0.8660 |
| 50.0% | 0.9379 | 3.02% | 0.8779 |

The raw model dominates the defense variant at **every** coverage level on both
macro-F1 and error rate. Deferring does not rescue the defense.

---

## 3. Declared operating points

Thresholds selected on CAL, metrics and 1,000-resample bootstrap CIs from EVAL
(C4-4). Both points fixed by rule in advance (C4-8), not read off the curve.

### raw BERTurk — the system we would ship

> **High-automation.** At **91.2%** automatic coverage the system holds
> **0.8504** macro-F1 / **7.92%** error, deferring **8.8%** to human review.

95% CI: coverage [0.9005, 0.9236], macro-F1 [0.8287, 0.8721], error rate
[0.0681, 0.0899]. Threshold 0.6632.

> **High-precision.** At **81.6%** automatic coverage the system holds
> **0.8756** macro-F1 / **5.81%** error, deferring **18.4%** to human review.

95% CI: coverage [0.8010, 0.8329], macro-F1 [0.8522, 0.8963], error rate
[0.0481, 0.0684]. Threshold 0.8009. Selected as the largest grid coverage whose
**CAL** error rate is ≤ 5.0%; realised EVAL error is 5.81%, i.e. the target is
met on the selection half and missed by 0.8pp on the held-out half — reported,
not retuned.

### +1a+1b+D, for comparison

> **High-automation.** At **91.4%** automatic coverage it holds **0.8488**
> macro-F1 / **8.08%** error, deferring **8.6%** to human review.
> (CI: macro-F1 [0.8280, 0.8684], error [0.0698, 0.0926].)

> **High-precision.** At **71.8%** automatic coverage it holds **0.8981**
> macro-F1 / **4.74%** error, deferring **28.2%** to human review.
> (CI: macro-F1 [0.8775, 0.9188], error [0.0377, 0.0575].)

Note the rule picked **70%** coverage for the defense variant against **80%** for
raw: to reach the same 5% error target the defense variant must defer **10
percentage points more work to humans**. That is the cost of its miscalibration
expressed in headcount.

---

## 4. Who gets deferred — the null result

**Deliverable 4 asked whether confidence-based deferral preferentially routes
`lexicon_free` errors to humans. It does not.**

**raw, high-automation** (448 deferred of 4,764)

| slice | rows | deferred | deferral rate | share of deferrals | auto error | deferred error | error capture |
|---|---:|---:|---:|---:|---:|---:|---:|
| `lexicon_free` | 4,150 | 389 | **9.4%** | 86.8% | 7.15% | 37.02% | 34.9% |
| `lexicon_hit` | 614 | 59 | **9.6%** | 13.2% | 10.99% | 40.68% | 28.2% |

**raw, high-precision** (914 deferred of 4,764)

| slice | rows | deferred | deferral rate | share of deferrals | auto error | deferred error | error capture |
|---|---:|---:|---:|---:|---:|---:|---:|
| `lexicon_free` | 4,150 | 772 | **18.6%** | 84.5% | 4.97% | 31.74% | 59.3% |
| `lexicon_hit` | 614 | 142 | **23.1%** | 15.5% | 7.84% | 33.80% | 56.5% |

The two slices are deferred at **essentially the same rate** — 9.4% vs 9.6% at
the high-automation point. `lexicon_free` is 87.1% of dev and makes up 86.8% of
the deferral queue: that is not selection, it is proportion. At the
high-precision point the ordering actually **reverses**: `lexicon_hit` is
deferred *more* (23.1% vs 18.6%).

So the mechanism is **error-selective but slice-blind**:

* Deferral is very good at finding errors in general. At the high-automation
  point the deferred 8.8% of rows contain **33.3% of all errors** — a **3.78×
  capture lift** over random routing, with a 41.0% error rate inside the queue
  against 7.9% outside it. At the high-precision point, 18.4% of rows carry
  56.2% of errors (3.06× lift).
* It is not doing this by finding the slice phase 02 identified. It is finding
  low-margin rows wherever they are.

**Two honest qualifications, in both directions:**

1. **Operationally, the queue is still mostly `lexicon_free`** — 86.8% of it. A
   reviewer working this queue does spend most of their time on implicit,
   profanity-free offense. That is a fact about the base rate, not evidence that
   confidence tracks the phase 02 weakness, and it should not be reported as the
   latter.
2. **After deferral, `lexicon_hit` is the *worse* residual slice on the
   auto-resolved path** — 10.99% error vs 7.15% for `lexicon_free` at the
   high-automation point. This is not a contradiction of phase 01: the gap there
   was in OFF-*recall*, whereas error *rate* on `lexicon_hit` is dominated by its
   18.1% false-positive rate. Confidence-based deferral removes neither
   preferentially.

The defense variant behaves the same way (`lexicon_free` 8.8% vs `lexicon_hit`
12.5% deferral at high-automation), so this is a property of confidence-based
selective prediction on this task, not of one checkpoint.

**This is a null on the hoped-for connection between phase 02's diagnosis and a
working mechanism, and it is reported as one.** The mechanism works; it simply
does not work *through* the lexical-cue weakness.

---

## Limitations

* **C4-5 rounding.** Confidences are dumped at 6dp. In this case **zero rows
  saturated** at `0.000000`/`1.000000` in either variant, so the clipping path
  was never exercised and the feared compression of the extreme logit tail did
  not occur. The limitation was pre-registered as real; it turned out not to
  bind. That is worth stating plainly in both directions.
* **One calibration method.** Temperature scaling only, pre-registered. Isotonic
  or Platt scaling might do better on the defense variant; not tested, and a
  method bake-off is a different phase.
* **Dev, not test.** Every number here is dev. The operating points are declared
  on dev and would need the official test set to be confirmed — that is phase 05,
  and the test set remains untouched.
* **The high-precision target is met on CAL, missed by 0.8pp on EVAL.** Threshold
  selection generalises imperfectly across a 2,382-row half. A production
  threshold should be set on more data than this.

## Files

| File | Contents |
|---|---|
| `calibration.json` | full report: both variants, reliability bins, curves, operating points, CIs |
| `findings.md` | this file |
