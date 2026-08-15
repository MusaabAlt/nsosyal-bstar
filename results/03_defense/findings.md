# Phase 03 — Defense results (four runs, frozen dev split)

Dev fingerprint `034415af3a23b388`, seed 42, official Çöltekin test set untouched.
Deltas are **paired** bootstraps (1,000 resamples): rows are resampled once and both
systems scored on that resample, because all four variants see identical dev rows.

---

## Verdict: the defense did not work as designed

**No metric improved except `lexicon_free` OFF-recall in the full variant (+0.0336), and
that gain is accompanied by a real loss of equal size on `lexicon_hit` (−0.0423) and by 30
additional no-profanity false positives. Overall macro-F1 did not move.** The recall gap
narrowed from +0.3301 to +0.2542, but roughly half of that narrowing is degradation of the
slice the model was already good at — the "within-gap trade" named as a failure mode in the
design, now observed.

Component 1b's stated purpose was to cut the profanity-bearing false positives. The
`lexicon_hit` false-positive rate went **up**, 0.1815 → 0.1931.

---

## All four runs

| Metric | BERTurk raw | +1a | +1a+1b | +1a+1b+D |
|---|---:|---:|---:|---:|
| overall macro-F1 | 0.8271 | 0.8244 | 0.8173 | 0.8202 |
| `lexicon_free` OFF-recall | 0.5628 | 0.5204 | 0.5841 | **0.5965** |
| `lexicon_hit` OFF-recall | 0.8930 | 0.8873 | 0.8282 | 0.8507 |
| `lexicon_hit` FP rate | 0.1815 | 0.1737 | 0.1853 | 0.1931 |
| recall gap | +0.3301 | +0.3670 | +0.2441 | +0.2542 |
| false positives (total) | 213 | 182 | 232 | 245 |
| — of which no profanity token | 185 | 156 | 205 | 215 |
| H-perturbed dev macro-F1 | 0.8122 | 0.8079 | 0.8085 | 0.8124 |
| H-perturbed dev OFF-recall | 0.6565 | 0.6261 | 0.6652 | 0.6793 |

Paired deltas against raw (CI excluding zero = a real change):

| | macro-F1 | `lexicon_free` OFF-R | `lexicon_hit` OFF-R |
|---|---|---|---|
| +1a | −0.0027 [−0.0125, +0.0065] | **−0.0425 [−0.0722, −0.0110]** | −0.0056 [−0.0310, +0.0194] |
| +1a+1b | −0.0098 [−0.0208, +0.0006] | +0.0212 [−0.0087, +0.0502] | **−0.0648 [−0.0978, −0.0315]** |
| +1a+1b+D | −0.0069 [−0.0185, +0.0052] | **+0.0336 [+0.0052, +0.0662]** | **−0.0423 [−0.0778, −0.0109]** |

---

## What each component actually did

**1a made the model worse at exactly what it was designed to fix.** Masking the profanity
in structurally-offensive OFF rows was meant to force the model to read structure, raising
`lexicon_free` recall. It *lowered* it by 0.0425, and the CI excludes zero — this is a real
effect, not noise. It also made the model more conservative overall: false positives fell
from 213 to 182 and no-profanity false positives from 185 to 156. The likely mechanism is
that 1,146 upsampled rows carrying a `[MASK]` token that never appears at inference gave
the model a cue available only in training; the OFF examples it learned from were the ones
with their strongest signal removed, and it responded by predicting OFF less often.

**1b moved recall but not the false positives it targeted.** Adding it moved
`lexicon_hit` recall down 0.0648 (CI excludes zero) — the model did stop treating a
profanity token as sufficient. But the `lexicon_hit` FP rate rose 47/259 → 48/259, and
total false positives rose 182 → 232. So the lexical cue was weakened without the
pragmatic distinction being learned in its place: the model became *less* certain on
profanity rather than *better* at judging its function.

**Component 2 (D-family) gave a small positive D→H transfer.** H-perturbed OFF-recall rose
0.6652 → 0.6793 over `+1a+1b` (+0.0141), and +0.0228 against raw. This is a small effect
and it is reported as *robustness to unseen adversarial input*, never as a fix for the
measured errors. Note also that the H perturbation costs raw only 0.0149 macro-F1
(0.8271 → 0.8122), which supports the design-time warning that the H operators —
particularly diacritic stripping — are close to ordinary Turkish typing in this corpus, so
this robustness test is weak and its numbers should not carry much weight.

**The no-profanity FP tripwire fired, and the four-run design attributed it correctly.**
The count rose 185 → 215 in the full variant. It was *not* 1a that caused it (1a alone
lowered it to 156) but 1b and D. Had the runs been combined, this would have been
misattributed to the masking operator.

---

## Stated limitations

**Attribution of any FP change is not evidence of pragmatic understanding.** Dev contains
none of the ~20 synthetic 1b fragment strings, which rules out literal string memorisation
and nothing more. A shallower distributional cue — "profanity in a subordinate clause after
a comma", "profanity not adjacent to a second-person pronoun", "profanity in a clause with
an inanimate subject" — would transfer to dev and move the numbers without the model having
acquired anything resembling use–mention understanding. The measurement cannot separate the
two, because the augmentation supplies both signals at once and there is no held-out set
that varies one while holding the other fixed. Building one means collecting natural
non-offensive profanity uses in syntactic configurations unlike the templates: a
corpus-collection task, out of scope for this window. **This limitation is stated, not
mitigated.**

Other limitations carried forward: the automated no-profanity FP count (185 for raw) is a
reproducible proxy and is *not* the same quantity as the 118 manually tagged in phase 02 —
the proxy counts a row as profanity-bearing only when a non-suspect lexicon token is
present, so out-of-lexicon and suspect-root forms fall on the other side. Only its deltas
across runs are meaningful. The 1a yield is 382 clean rows of 5,211 gold-OFF (7%) under a
deliberately strict filter, upsampled ×3.

## Files

| File | Contents |
|---|---|
| `comparison.json` | all four runs plus paired deltas |
| `run_{raw,1a,1a1b,1a1b_d}/metrics.json` | per-run metrics, augmentation counts, H column |
| `run_*/dev_predictions.csv` | per-row predictions (gitignored: corpus text) |
| `train_oof_summary.json` | the 5-fold out-of-fold error base used to derive 1b (C1) |
