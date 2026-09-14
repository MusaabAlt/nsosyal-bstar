# NSosyal B* — repo tree and convention extraction

Read-only audit performed 2026-08-18. `git status --porcelain --untracked-files=no`
was empty before and after and verified identical by diff. Nothing in the repo was
created, edited or deleted except this file. No training, no forward pass, no GPU,
official test set not opened.

---

# 1. `git ls-files`

```
.gitignore
README.md
config.py
conftest.py
data/beyhan/.gitkeep
data/coltekin/.gitkeep
data/lexicon/.gitkeep
data/mayda/.gitkeep
data/splits/split_seed42.json
day1_gate_en.py
demo/README.md
demo/__init__.py
demo/app.py
demo/build_assets.py
demo/examples.json
docs/HANDOFF.md
docs/PROJECT_HISTORY.md
docs/RESULTS_LOG.md
docs/claude_master_brief.md
docs/handoff_2026_08_15.md
docs/nsosyal_pycharm_setup_prompt.md
docs/phase_briefing.md
docs/repo_inventory_2026_08_17.md
legacy/README.md
legacy/day1_gate.py
legacy/day1_gate2.py
legacy/main.py
notebooks/.gitkeep
notebooks/colab_phase01_runbook.md
phase01_baseline.py
phase03_compare.py
phase03_make_augmentation.py
phase03_train_defense.py
phase03_train_errors.py
phase04_calibration.py
phase05_final_test.py
phase05_paired_deltas.py
phase08_lexical_analysis.py
phase09_stage1_auc.py
phase09_stage1b_defense_auc.py
phases/01_baseline_diagnosis.md
phases/03_defense_design.md
phases/04_calibration.md
phases/07_report.md
phases/08_lexical_analysis.md
phases/09_deeper_analysis.md
phases/10_sablon_mapping.md
report/01_veri_ve_deney_kurgusu.md
report/02_yontem.md
report/04_bulgular.md
report/05_sinirliliklar.md
requirements.txt
results/01_baseline_berturk/classification_report.txt
results/01_baseline_berturk/metrics.json
results/01_baseline_berturk/results_log_row.md
results/01_baseline_berturk/run_config.json
results/02_failure_analysis/findings.md
results/02_failure_analysis/fn_tags.json
results/02_failure_analysis/fp_function_tags.json
results/02_failure_analysis/slice_sensitivity.json
results/03_defense/augmentation_review.json
results/03_defense/comparison.json
results/03_defense/findings.md
results/03_defense/run_1a/metrics.json
results/03_defense/run_1a1b/metrics.json
results/03_defense/run_1a1b_d/metrics.json
results/03_defense/run_raw/metrics.json
results/03_defense/train_oof_summary.json
results/04_calibration/calibration.json
results/04_calibration/findings.md
results/05_final_test/TEST_SET_OPENED.json
results/05_final_test/TEST_SET_SPENT.json
results/05_final_test/findings.md
results/05_final_test/metrics.json
results/05_final_test/paired_deltas.json
results/05_final_test/raw_output.txt
results/08_lexical_analysis/findings.md
results/08_lexical_analysis/token_stats.json
results/09_deeper_analysis/stage_1/findings.md
results/09_deeper_analysis/stage_1/stage1_auc.json
results/09_deeper_analysis/stage_1b/findings.md
results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json
results/day1_report.json
results/day1_report_rerun.json
src/__init__.py
src/augment.py
src/calibration.py
src/data_io.py
src/evaluate.py
src/lexicon.py
src/models.py
src/obfuscation.py
tests/_dryrun_phase01_outputs.py
tests/_dryrun_phase04.py
tests/_dryrun_phase05.py
tests/_verify_day1_reproduction.py
tests/test_augment.py
tests/test_calibration.py
tests/test_data_io.py
tests/test_demo.py
tests/test_lexical_analysis.py
tests/test_split_and_metrics.py
tests/test_stage1_auc.py
tests/test_stage1b_defense_auc.py
tests/test_tee.py
tests/test_test_set_guard.py
```

---

# 2. `results/` tree with sizes

```
=== ls -la results/ ===
drwxr-xr-x 1 HP 197609   0 Aug 17 15:21 01_baseline_berturk/
drwxr-xr-x 1 HP 197609   0 Aug 15 20:26 02_failure_analysis/
drwxr-xr-x 1 HP 197609   0 Aug 16 16:22 03_defense/
drwxr-xr-x 1 HP 197609   0 Aug 16 13:52 04_calibration/
drwxr-xr-x 1 HP 197609   0 Aug 16 14:19 05_final_test/
drwxr-xr-x 1 HP 197609   0 Aug 17 13:17 08_lexical_analysis/
drwxr-xr-x 1 HP 197609   0 Aug 17 16:35 09_deeper_analysis/
-rw-r--r-- 1 HP 197609 671 Aug 14 14:43 day1_report.json
-rw-r--r-- 1 HP 197609 686 Aug 15 15:02 day1_report_rerun.json

=== results/01_baseline_berturk/ ===
-rw-r--r-- 1 HP 197609   2005 Aug 15 19:27 classification_report.txt
-rw-r--r-- 1 HP 197609 736591 Aug 17 15:21 dev_predictions.csv     <-- UNTRACKED (gitignored)
-rw-r--r-- 1 HP 197609   5524 Aug 15 19:28 metrics.json
-rw-r--r-- 1 HP 197609   1900 Aug 15 19:27 results_log_row.md
-rw-r--r-- 1 HP 197609   2330 Aug 15 19:27 run_config.json

=== results/02_failure_analysis/ ===
-rw-r--r-- 1 HP 197609 12180 Aug 15 20:26 findings.md
-rw-r--r-- 1 HP 197609  4372 Aug 15 19:59 fn_tags.json
-rw-r--r-- 1 HP 197609  6136 Aug 15 20:01 fp_function_tags.json
-rw-r--r-- 1 HP 197609  2406 Aug 15 20:26 slice_sensitivity.json

=== results/03_defense/ ===
-rw-r--r-- 1 HP 197609 1023 Aug 15 21:08 augmentation_review.json
-rw-r--r-- 1 HP 197609 4543 Aug 16 16:22 comparison.json
-rw-r--r-- 1 HP 197609 8255 Aug 16 14:25 findings.md
drwxr-xr-x 1 HP 197609    0 Aug 16 16:22 run_1a/
drwxr-xr-x 1 HP 197609    0 Aug 16 16:22 run_1a1b/
drwxr-xr-x 1 HP 197609    0 Aug 16 16:22 run_1a1b_d/
drwxr-xr-x 1 HP 197609    0 Aug 16 16:22 run_raw/
-rw-r--r-- 1 HP 197609 1111 Aug 16 16:22 train_oof_summary.json

=== results/03_defense/run_1a/ ===       -rw-r--r-- 3825 metrics.json
=== results/03_defense/run_1a1b/ ===     -rw-r--r-- 3832 metrics.json
=== results/03_defense/run_1a1b_d/ ===   -rw-r--r-- 3840 metrics.json
=== results/03_defense/run_raw/ ===      -rw-r--r-- 3271 metrics.json

=== results/04_calibration/ ===
-rw-r--r-- 1 HP 197609 46790 Aug 16 13:51 calibration.json
-rw-r--r-- 1 HP 197609 10932 Aug 16 13:52 findings.md

=== results/05_final_test/ ===
-rw-r--r-- 1 HP 197609   176 Aug 16 14:17 TEST_SET_OPENED.json
-rw-r--r-- 1 HP 197609   901 Aug 16 14:17 TEST_SET_SPENT.json
-rw-r--r-- 1 HP 197609  8740 Aug 16 14:19 findings.md
-rw-r--r-- 1 HP 197609 20114 Aug 16 14:17 metrics.json
-rw-r--r-- 1 HP 197609  1189 Aug 16 14:17 paired_deltas.json
-rw-r--r-- 1 HP 197609  7464 Aug 16 14:17 raw_output.txt

=== results/08_lexical_analysis/ ===
-rw-r--r-- 1 HP 197609 17982 Aug 17 13:20 findings.md
-rw-r--r-- 1 HP 197609 89324 Aug 17 13:05 token_stats.json

=== results/09_deeper_analysis/stage_1/ ===
-rw-r--r-- 1 HP 197609 15335 Aug 17 16:38 findings.md
-rw-r--r-- 1 HP 197609  6159 Aug 17 15:31 stage1_auc.json

=== results/09_deeper_analysis/stage_1b/ ===
-rw-r--r-- 1 HP 197609  8354 Aug 17 16:37 findings.md
-rw-r--r-- 1 HP 197609  4203 Aug 17 16:35 stage1b_defense_auc.json
```

**Critical fact for planning:** the *only* prediction dump on disk is
`results/01_baseline_berturk/dev_predictions.csv` (736,591 bytes, untracked/gitignored).
The four `results/03_defense/run_*/` directories hold **`metrics.json` only** — no
`dev_predictions.csv`. Phase 09 Stage 1b's docstring says those dumps "survive only on
the Drive mirror." Any new phase needing per-row defense-run predictions is blocked the
same way Stage 1b was.

`results/09_deeper_analysis/` has no `stage_2` … `stage_6` — **DOES NOT EXIST.**

---

# 3. `src/`, `tests/`, `requirements.txt`, `config.py`

