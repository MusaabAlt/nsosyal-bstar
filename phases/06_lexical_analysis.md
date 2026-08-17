# Phase 06 — word-level lexical dependence

Opened 17 Aug 2026, on an academic advisor's suggestion. **Measurement only.**
No training, no GPU, no forward pass, no intervention proposed. Everything is
computed from the corpus TSV, the frozen split file, the frozen lexicon, and the
phase-02 false-positive tag file.

## The question

Phases 01–03 measured lexical dependence at the **slice** level: `lexicon_hit`
vs `lexicon_free`, a binary derived from a 695-entry list. That is a coarse
instrument. It says the model leans on profanity vocabulary; it says nothing
about words *outside* the lexicon that might carry the same signal.

Phase 02 left a specific hole. Of 213 dev false positives, **118 contain no
profanity or slur token at all** (tag `NOPROF`) — the model fired on something,
and we have never said what. The advisor's hypothesis: frequent non-profane
tokens whose training label distribution skews toward OFF (political, religious
or identity terms) supply that something.

This phase measures whether those tokens exist and whether they are
disproportionately present in those 118 rows. It does **not** measure whether
the model used them — see C6-10(b).

## Inputs

| Source | Rows | Used for |
|---|---|---|
| `data/coltekin/offenseval-tr-training-v1.tsv` | 31,756 | text + gold labels |
| `data/splits/split_seed42.json` | — | train/dev membership, fingerprint `034415af3a23b388` |
| `data/lexicon/karaliste.txt` | 695 | frozen lexicon |
| `results/02_failure_analysis/fp_function_tags.json` | 213 | FP ids + per-row function tags |

`src.lexicon.tokens` is **imported**, not reimplemented, so tokenisation is
byte-identical to every slice definition in the project.

---

## Pre-registration

Written and committed **before any token count exists**. Not to be revised after
seeing results.

### C6-1 — data roles

Token–label statistics are computed on the **training split only** (26,992
rows). Dev is used for exactly two things: to locate rows already tagged in
phase 02, and to count how often a *train-derived* token set appears in them. No
ranking, threshold, or token list in this phase is derived from dev. The
official test set stays SPENT; `load_coltekin_test()` is not called.

This direction of travel is what makes step 3 interpretable: the token set is
fixed by data the model trained on, then applied to held-out errors.

### C6-2 — unit of counting

**Document frequency.** `df(t)` = number of training rows containing `t` at
least once; `off_df(t)` = number of those rows labelled OFF;
`P(OFF|t) = off_df(t)/df(t)`. Total occurrence counts are reported as a column
but are not used for ranking or for any probability: a row that repeats a token
still carries one label.

### C6-3 — candidate pool

The **top 200 tokens by `df`**, as instructed.

### C6-4 — ranking statistic

Raw frequency is uninformative — function words dominate it — so the pool is
ranked by deviation from the base rate, weighted by frequency. Two weightings
are reported; the first is primary.

* **Primary — binomial z:** `z(t) = (p̂ − p₀) / sqrt(p₀(1−p₀)/df(t))`, where
  `p₀` is the training base rate **computed, not assumed** (the advisor's 0.193
  is checked against it, not substituted for it). This is a √df weighting: it
  asks whether the skew exceeds sampling noise. At fixed `p̂` it is monotone
  increasing in `df`, so a low-frequency token cannot top the list unless its
  skew is genuinely extreme.
* **Secondary — excess OFF rows:** `E(t) = off_df(t) − df(t)·p₀`, a linear
  weighting answering a different question: how much of the corpus's OFF mass
  this token accounts for.

Tables are ordered by `z` descending (OFF direction) or ascending (NOT
direction), with `E` and the lift `p̂/p₀` as columns. Function words sit near
`p₀` and fall to the middle of both orderings, which is the intended behaviour.

### C6-5 — what "skews strongly" means

Declared numerically, in advance, because "strongly" is otherwise decided after
seeing the list.

200 tokens are tested. Bonferroni at two-sided α = 0.05 gives per-test
α = 2.5 × 10⁻⁴, i.e. **|z| ≥ 3.66**. A significance threshold alone would admit
high-frequency tokens with a trivial skew, so an effect floor is required too:

* **strong-OFF:** `z ≥ +3.66` **and** `p̂ ≥ 1.5 p₀`
* **strong-NOT:** `z ≤ −3.66` **and** `p̂ ≤ p₀/1.5`

