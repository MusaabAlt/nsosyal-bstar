# Phase 05 — the official Çöltekin test set, single pass

3,528 rows (2,812 NOT / 716 OFF). Slices under the frozen Day 1 matcher:
`lexicon_hit` 491, `lexicon_free` 3,037. Test sha256 `9052784e13248e58…`, gold
`ae9b0837e948c3d9…`.

Selective-prediction thresholds were **read from
`results/04_calibration/calibration.json`** and applied unchanged. Nothing in
`phase05_final_test.py` computes a threshold, a quantile, or a target coverage
from test data; `metrics.json` records `thresholds_re_derived_on_test: false`
with the provenance of each. Coverage below is **achieved**, never targeted.

The resource is now **spent** (`TEST_SET_SPENT.json`), and
`src.data_io.load_coltekin_test` refuses on this machine and on any clone of
this commit.

---

## Verdict: the gap replicates, and is if anything larger

**BERTurk raw's recall gap on held-out data is +0.3970, 95% CI
[+0.3418, +0.4542].** On dev it was +0.3301 [+0.2771, +0.3827]. Both exclude
zero decisively. The point estimate is **6.7pp larger on test**, but the two
intervals overlap over [+0.3418, +0.3827], so **the increase itself is not an
established difference** — what is established is that the finding holds on data
no design decision ever saw.

The central claim of this project survives its one real test.

---

## 1. Overall

| system | macro-F1 | 95% CI | OFF-recall | OFF-precision |
|---|---:|---|---:|---:|
| keyword filter | 0.6657 | [0.6456, 0.6857] | 0.3757 | 0.5479 |
| **BERTurk raw** | **0.8095** | [0.7930, 0.8261] | 0.6592 | 0.7295 |
| +1a+1b+D | 0.8093 | [0.7927, 0.8255] | 0.6718 | 0.7168 |

## 2. Slices and the recall gap

| system | hit n | hit OFF-R | free n | free OFF-R | gap | 95% CI | excludes 0 |
|---|---:|---:|---:|---:|---:|---|---|
| keyword filter | 491 | 1.0000 | 3,037 | 0.0000 | +1.0000 | [+1.0000, +1.0000] | yes |
| BERTurk raw | 491 | 0.9071 | 3,037 | 0.5101 | **+0.3970** | **[+0.3418, +0.4542]** | yes |
| +1a+1b+D | 491 | 0.8810 | 3,037 | 0.5459 | +0.3352 | [+0.2803, +0.3964] | yes |

The keyword filter's ±1.0000 is definitional, not a finding: the slice boundary
*is* the filter's decision rule, so it scores 100% inside `lexicon_hit` and 0%
outside by construction. It is listed to make the tautology explicit rather than
to let a reader mistake it for a result.

## 3. Dev → test

| | dev | test | delta |
|---|---:|---:|---:|
| keyword macro-F1 | 0.6799 | 0.6657 | −0.0142 |
| keyword OFF-recall | 0.3859 | 0.3757 | −0.0102 |
| raw macro-F1 | 0.8271 | 0.8095 | −0.0176 |
| raw OFF-recall | 0.6902 | 0.6592 | −0.0310 |
| raw `lexicon_hit` OFF-R | 0.8930 | 0.9071 | +0.0141 |
| raw `lexicon_free` OFF-R | 0.5628 | 0.5101 | −0.0528 |
| **raw RECALL GAP** | **0.3301** | **0.3970** | **+0.0669** |

Everything degrades slightly from dev to test — a 1.8pp macro-F1 drop is an
ordinary held-out penalty and nothing about it is surprising. The gap widens
because the degradation is **not evenly distributed**: `lexicon_hit` recall
*rose* 1.4pp while `lexicon_free` recall *fell* 5.3pp. The model got better at
the slice it was already good at and worse at the slice it was already bad at.
That is the phase 02 diagnosis behaving exactly as it predicts on new data.

## 4. Selective prediction at the frozen dev thresholds

The thresholds transferred well. Achieved coverage is within 1–2pp of dev in all
four cases, which is the practical claim a review layer needs: a threshold set
on development data does what it said it would on unseen data.

**BERTurk raw**

> **High-automation** (threshold 0.6632, dev coverage 91.2%).
> At **90.2%** automatic coverage the system holds **0.8485** macro-F1 /
> **8.52%** error, deferring **9.8%** to human review.
> CI: coverage [0.8926, 0.9116], macro-F1 [0.8320, 0.8653], error [0.0752, 0.0944].
> Deferred-set error rate 42.65%; **capture lift 3.59×** (35.3% of all errors in
> 9.8% of rows).

