# Protocol — m1_lexicon: terlik (balanced) versus the historical karaliste, on the frozen dev split

- **Status:** pre-registered 2026-09-17, before the comparison number exists (m1 spec §6, §8:
  "Coverage comparison: terlik balanced vs the historical karaliste, recall and FPR side by
  side, plus a count of disagreement cases"; `modules/README.md` "Freeze before you measure").
- **Script:** `eval/m1_terlik_vs_karaliste.py`. **Result:** `eval/results/m1_terlik_vs_karaliste.json`,
  committed with `git add -f` in the change that references this protocol.

## 1. Inputs (all frozen; hashed by the script, which stops on any mismatch)

| input | path | role |
|---|---|---|
| frozen karaliste slice | `eval/frozen/study_slice_dev.json` (sha256 in `eval/m4_stage1b.py::INPUTS`) | the `lexicon_hit` / `lexicon_free` label of every dev row under karaliste |
| derived terlik labels | `eval/derived/m1_lexicon_dev_seed42.json` (protocol-bound, `rows_sha256` inside) | `lexicon_hit_raw` of every dev row under m1 (terlik balanced, through m0 / m2 / m6 / m1) |
| gold OFF / NOT | `diagnosis/results/01_baseline_berturk/dev_predictions.csv` (`gold` column; sha256 `a2f5bddf…`, not in git) | the offensive label per row |

The official test set is not read. Rows: the 4,764 dev ids in `dev_ids` order; the script stops
if the three inputs do not cover the same id set.

## 2. Quantities (point estimate + 95 % percentile-bootstrap CI over rows, 2,000 resamples, seed 42)

For each lexicon L ∈ {karaliste, terlik}: treating "L hits the row" as a prediction of OFF,

- **recall** = hits among gold-OFF rows / gold-OFF rows;
- **FPR** = hits among gold-NOT rows / gold-NOT rows;
- **precision** = gold-OFF among hits / hits (reported, not headline);
- **hit count** and share of dev.

Paired differences terlik − karaliste for recall and FPR with a paired bootstrap CI.

**Disagreement**: the 2×2 table of (karaliste hit, terlik hit) over all rows and over gold-OFF
rows; counts of rows hit by exactly one lexicon, with 20 examples of each direction listed by
row id and surface (no corpus text beyond the matched surface is written to the result).

**Collision context**: the share of terlik-free rows carrying at least one `SUBSTRING_COLLISION`
guard, so the reader can see how much of the disagreement is the boundary rule at work.

## 3. Decision rule

None. This is a comparison the report must contain (spec §5: karaliste is a licence and precision
risk kept only as a comparison point). No threshold, no slice and no module behaviour changes on
its outcome. The frozen slice stays karaliste's (m1 spec §1).

## 4. Failure conditions

Input hash mismatch, id-set mismatch, or a derived file whose `protocol.committed_and_unchanged`
is false → the script exits 2 and writes nothing.

---

## Amendment 2026-09-18 (re-run on the regenerated derived file)

The derived terlik file is regenerated on the implemented m0 / m2 / m6 / m1 (dev protocol
amendment of 2026-09-18). The comparison is re-run unchanged in its pre-registered quantities:
the headline `terlik` numbers keep reading `lexicon_hit_raw` (§1), so the 2026-09-17 result and
this one measure the same thing on the same population.

One block is **added**, not substituted: `terlik_any_channel` — the same quantities with
`lexicon_hit` (raw OR normalized) as the predictor, and the count of rows that only the normalized
channel hits. It is reported next to the raw-channel numbers because the A-head pseudo-label uses
`lexicon_hit` (train protocol §5) and the reader must be able to see how much the normalized
channel adds on dev. The decision rule (§3) is unchanged: none.
