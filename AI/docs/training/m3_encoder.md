# Colab Pro+ handoff — m3_encoder multi-head fine-tune (binary + A; B / C when their data exists)

State (2026-09-18): **READY_FOR_COLAB for the binary + A-head run.** Owner decisions of
2026-09-18 (`docs/blockers/m3_head_labels.md`): HYBRID A-head strategy — training supervision is
the committed terlik-derived pseudo-label file on the frozen TRAIN split; the *only* A-head
quality claim is measured against a human-labelled DEV subset (`docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md`),
which does **not exist yet** and is not required to run the training. B and C stay
`BLOCKED_BY_DATA`; a run without their labels exports them as `trained: false` and the module
never publishes them. Every path below exists in the repository at the commit you clone.

## 1. Purpose

Produce the m3 artifact the spec describes (`modules/m3_encoder/spec.md` §1, §4): one BERTurk
encoder with a binary offensive head (`binary_offensive`), an A head ("profanity present", A1
carrier, ADR-005), and — when data exists — a B head (`B1 B2 B3 B5`, multi-label) and a C head
(`C1`–`C5`), replacing the frozen binary-only baseline `m3-berturk-pytorch-fp32-epoch1`.

## 2. Consumer

`AI/modules/m3_encoder/module.py` loads the class-free artifact directory (`heads.json` +
`weights.pt` + tokenizer files) named by `NSOSYAL_M3_ARTIFACT`, verifies every sha256 in
`sha256.txt`, and publishes `raw_score` / `norm_score` from the binary head and one
`ContentScore` per TRAINED head code and channel. Untrained heads are not published.

## 3. Architecture / base checkpoint

- Base: `dbmdz/bert-base-turkish-cased` (BERTurk), `AutoModel` encoder, pooled output, dropout 0.1.
- Heads (`training/m3_encoder/model.py`): `binary` 2 logits softmax (OFF = index 1); `a` 1 logit
  sigmoid; `b` 4 logits sigmoid (multi-label); `c` 6 logits softmax (C1–C5 + NONE).
- Loss: sum of cross-entropy (binary), BCE-with-logits (a), BCE-with-logits per code (b),
  cross-entropy with `ignore_index` (c); each head masked to the rows that carry its label.
- Initialisation from the base checkpoint (not from `berturk_epoch1.pt`).

## 4. Inputs — what exists and where it comes from

| input | role | exists? | where |
|---|---|---|---|
| Çöltekin OffensEval-TR 2020 training corpus `offenseval-tr-training-v1.tsv` (31,756 rows, OFF/NOT; sha256 `8509c01c…`) | binary head; text of every row for all heads | on the dev machine; **on Drive only once Musaab uploads it** (RESOURCES.md open item 1) | `NSOSYAL_DATA/coltekin/` |
| frozen split `diagnosis/data/splits/split_seed42.json` | train/dev | committed | in the clone (repo root, not `AI/`) |
| **A pseudo-labels, train:** `AI/eval/derived/m1_lexicon_train_seed42.json` (26,992 rows, field `a_label`) | A-head TRAINING supervision | **committed** (protocol `protocols/m1_lexicon_train_labels_protocol.md`) | in the clone |
| A pseudo-labels, dev: `AI/eval/derived/m1_lexicon_dev_seed42.json` (4,764 rows, `a_label`) | pseudo-label AGREEMENT reporting only — never the metric | committed | in the clone |
| **A human oracle:** `{"row_id","label"}` jsonl on DEV rows, exported by `python -m eval.a_head_dev_sample export` | the A head's evaluation metric (`dev_eval.json` → `a`) | **not yet** — pending human annotation | `labels/a_dev_human.jsonl` on Drive when it exists |
| B labels jsonl `{"row_id","codes":[...]}` | B head | no | — |
| C labels jsonl `{"row_id","code"}` | C head | no (slice being labelled, no date) | — |

