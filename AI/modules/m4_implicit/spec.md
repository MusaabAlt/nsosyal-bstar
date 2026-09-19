# M4 — Implicit Abuse (C1–C5)

**Type:** detection
**Owner:** Musaab
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

## 3. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| `C1` stereotyping, `C2` inferiority and dehumanisation, `C3` coded and veiled expression, `C4` incitement, `C5` defamation — scored by M3's third head; M4 owns their thresholds and the slice repair (ADR-006) | explicit profanity → M1 / M3 |
| Abuse whose harm needs an inference step to see | direct abuse with no profane root → M3's B head, see the boundary rule below |
| The lexicon-free slice, where the project's central result lives | degrading sarcasm → M5, decided by polarity inversion |
| | the target of the abuse → M6 |

**The B/C boundary — write this into the annotation guideline.**

The line is not "has a swear word" — neither family does. The line is whether
the harm is **stated** or **implied**:

- **B** is a direct, literal insult aimed at the addressee. Reading it requires
  no inference. `Bu suratla aynaya nasıl bakıyorsun` is B1: the insult is on
  the surface.
- **C** carries its harm in a proposition the reader has to reconstruct.
  `Onlardan başka ne beklenir` is C1: nothing in it is literally an insult, and
  the harm only exists once you supply the implied claim.

Operational test for the annotator: if you can write the harmful claim in the
form `<target> {is / does} <predicate>` and that claim is **not** present in
the sentence itself, it is C. If the claim is written out in the sentence, it
is B.

**The C/D boundary.** A case with a literally positive element — praise,
enthusiasm, laughter — is D1, not C. No polarity inversion means C. This rule
lives in M5's spec and is repeated here because the two families compete for
the same borderline cases and the rule must read identically in both.

**Also out of scope:**

- **Retraining the encoder for stage 1.** Stage 1 is a decision-layer change.
  It touches no weights. That is why it is safe and why it is already measured.
- **Inventing implicit-hate training data.** Counterfactual augmentation was
  attempted in this project, measured, and reported as a failure. Generating
  examples is not the mechanism here; selecting existing ones is.
- **Deciding anything.** M4 emits no scores: C1–C5 come from M3's C head
  (ADR-006). The threshold that repairs the slice lives in
  `decision/thresholds.yaml`, in the rows M4 owns, not in this module.

---

## 4. What it must do

**Stage 1 — threshold repair.** Port the cost-derived rule into the decision layer configuration. Single adapted parameter. No lexicon lookup at inference time. This stage is already proven; the work is integration and re-verification, not invention. It is the single global threshold on M3's binary offensive score (`binary_offensive` in `decision/thresholds.yaml`), exactly as measured (ADR-006).

**Stage 1b — signal-conditioned variant.** The same threshold conditioned on `m1_lexicon.lexicon_hit` (`threshold_when`). It is a variant, not the current design: it replaces stage 1 only after it has been measured against stage 1 at equal coverage (ADR-006).

**Stage 2 — influence-function hardening.** Mine a small set of veiled Turkish examples from your own data using two signals: model disagreement between channels, and low confidence inside the lexicon-free slice. Then use influence functions to select which *training* examples actually move the decision on those cases, and retrain on that selection. The model retrained is M3's encoder, which carries the C head (ADR-006).

The English reference for this protocol reports recall on veiled examples going from roughly 1% to 51%. Whether it transfers to Turkish is an open question, and answering it **in either direction** is a publishable result.

### 4.1 Named tools for stage 2

Influence functions are the mechanism, and the exact method matters less than
the constraint: full Hessian-based influence does not fit a CPU budget on a
BERT-sized model. Use a checkpoint-based approximation.

| Tool | What it gives | Constraint |
|---|---|---|
| `captum.influence` (TracInCP, SimilarityInfluence) | Checkpoint-based influence on plain PyTorch models. Maintained, documented, no custom training loop required | Needs saved checkpoints across training. Plan that before you train, not after |
| `FastIF` | Scalable approximation for larger candidate pools | Heavier to set up; only worth it if the candidate pool is large |
| The original release accompanying the veiled-abuse paper | The exact protocol the 1% → 51% figure came from | Verify it still runs on a current PyTorch before committing to it |

Evaluate one, record which and why in the protocol file, and do not switch
mid-experiment. Whichever you pick, the mechanism is example **selection** from
existing training data — not example generation.

Heavy dependencies for the influence tooling go in `modules/m4_implicit/requirements.txt`.
The retrained encoder is an M3 artifact: it gets its own row in `artifacts/MANIFEST.md`
with its own thresholds, as M3's artifact discipline requires (ADR-006).


---

## 5. Contract

**Reads:** `ctx.signals["m3_encoder"]` — `raw_score`, `norm_score` and `artifact`, exactly what M3 publishes (M3 spec §4). Nothing else: M3's C1–C5 content scores are not visible to another module.

**Writes:** no content scores. C1–C5 are M3's content (ADR-006). M4's deliverables are the `C1`–`C5` and `binary_offensive` rows of `decision/thresholds.yaml` and the slice repair.

**Publishes (signals, ADR-006 amendment 2026-09-19):** what stage 1 runs on, read from the three M3 signals above — `stage`, `stage1_input` / `stage1_input_present`, `m3_artifact` / `stage1_derived_for` / `stage1_artifact_match` / `stage1_protocol` (the threshold's
derivation record; since 0.3.0 the rule-v4 artifact), and `norm_minus_raw` (the channel disagreement of §4). Information only: no decision-layer row reads them, and M4 compares none of them with anything.

