# Phase 09 Stage 1 — threshold-free slice comparison

Pre-registration: `phases/09_deeper_analysis.md`, C9-1 … C9-11, committed at
**12afa74** before any number below existed. Machine-readable record:
`stage1_auc.json`. Driver: `phase09_stage1_auc.py`. Tests:
`tests/test_stage1_auc.py` (24, all passing; 166 in the suite).

Read-only. No training, no forward pass, dev split `034415af3a23b388` only.
The official test set was not touched. Measurement only — no intervention is
proposed (C9-11).

---

## 1. The answer

**Pre-registered verdict: `INTERMEDIATE`.**

| | `lexicon_hit` | `lexicon_free` |
|---|---|---|
| base rate (OFF) | 0.5782 (355/614) | 0.1361 (565/4150) |
| **ROC-AUC** | **0.9306** [0.9102, 0.9495] | **0.8962** [0.8821, 0.9095] |
| OFF-recall at t = 0.5 | 0.8930 | 0.5628 |

```
G = AUC(lexicon_hit) − AUC(lexicon_free) = +0.0345  [+0.0103, +0.0585]
```

The interval excludes zero, so a ranking-quality difference is real. But the
point estimate lands in the band C9-4 declared **inconclusive in advance**
(0.02 ≤ G < 0.05), so branch 4 of the C9-5 rule fires and the verdict is
`INTERMEDIATE`: this analysis **cannot separate** how much of the 33pp recall
gap is ranking quality and how much is where the threshold sits.

**The one thing that is now settled: the recall gap is not mostly a
ranking-quality gap.** A +0.3301 recall difference sits on top of a +0.0345 AUC
difference. The model *does* rank profanity-free offensive content above
profanity-free benign content, and it does so nearly as well as it ranks the
profanity-carrying slice (0.896 against 0.931). What it does not do is push that
content past 0.5.

That is a weaker claim than the report made, and it is the claim the evidence
supports. **The report was changed to match on 2026-08-17** — see §8.

---

## 2. Provenance (C9-1)

`results/01_baseline_berturk/dev_predictions.csv`, BERTurk `best.pt` = epoch 1,
the same dump phases 02 and 04 read.

```
sha256  a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
bytes   736,591     rows 4,764
```

The file is gitignored (corpus text) and its durable copy is the Drive mirror.
Before any new quantity was computed the dump was required to reproduce **every**
recorded phase-01 figure, and did: OFF-recall 635/920 = 0.6902, `lexicon_hit`
317/355 = 0.8930, `lexicon_free` 318/565 = 0.5628, 285 FN, 213 FP, FP rates
47/259 and 166/3585, OFF-precision 0.7488, and `pred == OFF iff p_OFF > 0.5` on
all 4,764 rows. Provenance is therefore established **by content**, not by
filename or by trust in a download.

**Mirror verification — CLOSED 2026-08-17.** This section previously recorded
that the Drive-side copy had not been hashed, after `drive.mount` failed
unattended twice. The project lead unblocked the mount and the mirror was hashed
during the Stage 1b run:

```
mirror  <drive>/results/01_baseline_berturk/dev_predictions.csv
        736,591 bytes   a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
local   736,591 bytes   a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346
```

**Byte-identical.** The provenance of every Stage 1 number now rests on a hash of
the only durable copy, not on the eight reproduced figures alone. Recorded in the
same sweep: `results/03_defense/run_raw/dev_predictions.csv` carries the **same**
sha256, so the phase-03 control and the phase-01 baseline are one file.

---

## 3. The primary result, and the honest problem with it

The design calculation in C9-4 said this dataset resolves an AUC difference to
roughly ±0.03–0.04. The observed interval is [+0.0103, +0.0585], width 0.048 —
almost exactly as predicted, and **it spans all three bands**: its lower end sits
below the SMALL floor (0.02) and its upper end above the LARGE threshold (0.05).

So the data cannot even localise the gap to one of the three verdicts. Reporting
`INTERMEDIATE` is not a hedge chosen after the fact; it is what a 355/259 and
565/3585 design can support, which is why the thresholds were fixed from the
denominators before the run rather than from the result after it.

**A larger dev split would resolve this.** Nothing else here will.

---

## 4. Where the difference actually lives (C9-7)

| slice | class | n | mean | Q1 | median | Q3 | share ≤ 0.5 |
|---|---|---|---|---|---|---|---|
| `lexicon_hit` | gold OFF | 355 | 0.8524 | 0.8439 | **0.9650** | 0.9872 | **0.1070** |
| `lexicon_hit` | gold NOT | 259 | 0.2438 | 0.0287 | 0.1057 | 0.3608 | 0.8185 |
| `lexicon_free` | gold OFF | 565 | 0.5285 | 0.2162 | **0.5861** | 0.8193 | **0.4372** |
| `lexicon_free` | gold NOT | 3585 | 0.0999 | 0.0131 | 0.0313 | 0.0980 | 0.9537 |

This is the finding in one row: the median offensive row **with** profanity scores
0.965; the median offensive row **without** it scores 0.586. Both are above 0.5,
but the second sits almost on the boundary, and **43.7% of profanity-free
offensive content falls at or below the threshold against 10.7% of the
profanity-carrying kind**.

