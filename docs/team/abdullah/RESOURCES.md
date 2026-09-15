# Resources for m3_encoder

Read this first. It lists everything m3 depends on: what each thing is, where it
lives, its sha256, and how you get it. Every path, count, digest and
hyperparameter here was checked on 2026-09-15 against the files themselves: the
local copies and the committed results files. None of it was copied from a README.
Anything not verified is marked as not verified, and everything unresolved is
listed at the end under **Open — Musaab owes you this**.

`AI/modules/m3_encoder/spec.md` is the source of truth for what m3 must do. This
file only covers the resources.

---

## Read these four points before anything else

1. **The baseline is EPOCH 1.** Epochs 1 and 3 tie exactly on dev macro-F1
   (0.8270752670616224) with identical confusion matrices, but they are
   different models: they disagree on **198 of 4,764** dev rows. Picking a
   checkpoint from that tie is not a free choice. Every reported baseline number
   is epoch 1's (`diagnosis/results/01_baseline_berturk/metrics.json` →
   `checkpoint_tie`). The checkpoint file stores `"epoch": 0` because it counts
   from zero, so 0 means epoch 1.
2. **Two thresholds, two different things. Don't mix them.**
   - **0.5** is the baseline's *decision* threshold: OFF if p(OFF) ≥ 0.5 (argmax).
     Source: `diagnosis/results/01_baseline_berturk/run_config.json` →
     `hyperparams.threshold`. Every baseline metric below uses it.
   - **0.663171** is the phase 04 *deferral* threshold, an operating point on
     decision confidence `max(p_OFF, 1 − p_OFF)` that decides whether a case is
     auto-resolved or queued for review
     (`diagnosis/results/04_calibration/calibration.json` → operating point
     `high_automation`; the rule is stated in `cal_eval_split.json` →
     `deferral_rule`). It is not an OFF/NOT cut-off.
   - Using 0.663171 as a decision threshold changes what a number means, and
     nothing will warn you.
