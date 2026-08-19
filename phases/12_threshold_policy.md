# Phase 12 — Threshold policy: slice-conditional versus a single cost-optimal threshold

Place at `phases/12_threshold_policy.md`.

**Written and committed BEFORE any Phase 12 number exists.** Nothing below is to
be revised after seeing a result. Revisions before the run are legitimate and are
made in the commit; revisions after are not.

**Binding throughout:**
- Dev split only, fingerprint `034415af3a23b388`. The official test set is SPENT
  and stays spent. Computing on saved test predictions to get around the guard is
  technically possible and is forbidden.
- Every number this phase produces is **dev-only** and is labelled dev-only
  wherever it appears.
- Lexicon and `MIN_ROOT_LEN` stay frozen. Import `src.lexicon.hit_root`.
- **Thresholds are fitted on CAL and scored on EVAL.** This phase *fits*, so
  unlike Phase 15 the CAL/EVAL split is doing methodological work and may not be
  pooled. Split loaded from the frozen `results/04_calibration/cal_eval_split.json`
  (sha256 `6d1e3ed7…af899`).
- **Per-slice macro-F1 and per-slice accuracy are not reported** (phase-01
  constraint). OFF-recall, precision, and raw confusion counts only.
- No retraining, no forward pass, no GPU.

---

## The question, and how Run A changed it

Phase 11 Run A established that `lexicon_free` sub-threshold probabilities are
**accurate** — signed gap −0.0046 [−0.0128, +0.0035] over 1,846 EVAL rows,
verdict `BASE-RATE-CORRECT`, dev-only. The scores are not broken.

This disqualifies the framing this phase was originally going to carry. A
slice-conditional threshold can no longer be described as *repairing
under-confidence*, because there is no measured under-confidence to repair in
the region that generates the false negatives. Lowering the `lexicon_free`
threshold does not recover hidden true positives; it knowingly flags a
population whose offensive rate the model already reports correctly.

**What is actually defective is the decision rule.** A fixed 0.5 threshold on a
calibrated probability is the cost-optimal rule if and only if a false negative
and a false positive cost the same. Nothing in this project has ever asserted
that, and no moderation setting satisfies it. The defect is the implicit
symmetric-cost assumption, not the slice.

So the comparison is **slice-conditional thresholds against a single
cost-optimal threshold**, and 0.5 is demoted from baseline to historical
reference.

## C12-1 — The theoretical result this phase is testing against

Elkan, *The Foundations of Cost-Sensitive Learning*, IJCAI 2001. For a
calibrated posterior `p` and costs `c_FP`, `c_FN`, flagging minimises expected
cost iff

```
p  >  t*  =  c_FP / (c_FP + c_FN)  =  1 / (1 + r),    r = c_FN / c_FP
```

**`t*` depends only on the cost ratio. It does not depend on the base rate.**

The consequence, stated before any number exists: **if both slices are
calibrated, the cost-optimal threshold is identical in both, and
slice-conditional thresholding has nothing to add — as a matter of theory, not
of measurement.** Slice-conditional thresholds can beat a single threshold only
to the extent that **per-slice calibration differs**.

Where that leaves room for this phase to fail:

1. `lexicon_hit`'s sub-threshold band is **unmeasured** — Run A returned
   `INSUFFICIENT` at n = 134. Its calibration is unknown in either direction.
2. Run A's `lexicon_free` bin **[0.4, 0.5) carries a gap of −0.162** (mean p
   0.4449 against an empirical rate of 0.2830), and bins above 0.5 run −0.13 to
   −0.18. A cost-optimal threshold at moderate asymmetry lands near that region.
3. Calibration was verified **below 0.5 only**. Any `t*` above 0.5 (i.e. r < 1)
   is outside verified territory and the Elkan argument may not be invoked there.

## C12-2 — Inputs and provenance

| role | file |
|---|---|
| scores | `results/01_baseline_berturk/dev_predictions.csv` |
| split | `results/04_calibration/cal_eval_split.json` |
| lexicon | `data/lexicon/karaliste.txt` (frozen) |

```
dev_predictions.csv   736,591 bytes
sha256  a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
karaliste.txt         5,988 bytes
sha256  0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b
cal_eval_split.json
sha256  6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899
```

