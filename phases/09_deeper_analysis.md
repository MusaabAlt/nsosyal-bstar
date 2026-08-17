# Phase 09 — Deeper analysis, staged

Place at `phases/09_deeper_analysis.md`.

**Run one stage at a time. Stop after each and report. Do not chain stages.**

Stages 1–3 need no GPU and no training. Stage 4 is inference only. Stages 5–6
require training and are separately authorised by the project lead.

**Binding throughout:**
- Dev split only, fingerprint `034415af3a23b388`. The official test set is spent
  and stays spent.
- Lexicon and `MIN_ROOT_LEN` stay frozen. Import `lexicon.hit_root`.
- `dev_predictions.csv` survives only on the Drive mirror — pull it, verify its
  sha256, and say so.
- **Write each stage's decision rule into this file and commit it BEFORE running
  that stage.** The rules below are drafts; refine them in the commit, never after
  seeing a number.
- Report negative results as results. A stage that answers "no" has done its job.

---

## Stage 1 — Threshold-free slice comparison

**Priority: highest. This closes the strongest objection to our headline.**

### The objection

A reviewer can say: the two slices have very different base rates (57.8% vs 13.6%
OFF). A well-calibrated model assigns lower probabilities in the rarer slice. With
a fixed 0.5 threshold, recall falls in `lexicon_free` **automatically** — as an
artefact of where the threshold sits, not because the model understands the
content less well. How much of the 40pp is threshold placement rather than lexical
dependence?

We currently have no answer.

### Method

Everything below reads `dev_predictions.csv`. No retraining.

1. **ROC-AUC within each slice.** AUC is a ranking measure — the probability a
   random gold-OFF row scores above a random gold-NOT row *from the same slice*.
   It is invariant to where the threshold falls. Report both slices with bootstrap
   CIs and the difference with a CI.
2. **Score distributions.** For gold-OFF rows only, report mean, median and
   quartiles of `p_OFF` in each slice. This shows directly whether scores are
   shifted downward in `lexicon_free`.
3. **Recall at matched operating points.** Instead of a fixed 0.5, find the
   per-slice threshold that yields equal *precision* in both slices, and report
   recall there. Then repeat holding *flagging rate* equal. Two different ways of
   removing the threshold confound.
4. Also report average-precision (PR-AUC) per slice, noting that unlike ROC-AUC it
   is base-rate sensitive, so it is reported for completeness rather than as the
   controlled comparison.

### Pre-registration — Stage 1

Written and committed **before any AUC number exists**. The draft this replaces
is in git at `bcb4b70`; it named "large" and "small" without numbers, which is
exactly the hole a post-hoc reading walks through. Everything below is fixed and
is not to be revised after seeing a result.

#### C9-1 — input and provenance

`results/01_baseline_berturk/dev_predictions.csv`, 4,764 rows, BERTurk
`best.pt` = **epoch 1** — the same dump phases 02 and 04 read.

```
sha256  a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
bytes   736,591
```

The score is the `confidence` column, which is **P(OFF)**, not max-class
probability. The frozen decision rule is `pred == OFF iff confidence > 0.5`;
this is asserted at load time, not assumed.

The file is gitignored (corpus text) and its durable copy is the Drive mirror.
Provenance is established by reproducing every recorded phase-01 figure from it
before any new quantity is computed — overall OFF-recall 635/920 = 0.6902,
`lexicon_hit` 317/355 = 0.8930, `lexicon_free` 318/565 = 0.5628, 285 FN, 213 FP,
FP rates 47/259 and 166/3585, OFF-precision 0.7488. **A mismatch on any one of
them aborts the stage.** No retraining, no forward pass, dev only, fingerprint
`034415af3a23b388`; `load_coltekin_test()` is not called.

#### C9-2 — AUC definition, including ties

Within a slice, over that slice's gold-OFF and gold-NOT rows only:

```
AUC = ( #{s_off > s_not} + 0.5 · #{s_off == s_not} ) / (n_off · n_not)
```

the Mann–Whitney U form with **half credit for ties**. Declared because the
scores carry six decimals and exact ties are possible; a tie convention chosen
after seeing the table is a free parameter.

The primary quantity is

```
G = AUC(lexicon_hit) − AUC(lexicon_free)
```

Slice membership is the **frozen** Day 1 definition (`hit_root`, `MIN_ROOT_LEN`
= 3). Its two known defects are not repaired here; they are carried into C9-10
as sensitivities.