> **High-precision** (threshold 0.8009, dev coverage 81.6%).
> At **79.8%** automatic coverage the system holds **0.8900** macro-F1 /
> **5.43%** error, deferring **20.2%** to human review.
> CI: coverage [0.7857, 0.8112], macro-F1 [0.8741, 0.9075], error [0.0457, 0.0628].
> Deferred-set error rate 37.36%; **capture lift 3.15×** (63.5% of all errors in
> 20.2% of rows).

The high-precision point was chosen on dev as "≤5% error"; it lands at 5.43% on
test (dev EVAL was 5.81%). Reported, not retuned.

**+1a+1b+D**

> **High-automation** (threshold 0.8656): at **91.1%** coverage, **0.8432**
> macro-F1 / **9.08%** error, deferring 8.9%. Capture lift 3.53×.

> **High-precision** (threshold 0.9877): at **71.1%** coverage, **0.9108**
> macro-F1 / **4.55%** error, deferring 28.9%. Capture lift 2.53×.

**The phase 04 null replicates.** Deferral remains error-selective and
slice-blind: at raw's high-automation point `lexicon_free` is deferred at 9.8%
and `lexicon_hit` at 10.0%; at the high-precision point, 20.3% vs 19.6%.
`lexicon_free` is 86.5% of the deferral queue against an 86.1% share of the test
set — proportion, not selection. Confidence finds errors wherever they are; it
does not find the lexical-cue weakness.

## 5. The defense on the official set

Paired deltas (`+1a+1b+D` − raw) on identical rows, 1,000 resamples, computed
from the saved predictions of the single pass:

| metric | delta | 95% CI | real? |
|---|---:|---|---|
| macro-F1 | −0.0002 | [−0.0129, +0.0118] | no |
| OFF-recall | +0.0126 | [−0.0126, +0.0364] | no |
| OFF-precision | −0.0127 | [−0.0397, +0.0109] | no |
| `lexicon_hit` OFF-recall | −0.0260 | [−0.0593, +0.0077] | no |
| **`lexicon_free` OFF-recall** | **+0.0358** | **[+0.0043, +0.0665]** | **yes** |

**This is more nuanced than the dev result, and the difference should not be
smoothed over.** On dev, the defense's `lexicon_free` gain (+0.0336) and its
`lexicon_hit` loss (−0.0423) *both* excluded zero, and the honest reading was
"a real gain paid for by an equal real loss". On test the **gain replicates
almost exactly** (+0.0358 vs +0.0336) while the **loss does not reach
significance** (−0.0260, CI spans zero).

So the targeted mechanism does work, and it works on held-out data: the
augmentation genuinely improves recall on profanity-free offensive content, by
roughly 3.5pp, twice measured.

It still does not produce a better **system**. Macro-F1 is −0.0002, as flat as a
result gets. The gain is absorbed by a precision cost (−0.0127) and a
`lexicon_hit` recall cost (−0.0260) that are individually indistinguishable from
noise but jointly cancel the benefit. And phase 04's finding stands: the defense
variant is badly miscalibrated (dev ECE 0.0786 vs raw's 0.0205), which on test
shows up as needing to defer 28.9% of rows to reach the error level raw reaches
while deferring 20.2%.

**Reported conclusion: the defense's targeted effect is real and replicated; its
net effect on the system is nil, and its calibration cost is real. Phase 03's
verdict stands at the system level and is refined at the component level.**

---

## Provenance and the single-use record

`raw_output.txt` is the verbatim console output of the run, unmodified.

**The test set was opened twice, and this is recorded rather than hidden.**
`TEST_SET_OPENED.json` shows two entries:

| opened at | outcome |
|---|---|
| 2026-08-16T11:09:00 | **crashed before any forward pass** — `AttributeError: 'Tee' object has no attribute 'isatty'`, raised by `transformers` while loading the first checkpoint. No predictions were made and no numbers were produced from this read. |
| 2026-08-16T11:10:36 | the complete run reported above (spend record written at 11:11:44) |

The open log is written *before* the bytes are read precisely so a crashed
attempt cannot disappear. The first read produced no result and therefore
informed no decision, but "it produced nothing" is a claim that deserves
evidence, not assertion — hence the log, the empty `metrics.json` at that point,
and the commit (`9af62f9`) that fixed the defect.

The spend record was written only after the complete run. `load_coltekin_test`
now raises `PermissionError` naming the run, the commit, and the results
directory, and states that deleting the record is a project-lead decision that
must be recorded in `docs/RESULTS_LOG.md`.

## Files

| File | Contents |
|---|---|
| `metrics.json` | every number above, with CIs, threshold provenance, environment |
| `paired_deltas.json` | defense − raw paired deltas from the saved predictions |
| `raw_output.txt` | verbatim console output, unmodified |
| `TEST_SET_OPENED.json` | append-only open log (2 entries) |
| `TEST_SET_SPENT.json` | the spend record that closes the resource |
| `test_predictions.csv` | per-row predictions (gitignored: corpus text; on the Drive mirror) |
