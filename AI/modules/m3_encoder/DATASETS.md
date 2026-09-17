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
| terlik-derived pseudo-labels on TRAIN (`eval/derived/m1_lexicon_train_seed42.json`, field `a_label`) | A-head TRAINING supervision (owner decision 2026-09-18, HYBRID strategy; `protocols/m1_lexicon_train_labels_protocol.md`) — a keyword label, never an evaluation oracle | 26,992 | committed (regenerable; `python -m eval.m1_lexicon_labels --check`) | see file header (`rows_sha256`) | project; terlik MIT, zeyrek MIT |
| terlik-derived pseudo-labels on DEV (`eval/derived/m1_lexicon_dev_seed42.json`, field `a_label`) | pseudo-label AGREEMENT reporting only (`dev_eval.json` `a_pseudo_label_agreement`), and the terlik-vs-karaliste comparison; never the A-head metric | 4,764 | committed (regenerable) | see file header | project; terlik MIT, zeyrek MIT |
| human "profanity present" dev oracle (`eval/annotation/private/a_dev_human.jsonl`, from `python -m eval.a_head_dev_sample`) | the ONLY A-head evaluation oracle (`docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md`); dev rows only, never trained on | sample n per the committed ids file in `eval/annotation/` (default 500) | **does not exist yet** — human labelling pending | recorded in the export's `.provenance.json` | project |
| `karaliste.txt` | defines the frozen `lexicon_hit` / `lexicon_free` evaluation slice only; never a training input | 697 lines | `diagnosis/data/lexicon/` (not in git) | `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` | comparison only (spec §5 of m1) |

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

## Truncation policy (spec §5, §9)

Maximum sequence length **128 tokens** (the study's `max_len`), first tokens kept, the rest
dropped; a note `truncated: N tokens, scored the first 128` is emitted whenever it happens
(`modules/m3_encoder/module.py`, `test_truncation_is_noted`). Both channels are tokenised
independently today; whether they truncate at the same character offset is measured once m2
publishes a normalized channel (ADR-008 makes the offset available).