The same provenance gate as Phase 11 Run A: all eight recorded phase-01 figures,
the dev fingerprint, the frozen decision rule `pred == OFF iff confidence > 0.5`,
and `hit_root` agreement with the dumped `slice` column. Any mismatch aborts.
`load_coltekin_test` is not called.

**Frozen fitting and scoring denominators** (from `cal_eval_split.json`):

| split | slice | gold OFF | gold NOT | rows |
|---|---|---:|---:|---:|
| CAL | `lexicon_hit` | 173 | 132 | 305 |
| CAL | `lexicon_free` | 287 | 1,790 | 2,077 |
| EVAL | `lexicon_hit` | 182 | 127 | 309 |
| EVAL | `lexicon_free` | 278 | 1,795 | 2,073 |

## C12-3 — The four systems

All operate on the same rows. None retrains. All thresholds that are *fitted* are
fitted on **CAL** and applied unchanged to **EVAL**.

| id | system | thresholds | fitted params | lexicon at inference |
|---|---|---|---:|---|
| **S0** | frozen historical | 0.5 everywhere | 0 | no |
| **S1a** | analytic Elkan | `t* = 1/(1+r)` everywhere | 0 | no |
| **S1b** | fitted single | one threshold, cost-minimising on CAL | 1 | **no** |
| **S2** | slice-conditional | `t_hit`, `t_free`, each cost-minimising on its own CAL slice | 2 | **yes** |

**S1b is the primary comparator**, not S1a and not S0. It equalises the fitting
procedure — one fitted threshold against two — so that any S2 advantage cannot be
attributed to S2 having been fitted while its comparator was not.

**S1a is a zero-parameter internal control.** If S1a ≈ S1b, the empirically
fitted single threshold has landed where calibration theory says it should, which
is independent evidence that the probabilities are well behaved. If they diverge
materially, the Elkan argument is weaker than C12-1 states and that is reported.

**Fitting protocol.** Thresholds are swept over the sorted distinct observed
scores **within the CAL rows being fitted**, frozen convention `flag iff
score > t`, selecting the `t` minimising empirical cost (C12-4). Ties broken
toward the **lower** `t`, declared in advance because it maximises recall at
equal cost and is therefore the choice least favourable to the null this phase
predicts.

## C12-4 — Cost model and the cost grid

Set `c_FP = 1`, `c_FN = r`. Expected cost per row on a set of size `N`:

```
Cost(r)  =  ( FP  +  r · FN ) / N
```

**`r` is a policy input and this project has no principled source for it.** No
value is defended. The frontier is reported over

```
r  ∈  {1, 2, 3, 5, 10}      t*  =  {0.500, 0.333, 0.250, 0.167, 0.091}
```

**`r = 3` is the primary**, declared here and not chosen afterwards. Its
justification is bounded and stated as such: it places `t*` at 0.250, inside the
p < 0.5 region where Run A verified calibration, and materially away from the
frozen 0.5. `r = 1` is retained because it reproduces S0 exactly and is a
correctness check on the implementation, not a policy proposal.

The other four `r` values **may qualify the verdict and may not overturn it**
(the C9-10 rule). A verdict is read off `r = 3` alone.

## C12-5 — The primary endpoint, and why it cannot be gamed

```
ΔCost_rel  =  [ Cost_S2(EVAL, r=3)  −  Cost_S1b(EVAL, r=3) ]  /  Cost_S1b(EVAL, r=3)
```

Negative means slice-conditional thresholds are better.

**Why this endpoint is capable of failing.** Lowering `t_free` raises
`lexicon_free` recall. That is arithmetic and it is not a finding. A cost
endpoint prices the false positives that the extra recall buys, so an arm cannot
win by flagging more: the "flag everything" limit has cost `(1−π)·N/N`, which is
worse than either arm. The matched-cost requirement is therefore **built into the
objective** rather than imposed as a side constraint.

**The SPEC-DEFECT distinction, restated because this project conflated it once.**
Recorded 2026-08-17 as a SPEC DEFECT against C9-8: matching operating points
*across slices* — equal precision or equal flagging rate between `lexicon_hit`
and `lexicon_free` — removes the threshold confound and leaves the **base-rate**
confound fully intact, because precision and top-*q* composition both depend on
the slice's OFF/NOT mixture. **Nothing in this phase does that.** Every
comparison here is **between two systems on the same rows**, which is a different
comparison and is legitimate. Any per-slice figure reported under C12-8 is
descriptive of one system and is never used to compare one slice against the
other.