The trainer's `--labels-a` reads either format (derived `.json` → `a_label`; `.jsonl` → `label`),
may be repeated, and errors on conflicting labels; `--labels-a-human` is refused on a train row.

## 5. How to obtain each

- Corpus: from Musaab's Drive (`docs/team/abdullah/RESOURCES.md`; the links are still marked
  "paste here" — that is the human step before any Colab run). Verify sha256 after download:
  `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa`.
- Pseudo-labels: in the clone. Confirm they are current before training:
  `python -m eval.m1_lexicon_labels --check eval/derived/m1_lexicon_train_seed42.json` (needs terlik
  and zeyrek installed to compare versions; on Colab skip it and rely on the commit's passing suite).
- Human oracle: `docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md` §6–§7. Until it exists, the run
  proceeds without `--labels-a-human` and `dev_eval.json` says so under `a`.

## 6. Licences / access

Çöltekin corpus: OffensEval 2020 research distribution (as recorded by the study). Never
redistribute; never commit corpus text. The official test set is SPENT and locked
(`diagnosis/src/data_io.py`); it is not on the Drive you mount and nothing here reads it.
Banned: `Toygar/turkish-offensive-language-detection`, `Overfit-GM/turkish-toxic-language`
(refused by name in `training/m3_encoder/data.py`; `modules/m3_encoder/DATASETS.md`).

## 7. Drive layout

```
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-training-v1.tsv     (required)
MyDrive/nsosyal-bstar/labels/a_dev_human.jsonl                         (when the human oracle exists)
MyDrive/nsosyal-bstar/labels/b_*.jsonl  c_*.jsonl                       (when they exist)
MyDrive/nsosyal-bstar/runs/m3_multihead/<date>/                         (--out; survives disconnects)
```

The pseudo-label files are NOT on Drive: they come with the clone (`AI/eval/derived/`).

## 8. Preprocessing

None beyond the study's reader (`diagnosis/src/data_io.read_offenseval_tsv`: tab-safe, no
pandas) and BERTurk tokenisation, `max_len 128`, first tokens kept, no padding beyond the batch.
No normalisation of any kind (m2 is a parallel channel at inference, never a training
preprocessor; m2 spec §2).

## 9. Label construction

Binary: `OFF` → 1, `NOT` → 0 from the corpus. A: `a_label` 0/1 per train row from the derived
file (missing → masked; dev rows of the dev derived file are used only for the agreement block).
B: one 0/1 per code from `codes` (missing → masked). C: index of the code, `CLEAN` → NONE class
(missing → masked). `training/m3_encoder/data.py` reports per-head coverage (`label_coverage`)
and every label file's sha256 (`label_sources`); both land in `heads.json` and `dev_eval.json`.

## 10. Splits

Only the frozen split (`get_split` verifies corpus hash, ids, overlap, dev fingerprint
`034415af…`); the code raises if a split would be created. Dev is never augmented. The official
test set is never touched. A human A label on a train row aborts the run.

## 11. Leakage protections

Banned names refused; test set locked; split frozen; label files may only contain ids of the
corpus (others are ignored); pseudo-labels are a deterministic function of the text (terlik), so
they carry no gold; no obfuscation augmentation in this run.

## 12. Seeds

`--seed 42` (Python, NumPy, torch, CUDA; DataLoader generator seeded). Bootstrap seed 42.

## 13–14. Versions

Python 3.11–3.13 on Colab (`docs/team/abdullah/COLAB_SETUP.md` refuses others because of the
study's scikit-learn pin; the training package itself does not need scikit-learn and the CPU
smoke test runs on 3.14 locally). `torch==2.11.0+cu128`, `transformers==5.15.0`, `numpy>=1.26`.

## 15. Installation (Colab cell)

```bash
pip install -q torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -q transformers==5.15.0 numpy pyyaml
git clone https://github.com/MusaabAlt/nsosyal-bstar.git /content/nsosyal-bstar   # token per COLAB_SETUP.md if private
cd /content/nsosyal-bstar/AI
```

