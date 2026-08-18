# Phase 11 — Per-slice calibration and prior correction

Place at `phases/11_prior_correction.md`.

**Written and committed BEFORE any Phase 11 number exists.** Nothing below is to
be revised after seeing a result. Revisions before the run are legitimate and
are made in the commit; revisions after are not.

**Binding throughout:**
- Dev split only, fingerprint `034415af3a23b388`. The official test set is
  SPENT and stays spent. Computing on saved test predictions to get around the
  guard is technically possible and is forbidden.
- Every number produced by this phase is **dev-only** and is labelled dev-only
  wherever it appears.
- Lexicon and `MIN_ROOT_LEN` stay frozen. Import `src.lexicon.hit_root`; never
  reimplement it.
- **Per-slice macro-F1 and per-slice accuracy are not reported** (phase-01
  pre-registered constraint; base rates 57.8% vs 13.6%). Raw confusion counts
  are retained.
- Fit on CAL, score on EVAL. Never fit and score on the same rows.
- Measurement only. **No intervention is proposed by this phase**, no threshold
  derived here is an operating point, and nothing here licenses Phase 12.

---

## The question

Phase 09 Stage 1 recorded that `lexicon_free` gold-`OFF` rows are scored far
below `lexicon_hit` gold-`OFF` rows — median **0.5861** against **0.9650**, with
**43.7%** at or below 0.5 against **10.7%** — while ranking is nearly intact
(AUC 0.8962 vs 0.9306, G = +0.0345 `INTERMEDIATE`).

`PROJECT_HISTORY` §7 lists the resulting question as open:

> whether the downward shift is **correct calibration to a 13.6% base rate** or
> **genuine under-confidence**.

A well-calibrated model *should* assign lower probabilities in a slice whose
base rate is 13.6% than in one whose base rate is 57.8%. If it does so
*correctly*, the depression is not a defect in the model and the operational
failure belongs entirely to the use of one global threshold across a
heterogeneous population. If the depression exceeds what the local base rate
justifies, there is genuine under-confidence, and it is a property of the
scores.

Per-slice calibration has never been computed in this project. Phase 04 measured
calibration **globally** (T = 0.9948, ECE(15) = 0.0205) and concluded raw
BERTurk needs no calibration. Surana (`arXiv:2605.14074`, May 2026, single-author
preprint, not peer-reviewed) reports the structurally analogous pattern on
identity subgroups in Civil Comments: near-perfect aggregate calibration (0.013)
alongside significant miscalibration on every subgroup (+0.029 to +0.134). This
phase asks the same question of our slice definition, and this is what makes the
project comparable to that work on its own axis.

**Polarity, stated in advance so it is not conflated later.** Surana's subgroups
are *over*-confident, producing false positives on identity-mentioning content.
Our hypothesis concerns *under*-scoring, producing false negatives on
profanity-free content. The shapes of evidence are analogous; the directions are
opposite. Any sentence that treats them as the same finding is wrong.

---

## C11-1 — Inputs and provenance

| role | file |
|---|---|
| scores | `results/01_baseline_berturk/dev_predictions.csv` |
| split | `results/04_calibration/cal_eval_split.json` (see C11-2) |
| lexicon | `data/lexicon/karaliste.txt` (frozen) |

```
dev_predictions.csv   736,591 bytes
sha256  a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
karaliste.txt         5,988 bytes
sha256  0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b
```

Both were byte-verified on 2026-08-18 at git HEAD `b902c32`. The score column is
`confidence` and is **P(OFF)**, not max-class probability; the frozen decision
rule `pred == OFF iff confidence > 0.5` is asserted at load time, not assumed.

The stage aborts unless it first reproduces, exactly:

```
dev fingerprint       034415af3a23b388
dev rows              4,764   (920 OFF)
lexicon_hit           614     (355 OFF)
lexicon_free          4,150   (565 OFF)
overall OFF-recall    635/920 = 0.6902
lexicon_hit recall    317/355 = 0.8930
lexicon_free recall   318/565 = 0.5628
false negatives       285
false positives       213
```

A mismatch on any one of them aborts the stage. `load_coltekin_test` is not
called.

## C11-2 — The CAL/EVAL split, and why it is now a file

Phase 04's split (C4-1) exists in `calibration.json` only as `n_cal: 2382`,
`n_eval: 2382`, `seed: 42` — **no row ids**. It is reconstructed by
`phase04_calibration.cal_eval_split`, which calls `data_io.stratified_split`
(sort by id, `random.Random(42).shuffle`, stratified on gold label only).

Reconstruction was verified on 2026-08-18 against four already-recorded phase-04
quantities and reproduced all four exactly:

| check | expected | observed |
|---|---:|---:|
| EVAL `lexicon_free` rows | 2,073 | 2,073 |
| EVAL `lexicon_hit` rows | 309 | 309 |
| EVAL auto @ threshold 0.663171 | 2,172 | 2,172 |
| EVAL deferred @ threshold 0.663171 | 210 | 210 |

Because the split survives only as an RNG replay, it is **frozen to a file**
before this phase runs: `results/04_calibration/cal_eval_split.json`, holding
both id lists, the four reproduction checks above, the Python version under which
they passed, and its own sha256. Every phase from here loads that file. This is
insurance, not measurement; it produces no number and licenses no claim.

**Frozen denominators** (from the verified reconstruction, counts only):

| split | slice | gold OFF | gold NOT | rows |
|---|---|---:|---:|---:|
| CAL | `lexicon_hit` | 173 | 132 | 305 |
| CAL | `lexicon_free` | 287 | 1,790 | 2,077 |
| EVAL | `lexicon_hit` | 182 | 127 | 309 |
| EVAL | `lexicon_free` | 278 | 1,795 | 2,073 |

Within-slice base rates differ between halves (`hit` 0.5672 CAL / 0.5890 EVAL;
`free` 0.1382 / 0.1341) because the split stratifies on label only, not on
slice. Wherever a prior is a *target* of rescaling, C11-6 names which half's
prior is used.

## C11-3 — Definitions

Binned on `p_OFF` over **10 equal-width bins on [0, 1]**, within a slice, over
EVAL rows of that slice:

```
ECE      = Σ_b (n_b / N) · | off_rate_b − mean_p_b |
SignedGap = Σ_b (n_b / N) · ( off_rate_b − mean_p_b )
```

where `off_rate_b` is the empirical share of gold-`OFF` rows in bin *b* and
`mean_p_b` the mean `p_OFF` in bin *b*.

**`SignedGap > 0` means the model under-states P(OFF) — under-confidence in the
`OFF` direction. `SignedGap < 0` means it over-states it.**

This is the **probabilistic** form, binned on P(OFF). It is **not** the phase-04
statistic, which bins on decision-confidence `max(p, 1−p)` over both classes and
returned a global signed gap of **−0.0091** with `direction: overconfident`.
The two are different quantities conditioned on different things and **may not be
compared, summed, or quoted in the same sentence** without naming both
definitions.

10 bins is primary. 15 and 20 are reported as sensitivities under C11-11.

## C11-4 — The primary endpoint, and why it is not the whole-slice figure

**Primary quantity:**

```
SG_free_low = SignedGap over EVAL `lexicon_free` rows with p_OFF < 0.5
```

**Why the whole-slice signed gap is disqualified as primary.** `SignedGap`
telescopes: the binning cancels and it equals `(slice OFF rate − slice mean
p_OFF)`. Since `lexicon_free` is 87.1% of dev and global calibration is good,

```
0.871 · SG_free + 0.129 · SG_hit ≈ SG_global ≈ 0
⇒  SG_free ≈ −0.148 · SG_hit
```

so `SG_free` is pinned near zero by arithmetic almost regardless of what the
model does. An endpoint that is near-forced to return the null is not an
endpoint. **This identity is unit-tested** (the binned computation must equal the
closed form to 1e-12) before the data loads, and the whole-slice figure is still
reported under C11-8 as a secondary, with this derivation attached so its
smallness is never read as a finding.

**Why the sub-threshold band.** The 0.5 threshold is frozen and is where false
negatives are created; 43.7% of `lexicon_free` gold-`OFF` sit at or below it.
This band is the population that generates the operational failure, and global
calibration — an average over all bins — constrains a single sub-band only
weakly. The band `p_OFF < 0.5` is defined by the frozen decision rule and by
nothing observed in this phase.

**Known limitation, stated now.** A signed gap is insensitive to compensating
errors across bins: a slice can be badly miscalibrated in shape and return
`SignedGap ≈ 0`. ECE (C11-8) is the shape-sensitive companion and is reported
alongside the primary in every table. Neither replaces the other.

## C11-5 — Interval estimation

Nonparametric bootstrap **stratified over the four (slice × gold) EVAL cells**
— 182 / 127 / 278 / 1,795 — each resampled with replacement to its own original
size, so the frozen denominators are preserved in every replicate. Band
membership (`p_OFF < 0.5`) is recomputed **inside** each replicate, so the
interval carries the variance of which rows fall in the band rather than
pretending the band was fixed in advance.

**10,000 replicates, seed 42, percentile interval, α = 0.05.**

## C11-6 — Design calculation: what this data can resolve

