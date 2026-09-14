# Onboarding-readiness audit — 2026-08-18

**Method.** Read-only inventory of the working tree, then one controlled cold-clone
test. No training, no forward pass, no GPU. The official test set was not opened.
Nothing under `report/` or `results/` was created, edited or deleted; `git status`
was clean before and after. All stdout below is real, captured output.

**Scope note.** Part B's clone was created outside the working tree and deleted
afterwards (§B5). No file was copied into it by hand and nothing was fetched from
the Drive mirror — the failures are the finding.

---

## PART A — what a new team member actually receives on clone

### A1. Ignored paths, and untracked files under `results/` and `demo/`

**Total paths matched by ignore rules: 8,002.** By top-level directory:

| Prefix | Count | Note |
|---|---:|---|
| `.venv/` | 7,952 | local virtualenv, not project content |
| `__pycache__/` (root) | 10 | bytecode |
| `tests/__pycache__/` | 10 | bytecode |
| `.idea/` | 8 | PyCharm |
| `src/__pycache__/` | 7 | bytecode |
| `data/` | 6 | **corpus + lexicon — project content** |
| `.pytest_cache/` | 5 | |
| `demo/__pycache__/` | 2 | bytecode |
| `results/` | 1 | **`dev_predictions.csv` — project content** |
| `.claude/settings.local.json` | 1 | matched by the user's **global** ignore (`~/.config/git/ignore:3`), not by repo `.gitignore` |

Stripping tooling noise, the ignored **project content** is exactly seven files:

```
data/coltekin/offenseval-annotation.txt          .gitignore:12  data/**
data/coltekin/offenseval-tr-labela-v1.tsv        .gitignore:12  data/**
data/coltekin/offenseval-tr-testset-v1.tsv       .gitignore:12  data/**
data/coltekin/offenseval-tr-training-v1.tsv      .gitignore:12  data/**
data/coltekin/readme-trainingset-tr.txt          .gitignore:12  data/**
data/lexicon/karaliste.txt                       .gitignore:12  data/**
results/01_baseline_berturk/dev_predictions.csv  .gitignore:35  results/**/*predictions*.csv
```

`.gitignore` also declares patterns that currently match **nothing on disk**,
because the artifacts do not exist locally at all: `checkpoints/`, `runs/`,
`*.pt` / `*.bin` / `*.safetensors` / `*.zip`, and `demo_assets/` (the 885.9 MB
demo bundle).

#### Untracked files under `results/`

| File | Size (bytes) | Read as an input by any script? |
|---|---:|---|
| `results/01_baseline_berturk/dev_predictions.csv` | **736,591** | **Yes** — `phase09_stage1_auc.py` (default `--pred`), `phase04_calibration.py` (`--baseline_pred`), and it is the stated source of every number in `results/02_failure_analysis/*` |

That is the only untracked file under `results/`. The other 33 files there are tracked.

#### Untracked files under `demo/`

| File | Size (bytes) | Read as an input? |
|---|---:|---|
| `demo/__pycache__/__init__.cpython-314.pyc` | 135 | No — compiler output |
| `demo/__pycache__/app.cpython-314.pyc` | 23,933 | No — compiler output |

All five real `demo/` files (`README.md`, `__init__.py`, `app.py`,
`build_assets.py`, `examples.json`) are tracked.

Incidental: root `__pycache__/` still holds `phase06_lexical_analysis.cpython-314.pyc`,
bytecode for a script that no longer exists under that name (now `phase08_lexical_analysis.py`).

### A2. `results/01_baseline_berturk/dev_predictions.csv`

**Not tracked.** Ignored by `.gitignore:35` — `results/**/*predictions*.csv`, the
exception listed last so it wins over the `!results/**/*.json` allowances above
it. It exists in the working tree at 736,591 bytes; it is absent from any clone.

Scripts that read it as an input:

| Script | How |
|---|---|
| `phase09_stage1_auc.py` | `--pred` default is this exact path (line 450); `load_predictions()` → `check_provenance()` |
| `phase04_calibration.py` | via `--baseline_pred` (line 283) — optional third input alongside the two `03_defense` dumps |
| `phase03_compare.py` | reads the *sibling* dumps `results/03_defense/run_*/dev_predictions.csv` (line 40), same ignore rule |
| `phase09_stage1b_defense_auc.py` | imports `phase09_stage1_auc.load_predictions` (lines 129–130) for the `03_defense` dumps |
| `tests/test_split_and_metrics.py` | only as a fabricated fixture in `tmp_path`; does not read the real file |

Non-script consumers that name it as their source of record:
`results/02_failure_analysis/{findings.md, fn_tags.json, fp_function_tags.json, slice_sensitivity.json}`,
`results/09_deeper_analysis/stage_1/findings.md`, `report/05_sinirliliklar.md`,
`phases/{01,04,09}*.md`.