The shift is specific to the OFF class in the sense that matters: gold-NOT rows
in `lexicon_free` are scored *lower* than gold-NOT rows in `lexicon_hit` (median
0.031 vs 0.106), i.e. the whole slice is shifted down, and the offensive rows are
shifted down into the decision boundary while the benign rows are shifted down
into safety. That is the mechanism behind both halves of the phase-01 result —
the missed offense **and** the 4× false-positive rate inside `lexicon_hit`.

---

## 5. Matched operating points (C9-8) — computed under a **defective specification**

> **Status, added 2026-08-17 after review by the project lead.** C9-8 is a
> **spec defect, not a finding.** The numbers below remain here as a record of
> what was computed; **none of them is usable as evidence and none enters the
> report.** The reason is spelled out below and is now recorded as a dated
> addendum in `phases/09_deeper_analysis.md`. In particular the equal-flagging-rate figure
> (`lexicon_free` recall 0.9681) may **not** be read as "the ranking was there
> all along" — that reading is exactly the base-rate confound the figure fails
> to remove.

Reference points at the frozen threshold:

| reference | precision | recall | flag rate |
|---|---|---|---|
| `lexicon_hit` @ 0.5 | 0.8709 | 0.8930 | 0.5928 |
| `lexicon_free` @ 0.5 | 0.6570 | 0.5628 | 0.1166 |

Moving one slice's threshold to match the other's operating point:

| comparison | t | precision | recall | 95% CI |
|---|---|---|---|---|
| `free` at `hit`'s **precision** (0.8709) | 0.8516 | 0.8741 | **0.2088** | [0.0779, 0.2850] |
| `free` at `hit`'s **flag rate** (0.5928) | 0.0275 | 0.2224 | **0.9681** | [0.9504, 0.9823] |
| `hit` at `free`'s **precision** (0.6570) | 0.0393 | 0.6579 | **0.9915** | [0.9803, 1.0000] |
| `hit` at `free`'s **flag rate** (0.1166) | 0.9887 | 0.9861 | **0.2000** | [0.1831, 0.2141] |

No match failed. CIs re-select the threshold inside every bootstrap replicate,
so they carry the selection variance.

**Why the specification is defective.** C9-8 called these "two different ways of
removing the threshold confound". They remove the **threshold** confound and
leave the **base-rate** confound fully intact. Precision depends on the base rate
directly. Recall at a fixed flagging rate depends on it too, because which rows
sit in the top *q* of a slice depends on that slice's OFF/NOT mixture. Between
two slices that differ 57.8% vs 13.6% — the exact variable this stage exists to
control for — neither comparison can be evidence about ranking quality.

**ROC-AUC is the only genuinely base-rate-free comparison in this stage.** C9-3
made it the primary, and that is the part of the design that survives.

The original draft of this section read the two matchings as pointing in opposite
directions and treated that as a result. **It is not a result.** The
equal-flagging-rate figure buys recall 0.9681 at **precision 0.2224**, flagging
59% of a slice that is 13.6% offensive; it is neither an achievable operating
point nor evidence that "the threshold was the whole problem". The
equal-precision figure inherits the same defect from the other side. Both are
withdrawn as evidence, and the withdrawal is recorded rather than the text
quietly rewritten.

---

## 6. Average precision (C9-9 — reported, not admissible)

`lexicon_hit` **0.9477**, `lexicon_free` **0.6479**.

C9-9 fixed in advance that AP may not argue either side of the verdict, because
it is base-rate sensitive and the slices differ 57.8% vs 13.6%. That ban is
demonstrated rather than asserted: `tests/test_stage1_auc.py` shows AP moving by
more than 0.1 under a manipulation that changes only the base rate, while AUC
does not move at all. The two numbers above are reported because the
pre-registration said they would be, and they are not evidence for anything here.

---

## 7. Sensitivities (C9-10) — one of them matters a great deal

| | AUC hit | AUC free | gap | shift vs primary |
|---|---|---|---|---|
| **primary** | 0.9306 | 0.8962 | **+0.0345** | — |
| S1 — `MIN_ROOT_LEN` leak removed (28 rows) | 0.9306 | 0.8907 | +0.0399 | +0.0054 |
| S2 — suspect-root rows removed (248 rows) | 0.9023 | 0.8962 | **+0.0062** | **−0.0283** |
| S3 — ties counted as 0 | 0.9306 | 0.8961 | +0.0345 | 0.0000 |
| S3 — ties counted as 1 | 0.9306 | 0.8962 | +0.0345 | 0.0000 |

Both reimplementations were checked against the earlier records before use and
reproduced them exactly: S1 finds the same **28** rows phase 08 recorded, S2 the
same **248** exclusions (175 NOT / 73 OFF) as
`results/02_failure_analysis/slice_sensitivity.json`.

**S3 closes a question:** the tie convention is worth nothing at all here — the
gap is identical to four decimals whether ties count 0, 0.5 or 1. The C9-2
convention could have been chosen either way without effect.