3. **The official test set is spent and locked.** See [Test set](#the-official-test-set--hard-rule).
4. **Use the frozen split. Never make a new one.** See [Frozen split](#the-frozen-split).

---

## Data files

None of these are in git (`diagnosis/.gitignore`: `data/**`), for licensing and
size. They exist on Musaab's machine at the paths below, and these are the
bytes every frozen number was measured on. You get them from Drive. After
downloading, check the sha256 **before** using any file: a mismatch means you
have a different file, and every comparison with the baseline breaks.

| File | What it is | Path the code expects (under `diagnosis/`) | Bytes | sha256 | How you get it |
|---|---|---|---|---|---|
| `offenseval-tr-training-v1.tsv` | Çöltekin OffensEval-TR 2020 training corpus. 31,756 rows, labels OFF/NOT. **The only corpus you train and evaluate on.** | `data/coltekin/offenseval-tr-training-v1.tsv` | 4,101,728 | `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa` | Drive: **MUSAAB: paste link here** |
| `offenseval-tr-testset-v1.tsv` | Official test set, text only. 3,528 rows. **LOCKED, never touch it.** | `data/coltekin/offenseval-tr-testset-v1.tsv` | 449,553 | `9052784e13248e58658e34a4f86a3463ef8b2594d2feb289e4b29bba2866b437` | Drive: **MUSAAB: paste link here**. Listed so the record is complete. You don't need it and must not read it. |
| `offenseval-tr-labela-v1.tsv` | Gold labels for the test set. Content is comma-separated with no header, despite the `.tsv` extension. **LOCKED, never touch it.** | `data/coltekin/offenseval-tr-labela-v1.tsv` | 35,280 | `ae9b0837e948c3d9c3a147d2a415989a4940a7756d5821b3289276574941c9e3` | Drive: **MUSAAB: paste link here**. Same rule as the test set. |
| `karaliste.txt` | Frozen profanity lexicon from Day 1. Defines the `lexicon_hit` / `lexicon_free` slices. | `data/lexicon/karaliste.txt` | 5,988 | `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` | Drive: **MUSAAB: paste link here** |

Where the digests are recorded:
- Training corpus: `diagnosis/results/01_baseline_berturk/run_config.json`, `results/day1_report.json`, `results/08_lexical_analysis/token_stats.json`.
- Lexicon: `run_config.json`, `results/day1_report.json`, `results/05_final_test/TEST_SET_SPENT.json`.
- Test and gold files: `results/05_final_test/TEST_SET_SPENT.json`.

All four local files matched their recorded digests on 2026-09-15.

**Where the files go.** `diagnosis/config.py` resolves `DATA_DIR` as
`diagnosis/data/`, or as whatever `NSOSYAL_DATA` is set to. Locally, put the
files under `diagnosis/data/` exactly as above. On Colab they stay on Drive and
`NSOSYAL_DATA` points at them ([COLAB_SETUP.md](COLAB_SETUP.md)).

**How to read the training corpus.** Use `diagnosis/src/data_io.py`
(`load_coltekin_train`). Never use `pandas.read_csv`. The TSV has no quoting,
tweets can contain tabs, and default parsers silently corrupt rows. The module
docstring lists the traps.

`diagnosis/data/coltekin/` also holds `offenseval-annotation.txt` and
`readme-trainingset-tr.txt`. Neither is read by any code, and no digest for
them is recorded in `diagnosis/results/`.

`diagnosis/data/mayda/` and `diagnosis/data/beyhan/` are **MISSING** (they hold
only `.gitkeep`). They are cross-corpus sources marked "never trained on", and
no code reads them, so they do not block m3.

---

## The frozen split

| | |
|---|---|
| Path | `diagnosis/data/splits/split_seed42.json`. **Committed to git**, and the only file under `data/` that is. |
| Bytes / sha256 | 815,066 / `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2`. Same bytes in a clone: `diagnosis/.gitattributes` sets `* -text`, so git does no line-ending conversion. |
| Seed | 42 |
| Ratio | 85/15, stratified by label (`dev_fraction` 0.15) |
| Source rows | 31,756 (`n_rows`), built from the training corpus with sha256 `8509c01c…` |
| Train | **26,992** ids: NOT 21,781 / OFF 5,211 |
| Dev | **4,764** ids: NOT 3,844 / OFF 920 |
| Overlap | 0 ids |
| Dev fingerprint | `034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4` (sha256 over the sorted dev ids; recomputed and matching) |

**Why you must use it rather than make a new one.**
- The frozen baseline was measured on exactly these 4,764 dev rows. So was every
  study result after it: the results files of phases 03, 04 and 05 record
  fingerprint `034415af…` in full, and phase 11 records its first 16 characters.
- m3's first job is a comparison against that baseline (spec §7). On a different
  dev set, the difference between m3 and the baseline mixes model differences
  with data differences, and nobody can separate the two afterwards.
- A new split with the same seed is not a substitute. The file is the authority,
  not the algorithm (`data_io.py`, comment above `save_split`).

Load it through `data_io.get_split(all_rows, path, train_sha256)`. It verifies
the corpus hash, missing ids and train/dev overlap, and reports
`reused_existing_file`. If that value is ever `False`, you created a split
instead of loading the frozen one. Stop.

---

## The frozen baseline

**The baseline exists. It is not in git (`*.pt` is ignored) and it lives only
on local disk and Drive.**

| | |
|---|---|
| What it is | Phase 01 BERTurk fine-tune, `best.pt` = **epoch 1** |
| Bytes | 442,544,192 |
| sha256 | `43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca` (recorded in `diagnosis/docs/RESULTS_LOG.md`, 2026-08-23 row) |
| Local copies (Musaab's machine) | `demo_assets/checkpoints/raw.pt`. A byte-identical copy sits at `other/New folder/best.pt`. |
| Training-time location | `<drive>/checkpoints/01_baseline_berturk/best.pt`, per `diagnosis/phase03_train_defense.py:23` and `diagnosis/demo/build_assets.py:16`. Not verified on Drive in this session. |
| How you get it | Drive: **MUSAAB: paste link here** |
| Decision threshold | **0.5** (`run_config.json` → `hyperparams.threshold`) |

**Contents, checked on 2026-09-15.**
- A dict with exactly three keys: `dev_macro_f1`, `epoch`, `model`.
- `epoch` = 0 (0-indexed, meaning epoch 1).
- `dev_macro_f1` = 0.8270752670616224.
- `model` holds 201 tensors and 110,618,882 parameters.
- It loads with `strict=True` into `BertForSequenceClassification`, with
  `id2label {0: NOT, 1: OFF}`.

**Loading it** follows the study's own path
(`diagnosis/phase03_train_defense.py:196-198`, `diagnosis/src/models.py:139`):

```python
tokenizer, model = models.load_model("dbmdz/bert-base-turkish-cased")   # diagnosis/src/models.py
state = torch.load(BASELINE_CKPT, map_location="cuda", weights_only=False)
model.load_state_dict(state["model"])
```

Probability of OFF is softmax index 1 (`src.models.predict` returns `p_off`).

**Recorded baseline numbers on the frozen dev split, threshold 0.5.**
Source: `diagnosis/results/01_baseline_berturk/metrics.json` → `berturk`. The
bootstrap used 1,000 resamples, α 0.05, seed 42.

| Metric | Value | 95% CI |
|---|---|---|
| macro-F1 | 0.8271 | [0.8139, 0.8405] |
| OFF recall | 0.6902 | [0.6603, 0.7191] |
| OFF precision | 0.7488 | not recorded |
| Confusion | tn 3631 · fp 213 · fn 285 · tp 635 | |
| OFF recall, `lexicon_hit` (614 rows) | 0.8930 | [0.8618, 0.9248] |
| OFF recall, `lexicon_free` (4,150 rows) | 0.5628 | [0.5210, 0.6010] |

**Per-row baseline predictions.** `dev_predictions.csv` has one row per dev id
(columns `row_id,text,gold,pred,confidence,slice`), produced by the epoch-1
checkpoint. It lets you compare against the baseline row by row without
re-running it.
- 736,591 bytes, sha256 `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346`.
  It matches `results/04_calibration/cal_eval_split.json` and
  `results/11_prior_correction/metrics.json`.
- Not in git: it carries corpus text (`diagnosis/.gitignore`:
  `results/**/*predictions*.csv`).
- Local path: `diagnosis/results/01_baseline_berturk/dev_predictions.csv`.
- Drive: **MUSAAB: paste link here**

Because the checkpoint exists, you do not retrain the baseline. If it were ever
lost, these recorded hyperparameters reproduce it.

---

## Recorded hyperparameters

All values come from one results file, not from any README:
**`diagnosis/results/01_baseline_berturk/run_config.json`**.

| Setting | Value | Key in that file |
|---|---|---|
| Model | `dbmdz/bert-base-turkish-cased` | `model` |
| Epochs | 3 (best = epoch 1, see above) | `hyperparams.epochs` |
| Batch size | 32 | `hyperparams.batch_size` |
| Learning rate | 2e-05 | `hyperparams.lr` |
| max_len | 128 | `hyperparams.max_len` |
| Precision | fp16 (`"fp16": true`) | `hyperparams.fp16` |
| Warmup | ratio 0.1 | `hyperparams.warmup_ratio` |
| Weight decay | 0.01 | `hyperparams.weight_decay` |
| Class weighting | none (`null`) | `hyperparams.class_weighting` |
| Seed | 42 | `hyperparams.seed` |
| Decision threshold | 0.5 | `hyperparams.threshold` |
| Bootstrap | n_boot 1000, alpha 0.05, seed 42 | `bootstrap` |
| Environment | torch 2.11.0+cu128, transformers 5.15.0, scikit-learn 1.6.1, NVIDIA L4 | `environment` |

The same epochs, batch size, lr, max_len and seed also appear in
`diagnosis/results/03_defense/run_raw/metrics.json`, which re-evaluated the
same checkpoint. m3's own pinned versions are in
`AI/modules/m3_encoder/requirements.txt`, matched to the environment row above.

---

## The official test set — hard rule

**The official Çöltekin test set is SPENT.** It was used once for the project's
single permitted held-out measurement on 2026-08-16
(`diagnosis/results/05_final_test/TEST_SET_SPENT.json`, run `05_final_test`,
n_test 3,528).

**It is locked in code.** `diagnosis/src/data_io.py` `load_coltekin_test()`
refuses in two ways:
- without `run_final_test=True` (line 382), and
- while `TEST_SET_SPENT.json` exists (lines 395-408), even with the flag.

The spent record is committed, so the lock survives a fresh clone. Both refusals
were checked on 2026-09-15, and `diagnosis/tests/test_test_set_guard.py` passes
(6 tests).

```python
if config.TEST_SPEND_RECORD.exists():
    spent = json.loads(config.TEST_SPEND_RECORD.read_text(encoding="utf-8"))
    raise PermissionError(
        "The official Çöltekin test set has already been SPENT.\n" ...
```

**It is never reopened.** Not to "just look", not for m3, not with a copy of the
file read by other code, and not by deleting the record.

**Any new number from it invalidates the project's methodological
discipline.** A second measurement is no longer held-out: every decision made
after the first read was informed by it. That would put in doubt the single
honest test result the project has, not only your number. All m3 numbers are dev
numbers on the frozen split. If you ever think you need the test set, stop and
ask Musaab. Do not look for a way around the lock.

---

## Open — Musaab owes you this

These were **not** resolved when this file was written. None of them is hidden:
if something here blocks you, it is waiting on Musaab, not on you.

1. **Drive links.** Five data files, the baseline checkpoint and
   `dev_predictions.csv` are marked *MUSAAB: paste link here*. Musaab uploads
   them, confirms each sha256 above after upload, and pastes the links.
2. **Drive path of the baseline checkpoint.** The study's code says
   `<drive>/checkpoints/01_baseline_berturk/best.pt`. Nobody has checked it on
   Drive.
3. **Çöltekin corpus size in the spec is wrong or unexplained.** m3 spec §5 says
   "36,232 tweets". The verified files hold 31,756 training + 3,528 test =
   **35,284**. Musaab resolves this. The spec has not been edited, and a jury
   will check this number. Until then, don't quote 36,232.
4. **How m3 gets corpus paths.**
   - `AI/` has no config of its own. The only place the corpus paths are defined
     is `diagnosis/config.py`.
   - m3 cannot simply import it. On 2026-09-15 a one-line `import config` placed
     in `AI/modules/m3_encoder/` made
     `AI/tests/test_architecture.py::test_modules_import_only_declared_dependencies`
     fail. Everything under a module folder may import only the standard
     library, `contracts`, its own module and what its `requirements.txt`
     declares.
   - The only working route today is running data-loading code **outside**
     `AI/modules/m3_encoder/` with `diagnosis/` on `sys.path`. That is what the
     Colab smoke test does.
   - Where m3's training and evaluation code lives, and how it receives paths,
     is **undecided**. Musaab decides; don't invent a mechanism.
5. **Gold labels for the A head on the frozen split.**
   - The A head scores "profanity present" (spec §1, §3).
   - The Çöltekin corpus carries only OFF/NOT. `data_io.assert_binary_labels`
     rejects anything else, and the split counts are OFF/NOT only.
   - There is no gold "profanity present" label on the frozen split. The
     `lexicon_hit` slice is a keyword match, not a human label.
   - Still to decide: what the A head's per-code metrics are measured against,
     and which m3 output is compared with the baseline's binary OFF numbers.
     Musaab decides.
6. **Training data for the B head.**
   - No corpus labelled with B1–B5 was found in the repo or on Musaab's machine.
   - The allowed datasets in spec §5 besides Çöltekin (Toraman v2, TDDİ-2023,
     ATC) are not on that machine either.
   - The source for the B head is unresolved.
7. **C slice.** The C head is deferred ([START_HERE.md](START_HERE.md)).
   Musaab is labelling a C1–C5 slice in parallel. No date has been set.
8. **Python version.** The pinned scikit-learn 1.6.1 ships wheels only up to
   Python 3.13 (checked on PyPI 2026-09-15), so the pins need Python 3.11–3.13.
   Colab's current Python version was not checked. The smoke test refuses
   anything outside that range.
9. **Repo visibility.** The Colab runbook clones with a `GH_TOKEN`, as the
   study's runbook did. Whether the repo is still private was not checked.
10. **The m5 sarcasm corpus is unnamed.** This is your research task, not
    Musaab's, but it is unresolved ([START_HERE.md](START_HERE.md)).
