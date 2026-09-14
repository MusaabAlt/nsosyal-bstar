# M2 — Parallel De-obfuscation Channel

**Type:** representation (not a detector)
**Owner:** _assign_
**Priority:** highest value-to-effort in the project. This is the live-demo module.

---

## 1. Objective

Produce a **second representation** of the text with obfuscation undone, so the decision layer can compare the raw and the de-obfuscated reading of the same input.

Read that sentence again. This module does **not** clean the text and hand it on. It creates a parallel copy. The original always survives to the model untouched.

---

## 2. Why parallel and not preprocessing — the evidence

A published Turkish study over 392,806 queries found that normalization **lowered** performance, because misspelled profanity was "corrected" into other words:

| model | without normalization | with normalization |
|---|---|---|
| LinearSVC | F1 0.91 | F1 0.88 |
| LogisticRegression | 0.86 | 0.85 |
| MultinomialNB | 0.81 | 0.80 |

Meanwhile English work reports large gains from **targeted** normalization on functional test suites. These two results do not contradict each other: one is blind dictionary correction, the other is targeted, reversible transformation. The design that satisfies both is a parallel channel merged at the decision layer.

There is a second reason, specific to this project: the parallel design **does not touch the model or its thresholds**. The cost-derived threshold is the core of the project's existing result. Any change that forces threshold re-derivation puts that result at risk. This is the lowest-risk possible integration point.

---

## 3. Patterns in scope

| Code | Pattern | Example | Reversible by rule? |
|---|---|---|---|
| `LEET` | digit/symbol for letter | `s4l4k` | yes, short fixed map |
| `REPEAT` | stretched letters | `saaalaaak` | yes, fold runs > 2 |
| `SPACED` | spaces between letters | `s a l a k` | yes |
| `PUNCT_SPLIT` | punctuation between letters | `s.a.l.a.k` | yes, except `*` |
| `CHAR_DROP` | one letter deleted | `apta` | partial |
| `WORD_MERGE` | words glued together | `busalak` | partial |
| `ABBREV` | initialism | `amk` → `amq` | yes, via a lexicon — long tail |
| `DEASCII` | Turkish letters flattened | `serefsiz` | yes, but **ambiguous direction** |
| `VOWEL_DROP` | SMS style | `sktr` | partial, vowel harmony narrows it |
| `SUFFIX_ON_MASKED` | suffix on a broken root | `s*ktirtmişler` | partial |
| `DIALECT` | dialect spelling | `napıyon` | partial |
| `PHONETIC` | same-sounding substitute | `siqtir` | partial |
| `EMOJI_SUB` | emoji replaces the word | — | no, needs a mapping |

Note that `DEASCII` is bidirectionally ambiguous: `sık` (tight/frequent) and `sik` (profane) collapse into each other, as do `kanı` and `kani`. **Do not resolve this with a rule.** Leave it to the model and measure the cell explicitly.

---

## 4. Contract

**Reads:** `ctx.charsafe_text` (falls back to `ctx.text`)

**Writes:**
- `out.normalized_text`
- `out.form_patterns` — one per transformation, each with `evidence` and `span`

**Never** writes content scores. **Never** replaces `ctx.text`.

---

## 5. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Replacing the raw text | Kills the parallel design and reproduces the documented Turkish F1 drop. |
| Blind Zemberek / deasciifier as a preprocessing layer | Same reason. Legitimate use is inside this channel only, with an over-correction guard. |
| Resolving `sık`/`sik` with a rule | Genuine ambiguity. Rule-resolving it guarantees errors in one direction. Measure it instead. |
| Treating obfuscation as a content category | It is an axis, not a class. Making it a class breaks mutual exclusivity and collapses annotation agreement. |
| Presenting "a Turkish obfuscation filter" as the contribution | `terlik` exists and uses the same example strings. The contribution is the **measurement** of how much recall collapses and where the repair belongs. |

---

## 6. Metrics this module must produce

This is the project's headline number. Produce it in this exact form:

> Under obfuscation pattern *P*, recall drops from **A** to **B** [CI]. The parallel decision channel recovers **C** points at a cost of **+D** FPR on clean text [CI].

Required breakdown:

- **Per pattern, never aggregated.** One row per pattern code. An average across patterns hides which ones you actually handle.
- **Paired measurement.** Build clean↔obfuscated 1:1 pairs from positives that are **not in training data**. Use McNemar or a paired bootstrap, with Holm correction across patterns.
- **Attack success rate must state its denominator** and be accompanied by the absolute recall-under-perturbation. ASR alone is uninterpretable.
- **Clean-to-dirty flip rate** on the trap list — the over-correction guard.
- **Real-obfuscation slice.** Keep a small, separately collected slice of *real* obfuscated text alongside the generated one, and report the gap between them. Published obfuscation distributions come from non-Turkish platforms, so your generated distribution is an assumption until measured.
- **Human spot-check.** Automatically generated character attacks have been reported to include a high rate of false alarms, so a sample of generated cases must be human-verified before the numbers are used.

---

## 7. Leakage rule

The generator that builds the **evaluation** obfuscation set must be separate — different seeds, different rules — from any generator used for **training** augmentation. Write this separation into the protocol file before producing any number.

---

## 8. Acceptance criteria

- [ ] `ctx.text` is provably unmodified after the module runs. Dedicated unit test.
- [ ] Capture rate ≥ **80%** per pattern on the generated set, reported per pattern with CIs.
- [ ] Clean-to-dirty flip rate **below the budget** in `decision/thresholds.yaml`. If exceeded: disable the dictionary rules, keep the conservative character rules, and document it as a measured negative — that is a result, not a failure.
- [ ] Every transformation emits a `FormPattern` with `evidence` and `span`.
- [ ] Real-obfuscation slice exists and the distribution gap is reported.
- [ ] Human verification of a generated sample documented.
- [ ] p95 latency under **10 ms**.

---

## 9. Research pointers

- The Turkish normalization pipeline literature (Eryiğit & Torunoğlu-Selamet) defines seven modules: case transformation, replacement rules and lexicon lookup, proper-noun detection, deasciification, vowel restoration, accent normalization, spelling correction. Reported overall accuracy is in the 67–77% range depending on evaluation mode. Use this as the structure of your channel and as the honest ceiling of rule-based repair.
- HateCheck spelling-variation functions (character swap, deletion, spacing, leet) — the template for your test functions.
- Multilingual HateCheck's Arabic functions (Latin-letter substitution, character repetition, Arabizi, alternative accepted spellings) are the closest structural analogue to Turkish. Use them as the model for your Turkish-specific functions.

---

## 10. Definition of done

Per-pattern numbers exist with CIs, the flip-rate budget is respected or the fallback is documented, the raw text is provably untouched, and the demo case works: a judge types an obfuscated insult and the system catches it live.