Set from the frozen EVAL denominators and from **already-recorded phase-01
flagging rates** — never from anything this phase observes. Sub-band sizes are
projected from the full-dev slice flagging rates (`free` 484/4,150 = 0.1166;
`hit` 364/614 = 0.5928), halved to EVAL scale. The dominant variance term is
the binomial variance of the empirical `OFF` rate in the band; the mean-`p` term
is tightly concentrated and is not modelled here, so these half-widths are
optimistic by a small margin and the bootstrap governs.

| statistic | design *n* | design π | SE | 95% half-width |
|---|---:|---:|---:|---:|
| `SG_free_low` (**primary**) | ~1,831 | 0.067 | 0.0059 | **±0.0115** |
| `SG_hit_low` (**control**) | ~126 | 0.151 | 0.0319 | **±0.0625** |
| `SG_free` whole slice | 2,073 | 0.134 | 0.0075 | ±0.0148 |
| `SG_hit` whole slice | 309 | 0.589 | 0.0280 | ±0.0549 |

The primary resolves to roughly **±0.012**; the control to **±0.063**, five times
coarser. The realized band sizes will differ from the design projections and
**the realized *n* is reported beside every figure**.

**Verdict thresholds, fixed here:**

- **LARGE = `SG_free_low ≥ 0.05`.** Four times the design half-width, and
  operationally large: an empirical `OFF` rate of ~0.12 where the model says
  ~0.07 in the band that creates the false negatives.
- **SMALL = `|SG_free_low| < 0.02`.** Below ~1.7× the design half-width. A
  difference this size cannot be told from noise by this design and must not be
  quoted as under-confidence in either direction.
- The band between is **declared inconclusive in advance** and is not a third
  result available for spin.

These mirror the C9-4 bands deliberately: same numbers, independently justified
on this statistic's own scale.

## C11-7 — The verdict rule

Evaluated **in this order**, on the primary only. Branches are mutually
exclusive and exhaustive. Implemented as a single function and **unit-tested on
both sides of every boundary before the data loads**.

```
0. n_band < 400                          -> INSUFFICIENT
1. ci_high < 0                           -> OVER-SCORED
2. ci_low <= 0 <= ci_high                -> BASE-RATE-CORRECT
3. ci_low > 0 and SG <  0.02             -> BASE-RATE-CORRECT
4. ci_low > 0 and 0.02 <= SG < 0.05      -> INTERMEDIATE
5. ci_low > 0 and SG >= 0.05             -> UNDER-CONFIDENT
```

Branch 0 exists because the band size is data-dependent; 400 is a floor at which
the half-width would be ~±0.025, still inside the declared bands. It is not
expected to fire on the primary and is expected to be live for the control.

## C11-8 — What each verdict obliges, written now

- **BASE-RATE-CORRECT** → the depression is what a correctly calibrated model
  does in a 13.6%-prior region. `PROJECT_HISTORY` §7's open question closes in
  that direction, dev-only. The report states that the operational failure is a
  property of applying one global threshold to a heterogeneous population, **not**
  a defect in the scores. This is a real result and is reported as the headline
  if it occurs, not buried as a null.
- **UNDER-CONFIDENT** → genuine under-scoring beyond the local base rate exists
  in the band that creates the false negatives. Reported with the magnitude and
  the CI, and **without** any claim that recalibration would recover recall —
  that is Phase 12's question and this phase does not answer it.
- **INTERMEDIATE** → both figures reported, and the report states plainly that
  this analysis cannot separate the two contributions at this evaluation-set
  size. The `INTERMEDIATE` outcome in Stage 1 is the precedent for how this is
  written.
- **OVER-SCORED** → reported as its own finding, and the phase's framing is
  stated to have been wrong in direction.
- **INSUFFICIENT** → reported as a resolution limit with the realized *n*. Not
  reframed as a null.

**Always reported regardless of verdict**, per slice, on EVAL: `n`, ECE(10),
`SignedGap`, the full 10-bin reliability table (bin bounds, `n_b`, `mean_p_b`,
`off_rate_b`), the whole-slice signed gap with the C11-4 derivation beside it,
and the calibration-fairness gap `ECE_hit − ECE_free` with a CI — the statistic
directly comparable to Surana's +0.029…+0.134.

## C11-9 — The control, declared in advance

`SG_hit_low`: the same statistic on EVAL `lexicon_hit` rows with `p_OFF < 0.5`.

This is a real control, not a courtesy. **If under-scoring in the sub-threshold
band is a global property of the model rather than a slice-specific one, both
slices show it at comparable magnitude.** A `lexicon_free` effect accompanied by
a `lexicon_hit` effect of similar size does not support a slice-specific account
and must not be reported as one. Its design half-width is ±0.063, so it can
refute a large effect and cannot resolve a small one; C11-7 branch 0 applies to
it and INSUFFICIENT is a likely and legitimate outcome.