```
=== ls -la src/ ===
-rw-r--r-- 1 HP 197609   136 Aug 15 14:13 __init__.py
drwxr-xr-x 1 HP 197609     0 Aug 16 14:07 __pycache__/
-rw-r--r-- 1 HP 197609 13431 Aug 15 21:08 augment.py
-rw-r--r-- 1 HP 197609 14837 Aug 16 13:39 calibration.py
-rw-r--r-- 1 HP 197609 18415 Aug 16 14:04 data_io.py
-rw-r--r-- 1 HP 197609 13598 Aug 15 22:11 evaluate.py
-rw-r--r-- 1 HP 197609  5479 Aug 15 14:29 lexicon.py
-rw-r--r-- 1 HP 197609 13424 Aug 15 14:58 models.py
-rw-r--r-- 1 HP 197609  5328 Aug 15 21:48 obfuscation.py

=== ls -la tests/ ===
drwxr-xr-x 1 HP 197609     0 Aug 17 16:29 __pycache__/
-rw-r--r-- 1 HP 197609  7197 Aug 15 15:31 _dryrun_phase01_outputs.py
-rwxr-xr-x 1 HP 197609  3768 Aug 16 13:39 _dryrun_phase04.py*
-rwxr-xr-x 1 HP 197609  3775 Aug 16 14:07 _dryrun_phase05.py*
-rw-r--r-- 1 HP 197609  1078 Aug 15 14:29 _verify_day1_reproduction.py
-rw-r--r-- 1 HP 197609  4947 Aug 15 21:09 test_augment.py
-rw-r--r-- 1 HP 197609  7448 Aug 16 13:39 test_calibration.py
-rw-r--r-- 1 HP 197609  7404 Aug 15 14:29 test_data_io.py
-rw-r--r-- 1 HP 197609  4879 Aug 16 14:29 test_demo.py
-rw-r--r-- 1 HP 197609  8176 Aug 17 13:08 test_lexical_analysis.py
-rw-r--r-- 1 HP 197609 12882 Aug 15 16:40 test_split_and_metrics.py
-rw-r--r-- 1 HP 197609 10473 Aug 17 15:31 test_stage1_auc.py
-rw-r--r-- 1 HP 197609  9680 Aug 17 16:29 test_stage1b_defense_auc.py
-rw-r--r-- 1 HP 197609  1528 Aug 16 14:10 test_tee.py
-rw-r--r-- 1 HP 197609  3981 Aug 16 14:07 test_test_set_guard.py
```

## `requirements.txt` — full text

```
# Versions phase 01 actually resolved to on Colab, 2026-08-15 (recorded in
# results/01_baseline_berturk/run_config.json): torch 2.11.0+cu128,
# transformers 5.15.0, scikit-learn 1.6.1, on an NVIDIA L4.
# The floors below are what the code needs; the runbook pins transformers
# exactly and asserts torch/scikit-learn, so a later phase cannot silently
# land on a different major without it showing up in the log.
transformers>=4.40
datasets>=2.19
torch>=2.2
scikit-learn>=1.4
numpy>=1.26
pandas>=2.2
gradio>=4.30
python-dotenv>=1.0
pytest>=8.0
```

Note: **no scipy.** Any new statistic must be hand-rolled (as `_norm_ppf` and
`auc_ties` already are) or cross-checked against sklearn.

## `config.py` — full text

```python
"""Central path + constant configuration for NSosyal B*.

Every file location in this project goes through this module. No script may
hardcode a path -- that is what lets the same `src/` code run unmodified on a
local Windows machine, on Kaggle, and in Colab.

Environment variables
---------------------
NSOSYAL_ENV   local (default) | kaggle | colab
NSOSYAL_ROOT  overrides the repo root entirely (useful when the repo is cloned
              somewhere unexpected)
NSOSYAL_DATA  overrides only the data directory, e.g. when raw files live in
              Drive / a Kaggle input mount while the code lives elsewhere
NSOSYAL_RESULTS  overrides the results directory (point it at Drive on Colab --
              /content is wiped when the session ends)
NSOSYAL_CKPT  overrides the checkpoint directory (same reason)

Set these BEFORE importing config:

    import os; os.environ["NSOSYAL_ENV"] = "kaggle"
    import config
"""

import os
from pathlib import Path

ENV = os.getenv("NSOSYAL_ENV", "local")

if os.getenv("NSOSYAL_ROOT"):
    ROOT = Path(os.environ["NSOSYAL_ROOT"])
elif ENV == "colab":
    ROOT = Path("/content/nsosyal-bstar")
elif ENV == "kaggle":
    ROOT = Path("/kaggle/working/nsosyal-bstar")
else:
    ROOT = Path(__file__).resolve().parent

# Raw data is gitignored, so on a cloned checkout it has to be mounted or
# copied in. NSOSYAL_DATA lets that happen without touching any code.
DATA_DIR = Path(os.getenv("NSOSYAL_DATA", ROOT / "data"))
# On Colab the repo clone lives in /content, which is wiped when the session
# ends -- results and checkpoints must be able to point at Drive instead.
RESULTS_DIR = Path(os.getenv("NSOSYAL_RESULTS", ROOT / "results"))
DOCS_DIR = ROOT / "docs"
# Model checkpoints. Gitignored (see .gitignore): they are reproducible from a
# seed + a results file, and a free Kaggle/Colab session can drop mid-run, so
# this directory is what makes a run resumable rather than restartable.
CKPT_DIR = Path(os.getenv("NSOSYAL_CKPT", ROOT / "checkpoints"))

# --- Çöltekin / OffensEval-2020 TR ------------------------------------------
COLTEKIN_DIR = DATA_DIR / "coltekin"
COLTEKIN_TRAIN = COLTEKIN_DIR / "offenseval-tr-training-v1.tsv"
COLTEKIN_TEST = COLTEKIN_DIR / "offenseval-tr-testset-v1.tsv"
COLTEKIN_GOLD = COLTEKIN_DIR / "offenseval-tr-labela-v1.tsv"

# --- cross-corpus generalization sources (never trained on) ------------------
MAYDA_DIR = DATA_DIR / "mayda"
BEYHAN_DIR = DATA_DIR / "beyhan"

# --- frozen lexicon (Day 1) --------------------------------------------------
LEXICON_PATH = DATA_DIR / "lexicon" / "karaliste.txt"

# --- train/dev split (phase 01 S1) -------------------------------------------
# Deliberately ROOT-relative, not DATA_DIR-relative: the split file holds row
# ids only, it is committed to the repo (see .gitignore), and it must travel
# with the code so a Colab clone reuses the exact same dev set instead of
# regenerating one. Raw corpora move; the split must not.
SPLITS_DIR = Path(os.getenv("NSOSYAL_SPLITS", ROOT / "data" / "splits"))

# --- single-use test-set accounting (phase 05) -------------------------------
# ROOT-relative for the same reason as SPLITS_DIR: these two files are committed
# and must travel with the code. A fresh clone on a new machine has to inherit
# the fact that the test set is already spent -- otherwise "touched exactly
# once" is a promise kept only by whoever remembers making it.
#
#   OPENED : append-only log, one entry per load. Written BEFORE the read, so a
#            crashed run still leaves evidence that the data was seen.
#   SPENT  : written only on a completed run. Its existence makes
#            load_coltekin_test refuse outright.
TEST_OPEN_LOG = ROOT / "results" / "05_final_test" / "TEST_SET_OPENED.json"
TEST_SPEND_RECORD = ROOT / "results" / "05_final_test" / "TEST_SET_SPENT.json"

# --- experiment constants ----------------------------------------------------
SEED = 42
MAX_LEN = 128
DEV_FRACTION = 0.15  # 85/15 stratified train/dev split, per briefing S5

MODEL_BASELINE = "dbmdz/bert-base-turkish-cased"
MODEL_SECOND = "dbmdz/convbert-base-turkish-cased"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
```

---

# 4. THE BOOTSTRAP / CI HELPERS — there are **five**, not one

A second convention already exists, and in fact a fourth and a fifth. They are not
interchangeable, and which one you inherit depends on what you are measuring.

| # | Location | Family | RNG | Default n_boot |
|---|---|---|---|---|
| 1 | `src/evaluate.py` | canonical, label-list metrics | stdlib `random.Random(seed)` | 1000 |
| 2 | `src/calibration.py:319` | operating-point CIs at a fixed threshold | stdlib `random.Random(seed)` | 1000 |
| 3 | `phase08_lexical_analysis.py` | stratum-matched rate difference | stdlib `random.Random(seed)` | 10000 |
| 4 | `phase09_stage1_auc.py` | AUC, four-cell stratified | `np.random.default_rng(seed)` | 10000 |
| 5 | `phase09_stage1b_defense_auc.py:156` | AUC, paired two-system | `np.random.default_rng(seed)` | 10000 |

`confidence_interval` and `RandomState` — **DO NOT EXIST** anywhere in the repo.

## 4.1 — Family 1: `src/evaluate.py` (the canonical one; phases 01, 03, 05)

**(a) Definitions.** `src/evaluate.py:110` (`_percentile`), `:124` (`_resample_tallies`),
`:134` (`bootstrap_ci`), `:166` (`bootstrap_delta_ci`), `:210` (`bootstrap_gap_ci`).

**(b) Exact signatures — every parameter, order, default:**

```python
src/evaluate.py:110   def _percentile(sorted_vals, q):
src/evaluate.py:124   def _resample_tallies(codes, n_boot, rng):
src/evaluate.py:134   def bootstrap_ci(y_true, y_pred, metric="macro_f1", n_boot=1000, seed=42, alpha=0.05):
src/evaluate.py:166   def bootstrap_delta_ci(y_true, pred_a, pred_b, metric="macro_f1", n_boot=1000,
                                             seed=42, alpha=0.05):
src/evaluate.py:210   def bootstrap_gap_ci(
                          y_true_a, y_pred_a, y_true_b, y_pred_b, metric="off_recall", n_boot=1000, seed=42, alpha=0.05
                      ):
src/evaluate.py:273   def score(y_true, y_pred, n_boot=1000, seed=42, alpha=0.05, with_ci=True):
src/evaluate.py:302   def score_by_slice(y_true, y_pred, slice_tags, n_boot=1000, seed=42, alpha=0.05):
```

**(c) Return type and shape.** All three return a **flat `dict`**, keys in this
insertion order:

`bootstrap_ci` →
```
"metric", "ci_low", "ci_high", "n_boot", "n_boot_used", "n_boot_undefined", "alpha", "seed"
```

`bootstrap_delta_ci` →
```
"metric", "value_a", "value_b", "delta", "ci_low", "ci_high", "excludes_zero",
"n_boot", "n_boot_used", "n_boot_undefined", "alpha", "seed", "resampling"
```
with `"resampling": "paired (same rows for both systems)"`.

`bootstrap_gap_ci` →
```
"metric", "value_a", "value_b", "delta", "ci_low", "ci_high", "excludes_zero",
"n_boot", "n_boot_used", "n_boot_undefined", "alpha", "seed", "resampling"
```
with `"resampling": "independent (disjoint slices), percentile CI"`.

`excludes_zero` is
`None if (ci_low is None or ci_high is None) else (ci_low > 0 or ci_high < 0)` —
tri-state, not boolean. `ci_low`/`ci_high` are `None` when every resample was undefined.

**(d) Docstrings verbatim:**