### A3. Corpus, lexicon, split file

| File | Tracked? | Size on local disk |
|---|---|---:|
| `data/coltekin/offenseval-tr-training-v1.tsv` | **NO** (`.gitignore:12 data/**`) | 4,101,728 |
| `data/coltekin/offenseval-tr-testset-v1.tsv` | **NO** | 449,553 |
| `data/coltekin/offenseval-tr-labela-v1.tsv` (gold) | **NO** | 35,280 |
| `data/lexicon/karaliste.txt` | **NO** | 5,988 |
| `data/splits/split_seed42.json` | **YES** (`.gitignore:20 !data/splits/*.json`) | 815,066 |

`git ls-files data/` returns exactly five paths: four `.gitkeep` files and
`split_seed42.json`. A clone gets the directory shape and the split, and no data.

### A4. Definitive table — required inputs absent from a fresh clone

Verified by execution in the cold clone (Part B), not by reading alone.

| Script | Required input | Tracked? | Where it actually lives |
|---|---|---|---|
| `day1_gate_en.py` | `data/coltekin/offenseval-tr-training-v1.tsv` | **NO** | local working tree; Drive `<drive>/data` |
| | `data/lexicon/karaliste.txt` | **NO** | local working tree; Drive `<drive>/data` |
| `phase01_baseline.py` (preflight) | `COLTEKIN_TRAIN`, `LEXICON_PATH` | **NO** | as above |
| | `data/splits/split_seed42.json` | YES | in the clone |
| `phase01_baseline.py --stage train` | above + CUDA GPU | n/a | Colab L4 |
| `phase03_make_augmentation.py` | `COLTEKIN_TRAIN`, lexicon, split | **NO** / **NO** / YES | as above |
| `phase03_train_errors.py` | same + GPU | **NO** | as above |
| `phase03_train_defense.py` | same + GPU (or `--load_checkpoint best.pt`) | **NO** | checkpoints: Drive `<drive>/checkpoints/…/best.pt`, gitignored, **not in the local working tree either** |
| `phase03_compare.py` | `karaliste.txt` | **NO** | local working tree |
| | `results/03_defense/run_{raw,1a,1a1b,1a1b_d}/dev_predictions.csv` (×4) | **NO** | **Drive mirror only** — absent from the local working tree too |
| `phase04_calibration.py` | `results/03_defense/run_raw/dev_predictions.csv` | **NO** | **Drive mirror only** |
| | `results/03_defense/run_1a1b_d/dev_predictions.csv` | **NO** | **Drive mirror only** |
| `phase05_final_test.py` | test TSV + gold TSV + lexicon | **NO** | local working tree |
| | `raw_ckpt`, `defense_ckpt` (`.pt`) | **NO** | Drive only |
| | — blocked regardless by `TEST_SET_SPENT.json` | YES (tracked) | in the clone, and the refusal travels with it |
| `phase05_paired_deltas.py` | `results/05_final_test/test_predictions.csv` | **NO** | **Drive mirror only** |
| `phase08_lexical_analysis.py` | `COLTEKIN_TRAIN`, lexicon, split | **NO** / **NO** / YES | local working tree |
| `phase09_stage1_auc.py` | `results/01_baseline_berturk/dev_predictions.csv` | **NO** | local working tree **and** Drive mirror (byte-verified, sha256 `a2f5bddf…`) |
| | `karaliste.txt` (line 535, C9-10 sensitivity) | **NO** | local working tree |
| `phase09_stage1b_defense_auc.py` | `run_raw` + `run_1a1b_d` dumps | **NO** | **Drive mirror only** |
| `demo/app.py` | `demo_assets/` bundle (885.9 MB: tokenizer, 2 `.pt`, lexicon, `operating_point.json`) | **NO** | Drive / rebuilt by `build_assets.py` on a GPU+network machine |
| `demo/build_assets.py` | two `.pt` checkpoints + lexicon | **NO** | Drive only |
| | `results/04_calibration/calibration.json` | YES | in the clone |
| `tests/_verify_day1_reproduction.py` | `results/day1_report.json`, `results/day1_report_rerun.json` | **YES, both** | in the clone |

**Every analysis script in the repo except `tests/_verify_day1_reproduction.py`
is missing at least one required input on a fresh clone.**

---

## PART B — the cold-clone test

### B1. Clone

First attempt cloned into the session scratchpad and the `pip install` died on a
Windows long-path error inside
`torch/include/ATen/…/predicated_tile_access_iterator_residual_last.h` — an
artifact of the deep scratchpad path, not of the repo. It was discarded and
re-cloned to a short path so the result would be about the repo:

```
$ git clone C:/Projects/NSosyal C:/cctmp/ns
Cloning into 'C:/cctmp/ns'...
done.
```