## 16. Runtime

GPU runtime (A100 or L4). Mount Drive. `NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-bstar/data`
(the variable `diagnosis/config.py` honours).

## 17. Resources

~3 GB GPU memory at batch 32 × 128 tokens fp16 (BERT-base); ~2 GB RAM; ~1.5 GB disk per run
(`latest.pt` + `best.pt` + artifact). Study reference: 3 epochs on an L4 ≈ 25 min.

## 18. Training command (binary + A head)

```bash
cd /content/nsosyal-bstar/AI
export NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-bstar/data
python -m training.m3_encoder.train \
  --out /content/drive/MyDrive/nsosyal-bstar/runs/m3_multihead/$(date +%F) \
  --labels-a eval/derived/m1_lexicon_train_seed42.json \
  --labels-a eval/derived/m1_lexicon_dev_seed42.json \
  --epochs 3 --batch-size 32 --lr 2e-5 --max-len 128 --warmup-ratio 0.1 --weight-decay 0.01 --seed 42 --fp16
```

- Add `--labels-a-human /content/drive/MyDrive/nsosyal-bstar/labels/a_dev_human.jsonl` once the
  human oracle exists (it can also be applied afterwards with `evaluate`, §35).
- Add `--labels-b` / `--labels-c` only when those files exist.
- Resume after a disconnect: rerun the same command with `--resume` (reads `<out>/latest.pt`).

## 19–26. Hyperparameters

| setting | value | source |
|---|---|---|
| epochs | 3, best epoch by dev binary macro-F1 | study phase 01 |
| batch size | 32 (`--grad-accum 1`; use `--batch-size 16 --grad-accum 2` on a smaller GPU) | study |
| learning rate | 2e-5, linear warmup 10 % then linear decay to 0 | study |
| weight decay | 0.01 (not on bias / LayerNorm) | study |
| max grad norm | 1.0 | study |
| precision | fp16 autocast + GradScaler | study |
| loss | summed masked heads, weights 1.0 each (`model.multitask_loss`) | this handoff |
| class weighting / sampling | none (matches the baseline; change only with a written protocol) | study |
| early stopping | none; best-of-3 by dev binary macro-F1 | study |
| checkpoints | `latest.pt` every epoch (resume), `best.pt` best epoch; best is exported | study |

## 27. Evaluation metrics

`training/m3_encoder/evaluate.py`, written to `<artifact>/dev_eval.json`:

- `binary`: macro-F1, OFF recall / precision / FPR with 95 % percentile-bootstrap CIs (1000
  resamples) and the confusion matrix on the 4,764 dev rows at the study's 0.5 reporting point.
- `a`: **the A-head metric, against the human oracle only** (`oracle: "human"`, P/R/F1/FPR with
  CIs over the labelled rows, `insufficient_sample` under 20 positives). Without the oracle:
  `oracle: null` and a note that no quality claim can be made.
- `a_pseudo_label_agreement`: the same quantities against the dev pseudo-labels, under its own
  key with the note "NOT accuracy". Never quoted as A-head quality.
- `b`, `c`: per code over the labelled rows only, when labels exist.

## 28. Acceptance criteria

- Binary head: dev macro-F1 not below the frozen baseline's 0.8271 [0.8139, 0.8405] by more than
  the CI width (a regression means the extra head hurt the shared encoder: report, do not ship).
  This is the comparison with the baseline's binary numbers (same rows, same reporting point).
- A head: a number is claimed **only** from `dev_eval.json` → `a` with `oracle: "human"` and
  ≥ 20 positives, reported with the oracle's n, its agreement (guideline §5) and its CI.
  Pseudo-label agreement is reported next to it, labelled as agreement.
- B / C heads: reported only where ≥ 20 positives per code; no acceptance number is claimed
  for a head without a human-labelled slice.
- The banned-dataset check (`modules/m3_encoder/DATASETS.md`) re-dated for this run.

## 29–30. Output files and naming