#### C9-3 — interval estimation

Stratified nonparametric bootstrap over the four (slice × gold) cells: each cell
is resampled with replacement **to its own original size**, so the four
denominators 355 / 259 / 565 / 3585 are preserved in every replicate. Both AUCs
and their difference are computed inside the replicate. **10,000 replicates,
seed 42, percentile interval, α = 0.05.** The slices are disjoint row sets, so
the two AUCs are independent and no pairing is available; differencing inside a
replicate is stated only to remove ambiguity about how the interval was formed.

#### C9-4 — what "large" and "small" mean, and why these numbers

The thresholds are set from a design calculation that uses only the four frozen
denominators and an *assumed* AUC — not the observed one. Hanley–McNeil standard
errors, 95% half-widths in brackets:

| assumed AUC | `lexicon_hit` (355/259) | `lexicon_free` (565/3585) | difference |
|---|---|---|---|
| 0.80 | 0.0174 [±0.0342] | 0.0115 [±0.0226] | 0.0209 [**±0.0410**] |
| 0.85 | 0.0152 [±0.0297] | 0.0104 [±0.0204] | 0.0184 [**±0.0360**] |
| 0.90 | 0.0123 [±0.0242] | 0.0088 [±0.0173] | 0.0152 [**±0.0297**] |

So this dataset can resolve a difference of roughly **±0.03 to ±0.04** and no
finer. Two thresholds follow:

- **LARGE = `G ≥ 0.05`.** Above the design half-width across the whole assumed
  range, and 10% of the 0.5-wide usable span of AUC. A gap this size is a
  property of the model, not of the sample size.
- **SMALL = `G < 0.02`.** Below the half-width of even the better-resolved single
  slice. A difference under 0.02 cannot be told from noise by this design and
  must not be quoted as a discrimination difference in either direction.
- The band between them is **not** a third result to be spun; it is declared in
  advance as inconclusive (C9-5, V2).

#### C9-5 — the verdict rule

Evaluated **in this order**, on the primary comparison only. The branches are
mutually exclusive and exhaustive, so no result can fall between them:

```
1. ci_high < 0                    -> REVERSES
2. ci_low <= 0 <= ci_high         -> NARROWS      (interval includes zero)
3. ci_low > 0 and G <  0.02       -> NARROWS      (resolvable but below the floor)
4. ci_low > 0 and 0.02 <= G < 0.05 -> INTERMEDIATE
5. ci_low > 0 and G >= 0.05       -> CONFIRMS
```

This is implemented as a single function and unit-tested on both sides of every
boundary before the real data is loaded.

#### C9-6 — what each verdict obliges, written now

- **CONFIRMS** → the recall gap is not merely threshold placement; ranking
  quality itself differs. AUC is reported in §4 beside recall as the
  threshold-free confirmation. Note the limit even here: it licenses "ranks
  profanity-free offensive content worse", **not** any claim about
  comprehension.
- **INTERMEDIATE** → both numbers reported, and the report states plainly that
  this analysis cannot separate the two contributions.
- **NARROWS** → the headline is narrowed **in the report**, in §4 and §5, to:
  *at the fixed 0.5 threshold the model's scores are systematically lower on
  profanity-free offensive content* — operationally real, weaker than the
  current wording. The narrowed sentences are drafted in the same commit as the
  result, not deferred.
- **REVERSES** → as NARROWS, and the reversal is stated as its own finding.

The verdict rests on the primary comparison. **No sensitivity in C9-10 may
overturn it**; sensitivities qualify a verdict, they do not select one.

#### C9-7 — score distributions (descriptive, no verdict)

Per slice and per gold class: n, mean, median, Q1, Q3, and the share below 0.5.
Reported for both classes, not only gold-OFF, because a downward shift confined
to the OFF class and one affecting the whole slice are different findings. No
verdict attaches to this step; it describes whichever verdict C9-5 returns.

#### C9-8 — matched operating points

Thresholds are swept over the sorted distinct observed scores **within** the
slice being moved, with the frozen convention `pred = OFF iff score > t`.

Reference points, both directions reported:

- **A → B, equal precision.** Take the reference slice's precision `P*` at
  t = 0.5. In the other slice choose the **lowest** t whose precision ≥ `P*`.
  Lowest is declared in advance because it maximises recall at the matched
  precision — the choice most favourable to the model, so the comparison cannot
  be accused of being rigged against it.
