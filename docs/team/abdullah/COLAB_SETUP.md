# Colab setup for m3_encoder

Adapted from the study's runbook, `diagnosis/notebooks/colab_phase01_runbook.md`,
which stays the reference for the diagnosis phases. This file covers m3 only.
Paths match the repository after the restructure: the study lives in
`diagnosis/`, the moderation system in `AI/`.

A Colab session is disposable. Everything under `/content` is lost when the
session disconnects. Only Drive survives.

---

## Prerequisites (once, outside the notebook)

**Drive layout.** Musaab provides the data (links in [RESOURCES.md](RESOURCES.md)).
Put it in your own Drive exactly like this. This is the layout the study
runbook uses:

```
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-training-v1.tsv
MyDrive/nsosyal-bstar/data/lexicon/karaliste.txt
MyDrive/nsosyal-bstar/checkpoints/01_baseline_berturk/best.pt     <- frozen baseline, epoch 1
```

- Do **not** put the test set or gold file on the Drive you mount. Nothing you
  run needs them, and the rule in RESOURCES.md is that you never touch them.
- `diagnosis/config.py` finds the data because `NSOSYAL_DATA` is set to
  `MyDrive/nsosyal-bstar/data` in the setup cell below. With `NSOSYAL_DATA` set,
  `config.COLTEKIN_TRAIN` resolves to `<that>/coltekin/offenseval-tr-training-v1.tsv`
  and `config.LEXICON_PATH` to `<that>/lexicon/karaliste.txt`.

**`GH_TOKEN`.**
- The study runbook clones with a fine-grained personal access token stored in
  Colab Secrets (🔑 sidebar) as `GH_TOKEN`, with read-only Contents access to
  this repository only.
- Whether the repo is still private is open (RESOURCES.md, open item 9). If it
  is public, the clone works without the token.
- The "Notebook access" toggle is **per notebook**: switch it on for every new
  notebook.
- Never paste the token into a cell.

**Runtime.** Runtime → Change runtime type → GPU.

---

## Cell 1 — mount Drive and clone

```python
from google.colab import drive, userdata
import os, shutil, subprocess
drive.mount('/content/drive')            # click the popup within 120 s
DRIVE, REPO = '/content/drive/MyDrive/nsosyal-bstar', '/content/nsosyal-bstar'
assert os.path.isdir(DRIVE), f"{DRIVE} not found - set up the Drive layout first"

shutil.rmtree(REPO, ignore_errors=True)
token = userdata.get('GH_TOKEN')
subprocess.run(['git', 'clone', '--quiet',
                f'https://{token}@github.com/MusaabAlt/nsosyal-bstar.git', REPO], check=True)
print(subprocess.run(['git', '-C', REPO, 'log', '--oneline', '-1'],
                     capture_output=True, text=True).stdout)
```

The clone has two top-level folders you use:
- `REPO/AI/`: m3's code and tests. The unit tests, the evals and `scripts/check.sh` run from here.
- `REPO/diagnosis/`: `config.py`, `src/data_io.py`, the frozen split and the test-set lock.

After the restructure, always `cd` into one of these two, never the repo root:

```python
%cd /content/nsosyal-bstar/AI
```

---

## Cell 2 — install the pinned environment

**The pins exist for comparability, not caution.** The frozen baseline was
produced with torch 2.11.0+cu128, transformers 5.15.0 and scikit-learn 1.6.1
(`diagnosis/results/01_baseline_berturk/run_config.json` → `environment`). If
your numbers come from a different stack, the difference between m3 and the
baseline includes library differences nobody can separate out afterwards.

```python
import sys, subprocess
assert (3, 11) <= sys.version_info[:2] <= (3, 13), (
    f"Python {sys.version.split()[0]}: scikit-learn 1.6.1 has no wheel for it. "
    "Stop and tell Musaab (RESOURCES.md, open item 8).")
pip = [sys.executable, '-m', 'pip', 'install', '-q']
# torch first, from the CUDA 12.8 index, so the +cu128 build is the one installed
subprocess.run(pip + ['torch==2.11.0+cu128', '--index-url', 'https://download.pytorch.org/whl/cu128'], check=True)
subprocess.run(pip + ['-r', '/content/nsosyal-bstar/AI/requirements.txt'], check=True)
subprocess.run(pip + ['-r', '/content/nsosyal-bstar/AI/modules/m1_lexicon/requirements.txt'], check=True)  # terlik; check 7 runs m1's tests
subprocess.run(pip + ['-r', '/content/nsosyal-bstar/AI/modules/m3_encoder/requirements.txt'], check=True)
print("installed - now Runtime -> Restart session, then run cell 3")
```

- **Restart the session** (Runtime → Restart session) after this cell. Colab
  imports its own torch at startup, and the pinned build takes effect only in a
  fresh interpreter.