`<out>/artifact/m3-berturk-multihead-<YYYY-MM-DD>/` containing `weights.pt`, `heads.json`,
`config.json`, `tokenizer.json`, `tokenizer_config.json`, `sha256.txt`, `MANIFEST_ROW.md`,
`dev_eval.json`. Artifact id = directory name; use `--artifact-id` to override.

## 31. Provenance

`heads.json` records base model, seed, hyperparameters, split meta (fingerprint), label coverage,
label sources (file name + sha256 + kind), `a_head_supervision`, history, date. `sha256.txt`
lists every file. Keep the Colab notebook's printed log with the run.

## 32. Where to place the returned artifact

Copy the whole directory to `AI/artifacts/m3_encoder/<artifact_id>/` on the development machine
(git-ignored). Do not rename files.

## 33. MANIFEST changes

Append the row from `MANIFEST_ROW.md` to `AI/artifacts/MANIFEST.md`, replacing `TBD` in the
thresholds column with the derivation file produced in §34; add a change-log line.

## 34. Threshold / calibration work after training

Every artifact carries its own thresholds (m3 spec §8). Before any verdict uses the new artifact:
derive `binary_offensive` on the frozen dev split (CAL half) exactly as
`protocols/threshold_derivation_binary_offensive_stage1.md` did (r = 3), plus the A row
(`protocols/templates/threshold_derivation.md`) — the A threshold is derived on the **human**
oracle rows, never on pseudo-labels — and record the decision-flip table between this artifact and
the baseline. The shared rows are the owner's to edit (CONTRIBUTING step 7).

## 35. Verification after installation

```bash
cd AI                                                                   # with AI/.venv
export NSOSYAL_M3_ARTIFACT=artifacts/m3_encoder/<artifact_id>            # the module's multi-head override
python -m unittest modules.m3_encoder.test_unit tests.test_signal_interfaces tests.test_end_to_end training.tests.test_training_m3
python -m training.m3_encoder.evaluate --artifact artifacts/m3_encoder/<artifact_id> \
    --labels-a eval/derived/m1_lexicon_dev_seed42.json \
    --labels-a-human eval/annotation/private/a_dev_human.jsonl          # once the oracle exists
python -m modules.m3_encoder.eval
python -m eval.run_all --results-dir eval/results/<artifact_id>
```
Expected: sha256 verification passes; `signals.artifact` equals the new id; content scores appear
only for trained heads (A1 on both channels); the binary row of `dev_eval.json` matches what
`evaluate` prints; `a.oracle` is `"human"` when the oracle was given.

## 36. Failure / recovery

- `LeakageError`: a banned name, a created split, or a wrong fingerprint — stop; fix the inputs.
- `ValueError: ... human A labels fall on TRAIN rows`: the oracle file is not the dev export.
- `ValueError: conflicting A labels`: two `--labels-a` files disagree on a row — regenerate both.
- CUDA OOM: `--batch-size 16 --grad-accum 2`.
- Disconnect: rerun the same command with `--resume`.
- Base model download blocked: pre-download `dbmdz/bert-base-turkish-cased` to Drive and pass
  `--base <that dir>`.
- Dev macro-F1 far above 0.83: look for leakage before celebrating (spec §11).

## 37. Estimated stages

Setup 5 min · data load 1 min · 3 epochs ≈ 25 min (L4) · dev eval 2 min · export 1 min.

## Smoke test (CPU, on the development machine, no GPU)

```bash
cd AI && python -m training.m3_encoder.train --out <scratch dir> --smoke 32 --base artifacts/m3_encoder/tokenizer \
    --labels-a eval/derived/m1_lexicon_train_seed42.json
```
uses the local tokenizer/config directory as the base (random-initialised encoder), trains two
steps and exports a `smoke-` artifact with the A head marked trained: proves the pipeline end to
end without a network or a GPU. `training/tests/test_training_m3.py` does the same with synthetic
label files, including the human-oracle path.