`bootstrap_ci`:
```
Percentile CI for one metric on one set of predictions.

Nonparametric bootstrap over rows: resample the evaluation set with
replacement n_boot times, recompute, take the alpha/2 and 1-alpha/2
percentiles. Resamples in which the metric is undefined (e.g. OFF-recall
with zero OFF examples drawn) are dropped and counted, not treated as 0.
```

`bootstrap_delta_ci`:
```
PAIRED CI for (metric of system A) - (metric of system B) on the SAME rows.

Two systems evaluated on one evaluation set are not independent samples: they
see identical rows, so the correct procedure resamples row indices once per
iteration and scores BOTH systems on that same resample. Comparing their
separately-computed CIs instead would overstate the uncertainty of the
difference and can hide a real change (or manufacture a spurious one).

Returns the point delta plus the percentile CI of the resampled deltas.
```

`bootstrap_gap_ci`:
```
CI for (metric on slice A) - (metric on slice B).

THE pivotal number of phase 01: A = lexicon_hit, B = lexicon_free.

The two slices are disjoint sets of rows, so they are resampled
independently -- an unpaired difference of two proportions. Pairing would be
wrong here: no row appears in both slices, so there is nothing to pair on.
The same rng drives both, so the whole procedure is reproducible from `seed`.

Returns delta (the point estimate on the real data) plus the percentile CI
of the resampled deltas. A CI excluding zero is what the pre-registered
decision rule calls "gap survives".
```

`_percentile`: `"""Linear-interpolated percentile, q in [0, 1]."""`

`_resample_tallies`: `"""Yield (tn, fp, fn, tp) for each nonparametric bootstrap resample."""`

**(e) Seeding and resample count.** `rng = random.Random(seed)`, `seed=42` default,
`n_boot=1000` default. Rows are reduced to per-row outcome codes
(`3=tp 2=fn 1=fp 0=tn`, `_codes`, line 44) and the *codes* are resampled — that is what
makes 1,000 pure-Python resamples cheap. `alpha=0.05`, percentile interval at `alpha/2`
and `1-alpha/2` (note: **fractions in [0,1]**, not 0–100).

**(f) Paired vs unpaired — TWO SEPARATE FUNCTIONS, selected by which you call.**
There is no flag.

- `bootstrap_delta_ci` = **paired**, same rows, two systems.
  `idx = rng.choices(population, k=n)` once per iteration, both systems scored on that
  `idx` (line 192).
- `bootstrap_gap_ci` = **unpaired**, two disjoint slices, one system. Two independent
  generators `gen_a`/`gen_b` zipped (lines 238–240).

The docstrings state explicitly why each is correct for its case; picking the wrong one
is a substantive error, not a style choice.

**(g) Stratification.** **Not a parameter, and not present.** Family 1 does plain
row-level resampling. Stratification in this repo exists only in family 4 (four fixed
cells, hardcoded) and in phase 08's stratum-*matching* (which is an estimator, not a
resampling scheme).

**(h) EVERY call site, verbatim.**

`bootstrap_gap_ci` — 6 sites:

```python
phase01_baseline.py:333
    gap = evaluate.bootstrap_gap_ci(
        [dev_gold[i] for i in hit_idx], [dev_pred[i] for i in hit_idx],
        [dev_gold[i] for i in free_idx], [dev_pred[i] for i in free_idx],
        metric="off_recall", n_boot=args.n_boot, seed=args.seed,
    )

phase03_compare.py:91
        gap = evaluate.bootstrap_gap_ci(
            [gold[i] for i in hit_idx], [preds[v][i] for i in hit_idx],
            [gold[i] for i in free_idx], [preds[v][i] for i in free_idx],
            metric="off_recall", n_boot=args.n_boot, seed=args.seed)

phase03_train_defense.py:105
    gap = evaluate.bootstrap_gap_ci(
        [dev_gold[i] for i in hit_idx], [pred[i] for i in hit_idx],
        [dev_gold[i] for i in free_idx], [pred[i] for i in free_idx],
        metric="off_recall", n_boot=args.n_boot, seed=args.seed)

phase05_final_test.py:168
        gap = evaluate.bootstrap_gap_ci(
            [gold[i] for i in hit], [p[i] for i in hit],
            [gold[i] for i in free], [p[i] for i in free],
            metric="off_recall", n_boot=n_boot, seed=seed)

tests/test_split_and_metrics.py:154
    gap = evaluate.bootstrap_gap_ci(hit_true, hit_pred, free_true, free_pred,
                                    metric="off_recall", n_boot=200, seed=42)

tests/test_split_and_metrics.py:163
    gap = evaluate.bootstrap_gap_ci(true_a, pred_a, list(true_a), list(pred_a),
                                    metric="off_recall", n_boot=300, seed=42)
```

Note the **invariant convention**: slice A is always `lexicon_hit`, slice B always
`lexicon_free`, `metric="off_recall"` always passed explicitly even though it is the
default, and `n_boot`/`seed` always come from `args`.

`bootstrap_delta_ci` — 4 sites:

```python
phase03_compare.py:108
        d["macro_f1"] = evaluate.bootstrap_delta_ci(gold, preds[v], preds["raw"], "macro_f1",
                                                    args.n_boot, args.seed)

phase03_compare.py:110
        d["lexicon_free_off_recall"] = evaluate.bootstrap_delta_ci(
            [gold[i] for i in free_idx], [preds[v][i] for i in free_idx],
            [preds["raw"][i] for i in free_idx], "off_recall", args.n_boot, args.seed)

phase03_compare.py:113
        d["lexicon_hit_off_recall"] = evaluate.bootstrap_delta_ci(
            [gold[i] for i in hit_idx], [preds[v][i] for i in hit_idx],
            [preds["raw"][i] for i in hit_idx], "off_recall", args.n_boot, args.seed)

phase05_paired_deltas.py:64
        d = evaluate.bootstrap_delta_ci(g, a, b, metric, args.n_boot, args.seed)
```

Convention: **A is the treatment, B is `raw` (the control)**, so `delta` reads as
treatment-minus-control. Positional args after `y_true`, not keyword.

`bootstrap_ci` — call sites:

```python
src/evaluate.py:279   "macro_f1": bootstrap_ci(y_true, y_pred, "macro_f1", n_boot, seed, alpha),
src/evaluate.py:280   "off_recall": bootstrap_ci(y_true, y_pred, "off_recall", n_boot, seed, alpha),
      (both inside score(), which is the normal entry point)

phase05_final_test.py:183
    "off_recall_ci": evaluate.bootstrap_ci(g, q, "off_recall", n_boot, seed),

tests/test_split_and_metrics.py:140   a = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=42)
tests/test_split_and_metrics.py:141   b = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=42)
tests/test_split_and_metrics.py:142   c = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=1)
```

In practice **phases do not call `bootstrap_ci` directly** — they call
`evaluate.score(...)` and read `out["ci"]["macro_f1"]` / `out["ci"]["off_recall"]`.
The one direct call, `phase05_final_test.py:183`, exists because the per-slice block
deliberately omits macro-F1.

## 4.2 — Family 2: `src/calibration.py` (phase 04, phase 05)

**(a)** Defined at `src/calibration.py:319`.

**(b)** `def bootstrap_operating_point(y_true, y_pred, p_off, threshold, n_boot=1000, seed=42, alpha=0.05):`

**(c)** Returns a **nested dict**, three metric blocks plus a count:

```python
{"coverage":   {"ci_low": ..., "ci_high": ...},
 "macro_f1":   {"ci_low": ..., "ci_high": ...},
 "error_rate": {"ci_low": ..., "ci_high": ...},
 "n_boot_used": int}
```

Note: **no `n_boot`, no `alpha`, no `seed`, no `excludes_zero`** in the return — a
different shape from family 1.

**(d)** Docstring verbatim:
```
Percentile CIs for an operating point at a FIXED threshold.

Rows are resampled with replacement and the same threshold reapplied, so the
interval covers both which rows are auto-resolved and how well they score.
The threshold is held fixed because it was selected on CAL -- re-selecting it
inside each resample would measure a different, self-tuning procedure.
```

**(e)** `import random` **inside the function body** (line 328), `rng = random.Random(seed)`,
`idx = [rng.randrange(n) for _ in range(n)]` — note this is `randrange`, not
`rng.choices`, so it does **not** reproduce family 1's stream even at the same seed.
`n_boot=1000`. Reuses `evaluate._percentile`, `evaluate._codes`,
`evaluate._metrics_from_tally`.

**(f)** Unpaired only. There is no paired variant in this family.

**(g)** No stratification.

**(h)** Call sites:

```python
phase04_calibration.py:173
        block["ci"] = cal.bootstrap_operating_point(E["gold"], E["pred"], E["p_off"],
                                                    thr, n_boot=n_boot, seed=seed)

phase05_final_test.py:211
                b["ci"] = cal.bootstrap_operating_point(gold, p, probs[name], t,
                                                        n_boot=n_boot, seed=seed)

tests/test_calibration.py:169   ci = cal.bootstrap_operating_point(y, pred, p, t, n_boot=200, seed=42)
tests/test_calibration.py:178   a = cal.bootstrap_operating_point(y, pred, p, t, n_boot=100, seed=42)
tests/test_calibration.py:179   b = cal.bootstrap_operating_point(y, pred, p, t, n_boot=100, seed=42)
```

Convention: always assigned to `block["ci"]` / `b["ci"]`, always right after
`cal.apply_threshold(...)`.

## 4.3 — Family 3: `phase08_lexical_analysis.py` (phase-local)

**(a)** `percentile` at `:107`; `matched_comparison` at `:143`; the CI closure
`def ci(vals)` at `:173`.

**(b)**
```python
phase08_lexical_analysis.py:107   def percentile(sorted_vals, q):
phase08_lexical_analysis.py:143   def matched_comparison(a_rows, b_rows, edges, n_boot=N_BOOT, seed=BOOT_SEED):
phase08_lexical_analysis.py:191   def verdict(diff, ci):
```
with module constants `N_BOOT = 10000` (`:36`), `BOOT_SEED = 42` (`:37`),
`N_QUANTILES = 4` (`:38`), `ALPHA = 0.05` (`:33`).

**(c)** `matched_comparison` returns a flat dict:
```
"n_a", "n_b", "rate_a", "rate_b_unmatched", "rate_b_matched",
"diff_matched", "diff_matched_ci", "diff_unmatched", "diff_unmatched_ci",
"a_mass_in_unsupported_strata"
```
The two `*_ci` values are sub-dicts `{"ci_low", "ci_high", "n_resamples"}` — note
**`n_resamples`**, not family 1's `n_boot_used`.

