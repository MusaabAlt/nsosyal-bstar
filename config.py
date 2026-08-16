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