- **A → B, equal flagging rate.** Choose the t minimising |flag rate − `F*`|,
  where `F*` is the reference slice's share of rows predicted OFF at t = 0.5.
  Ties broken toward the **lower** t, same reasoning.
- Both directions are run: `lexicon_hit` held at 0.5 and `lexicon_free` moved,
  and the reverse.
- **If the target is unattainable** in the moved slice, report the best
  attainable value and mark the match **FAILED**. No substitute target is
  selected. A failed match is itself informative and is reported as one.

CIs on matched recall use the same stratified bootstrap, **re-selecting the
threshold inside each replicate**, so the interval carries the selection
variance rather than pretending the threshold was known in advance.

These thresholds are **diagnostic only**. They are not an operating point, are
not compared to the phase-04 deployment thresholds, and nothing may be built on
them (C9-11).

#### C9-9 — PR-AUC

Average precision, step interpolation: `AP = Σ_n (R_n − R_{n−1}) · P_n`.
Reported per slice for completeness. It is **base-rate sensitive** — the slices
differ 57.8% vs 13.6% — so it may **not** be used to support or to oppose the
C9-5 verdict, in either direction. Stated here so that it cannot be recruited
afterwards.

#### C9-10 — sensitivities, all fixed in advance, all reported regardless of sign

- **S1 — `MIN_ROOT_LEN` leak.** Drop from `lexicon_free` the gold-OFF rows whose
  token set intersects the lexicon entries shorter than `MIN_ROOT_LEN`
  (`ag, am, aq, oc, oç`; 28 rows in dev, phase 08). Recompute.
- **S2 — suspect-root contamination.** Drop from `lexicon_hit` every row for
  which *every* matching lexicon root is in the suspect set
  `{allah, ana, cim, emi, göt, mal, sie}` — the exact rule already recorded in
  `results/02_failure_analysis/slice_sensitivity.json`. Recompute.
- **S3 — tie convention.** Recompute the primary AUCs counting ties as 0 and as
  1, to bound how much the C9-2 convention could be worth.

None of these is a repair. The lexicon and `MIN_ROOT_LEN` stay frozen.

#### C9-11 — scope

Measurement only. **No intervention is proposed from this stage**, no threshold
derived here becomes an operating point, the lexicon and matcher are not
touched, and the official test set is spent and stays spent.

Whatever comes back is reported. Do not soften an unfavourable result and do not
reach for the test set.

---

## Stage 2 — How much of BERTurk is bag-of-words?

**The question:** how much of the 0.8271 macro-F1 is recoverable by a linear model
that only counts words — no context, no order, no understanding?

### Method

Train TF-IDF + logistic regression on the **training split only**, evaluate on the
same frozen dev split. Word unigrams + bigrams; also run a character n-gram variant
(3–5) since Turkish is agglutinative and character n-grams partially capture
morphology. `seed=42`.

Report, for each of the three systems (keyword filter, TF-IDF+LR, BERTurk):
overall macro-F1, and `lexicon_hit` / `lexicon_free` OFF-recall separately, all
with CIs. Report the BERTurk − LR delta with a paired CI.

Also extract the LR's highest-weight features for the OFF class and compare them
against Stage 8's high-skew token list. If they overlap heavily, two independent
methods have found the same lexical signal.

### Why it matters

If BERTurk beats a word-counter by only a few points, that single comparison
supports the entire thesis: apparent performance rests on surface lexical patterns
rather than comprehension.

**Watch the slice breakdown.** The interesting prediction is that BERTurk's
advantage over LR is small in `lexicon_hit` and larger in `lexicon_free` — i.e.
whatever BERTurk knows beyond word-counting is concentrated exactly where the
lexicon does not help. If that holds it is independent evidence for the diagnosis.
If BERTurk's advantage is flat across slices, say so.

### Pre-registered decision rule

State in advance what counts as "close": we pre-register that a BERTurk−LR
macro-F1 delta under 0.05 will be described as *narrow*, 0.05–0.10 as *moderate*,
above 0.10 as *substantial*. No adjusting these labels after seeing the number.

---

## Stage 3 — Do BERTurk and the keyword filter fail on the same rows?

**The question:** is BERTurk doing something categorically different from the
lexicon, or the same thing more cleanly?