**(d)** Docstrings verbatim:

`matched_comparison`:
```
Difference in P(row contains a group-2 token), A minus matched B.

a_rows / b_rows are lists of (x, in_lex, ntok). Strata are
(in_lex, token-count quartile); the quartile edges are fixed at A's
observed values and are NOT recomputed inside the bootstrap -- the estimator
being resampled is the one defined on the observed strata.
```

`verdict`: `"""C8-7: the interpretation was fixed before the number existed."""`

`percentile` has **no docstring**.

**(e)** `rng = random.Random(seed)` (line 162), `rng.randrange(...)`, `n_boot=10000`,
`seed=42`. The CI closure hardcodes `percentile(s, 0.025)` / `percentile(s, 0.975)` —
**ALPHA is not threaded through**, it is inlined.

**(f)** Unpaired: A and B are resampled independently (lines 165–166), correct because
A (NOPROF false positives) and B (true negatives) are disjoint row sets.

**(g)** Stratification is **an estimator, not a resampling parameter**:
`stratum_weighted_rate` reweights B onto A's `(in_lex, token-count quartile)`
distribution. The `edges` are a **required positional parameter** computed by the caller
via `quantile_edges(...)` and deliberately frozen outside the loop.

**(h)** Call sites — all within phase08:

```python
phase08_lexical_analysis.py:413   primary = matched_comparison(a_feat, b_feat, edges, n_boot=args.n_boot)
phase08_lexical_analysis.py:463   wide_cmp = matched_comparison(
                                      featurise(a_src, wide_group2), featurise(tn_rows, wide_group2),
                                      edges, n_boot=args.n_boot)
phase08_lexical_analysis.py:472   g3_cmp = matched_comparison(featurise(a_src, group3), featurise(tn_rows, group3),
                                                              edges, n_boot=args.n_boot)
phase08_lexical_analysis.py:505   c = matched_comparison(featurise(a_src, vocab), featurise(tn_rows, vocab),
                                                         edges, n_boot=args.n_boot)
tests/test_lexical_analysis.py:154   one = p8.matched_comparison(a, b, edges, n_boot=300, seed=42)
tests/test_lexical_analysis.py:155   two = p8.matched_comparison(a, b, edges, n_boot=300, seed=42)
tests/test_lexical_analysis.py:164   r = p8.matched_comparison(a, b, edges, n_boot=500, seed=42)
```

Note `seed` is never passed at the four production sites — the module default
`BOOT_SEED` is relied on, and only `n_boot` is exposed on the CLI.

## 4.4 — Family 4: `phase09_stage1_auc.py` (Stage 1) — the most recent convention

**(a)** `pct` at `:172`, `ci_of` at `:176`, `bootstrap_pair` at `:305`. Constants
`N_BOOT = 10000` (`:61`), `BOOT_SEED = 42` (`:62`), `ALPHA = 0.05` (`:63`).

**(b)**
```python
phase09_stage1_auc.py:172   def pct(vals, q):
phase09_stage1_auc.py:176   def ci_of(vals):
phase09_stage1_auc.py:305   def bootstrap_pair(hit, free, n_boot=N_BOOT, seed=BOOT_SEED, matched=True):
```

**(c)** `ci_of` returns `{"ci_low": <rounded 6dp>, "ci_high": <rounded 6dp>}` —
**two keys only**, no metric/n_boot/alpha/seed/excludes_zero. `bootstrap_pair` returns a
**4-tuple, positional**: `(a_hit, a_free, a_diff, m)` where the first three are
`list[float]` of length `n_boot` and `m` is a dict of four lists keyed
`"hit_at_free_prec"`, `"hit_at_free_rate"`, `"free_at_hit_prec"`, `"free_at_hit_rate"`.

**This is the key structural break from family 1: the bootstrap function returns raw
replicate arrays, and `ci_of` is applied separately by the caller.** Family 1 returns a
finished CI dict; family 4 separates production from summarisation.

**(d)** `bootstrap_pair` docstring verbatim:
```
C9-3. Four cells, each resampled to its own original size, 10k, seed 42.

Matched operating points are recomputed inside the replicate, threshold
selection included (C9-8), so the interval carries the selection variance.
```
`pct` and `ci_of` have **no docstrings**.

**(e)** `rng = np.random.default_rng(seed)` (line 311) — **numpy Generator, not stdlib
random**. `n_boot=10000`, `seed=42`. `pct` uses `np.percentile` with **q in 0–100**:
`ci_of` calls `pct(vals, 100 * ALPHA / 2)` and `pct(vals, 100 * (1 - ALPHA / 2))`.
This is the opposite convention to `evaluate._percentile`, which takes q in [0,1].
Results are `round(..., 6)`.

**(f)** `bootstrap_pair` is **unpaired between the two slices** (four independently drawn
index arrays, lines 316–319) because hit and free are disjoint. The **paired**
counterpart is family 5, a separate function in a separate file.

**(g)** Stratification is **hardcoded, not a parameter**: four cells — `hit.n_pos`,
`hit.n_neg`, `free.n_pos`, `free.n_neg` — each resampled to its own original size.
`matched=True` is a parameter but controls whether operating-point matching runs inside
the replicate, not the stratification. The JSON records it as
`"method": "stratified over the four slice x gold cells, percentile interval"`.

**(h)** Call sites:

```python
phase09_stage1_auc.py:478   b_hit, b_free, b_diff, b_match = bootstrap_pair(hit, free, n_boot=args.n_boot)
tests/test_stage1_auc.py:212   a = s1.bootstrap_pair(hit, free, n_boot=200, seed=42)
tests/test_stage1_auc.py:213   b = s1.bootstrap_pair(hit, free, n_boot=200, seed=42)
tests/test_stage1_auc.py:223   a_hit, a_free, a_diff, _ = s1.bootstrap_pair(hit, free, n_boot=50, matched=False)
tests/test_stage1_auc.py:234   b_hit, _, _, _ = s1.bootstrap_pair(hit, free, n_boot=400, matched=False)
```

`ci_of` call sites:
```
phase09_stage1_auc.py:479   ci_hit, ci_free, ci_gap = ci_of(b_hit), ci_of(b_free), ci_of(b_diff)
phase09_stage1_auc.py:516   matched[k]["recall_ci"] = ci_of(b_match[bk])
phase09_stage1b_defense_auc.py:224   ci_a, ci_b, ci_d = s1.ci_of(ba), s1.ci_of(bb), s1.ci_of(bd)
tests/test_stage1_auc.py:214, 235; tests/test_stage1b_defense_auc.py:107, 142, 149, 150
```

## 4.5 — Family 5: `phase09_stage1b_defense_auc.py` (Stage 1b)

**(a)** `:156`. Constants `N_BOOT = 10000` (`:40`), `BOOT_SEED = 42` (`:41`).

**(b)** `def paired_delta(sa, sb, n_boot=N_BOOT, seed=BOOT_SEED):`

**(c)** Returns a **3-tuple** `(da, db, dd)` — three `list[float]` of length `n_boot`:
control AUCs, treatment AUCs, and their per-replicate differences. Again raw replicates;
the caller applies `s1.ci_of`.

**(d)** Docstring verbatim:
```
C9-13: resample rows ONCE per replicate, score BOTH systems on them.

Using independent resamples for the two systems would discard the pairing
and widen the interval for no reason; using different indices for the two
would be worse than that -- it would not estimate the paired difference at
all. The same index arrays therefore drive both.
```

**(e)** `rng = np.random.default_rng(seed)`, `n_boot=10000`, `seed=42`.

**(f)** **Paired.** `pi`/`ni` drawn once (lines 167–168) and applied to both
`sa.counts(pi, ni)` and `sb.counts(pi, ni)` with the comment `# SAME rows`. Selection
between paired and unpaired at the AUC level is by **choosing the function/module**,
exactly as in family 1.

**(g)** Stratification hardcoded: two cells (`n_pos`, `n_neg`), each to its own size.

**(h)** Call sites:
```
phase09_stage1b_defense_auc.py:223   ba, bb, bd = paired_delta(sa, sb, n_boot=args.n_boot)
tests/test_stage1b_defense_auc.py:149   s1.ci_of(s1b.paired_delta(a, b, n_boot=200, seed=42)[2])
tests/test_stage1b_defense_auc.py:150   s1.ci_of(s1b.paired_delta(a, b, n_boot=200, seed=42)[2])
```

## 4.6 — Which phases use which

| Phase | CI family |
|---|---|
| 01 baseline | `evaluate.bootstrap_gap_ci`, `evaluate.score`→`bootstrap_ci` |
| 03 train_defense / compare | `evaluate.bootstrap_gap_ci`, `evaluate.bootstrap_delta_ci` |
| 04 calibration | `cal.bootstrap_operating_point` |
| 05 final_test / paired_deltas | all of family 1 + family 2 |
| 08 lexical | phase-local `matched_comparison` (family 3) |
| 09 Stage 1 | phase-local `bootstrap_pair` + `ci_of` (family 4) |
| 09 Stage 1b | phase-local `paired_delta` + **imported** `s1.ci_of` (family 5) |

**The trend a new phase should read from this:** the two most recent phases both wrote a
phase-local bootstrap rather than extending `src/evaluate.py`, because their estimator
(AUC / stratum-matched rate) is not expressible as a confusion-matrix tally. But Stage 1b,
the *most* recent, **imported `ci_of`, `Slice`, `auc_ties`, `describe`,
`load_predictions`, `sha256_of`, `PRED_SHA256` and `FROZEN_THRESHOLD` from Stage 1 rather
than copying them.** That is the live convention: new statistic → new local function;
CI summarisation, slice machinery and loading → import from `phase09_stage1_auc`.

---

# 5. The other shared helpers

## Slice assignment / `lexicon.hit_root`

```python
src/lexicon.py:81   def hit_root(text, lex_list):
    """Root/prefix match -- catches inflected forms via Turkish agglutination.

    This is the ADOPTED definition of "the lexicon caught it". Using the
    stronger matcher makes the lexicon-free slice smaller, i.e. it argues
    against our own hypothesis -- which is why it is the honest choice.
    """
```

Returns `bool`. Note the argument is `lex_list` — **a sorted list, order matters**;
`hit_literal(text, lex_set)` takes a set instead. `MIN_ROOT_LEN = 3`
(`src/lexicon.py:65`). Companion: `lexicon.tokens(text)` (`:68`),
`lexicon.tr_lower(s)` (`:23`), `lexicon.load_lexicon(path=None)` (`:32`).

