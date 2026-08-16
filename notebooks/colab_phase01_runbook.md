# Colab runbook — session rebuild + phase run cells

A Colab session is disposable and `/content` dies with it. This file exists so
rebuilding a working notebook from an empty one is **one paste**, not seven
guesses. Section 1 is that paste. Section 2 is the same seven cells split apart
with their expected stdout, for when one of them fails and you need to know
which. Section 3 is the per-phase run cells. Section 4 is the hardware note.

Nothing here hardcodes a path into the repo — `config.py` reads the environment
variables set in cell 5.

---

## Prerequisites (do these once, outside the notebook)

**Drive layout.** The raw corpora and the lexicon live on Drive, never in the
clone (they are gitignored and too large to travel with it):

```
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-training-v1.tsv
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-testset-v1.tsv     <- present, never read before phase 05
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-labela-v1.tsv      <- present, never read before phase 05
MyDrive/nsosyal-bstar/data/lexicon/karaliste.txt
```

**`GH_TOKEN`.** The repo is private because `src/obfuscation.py` generates
functional evasion text. Store a **fine-grained PAT** in Colab Secrets
(🔑 sidebar) as `GH_TOKEN`, with **Repository access: only `nsosyal-bstar`** and
**Permissions → Repository → Contents: Read-only**. Nothing more is needed —
the clone is read-only and results are committed from the local machine.
Toggle **Notebook access** on for the secret, or `userdata.get` raises.

Do not paste the token into a cell.

---

## Section 1 — one-paste rebuild

Paste this into a single cell of an empty notebook on a **GPU runtime** and run
it. It performs all seven checks in order and stops at the first failure, so a
green run means the session is genuinely ready.

Two points where it will pause for you: Drive's OAuth popup (cell 2 — **click
it within 120 s or the mount raises `ValueError: mount failed`**), and the pip
install in cell 5.