Nothing was copied in by hand. The clone contains 106 tracked files; `data/`
holds only four `.gitkeep` files plus `split_seed42.json`; `checkpoints/` and
`demo_assets/` do not exist.

### B2. Fresh venv, install, test suite

```
$ python -m venv .venv
VENV OK
$ .venv/Scripts/python.exe -m pip install -r requirements.txt
Successfully installed ... numpy-2.5.2 pandas-3.0.5 pytest-9.1.1 scikit-learn-1.9.0
scipy-1.18.0 tokenizers-0.22.2 torch-2.13.0 transformers-5.15.0 gradio-6.24.0 ...
=== pip exit: 0 ===
```

Install clean on Python 3.14. Test suite:

```
$ .venv/Scripts/python.exe -m pytest tests/ -q
.......................................................................F [ 43%]
...F.................................................................... [ 86%]
......................                                                   [100%]
=========================== short test summary info ===========================
FAILED tests/test_demo.py::test_keyword_decision_delegates_to_the_frozen_matcher
FAILED tests/test_demo.py::test_examples_are_consistent_with_their_slice_tag
2 failed, 164 passed in 6.76s
=== PYTEST EXIT: 1 ===
```

**166 collected · 164 passed · 2 failed · 0 errors.** Both failures are the same
missing input:

```
    def test_keyword_decision_delegates_to_the_frozen_matcher():
        from src import lexicon
>       lex = lexicon.load_lexicon()

path = WindowsPath('C:/cctmp/ns/data/lexicon/karaliste.txt')
>       with open(path, encoding="utf-8") as f:
E       FileNotFoundError: [Errno 2] No such file or directory:
E       'C:\\cctmp\\ns\\data\\lexicon\\karaliste.txt'
src\lexicon.py:43: FileNotFoundError
```

Neither test is skip-guarded, so a new member's first `pytest` run is red.

### B3–B4. Reproducing the +0.3301 recall gap

The producer of record per `docs/RESULTS_LOG.md:15` is
`phase01_baseline.py --stage train` — a GPU training job, outside this audit's
scope. Its non-GPU entry point dies first on the corpus:

```
$ .venv/Scripts/python.exe phase01_baseline.py --stage preflight
NSosyal B* -- phase 01 (preflight)
env=local  root=C:\cctmp\ns
data=C:\cctmp\ns\data
Training file not found: C:\cctmp\ns\data\coltekin\offenseval-tr-training-v1.tsv
Raw data is gitignored -- mount/copy it, or set NSOSYAL_DATA.
[exit 1]
```

The read-only path that actually recomputes the gap is `phase09_stage1_auc.py`.
Its C9-1 provenance check recomputes `hit_recall = 317/355` and
`free_recall = 318/565` from the dump — i.e. 0.8929577 − 0.5628319 =
**0.33012588807179366** — before anything new is computed. Run in the cold clone:

```
$ .venv/Scripts/python.exe phase09_stage1_auc.py
========================================================================================
PHASE 09 STAGE 1 -- threshold-free slice comparison
pre-registration: phases/09_deeper_analysis.md C9-1..C9-11 (commit 12afa74)
========================================================================================

[C9-1] provenance
Traceback (most recent call last):
  File "C:\cctmp\ns\phase09_stage1_auc.py", line 603, in <module>
    main()
    ~~~~^^
  File "C:\cctmp\ns\phase09_stage1_auc.py", line 461, in main
    rows, got_sha, got_bytes = load_predictions(args.pred)
                               ~~~~~~~~~~~~~~~~^^^^^^^^^^^
  File "C:\cctmp\ns\phase09_stage1_auc.py", line 235, in load_predictions
    got_sha, got_bytes = sha256_of(path), path.stat().st_size
                         ~~~~~~~~~^^^^^^
  File "C:\cctmp\ns\phase09_stage1_auc.py", line 227, in sha256_of
    with open(path, "rb") as f:
         ~~~~^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory:
'results\\01_baseline_berturk\\dev_predictions.csv'
=== EXIT: 1 ===
```

**First missing input: `results/01_baseline_berturk/dev_predictions.csv`.**
Not fixed, nothing fetched from Drive, nothing copied from the working tree.

The remaining analysis entry points were run in the same clone to get the full
picture. Real stdout:

```
#### day1_gate_en.py --out <tmp>
Training file not found: C:\cctmp\ns\data\coltekin\offenseval-tr-training-v1.tsv
Raw data is gitignored -- copy it into data/coltekin/ first.                    [exit 1]

#### tests/_verify_day1_reproduction.py
OK -- 16 fields reproduce the frozen Day 1 record exactly.                      [exit 0]

#### phase08_lexical_analysis.py
  File "C:\cctmp\ns\phase08_lexical_analysis.py", line 262, in main
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
FileNotFoundError: ...\data\coltekin\offenseval-tr-training-v1.tsv              [exit 1]

#### phase03_compare.py
  File "C:\cctmp\ns\phase03_compare.py", line 56, in main
    lex = lexicon.load_lexicon()
FileNotFoundError: ...\data\lexicon\karaliste.txt                               [exit 1]

#### phase04_calibration.py
ABORT: missing prediction dump C:\cctmp\ns\results\03_defense\run_raw\dev_predictions.csv
                                                                                [exit 1]
#### phase05_paired_deltas.py
ABORT: C:\cctmp\ns\results\05_final_test\test_predictions.csv not found.
Run phase05_final_test.py first.                                                [exit 1]

#### phase09_stage1b_defense_auc.py --control ... --treatment ...
[C9-12] provenance
ABORT (C9-12): results/03_defense/run_raw/dev_predictions.csv not found. Stage 1b is
BLOCKED, not run with a substitute -- the dumps live only on the Drive mirror.  [exit 1]

#### phase03_make_augmentation.py
FileNotFoundError: ...\data\coltekin\offenseval-tr-training-v1.tsv              [exit 1]

#### demo/app.py --selftest
ABORT: asset bundle at C:\cctmp\ns\demo_assets is incomplete: ['tokenizer',
'checkpoints/raw.pt', 'checkpoints/1a1b_d.pt', 'lexicon/karaliste.txt',
'operating_point.json']
Run demo/build_assets.py once on a machine with network.                        [exit 1]

#### phase05_final_test.py --run_final_test 1 --raw_ckpt ... --defense_ckpt ...
Refusing to run: the test set is already SPENT
(C:\cctmp\ns\results\05_final_test\TEST_SET_SPENT.json).                        [exit 1]
```

Two things that worked as designed, and one worth flagging:

- **The test-set spend guard travels with the clone.** A new member on a new
  machine inherits the refusal from a tracked file, exactly as `config.py`
  intends. That mechanism is sound.
- **The C9-12 abort refuses to substitute a different dump** rather than
  silently proceeding.
- **`tests/_verify_day1_reproduction.py` passes on the cold clone but verifies
  nothing.** Its docstring says it "needs the real corpus", but it does not run
  `day1_gate_en.py` — it diffs two files that are *both tracked*
  (`day1_report.json` vs `day1_report_rerun.json`). On a clone it compares two
  committed constants and prints OK. The reproduction it appears to certify did
  not occur.

### B5. Deletion

```
$ rm -rf C:/cctmp
$ ls -d C:/cctmp
ls: cannot access 'C:/cctmp': No such file or directory
C:/cctmp DELETED — does not exist
scratchpad/coldclone DELETED — does not exist
```

Both the abandoned first clone and the working one are gone. The main working
tree is clean — `git status --short` returns nothing, and no file under
`report/` or `results/` was created, edited or deleted.

---

## PART C — documentation state

### C1. `README.md` in full

````markdown
# NSosyal B* — Turkish adversarial toxicity detection + review triage

Catches Turkish offensive content that slips past a keyword filter — because it
is orthographically obfuscated (`aptal` → `a.p.t.a.l`) or because it carries no
profanity word at all — and pairs every prediction with a calibrated confidence
that decides: auto-resolve, or send to a human reviewer.

The deliverable is **not** "a better toxicity model". It is a rigorous
comparison proving which defense actually works in Turkish, plus a triage layer
that connects model failures to human-review workload.

Full spec: [`docs/phase_briefing.md`](docs/phase_briefing.md) (what we are
building) and [`docs/claude_master_brief.md`](docs/claude_master_brief.md) (how
the work is run). Both are binding.

**Repo stays private until submission** — `src/obfuscation.py` generates
functional evasion text.

## Status

| Step | State |
|---|---|
| Day 1 — data loading + lexicon freeze + go/no-go gate | ✅ done, `results/day1_report.json` |
| Phase 0 — private GitHub remote + Colab clone | remote ✅ `MusaabAlt/nsosyal-bstar` (private, verified 404 unauthenticated); Colab clone not yet exercised |
| Phase 1 — [baseline diagnosis](phases/01_baseline_diagnosis.md) | preflight ✅ (split + sanity gate + keyword row); BERTurk training not yet run |
| Phase 2 — failure analysis + defense design | not started |
| Phase 3 — obfuscation families + cross-corpus (Mayda, Beyhan) | not started |
| Phase 4 — calibration + risk–coverage | not started |
| Phase 5 — official Çöltekin test run (once) + offline demo | not started |
| ConvBERTurk | cut; reinstated only if phase 4 finishes early |

Day 1 headline: **3,892 of 6,131 OFF tweets (63%) evade a 695-word lexicon**
even with agglutination-aware root matching.

