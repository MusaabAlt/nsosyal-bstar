# Phase 08 — word-level lexical dependence

Run 17 Aug 2026. Measurement only: no training, no GPU, no forward pass, no
intervention proposed. Pre-registered in `phases/08_lexical_analysis.md`
(commit `b127d44`), written before any token count existed. Every number here
comes from `results/08_lexical_analysis/token_stats.json`.

Token–label statistics are computed on the **training split only** (26,992
rows). Dev supplied 118 row ids already tagged in phase 02 and nothing else.
The official test set was not opened.

---

## 1. Verdict

The advisor's hypothesis is **supported in structure and refuted in content.**

Non-lexicon tokens with a strong OFF skew in training **do** occur
disproportionately in the 118 no-profanity false positives: 39.8 % of them carry
one, against 19.2 % of length-and-slice-matched true negatives — a difference of
**+0.2066 [+0.1216, +0.2960]**, which is the pre-registered SUPPORT outcome.

But the tokens driving it are not what the hypothesis predicted. The top-200
list contains **two** political or identity terms (`türk`, `oy`) and they carry
no signal on their own (+0.0111 [−0.0138, +0.0437], the pre-registered NO
SUPPORT outcome). What dominates is **second-person address and person deixis** —
`sizin, sen, siz, senin, sizi, bak, lan, adam, bunlar, onlar`. The model appears
to have learned that *being addressed* predicts OFF, independently of any
profanity.

This is a partial account, not a complete one. Even at the widest vocabulary
tested, **47 of the 118 (39.8 %) carry no strongly-OFF-skewed token at all** and
remain unexplained.

---

## 2. Class balance (advisor's second question)

| split | slice | n | OFF | NOT | OFF rate | OFF:NOT |
|---|---|---:|---:|---:|---:|---|
| train | overall | 26,992 | 5,211 | 21,781 | 0.1931 | 1 : 4.18 |
| train | lexicon_hit | 3,404 | 1,884 | 1,520 | 0.5535 | 1 : 0.81 |
| train | lexicon_free | 23,588 | 3,327 | 20,261 | 0.1410 | 1 : 6.09 |
| dev | overall | 4,764 | 920 | 3,844 | 0.1931 | 1 : 4.18 |
| dev | lexicon_hit | 614 | 355 | 259 | 0.5782 | 1 : 0.73 |
| dev | lexicon_free | 4,150 | 565 | 3,585 | 0.1361 | 1 : 6.35 |

The computed training base rate is **0.193057**, matching the advisor's stated
0.193.

**Could the 19.3 % imbalance itself be driving what we attribute to lexical
dependence?** Three separate answers, because the question has three parts:

1. **On the absolute level of `lexicon_free` OFF-recall — yes, plausibly, and we
   cannot rule it out.** Training is 1:4.18 against the positive class with no
   class weighting and a threshold fixed at 0.5. That configuration depresses
   recall on the minority class generally. We never trained a class-weighted or
   threshold-tuned variant, so the contribution of imbalance to the 0.5628 figure
   is unmeasured. This is a real gap in the study, and it is the strongest form
   of the advisor's point.
2. **On the *gap* between slices — no.** One model, one threshold, evaluated on
   two disjoint subsets. A global class imbalance depresses recall on both slices
   alike; it cannot by itself create a differential between them.
3. **On the slice-conditional priors — the question dissolves.** The corpus
   prior is 0.5535 OFF given a lexicon hit and 0.1410 given none — a 3.9× ratio.
   That *is* lexical dependence, measured as a corpus property rather than as a
   model behaviour. "The model learned the prior attached to profanity tokens"
   and "the model depends on profanity tokens" are not competing explanations;
   they are the same statement at different levels of description. Nothing in
   this project distinguishes them, and the report should not claim otherwise.

---

## 3. Token frequency and label skew (step 1)

Pool: the top 200 tokens by document frequency in train. Counting is
**document-frequency** — a row containing a token twice contributes one row and
one label (C8-2).