### C6-6 — lexicon membership of a token

A token is **in-lexicon** iff `lexicon.hit_root(t, lex)` — the adopted matcher,
any lexicon root of length ≥ 3 prefixing the token.

Exact set membership is reported as a separate column but is **not** used for
grouping. Grouping on exact match would push inflected profanity
(`aptallara`, `sikeyim`) into the "not in the lexicon" group and manufacture the
very finding this phase is testing for. Using the stronger matcher shrinks
group 2 and argues against our own hypothesis, which is why it is the honest
choice — the same reasoning that fixed `hit_root` as the slice definition in
phase 01.

Tokens whose *only* match is a `SUSPECT_ROOTS` entry (`augment.SUSPECT_ROOTS`,
demonstrated false-match roots such as `allah`, `ana`, `mal`) are reported
separately, because that set is exactly where a lexical-hit label is least
trustworthy.

### C6-7 — the step-3 test, declared before computing

Row indicator `X(r) = 1` iff `r` contains at least one token from **group 2**
(the strong-OFF, non-lexicon set from C6-5/C6-6).

* **A** = the 118 dev false positives tagged `NOPROF` in phase 02.
* **B** = correctly-classified dev NOT rows (true negatives), derived as
  dev gold-NOT minus the 213 FP ids — no prediction dump required, since a
  gold-NOT row is either a false positive or a true negative.

`B` is **reweighted** to `A`'s joint distribution over
(in-lexicon-row status × token-count quartile). Length matching is not optional
dressing: a longer row contains more tokens and so is mechanically more likely
to contain any given token, and FP rows may differ in length from TN rows.
Quartile edges come from `A`.

Reported quantity: `mean X(A) − mean X(B_weighted)`, with a 95 % percentile
bootstrap CI, 10,000 resamples, seed 42, resampling A and B independently
(unpaired — disjoint row sets).

**Interpretation is fixed now, not after:**

* **support** — difference > 0 and the CI excludes 0;
* **no support** — the CI includes 0, or the difference is ≤ 0.

A no-support result is a result. It closes the question of whether non-lexicon
topic vocabulary accounts for the 118, and it gets written up as such.

### C6-8 — sensitivities, planned rather than discovered

Run and reported whatever they show:

1. **Wider pool.** Repeat with candidates = all tokens with `df ≥ 30` instead of
   the top 200, same z and effect thresholds (Bonferroni recomputed for the
   larger test count). The top-200 cut is the advisor's framing, not a
   principled vocabulary boundary.
2. **No matching.** Repeat the step-3 comparison unweighted, to show what the
   matching is doing.
3. **Group-3 control.** The same comparison using strong-**NOT** tokens. If the
   118 show elevated rates of *both* directions, the effect is about row length
   or register, not about OFF-skewed vocabulary.

### C6-9 — class balance

Report the OFF/NOT ratio overall and within each slice, on train and dev
separately, and state plainly whether the 19.3 % base rate could itself produce
what phases 01–03 attribute to lexical dependence.

### C6-10 — limitations known before the run

Recorded now so they are not presented later as discoveries.

* **(a)** The `NOPROF` tag is one annotator's judgment (the assistant's), from
  a single unadjudicated pass. Step 3 conditions entirely on it.
* **(b) The inferential ceiling.** Co-occurrence between a train-skewed token
  and a dev error shows that the signal was *available*; it does not show the
  model used it. Establishing use requires attribution or ablation, neither of
  which is in scope here. Every statement in the findings must respect that
  ceiling — "consistent with", not "because of".
* **(c)** Unigram statistics cannot see negation, quotation, or composition —
  precisely the phenomena phase 02 tagged as `META`/`NEG`/`QUOT`.
* **(d)** `P(OFF|t)` is a corpus property. It reflects the annotation
  convention (Çöltekin's, adopted as given) as much as it reflects language.

### C6-11 — no intervention

Measurement only. Nothing produced here may enter training, alter the frozen
lexicon, or define a new slice used in a headline number. The ranked table is
evidence, not a feature list.

---

## Outputs

`results/06_lexical_analysis/` — `token_stats.json` (ranked table, aggregates
only), `findings.md`, and an appended row in `docs/RESULTS_LOG.md`. Row text
stays out of git as always; tokens and counts are aggregates and are committed.