## Layout

```
config.py        every path + constant; no script hardcodes a location
src/             source of truth — notebooks import from here, never re-implement
  data_io.py     corpus readers with the format traps guarded in code
  lexicon.py     Turkish-aware casing + literal/root lexicon matching
  obfuscation.py attack families D (train) / H (eval) + the disjointness guard
  models.py      BERTurk / ConvBERTurk wrappers                     [stub]
  calibration.py temperature scaling + risk–coverage                [stub]
  evaluate.py    one metric path shared by every system             [stub]
data/            gitignored — raw corpora live here locally only
results/         experiment JSON (committed); everything else ignored
docs/            briefings + RESULTS_LOG.md
tests/           regression tests for the confirmed format traps
demo/            offline side-by-side demo                          [stub]
```

Stubs raise `NotImplementedError` on purpose. They get written when the
corresponding step is specified, so `src/` and the execution-phase scripts stay
in sync — a plausible-looking placeholder implementation would become a second,
unverified source of truth.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
pytest tests/ -q
```

Raw data is gitignored. On a fresh checkout, place it as:

```
data/coltekin/offenseval-tr-training-v1.tsv
data/coltekin/offenseval-tr-testset-v1.tsv
data/coltekin/offenseval-tr-labela-v1.tsv     # comma-separated despite .tsv
data/lexicon/karaliste.txt                     # frozen, 695 entries
```

Reproduce the Day 1 gate:

```bash
python day1_gate_en.py --out results/day1_report_rerun.json
python tests/_verify_day1_reproduction.py      # diffs it against the frozen record
```

## Running on Kaggle / Colab

`config.py` is environment-driven — the same `src/` code runs unmodified:

```python
import os
os.environ["NSOSYAL_ENV"] = "kaggle"        # or "colab"
os.environ["NSOSYAL_DATA"] = "/kaggle/input/nsosyal-data"   # optional override
import config
```

`NSOSYAL_ROOT` overrides the repo root outright if the clone lands somewhere
unexpected. Training is a GPU job and does not run locally; PyCharm is for
writing, reviewing and version-controlling the code.

## Ground rules

These are enforced in code where possible, not left as tribal knowledge:

- **Seed 42** everywhere data is split, shuffled or a model is initialised, and
  stated in every result file.
- **Every experiment writes a step-named JSON** into `results/`. Nothing is
  silently overwritten — `day1_gate_en.py` refuses to clobber without `--force`.
- **The official Çöltekin test set is touched exactly once, at the end.**
  `data_io.load_coltekin_test()` raises `PermissionError` unless a caller passes
  `run_final_test=True`, which in practice means an explicit `--run_final_test 1`
  flag that defaults to off.
- **Training obfuscation ≠ evaluation obfuscation.** `obfuscation.assert_disjoint()`
  raises if a robustness number would be measured on an attack family the model
  was trained on. That circularity killed an earlier version of this idea.
- **The lexicon is frozen** (695 entries, sha256 in `results/day1_report.json`).
  Adding words after seeing a result is post-hoc tuning and invalidates the
  lexicon-free measurement the whole project rests on.
- **`docs/RESULTS_LOG.md` gets one entry per completed experiment** — date, what
  ran, headline numbers, interpretation, decision.
- **Commit after every completed, verified step.** Messages state the finding,
  not the action: `"Day 2: BERTurk baseline, lexicon-free gap confirmed (delta=0.09)"`.

## Data sources

| Role | Source | Note |
|---|---|---|
| Train + diagnose | Çöltekin OffensEval-2020 TR | 31,756 rows, 85/15 train/dev |
| Final test | Çöltekin official test + gold | touch once |
| Cross-corpus | [Mayda](https://github.com/imayda/turkish-hate-speech-dataset-1), [Beyhan](https://github.com/verimsu/Turkish-HS-Dataset) | never trained on; 3-way labels → `LABEL_MAP_3TO2` |
| Lexicon | [turkce-kufur-karaliste](https://github.com/ooguz/turkce-kufur-karaliste) | frozen Day 1 |

Rejected: `Overfit-GM/turkish-toxic-language` — merged (likely contains
Çöltekin → contamination) and partly pseudo-labeled.
````

The Status table is stale by nine phases: it says Phases 2–5 "not started" and
BERTurk "not yet run". Phases 01–10 are complete and recorded in
`docs/RESULTS_LOG.md`. It also lists `calibration.py`, `evaluate.py`,
`models.py` and `demo/` as `[stub]`; all four are implemented.

### C2. `README#Ground rules` — which binding rules it states, which it omits

The section is quoted verbatim above (README.md lines 98–119). Against the eight rules:

| Binding rule | README#Ground rules |
|---|---|
| **Test set spent** | **PARTIAL.** States the *policy* ("touched exactly once, at the end") and the `PermissionError` guard. Omits the *fact* that it has already been spent, omits `TEST_SET_SPENT.json`, and omits that it was opened twice. A new member reads this as a future constraint, not a closed door. |
| **Lexicon and `MIN_ROOT_LEN` frozen** | **PARTIAL.** Lexicon freeze is stated in full, with the reason. `MIN_ROOT_LEN` appears **zero times in the entire README** — and it is a frozen instrument with a recorded, quantified blind spot (Phase 08: 28/565 lexicon-free gold-OFF rows leaked). |
| **Dev-derived signals never re-enter training** | **OMITTED.** Zero occurrences in the README. This is the rule Phase 03 violated once and had corrected. |
| **Train/test obfuscation families disjoint** | **STATED**, with the enforcement point (`obfuscation.assert_disjoint()`) and the rationale. The one rule fully covered. |
| **`RESULTS_LOG` append-only** | **OMITTED.** README says "gets one entry per completed experiment" — the write cadence, not the immutability. "append-only" appears zero times. The rule exists in `docs/RESULTS_LOG.md` lines 8–9 and `handoff_2026_08_15.md` §5.4, neither of which the README points to for this. |
| **Every number traces to a recorded run** | **OMITTED as stated.** README covers the write side ("every experiment writes a step-named JSON") but never the read side — that a figure not in the record must be flagged, not written, and never reconstructed from memory. |
| **Per-slice macro-F1 never reported** | **OMITTED.** "macro-F1" appears zero times in the README. This is a pre-registered constraint in `phases/01_baseline_diagnosis.md`. |
| **Repo stays private** | **OMITTED from Ground rules**, though stated twice elsewhere in the README (line 16, and the Phase 0 status row). |

The section additionally states two rules not on the list: **seed 42 everywhere**,
and **commit after every completed, verified step**.

**Score: 1 of 8 fully stated, 2 partial, 5 omitted.** The complete set of eight
lives only in `docs/handoff_2026_08_15.md` §5 — a file the README does not link to.

### C3. Heading trees and word counts of the two handoff documents

#### `docs/HANDOFF.md` — 130 lines · **860 words** · 6,273 bytes

```
# Handoff — paste this at the start of a new chat        (1)
├── ## Read first — both are binding                     (12)
├── ## Environment                                       (24)
├── ## What already exists and is verified               (38)
├── ## Repo layout and current state                     (54)
├── ## Guards that are already code, not tribal knowledge (81)
├── ## Data on disk                                      (95)
├── ## One known quirk, deliberately preserved           (106)
├── ## Next step                                         (115)
└── ## Deadlines                                         (128)
```

Highest phase mentioned: **Phase 01**, once, at line 6 — "Phase 01 preflight is
done; BERTurk has not been trained." Nothing after 05, and nothing after 01.

**STALE, and stale in ways that actively mislead.** Its own banner marks it
"Partly superseded (15 Aug 2026)", but it still asserts: the repo is "local-only
— no GitHub remote yet" (there is one, `origin`); "one commit: `c33d1bd`" (there
are 48); `calibration.py STUB`, `demo/app.py STUB` (both implemented); "the
modeling phase has not started" (all ten phases are complete). It is the file
whose title tells a new member to paste it at the start of a new chat.

#### `docs/handoff_2026_08_15.md` — 206 lines · **1,670 words** · 11,266 bytes

```
# NSosyal B* — continuation brief                        (1)
├── ## 1. Where the project is                           (15)
├── ## 2. The committed framing — read this before drafting anything (43)
├── ## 3. Headline numbers                               (75)
├── ## 4. The four gap rulings                           (116)
├── ## 5. Binding rules that survive this chat change    (130)
├── ## 6. What remains                                   (157)
├── ## 7. Scope note — read before proposing more work   (176)
└── ## 8. Working practices worth knowing                (190)
```