**Weighting used, and why.** Ranking is by the **binomial z-score**
`(p̂ − p₀)/√(p₀(1−p₀)/df)`, a √df weighting. Raw frequency is uninformative
because function words dominate it, and raw lift is uninformative in the other
direction because it is maximised by rare tokens. The z-score is monotone in `df`
at fixed `p̂`, so a low-frequency token cannot reach the top unless its skew is
genuinely extreme. **Excess OFF rows** `E = off_df − df·p₀` is reported alongside
as a linear-weighted secondary, answering a different question — how much of the
corpus's OFF mass a token accounts for.

The two orderings disagree in an instructive way. By `E`, the top entries are
`user` (+282.0) and `bu` (+255.1) — a placeholder and a demonstrative, both with
`df` in the thousands and lifts near 1. Both fall into the *unremarkable* group
under the declared thresholds. High-frequency tokens accumulate large absolute
excesses from trivial skews, which is exactly why the z-score is primary.

Significance threshold: **|z| ≥ 3.6623** (Bonferroni over 200 tests, two-sided
α = 0.05), plus an effect floor of `p̂ ≥ 0.2896` (OFF) or `p̂ ≤ 0.1287` (NOT).
Both declared in advance.

---

## 4. The three-way split (step 2)

### Group 1 — in the frozen karaliste (`hit_root`): 2 tokens

| token | df | OFF | NOT | P(OFF\|t) | lift | z |
|---|---:|---:|---:|---:|---:|---:|
| amk | 269 | 257 | 12 | 0.9554 | 4.95 | 31.68 |
| allah | 668 | 186 | 482 | 0.2784 | 1.44 | 5.59 |

Only two lexicon entries are frequent enough to reach the top 200. `allah` is a
`SUSPECT_ROOTS` member — the phase-02 false-match root — and its modest 1.44 lift
is consistent with that: it is a religious formula far more often than an insult.

### Group 2 — not in the lexicon, skewing strongly OFF: 19 tokens

| token | df | OFF | NOT | P(OFF\|t) | lift | z | excess |
|---|---:|---:|---:|---:|---:|---:|---:|
| aq | 215 | 212 | 3 | 0.9860 | 5.11 | 29.46 | 170.5 |
| sizin | 375 | 170 | 205 | 0.4533 | 2.35 | 12.77 | 97.6 |
| bunlar | 233 | 107 | 126 | 0.4592 | 2.38 | 10.29 | 62.0 |
| lan | 217 | 94 | 123 | 0.4332 | 2.24 | 8.96 | 52.1 |
| sen | 1,106 | 331 | 775 | 0.2993 | 1.55 | 8.95 | 117.5 |
| adam | 405 | 147 | 258 | 0.3630 | 1.88 | 8.66 | 68.8 |
| siz | 480 | 167 | 313 | 0.3479 | 1.80 | 8.60 | 74.3 |
| senin | 534 | 180 | 354 | 0.3371 | 1.75 | 8.43 | 76.9 |
| bak | 320 | 116 | 204 | 0.3625 | 1.88 | 7.68 | 54.2 |
| nasıl | 858 | 253 | 605 | 0.2949 | 1.53 | 7.56 | 87.4 |
| türk | 218 | 83 | 135 | 0.3807 | 1.97 | 7.02 | 40.9 |
| niye | 339 | 115 | 224 | 0.3392 | 1.76 | 6.82 | 49.5 |
| sizi | 269 | 90 | 179 | 0.3346 | 1.73 | 5.88 | 38.1 |
| oy | 205 | 71 | 134 | 0.3463 | 1.79 | 5.56 | 31.4 |
| kendi | 413 | 122 | 291 | 0.2954 | 1.53 | 5.27 | 42.3 |
| onlar | 191 | 64 | 127 | 0.3351 | 1.74 | 4.97 | 27.1 |
| para | 223 | 72 | 151 | 0.3229 | 1.67 | 4.91 | 28.9 |
| ye | 244 | 73 | 171 | 0.2992 | 1.55 | 4.20 | 25.9 |
| belli | 193 | 58 | 135 | 0.3005 | 1.56 | 3.78 | 20.7 |

Five of the nineteen are second-person pronouns. Adding the address particle
`lan`, the imperative `bak`, the person-reference `adam`, and the out-group
demonstratives `bunlar`/`onlar` gives ten of nineteen in a single semantic
family: **who is being addressed, and how.** Political or identity terms number
two (`türk`, `oy`).