The wrapper that produces slice tags:

```python
src/evaluate.py:290   def tag_slices(rows, lex_list):
    """Tag each row 'lexicon_hit' / 'lexicon_free' with the FROZEN matcher.

    `lexicon.hit_root` is the Day 1 adopted definition of "the lexicon caught
    it". It is imported, never reimplemented -- a second copy of the rule would
    be free to drift away from the frozen record.
    """
```

Representative call site:
```
phase08_lexical_analysis.py:402
                        lexicon.hit_root(r["text"], lex_list),
```

**Important precedent:** `phase09_stage1_auc.py:344` defines `matching_roots(text, lex_list)`
which *does* reimplement hit_root's inner rule — and it is explicitly licensed by a
docstring plus a dedicated test (`test_matching_roots_agrees_with_hit_root_on_every_text`,
`tests/test_stage1_auc.py:243`) that asserts agreement on every text. If a new phase must
reimplement a frozen rule, that is the pattern: state why, and unit-test equivalence.

## Loading a prediction dump

**Two `load_predictions` exist.** The one phase09 uses:

```python
phase09_stage1_auc.py:233
def load_predictions(path):
    path = Path(path)
    got_sha, got_bytes = sha256_of(path), path.stat().st_size
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["p_off"] = float(r["confidence"])
    return rows, got_sha, got_bytes
```

No docstring. Returns a **3-tuple** `(rows, sha256_hex, byte_count)`. Each row is a
`dict` from `csv.DictReader` with the added float key `p_off`.

CSV schema (`head -1 results/01_baseline_berturk/dev_predictions.csv`):
```
row_id,text,gold,pred,confidence,slice
```
written by `phase01_baseline.py:397`. `confidence` is softmax P(OFF).

Representative call sites:
```
phase09_stage1_auc.py:461      rows, got_sha, got_bytes = load_predictions(args.pred)
phase09_stage1b_defense_auc.py:129   a, _, _ = s1.load_predictions(control_path)
phase09_stage1b_defense_auc.py:130   b, _, _ = s1.load_predictions(treatment_path)
```

The **other** one, `phase04_calibration.py:51`, has a different contract — it returns
`rows` only and validates the dev fingerprint rather than a sha256:

```python
def load_predictions(path):
    """Load a dump and verify it describes the frozen dev split.

    The fingerprint is recomputed from the row ids in the file itself, so this
    check needs neither the corpus nor the split file -- a dump that came from a
    different dev set is rejected here rather than silently averaged in.
    """
```

Do not confuse them.

## Provenance / sha256 check

Three distinct mechanisms, all in use:

**1. File-content sha256.** Two implementations with identical behaviour but different
chunk sizes:

```python
src/data_io.py:34   def sha256(path):
    """Content fingerprint -- recorded in every result file so a rerun can
    prove it read the same bytes."""
    # chunk size 8192

phase09_stage1_auc.py:225   def sha256_of(path):
    # no docstring; chunk size 1 << 20
```

Representative: `phase08_lexical_analysis.py:262  train_sha = data_io.sha256(config.COLTEKIN_TRAIN)`

**2. Provenance by recomputed content (the C9-1 pattern), `phase09_stage1_auc.py:243`:**

```python
def check_provenance(rows, got_sha, got_bytes):
    """C9-1. Eight recorded figures. A mismatch on any one aborts the stage."""
```

It hardcodes `PRED_SHA256` / `PRED_BYTES` / a `RECORDED` dict of thirteen figures at
module level (lines 40–56), reprints each as `OK  `/`FAIL`, and `sys.exit`s on any
mismatch with the message `"ABORT (C9-1): the dump does not reproduce the record:"`.
Stage 1b's equivalent is `check_run(label, rows, run_key, comparison_path=COMPARISON)`
at `:106`, aborting with `"ABORT (C9-12): ..."`.

Call site: `phase09_stage1_auc.py:462  check_provenance(rows, got_sha, got_bytes)`

**3. Dev fingerprint** — see below.

## Metric computation — where each lives

| Metric | Location |
|---|---|
| macro-F1 | `src/evaluate.py:95  def macro_f1(y_true, y_pred)` — and `_metrics_from_tally` (`:75`) which computes it as the mean of `f1_off` and `f1_not` |
| OFF-recall | `src/evaluate.py:100  def off_recall(y_true, y_pred)` |
| OFF-precision, off_f1, not_f1, accuracy, confusion | `src/evaluate.py:75  _metrics_from_tally` — returned by `score()` |
| full block, one system | `src/evaluate.py:273  def score(y_true, y_pred, n_boot=1000, seed=42, alpha=0.05, with_ci=True)` |
| per-slice blocks | `src/evaluate.py:302  def score_by_slice(y_true, y_pred, slice_tags, n_boot=1000, seed=42, alpha=0.05)` |
| **ROC-AUC** | **`phase09_stage1_auc.py:80  def auc_ties(pos, neg)`** — Mann-Whitney U, ties at half credit. **Not in `src/`.** |
| Average precision | `phase09_stage1_auc.py:99  def average_precision(pos, neg)` |
| sklearn cross-check | `src/evaluate.py:333  def sklearn_report(y_true, y_pred, title="", digits=4, strict=True)` |

`grep -rn "auc\|roc" src/ -i` → no AUC implementation in `src/`.
**AUC lives only in `phase09_stage1_auc.py`.**

Two hard constraints attached to these:

- `score_by_slice`'s docstring carries a **pre-registered constraint binding on every
  later phase**: cross-slice comparison is **OFF-recall only**; macro-F1 and accuracy
  must not be compared between slices (base rates 57.8% vs 13.6%). Phases 01 and 05 both
  emit `"macro_f1": None` per slice with an explanatory note rather than the number.
- `sklearn_report` raises `AssertionError` if sklearn's macro-F1 disagrees with the
  stdlib one by more than `1e-9`.

Representative call sites:
```
phase03_compare.py:89        s = evaluate.score(gold, preds[v], with_ci=False)
phase05_final_test.py:167    s = evaluate.score(gold, p, n_boot=n_boot, seed=seed)
phase09_stage1_auc.py:468    auc_hit = auc_ties(hit.pos, hit.neg)
```

## Split loading and the dev fingerprint check

```python
src/data_io.py:328
def get_split(all_rows, path, train_sha256, seed=None, dev_fraction=None):
    """The only split entry point callers should use.

    Creates the split file on first use, loads and verifies it thereafter.
    Returns (train_rows, dev_rows, meta) where meta["reused_existing_file"] and
    meta["matches_regeneration"] record how the split was obtained -- both go
    into the result file so a reader can tell.
    """
```

Returns `(train_rows, dev_rows, meta)`. Supporting:
`stratified_split(rows, dev_fraction=None, seed=None)` (`:157`),
`save_split(path, all_rows, train_rows, dev_rows, train_sha256, seed, dev_fraction)` (`:263`),
`load_split(path, all_rows, train_sha256=None)` (`:292`).

```python
src/data_io.py:232
def dev_fingerprint(dev_rows):
    """sha256 over the sorted dev ids -- the identity of a dev set.

    Recorded in every result file. If two result files disagree, this says
    immediately whether they were even measured on the same examples.
    """
```

Raises `ValueError` on duplicate ids.

**The frozen dev fingerprint is `034415af3a23b388`** (first 16 hex chars). Three
enforcement idioms are in use:

```python
phase03_train_defense.py:177
    if not split_meta["dev_fingerprint"].startswith("034415af3a23b388"):
        sys.exit(f"ABORT: dev fingerprint is {split_meta['dev_fingerprint'][:16]}, ...

phase08_lexical_analysis.py:268
    if not meta["reused_existing_file"]:
        raise SystemExit("ABORT: the split was CREATED, not loaded.")

phase08_lexical_analysis.py:377
    if not tags["dev_fingerprint"].startswith(meta["dev_fingerprint"][:16]):
        raise SystemExit("ABORT: FP tag file is from a different dev split.")
```

Phase 09 Stage 1/1b do **not** load the split at all — they assert provenance from the
dump's own content and record `"dev_fingerprint": "034415af3a23b388"` as a literal string
in the payload.

Representative full call site (`phase08_lexical_analysis.py:262-269`):

```python
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
    all_rows = data_io.load_coltekin_train(config.COLTEKIN_TRAIN)
    split_path = config.SPLITS_DIR / "split_seed42.json"
    train_rows, dev_rows, meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=config.SEED,
        dev_fraction=config.DEV_FRACTION)
    if not meta["reused_existing_file"]:
        raise SystemExit("ABORT: the split was CREATED, not loaded.")
```

Also relevant: `load_coltekin_test(run_final_test=False, path=None, gold_path=None)`
(`src/data_io.py:371`) refuses outright — `config.TEST_SPEND_RECORD` exists, so any
accidental call raises `PermissionError`. The test set is locked by a committed file, not
by convention.

## `git_sha()` and what writes `run_config.json`

**Two conventions.** The full one:

```python
phase01_baseline.py:69
def git_sha():
    """HEAD sha, suffixed `-dirty` only if a TRACKED file was modified.

    Untracked files are deliberately excluded (`--untracked-files=no`). The
    first phase-01 run reported `837c351-dirty` purely because it had written
    its own four output files into results/, which are untracked until
    committed -- so every run marked itself dirty by succeeding, and the flag
    carried no information. It now means what it should: the code that produced
    the numbers differs from the commit.
    """
```

Imported by phases 03 and 05: `from phase01_baseline import assert_trainable_runtime, git_sha`.

The **lightweight inline one**, used by both recent phases (phase08 `:561`,
phase09 `:543`, phase09-1b `:259`) — identical five lines in all three:

```python
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "?"
```

Note it returns the **short** sha and has **no dirty flag**. This is the current
convention for read-only measurement phases.

`run_config.json` is written **only by `phase01_baseline.py:467-493`** — one site, inline
`json.dump(run_config, f, ensure_ascii=False, indent=2)`. There is **no shared run-config
writer**. Its key order:

```
run_id, git_sha, started_at, finished_at, env, paths{root,data,results,checkpoints,split_file},
hashes{train_sha256,lexicon_sha256,dev_fingerprint}, preconditions, split{...},
model, hyperparams{...}, bootstrap{n_boot,alpha,seed}, environment, official_test_set_touched
```

