# M5 — Degrading Sarcasm (D1)

**Type:** detection
**Owner:** _assign_
**Status:** GATED. Do not start implementation until section 2 passes.

---

## 1. Objective

Catch abuse whose **literal polarity is positive** but whose intent is to humiliate.

```
"Zekânı hayranlıkla izliyorum, gerçekten."     → literal praise, actual contempt
"Bu kadar 'derin' bir yorum yapman etkileyici." → same
```

---

## 2. Entry gate — do this before writing any code

**Check dataset availability first.** The main Turkish sarcasm corpus is recent and distributed on request. Contact the authors. Then, one of three outcomes:

| Outcome | Action |
|---|---|
| Corpus granted | Proceed with full plan. |
| Not granted | Fall back to the smaller public irony dataset. All results are labelled **exploratory** because the confidence intervals will be wide. |
| Neither available | **Drop the D1 claim entirely** from the project. |

The rule behind this: claiming sarcasm coverage with no evaluation set is the easiest thing for a judge to break. Either you have a slice with a declared agreement number, or you do not make the claim. Silence is an acceptable outcome for this module.

Be careful with dataset identity — there are at least two distinct small Turkish irony datasets with different sizes floating around in citations. Record the exact name, version and size of whatever you use.

---

## 3. The originality angle — read this before you scope the work

The main Turkish sarcasm corpus **deliberately excluded entries whose primary function was insult or profanity**. That means the intersection of *sarcastic* and *degrading* is untouched in Turkish.

So: you are not building "a Turkish sarcasm detector" — that space is occupied by several published works and a doctoral thesis, and a judge will match it in one search. You are building **sarcasm as a carrier of abuse**, which nobody has done in Turkish. Frame the module that way in the report.

---

## 4. The labelling rule that keeps D1 from eating C

> A case is **D1 only if a literally positive element exists inside the sentence** — a compliment, an exclamation, laughter. That is polarity inversion.
>
> **No inversion → the case is C, not D1.**

Without this rule, D1 absorbs the entire implicit family and annotation agreement collapses. Write it into the annotation guideline verbatim.

Related warning: the reference functional test suite for hate speech **deliberately excluded humour** because there was no consensus on how to judge it. You are working in a zone that a major reference declared undecidable. Expect low agreement and declare it up front rather than discovering it later.

---

## 5. Approach

Sequential transfer: pre-train on the sarcasm corpus, then fine-tune on the offensive task. Implemented as a third head on the shared M3 encoder, not a separate model.

The English reference for sarcasm-transfer into abuse detection is a preprint reporting a recall gain of roughly +9.7 points on an abuse benchmark. Treat that as a plausibility argument, not as a target.

Reported context effect in the Turkish sarcasm corpus is small — accuracy around 0.73 without title context, 0.76 with it. A gain of about three points on 1,515 samples is inside the noise for your purposes. Do not build a context mechanism on the strength of it.

---

## 6. Contract

**Reads:** `ctx.text` (raw — sarcasm markers are often in the original punctuation and casing)

**Writes:** `out.content_scores` for `D1`

**Never** sets `threshold` or `fired`.

---

## 7. The critical negative control

Your precision guard is **benign sarcasm aimed at things, not people**:

```
"Harika, otobüs yine gelmedi."          → sarcastic, not abusive
"Bu program mükemmel çalışıyor tabii."  → sarcastic, target is software
```

A D1 head that fires on these is useless. This control set is mandatory and its size must be comparable to the positive slice — not a token handful.

---

## 8. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Claiming D1 coverage without an evaluation slice | Easiest point for a judge to break. |
| Presenting "Turkish sarcasm detection" as the contribution | Occupied space; several published works plus a thesis. |
| Hiding wide confidence intervals | Small corpus means wide CIs. Publish them and label the results exploratory. |
| Building a context model on the +3-point finding | Too small, on too few samples, and a separate published Turkish result found context **reduced** recall on offensive detection. |
| Letting D1 and C compete for the same cases | Apply the polarity-inversion rule. |

---

## 9. Metrics this module must produce

- Recall on the D1 slice with CIs.
- **Precision on the benign-sarcasm control set** — this number gates acceptance, not recall.
- Annotation agreement on the D1 slice, reported per function. If agreement is below the declared gate, the results ship as exploratory.
- Confusion count between D1 and family C, to prove the polarity rule is working.

---

## 10. Acceptance criteria

- [ ] Availability gate resolved and recorded, with the exact dataset name, version and size.
- [ ] Polarity-inversion rule written into the annotation guideline.
- [ ] Benign-sarcasm control set exists, comparable in size to the positive slice.
- [ ] Precision on the control set reported **before** recall in the results file.
- [ ] Agreement number published, however low.
- [ ] Results labelled exploratory if the fallback dataset was used.
- [ ] D1↔C confusion count reported.

---

## 11. Definition of done

Either: the gate passed, the control set holds, and the numbers ship with their CIs and their exploratory label. Or: the gate failed and the D1 claim is formally dropped from the project, with the reason written in the report. Both are successful outcomes for this module.
