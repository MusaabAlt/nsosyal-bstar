# NSosyal B* — PyCharm Project Setup Prompt

> Paste this into PyCharm's AI Assistant / Junie to have it scaffold the
> project, OR follow it manually as a setup checklist. Either way, treat
> Section 3 (standards) as permanent project rules, not one-time setup.

---

## 1. What this project is (context for the assistant)

A Turkish content-moderation research/engineering project: train and compare
baseline vs defended toxicity classifiers on obfuscated and lexicon-free
Turkish offensive text, calibrate a confidence-based human-review triage
layer, and produce a reproducible offline demo + results log for a technical
report. Full specification lives in `docs/claude_master_brief.md` and
`docs/phase_briefing.md` (copy the two files already prepared into `docs/`
as the first setup step).

Training runs on **Colab Pro+**, not locally — PyCharm is for writing,
reviewing, and version-controlling code, not for running BERT fine-tuning.

---

## 2. Project structure to create

```
nsosyal-bstar/
├── .gitignore
├── README.md
├── requirements.txt
├── config.py
├── docs/
│   ├── claude_master_brief.md
│   ├── phase_briefing.md
│   └── RESULTS_LOG.md
├── data/                      # gitignored — raw files live here locally only
│   ├── coltekin/
│   ├── mayda/
│   ├── beyhan/
│   └── lexicon/
├── src/
│   ├── __init__.py
│   ├── data_io.py             # TSV/CSV readers with the known format traps handled
│   ├── lexicon.py             # Turkish-aware lowercasing, literal/root matching
│   ├── obfuscation.py         # design-set (D) and held-out (H) attack families
│   ├── models.py               # BERTurk / ConvBERTurk loading + training wrappers
│   ├── calibration.py          # temperature scaling, risk-coverage curve
│   └── evaluate.py             # unified metric computation across all systems
├── notebooks/
│   ├── day2_train_diagnose.ipynb   # Colab Pro+ entry point, mirrors src/
│   ├── day3_defense.ipynb
│   └── day5_crosscorpus.ipynb
├── results/                    # gitignored except summary JSON/CSV + this log
│   └── (day*_report.json files land here)
├── demo/
│   └── app.py                  # local Gradio/Streamlit demo, offline only
└── tests/
    └── test_data_io.py         # sanity checks for the known parsing traps
```

---

## 3. Engineering standards (permanent, not just for setup)

- **`src/` is the source of truth.** Notebooks import from `src/`, they do
  not duplicate logic — a Colab notebook that reimplements `data_io.py`
  inline instead of importing it is a bug to fix, not a shortcut to accept.
- **No hardcoded paths.** All file locations go through `config.py`, which
  reads from environment variables so the same code runs unmodified on a
  local machine or in Colab (`/content/drive/...`).
- **Every experiment writes a JSON result file into `results/`**, named with
  the step and never silently overwritten (`day2_bertturk_v1.json`, not a
  generic `result.json` that a rerun clobbers).
- **Fixed seed = 42** everywhere data is split, shuffled, or a model is
  initialized. State it in every result file.
- **Known format traps must have explicit guards in `data_io.py`, not
  tribal knowledge:**
  - Çöltekin training TSV: no quoting, newlines replaced with three spaces —
    read line-by-line, split on `\t` manually.
  - Çöltekin gold label file: `.tsv` extension, comma-separated content.
  - Turkish casing: map `I→ı`, `İ→i` before `.lower()` anywhere text is
    matched against the lexicon.
  - Mayda/Beyhan: 3-way labels — the mapping to binary OFF/NOT must be a
    named constant in code (e.g. `LABEL_MAP_3TO2`), not an inline decision
    buried in a script.
- **Anti-circularity guards are code, not comments.** Any script that could
  touch the official Çöltekin test set must require an explicit flag (e.g.
  `--run_final_test 1`) defaulting to off, exactly as already established.
  Any script testing obfuscation robustness must assert that the attack
  family used for evaluation is disjoint from the one used for training
  augmentation — fail loudly if not.
- **`docs/RESULTS_LOG.md` gets one entry per completed experiment**: date,
  what ran, headline numbers, interpretation, decision made. This is what
  the technical report's methodology section will be drafted from — write
  it like an engineering log, not a chat message.
- **Git discipline:** commit after every completed, verified step (not
  after every file edit). Commit messages state the finding, not just the
  action — `"Day 2: BERTurk baseline, lexicon-free gap confirmed (delta=0.09)"`,
  not `"update script"`.
- Repo stays **private** on GitHub — the obfuscation-generation code is a
  functional evasion tool and should not be public before submission.

---

## 4. requirements.txt (starting point)

```
transformers>=4.40
datasets>=2.19
torch>=2.2
scikit-learn>=1.4
numpy>=1.26
pandas>=2.2
gradio>=4.30
python-dotenv>=1.0
```

---

## 5. config.py (starting point)

```python
import os
from pathlib import Path

# Set NSOSYAL_ENV=colab in Colab's first cell before importing config
ENV = os.getenv("NSOSYAL_ENV", "local")

if ENV == "colab":
    ROOT = Path("/content/nsosyal-bstar")
else:
    ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
LEXICON_PATH = DATA_DIR / "lexicon" / "karaliste.txt"
COLTEKIN_TRAIN = DATA_DIR / "coltekin" / "offenseval-tr-training-v1.tsv"
COLTEKIN_TEST = DATA_DIR / "coltekin" / "offenseval-tr-testset-v1.tsv"
COLTEKIN_GOLD = DATA_DIR / "coltekin" / "offenseval-tr-labela-v1.tsv"

SEED = 42
MAX_LEN = 128

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
```

---

## 6. Colab Pro+ entry-cell pattern (put this at the top of every notebook)

```python
import os
os.environ["NSOSYAL_ENV"] = "colab"

!git clone https://github.com/<username>/nsosyal-bstar.git /content/nsosyal-bstar
%cd /content/nsosyal-bstar
!pip install -q -r requirements.txt

# raw data is gitignored -- pull it from Drive before running
from google.colab import drive
drive.mount('/content/drive')
# then copy/symlink the needed files from Drive into data/ before running

import sys
sys.path.insert(0, "/content/nsosyal-bstar")
from src import data_io, lexicon, models, evaluate
```

After a run, push results back:
```python
!git add results/ docs/RESULTS_LOG.md
!git commit -m "Day X: <one-line finding>"
!git push
```

---

## 7. First setup task for the assistant

1. Create the structure in Section 2.
2. Copy the two provided briefing files into `docs/`.
3. Populate `requirements.txt` and `config.py` as above.
4. Create `docs/RESULTS_LOG.md` with a single header row and nothing else —
   it gets filled in as real experiments run, not pre-written.
5. Move the already-written `day1_gate_en.py` logic into `src/lexicon.py`
   and `src/data_io.py` (split by responsibility: reading vs matching) and
   write `tests/test_data_io.py` covering the two confirmed format traps
   (unquoted TSV with embedded triple-space newlines; comma-separated gold
   file). Do not rewrite the matching logic from scratch — port the
   already-verified functions.
6. Do not create `src/models.py`, `src/obfuscation.py`, or the notebooks yet
   with invented training code — those get written when the Claude chat
   provides the exact Day 2 script, so the two stay in sync. Stub them with
   a docstring and `raise NotImplementedError` only.
7. `git init`, first commit: `"Project scaffold + ported Day 1 lexicon logic"`.