### Method

Row-level comparison on dev, from existing predictions:

- 2×2 agreement table: rows both get right, both get wrong, and each direction of
  disagreement
- Of the keyword filter's 565 false negatives, how many does BERTurk also miss?
- Of BERTurk's 285 false negatives, what share are also filter false negatives?
- Cohen's κ between the two systems' errors, and the same broken down by slice

### Pre-registered decision rule

- **BERTurk's errors are largely a subset of the filter's** → BERTurk is a cleaner
  lexicon, and that is a strong, quotable framing of the diagnosis.
- **Substantial non-overlap** → BERTurk has learned something the lexicon has not,
  and the diagnosis needs qualifying. Report the size of what it learned.

---

## Stage 4 — Is the deixis signal used, or merely present?

**Current limitation, stated in `results/08_lexical_analysis/findings.md`:**
co-occurrence shows the signal was *available*, not that the model *used* it. This
stage tests use.

### Method

Inference only, no training. On the 118 no-profanity false positives:

1. **Perturbation.** Replace second-person deictic tokens (`sen`, `siz`, `sizin`,
   `senin`, `sizi`, `sana`, `size` — enumerate the exact set and commit it before
   running) with third-person equivalents. **Replace, do not delete** — Turkish is
   agglutinative and deletion breaks agreement and case. Where a clean third-person
   substitution is impossible, skip the row and report how many were skipped.
2. Re-run the frozen model on the perturbed rows and report the change in mean
   `p_OFF` and in the number still predicted OFF, with a paired CI.
3. **Control, mandatory.** Repeat with a non-deictic token of comparable document
   frequency, substituted for a comparable one. Without this, any movement measures
   sensitivity to perturbation in general rather than to deixis specifically.
4. **Second control.** Run the same perturbation on a matched sample of correctly
   classified NOT rows. If `p_OFF` moves there too, the effect is not specific to
   the error set.

### Pre-registered decision rule

- **`p_OFF` drops on deictic perturbation, control flat** → the model uses the
  signal. The claim upgrades from co-occurrence to attribution and the ceiling
  currently attached to the finding can be lifted, with the perturbation method
  stated.
- **Both move** → measuring perturbation sensitivity, not deixis. Report as
  inconclusive and keep the existing ceiling.
- **Neither moves** → the co-occurrence is incidental. Report as a null and keep
  the ceiling. This is a real answer.

---

## Stage 5 — `[MASK]` alternative *(requires GPU; authorise separately)*

**The hypothesis:** 1a failed because `[MASK]` exists in training and never at
inference, giving the model a cue it cannot use in deployment.

**Method:** rebuild the 1a operator replacing the profanity with a **different
randomly chosen profanity** from the frozen lexicon rather than `[MASK]`. Same 382
qualifying rows, same filter, same hyperparameters, same seed. Train and evaluate
on the same four metrics.

**Value:** if this recovers `lexicon_free` recall where `[MASK]` lost it, the
project's one failed component becomes a working one, and the mechanism is
explained rather than guessed.

**Risk:** it may fail too — but a failure with a tested mechanism is reportable
where an untested guess is not.

**Cost:** operator rewrite plus one ~5-minute training run.

---

## Stage 6 — Class weighting *(requires GPU; authorise separately)*

`results/08_lexical_analysis/findings.md` records this as an explicit gap: the
corpus is 1:4.18, no weighted variant was ever trained, and its contribution to the
absolute level of `lexicon_free` recall is unmeasured. The advisor also raised data
balance.

**Method:** one training run with inverse-frequency class weights, everything else
identical. Report all four metrics plus the recall gap.

**What it answers:** whether the absolute level of profanity-free recall is partly
an imbalance artefact. Note in advance that this cannot explain the *gap* — one
model and one threshold across two disjoint subsets, so a global imbalance
depresses both alike. It speaks to the level, not the difference.

**Cost:** one ~5-minute training run.

---

## Output

Each stage writes to `results/09_deeper_analysis/stage_N/` with metrics JSON, a
`findings.md`, and a `RESULTS_LOG.md` row. Aggregate statistics may be committed;
row text stays out of git as always.

Stages 1–4 touch no GPU and no training. Stages 5–6 do, and are not to be started
without explicit authorisation from the project lead.

**No intervention is to be proposed from any stage. Measurement only.**