```python
# =========================================================================
# NSosyal B* — full session rebuild.  Stops at the first failed check.
# =========================================================================
import os, sys, json, hashlib, platform, shutil, subprocess, textwrap

def die(msg):
    raise SystemExit("ABORT: " + textwrap.dedent(msg).strip())

# --- 1. runtime probe ----------------------------------------------------
import torch
print("python      :", platform.python_version())
print("torch       :", torch.__version__, "| cuda build:", torch.version.cuda)
if "+cpu" in torch.__version__:
    die("""torch is a +cpu wheel, so this is a CPU runtime.
           Runtime -> Change runtime type -> GPU, then Restart session.
           Nothing in this repo installs torch; pip-installing it is NOT the fix.""")
if not torch.cuda.is_available():
    die("torch.cuda.is_available() is False -- no GPU attached to this runtime.")
GPU = torch.cuda.get_device_name(0)
print("device      :", GPU,
      "|", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1), "GB")
if "T4" in GPU:
    print("[NOTE] T4: budget ~3x the L4 wall-clock. See section 4 of the runbook.")
print("[PASS] 1 - trainable GPU runtime\n")

# --- 2. mount Drive ------------------------------------------------------
from google.colab import drive
drive.mount('/content/drive')            # <- click the popup within 120 s
DRIVE, REPO = '/content/drive/MyDrive/nsosyal-bstar', '/content/nsosyal-bstar'
if not os.path.isdir(DRIVE):
    die(f"{DRIVE} not found. The corpora and lexicon live there; nothing can be verified without it.")
print("[PASS] 2 - Drive mounted at", DRIVE, "\n")

# --- 3. prerequisites BEFORE anything else -------------------------------
from google.colab import userdata
try:
    TOKEN = userdata.get('GH_TOKEN')
except Exception as e:
    die(f"""GH_TOKEN did not resolve ({type(e).__name__}).
            Colab Secrets -> GH_TOKEN must exist AND have 'Notebook access' toggled on.""")
if not TOKEN:
    die("GH_TOKEN resolved to an empty value.")
print("GH_TOKEN    : resolved, length", len(TOKEN))

EXPECT = {
  f'{DRIVE}/data/coltekin/offenseval-tr-training-v1.tsv':
      '8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa',
  f'{DRIVE}/data/lexicon/karaliste.txt':
      '0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b',
}
for path, want in EXPECT.items():
    if not os.path.isfile(path):
        die(f"missing input file: {path}")
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    got = h.hexdigest()
    print(f"  {'OK  ' if got == want else 'MISMATCH'} {os.path.basename(path):<32} {got[:16]}...")
    if got != want:
        die(f"""{path}
                got      {got}
                expected {want}
                Every frozen number in docs/RESULTS_LOG.md was measured on the expected bytes.
                Do not train on a corpus that has moved.""")
print("[PASS] 3 - token + both inputs verified\n")

# --- 4. fresh clone ------------------------------------------------------
MIN_COMMIT = 'e92d306'                   # carries all four phase-03 defense runs
shutil.rmtree(REPO, ignore_errors=True)
subprocess.run(['git', 'clone', '--quiet',
                f'https://{TOKEN}@github.com/MusaabAlt/nsosyal-bstar.git', REPO], check=True)
print(subprocess.run(['git', '-C', REPO, 'log', '--oneline', '-1'],
                     capture_output=True, text=True).stdout.strip())
if subprocess.run(['git', '-C', REPO, 'merge-base', '--is-ancestor', MIN_COMMIT, 'HEAD'],
                  capture_output=True).returncode != 0:
    die(f"""clone HEAD does not contain {MIN_COMMIT}.
            That commit carries the four defense runs; anything earlier is a stale repo.
            Push the local branch first, then re-run.""")
print(f"[PASS] 4 - clone contains {MIN_COMMIT}\n")

# --- 5. environment + library versions -----------------------------------
# NSOSYAL_RESULTS points at the CLONE, not at Drive: the repo copy of a result is
# canonical and is what gets committed. Drive is a mirror written only after a run
# succeeds. Checkpoints are the exception and do live on Drive -- they are not
# results, they are gitignored, and --resume needs them to outlive a dropped session.
# The split file is untouched by all of this: ROOT-relative, inside the clone, in git.
os.environ['NSOSYAL_ENV']     = 'colab'
os.environ['NSOSYAL_ROOT']    = REPO
os.environ['NSOSYAL_DATA']    = f'{DRIVE}/data'
os.environ['NSOSYAL_RESULTS'] = f'{REPO}/results'
os.environ['NSOSYAL_CKPT']    = f'{DRIVE}/checkpoints'

# transformers is PINNED: phase 01's `>=4.40` silently resolved to 5.15.0, and a
# later phase picking up a different major would change results with nothing in the
# record to show it. torch and scikit-learn come from the Colab image -- pinning
# torch would fight the runtime's CUDA build -- so they are ASSERTED, not installed.
subprocess.run([sys.executable, '-m', 'pip', '-q', 'install', 'transformers==5.15.0'], check=True)
import sklearn, transformers
BASELINE = {'transformers': '5.15.0', 'torch': '2.11.0+cu128', 'scikit-learn': '1.6.1'}
now = {'transformers': transformers.__version__, 'torch': torch.__version__,
       'scikit-learn': sklearn.__version__}
for k, want in BASELINE.items():
    print(f"  {'OK  ' if now[k] == want else 'DIFF'} {k:<13} baseline={want:<12} now={now[k]}")
if now['transformers'] != BASELINE['transformers']:
    die("transformers is pinned and did not install at 5.15.0.")
if now != BASELINE:
    print("\n[WARN] torch and/or scikit-learn differ from the phase 01 baseline run.")
    print("       Record this in docs/RESULTS_LOG.md -- do not silently compare across it.")
print("[PASS] 5 - transformers pinned, torch/sklearn asserted\n")

# --- 6. the split travelled, and is LOADED not created --------------------
sys.path.insert(0, REPO)
import config
from src import data_io
SPLIT = config.SPLITS_DIR / 'split_seed42.json'
if not SPLIT.exists():
    die(f"""{SPLIT} did not travel with the clone.
            It is committed on purpose (.gitignore has an explicit exception) so that a
            Colab clone reuses the exact dev set instead of regenerating one.""")
if subprocess.run(['git', '-C', REPO, 'ls-files', '--error-unmatch', str(SPLIT)],
                  capture_output=True).returncode != 0:
    die(f"{SPLIT} exists but is untracked -- it was created just now, not cloned.")
train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
all_rows = data_io.load_coltekin_train(config.COLTEKIN_TRAIN)
train_rows, dev_rows, meta = data_io.get_split(all_rows, SPLIT, train_sha,
                                               seed=config.SEED,
                                               dev_fraction=config.DEV_FRACTION)
FINGERPRINT = '034415af3a23b388'
print(f"  corpus      : {len(all_rows):,} rows")
print(f"  train / dev : {len(train_rows):,} / {len(dev_rows):,}")
print(f"  source      : {'LOADED from the committed file' if meta['reused_existing_file'] else 'CREATED just now'}")
print(f"  regen match : {meta['matches_regeneration']}")
print(f"  fingerprint : {meta['dev_fingerprint'][:16]}")
if not meta['reused_existing_file']:
    die("the split was CREATED, not loaded -- this session is not on the frozen dev set.")
if not meta['dev_fingerprint'].startswith(FINGERPRINT):
    die(f"""dev fingerprint {meta['dev_fingerprint'][:16]} != {FINGERPRINT}.
            Every number in docs/RESULTS_LOG.md was measured on {FINGERPRINT}.
            A different dev set makes all of them incomparable.""")
print(f"[PASS] 6 - frozen dev split {FINGERPRINT}, loaded\n")

# --- 7. results mirror is present and writable ---------------------------
MIRROR = f'{DRIVE}/results'
os.makedirs(MIRROR, exist_ok=True)
probe = os.path.join(MIRROR, '.write_probe')
try:
    with open(probe, 'w') as f:
        f.write('ok')
    os.remove(probe)
except OSError as e:
    die(f"""{MIRROR} is not writable ({e}).
            A run that finishes and then cannot mirror has lost its outputs when the
            session drops -- /content does not survive.""")
print("mirror      :", MIRROR, "| writable: True")
print("existing    :", sorted(os.listdir(MIRROR)) or "(empty)")
print("ckpt dir    :", os.environ['NSOSYAL_CKPT'])
print("\n[PASS] 7 - mirror writable")
print("=" * 70)
print("SESSION READY —", GPU, "| dev", FINGERPRINT, "| no run launched")
```