## C12-6 — Interval estimation

**Paired** nonparametric bootstrap over EVAL rows: both arms score the identical
rows, so pairing is available and removes the between-system variance. Resampling
is stratified over the four EVAL (slice × gold) cells — 182 / 127 / 278 / 1,795 —
each to its own original size. Thresholds are **not** re-fitted inside the
replicate; they are fixed by CAL, which is what "fitted on CAL, applied to EVAL"
means. The interval therefore carries EVAL sampling variance and **not**
threshold-selection variance; C12-9 measures the latter separately and directly.

**10,000 replicates, seed 42, percentile interval, α = 0.05.**

## C12-7 — Design calculation and the verdict rule

S1b and S2 differ only on **discordant rows** — rows on one side of one arm's
threshold and the other side of the other's. Let `d` be the discordant count on
EVAL. Each discordant row changes cost by `1/N` (a new false positive) or `r/N`
(a corrected false negative), so the paired standard error is bounded by

```
SE(ΔCost)  ≤  r · sqrt(d) / N ,        N = 2,382,  r = 3
```

Taking `Cost_S1b ≈ 0.27` per row as an order-of-magnitude scale (from S0's
recorded 285 FN / 213 FP at 0.5, adjusted to EVAL size — an ordering-of-magnitude
input, not a claim):

| discordant `d` | SE(ΔCost) | 95% half-width, relative |
|---:|---:|---:|
| 40 | 0.0080 | ±0.058 |
| 100 | 0.0126 | ±0.092 |
| 200 | 0.0178 | ±0.129 |

This bound is conservative — discordant rows are not independent worst-case
flips, and the bootstrap governs — but it fixes the bands:

- **LARGE = `ΔCost_rel ≤ −0.10`.** Slice-conditional thresholding meaningfully
  reduces cost.
- **SMALL = `|ΔCost_rel| < 0.04`.** Below the half-width at any plausible `d`;
  cannot be distinguished from no difference by this design.
- The band between is **declared inconclusive in advance**.

**Verdict rule, evaluated in this order. Branches are mutually exclusive and
exhaustive, and the function is unit-tested on both sides of every boundary
before the data loads.**

```
0. d < 40                                    -> INSUFFICIENT
1. ci_low > 0                                -> SLICE-CONDITIONAL WORSE
2. ci_low <= 0 <= ci_high                    -> SINGLE-THRESHOLD-SUFFICIENT
3. ci_high < 0 and |dCost_rel| <  0.04       -> SINGLE-THRESHOLD-SUFFICIENT
4. ci_high < 0 and 0.04 <= |dCost_rel| < 0.10 -> INTERMEDIATE
5. ci_high < 0 and |dCost_rel| >= 0.10       -> SLICE-CONDITIONAL BETTER
```

Branch 0 exists because `d` is not knowable until the thresholds are fitted. If
it fires, the phase reports `INSUFFICIENT` with the realized `d` and **does not**
reframe a coincidentally small `ΔCost_rel` as a null.

## C12-8 — What each verdict obliges, written now

**`SINGLE-THRESHOLD-SUFFICIENT` is a success and is pre-registered as one.** It
is not a failed intervention and may not be written up as one. Its obligations:

- Report that a single cost-derived threshold captures the available gain, with
  the C12-1 derivation as the reason rather than as a post-hoc rationalisation.
- **State that the lexicon does not enter inference.** The standing objection
  this project could not answer — that repairing lexicon dependence with a
  slice-conditional rule means consulting the lexicon at inference, which no
  paper in either research pass addresses, defends, or circumvents — **does not
  arise**, because there is no routing variable in the deployed rule. This is the
  strongest available answer to that objection and it is reported as the phase's
  headline.
- Report the recovered recall against S0 at `r = 3`, and the precision it cost.

**`SLICE-CONDITIONAL BETTER`** → report the magnitude, and report that the
deployed rule now consults the profanity lexicon at inference. The routing-variable
defence must then be **argued explicitly**: the lexicon selects which calibration
applies and does not vote on the label. It is not asserted, and the objection is
stated in the report in its strongest form beside the answer.

