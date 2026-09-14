# NSosyal B* — Modeling & Evaluation Phase: Briefing

> Paste this whole file at the start of a fresh conversation. It contains everything
> needed to run the training / diagnosis / evaluation phase without re-explaining the
> project. It intentionally omits day-by-day scheduling — that is decided in-flight.

---

## 1. What we are building (one sentence)

A Turkish system that catches offensive content which slips past a normal
keyword filter — either because it is orthographically obfuscated
(`aptal` → `a.p.t.a.l`) or because it is offensive with no profanity word at all
— and pairs every prediction with a calibrated confidence that decides:
auto-resolve, or send to a human reviewer.

The deliverable is **not** "a better toxicity model." It is a **rigorous
comparison that proves which defense actually works in Turkish**, plus a
selective-triage layer that connects model failures to human-review workload.

---

## 2. The core method (what we actually do)

This is an **empirical, diagnosis-first** project. We do not assume where models
fail — we train, observe the real failures, then design the fix around what we
actually found.

1. Train a baseline Turkish model on clean text only.
2. Analyze its failures in detail: count them, categorize them, record them, and
   read the actual failing texts to find the real failure pattern.
3. Repeat with a second Turkish model to test whether the failure pattern is
   general (strong claim) or model-specific (weaker claim).
4. From the observed failures, design a defense — extra layer(s) or a
   noise-augmented model — that targets what the models actually failed on.
5. Compare every system honestly on the same fixed protocol.
6. Add a confidence-calibration + selective-prediction layer that translates
   model errors into a measurable human-review trade-off.

**Guiding rule:** let the data lead the design, not the other way around. Do not
commit to "obfuscation defense" (or any fix) until the failure analysis proves
that is the real failure mode.

---

## 3. What we want to prove (the questions each experiment answers)

| Question | How it's answered |
|---|---|
| Does a keyword filter really miss a large share of Turkish offensive content? | Already proven on Day 1: **3,892 / 6,131 OFF tweets (~63%)** evade a 695-word lexicon. |
| Does a *real trained model* still struggle on lexicon-free offensive text, or does it learn it on its own? | Train BERTurk, compare OFF-recall on lexicon-hit vs lexicon-free slices of the dev set. |
| What do the models *actually* fail on? | Read the most confidently-wrong false negatives on the dev set. |
| Is the failure pattern general or model-specific? | Compare BERTurk vs ConvBERTurk failures — same cases or different? |
| Does our defense recover performance on *unseen* attacks (not the ones we trained on)? | Test on held-out obfuscation families the model never saw in training. |
| Does the system generalize beyond its training source? | Test on independent Turkish corpora (cross-corpus). |
| Can we cut human-review load at a fixed error level? | Confidence calibration + risk–coverage curve. |

---

## 4. Models

| Role | Model | HF string |
|---|---|---|
| Primary baseline | BERTurk (base, cased) | `dbmdz/bert-base-turkish-cased` |
| Second model (comparison) | ConvBERTurk (base, cased) | `dbmdz/convbert-base-turkish-cased` |

Run the primary first, read its failures fully, then run the second — its value is
answering "does the *same* failure pattern hold?", not just adding a number.

---

## 5. Data — strict role separation

**Never mix training data with generalization-test sources. Every "generalization"
number is only meaningful because the model never saw that source.**

### Training + diagnosis (single source)
- **Çöltekin — Turkish Offensive Tweet Corpus / OffensEval-2020 TR**
  - Site: `https://coltekin.github.io/offensive-turkish/`
  - HuggingFace: `coltekin/offenseval2020_tr`
  - 31,756 training rows, binary `OFF` / `NOT`, ~19.3% OFF, human-annotated, CC-BY.
  - Split internally: **85% train / 15% dev**. Error analysis happens on **dev only**.

### Official same-source test (touch once, at the very end)
- **Çöltekin official test set** — `offenseval-tr-testset-v1.tsv` (no labels) +
  `offenseval-tr-labela-v1.tsv` (gold, **comma-separated** despite `.tsv` extension).
  - This produces the final reported number. Touching it more than once, or
    tuning against it, contaminates the whole evaluation.

### Cross-corpus generalization tests (independent, human-labeled, never trained on)
- **Mayda** — `https://github.com/imayda/turkish-hate-speech-dataset-1`
  (1,000 rows; a larger ~10,224-row version exists under the same `imayda` account — prefer it).
- **Beyhan (verimsu)** — `https://github.com/verimsu/Turkish-HS-Dataset`
  (İstanbul Convention + Refugees, ~2.5K rows).

### Lexicon (frozen Day 1 — do not modify after seeing results)
- `https://github.com/ooguz/turkce-kufur-karaliste` → `karaliste.txt` (695 entries).
- Alt: `https://github.com/d35k/Turkish-Swear-Words` → `swears.txt`.

### Rejected sources (do not use)
- **Overfit-GM/turkish-toxic-language** (77,800) — merged from other datasets (likely
  contains Çöltekin → contamination) AND partly pseudo-labeled (not human ground truth).
- Any dataset described as "merged" or "pseudo-labeled" is disqualified for
  generalization testing: it breaks source-independence and/or human-ground-truth.

---