### Group 3 — skewing strongly NOT: 5 tokens

`güzel` (0.1102), `günaydın` (0.0512), `mutlu` (0.0963), `bugün` (0.1128),
`zor` (0.0926). Greetings and positive-affect vocabulary. Used below as a
control.

### Group 0 — unremarkable: 174 of 200

The overwhelming majority of frequent tokens sit inside the thresholds. This is
worth stating: the skew is concentrated in a small vocabulary, not diffuse.

### `aq` — a defect in our slice definition, found here

`aq` is an **exact entry in the frozen karaliste** yet `hit_root` never fires on
it, because `MIN_ROOT_LEN = 3` and the token is two characters. Under the
declared grouping rule (C8-6) it therefore lands in group 2. It is left there
rather than quietly reassigned, and §7 records the consequence.

---

## 5. Connecting to the actual errors (step 3)

* **A** = the 118 phase-02 false positives tagged `NOPROF`.
* **B** = 3,631 true negatives, derived as dev gold-NOT (3,844) minus the 213
  false-positive ids. No prediction dump was needed.
* B is reweighted to A's joint distribution over (lexicon-hit status × token-count
  quartile), edges `[10, 16, 26]` taken from A.

Matching is not cosmetic: A rows are substantially longer (median 16 tokens,
mean 19.14) than B rows (median 11, mean 14.40), and a longer row is
mechanically more likely to contain any given token. 100 % of A's mass sits in
strata B can cover, so nothing was dropped.

An independent cross-check on the join: 6 of the 118 sit on lexicon-hit rows,
exactly matching phase 02's separately-recorded `counts_lexicon_hit_47` NOPROF
count of 6.

| comparison | tokens | rate in A | rate in B (matched) | difference | verdict |
|---|---:|---:|---:|---|---|
| **group 2 (pre-registered)** | 19 | 0.3983 (47/118) | 0.1917 | **+0.2066 [+0.1216, +0.2960]** | **SUPPORT** |
| wider pool, df ≥ 30 | 104 | 0.6017 (71/118) | 0.3000 | +0.3017 [+0.2187, +0.3784] | SUPPORT |
| **group 3 control (strong-NOT)** | 5 | 0.0847 (10/118) | 0.0879 | **−0.0032 [−0.0454, +0.0429]** | **null** |

The control is the load-bearing row. If the 118 were merely longer, odder, or
more emotionally charged than average, they would show elevated rates of *both*
skew directions. They do not: strong-NOT tokens appear at the matched-baseline
rate. The effect is specific to OFF-skewed vocabulary.

Unmatched differences are larger throughout (+0.2361 for group 2), so the
matching removes some of the effect rather than manufacturing it.

Which group-2 tokens actually appear in the 118, by row count: `senin` 11,
`adam` 9, `siz` 7, `sen` 5, `kendi` 4, `nasıl` 4, `türk` 3, `bak` 3, `sizin` 3,
`niye` 3, `onlar` 3, `ye` 2, `sizi` 2, `bunlar` 1. Note `aq` appears in **zero**
of them, which is an independent confirmation that the `NOPROF` tagging was
applied correctly — a row containing `aq` would not have been tagged as carrying
no profanity.

---

## 6. Composition — exploratory, not confirmatory

Everything in this section was decided **after** seeing the ranked list. The
subsets are the assistant's semantic judgment of Turkish tokens, not a
measurement. No verdict is claimed from them; they are reported because the
composition turned out to be the substantive answer and describing it with the
caveat attached is better than omitting it.

| pool | subset | tokens | A | B | matched difference |
|---|---|---:|---:|---:|---|
| top 200 | person / address deixis | 10 | 36/118 | 350/3,631 | +0.1965 [+0.1149, +0.2837] |
| top 200 | political / religious / identity | 2 | 3/118 | 37/3,631 | +0.0111 [−0.0138, +0.0437] |
| df ≥ 30 | person / address deixis | 24 | 40/118 | 410/3,631 | +0.2106 [+0.1263, +0.2982] |
| df ≥ 30 | political / religious / identity | 26 | 23/118 | 112/3,631 | +0.1494 [+0.0825, +0.2224] |