Phases 08 and 09 do **not** write `run_config.json` — they fold the same information into
the single results JSON under `inputs`, `git_sha`, `preregistration`, `scope`.

## The results-writing helper: how a phase persists metrics.json

**There is no shared results-writing helper.** `grep` for `write_results` →
**DOES NOT EXIST.** Every phase writes inline. Two idioms:

Training phases (01, 05) use `json.dump` to an open handle:
```python
phase01_baseline.py:464
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
```

Recent measurement phases (08, 09, 09-1b) use `Path.write_text` and print the byte count:
```python
phase08_lexical_analysis.py:634
    out = out_dir / "token_stats.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)")

phase09_stage1_auc.py:594
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "stage1_auc.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)")
```

Note the filename is **phase-specific** (`token_stats.json`, `stage1_auc.json`,
`stage1b_defense_auc.json`), not `metrics.json`. `metrics.json` is the name used by the
*training* phases only.

What **is** shared is the Drive mirror:

```python
phase01_baseline.py:244
def mirror_outputs(out_dir, mirror_dir, required=None, marker="metrics.json"):
    """Copy a COMPLETED run's outputs to Drive.
    ...
    `required` is the output contract to enforce and defaults to phase 01's five
    files. Later phases pass their own list rather than getting a second copy of
    this function -- two mirrors would be free to drift apart on exactly the
    checks that make this one worth having.
    """
```

with `PHASE01_CONTRACT = ("metrics.json", "classification_report.txt",
"dev_predictions.csv", "run_config.json", "results_log_row.md")` at `:240`.

Representative call site:
```python
phase05_final_test.py:432
        from phase01_baseline import mirror_outputs
        mirror_outputs(out_dir, Path(args.mirror_dir),
                       required=("metrics.json", "test_predictions.csv", "raw_output.txt"),
                       marker="metrics.json")
```

Phase 08 **deliberately declines** the mirror, and says so in a comment at `:637`:
*"No Drive mirror: this phase runs locally on CPU, writes one small JSON of aggregates,
and that file is committed."* Phase 09 likewise has no mirror call.

---

# 6. CONVENTIONS — evidenced from the two most recent phase scripts

## (a) Import blocks, verbatim

`phase09_stage1_auc.py:23-37`:
```python
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                                    # noqa: E402
from src import lexicon                          # noqa: E402
```

`phase08_lexical_analysis.py:16-29`:
```python
import argparse
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import augment, data_io, lexicon
```

`phase09_stage1b_defense_auc.py:26-37` for contrast:
```python
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase09_stage1_auc as s1                  # noqa: E402
```

The shape is fixed: stdlib block, blank line, third-party block, blank line,
`sys.path.insert(0, str(Path(__file__).resolve().parent))`, blank line, project imports.
Phase 09 adds `# noqa: E402` to the project imports; phase 08 does not.
**`argparse`, `json`, `subprocess`, `sys`, `datetime.datetime`, `pathlib.Path` appear in
all three** — the last three exist purely for the provenance/results payload.

## (b) CLI argument structure

`phase09_stage1_auc.py:449-453`:
```python
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="results/01_baseline_berturk/dev_predictions.csv")
    ap.add_argument("--out_dir", default="results/09_deeper_analysis/stage_1")
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
    args = ap.parse_args()
```

`phase08_lexical_analysis.py:245-247`:
```python
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
    args = ap.parse_args()
```
— phase 08 hardcodes its out_dir instead:
`out_dir = config.RESULTS_DIR / "08_lexical_analysis"` (`:254`).

`phase09_stage1b_defense_auc.py:193-200` shows the `required=True` idiom for inputs that
must not be silently defaulted:
```python
    ap.add_argument("--control", required=True,
                    help="run_raw/dev_predictions.csv -- C9-12 forbids substituting "
                         "the phase-01 dump here")
    ap.add_argument("--treatment", required=True, help="run_1a1b_d/dev_predictions.csv")
    ap.add_argument("--out_dir", default="results/09_deeper_analysis/stage_1b")
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
```

Invariants: bare `ArgumentParser()` with no description; **`--n_boot` is always exposed,
`--seed` is never** (the seed is a module constant, not tunable from the CLI, in both
recent phases); `--out_dir` defaults to a repo-relative string literal, not a `config`
path; no `argparse` group/subcommand machinery. Contrast
`phase05_final_test.py:325-326`, which does expose `--seed`.

## (c) stdout emission — and the `isatty` crash history

**Neither phase08 nor phase09 uses a Tee or `logging`.** They print to stdout directly.

Phase 08 does one thing first (`:249-252`):
```python
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
```
Phase 09 Stage 1 does **not** do this — it has no `reconfigure` call at all.

`Tee` exists in exactly one place, `phase05_final_test.py:55`:

```python
class Tee:
    """Duplicate stdout to a file so the raw run output is preserved verbatim.

    The write-up quotes numbers; this keeps the unedited console output next to
    them, which is what makes the quoting checkable.


    Anything this class does not implement is delegated to the real stream.
    Libraries interrogate sys.stdout for more than write/flush -- transformers
    calls .isatty() while reporting checkpoint loading -- and a Tee that answers
    only the two obvious methods turns into an AttributeError at exactly the
    wrong moment. (It did, on the first attempt at this run.)
    """
```

Its methods: `write` (returns `len(s)`), `flush`, `isatty` (hardcoded `False`, with a
comment explaining that colour codes would corrupt the preserved file), `close`, and
`__getattr__` delegating everything else to the real stream. Used once,
`phase05_final_test.py:338-339`:
```python
    tee = Tee(sys.stdout, out_dir / "raw_output.txt")
    sys.stdout = tee
```

**The crash history**, from `tests/test_tee.py:1-7` verbatim:
```
"""Tests for the phase-05 stdout tee.

Written after the real failure: transformers calls `sys.stdout.isatty()` while
reporting checkpoint loading, and the first Tee implemented only write/flush.
The AttributeError landed AFTER the official test set had been opened, which is
the most expensive place in the project to discover a missing method.
"""
```

Four regression tests guard it: `test_writes_to_both_stream_and_file`,
`test_isatty_is_false_so_colour_codes_never_reach_the_file`,
`test_unknown_attributes_delegate_to_the_real_stream`,
`test_write_returns_character_count`.

**Bearing on a new phase:** the Tee was needed because transformers was in the process.
A phase that loads no model has no `isatty` exposure — which is exactly why phases 08 and
09 skipped it. `raw_output.txt` exists only under `results/05_final_test/`.

The **print convention** in both recent phases: an `"=" * 96` (phase 08) or `"=" * 88`
(phase 09) banner at start and end, section headers tagged with the constraint ID they
implement — `print("\n[C9-3] bootstrap: ...")`,
`print("C8-7  DO THE 118 NO-PROFANITY FALSE POSITIVES CARRY GROUP-2 TOKENS?")` — and
every printed number formatted to a fixed width so console output and JSON agree.

## (d) How they write results and where

Phase 08 → `config.RESULTS_DIR / "08_lexical_analysis" / "token_stats.json"`
(out_dir made at `:254-255`, written at `:634-636`).

Phase 09 Stage 1 → `Path(args.out_dir) / "stage1_auc.json"`, `args.out_dir` defaulting to
`results/09_deeper_analysis/stage_1` (`:594-598`).

Both build a single `payload` dict and write it with
`json.dumps(payload, ensure_ascii=False, indent=2)`. `ensure_ascii=False` is
non-negotiable — the payloads carry Turkish tokens.

The payload's leading keys are the same in both, and Stage 1b matches:
```
run_id, created_at, git_sha, preregistration, scope, inputs{...}, ...
```
with `scope` a literal sentence naming what was not done — phase 09:
`"measurement only; no training, no forward pass, no intervention (C9-11)"`; phase 08:
`"measurement only; no training, no intervention"` — and `inputs` always containing
`"test_set_touched": False`.

Both then print `f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)"` and a closing
banner.

`findings.md` is written **by hand, not by the script** — no script writes it. Both
`results/08_lexical_analysis/findings.md` and
`results/09_deeper_analysis/stage_1/findings.md` have mtimes *later* than their JSON
(13:20 vs 13:05; 16:38 vs 15:31). The same holds for `RESULTS_LOG.md` rows:
`phase01_baseline.py:495-499` states the rule explicitly — *"The driver does NOT append
to docs/RESULTS_LOG.md itself: two of that table's columns are Interpretation and
Decision, and a script cannot honestly fill them."*

## (e) The skeleton a new phase script is expected to follow

From `phase09_stage1_auc.py`, in order:

1. `#!/usr/bin/env python`
2. Module docstring: one-line title;
   **`Pre-registration: phases/NN_*.md, C-IDs, committed at <sha> BEFORE any number in
   this file existed`**; the objection being answered; a `Read-only:` / scope line naming
   what is not done; a `Usage:` block with the exact command line.
3. Import block (see 6a).
4. **Pre-registered constants, each under a `# --- C9-x ---` banner comment**: hardcoded
   provenance (`PRED_SHA256`, `PRED_BYTES`, `RECORDED`), `FROZEN_THRESHOLD`, `N_BOOT` /
   `BOOT_SEED` / `ALPHA`, verdict thresholds annotated
   `fixed at <sha>, from a design calculation, never from the data`, and cross-check
   expectations (`S2_EXPECT`, `S1_EXPECT`).
5. `# ===...` section: **the statistic** — the estimator, written out rather than
   imported, with the reason given.
6. `# ===...` section: **the verdict rule** — an ordered, exhaustive, mutually-exclusive
   branch function whose docstring says
   `Branch order is part of the rule, not an implementation detail.`
7. CI helpers (`pct`, `ci_of`).
8. `# ===...` section: matched/derived quantities.
9. `# ===...` section: **loading + provenance** — `sha256_of`, `load_predictions`,
   `check_provenance` that prints `OK  `/`FAIL` per figure and `sys.exit`s with
   `ABORT (C9-1): ...` on any mismatch.
10. `# ===...` section: **the run** — slice construction, the bootstrap, descriptive
    helpers, sensitivities (all reported regardless of sign, none permitted to overturn
    the primary verdict).
11. `def main():` — argparse; banner; `[C9-1] provenance`; then one labelled block per
    constraint ID in order, each printing its numbers; then git sha; then `payload`; then
    `out_dir.mkdir(parents=True, exist_ok=True)`; write; print bytes; closing banner.
