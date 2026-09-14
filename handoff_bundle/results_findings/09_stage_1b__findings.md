# Phase 09 Stage 1b — did the intervention improve ranking, or move scores?

Pre-registration: `phases/09_deeper_analysis.md`, C9-12 … C9-17, committed at
**910d21e** before any number below existed. Machine-readable record:
`stage1b_defense_auc.json` (sha256 `3471a7fc…`, 4,203 bytes — the Drive-side file
and this repo copy are byte-identical). Driver: `phase09_stage1b_defense_auc.py`.
Tests: `tests/test_stage1b_defense_auc.py` (16).

Run on Colab against the Drive mirror, 2026-08-17. Read-only: no training, no
forward pass, dev split `034415af3a23b388` only, official test set untouched.
Measurement only — no intervention is proposed (C9-17).

---

## 1. The answer

**Primary verdict (`lexicon_free`): `FLAT`.** The recall gain did **not** come
from better ranking.

```
ΔAUC(lexicon_free) = AUC(+1a+1b+D) − AUC(run_raw)
                   = −0.005587   [−0.013387, +0.002366]      -> FLAT (C9-15, branch 2)
```

The interval contains zero, so branch 2 fires. Branch 2 is the one C9-15 named
in advance as *"threshold crossing, not better ordering"*.

This is a stronger negative than a bare null. The interval's **upper** end is
+0.0024 — an order of magnitude below the 0.01 floor fixed at 910d21e. The data
do not merely fail to show an ordering improvement; they **exclude** one large
enough to account for a +0.0336 recall gain.

**Control verdict (`lexicon_hit`): `ORDERING WORSENED`**, and this is where the
pre-registered prediction failed. See §4.

---

## 2. Provenance (C9-12)

| role | run | sha256 | rows |
|---|---|---|---|
| control | `run_raw` | `a2f5bddf…538a6346` | 4,764 |
| treatment | `run_1a1b_d` | `e525eaab…de6bbd4a` | 4,764 |

Both reproduce every figure recorded for them in
`results/03_defense/comparison.json` — macro-F1, `OFF`-recall, both slice
recalls, the `lexicon_hit` false-positive rate and the total false-positive
count — checked before any new quantity was computed. The two dumps are aligned
row-for-row on `row_id`, with `gold` and `slice` asserted equal on every row,
because a silently unpaired comparison would return a *tighter*-looking result
rather than an obviously broken one.

**A fact C9-12 said to report rather than assume: `run_raw` is byte-identical to
the phase-01 baseline dump.** Same sha256, same 736,591 bytes. The phase-03
control and the phase-01 baseline are one file, not two runs that happen to
agree on their scalars. This also explains why the control's slice AUC gap here
(+0.034461) equals Stage 1's to six decimals — it is the same data, and that
agreement is a consistency check passed, not a coincidence.

---

## 3. Where the +0.0336 actually came from

Threshold crossings under the frozen 0.5 rule, gold-`OFF` rows:

| slice | `NOT`→`OFF` | `OFF`→`NOT` | net | net / n | recorded recall Δ |
|---|---:|---:|---:|---:|---:|
| `lexicon_free` | 52 | 33 | **+19** | +19/565 = **+0.0336283** | **+0.0336283** |
| `lexicon_hit` | 13 | 28 | **−15** | −15/355 = **−0.0422535** | **−0.0422535** |

The net crossings reproduce the recorded recall deltas **exactly**, to ten
decimal places. The gold-`NOT` side closes the same way: +29 net in
`lexicon_free` and +3 in `lexicon_hit` sum to +32, and the recorded
false-positive count went 213 → 245.

So the entire reported effect of `+1a+1b+D` on dev is 19 rows of one slice and
15 of the other changing sides of a fixed threshold, plus 32 new false
positives — with **no measurable change in how the rows are ordered** in the
slice the intervention targeted.

**And the movement is not a uniform shift.** In `lexicon_free`'s gold-`OFF`
rows the median rises 0.5861 → 0.7818 while the first quartile *falls*
0.2162 → 0.0776 and the third rises 0.8193 → 0.9921. Scores are being pushed
toward both extremes, not slid upward together. That is the signature of the
overconfidence already on record for this variant — fitted temperature **1.9732**
against the baseline's 0.9948, ECE 3.8× (`results/04_calibration/`) — and it was
named in C9-14 as the *a priori* likely mechanism before this stage ran.