## C11-10 — Prior correction and recalibration (secondary; no verdict attaches)

Three post-hoc treatments, each fitted on **CAL** and scored on **EVAL**, each
reported with per-slice ECE and `SignedGap` before and after:

1. **Saerens EM prior correction** (Saerens, Latinne & Decaestecker, *Neural
   Computation* 14(1):21–41, 2002, DOI `10.1162/089976602753284446`). Run
   **unsupervised** on the slice's EVAL scores, as it would be at deployment.
   The source prior is the **training** prior of that slice (`hit` 0.5535,
   `free` 0.1410, recorded in phase 08), not the dev prior. Report the
   EM-estimated prior against the known EVAL prior (`hit` 0.5890, `free` 0.1341)
   — that comparison is itself a diagnostic. **Limitation stated in advance:** EM
   prior estimation is biased when the classifier is miscalibrated, which is the
   condition under test, so a divergence is not cleanly attributable.
2. **Per-slice Platt scaling**, fitted on that slice's CAL rows.
3. **Per-slice isotonic regression**, fitted on that slice's CAL rows.
   `lexicon_hit` CAL carries **173** gold positives; isotonic will be noisy and
   may overfit. Reported, not hidden, and not preferred over Platt on the basis
   of a better EVAL number.

**A forbidden reading, fixed before the numbers exist.** The slice-conditional
training priors are `hit` 0.5535 and `free` 0.1410 against a global 0.1931.
Rescaling `lexicon_free` toward its own prior therefore pushes those scores
**down** and `lexicon_hit`'s **up**: prior correction to the slice prior
**widens** the recall gap. That is arithmetic, not a finding, and it may not be
reported as a failure of the method, as evidence about the model, or as a reason
to select a different target prior after seeing it. This phase measures
calibration; recall movement here is a by-product and is reported as one.

## C11-11 — Sensitivities: may qualify a verdict, may not overturn it

- **S1 — bin count.** ECE and `SignedGap` at 10 (primary), 15 and 20 bins. The
  phase-04 precedent is that raw ECE gets marginally *worse* at 20 bins after
  scaling; bin-count instability is reported, not resolved.
- **S2 — `MIN_ROOT_LEN` leak.** Drop from `lexicon_free` the gold-`OFF` rows whose
  tokens intersect the sub-`MIN_ROOT_LEN` entries (`ag, am, aq, oc, oç`; 28 rows
  in full dev, phase 08). Recompute.
- **S3 — suspect-root contamination.** Drop from `lexicon_hit` every row for
  which *every* matching root is in `{allah, ana, cim, emi, göt, mal, sie}` —
  the exact rule in `results/02_failure_analysis/slice_sensitivity.json`.
  Recompute.

Neither S2 nor S3 is a repair. The lexicon and `MIN_ROOT_LEN` stay frozen.

## C11-12 — A prediction, recorded before the number exists

**`SG_free_low` will be positive but below 0.05 — branch 4, `INTERMEDIATE` — and
the substantive content of this phase will be in the shape of the reliability
curve rather than in the mean.**

Basis: the model ranks `lexicon_free` well (AUC 0.8962) and is globally near
calibrated, which argues against a large mean-level distortion; but 43.7% of
gold-`OFF` sit at or below 0.5 with a median of 0.5861, which suggests mass
accumulated just under the line rather than spread evenly.

This can fail in both directions and either failure is informative. C9-16 is the
precedent: **a control that cannot fail is not a control, and a prediction that
cannot be wrong is not a prediction.**

## C11-13 — What counts as a null, stated so it cannot be reframed

A `BASE-RATE-CORRECT` verdict is **a result, not a failure of the phase.** It
answers an open question in `PROJECT_HISTORY` §7 and it is reported as the
phase's headline if it occurs. It may not afterwards be described as
inconclusive, as underpowered, or as a reason to run a variant until a different
verdict appears. If the primary returns branch 2 or 3, no further treatment in
C11-10 may be promoted to primary in its place.

## C11-14 — Scope and ceiling

Measurement only. No intervention is proposed, no threshold derived here is an
operating point, no model is retrained, no forward pass is run, the lexicon and
`MIN_ROOT_LEN` stay frozen, and the official test set is spent and stays spent.

Ceilings that travel with every number this phase produces: **dev-only**;
one seed; one checkpoint (`best.pt` = epoch 1); same-corpus; and the two known
slice-definition defects unrepaired, both of which push the headline in the
conservative direction.

Phase 11's answer does not license Phase 12. It changes what Phase 12 would be
testing, and that is all.

---

## Output

`results/11_prior_correction/` — `metrics.json`, `findings.md`, and one
`RESULTS_LOG.md` row. Aggregate statistics may be committed; **row text stays out
of git**, as always.