**`INTERMEDIATE`** → both figures reported; the report states plainly that this
analysis cannot separate the two at this evaluation-set size.

**`SLICE-CONDITIONAL WORSE`** → reported as its own finding.

**`INSUFFICIENT`** → reported as a resolution limit with the realized `d`.

**Reported regardless of verdict**, on EVAL, for all four systems at every `r`:
total cost, FP, FN, OFF-recall overall and per slice, OFF-precision overall and
per slice, flagging count, the recall gap `hit − free`, and the fitted thresholds.
Plus a matched-flag-count view: at S1b's EVAL flag count, S2's recall gap and
precision, labelled as a between-systems comparison per C12-5.

## C12-9 — `t_hit` is fitted on 173 positives, and that is measured, not assumed

The `lexicon_hit` CAL cell is **305 rows (173 gold OFF)**. Near its minimum the
empirical cost curve on so few rows is flat, so the argmin is weakly determined
and the fitted `t_hit` will be noisy. This is **not** declared
`INSUFFICIENT`-by-construction — 305 rows supports a fit, unlike Phase 15's
address × `lexicon_hit` control cell at n = 22, which was declared unfittable
before any run and is not being run.

Instead it is **measured**: refit `t_hit` and `t_free` inside 10,000 bootstrap
replicates **of CAL**, and report the distribution of each fitted threshold.

- Pre-registered instability rule: **if the IQR of the bootstrap distribution of
  `t_hit` exceeds 0.20**, the S2 arm is reported as **unstable**, and its point
  estimate is reported with that label attached everywhere it appears. An
  unstable S2 that nonetheless wins is a weaker result than a stable one and is
  written as such.
- This is a separate computation from C12-6 and its output may qualify the
  verdict. **It may not overturn it.**

## C12-10 — A prediction, recorded before the number exists

**`ΔCost_rel` will fall inside SMALL — branch 2 or 3, `SINGLE-THRESHOLD-SUFFICIENT`.**

Basis: C12-1's derivation plus Run A's measured calibration in the region where
`t*(r=3) = 0.250` falls.

It can fail in both directions and either failure is informative. C9-16 is the
precedent: **a prediction that cannot be wrong is not a prediction.** C11-12
failed on its own terms four hours ago and its failure is on the record.

## C12-11 — Sensitivities: may qualify a verdict, may not overturn it

- **S1 — the cost frontier.** All four non-primary `r` values.
- **S2 — `MIN_ROOT_LEN` leak.** Drop from `lexicon_free` the gold-`OFF` rows whose
  tokens intersect `{ag, am, aq, oc, oç}` (28 rows in full dev, phase 08).
- **S3 — suspect-root contamination.** Drop from `lexicon_hit` every row for which
  *every* matching root is in `{allah, ana, cim, emi, göt, mal, sie}`.

Neither S2 nor S3 is a repair. The lexicon and `MIN_ROOT_LEN` stay frozen.

## C12-12 — What counts as a null, so it cannot be reframed

`SINGLE-THRESHOLD-SUFFICIENT` is **the pre-registered success case**, per C12-8.
It may not afterwards be described as a failure, as inconclusive, or as a reason
to run further arms until a different verdict appears. If the primary returns
branch 2 or 3, no sensitivity and no additional `r` may be promoted in its place,
and no fifth system may be added to the comparison.

## C12-13 — Scope change, declared: this phase derives an operating point

C9-11 and C9-17 forbade deriving operating points, and C11-14 repeated the
prohibition. **Phase 12 derives one, and that is its purpose.** The prohibition
is lifted here and only here, by this pre-registration, and it remains in force
for every earlier phase's outputs.

## C12-14 — The ceiling on anything this phase produces

**The official test set is spent. Any threshold selected here can never receive
an independent held-out number.** It is fitted on dev CAL and scored on dev EVAL,
and no measurement outside that is available to this project.

Consequences, binding on the report and on the demo:

- A Phase 12 threshold **may** be wired into the offline demo.
- It **may not** carry any generalisation claim. No sentence may state or imply
  that it will hold on unseen data.
