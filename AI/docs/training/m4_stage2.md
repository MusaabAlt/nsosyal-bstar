# Colab Pro+ handoff — m4 stage 2: influence-function hardening of the lexicon-free slice

State: **BLOCKED_BY_POLICY and BLOCKED_BY_DATA**. Two things must exist before the first stage-2
number (m4 spec §7, §9, §10): (1) a pre-registered precision budget committed in `protocols/`
with a version-control timestamp earlier than the result, and (2) the labelled evaluation slice
of lexicon-negative positives with per-category agreement (m4 spec §8: 400 positives → ±4.8
points). The GPU procedure below is written so that, once those exist, it can be run without
redesign. Nothing here is executed until then, and a negative outcome is a delivered result
(spec §10).

## 1. Purpose

Raise recall on the **lexicon-free slice** (offensive posts with no profane root; recall 0.5628
at baseline, 0.6367 after stage 1) by retraining m3's encoder on a **selected** subset of
existing training rows chosen with influence functions — example selection, never generation
(spec §3, §4).

## 2. Consumer

The retrained encoder is an **m3 artifact** (ADR-006): it replaces the m3 artifact under m3's
discipline (own MANIFEST row, own thresholds derived on dev, decision-flip table). m4 consumes
nothing new at inference; its deliverable is the `binary_offensive` / `C1`–`C5` rows re-derived
for the new artifact.

## 3. Architecture / base checkpoint

Start from the current m3 artifact (the frozen binary baseline `m3-berturk-pytorch-fp32-epoch1`
today; the multi-head artifact of `m3_encoder.md` once it exists). Same heads, same tokenizer.
Method: checkpoint-based influence, `captum.influence.TracInCP` (spec §4.1) over the epoch
checkpoints saved by `training/m3_encoder/train.py` (`latest.pt` per epoch — keep every epoch's
weights for this run: pass `--keep-epoch-checkpoints`, to be added to `train.py` when this task
unblocks).

## 4–6. Data, sources, licences

- Training rows: the frozen split's train half (26,992 rows), same corpus and licence as
  `m3_encoder.md` §4–§6.
- **Probe set** (the cases to move): veiled Turkish examples mined from the project's own dev data
  by two signals — disagreement between the raw and normalized channels, and low confidence inside
  the lexicon-free slice (`eval/frozen/study_slice_dev.json`). Mining script to be added under
  `training/m4_implicit/mine_probes.py` when unblocked; it reads `dev_predictions.csv` and the
  frozen slice, never the test set.
- **Evaluation slice**: the human-labelled lexicon-negative positives (BLOCKED_BY_DATA).

## 7. Drive layout

```
MyDrive/nsosyal-bstar/runs/m3_multihead/<date>/epoch_0.pt … epoch_2.pt   (checkpoints for TracIn)
MyDrive/nsosyal-bstar/labels/c_eval_slice.jsonl                          (labelled slice)
MyDrive/nsosyal-bstar/runs/m4_stage2/<date>/                              (--out)
```

## 8–11. Preprocessing, labels, splits, leakage

As in `m3_encoder.md`. Additionally: the probe set is drawn from dev, the evaluation slice is a
frozen subset of dev committed with its size, labelling date and agreement (spec §9 "Frozen dev
slice"); once a number is published against it, it does not change. Selected training rows are
listed by id in the result file so the selection is auditable.

## 12–17. Seeds, versions, install, runtime, resources

As in `m3_encoder.md`, plus `captum>=0.7` (BSD-3). TracInCP over 27k training rows × 3
checkpoints on an A100: several hours of gradient computation; store per-checkpoint influence
scores on Drive incrementally.

## 18–26. Procedure and hyperparameters

1. Compute TracInCP influence of every training row on every probe example, per checkpoint;
   sum over checkpoints.
2. Select the top-k training rows by aggregate positive influence on the probe set (k is a
   pre-registered protocol parameter, not tuned on the evaluation slice).
3. Retrain m3 from the base checkpoint on the selected rows plus the full training set with
   the selected rows up-weighted (weight = protocol parameter), same hyperparameters as
   `m3_encoder.md` §19–26.
4. Export as an m3 artifact (`m3-berturk-stage2-<date>`).

## 27. Metrics

Recall on the lexicon-free slice before / after with CIs and the precision cost in the same
sentence; risk–coverage curve at equal coverage; per-code C1–C5 where the slice allows; the
precision budget check (spec §7).

## 28. Acceptance

Precision drop within the pre-registered budget → adopt; exceeded → keep stage 1 and document
stage 2 as a measured negative (spec §10). Either way the result ships.

## 29–33. Outputs, naming, provenance, placement, MANIFEST

As in `m3_encoder.md`, artifact id `m3-berturk-stage2-<date>`, plus the selection list and the
influence-score file under the run directory.

## 34. Thresholds after training

Full re-derivation of every m3 row on dev for the new artifact (ADR-006 consequence: a new m3
artifact re-couples every m3 threshold).

## 35. Verification

As in `m3_encoder.md` §35 plus `python -m eval.m4_stage1b` re-run against the new artifact's
scores (the stage-1b protocol compares at equal coverage).

## 36–37. Failure and stages

Influence computation is the cost centre; checkpoint it per training-row chunk. Stages: probe
mining 10 min · influence 2–6 h · retrain 25 min · eval 5 min.
