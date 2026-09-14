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

## 3. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| The 13 obfuscation patterns listed in the next section | invisible characters, homoglyphs, Turkish casing → M0, already applied upstream |
| Accent normalisation (`áptal` → `aptal`) | profane roots themselves → M1 runs on this module's output |
| Turkish-specific spelling evasion (ASCII flattening, vowel dropping, suffixes on a masked root) | any meaning, category or intent → M3 / M4 / M5 |
| A second representation of the text, with every change traceable to a span | ordinary typos and spelling errors → deliberately out of scope, see below |

**Explicitly out of scope, with the reason:**

- **Ordinary typo correction.** This module repairs *evasion*, not *error*. General spelling correction is exactly the blind normalization that lowered F1 on Turkish in the study above. If a repair rule cannot name which obfuscation pattern it is undoing, it does not belong here.
- **Intent.** The module reports that text was obfuscated, never that it was obfuscated *maliciously*. A typo and an evasion can produce the same string; separating them is not this module's job and no downstream consumer should assume it was done.
- **`EMOJI_SUB`.** Listed as a pattern for completeness, but out of scope for v1: it needs a curated emoji-to-word mapping that does not exist for Turkish. Declare it unhandled rather than half-handling it.
- **Proper nouns, brands, hashtags, mentions and URLs.** These must pass through untouched. `3M`, `Turkcell'in`, `@kullanici`, `#etiket` and any URL look exactly like leet or word-merge patterns to a naive rule. Detect and protect them before any repair pass runs.
- **Resolving `sık`/`sik` or `kanı`/`kani`.** Genuinely ambiguous. Emit both readings or neither; a rule that picks one guarantees errors in one direction.

---

## 4. Patterns in scope

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

## 5. Approach and named tools

Two tiers, run in order. The tier split exists so the dictionary layer can be
switched off without losing the module.

**Tier 1 — conservative character rules. Always on, no dictionary.**
Leet mapping, repeat folding (runs longer than 2), separator removal inside a
token, punctuation-split removal, accent normalisation. These are reversible,
cheap, and cannot invent a word that was not there. Implemented with
`unicodedata` and a short fixed table — no external tool required.

**Tier 2 — dictionary and morphology-backed repairs. Disable-able.**
Vowel restoration, ASCII-to-Turkish restoration, word-merge splitting,
abbreviation expansion, suffix reattachment on a masked root. These can turn a
clean word into a dirty one, so they sit behind the over-correction budget in
`decision/thresholds.yaml`. If the budget is exceeded, tier 2 is disabled, tier
1 stays, and the outcome is reported as a measured negative.

**Named tools — evaluate these before writing your own:**

