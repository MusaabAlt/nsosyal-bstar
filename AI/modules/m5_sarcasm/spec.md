# M5 — Degrading Sarcasm (D1)

**Type:** detection
**Owner:** Abdullah
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

### 2.1 The datasets, identified (PROPOSED by Abdullah 2026-09-16 — awaiting Musaab's approval)

Identification only: nothing has been requested, obtained or trained on. The full record,
with the access request and its outcome, lives in [`GATE.md`](GATE.md).

**Main corpus — SarcasTürk.** Metin, Yılmaz, Erdoğdu, Meydan, Sümer & Keküllüoğlu
(Sabancı University), "SarcasTürk: Turkish Context-Aware Sarcasm Detection Dataset",
SIGTURK 2026 (ACL), pp. 61–71, DOI 10.18653/v1/2026.sigturk-1.6. **1,515 entries** from 98
titles, 774 sarcasm / 741 no-sarcasm, no version number. Shared **only on request by
e-mail** (dilara.kekulluoglu@sabanciuniv.edu, cc ahmet.metin@sabanciuniv.edu) because the
data contains sensitive and offensive language; **no licence is stated**, so terms of use
must be asked for in the same message. It matches every property this section assumes,
including the 0.73 → 0.76 context effect in §6 (fine-tuned BERTurk, entry-only vs.
title-context) and the exclusion of abusive entries in §4.