The last line is deliberate: this cell **sets up and verifies, it never trains.**
Launching is section 3, and it is a separate decision.

---

## Section 2 — the same seven cells, separately

Use these when the one-paste cell aborts and you want to iterate on one step
without re-running the rest. Contents are identical to the corresponding block
above; only the expected output is added here.

| # | Cell | What a pass looks like |
|---|---|---|
| 1 | runtime probe | `device : NVIDIA L4 | 22.0 GB`, `[PASS] 1` |
| 2 | `drive.mount('/content/drive')` | `Mounted at /content/drive`, `[PASS] 2` |
| 3 | token + SHA256 of both inputs | two `OK` lines, `8509c01c…` and `0f5a05f5…` |
| 4 | clone + `git log --oneline -1` | HEAD at `e92d306` or later |
| 5 | pin transformers, assert torch/sklearn | three `OK` lines, or a loud `[WARN]` |
| 6 | split + fingerprint | `train / dev : 26,992 / 4,764`, `LOADED`, `034415af3a23b388` |
| 7 | mirror writable | `writable: True` |

Cell 6 is also covered end-to-end by the repo's own gate, which additionally
re-runs the 3,892/6,131 sanity check and the keyword-filter matrix row:

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage preflight
```

Expected: `lexicon-free OFF 3,892 / total OFF 6,131`, dev
`4,764 {'NOT': 3844, 'OFF': 920}`, fingerprint `034415af3a23b388…`, split
**loaded from** the committed file. If this does not print `[PASS]`, stop — do
not spend GPU time on a corpus or a tagger that has moved.

---

## Section 3 — run cells (launch only when a phase is open)

**Phase 01 — baseline.** Writes the five output-contract files to
`$REPO/results/01_baseline_berturk/` (canonical), then — only if the run
succeeded — mirrors them to Drive and prints the destination and file list.
Mock or partial output is never mirrored.

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage train \
    --mirror_dir /content/drive/MyDrive/nsosyal-bstar/results/01_baseline_berturk \
    2>&1 | tee /content/phase01.log
```

