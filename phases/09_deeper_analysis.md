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

### Pre-registered decision rule

- **AUC gap large, CI excludes zero** → the difference is in ranking quality, not
  threshold placement. The central claim strengthens: the model genuinely
  discriminates worse on profanity-free content. Report AUC alongside recall as
  the threshold-free confirmation.
- **AUC gap small or CI includes zero** → ranking quality is comparable and the
  recall gap is substantially a threshold/score-shift effect. **The claim must be
  narrowed**, and narrowed in the report, not hidden. The finding becomes: at a
  fixed operating threshold the model's scores are systematically lower on
  profanity-free offensive content — still operationally real, but a different and
  weaker statement than "understands it less well."
- **Intermediate** → report both numbers and state plainly that the two
  contributions cannot be separated by this analysis.

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