**Never** sets `threshold` or `fired`.

---

## 6. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Claiming high accuracy on implicit abuse | Published Turkish figures for implicit categories are extremely low — around F1 0.08 for exclusionary/discriminatory speech and 0.17 for exaggeration/generalization, against 0.44 for explicit threat. The published ceiling for covert toxicity detection is around AUC 0.60. Any high number here will be read as a measurement error, not an achievement. |
| Blind data augmentation | Counterfactual augmentation was already attempted in this project, measured, and reported as a failure. Repeating it without a different mechanism repeats a known negative. |
| Competing head-on with published Turkish implicit-hate systems | Two labs have published contrastive/domain approaches with expert-annotated data. Direct competition there is a losing position. Cite their numbers as the problem statement instead. |
| Reporting a recall gain without its precision cost | The repair buys recall with precision. Both go in the same sentence or the number is dishonest. |
| Comparing methods at different coverage | A gain may be bought by deferring more. Compare at equal coverage on the risk–coverage curve. |
| Translate-train from English implicit-hate corpora as the main path | Implicit categories collapse across languages in the published multilingual results. Allowed only as a weak comparison baseline. |

---

## 7. Metrics this module must produce

- **Recall on the lexicon-free slice, before and after**, with CIs, and with the precision cost stated alongside.
- **A pre-registered precision budget.** Written into `protocols/` before the first number. Exceeding it means: keep stage 1, document stage 2 as a measured negative.
- **Risk–coverage curve before and after.** Compare at equal coverage.
- **Per-code breakdown** across C1–C5 where slice size allows; where it does not, say so rather than averaging.

---

## 8. Labelling and sample size

The critical evaluation slice is lexicon-negative positives. Sample size drives your confidence interval width:

| positives in slice | approximate CI half-width |
|---|---|
| 400 | ±4.8 points |
| 800 | ±3.4 points |

Decide the target before labelling. Mine candidates from your own data by model disagreement and low confidence — this is far cheaper than labelling at random and concentrates on the cases that matter.

Annotation must be **prescriptive**: a sealed guideline, annotators applying it, agreement reported per category. For C3 (coded/implicit), require the annotator to be able to write the implied proposition in the form `<target> {is/does} <predicate>`. If they cannot produce it, the case is not C3.

---

## 9. Required fixtures

`fixtures/cases.jsonl` — `{"id": ..., "text": ..., "context": {"signals": {"m3_encoder": {"raw_score": ..., "norm_score": ...}, "m1_lexicon": {"lexicon_hit": true|false}}}, "expected": [...]}` (keys as read by `eval/harness.py`)

**Per code.** Positives for each of C1–C5. Where a code has too few examples to
support a metric, the fixture file records the count and the eval reports
"insufficient sample" — it does not average the code away into the family.

**Slice discipline.** Every fixture carries its slice as
`context.signals.m1_lexicon.lexicon_hit`, and a unit test asserts that it
matches what M1's `lexicon_hit` signal actually returns on that text. The slice is defined by the signal, never by the category: a
stereotype that happens to contain a swear word belongs to `lexicon_hit`, and
filing it under `lexicon_free` because "C means implicit" corrupts the number
the whole project rests on.

**Boundary pairs.** Matched pairs that differ only across a boundary:
- a B1 and a C2 expressing the same contempt, one stated and one implied
- a C-family case and a D1 case with the same content, one with and one without
  a literally positive element

These pairs are how you prove the boundary rules are working rather than
asserting they are.

**Negative controls — must not fire:**
- counter-speech quoting a stereotype in order to reject it
- academic or journalistic discussion of a stereotype
- self-directed criticism
- a factual statement about a group with no evaluative predicate
- negation that flips the polarity

Implicit-abuse detectors fail on these more than on anything else, and a C-family
false positive on counter-speech is the single most damaging error this system
can make in public.

**Frozen dev slice.** The evaluation slice used for the before/after numbers is
committed with its size, its labelling date, and its per-category agreement.
Once a number is published against it, it does not change.

**Protocol precondition.** A test asserts that `protocols/` contains the
pre-registered precision budget with a commit timestamp **earlier** than the
first stage-2 result file. A budget written after the result is not a budget.

**Edge inputs.** Empty string, whitespace, 5000 characters.

---

## 10. Acceptance criteria

- [ ] Stage 1 integrated into `decision/thresholds.yaml` and re-verified on the frozen dev set.
- [ ] Stage 1b, if proposed, measured against stage 1 at equal coverage before it replaces stage 1.
- [ ] Pre-registered precision budget committed **before** any stage-2 number exists, with a timestamp in version control.
- [ ] Recall before/after with CIs, precision cost in the same reported sentence.
- [ ] Risk–coverage comparison at equal coverage.
- [ ] Evaluation slice labelled with agreement reported per category.
- [ ] Negative result, if that is the outcome, written up in full — that satisfies this module.
- [ ] No use of the closed official test set. Query count on it stays at one, documented.

---

## 11. Research pointers

- The influence-function hardening protocol for veiled abuse (EMNLP-published) — read the method section closely; the mechanism is example *selection*, not example generation.
- Contrastive learning with implication pairs — promising but requires Turkish implication pairs that do not exist. Keep it as a future path, not a current one.
- Published Turkish implicit-hate results — use them as the problem statement in the report.

---

## 12. Definition of done

Stage 1 is integrated and verified, stage 2 has a pre-registered budget and a measured outcome in either direction, and the precision cost is never separated from the recall gain.