| Tool | Use it for | Constraint |
|---|---|---|
| `terlik` | leet, separators, repetition, zero-width handling on Turkish roots; already a dependency of M1 | MIT. Use its normalisation helpers only — its detection verdict belongs to M1, not here |
| Zemberek (`zemberek-python`) or `zeyrek` | validating that a candidate repair is a legal Turkish word form | Morphological **validation** only. Never as a blind normalizer — that is the documented F1 drop |
| A Turkish deasciifier (Deniz Yuret's algorithm, or the implementation in `trnlp`) | ASCII-to-Turkish restoration | Tier 2 only, behind the over-correction guard. It is a statistical guesser, not a decoder |
| `unicodedata` (stdlib) | accent composition/decomposition, category checks | — |

Do not adopt a tool without recording its licence in the module README, and do
not let a tool's own profanity verdict leak into this module's output. M2
reports form; M1 and M3 report content.

**Protection pass, before any repair.** Detect and mask URLs, mentions,
hashtags, numbers attached to brand names, and capitalised proper nouns. Repair
runs on what remains. This single pass prevents most of the tier-2 damage the
budget is there to catch.

**Every transformation emits a `FormPattern`** with its code, its evidence and
its span into the original text. A repair with no pattern is a contract
violation: the decision layer and the demo UI both read the span, and a change
the system cannot point at is a change it cannot defend.

---

## 6. Contract

**Reads:** `ctx.charsafe_text` (falls back to `ctx.text`)

**Writes:**
- `out.normalized_text`
- `out.form.patterns` — one per transformation, each with `evidence` and `span`

**Never** writes content scores. **Never** replaces `ctx.text`.

---

## 7. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Replacing the raw text | Kills the parallel design and reproduces the documented Turkish F1 drop. |
| Blind Zemberek / deasciifier as a preprocessing layer | Same reason. Legitimate use is inside this channel only, with an over-correction guard. |
| Resolving `sık`/`sik` with a rule | Genuine ambiguity. Rule-resolving it guarantees errors in one direction. Measure it instead. |
| Treating obfuscation as a content category | It is an axis, not a class. Making it a class breaks mutual exclusivity and collapses annotation agreement. |
| Presenting "a Turkish obfuscation filter" as the contribution | `terlik` exists and uses the same example strings. The contribution is the **measurement** of how much recall collapses and where the repair belongs. |

---

## 8. Metrics this module must produce

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

## 9. Required fixtures

`fixtures/cases.jsonl` — `{"id": ..., "text": ..., "context": {"charsafe_text": ...}, "expect_patterns": [...], "expect": {"normalized_text": ...}, "expect_clean": true|false}` (keys as read by `eval/harness.py`)

**Per pattern.** At least 10 clean↔obfuscated pairs for every code in the
patterns table, built from positives that are **not** in training data. This is
what the per-pattern capture rate is computed on; a pattern with fewer than 10
pairs reports "insufficient sample" rather than a number.

**Protection cases — must pass through unchanged:**
`3M`, `Turkcell'in`, `@kullanici`, `#TeknoFest2026`, `https://example.com/a1b2`,
`Ayşe'yi`, `COVID-19`, `Ar-Ge`, a phone number, an IBAN-shaped string.

**Ambiguity cases — must not be rule-resolved:**
`sık` / `sik`, `kanı` / `kani`, `kısmet` / `kismet`. Assert that the module
either keeps both readings or emits neither, and that it never silently picks
one.

**Over-correction traps.** The full list from `eval/traps/traps.jsonl`, each
asserted to produce zero clean-to-dirty flips after both tiers run.

**Idempotency.** Normalising an already-normalised string must be a no-op:
`f(f(x)) == f(x)`. A rule that keeps firing on its own output will loop or
drift.

**Span correctness.** For every emitted pattern, `text[start:end]` equals the
declared evidence. A unit test asserts this on every fixture, not on a sample.

**Real-obfuscation slice.** A small, separately collected set of genuinely
obfuscated Turkish text, stored apart from the generated set and never used to
tune the rules. The gap between generated and real capture rate is a reported
number, not a footnote.

**Edge inputs.** Empty string, single space, a 5000-character post, a string
that is entirely punctuation, and a string mixing Turkish with Arabic script.

---

## 10. Leakage rule

The generator that builds the **evaluation** obfuscation set must be separate — different seeds, different rules — from any generator used for **training** augmentation. Write this separation into the protocol file before producing any number.

---

## 11. Acceptance criteria

- [ ] `ctx.text` is provably unmodified after the module runs. Dedicated unit test.
- [ ] Capture rate ≥ **80%** per pattern on the generated set, reported per pattern with CIs.
- [ ] Clean-to-dirty flip rate **below the budget** in `decision/thresholds.yaml`. If exceeded: disable the dictionary rules, keep the conservative character rules, and document it as a measured negative — that is a result, not a failure.
- [ ] Every transformation emits a `FormPattern` with `evidence` and `span`.
- [ ] Real-obfuscation slice exists and the distribution gap is reported.
- [ ] Human verification of a generated sample documented.
- [ ] p95 latency under **10 ms**.

---

## 12. Research pointers

- The Turkish normalization pipeline literature (Eryiğit & Torunoğlu-Selamet) defines seven modules: case transformation, replacement rules and lexicon lookup, proper-noun detection, deasciification, vowel restoration, accent normalization, spelling correction. Reported overall accuracy is in the 67–77% range depending on evaluation mode. Use this as the structure of your channel and as the honest ceiling of rule-based repair.
- HateCheck spelling-variation functions (character swap, deletion, spacing, leet) — the template for your test functions.
- Multilingual HateCheck's Arabic functions (Latin-letter substitution, character repetition, Arabizi, alternative accepted spellings) are the closest structural analogue to Turkish. Use them as the model for your Turkish-specific functions.

---

## 13. Definition of done

Per-pattern numbers exist with CIs, the flip-rate budget is respected or the fallback is documented, the raw text is provably untouched, and the demo case works: a judge types an obfuscated insult and the system catches it live.