**S1's asymmetry turns out to be empty.** The registered rule drops gold-OFF rows
only, which invited the objection that it biases AUC by removing positives. The
symmetric version (not pre-registered, run for completeness) drops the same 28
rows, because **zero** gold-NOT `lexicon_free` rows carry a short lexicon entry.
The two variants agree to six decimals.

**S2 is the one that matters.** Excluding the rows whose only lexicon match is a
suspect root — `allah`, `ana`, `cim`, `emi`, `göt`, `mal`, `sie` — drops the AUC
gap to **+0.0062**, below the SMALL floor. The same correction *widens* the
recall gap, from +0.3301 to +0.3662 (phase 02).

**The same slice-definition repair moves recall and AUC in opposite
directions.** Under the cleaner definition the two slices are all but
indistinguishable in ranking quality while diverging further in recall. That is a
strong qualification in the narrowing direction, and it is stated as a
qualification: C9-10 fixed in advance that no sensitivity may overturn the
primary verdict, and this one does not. The verdict remains `INTERMEDIATE` on the
frozen slice definition.

---

## 8. What this obliges (C9-6) — **applied 2026-08-17**

C9-6 was written before the run. For `INTERMEDIATE` it obliges: **both numbers
reported, and the report stating plainly that this analysis cannot separate the
two contributions.** All four requirements are now in the report:

| # | requirement | where |
|---|---|---|
| 1 | the AUC pair and the gap with its CI, beside the recall gap | §4.2, new subsection *Eşikten bağımsız karşılaştırma* |
| 2 | the recall gap is **not** mostly a ranking-quality gap; the model ranks this content well (0.8962) but scores it near the threshold | §4.2, §4.3, §4.10 row 2b |
| 3 | calibration-to-base-rate vs genuine under-confidence is **not separable** | §4.2 closing paragraph, §5.12 |
| 4 | the S2 qualification, pointing the other way from its effect on recall | §4.5, §5.3 *Aynı düzeltme, iki ölçütte zıt yön*, §5.13 row 3c |

Beyond the four, the claim itself was audited and rewritten. §4.3's diagnosis
sentence read *"the model detects offensive VOCABULARY, not the offensive ACT"*;
it now reads that vocabulary presence is what drives the **decision**, with an
explicit paragraph stating that this does **not** mean the model cannot
discriminate offense without profanity — AUC 0.8962 says otherwise. §4.1's
summary bullet and §4.4's "topic effect: religion, politics" aside were corrected
on the same grounds. §1.4 now says that recall, though base-rate-free, is
**threshold**-dependent, and points forward; §2.7 gives the ROC-AUC definition,
its tie convention, and why it is admissible across slices where macro-F1 is not.

**Not obliged, and not done:** the wholesale narrowing that C9-6 attaches to a
`NARROWS` verdict. That branch did not fire.

**Withdrawn:** the matched-operating-point numbers, on the spec defect in §5.
They do not appear in the report in any form.

**What survives untouched.** The operational finding is unaffected: at the
deployed threshold, 43.7% of profanity-free offensive content is scored at or
below 0.5 against 10.7% of profanity-carrying content, and the phase-01 confusion
matrix stands. The phase-02 diagnosis (the model keys on offensive vocabulary)
and the phase-08 second predictor (being addressed) are about *what drives the
score*; this stage is about *where the score lands*. Neither displaces the other.

**What is weakened.** Any wording implying the model cannot *detect* offense
without profanity. It can rank it. The report must not say otherwise.

---

## 9. Limitations

- **The design cannot resolve its own question.** The CI spans all three
  pre-registered bands. This is a property of 355/259 and 565/3585, known in
  advance from C9-4, not a surprise.
- ~~The Drive mirror was not byte-compared.~~ **Closed 2026-08-17**: the mirror
  hashes to `a2f5bddf…538a6346`, byte-identical to the local copy (§2). This
  limitation no longer applies to any Stage 1 number.
- **One checkpoint.** Everything here is `best.pt` = epoch 1. Phase 02 recorded
  that epochs 1 and 3 tie on macro-F1 while disagreeing on 198/4,764 rows, so the
  AUC figures inherit that checkpoint dependence and it is unmeasured.
- **Frozen slice definition.** Both known defects are carried, not repaired
  (S1, S2). The lexicon and `MIN_ROOT_LEN` were not touched.
- **AUC is one summary of a curve.** Two slices can share an AUC with different
  curve shapes; no ROC curves were compared point by point.
- **Dev only.** The test set is spent and stays spent.

## 10. Questions this opens (measurement, not proposals)

- Whether the observed downward score shift in `lexicon_free` matches the shift a
  Bayes-optimal model would show given a 13.6% versus 57.8% base rate is
  **measurable and unmeasured**. That measurement, not this stage, is what would
  separate "correctly calibrated" from "under-confident".
- Whether the AUC gap survives on the other checkpoint.
- The phase-08 `MIN_ROOT_LEN` recall **bound** (+0.3529) can now become a
  measurement, since the prediction dump is local. Not done here — it is not part
  of Stage 1 and was not authorised.