Session dropped mid-run? Re-run the rebuild paste, then add `--resume`, which
reads `$DRIVE/checkpoints/01_baseline_berturk/latest.pt` (rewritten every epoch)
and continues from the next epoch with optimizer, scheduler and RNG state
restored.

**Phase 03 — defense, one variant per run.** Four separate runs, because 1a and
1b differ in both volume and mechanism and a combined run cannot attribute an
effect to either:

```python
!cd /content/nsosyal-bstar && python phase03_train_defense.py --variant raw \
    --mirror_dir /content/drive/MyDrive/nsosyal-bstar/results/03_defense/run_raw \
    2>&1 | tee /content/p03_raw.log
# then --variant 1a | 1a1b | 1a1b_d
!cd /content/nsosyal-bstar && python phase03_compare.py
```

**Getting results into git.** `/content` is wiped when the session ends, so the
canonical copy has to leave the clone or it dies with it:

```python
!cd /content/nsosyal-bstar && git status --short results/
```

`dev_predictions.csv` is gitignored by design (it contains corpus text); the
other files are committed as evidence. Take them off the Drive mirror and commit
locally.

**Never** add a test-set call to any of these. `load_coltekin_test()`'s
`PermissionError` guard stays armed until phase 05 opens.

---

## Section 4 — hardware: T4 is about 3x slower than L4

Colab hands out whatever is free, so check `device` in cell 1 rather than
assuming. Both are adequate; only the wall-clock changes.

| | L4 | T4 |
|---|---|---|
| VRAM | 22 GB | 16 GB |
| fp16 tensor throughput | ~242 TFLOPS | ~65 TFLOPS |
| bf16 | yes (sm_89) | **no** (sm_75) |
| batch 32 @ `max_len=128` | fits comfortably | fits |

**Budget roughly 3x the L4 time on a T4.** The one hard measurement we have:
the 5-fold OOF run (`phase03_train_errors.py`, 26,992 rows × 5 folds) took
**~25 min on an L4**, so budget **~75 min on a T4**. A single 3-epoch fine-tune
scales the same way. The ratio is an extrapolation from the throughput figures,
not a timed T4 run — treat it as a planning number, and record the real one in
`docs/RESULTS_LOG.md` the first time a phase runs on a T4.

Practical consequences on a T4: the four phase-03 variants stop being a
single-sitting job, so use `--resume` and expect at least one dropped session;
and do not raise the batch size to compensate — it would change the effective
optimisation setup and break comparability with every frozen number.

---

## Section 5 — failures actually hit in this project

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: mount failed` | OAuth popup not clicked inside 120 s | re-run cell 2, click promptly |
| `userdata.SecretNotFoundError` | secret exists but **Notebook access** is off | toggle it in the 🔑 sidebar |
| training silently ~20x slow | `+cpu` torch wheel on a GPU-less runtime | change runtime type; do **not** pip-install torch |
| `git pull` refuses in the clone | run outputs, untracked locally, now tracked upstream | verify byte-identical, remove, pull |
| results dir looks empty in `git status` | `results/**` ignored inside run subdirs | fixed in `.gitignore`; keep the `!results/**/*.json` exceptions |
| every run self-reports `-dirty` | `git status --porcelain` counts the run's own untracked outputs | fixed: `--untracked-files=no` |
| the proxy attaches to the wrong tab | a restored browser session reconnects to an old runtime | check `device` and stale cells before pasting |