12. `if __name__ == "__main__": main()`

Phase 08 follows the same shape with its own section comment style (`# ---...` rather
than `# ===...`) and an inline post-hoc block fenced by a printed `POST-HOC` header and a
`"WARNING"` key in the JSON declaring it exploratory and non-confirmatory.

---

# 7. `tests/` and `tests/test_stage1_auc.py`

`ls -la tests/` is reproduced in §3 above.

`tests/test_stage1_auc.py` — test function names only, in file order, with the section
banners that group them:

```
# the statistic
34    test_auc_of_perfect_separation_and_of_its_reverse
39    test_all_ties_give_exactly_one_half
44    test_ties_get_half_credit_not_zero_and_not_one
49    test_auc_matches_sklearn_on_random_scores
61    test_average_precision_matches_sklearn
72    test_auc_is_invariant_to_the_base_rate
87    test_average_precision_does_move_with_the_base_rate
94    test_auc_is_invariant_to_any_monotone_rescaling_of_scores
104   test_slice_count_path_agrees_with_the_direct_computation

# C9-5: the verdict rule, on both sides of every boundary
118   test_verdict_confirms_only_above_the_large_threshold_with_a_positive_interval
123   test_verdict_intermediate_band_is_declared_not_spun
128   test_verdict_narrows_below_the_floor_even_with_a_tight_interval
132   test_verdict_narrows_whenever_the_interval_touches_zero
138   test_verdict_reverses_only_when_the_whole_interval_is_below_zero
143   test_verdict_branches_are_exhaustive

# C9-8: matched operating points
157   _toy                                      (helper, not a test)
164   test_match_precision_takes_the_lowest_threshold_that_attains_the_target
178   test_match_precision_reports_failure_instead_of_substituting_a_target
186   test_match_flag_rate_breaks_ties_toward_the_lower_threshold
194   test_reference_point_uses_the_frozen_half_threshold

# C9-3: the bootstrap
208   test_bootstrap_is_deterministic_under_the_fixed_seed
217   test_bootstrap_preserves_every_cell_size
228   test_ci_brackets_the_point_estimate

# C9-10: the sensitivity reimplements hit_root's inner rule -- it must match
243   test_matching_roots_agrees_with_hit_root_on_every_text
253   test_matching_roots_respects_min_root_len
```

**How the verdict rule was tested before data loaded** — this is the pattern to match.
The module docstring (`:1-15`) states it:

```
"""Tests for phase09_stage1_auc.py, written before the real scores were loaded.

Two of these carry the whole stage:

  * `test_auc_is_invariant_to_the_base_rate` -- AUC not moving when the negative
    class is duplicated IS the reason this stage answers the reviewer's
    objection. If it moved, the analysis would be measuring the thing it was
    built to control for.
  * `test_average_precision_does_move_with_the_base_rate` -- the same
    manipulation on AP, which is why C9-9 forbids AP from arguing the verdict.
    The ban is a property of the metric, and it is demonstrated, not asserted.

The verdict rule is tested on both sides of every boundary because C9-5's whole
purpose is that no result can be argued into a branch after the fact.
"""
```

The rule is exercised on **synthetic scalars only** — e.g.
`assert s1.verdict(0.05, 0.01, 0.09) == "CONFIRMS"      # exactly at LARGE` (`:119`) —
never on loaded predictions. Six tests: one per branch, plus an exhaustiveness test.
`tests/test_stage1b_defense_auc.py` mirrors this exactly (`:37-72`): five branch tests,
`test_verdict_branches_are_exhaustive`, and `test_the_floor_is_the_preregistered_one`
which asserts the constant itself equals the document's declared value.
`tests/test_lexical_analysis.py:36` does the same with
`test_preregistered_threshold_is_what_the_document_says`.

Sibling test files also worth matching: `tests/test_stage1b_defense_auc.py` has
`test_pairing_is_real_not_two_independent_resamples` (`:112`) — the docstring at `:8-10`
explains why: *"An accidentally unpaired version would not fail loudly; it [would look
like a tighter result]"* — and abort-path tests
`test_a_missing_dump_aborts_instead_of_substituting`, `test_misaligned_dumps_abort`,
`test_provenance_check_rejects_a_dump_that_does_not_match_the_record`.

`conftest.py` (repo root, 6 lines) puts the root on `sys.path`; test files *also* do
`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` themselves and import the
phase module as `import phase09_stage1_auc as s1`.

---

# 8. `phases/09_deeper_analysis.md` — Stage 2 onward, verbatim

Lines 393–545 of the file, reproduced without summary.

---

## Stage 2 — How much of BERTurk is bag-of-words?

**The question:** how much of the 0.8271 macro-F1 is recoverable by a linear model
that only counts words — no context, no order, no understanding?

### Method

Train TF-IDF + logistic regression on the **training split only**, evaluate on the
same frozen dev split. Word unigrams + bigrams; also run a character n-gram variant
(3–5) since Turkish is agglutinative and character n-grams partially capture
morphology. `seed=42`.

Report, for each of the three systems (keyword filter, TF-IDF+LR, BERTurk):
overall macro-F1, and `lexicon_hit` / `lexicon_free` OFF-recall separately, all
with CIs. Report the BERTurk − LR delta with a paired CI.

Also extract the LR's highest-weight features for the OFF class and compare them
against Stage 8's high-skew token list. If they overlap heavily, two independent
methods have found the same lexical signal.

### Why it matters

If BERTurk beats a word-counter by only a few points, that single comparison
supports the entire thesis: apparent performance rests on surface lexical patterns
rather than comprehension.

**Watch the slice breakdown.** The interesting prediction is that BERTurk's
advantage over LR is small in `lexicon_hit` and larger in `lexicon_free` — i.e.
whatever BERTurk knows beyond word-counting is concentrated exactly where the
lexicon does not help. If that holds it is independent evidence for the diagnosis.
If BERTurk's advantage is flat across slices, say so.

### Pre-registered decision rule

State in advance what counts as "close": we pre-register that a BERTurk−LR
macro-F1 delta under 0.05 will be described as *narrow*, 0.05–0.10 as *moderate*,
above 0.10 as *substantial*. No adjusting these labels after seeing the number.

---

## Stage 3 — Do BERTurk and the keyword filter fail on the same rows?

**The question:** is BERTurk doing something categorically different from the
lexicon, or the same thing more cleanly?

### Method

Row-level comparison on dev, from existing predictions:

- 2×2 agreement table: rows both get right, both get wrong, and each direction of
  disagreement
- Of the keyword filter's 565 false negatives, how many does BERTurk also miss?
- Of BERTurk's 285 false negatives, what share are also filter false negatives?
- Cohen's κ between the two systems' errors, and the same broken down by slice

### Pre-registered decision rule

- **BERTurk's errors are largely a subset of the filter's** → BERTurk is a cleaner
  lexicon, and that is a strong, quotable framing of the diagnosis.
- **Substantial non-overlap** → BERTurk has learned something the lexicon has not,
  and the diagnosis needs qualifying. Report the size of what it learned.

---

## Stage 4 — Is the deixis signal used, or merely present?

**Current limitation, stated in `results/08_lexical_analysis/findings.md`:**
co-occurrence shows the signal was *available*, not that the model *used* it. This
stage tests use.

### Method

Inference only, no training. On the 118 no-profanity false positives:

1. **Perturbation.** Replace second-person deictic tokens (`sen`, `siz`, `sizin`,
   `senin`, `sizi`, `sana`, `size` — enumerate the exact set and commit it before
   running) with third-person equivalents. **Replace, do not delete** — Turkish is
   agglutinative and deletion breaks agreement and case. Where a clean third-person
   substitution is impossible, skip the row and report how many were skipped.
2. Re-run the frozen model on the perturbed rows and report the change in mean
   `p_OFF` and in the number still predicted OFF, with a paired CI.
3. **Control, mandatory.** Repeat with a non-deictic token of comparable document
   frequency, substituted for a comparable one. Without this, any movement measures
   sensitivity to perturbation in general rather than to deixis specifically.
4. **Second control.** Run the same perturbation on a matched sample of correctly
   classified NOT rows. If `p_OFF` moves there too, the effect is not specific to
   the error set.

### Pre-registered decision rule

- **`p_OFF` drops on deictic perturbation, control flat** → the model uses the
  signal. The claim upgrades from co-occurrence to attribution and the ceiling
  currently attached to the finding can be lifted, with the perturbation method
  stated.
- **Both move** → measuring perturbation sensitivity, not deixis. Report as
  inconclusive and keep the existing ceiling.
- **Neither moves** → the co-occurrence is incidental. Report as a null and keep
  the ceiling. This is a real answer.

---

## Stage 5 — `[MASK]` alternative *(requires GPU; authorise separately)*

**The hypothesis:** 1a failed because `[MASK]` exists in training and never at
inference, giving the model a cue it cannot use in deployment.

**Method:** rebuild the 1a operator replacing the profanity with a **different
randomly chosen profanity** from the frozen lexicon rather than `[MASK]`. Same 382
qualifying rows, same filter, same hyperparameters, same seed. Train and evaluate
on the same four metrics.

**Value:** if this recovers `lexicon_free` recall where `[MASK]` lost it, the
project's one failed component becomes a working one, and the mechanism is
explained rather than guessed.

**Risk:** it may fail too — but a failure with a tested mechanism is reportable
where an untested guess is not.

**Cost:** operator rewrite plus one ~5-minute training run.

---

## Stage 6 — Class weighting *(requires GPU; authorise separately)*

`results/08_lexical_analysis/findings.md` records this as an explicit gap: the
corpus is 1:4.18, no weighted variant was ever trained, and its contribution to the
absolute level of `lexicon_free` recall is unmeasured. The advisor also raised data
balance.

**Method:** one training run with inverse-frequency class weights, everything else
identical. Report all four metrics plus the recall gap.

**What it answers:** whether the absolute level of profanity-free recall is partly
an imbalance artefact. Note in advance that this cannot explain the *gap* — one
model and one threshold across two disjoint subsets, so a global imbalance
depresses both alike. It speaks to the level, not the difference.

**Cost:** one ~5-minute training run.

---

## Output

Each stage writes to `results/09_deeper_analysis/stage_N/` with metrics JSON, a
`findings.md`, and a `RESULTS_LOG.md` row. Aggregate statistics may be committed;
row text stays out of git as always.