- Phase 05 recorded that dev-fitted thresholds transferred to test within 1–2pp
  of coverage. That is a fact about the **phase-04** thresholds and is **not**
  evidence about these; it may be cited as background and not as validation.
- One seed, one checkpoint (`best.pt` = epoch 1), same-corpus, dev-only, with
  both known slice-definition defects unrepaired.

## C12-15 — Scope

No retraining, no forward pass, no GPU, no new corpus, no new labels. The
lexicon and `MIN_ROOT_LEN` stay frozen. The official test set is spent and stays
spent. Phase 15 is a separate measurement and no Phase 15 quantity enters this
phase in any arm.

---

## Output

`results/12_threshold_policy/` — `metrics.json`, `findings.md`, and one
`RESULTS_LOG.md` row. Aggregate statistics may be committed; **row text stays out
of git**, as always.

---

### Addendum, 2026-08-19 — four defects found before any Phase 12 number existed. Recorded, not rewritten.

Found by Claude Code in the commit session for `ec2fd3a7`, before the run.
**C12-1…C12-15 above are left exactly as committed**, per the C9-8 and C11-2
precedents. No verdict band moves.

**1. `S1` and `S2` each name two different objects.** C12-3 defines systems
S0 / S1a / S1b / S2; C12-11 labels its sensitivities S1, S2, S3. "S2 is
unstable" (C12-9) and "S2 drops 28 rows" (C12-11) refer to unrelated things.
**Binding convention from here:** the four systems keep S0 / S1a / S1b / S2; the
three sensitivities are renamed **SENS-1** (cost frontier), **SENS-2**
(`MIN_ROOT_LEN` leak), **SENS-3** (suspect-root contamination). `metrics.json`
keys and all prose use these names. This is a naming defect, not a change to any
comparison.

**2. `Cost_S1b ≈ 0.27` in C12-7 is wrong arithmetic.** From the figures cited
beside it, S0 costs `(213 + 3·285)/4764 = 0.2242` on full dev and
`(100 + 3·158)/2382 = 0.2410` on EVAL, which is the relevant scoring set.
S1b's cost is lower still, since `t* = 0.250` trades false negatives for false
positives at `r = 3`. Corrected relative half-widths, against 0.241:

| discordant `d` | SE(ΔCost) | 95% half-width, relative |
|---:|---:|---:|
| 40 | 0.0080 | ±0.065 |
| 100 | 0.0126 | ±0.103 |
| 200 | 0.0178 | ±0.145 |

The SE column is unchanged and was correct; only the denominator was wrong.

**3. The corrected table under-powers branch 5, and the bias is declared rather
than corrected.** At `d = 100` the half-width (±0.103) meets the LARGE band
(0.10), so `SLICE-CONDITIONAL BETTER` is reachable only for a large effect.
That biases the design **toward** the outcome C12-10 predicts. The band is **not**
moved: no Phase 12 number exists, so a change would be legitimate in principle,
but any replacement value would be chosen with knowledge of which direction
favours the recorded prediction, and that is a worse defect than an
under-powered branch.

**Pre-registered reporting requirement, added in its place:** the run reports the
realized `d`, the realized relative half-width, and — whenever that half-width
equals or exceeds 0.10 — an explicit statement that branch 5 was not reachable at
the realized resolution. This appears beside the verdict, in `metrics.json` and in
the findings, whatever the verdict is.

**4. "bins above 0.5 run −0.13 to −0.18" (C12-1) overstates Run A.** The actual
`lexicon_free` gaps above 0.5 are −0.1362, −0.0140, −0.0334, −0.1791, −0.1375.
Two of the five sit well outside the stated range; the over-statement is real but
not uniform. C12-1's point — that a cost-optimal threshold lands near a region of
over-statement, leaving room for this phase to fail — survives on the [0.4, 0.5)
gap of −0.162 and on bins [0.8, 0.9) and [0.9, 1.0).

**5. C12-9's citation of Phase 15 pointed at a document that does not exist.**
There is no Phase 15 pre-registration in the repo; the address × `lexicon_hit`
band cell of **n = 22** is recorded in `results/15_deixis/cell_counts.json`
(commit `95d20de4`), and the decision not to run that control was taken by the
project lead on 2026-08-19. C12-9's claim stands on that record; the citation is
corrected to it here.