- A restart keeps `/content` and the Drive mount. A *disconnect* loses both, and
  then you start again from cell 1.
- Every torch, transformers and scikit-learn wheel named above was checked on
  its package index on 2026-09-15.

---

## Checkpoints go to Drive, never to session disk

**Rule: every checkpoint m3 writes goes to Drive, under
`MyDrive/nsosyal-bstar/checkpoints/m3_encoder/`, never under `/content`.**

- Colab disconnects without warning, and a BERTurk fine-tune on 26,992 rows
  runs for a long time.
- A checkpoint in `/content` dies with the session, and so does every hour of
  training behind it.
- Write the checkpoint at the end of every epoch, including the optimizer,
  scheduler and RNG state, so a dropped session resumes instead of restarting.
  The study's loop in `diagnosis/src/models.py` does exactly this.
- Checkpoints are never committed to git (`*.pt` is ignored).

The smoke cell creates that folder and proves it is writable before anything
trains.

---

## Cell 3 — smoke test (run after the restart, before any training)

This cell checks everything and trains nothing. Every check stops at the first
failure. If it doesn't finish with `SMOKE PASS`, do not start a training run.

```python
# =========================================================================
# m3_encoder smoke - proves the environment is correct. Never trains.
# =========================================================================
import os, sys, json, hashlib, subprocess, textwrap

DRIVE = '/content/drive/MyDrive/nsosyal-bstar'
REPO = '/content/nsosyal-bstar'
BASELINE_CKPT = f'{DRIVE}/checkpoints/01_baseline_berturk/best.pt'
M3_CKPT_DIR = f'{DRIVE}/checkpoints/m3_encoder'

def die(msg):
    raise SystemExit("ABORT: " + textwrap.dedent(msg).strip())

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

# --- 1. Python, pinned versions, GPU ---------------------------------------
if not (3, 11) <= sys.version_info[:2] <= (3, 13):
    die(f"Python {sys.version.split()[0]} is outside 3.11-3.13 (scikit-learn 1.6.1 wheels).")
import torch, transformers, sklearn
PINS = {'torch': '2.11.0+cu128', 'transformers': '5.15.0', 'scikit-learn': '1.6.1'}
now = {'torch': torch.__version__, 'transformers': transformers.__version__,
       'scikit-learn': sklearn.__version__}
for k, want in PINS.items():
    print(f"  {'OK  ' if now[k] == want else 'DIFF'} {k:<13} pinned={want:<13} now={now[k]}")
if now != PINS:
    die("""Versions differ from the frozen baseline's environment.
           Re-run cell 2, then Runtime -> Restart session. Numbers from another
           stack are not comparable to the baseline.""")
if not torch.cuda.is_available():
    die("No GPU. Runtime -> Change runtime type -> GPU.")
print("  device       :", torch.cuda.get_device_name(0))
print("[PASS] 1 - Python, pins, GPU\n")

# --- 2. inputs on Drive are the exact bytes the baseline used ---------------
EXPECT = {
    f'{DRIVE}/data/coltekin/offenseval-tr-training-v1.tsv':
        '8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa',
    f'{DRIVE}/data/lexicon/karaliste.txt':
        '0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b',
    BASELINE_CKPT:
        '43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca',
}
for path, want in EXPECT.items():
    if not os.path.isfile(path):
        die(f"missing: {path} - see the Drive layout in COLAB_SETUP.md")
    got = sha256(path)
    print(f"  {'OK  ' if got == want else 'MISMATCH'} {os.path.basename(path):<34} {got[:16]}")
    if got != want:
        die(f"{path}\n got      {got}\n expected {want}\nNot the frozen bytes. Do not continue.")
print("[PASS] 2 - corpus, lexicon, baseline checkpoint verified\n")

# --- 3. config resolves to Drive; the frozen split is LOADED, not created ----
os.environ['NSOSYAL_ENV'] = 'colab'
os.environ['NSOSYAL_ROOT'] = f'{REPO}/diagnosis'
os.environ['NSOSYAL_DATA'] = f'{DRIVE}/data'
os.environ['NSOSYAL_CKPT'] = f'{DRIVE}/checkpoints'
sys.path.insert(0, f'{REPO}/diagnosis')
import config
from src import data_io
SPLIT = config.SPLITS_DIR / 'split_seed42.json'
if subprocess.run(['git', '-C', REPO, 'ls-files', '--error-unmatch', str(SPLIT)],
                  capture_output=True).returncode != 0:
    die(f"{SPLIT} is not a tracked file - the frozen split did not come with the clone.")
rows = data_io.load_coltekin_train()
train_rows, dev_rows, meta = data_io.get_split(rows, SPLIT, data_io.sha256(config.COLTEKIN_TRAIN))
print(f"  corpus       : {len(rows):,} rows")
print(f"  train / dev  : {len(train_rows):,} / {len(dev_rows):,}")
print(f"  fingerprint  : {meta['dev_fingerprint']}")
if not meta['reused_existing_file']:
    die("The split was CREATED, not loaded. This session is not on the frozen split.")
if (len(rows), len(train_rows), len(dev_rows)) != (31756, 26992, 4764):
    die("Row counts differ from the frozen split (31,756 / 26,992 / 4,764).")
if meta['dev_fingerprint'] != '034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4':
    die("Dev fingerprint differs from 034415af... - every baseline number was measured on that set.")
print("[PASS] 3 - frozen split loaded\n")

# --- 4. the test-set lock is armed -------------------------------------------
# The spent record must exist BEFORE the flagged call below: with the record in
# place load_coltekin_test raises before it opens or logs anything.
if not config.TEST_SPEND_RECORD.exists():
    die(f"{config.TEST_SPEND_RECORD} is missing. The lock is gone - stop and tell Musaab.")
for kwargs, expect in (({}, 'Refusing to load'),
                       ({'run_final_test': True}, 'already been SPENT')):
    try:
        data_io.load_coltekin_test(**kwargs)
        die("load_coltekin_test did NOT refuse. Stop and tell Musaab.")
    except PermissionError as e:
        if expect not in str(e):
            die(f"Unexpected refusal text: {e}")
        print(f"  refused {str(kwargs) or '{}':<26} -> {expect!r}")
print("[PASS] 4 - test set locked (spent)\n")

# --- 5. the frozen baseline is epoch 1 and loads ------------------------------
blob = torch.load(BASELINE_CKPT, map_location='cpu', weights_only=False)
if sorted(blob) != ['dev_macro_f1', 'epoch', 'model']:
    die(f"Unexpected checkpoint keys {sorted(blob)} - not the phase 01 best.pt.")
print(f"  epoch (0-idx): {blob['epoch']}   dev_macro_f1: {blob['dev_macro_f1']!r}")
if blob['epoch'] != 0 or blob['dev_macro_f1'] != 0.8270752670616224:
    die("Not the epoch-1 baseline.")
del blob
print("[PASS] 5 - baseline checkpoint is epoch 1\n")

# --- 6. checkpoint folder on Drive is writable --------------------------------
os.makedirs(M3_CKPT_DIR, exist_ok=True)
probe = os.path.join(M3_CKPT_DIR, '.write_probe')
with open(probe, 'w') as f:
    f.write('ok')
os.remove(probe)
print(f"  m3 checkpoints -> {M3_CKPT_DIR} (writable)")
print("[PASS] 6 - Drive checkpoint folder writable\n")

# --- 7. the AI/ suite is green in this environment ----------------------------
for cmd in (['-m', 'unittest', 'discover', '-p', 'test_*.py'],
            ['-m', 'pipeline.run', 'Bu bir test cumlesi', '--compact']):
    r = subprocess.run([sys.executable, *cmd], cwd=f'{REPO}/AI', capture_output=True, text=True)
    print(f"  {' '.join(cmd[:2]):<22} exit {r.returncode}")
    if r.returncode != 0:
        die(f"{' '.join(cmd)} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
print("[PASS] 7 - AI/ tests and pipeline smoke\n")
print("=" * 70)
print("SMOKE PASS - environment verified, nothing trained")
```

