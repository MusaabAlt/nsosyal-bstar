# Protocol — m4 stage 1b: lexicon-conditioned `binary_offensive` threshold vs stage 1

- **Status:** pre-registered. Committed BEFORE any stage-1b number was computed.
- **Owner:** Musaab (m4_implicit)
- **Date:** 2026-09-16
- **Governs:** m4 spec §4 "Stage 1b", ADR-006 decision 3 ("measured against stage 1 at
  equal coverage before it replaces it"), m4 spec §6 (no recall gain without its
  precision cost; compare at equal coverage).
- **Implementation:** `AI/eval/m4_stage1b.py`, run exactly as in §8. Output
  `AI/eval/results/m4_stage1b.json`, committed with `git add -f` together with the
  decision (eval/README.md). The official test set is not opened at any step.

## 1. Question

Does replacing the stage-1 global threshold on m3's raw binary offensive score
(`binary_offensive.threshold` = 0.320188, `protocols/threshold_derivation_binary_offensive_stage1.md`)
with two thresholds conditioned on m1's raw-channel lexicon signal (`t_hit` when
`m1_lexicon.lexicon_hit_raw` is true, `t_free` when false) raise recall on the
lexicon-free slice at equal coverage, without costing more than the precision budget?

## 2. Data (all dev; nothing from test)

| input | file | sha256 (must match, else stop) |
|---|---|---|
| scores, gold, text | `diagnosis/results/01_baseline_berturk/dev_predictions.csv` (study epoch-1 BERTurk p(OFF) on raw text, 6 decimals; `m3-berturk-pytorch-fp32-epoch1`) | `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346` |
| CAL / EVAL halves | `diagnosis/results/04_calibration/cal_eval_split.json` (`cal_row_ids`, `eval_row_ids`) | `6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899` |
| PRIMARY slice | `AI/eval/frozen/study_slice_dev.json` (study karaliste matcher, frozen) | `94754632fb66d543b7c1e84bc4e396b65585f8adba90a4f2fc87aca8f2acbed8` |
| dev split (hash only, not read) | `diagnosis/data/splits/split_seed42.json` | `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2` |

- **Scores are not recomputed.** m3 is not run. The CSV scores are the ones stage 1 was
  fitted on (owner decision D, 2026-09-16).
- Gold: CSV `gold`, `OFF` = positive, `NOT` = negative.

**Integrity checks (all must pass, else stop and report; no number is produced):**
1. The CSV has 4,764 rows with unique `row_id`s. CAL and EVAL are disjoint, 2,382 rows each, and together they are exactly the CSV's row_ids.
2. The frozen slice file lists all 4,764 CSV row_ids. Its `split.dev_fingerprint` is `034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4`. Its `verified_against.sha256` equals the CSV hash above.
3. EVAL has 460 OFF / 1,922 NOT, and 2,073 frozen-lexicon_free / 309 frozen-lexicon_hit rows (cal_eval_split.json reproduction checks).
4. **Stage-1 reproduction.** Refitting stage 1 on CAL with the rule in §4 gives
   t = 0.320188. On EVAL it gives tp 343 / fp 184 / fn 117 / tn 1,738.

## 3. Condition signal (terlik), and the two slices

- **Condition signal** = `m1_lexicon.lexicon_hit_raw`, computed now (owner decisions B, C).
  It is computed exactly as it will be read at runtime: each CSV `text` goes through
  `pipeline.run.Pipeline` with the modules `m0_charsafe`, `m2_deobf`, `m6_target` and
  `m1_lexicon`, in registry order. The value is read from
  `result.signals["m1_lexicon"]["lexicon_hit_raw"]`. m3, m4 and m5 are not run. Record the
  m0 and m1 versions and the terlik version. If m1 fails, degrades, or returns a non-bool
  on any row, stop.
  - It is `lexicon_hit_raw`, not `lexicon_hit`. `lexicon_hit` also ORs in the normalized
    channel, which would drift from this fit once m2 is implemented.
  - The frozen karaliste slice is NOT the condition signal. At runtime there is no
    karaliste, only m1.
- **PRIMARY slice (decides):** the frozen study slice, `lexicon_free` / `lexicon_hit` from
  `AI/eval/frozen/study_slice_dev.json` (m1 spec §1). It is comparable with the published
  stage-1 numbers (m4 spec §2).
- **SECONDARY slice (reported, never decides):** the terlik slice. `lexicon_hit_raw` false
  = lexicon-free.
- Report the 2×2 agreement between the two slices on EVAL.

## 4. Fit (CAL half only)

- **Decision rule for fitting and evaluation:** flag iff `score > t`, as in stage 1
  (C12-3). The runtime rule in `decision/fusion.py` is `score >= t`. For every threshold
  reported, count the EVAL rows whose score equals it exactly (§6).