Read carefully:

* At the top-200 vocabulary the advisor's specific hypothesis **fails** — two
  tokens, no detectable effect.
* Widen the vocabulary and political/religious/identity terms *do* show an
  effect (`akp`, `chp`, `hdp`, `pkk`, `fetö`, `atatürk`, `islam`, `israil`,
  `kürt`, `müslüman`, `tayyip`, `vatan`, `şehit`, …). So the hypothesis is not
  wrong, it was tested at the wrong resolution.
* Even there, person deixis is the larger contributor: 40 rows against 23, and a
  difference of +0.2106 against +0.1494.

The political finding also sits directly on the annotation-convention question
already flagged in report §4.4 and §5: if criticism of a party is annotated OFF
in this corpus, then a party name predicting OFF is the convention showing
through the data, not necessarily a model defect. This phase cannot separate
those.

---

## 7. A new limitation, found in passing

`MIN_ROOT_LEN = 3` means five karaliste entries — `ag`, `am`, `aq`, `oc`, `oç` —
can never be matched by `hit_root`. Rows carrying them are filed as
`lexicon_free`.

In dev, **28 of the 565 gold-OFF `lexicon_free` rows (4.96 %) contain one**, and
`aq` alone has P(OFF | token) = 0.9860 in training. These are explicit
abbreviated profanity sitting inside the slice defined as profanity-free.

This is the **opposite** leak to the one `slice_sensitivity.json` measured. That
check removed suspect-root contamination *from* `lexicon_hit` and found the gap
widened by +0.0361. This one puts easy explicit-profanity rows *into*
`lexicon_free`, which inflates `lexicon_free` recall and therefore also
understates the gap.

Bounding the effect: reported `lexicon_free` OFF-recall is 0.5628 = 318/565. If
all 28 leaked rows are correctly classified — the assumption that maximises the
effect, hence an upper bound — recall on the remainder is 290/537 = **0.5400**,
and the gap widens from +0.3301 to **+0.3529**.

This is a **bound, not a measurement.** The per-row outcome for those 28 rows
needs `dev_predictions.csv`, which lives only on the Drive mirror. Both known
slice-definition defects move the headline in the same, conservative direction:
the reported +0.3301 understates the gap under either correction.

No change to the frozen lexicon or to `MIN_ROOT_LEN` follows from this. The
matcher stays frozen; this is recorded as a limitation, per C8-11.

---

## 8. What this does not show

Stated in advance as C8-10(b) and restated because it is the easiest thing to
overclaim. **Co-occurrence between a train-skewed token and a dev error shows
the signal was available. It does not show the model used it.** Establishing use
requires attribution or ablation, neither of which was run. Every claim above is
"consistent with", not "because of".

Further limits, all declared before the run:

* The `NOPROF` tag is one annotator's judgment (the assistant's), from a single
  unadjudicated pass. Section 5 conditions entirely on it.
* Unigram statistics cannot see negation, quotation, or composition — precisely
  the phenomena phase 02 tagged `META` / `NEG` / `QUOT`.
* `P(OFF | token)` is a corpus property and reflects Çöltekin's annotation
  convention as much as it reflects Turkish.
* Sections 6 and 7 are post-hoc and exploratory.
* 47 of the 118 remain unaccounted for even at the widest vocabulary tested.

---

## 9. What this closes and what it opens

**Closed:** "we have no account for the 118" is no longer true. There is now a
measured, pre-registered, control-verified partial account covering roughly 40 %
of them at the top-200 vocabulary and 60 % at df ≥ 30.

**Closed negatively:** the specific hypothesis that political/religious/identity
terms drive the 118 does **not** hold at the frequency band the advisor
proposed. It holds only after widening the vocabulary, and even then it is the
smaller of the two effects.

**Opened:** the model's apparent sensitivity to second-person address is a
finding phases 01–03 could not see, because the slice instrument is binary on
profanity and blind to everything else. Nothing follows from it in this phase —
C8-11 forbids turning it into a feature, and the inferential ceiling in §8
forbids calling it a mechanism.
