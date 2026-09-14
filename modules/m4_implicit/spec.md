# M4 — Implicit Abuse (C1–C5)

**Type:** detection
**Owner:** _assign_
**Note:** this module carries the project's core scientific claim. Read the whole spec before writing code.

---

## 1. Objective

Raise recall on the **lexicon-free slice** — offensive content that contains no profane root — without retraining the base model beyond what is explicitly budgeted.

---

## 2. The measured starting point

These numbers already exist in the submitted report. They are the baseline every change is measured against. Do not re-derive them casually; if you re-measure, re-measure on a frozen set with CIs.

| Quantity | Value |
|---|---|
| Offensive posts with no lexicon match | **63.5%** |
| Recall, lexicon-hit slice (dev) | **0.8930** |
| Recall, lexicon-free slice (dev) | **0.5628** |
| Slice difference (dev) | **+0.3301** [+0.2771, +0.3827] |
| Slice difference (held-out test, one pass) | **+0.3970** [+0.3418, +0.4542] |
| ROC-AUC, lexicon-free | **0.8962** |
| ROC-AUC, lexicon-hit | **0.9306** |

The last two rows are the whole thesis: **the model ranks lexicon-free abuse almost as well as it ranks profanity. It fails only at the decision threshold.** That is why the repair belongs at the decision layer, not inside the model.

Existing repair (stage 1, already measured on the EVAL half, n = 2382):

| | before | after |
|---|---|---|
| lexicon-free recall | 0.5180 | **0.6367** |
| overall offensive precision | 0.7512 | **0.6509** |
| slice gap | 0.3501 | 0.2754 |

An analytic control with no tuned parameter is also on record and lands close to the adapted threshold — that closeness is a calibration indicator and should stay in the report.

---

## 3. What it must do

**Stage 1 — threshold repair.** Port the cost-derived rule into the decision layer configuration. Single adapted parameter. No lexicon lookup at inference time. This stage is already proven; the work is integration and re-verification, not invention.

**Stage 2 — influence-function hardening.** Mine a small set of veiled Turkish examples from your own data using two signals: model disagreement between channels, and low confidence inside the lexicon-free slice. Then use influence functions to select which *training* examples actually move the decision on those cases, and retrain on that selection.

The English reference for this protocol reports recall on veiled examples going from roughly 1% to 51%. Whether it transfers to Turkish is an open question, and answering it **in either direction** is a publishable result.

---

## 4. Contract

**Reads:** `ctx.text`, `ctx.signals` (M3's published scores are read from `ctx.signals["m3_encoder"]`; a module never sees the result)

**Writes:** `out.content` for `C1`–`C5`

**Never** sets `threshold` or `fired`.

---

## 5. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Claiming high accuracy on implicit abuse | Published Turkish figures for implicit categories are extremely low — around F1 0.08 for exclusionary/discriminatory speech and 0.17 for exaggeration/generalization, against 0.44 for explicit threat. The published ceiling for covert toxicity detection is around AUC 0.60. Any high number here will be read as a measurement error, not an achievement. |
| Blind data augmentation | Counterfactual augmentation was already attempted in this project, measured, and reported as a failure. Repeating it without a different mechanism repeats a known negative. |
| Competing head-on with published Turkish implicit-hate systems | Two labs have published contrastive/domain approaches with expert-annotated data. Direct competition there is a losing position. Cite their numbers as the problem statement instead. |
| Reporting a recall gain without its precision cost | The repair buys recall with precision. Both go in the same sentence or the number is dishonest. |
| Comparing methods at different coverage | A gain may be bought by deferring more. Compare at equal coverage on the risk–coverage curve. |
| Translate-train from English implicit-hate corpora as the main path | Implicit categories collapse across languages in the published multilingual results. Allowed only as a weak comparison baseline. |

---

## 6. Metrics this module must produce

- **Recall on the lexicon-free slice, before and after**, with CIs, and with the precision cost stated alongside.
- **A pre-registered precision budget.** Written into `protocols/` before the first number. Exceeding it means: keep stage 1, document stage 2 as a measured negative.
- **Risk–coverage curve before and after.** Compare at equal coverage.
- **Per-code breakdown** across C1–C5 where slice size allows; where it does not, say so rather than averaging.

---

## 7. Labelling and sample size

The critical evaluation slice is lexicon-negative positives. Sample size drives your confidence interval width:

| positives in slice | approximate CI half-width |
|---|---|
| 400 | ±4.8 points |
| 800 | ±3.4 points |

Decide the target before labelling. Mine candidates from your own data by model disagreement and low confidence — this is far cheaper than labelling at random and concentrates on the cases that matter.

Annotation must be **prescriptive**: a sealed guideline, annotators applying it, agreement reported per category. For C3 (coded/implicit), require the annotator to be able to write the implied proposition in the form `<target> {is/does} <predicate>`. If they cannot produce it, the case is not C3.

---

## 8. Acceptance criteria

- [ ] Stage 1 integrated into `decision/thresholds.yaml` and re-verified on the frozen dev set.
- [ ] Pre-registered precision budget committed **before** any stage-2 number exists, with a timestamp in version control.
- [ ] Recall before/after with CIs, precision cost in the same reported sentence.
- [ ] Risk–coverage comparison at equal coverage.
- [ ] Evaluation slice labelled with agreement reported per category.
- [ ] Negative result, if that is the outcome, written up in full — that satisfies this module.
- [ ] No use of the closed official test set. Query count on it stays at one, documented.

---

## 9. Research pointers

- The influence-function hardening protocol for veiled abuse (EMNLP-published) — read the method section closely; the mechanism is example *selection*, not example generation.
- Contrastive learning with implication pairs — promising but requires Turkish implication pairs that do not exist. Keep it as a future path, not a current one.
- Published Turkish implicit-hate results — use them as the problem statement in the report.

---

## 10. Definition of done

Stage 1 is integrated and verified, stage 2 has a pre-registered budget and a measured outcome in either direction, and the precision cost is never separated from the recall gain.