Stages 1–4 touch no GPU and no training. Stages 5–6 do, and are not to be started
without explicit authorisation from the project lead.

**No intervention is to be proposed from any stage. Measurement only.**

---

## Note on the authorisation status of these stages

The audit request described these as "pre-registered and unauthorised." The document
draws the line differently, and it matters: **Stages 2, 3 and 4 are pre-registered *and*
cleared** — line 542 says "Stages 1–4 touch no GPU and no training," and Stage 4 is
explicitly "Inference only, no training." Only **Stages 5 and 6** carry
*(requires GPU; authorise separately)* and the standing bar at line 543.

The overlap risk is real and specific. Stages 2, 3 and 4 already fix, in git:

- **Stage 2** — the three-system comparison, the slice breakdown prediction, and a
  three-band label rule (`<0.05` narrow / `0.05–0.10` moderate / `>0.10` substantial).
- **Stage 3** — the exact four quantities (2×2 table, 565 filter FNs, 285 BERTurk FNs,
  Cohen's κ by slice) and a two-branch decision rule.
- **Stage 4** — the deictic token set to be enumerated-and-committed-before-running, the
  replace-not-delete constraint, **two mandatory controls**, and a three-branch rule.

Note also that these three stages are pre-registered at a **lower resolution** than
Stages 1 and 1b: they have prose decision rules but no `C9-x` constraint IDs (the IDs run
C9-1..C9-11 for Stage 1 and C9-12..C9-17 for Stage 1b, then stop). If you are about to
specify one of these stages, the existing text is the binding registration for the
decision rule; what is missing is the constraint-ID layer, and adding that is a different
act from re-specifying the rule.

One further caution from §2: **Stage 3 needs the keyword filter's per-row dev
predictions, and Stage 2 needs BERTurk's.** Only
`results/01_baseline_berturk/dev_predictions.csv` exists on disk, and it is untracked.
The keyword filter's per-row output is not dumped anywhere — `phase01_baseline.py`
computes `kw_pred` in memory and writes only its aggregate block to `metrics.json`. That
is a blocker to check before specifying Stage 3, of the same kind that blocked Stage 1b.

---

# CONVENTIONS A NEW PHASE MUST MATCH

Import and call these. Do not reimplement.

## Configuration — never hardcode a path

- `import config` — `config.SEED` (42), `config.MAX_LEN` (128), `config.DEV_FRACTION`
  (0.15), `config.RESULTS_DIR`, `config.SPLITS_DIR`, `config.LEXICON_PATH`,
  `config.COLTEKIN_TRAIN`, `config.MODEL_BASELINE`, `config.TEST_SPEND_RECORD`

## Data and split

- `data_io.sha256(path) -> str`
- `data_io.load_coltekin_train(path=None) -> rows`
- `data_io.get_split(all_rows, path, train_sha256, seed=None, dev_fraction=None) -> (train_rows, dev_rows, meta)`
  — the only split entry point
- `data_io.dev_fingerprint(dev_rows) -> str` — frozen value `034415af3a23b388`
- guard: `if not meta["reused_existing_file"]: raise SystemExit("ABORT: the split was CREATED, not loaded.")`
- `data_io.load_coltekin_test(run_final_test=False, ...)` — **do not call.** The set is
  SPENT; it raises `PermissionError`.

## Lexicon and slices — frozen, ported verbatim from Day 1

- `lexicon.load_lexicon(path=None) -> sorted list`
- `lexicon.tokens(text) -> list[str]`
- `lexicon.tr_lower(s) -> str`
- `lexicon.hit_root(text, lex_list) -> bool` — the adopted definition of
  "the lexicon caught it"
- `lexicon.MIN_ROOT_LEN` (3), `lexicon.SKIP`, `lexicon.ABBREV_PROFANITY`
- `evaluate.tag_slices(rows, lex_list) -> list["lexicon_hit"|"lexicon_free"]`
- If you must reimplement a frozen rule, follow `phase09_stage1_auc.matching_roots` —
  say why in the docstring and add an equivalence test.

## Metrics

- `evaluate.score(y_true, y_pred, n_boot=1000, seed=42, alpha=0.05, with_ci=True) -> dict`
- `evaluate.score_by_slice(y_true, y_pred, slice_tags, n_boot=1000, seed=42, alpha=0.05) -> dict`
- `evaluate.macro_f1(y_true, y_pred)`, `evaluate.off_recall(y_true, y_pred)`
- `evaluate.sklearn_report(y_true, y_pred, title="", digits=4, strict=True)` — raises if
  sklearn disagrees beyond 1e-9
- **Binding constraint:** cross-slice comparison is OFF-recall only. Emit
  `"macro_f1": None` per slice with a note.
- AUC: `phase09_stage1_auc.auc_ties(pos, neg)` — half credit for ties. Not in `src/`.
- AP: `phase09_stage1_auc.average_precision(pos, neg)` — base-rate sensitive; C9-9
  forbids it arguing a verdict.

## Confidence intervals — pick the family that matches the estimator

- Label-list metrics, one system:
  `evaluate.bootstrap_ci(y_true, y_pred, metric="macro_f1", n_boot=1000, seed=42, alpha=0.05)`
- Label-list metrics, **two systems on the same rows (paired)**:
  `evaluate.bootstrap_delta_ci(y_true, pred_a, pred_b, metric="macro_f1", n_boot=1000, seed=42, alpha=0.05)`
  — A is treatment, B is control
- Label-list metrics, **two disjoint slices (unpaired)**:
  `evaluate.bootstrap_gap_ci(y_true_a, y_pred_a, y_true_b, y_pred_b, metric="off_recall", n_boot=1000, seed=42, alpha=0.05)`
  — A is `lexicon_hit`, B is `lexicon_free`
- Operating point at a fixed threshold:
  `calibration.bootstrap_operating_point(y_true, y_pred, p_off, threshold, n_boot=1000, seed=42, alpha=0.05)`
- AUC-style, and any new estimator: follow phase 09 — write a local bootstrap returning
  **raw replicate lists**, then summarise with
  `phase09_stage1_auc.ci_of(vals) -> {"ci_low", "ci_high"}`. Import `ci_of`; do not write
  a sixth percentile helper.
- Percentile-argument trap: `evaluate._percentile(vals, q)` takes q in **[0,1]**;
  `phase09_stage1_auc.pct(vals, q)` takes q in **0–100**.
- RNG: stdlib `random.Random(seed)` for the `src/` families,
  `np.random.default_rng(seed)` for the phase-09 families. Do not mix within one
  estimator.
- Constants: `N_BOOT = 10000`, `BOOT_SEED = 42`, `ALPHA = 0.05` as module-level names for
  measurement phases (`src/` defaults remain 1000/42/0.05).
- Return-key vocabulary: `ci_low`, `ci_high`, `delta`, `excludes_zero`, `n_boot`,
  `n_boot_used`, `n_boot_undefined`, `alpha`, `seed`, `resampling`.

## Prediction dumps

- `phase09_stage1_auc.load_predictions(path) -> (rows, sha256, bytes)` — adds `r["p_off"]`
- `phase09_stage1_auc.sha256_of(path) -> str`
- `phase09_stage1_auc.Slice(name, pos_scores, neg_scores)` with
  `.counts(pos_idx, neg_idx)`, `.auc_from_counts(cp, cn)`, `.sweep(cp, cn)`, `.n_pos`,
  `.n_neg`
- `phase09_stage1_auc.describe(scores) -> dict`
- `phase09_stage1_auc.FROZEN_THRESHOLD` (0.5), `PRED_SHA256`, `PRED_BYTES`
- CSV schema: `row_id,text,gold,pred,confidence,slice`
- Do **not** use `phase04_calibration.load_predictions` — different contract, returns
  rows only.

## Provenance and results

- Inline `git rev-parse --short HEAD` in a `try/except` returning `"?"` — the
  phase-08/09 convention; `phase01_baseline.git_sha()` only if you need the `-dirty` flag
- Provenance by recomputed content: hardcode the recorded figures as a module constant,
  print `OK  `/`FAIL` per figure, `sys.exit("ABORT (Cx-y): ...")` on mismatch — pattern at
  `phase09_stage1_auc.check_provenance` / `phase09_stage1b_defense_auc.check_run`
- Payload keys, in order:
  `run_id, created_at, git_sha, preregistration, scope, inputs{..., "test_set_touched": False}, ...`
- Write with `out_dir.mkdir(parents=True, exist_ok=True)` then
  `out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")`,
  then print `f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)"`
- Filename is phase-specific (`stage2_*.json`), not `metrics.json`
- `phase01_baseline.mirror_outputs(out_dir, mirror_dir, required=None, marker="metrics.json")`
  — only if outputs are gitignored or born in a Colab session; phase 08 declined it with a
  stated reason
- `findings.md` and the `RESULTS_LOG.md` row are written **by a human**, never by the
  script

## Script shape

- `#!/usr/bin/env python`; docstring naming the pre-registration file, the C-IDs, the
  commit sha, the scope line, the `Usage:` block
- Imports: stdlib / blank / third-party / blank /
  `sys.path.insert(0, str(Path(__file__).resolve().parent))` / blank / `import config`,
  `from src import ...` with `# noqa: E402`
- Constants under `# --- Cx-y ---` banners, verdict thresholds annotated as fixed at a
  named commit
- Verdict rule as an ordered, exhaustive, mutually-exclusive branch function, docstring
  `Branch order is part of the rule, not an implementation detail.`
- `main()` with bare `argparse.ArgumentParser()`, `--n_boot` exposed, `--seed` not;
  banner, one labelled block per constraint ID, write, closing banner
- `if __name__ == "__main__": main()`
- stdout direct — no Tee unless the process loads transformers;
  `sys.stdout.reconfigure(encoding="utf-8")` in a `try/except` if emitting Turkish

## Tests, before any data loads

- `tests/test_<phase>.py`,
  `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))`,
  `import <phase_module> as pN`
- One test per verdict branch on **synthetic scalars**, plus
  `test_verdict_branches_are_exhaustive`, plus `test_the_floor_is_the_preregistered_one`
  asserting the constant matches the document
- `test_bootstrap_is_deterministic_under_a_fixed_seed`,
  `test_ci_brackets_the_point_estimate`
- If the estimator is paired: `test_pairing_is_real_not_two_independent_resamples`
- Abort-path tests for every `sys.exit` in the provenance check
- Cross-check any hand-rolled statistic against sklearn (no scipy in `requirements.txt`)