## 6. Reading warnings (avoid corrupting the data)

- **Çöltekin training TSV**: no quoting, no escapes; newlines inside tweets were
  replaced by three spaces. Read line-by-line and split on `\t` manually — default
  csv/pandas parsing will corrupt rows.
- **Çöltekin gold labels file**: `.tsv` extension but **comma-separated** content.
- **Turkish lowercasing**: map `I→ı` and `İ→i` before `.lower()`.
- **Mayda / Beyhan**: their internal structure (column names, label values, encoding)
  was not verified from the files themselves — inspect before use. Their label schemes
  are 3-way (`hate`/`offensive`/`none`); map explicitly to binary and state it as a
  documented limitation: `{hate, offensive} → OFF`, `{none} → NOT`.

---

## 7. Anti-circularity rules (these protect every number we report)

1. **Freeze the lexicon before any measurement.** Record commit hash + license + date.
2. **Dev set is for design; the official test set is for the final number only.**
   No tuning against the test set, ever.
3. **Obfuscation for training ≠ obfuscation for testing.** If we noise-augment
   training, we must test on a *held-out* attack family the model never saw. Testing
   on the same operators we trained on measures memorization, not robustness — this is
   the exact circularity that killed an earlier version of the idea.
4. Real-world self-censored profanity found in the data (`o***`, `aq`) is valuable
   *qualitative* evidence but too rare (n≈5) to be a standalone statistical axis.

---

## 8. Final matrix — this table is the technical core

Each cell: macro-F1 + OFF-recall + bootstrap confidence interval.

| System | Çöltekin test | Mayda | Beyhan | Held-out obfusc. | Lexicon-hit | Lexicon-free |
|---|---|---|---|---|---|---|
| Keyword filter (baseline) | | | | | | |
| BERTurk (raw) | | | | | | |
| ConvBERTurk (raw) | | | | | | |
| Our defense | | | | | | |

Plus the pivotal operational figure:
> "At X% automatic coverage, the system holds Y macro-F1 / Z% error, deferring only
> (100−X)% of items to human review; on lexicon-free and held-out-obfuscation slices,
> degradation is Δ₁ and Δ₂."

---

## 9. What the finished phase must produce

1. Baseline numbers (macro-F1, OFF-recall) for BERTurk and ConvBERTurk on dev.
2. A documented failure analysis: counts, categories, and the actual
   most-confident false-negative texts — the empirical basis for the fix.
3. A verdict on whether the lexicon-free gap survives a real model.
4. A verdict on whether the failure pattern is general (both models) or specific.
5. Cross-corpus generalization numbers (Mayda, Beyhan).
6. The completed comparison matrix (Section 8).
7. A calibrated risk–coverage curve with 2–3 declared operating points.
8. One reproducible offline demo screen showing all systems side-by-side, with the
   confidence-based auto-resolve / send-to-review decision.

---

## 10. Related work we must cite (originality is narrow and honest)

We do **not** claim to have invented any of these — we cite them and claim only the
Turkish operational synthesis:
- **CITA** (arXiv 2605.22258) — already combines semantic-indirectness + surface
  obfuscation (for Chinese). Never claim we invented the two-axis idea.
- **ToxiCloakCN** (arXiv 2406.12223) — cloaked offensive-text robustness benchmark.
- **On the Robustness of Offensive Language Classifiers** (arXiv 2203.11331, ACL 2022).
- **Selective text classification / abstention** (ACL 2023; arXiv 2605.14074) — the
  risk–coverage / human-deferral idea is established; we apply it, not invent it.
- Turkish baselines: Çöltekin 2020 (LREC); BERTurk on OffensEval-TR macro-F1 ≈ 0.786
  (BRUMS, arXiv 2010.06278); ConvBERTurk ≈ 82 macro-F1 (SindBERT, arXiv 2510.21364;
  TOLID, 2026). Turkish normalization: Adalı & Eryiğit 2014 (deasciification / vowel
  restoration).

> Any figure copied into the technical report must be re-verified from its primary
> source before writing — secondary-source numbers are for orientation only.

---

## 11. Environment

- **Compute: Colab Pro+** — decided 15 Aug 2026 (phase 01 precondition 3). This
  supersedes the earlier Kaggle Notebooks plan; `NSOSYAL_ENV=colab`. BERT-base
  fine-tuning on ~30K examples is a light job (minutes on an A100/T4). Checkpoint
  everything — a session can still drop, and `/content` is wiped when it does, so
  point `NSOSYAL_RESULTS` and `NSOSYAL_CKPT` at Drive.
- **Stack:** `transformers`, `datasets`, `torch`, `scikit-learn`.
- `max_len=128`, fixed seed (42), stratified split, `fp16` when GPU available.

---

## Competition constraints (fixed)

- Track: **Sosyal Yapay Zekâ** — weights: Technical 35% / Innovation 20% /
  Problem-solving 20% / UI/UX 10% / Presentation 15% / Business 0%.
- No NSosyal API; everything runs offline, no real money, no live-platform dependency.
- No individual-account scoring; keep framing as a reviewer tool, not "your platform
  fails on X%".
- Technical report due **24 Aug 2026, 17:00 TSİ**; application due 20 Aug.
