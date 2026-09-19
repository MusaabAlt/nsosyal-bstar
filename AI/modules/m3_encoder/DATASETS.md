# m3_encoder — datasets in the training and evaluation path (written check)

m3 spec §9 "Leakage check": a committed file listing every dataset in the training and
evaluation path, with an explicit line confirming that neither banned dataset appears. Dated,
not assumed. Re-check and re-date this file whenever a dataset is added.

**Checked: 2026-09-18** (re-dated for the A-head label decision), against the files on the
development machine and the committed results (`docs/team/abdullah/RESOURCES.md` records the
digests). Neither banned dataset appears anywhere in the training or evaluation path.

## In the path

| dataset | role | rows | where | sha256 | licence |
|---|---|---|---|---|---|
| Çöltekin OffensEval-TR 2020, training corpus (`offenseval-tr-training-v1.tsv`) | the only corpus trained and evaluated on; frozen split seed 42 (26,992 train / 4,764 dev) | 31,756 | `diagnosis/data/coltekin/` (not in git) | `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa` | as distributed by the OffensEval 2020 organisers (research use); recorded in the study |
| frozen split `split_seed42.json` | the split; never regenerated | — | `diagnosis/data/splits/` (committed) | `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2` | project |
| terlik-derived pseudo-labels on TRAIN (`eval/derived/m1_lexicon_train_seed42.json`, field `a_label`) | A-head TRAINING supervision (owner decision 2026-09-18, HYBRID strategy; `protocols/m1_lexicon_train_labels_protocol.md`, **rule v3**: explicit obscene / profane roots only — 1,528 positive, no row masked) — a keyword label, never an evaluation oracle | 26,992 | committed (regenerable; `python -m eval.m1_lexicon_labels --check`) | see file header (`rows_sha256`) | project; terlik MIT, zeyrek MIT |
| terlik-derived pseudo-labels on DEV (`eval/derived/m1_lexicon_dev_seed42.json`, field `a_label`) | pseudo-label AGREEMENT reporting only (`dev_eval.json` `a_pseudo_label_agreement`), and the terlik-vs-karaliste comparison; never the A-head metric | 4,764 | committed (regenerable) | see file header | project; terlik MIT, zeyrek MIT |
| A-head dev evaluation reference (`eval/annotation/private/a_dev_ai_assisted_adjudicated.jsonl`) — **AI-assisted, human-adjudicated**: two AI annotators (Claude/Fable, Gemini), 3 disagreements decided by the human owner; NOT a human oracle | evaluation only (`--labels-a-reference … --labels-a-reference-kind ai-assisted-human-adjudicated`); dev rows only; never trained on, never a source of rule edits | 500 (39 positive), sample `eval/annotation/a_head_dev_sample_seed42_n500.ids.json`, guideline v1.1 | private, uncommitted; sha256 `931c606b…` | recorded in the export's `.provenance.json` | project |
| `karaliste.txt` | defines the frozen `lexicon_hit` / `lexicon_free` evaluation slice only; never a training input | 697 lines | `diagnosis/data/lexicon/` (not in git) | `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` | comparison only (spec §5 of m1) |
| Train + dev | Çöltekin, Ç. (2020), *A Corpus of Turkish Offensive Language on Social Media*, LREC 2020 (OffensEval-TR 2020 training data) | `offenseval-tr-training-v1.tsv` | 31,756 rows | TBD — record from the corpus distribution before the first commit of numbers | Yes |
| Split | Row-ID split, seed 42, 85/15 stratified | `diagnosis/data/splits/split_seed42.json` | 26,992 train / 4,764 dev | in-repo | — |
| Base model (not a labelled dataset) | `dbmdz/bert-base-turkish-cased` | Hugging Face checkpoint | ~110M params | TBD — verify on model card | Yes (spec §5 Encoder) |

No other dataset is used. Toraman v2, TDDİ-2023 and ATC are allowed by spec §5 but
are **not** in the path for this artifact.

## Explicitly NOT in the path

- **`Toygar/turkish-offensive-language-detection`** — BANNED (m3 spec §5: merges
  `offenseval2020_tr`, i.e. the closed official test set). Not present on the machine, not
  referenced by any code; `training/m3_encoder/data.py` refuses the name.
- **`Overfit-GM/turkish-toxic-language`** — BANNED (pseudo-labels and machine-translated Jigsaw).
  Not present, not referenced; refused by name in the same place.
- **The official Çöltekin test set and its gold labels** — SPENT (one held-out measurement on
  2026-08-16, `diagnosis/results/05_final_test/TEST_SET_SPENT.json`); locked by
  `diagnosis/src/data_io.py::load_coltekin_test`. Never loaded by m3 code.
- Toraman v2, TDDİ-2023, ATC (allowed by spec §5) — not obtained; if any is added, this file
  gets a row with hydration loss, class distribution and licence (spec §5, §10).
- No sarcasm or irony data (m5's gate is unresolved and m5 is a separate model, ADR-003).
### Explicitly excluded from every path
| Dataset | Status |
|---|---|
| Official OffensEval-TR 2020 **test set** (`offenseval-tr-testset-v1.tsv`, `offenseval-tr-labela-v1.tsv`) | **Not used** for training, dev, threshold derivation or m3 fixtures. It was spent once in `diagnosis/` (`diagnosis/results/05_final_test/TEST_SET_SPENT.json`) and stays closed. |

## Truncation policy (spec §5, §9)

Maximum sequence length **128 tokens** (the study's `max_len`), first tokens kept, the rest
dropped; a note `truncated: N tokens, scored the first 128` is emitted whenever it happens
(`modules/m3_encoder/module.py`, `test_truncation_is_noted`). Both channels are tokenised
independently today; whether they truncate at the same character offset is measured once m2
publishes a normalized channel (ADR-008 makes the offset available).
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