Two corrections this raises, for Musaab: the corpus is built from **Ekşi Sözlük** entries
with LLM-written context summaries, **not** from news headlines or Zaytung (the Zaytung
resource is Onan & Toçoğlu's larger *satire* corpus); and the exclusion of entries "whose
main function was direct abuse or swearing" is a filtering rule at annotation time, not a
claim that the data is clean — the paper's ethics section warns it still holds uncensored
slurs and sexual content.

**Fallback — IronyTR.** Öztürk, Cemek & Karagöz (METU), "IronyTR: Irony Detection in
Turkish Informal Texts", IJIIT 17(4), 2021, pp. 1–18, DOI 10.4018/IJIIT.289965,
https://github.com/teghub/IronyTR. **600 items**, 300 ironic / 300 non-ironic, publicly
downloadable, no licence file in the repo (the paper says "open for research purposes").

**The identity trap in this section, concretely.** Small Turkish irony sets run to 144
(Dülger 2018), 194 (Taslıoğlu & Karagöz 2017), 220 (Cemek et al., SIU 2020) and 600
(IronyTR). The 220 and the 600 come from the same METU group and share a GitHub
organisation, and are routinely conflated in citations; the 600 is cited as Öztürk, Cemek
& Karagöz (2021), never as Cemek et al. (2020). A count of 1,000 for SarcasTürk refers to
its earlier subset, not the release.

---

## 3. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| `D1` — abuse delivered through a literally positive sentence | implicit abuse with no polarity inversion → M4 |
| Praise, enthusiasm or laughter used to humiliate a person | benign sarcasm aimed at objects, situations or events — this is the control set, not a miss |
| | sarcasm detection as a general capability — occupied space, and not the contribution |
| | humour, jokes and banter → out of scope, see below |
| | who is being mocked → M6 |

**Precedence rule: explicit content wins.** A sarcastic sentence that also
contains a profane root is labelled with its A code, not D1. The content axis
is single-label, and `A2` describes the post more usefully than `D1` does.
`D1` is for abuse that has **no other way** to be caught. Write this into the
guideline; without it, annotators will double-label and the confusion matrix
between A and D will be unreadable.

**Humour is deliberately excluded.** The reference functional test suite for
hate speech left humour out because there was no consensus on how to judge it.
This module does not attempt to succeed where that reference declined to try.
`D1` is not "jokes that offend someone"; it is specifically polarity inversion
used as a delivery mechanism for contempt toward a person.

**Sincere praise is a hard negative, not an edge case.** A model that cannot
separate `Zekânı hayranlıkla izliyorum` said sincerely from the same sentence
said with contempt has learned nothing useful. This separation is what the
control set measures, and it is why precision gates acceptance here rather than
recall.

---

## 4. The originality angle — read this before you scope the work

The main Turkish sarcasm corpus **deliberately excluded entries whose primary function was insult or profanity**. That means the intersection of *sarcastic* and *degrading* is untouched in Turkish.

So: you are not building "a Turkish sarcasm detector" — that space is occupied by several published works and a doctoral thesis, and a judge will match it in one search. You are building **sarcasm as a carrier of abuse**, which nobody has done in Turkish. Frame the module that way in the report.

---

## 5. The labelling rule that keeps D1 from eating C

> A case is **D1 only if a literally positive element exists inside the sentence** — a compliment, an exclamation, laughter. That is polarity inversion.
>
> **No inversion → the case is C, not D1.**

Without this rule, D1 absorbs the entire implicit family and annotation agreement collapses. Write it into the annotation guideline verbatim.

Related warning: the reference functional test suite for hate speech **deliberately excluded humour** because there was no consensus on how to judge it. You are working in a zone that a major reference declared undecidable. Expect low agreement and declare it up front rather than discovering it later.

---

## 6. Approach

Sequential transfer: pre-train on the sarcasm corpus, then fine-tune on the offensive task. Implemented as **m5's own model** with its own artifact, its own row in `artifacts/MANIFEST.md` and its own thresholds in `decision/thresholds.yaml` - not a head on the shared M3 encoder (ADR-003). A failed entry gate disables m5 with zero impact on m3. Heavy dependencies go in `modules/m5_sarcasm/requirements.txt`.

**m5 does not read m3 embeddings, and m3 does not publish them.** There is no shared encoder state between the two modules: m5 runs its own model on `ctx.text`, and no field of the contract carries hidden states or embeddings. A middle path - a separate m5 head on m3's representations - would bring back the artifact entanglement ADR-003 removed, and the contract cannot express it.

**Constraint for the m5 owner: the model must be small or distilled.** A second full BERT-sized pass per channel doubles encoder latency and memory on CPU. Which model meets the `budgets.module_latency_p95_ms.m5_sarcasm` budget is not decided here; the m5 owner resolves it and records the choice and its measurement.

The English reference for sarcasm-transfer into abuse detection is a preprint reporting a recall gain of roughly +9.7 points on an abuse benchmark. Treat that as a plausibility argument, not as a target.

Reported context effect in the Turkish sarcasm corpus is small — accuracy around 0.73 without title context, 0.76 with it. A gain of about three points on 1,515 samples is inside the noise for your purposes. Do not build a context mechanism on the strength of it.

---

## 7. Contract

**Reads:** `ctx.text` (raw — sarcasm markers are often in the original punctuation and casing)

**Writes:** `out.content` for `D1`

**Never** sets `threshold` or `fired`.

---

## 8. The critical negative control

Your precision guard is **benign sarcasm aimed at things, not people**:

```
"Harika, otobüs yine gelmedi."          → sarcastic, not abusive
"Bu program mükemmel çalışıyor tabii."  → sarcastic, target is software
```

A D1 head that fires on these is useless. This control set is mandatory and its size must be comparable to the positive slice — not a token handful.

---

## 9. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Claiming D1 coverage without an evaluation slice | Easiest point for a judge to break. |
| Presenting "Turkish sarcasm detection" as the contribution | Occupied space; several published works plus a thesis. |
| Hiding wide confidence intervals | Small corpus means wide CIs. Publish them and label the results exploratory. |
| Building a context model on the +3-point finding | Too small, on too few samples, and a separate published Turkish result found context **reduced** recall on offensive detection. |
| Letting D1 and C compete for the same cases | Apply the polarity-inversion rule. |

---

## 10. Metrics this module must produce

- Recall on the D1 slice with CIs.
- **Precision on the benign-sarcasm control set** — this number gates acceptance, not recall.
- Annotation agreement on the D1 slice, reported per function. If agreement is below the declared gate, the results ship as exploratory.
- Confusion count between D1 and family C, to prove the polarity rule is working.

---

## 11. Required fixtures

`fixtures/cases.jsonl` — `{"id": ..., "text": ..., "expected": [...], "inversion_span": [start, end] | null}` (keys as read by `eval/harness.py`; `inversion_span` is not read by the harness and is asserted by this module's unit tests)

**D1 positives.** Each one carries `inversion_span` marking the literally
positive element that makes it D1. A positive with no marked inversion span
fails the fixture check — if the annotator cannot point at the inversion, the
polarity rule was not applied and the case is C, not D1.

**Benign-sarcasm control set.** Sarcasm aimed at objects, weather, software,
traffic, a match result. **Size comparable to the positive slice**, not a token
handful. This set produces the precision number that gates acceptance, so an
undersized control set means no acceptance.

**Sincere-praise negatives.** Genuine compliments using the same vocabulary and
the same punctuation patterns as the positives. This is the hardest negative
class and the one most likely to be missing.

**Boundary cases against C.** Implicit abuse with no positive element, asserted
to produce no D1 score. These prove the polarity rule is implemented, not just
written down.

**Boundary cases against A.** Sarcastic sentences containing a profane root,
asserted to carry the A code with D1 not assigned, per the precedence rule.

**Raw-text sensitivity.** Fixtures where the sarcasm marker is in the original
punctuation, casing or emoji — scare quotes, ellipsis, an exaggerated
exclamation, `tabii ki`. Assert the module reads `ctx.text` and not the
normalized channel: de-obfuscation strips exactly the signals this module
depends on.

**Reported speech.** A sarcastic line quoted by someone describing it, asserted
not to fire. Quoting sarcasm is not producing it.

**Gate record.** A committed file naming the dataset actually obtained — exact
name, version, size, and the date access was granted or refused. Referenced by
the acceptance checklist. If the gate failed, this file is what documents the
dropped claim.

**Edge inputs.** Empty string, whitespace, a single emoji, 5000 characters.

---

## 12. Acceptance criteria

- [ ] Availability gate resolved and recorded, with the exact dataset name, version and size.
- [ ] Polarity-inversion rule written into the annotation guideline.
- [ ] Benign-sarcasm control set exists, comparable in size to the positive slice.
- [ ] Precision on the control set reported **before** recall in the results file.
- [ ] Agreement number published, however low.
- [ ] Results labelled exploratory if the fallback dataset was used.
- [ ] D1↔C confusion count reported.

---

## 13. Definition of done

Either: the gate passed, the control set holds, and the numbers ship with their CIs and their exploratory label. Or: the gate failed and the D1 claim is formally dropped from the project, with the reason written in the report. Both are successful outcomes for this module.