Expected output on a good session:
- `[PASS] 1` through `[PASS] 7`
- `train / dev  : 26,992 / 4,764`
- `fingerprint  : 034415af3a23b388…`
- `epoch (0-idx): 0   dev_macro_f1: 0.8270752670616224`

Before this file was committed, checks 2–7 were run on Musaab's Windows machine
against a local folder laid out like the Drive above, and all passed. Check 1
(Colab's GPU and the pinned versions) can only pass on Colab and has not been
run there yet.

---

## Known failures (from the study runbook)

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: mount failed` | OAuth popup not clicked within 120 s | re-run cell 1, click promptly |
| `userdata...TimeoutException` / `SecretNotFoundError` for `GH_TOKEN` | Notebook access is per notebook and starts off | toggle it in the 🔑 sidebar, keep the tab focused |
| Training ~20x slower than expected | CPU runtime | change runtime type; a `+cpu` torch never passes check 1 |
| Check 1 says `DIFF` right after cell 2 | session not restarted | Runtime → Restart session, run cell 3 again |
| Check 2 `MISMATCH` | a different file uploaded to Drive | re-download from the link in RESOURCES.md; never edit the expected hash |

The study measured a T4 at roughly 3x slower than an L4 (study runbook, §4).
Check which GPU cell 3 reports, and don't raise the batch size to make up for
it. That changes the optimisation setup and breaks comparability.
