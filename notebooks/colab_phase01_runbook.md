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

**Cell 1 — GPU check.** Abort the session and get a better runtime if this is
empty; the run is minutes on a GPU and hours on CPU.

```python
!nvidia-smi
```

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

**Cell 4 — environment.** These four variables are the entire Colab-specific
configuration. Set them *before* importing anything from the repo.

```python
import os
DRIVE = '/content/drive/MyDrive/nsosyal-bstar'
os.environ['NSOSYAL_ENV']     = 'colab'
os.environ['NSOSYAL_ROOT']    = '/content/nsosyal-bstar'
os.environ['NSOSYAL_DATA']    = f'{DRIVE}/data'
os.environ['NSOSYAL_RESULTS'] = f'{DRIVE}/results'
os.environ['NSOSYAL_CKPT']    = f'{DRIVE}/checkpoints'
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

**Cell 6 — train + evaluate.** Writes the four output-contract files to
`$DRIVE/results/01_baseline_berturk/`.

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage train 2>&1 | tee /content/phase01.log
```

**Cell 6b — if the session dropped mid-run.** Re-run cells 1–4, then:

```python
!cd /content/nsosyal-bstar && python phase01_baseline.py --stage train --resume 2>&1 | tee -a /content/phase01.log
```

`--resume` reads `$DRIVE/checkpoints/01_baseline_berturk/latest.pt`, which is
rewritten after every epoch, and continues from the next epoch with the
optimizer, scheduler and RNG state restored.

**Cell 7 — paste back.** The full stdout of cell 6, plus:

```python
print(open(f'{DRIVE}/results/01_baseline_berturk/metrics.json', encoding='utf-8').read())
```

Then download `dev_predictions.csv` from Drive — phase 2's failure analysis
reads it, and it is not committed (it contains corpus text).
