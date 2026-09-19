# m3_encoder — dataset and leakage check

Written check required by spec.md §9 (Leakage check) and §10 (Acceptance criteria).
Update this file, with a new dated entry, whenever a dataset enters or leaves the
training or evaluation path. Entries are appended, never edited.

---

## Check of 2026-09-15 — Abdullah

### Datasets in the training and evaluation path

| Role | Dataset | Exact file(s) | Size | Licence | Allowed by spec §5 |
|---|---|---|---|---|---|
| Train + dev | Çöltekin, Ç. (2020), *A Corpus of Turkish Offensive Language on Social Media*, LREC 2020 (OffensEval-TR 2020 training data) | `offenseval-tr-training-v1.tsv` | 31,756 rows | TBD — record from the corpus distribution before the first commit of numbers | Yes |
| Split | Row-ID split, seed 42, 85/15 stratified | `diagnosis/data/splits/split_seed42.json` | 26,992 train / 4,764 dev | in-repo | — |
| Base model (not a labelled dataset) | `dbmdz/bert-base-turkish-cased` | Hugging Face checkpoint | ~110M params | TBD — verify on model card | Yes (spec §5 Encoder) |

No other dataset is used. Toraman v2, TDDİ-2023 and ATC are allowed by spec §5 but
are **not** in the path for this artifact.

### Explicitly excluded from every path

| Dataset | Status |
|---|---|
| Official OffensEval-TR 2020 **test set** (`offenseval-tr-testset-v1.tsv`, `offenseval-tr-labela-v1.tsv`) | **Not used** for training, dev, threshold derivation or m3 fixtures. It was spent once in `diagnosis/` (`diagnosis/results/05_final_test/TEST_SET_SPENT.json`) and stays closed. |

### Banned datasets (spec §5) — confirmation

- `Toygar/turkish-offensive-language-detection` — **does not appear** in the training or evaluation path.
- `Overfit-GM/turkish-toxic-language` — **does not appear** in the training or evaluation path.

**How this was checked:** a full-text search of the repository (excluding `.venv/`)
for `Toygar`, `turkish-offensive-language-detection`, `Overfit-GM` and
`turkish-toxic-language`. The only hits are `AI/modules/m3_encoder/spec.md` (the ban
itself) and two `diagnosis/docs/` files that record rejecting `Overfit-GM`. No code,
config, notebook or data file references either dataset. The only corpus loaders in
`diagnosis/` (`diagnosis/config.py`, `diagnosis/src/data_io.py`) read the Çöltekin
files listed above.

**Leakage note:** the Çöltekin training file and the official test set are disjoint
releases of the same corpus. `Toygar/...` is banned precisely because it merges the
test set in, so no Hugging Face mirror of OffensEval-TR is used; the corpus is read
from the original `.tsv` files only.
