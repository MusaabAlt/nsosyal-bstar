# Colab runbook — phase 01 (baseline diagnosis)

Copy-paste cells for a Colab Pro+ notebook. The repo is private, so the clone
needs a token; nothing here hardcodes a path — `config.py` reads the env vars
set in cell 4.

One-time setup on Drive (do this before cell 1):

```
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-training-v1.tsv
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-testset-v1.tsv     <- present, never read in this phase
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-labela-v1.tsv      <- present, never read in this phase
MyDrive/nsosyal-bstar/data/lexicon/karaliste.txt
```

---

**Cell 1 — GPU check.** If this shows no GPU, or torch reports a `+cpu` build,
change the runtime (Runtime → Change runtime type → L4/T4 GPU) and restart the
session before going further. Cell 6 enforces the same thing and will abort, but
finding out here costs seconds.

```python
!nvidia-smi -L || echo "NO GPU -- change the runtime type"
import torch; print(torch.__version__, "| cuda:", torch.cuda.is_available())
```

A `+cpu` torch build means the *session* is a CPU runtime — nothing in this repo
installs torch, so reinstalling it is not the fix; changing the runtime type is.

**Cell 2 — Drive.** Results and checkpoints go here, not to `/content`, which
is wiped when the session drops.

```python
from google.colab import drive
drive.mount('/content/drive')
```

**Cell 3 — clone the private repo.** Store a fine-grained PAT (repo: read) in
Colab Secrets as `GH_TOKEN`; do not paste it into a cell.

```python
from google.colab import userdata
import os, subprocess
TOKEN = userdata.get('GH_TOKEN')
USER, REPO = 'MusaabAlt', 'nsosyal-bstar'
!rm -rf /content/nsosyal-bstar
subprocess.run(['git', 'clone',
                f'https://{TOKEN}@github.com/{USER}/{REPO}.git',
                '/content/nsosyal-bstar'], check=True)
!git -C /content/nsosyal-bstar log --oneline -1
```

**Cell 4 — environment.** These variables are the entire Colab-specific
configuration. Set them *before* importing anything from the repo.

Note what is **not** here: `NSOSYAL_RESULTS` points at the repo clone, not at
Drive. The repo copy of a result is canonical and is what gets committed; Drive
is a mirror written after the run succeeds (cell 6). Checkpoints are the
exception and do live on Drive — they are not results, they are gitignored, and
`--resume` needs them to outlive a dropped session. The split file is untouched
by any of this: it stays ROOT-relative, inside the clone, in git.

```python
import os
DRIVE = '/content/drive/MyDrive/nsosyal-bstar'
REPO  = '/content/nsosyal-bstar'
os.environ['NSOSYAL_ENV']     = 'colab'
os.environ['NSOSYAL_ROOT']    = REPO
os.environ['NSOSYAL_DATA']    = f'{DRIVE}/data'       # raw corpora live on Drive
os.environ['NSOSYAL_RESULTS'] = f'{REPO}/results'     # canonical; mirrored to Drive after the run
os.environ['NSOSYAL_CKPT']    = f'{DRIVE}/checkpoints'  # must survive a dropped session
!pip -q install -U "transformers>=4.40"
```

**Cell 5 — preflight.** Gates only: hashes, the 3,892/6,131 sanity check, the
split, and the keyword-filter matrix row. If this does not print `[PASS]`, stop
— do not spend GPU time on a corpus or a tagger that has moved.

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage preflight
```

Expected (must match the local run exactly, or the environments disagree):
`lexicon-free OFF 3,892 / total OFF 6,131`, dev `4,764 {'NOT': 3844, 'OFF': 920}`,
dev fingerprint starting `034415af3a23b388`, and the split **loaded from** the
committed file rather than created.

**Cell 6 — train + evaluate + mirror.** Writes the five output-contract files to
`$REPO/results/01_baseline_berturk/` (canonical), then — only if the run
succeeded — copies them to Drive and prints the destination path and file list
so you can confirm the write landed. Mock or partial output is never mirrored.

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage train \
    --mirror_dir /content/drive/MyDrive/nsosyal-bstar/results/01_baseline_berturk \
    2>&1 | tee /content/phase01.log
```

**Cell 6b — if the session dropped mid-run.** Re-run cells 1–4, then:

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage train --resume \
    --mirror_dir /content/drive/MyDrive/nsosyal-bstar/results/01_baseline_berturk \
    2>&1 | tee -a /content/phase01.log
```

`--resume` reads `$DRIVE/checkpoints/01_baseline_berturk/latest.pt`, which is
rewritten after every epoch, and continues from the next epoch with the
optimizer, scheduler and RNG state restored.

**Cell 7 — paste back.** The full stdout of cell 6, plus:

```python
print(open(f'{REPO}/results/01_baseline_berturk/metrics.json', encoding='utf-8').read())
```

Then download `dev_predictions.csv` from the Drive mirror — phase 2's failure
analysis reads it, and it is not committed (it contains corpus text).

**Cell 8 — get the canonical copy into git.** `/content` is wiped when the
session ends, so the repo copy has to leave the clone or it dies with it. Either
commit and push from Colab (needs a token with write scope), or take the four
committable files off the Drive mirror and commit them locally.

```python
!cd /content/nsosyal-bstar && git status --short results/
```

`dev_predictions.csv` is gitignored by design (corpus text); the other four
files are committed as evidence.