Phase tokens: **Phase 3 (×2), Phase 4 (×1)** — highest numbered mention is 4. It
covers Phase 05 substantively without numbering it ("the official test set is
spent and guarded", §5.1). §1 states "All six measurement phases are **complete**."

**Mentions nothing after 05.** No Phase 06 (demo), 07 (report outline), 08
(lexical analysis / `MIN_ROOT_LEN` blind spot), 09 Stage 1 or Stage 1b (the
ROC-AUC work that *narrowed the central claim*), or 10 (KYS şablon mapping).
**STALE.** It is authoritative for the rules in §5 and wrong about the project's
position: §6 lists Sections 4 and 5 of the report as unwritten, both now exist
under `report/`; §1 says the report is the only remaining deliverable, three
measurement phases have run since.

Neither handoff is current. The most recent of the two is three days old and
predates the phase that changed what the headline claim means.

### C4. Is there a file that indexes the phases and says what each produced?

**Yes — `docs/PROJECT_HISTORY.md` §3 "Chronology" (line 62 onward).** 45,698 bytes,
tracked. One subsection per phase, each stating the question, the pre-registration
commit, the numbers produced and the result commit:

```
### Day 1 reproduction check — 2026-08-15          (64)
### Phase 01 — baseline diagnosis                  (70)
### Phase 02 — failure analysis (read-only)        (122)
### Phase 03 — the defense                         (183)
### Phase 04 — calibration and risk–coverage       (248)
### Phase 05 — the official test set, single pass  (304)
### Phase 06 — offline demo                        (352)
### Phase 07 — technical report                    (366)
### Phase 08 — word-level lexical dependence       (378)
### Phase 09 Stage 1 — threshold-free slice comparison (455)
### Phase 09 Stage 1b — ranking or placement?      (501)
```

It also carries §4 "Pre-registration index", §5 "Corrections and supersessions",
§6 "Interpretations later proven wrong", and §7 "What is still open".

Two gaps: **Phase 10 (`phases/10_sablon_mapping.md`, the KYS coverage map) is
absent** — "Phase 10", "şablon" and "sablon" all return zero hits. And nothing in
the README, in either handoff, or in `CLAUDE.md` points a new member at
`PROJECT_HISTORY.md`; it is discoverable only by listing `docs/`.

---

## PART D — collaboration mechanics

### D1. Branch protection, CONTRIBUTING, PR templates, CI

| Item | State |
|---|---|
| `.github/` directory | **DOES NOT EXIST** |
| CI workflow (any `.yml`/`.yaml`) | **DOES NOT EXIST** — `git ls-files` matches zero YAML files anywhere in the repo |
| `CONTRIBUTING*` | **DOES NOT EXIST** |
| PR template / issue template | **DOES NOT EXIST** |
| `CODEOWNERS` | **DOES NOT EXIST** |
| `.pre-commit-config.yaml` | **DOES NOT EXIST** |
| Makefile / tox / nox | **DOES NOT EXIST** |
| Local git hooks | none beyond the `.sample` defaults |
| Branches | one: `master` (plus `remotes/origin/master`) |
| Remote | one: `origin` → `https://github.com/MusaabAlt/nsosyal-bstar.git` |
| Branch protection | **not verifiable from here** — `gh` CLI is not installed on this machine, so the GitHub API was not queried. What the repo shows: a single branch, no CI to require as a status check, and no CODEOWNERS to require as a reviewer. |

The 166-test suite exists and is meaningful, and nothing runs it automatically.
`docs/HANDOFF.md` names PyCharm as the review surface; review is a human habit
here, not a gate.

### D2. `docs/RESULTS_LOG.md` structure

- **Line count: 46.**
- Lines 1–9: title and the append-only preamble. Line 10 blank.
- Line 11: table header. Line 12: separator.
- Lines 13–46: table body, 34 rows.
- **The table body ends at line 46, which is the last line of the file.** The file
  ends `... proposed (C9-17). |\r\n` with no trailing content.

**Appends land at end-of-file, and it is conflict-prone for multiple writers.**
Every new entry is a single very long line appended at EOF, and every writer's
insertion point is the identical byte offset at the identical line number. Two
people logging experiments on the same day produce a guaranteed same-line
conflict in `git merge`, on lines several thousand characters wide — the hardest
possible shape to resolve by hand. The append-only rule (lines 8–9) makes it
worse rather than better: neither side may rewrite the other's row, so the
resolution must preserve both, in an order neither writer chose.

### D3. What imports `src/obfuscation.py`

Two files, repo-wide:

| Importer | Line | What it does with it |
|---|---|---|
| `phase03_train_defense.py` | 43 | `from src import augment, data_io, evaluate, lexicon, obfuscation` — calls `assert_disjoint()` at line 75 (training augmentation) and line 213 (H-perturbed dev eval), and `apply_family()` at lines 83 (D) and 217 (H) |
| `tests/test_data_io.py` | 11 | `from src import data_io, lexicon, obfuscation` — asserts `assert_disjoint` raises on D/D (line 185) and returns True on D/H (line 189) |

The module has no `__main__` block and no CLI. It is not imported by
`src/__init__.py`, by any other `src/` module, or by any other phase script.

**Is it reachable from anything a new researcher would run?** Split answer:

- **Through the test suite: yes, and it runs on a cold clone.**
  `tests/test_data_io.py` is collected by `pytest tests/ -q` and both
  `assert_disjoint` tests passed in the clone — they need no corpus, no lexicon,
  no predictions. The disjointness guard is the one project invariant a new
  member can actually exercise on day one.
- **Through the analysis path: no.** Its only non-test caller is
  `phase03_train_defense.py`, which requires the Çöltekin corpus,
  `karaliste.txt`, and either a GPU or a Drive checkpoint — none present in a
  clone. `apply_family()`, the code that generates functional evasion text and
  is the stated reason the repo is private, is unreachable from any script a new
  member can successfully run.

---

## WHAT A NEW MEMBER CANNOT DO

From Part B's real result. Everything below was attempted in the cold clone and
failed there.

| Analysis | Missing |
|---|---|
| **Reproduce the headline +0.3301 lexicon-free/lexicon-hit recall gap** (Phase 09 Stage 1, `phase09_stage1_auc.py`) | `results/01_baseline_berturk/dev_predictions.csv` (736,591 B, sha256 `a2f5bddf…`) — the C9-1 provenance check dies on it before any computation. Then also `data/lexicon/karaliste.txt` for the C9-10 suspect-root sensitivity. |
| **Re-derive the baseline from scratch** (`phase01_baseline.py --stage train`, the producer of record) | `data/coltekin/offenseval-tr-training-v1.tsv` (4,101,728 B), `data/lexicon/karaliste.txt` (5,988 B), and a CUDA GPU. `--stage preflight` already fails on the corpus. |
| **Re-run the Day 1 go/no-go gate** (`day1_gate_en.py` — the one reproduction the README instructs a new member to perform) | the training TSV and `karaliste.txt`. Note `tests/_verify_day1_reproduction.py` prints `OK -- 16 fields reproduce` on a cold clone anyway, because it diffs two committed JSON files and never invokes the gate. |
| **Phase 08 word-level lexical dependence** (`phase08_lexical_analysis.py`) | the training TSV; then `karaliste.txt`. |
| **Phase 03 four-variant defense comparison** (`phase03_compare.py`) | `karaliste.txt`, then all four of `results/03_defense/run_{raw,1a,1a1b,1a1b_d}/dev_predictions.csv` — **Drive mirror only; absent from the main working tree as well as from any clone.** |
| **Phase 04 calibration / risk–coverage** (`phase04_calibration.py`) | `results/03_defense/run_raw/dev_predictions.csv` and `run_1a1b_d/dev_predictions.csv` — Drive only. |
| **Phase 09 Stage 1b defense AUC** (`phase09_stage1b_defense_auc.py`) | the same two dumps. The C9-12 guard aborts by design rather than substituting. |
| **Phase 05 paired deltas on the test set** (`phase05_paired_deltas.py`) | `results/05_final_test/test_predictions.csv` — Drive only. |
| **Any re-measurement on the official test set** (`phase05_final_test.py`) | test + gold TSVs and two `.pt` checkpoints — *and* it is refused outright by the tracked `TEST_SET_SPENT.json`. This one is intentional and works correctly on a clone. |
| **Run the offline demo** (`demo/app.py`) | the whole `demo_assets/` bundle — 885.9 MB: `tokenizer`, `checkpoints/raw.pt`, `checkpoints/1a1b_d.pt`, `lexicon/karaliste.txt`, `operating_point.json`. Rebuilding it via `build_assets.py` needs the two checkpoints and network. |
| **Retrain anything** (`phase03_train_defense.py`, `phase03_train_errors.py`) | corpus, lexicon, GPU; `--load_checkpoint` needs `best.pt`, which is gitignored and not in the working tree either. |
| **Get a green test run** | `data/lexicon/karaliste.txt`. 164/166 pass; the 2 failures in `tests/test_demo.py` are unguarded `FileNotFoundError`s on the lexicon. |
| **Convert the Phase 08 `MIN_ROOT_LEN` *bound* (+0.3529) into a measurement** | `dev_predictions.csv` for the per-row outcome of the 28 leaked rows — the follow-up `RESULTS_LOG.md:38` explicitly names as available to the lead. |
| **Exercise `src/obfuscation.apply_family()`** — the evasion generator the repo is private for | reachable only from `phase03_train_defense.py`, which cannot run. Only `assert_disjoint()` is exercisable, via the test suite. |

**What a new member *can* do from a fresh clone:** read every tracked
`findings.md`, `metrics.json`, `phases/*.md` pre-registration and the four
`report/` sections; run 164 of 166 tests; and confirm the test-set spend guard
refuses. They can read every recorded number. They cannot recompute a single one.

The binding constraint is two files. `data/lexicon/karaliste.txt` (5,988 bytes)
blocks the test suite and every lexicon-touching script. `dev_predictions.csv`
(736,591 bytes) blocks the entire Phase 09 line of analysis. Both exist in the
working tree this audit ran from. Neither is in the clone, and the repo contains
no instruction, script, or manifest that tells a new member where to obtain them
beyond prose in `phases/09_deeper_analysis.md` naming the Drive mirror.

*No fixes proposed.*