- **Cost:** `Cost = (FP + r·FN) / N_CAL`, with **r = 3**. A false negative costs three
  false positives.
- **Stage 1 (reference):** candidates = distinct CAL scores. Take the minimum cost; ties
  go to the lower t. Its CAL flag count is **K**.
- **Stage 1b:**
  - Candidate `t_hit` = the distinct CAL scores among CAL rows with `lexicon_hit_raw`
    true. Candidate `t_free` = the distinct CAL scores among CAL rows with it false.
    Each slice is flagged by its own threshold.
  - **Coverage constraint (owner decision E):** the total CAL flag count
    `n_hit(t_hit) + n_free(t_free)` must equal K. If no candidate pair reaches exactly K,
    use the largest achievable count **K\* < K**. Record the gap `K − K*`.
  - Among pairs with count K\*, choose the minimum CAL cost. Ties go to the lower
    `t_hit`, then the lower `t_free`.
  - **Known limit:** because of the `>` rule, a slice's lowest-scoring CAL row can never
    be flagged. Stage 1 has the same limit.
- Also report, not deciding: CAL cost and CAL flag count for both stages.

## 5. Evaluation (EVAL half only)

The EVAL half was already used in the study, to evaluate the study's S1b (the stage-1
global threshold) and its slice-conditional S2 (`12_threshold_policy`). This comparison is
therefore not an untouched held-out test. The CI below is conditional on that reuse, and
any report of this result must say so.

Computed for stage 1 and stage 1b, with the fitted thresholds fixed:

| metric | definition |
|---|---|
| **lexicon-free recall (PRIMARY)** | TP / OFF among EVAL rows the frozen slice marks `lexicon_free` |
| **overall precision** | TP / flagged, over all EVAL rows |
| reported alongside | lexicon-hit recall (frozen slice); overall recall; FPR; slice gap (hit recall − free recall); EVAL flag count and flag rate (coverage); confusion matrix |
| SECONDARY | the same recall and gap on the terlik slice |

**Paired bootstrap, lexicon-free recall difference:**
- Δ = recall_free(1b) − recall_free(1) on the PRIMARY slice.
- Resample the 2,382 EVAL rows with replacement, the same resample for both stages,
  **2,000 resamples, seed 42** (`random.Random(42)`, one `choices` call of k = 2,382 per
  resample).
- 95% percentile CI. Lower bound = the sorted Δ at index 50, upper bound = the sorted Δ
  at index 1,949 (0-based), so 50 resamples lie outside on each side.
- A resample with no lexicon-free OFF row is dropped and counted. If any are dropped, the
  indices are rescaled to the kept count, `floor(0.025·B')` and `ceil(0.975·B') − 1`.
- The same procedure gives descriptive CIs for Δ on the SECONDARY slice and for the
  overall-precision difference. Neither decides.

## 6. Decision rule (pre-registered)

**Adopt stage 1b if and only if both hold:**
1. The lower bound of the 95% CI for the PRIMARY Δ is **strictly greater than 0**.
2. The overall precision drop on EVAL, point estimate `precision(1) − precision(1b)`, is
   **≤ 0.02**.

Otherwise keep stage 1. The SECONDARY slice cannot change the decision.

- **If adopt:** `decision/thresholds.yaml` `binary_offensive` becomes:
  - `threshold: 0.320188`, stage 1, kept as the fallback when the signal is absent
  - `threshold_when: {signal: m1_lexicon.lexicon_hit_raw, true: t_hit, false: t_free}`

  The thresholds artifact id is bumped and `derived_on` is updated. A derivation file
  `protocols/threshold_derivation_binary_offensive_stage1b.md` records the numbers, the
  `lexicon_hit_raw` choice (decision B) and the tie rows at `>=`, and `artifacts/MANIFEST.md`
  gets a change-log row. All of this goes in the same commit as the result file.
- **If keep:** no change to `decision/thresholds.yaml`. The result file is committed as a
  measured negative (m4 spec §10).

Either way, the report gives the recall change and the precision change in the same
sentence (m4 spec §6).

## 7. What this protocol does not do

- No stage-2 work and no C1–C5 thresholds.
- No rescoring with m3.
- No use of the normalized channel.
- No tuning of r, of the precision budget, of the bootstrap settings or of the
  tie-breaks after seeing any number.
- A change to any of these is a new protocol with a new commit, not an edit of this one.

## 8. Command

From `AI/`, after this protocol is committed:

    python -m eval.m4_stage1b --r 3 --precision-drop-budget 0.02 --n-boot 2000 --seed 42 --out eval/results/m4_stage1b.json

The result file records this protocol's commit hash and the input hashes it checked.
