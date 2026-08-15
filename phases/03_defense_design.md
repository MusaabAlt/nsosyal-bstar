# Phase 3 — Defense design

**Entry gate:** Phase 2 closed. The diagnosis is recorded in
`results/02_failure_analysis/findings.md` with its central claim:

> The model detects offensive VOCABULARY rather than offensive ACTS. 84 of 95
> profanity-bearing false positives perform no offensive act toward anyone, while the
> genuine false negatives are directed offense carrying no profanity. One mechanism, both
> error directions, quantified.

**Exit gate:** three runs evaluated on the frozen dev split, all four metrics reported
together as deltas against BERTurk raw with CIs, regardless of sign.

---

## The mechanism the defense attacks

In Çöltekin a profanity token is a near-sufficient cue for OFF, so the model never has to
learn who is targeted or whether the word is being *used* at all. The defense breaks that
token↔label correlation in both directions during training. Both components are that one
idea; nothing else is in scope.

---

## Binding constraints (corrections issued 15 Aug 2026, before any code)

### C1 — Insertion patterns must NOT be derived from dev

**The severe one.** Deriving 1b's insertion patterns from the FP families measured on dev
would mean the reported FP reduction partly measures the template rather than the model —
the same circularity that killed an earlier version of this project, in a new form.

Therefore:

- All 1b insertion patterns are derived from **training-split errors only**.
- Training-split errors are obtained by **5-fold stratified cross-validation inside the
  training split** (seed 42), producing out-of-fold predictions for all 26,992 training
  rows. Chosen over the epoch-1-checkpoint-on-held-in-rows alternative because out-of-fold
  predictions are made on rows the model did not train on, which is the same condition dev
  is evaluated under; predictions on held-in rows are memorisation-contaminated and their
  error structure is not comparable. Cost is ~25 min of L4 time, which we have.
- The dev FP families measured in phase 2 are **untouched by design** and serve one
  purpose only: validating afterwards that the diagnosis generalises, by comparing the
  training-derived family distribution against the dev one. Comparison is permitted;
  derivation is not.

### C2 — 1a must not inject label noise

Measuring an injected-noise rate after the fact is not enough: the noise sits inside
training data and its effect cannot be separated from the intervention.

Therefore 1a applies **only** to gold-OFF rows that carry offensive structure independent
of the profanity token — second-person address, imperative, explicit target mention, or a
sarcastic frame. Rows where the profanity *is* the offense are skipped. The count of
qualifying and skipped OFF rows is reported. **Fewer clean augmented rows beats more noisy
ones.**

### C3 — Attack-family disjointness

`obfuscation.assert_disjoint(train_families=['D'], eval_families=['H'])` is called at
**both** call sites: the top of the training script and the robustness evaluation. D and H
are fixed before any robustness number is measured.

### C4 — Evaluation protocol

Same fixed dev split, fingerprint `034415af3a23b388`, seed 42. The official Çöltekin test
set stays untouched. Deltas are reported with CIs regardless of sign, including if the
defense makes things worse.

---

## Component 1 — Counterfactual token augmentation

Training split only; dev is never augmented.

**1a — mask the profanity in gold-OFF rows, keep the label OFF.** Forces the model to
locate offense in structure rather than vocabulary. Subject to C2's structural filter.

**1b — insert profanity into gold-NOT rows in a non-offensive function, keep the label
NOT.** Functions are taken from the training-split error taxonomy (C1): filler /
intensifier, non-directed, meta-discussion, negated, quoted, self-directed.

**Targets.** 1a → the lexicon-free false negatives (implicit offense, 35% of the unbiased
dev sample). 1b → the profanity-bearing false positives that perform no offensive act.

**Not targeted, stated as a limitation.** Sense-collision false positives are reached only
indirectly. The false positives carrying no profanity token at all (topic/register:
religion, politics) are not addressed by this defense.

**Failure modes.** A new positional shortcut from templated insertion; a within-gap trade
where `lexicon_hit` recall falls and the gap narrows for the wrong reason — which is why
all four metrics are reported together.

## Component 2 — Character-level obfuscation augmentation

| | Family | Operators |
|---|---|---|
| Train | **D** | vowel deletion, digit/letter homoglyph substitution, character doubling |
| Held out | **H** | punctuation/space injection, diacritic stripping/swap, consonant transposition |

**Framing, fixed in advance:** this component is *robustness to unseen adversarial input*.
It is never reported as a fix for the measured errors — obfuscation was 1/40 of the
unbiased dev FN sample against 35% for implicit offense. **A near-zero D→H transfer is a
real result and gets reported as one.**

**Failure modes.** Memorisation of D rather than robustness (near-zero H transfer);
diacritic stripping being indistinguishable from ordinary Turkish typing in this corpus;
a gibberish shortcut raising no-profanity false positives.

---

## Runs

| Run | Contents |
|---|---|
| 1 | BERTurk raw — already have it (`results/01_baseline_berturk/`) |
| 2 | + Component 1 |
| 3 | + Components 1 & 2 |

Reported against the raw baseline: overall macro-F1 (0.8271 [0.8139, 0.8405]),
`lexicon_free` OFF-recall (0.5628 [0.5210, 0.6010]), `lexicon_hit` false-positive rate on
gold-NOT (47/259 = 18.1%), recall gap (+0.3301 [+0.2771, +0.3827]). Run 3 additionally
reports the held-out-obfuscation column on an H-perturbed copy of dev.

## Review gate

Augmentation samples — ~20 rows from each of 1a and 1b — are read and approved before any
training run is launched. Bad augmentation is cheaper to catch by reading than by training
on.