---

## 4. The control (C9-16) — the pre-registered prediction failed

C9-16 recorded a prediction before the number existed:

> if the mechanism is a global score shift, `lexicon_hit` AUC should also be flat
> while its recall falls.

It is not flat.

```
ΔAUC(lexicon_hit) = −0.025401   [−0.042863, −0.008646]   -> ORDERING WORSENED
```

The interval lies entirely below zero, so branch 1 fires. **The intervention
measurably degraded ranking quality in the slice where the lexicon fires**, while
leaving it unchanged, within a tight bound, in the slice it was designed to help.

That rules out the simplest account. `+1a+1b+D` is not a uniform recalibration
that happens to move some rows across a line; it is a change that **damaged the
ordering** precisely where profanity is present. `1b`'s stated purpose was the
profanity-bearing false positives, so the slice affected is the slice targeted —
but this stage measured the combined `1a+1b+D` run, so **the damage is not
attributed to any one component here**, and no attribution is claimed.

**The gap narrows on the threshold-free metric too, and for the wrong reason.**
The slice AUC gap goes +0.0345 → **+0.0146**, driven by `lexicon_hit` falling
0.9306 → 0.9052 rather than by `lexicon_free` rising — it fell slightly, to
0.8906. Report §1.7 pre-registered exactly this failure mode for the recall gap
(*"a within-gap trade where `lexicon_hit` recall falls and the gap narrows for
the wrong reason"*). The same trade is now visible on a metric that does not
depend on where the threshold sits.

---

## 5. What this does and does not establish

**Establishes.** The dev-set recall gain reported for `+1a+1b+D` is a
threshold-crossing effect. Ordering in `lexicon_free` did not improve; an
improvement of even +0.0024 is outside the interval. Ordering in `lexicon_hit`
got worse, with the interval excluding zero.

**Does not establish.** Nothing about *why* the scores moved — the miscalibration
is a recorded correlate, not a demonstrated cause; that would need an ablation.
Nothing about which component (1a, 1b or D) is responsible, since only the
combined run was compared. Nothing about the test set: this is dev only, and the
+0.0358 test gain is not re-examined here, so whether the same mechanism holds
there is **unmeasured**.

**Does not overturn phase 03.** The gain was real and it replicated; that
finding stands as recorded. What changes is the mechanism behind it, and
therefore what may be claimed about the model having learned anything. Report
§5.4 already refused a mechanism claim on other grounds; this measurement is
evidence in the same direction, from a different angle.

---

## 6. Limitations

- **Dev only, one checkpoint, one seed.** The treatment is `best.pt` = epoch 3,
  the control epoch 1; §5.6 and §5.7 of the report apply unchanged.
- **Combined run.** 1a, 1b and D are not separable here.
- **`FLAT` is a bounded null, not proof of zero.** It excludes an ordering gain
  above +0.0024 on dev; it does not prove the ordering is literally unchanged.
- **The two stages' CIs for the same control slice differ in the last decimals**
  (Stage 1: [0.8821, 0.9095]; Stage 1b: [0.8820, 0.9094]) because the bootstrap
  schemes differ — Stage 1 resamples all four slice × gold cells in one stream,
  Stage 1b resamples per slice for the paired design. Same data, same estimator,
  different resampling; the point estimates are identical.
- **No attribution or ablation was run**, here or anywhere in this project.

## 7. What this would oblige in the report — drafted, not applied

Not covered by C9-6, which governs Stage 1 only. Proposed, for the project
lead's decision:

1. §4.6, after the `+1a+1b+D` paragraph: the gain is 19 rows crossing the
   threshold, with no measurable ordering improvement (ΔAUC −0.0056
   [−0.0134, +0.0024]).
2. §4.6 or §4.7: `lexicon_hit` ordering measurably worsened (−0.0254
   [−0.0429, −0.0086]), i.e. the within-gap trade §1.7 warned about appears on
   the threshold-free metric as well.
3. §5.4, which currently says the mechanism of the gain cannot be separated:
   add that it is now known **not** to be an ordering improvement on dev, which
   narrows the space of live explanations without closing it.
