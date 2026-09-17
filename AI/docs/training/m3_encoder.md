# Colab Pro+ handoff — m3_encoder multi-head fine-tune (binary + A + B + C)

State: **code complete, run blocked** — `BLOCKED_BY_POLICY` for the A head (label source,
`docs/blockers/m3_head_labels.md`), `BLOCKED_BY_DATA` for B and C. The binary head alone can be
trained today (it reproduces the study's baseline setup); a run with only the binary head trained
produces an artifact whose A / B / C heads are marked `trained: false` and are never published by
the module. Follow this file top to bottom; every step invokes repository code.

## 1. Purpose

Produce the m3 artifact the spec describes (`modules/m3_encoder/spec.md` §1, §4): one BERTurk
encoder with a binary offensive head (the `binary_offensive` score), an A head ("profanity
present", A1 carrier), a B head (`B1 B2 B3 B5`, multi-label) and a C head (`C1`–`C5`), replacing
the frozen binary-only baseline `m3-berturk-pytorch-fp32-epoch1`.

## 2. Consumer

`AI/modules/m3_encoder/module.py` loads the class-free artifact directory (`heads.json` +
`weights.pt` + tokenizer files), verifies every sha256 in `sha256.txt`, and publishes
`raw_score` / `norm_score` from the binary head and one `ContentScore` per trained head code and
channel. Untrained heads are not published.

## 3. Architecture / base checkpoint

- Base: `dbmdz/bert-base-turkish-cased` (BERTurk), `AutoModel` encoder, pooled output
  (`pooler_output`), dropout 0.1.
- Heads (`training/m3_encoder/model.py`): `binary` 2 logits softmax (OFF = index 1); `a` 1 logit
  sigmoid; `b` 4 logits sigmoid (multi-label); `c` 6 logits softmax (C1–C5 + NONE).
- Loss: sum of cross-entropy (binary), BCE-with-logits (a), BCE-with-logits per code (b),
  cross-entropy with `ignore_index` (c); each head masked to the rows that carry its label.
- Initialisation from the base checkpoint (not from `berturk_epoch1.pt`; that is a
  `BertForSequenceClassification` with a different head layout).

## 4. Datasets required

| dataset | use | required |
|---|---|---|
| Çöltekin OffensEval-TR 2020 training corpus `offenseval-tr-training-v1.tsv` (31,756 rows, OFF/NOT) | binary head; the text of every row for all heads | yes |
| frozen split `diagnosis/data/splits/split_seed42.json` (committed) | train/dev | yes |
| A labels: jsonl `{"row_id","label"}` or the derived file `AI/eval/derived/m1_lexicon_dev_seed42.json` (dev only, terlik keyword labels) | A head | owner decision: which source, and a train-split version of it |
| B labels: jsonl `{"row_id","codes":[...]}` over B1/B2/B3/B5 | B head | does not exist |
| C labels: jsonl `{"row_id","code"}` over C1..C5 / CLEAN | C head | being labelled, no date |

## 5. How to obtain each

- Corpus, lexicon, baseline checkpoint, `dev_predictions.csv`: from Musaab's Drive
  (`docs/team/abdullah/RESOURCES.md`, links marked "paste here"); verify sha256 after download:
  corpus `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa`.
- Label files: produced under the project's annotation guideline (`protocols/templates/annotation_guideline.md`,
  the B/C boundary of m4 spec §3) or, for A, by the owner's decision on the derived labels.

## 6. Licences / access

Çöltekin corpus: OffensEval 2020 research distribution (as recorded by the study). Never
redistribute; never commit corpus text. The official test set is SPENT and locked
(`diagnosis/src/data_io.py`); it is not on the Drive you mount and this handoff never reads it.
Banned: `Toygar/turkish-offensive-language-detection`, `Overfit-GM/turkish-toxic-language`
(refused by name in `training/m3_encoder/data.py`; `modules/m3_encoder/DATASETS.md`).

## 7. Drive layout

```
MyDrive/nsosyal-bstar/data/coltekin/offenseval-tr-training-v1.tsv
MyDrive/nsosyal-bstar/data/lexicon/karaliste.txt                 (not needed for training; keeps NSOSYAL_DATA complete)
MyDrive/nsosyal-bstar/labels/a_train.jsonl  a_dev.jsonl           (when the owner decides)
MyDrive/nsosyal-bstar/labels/b_*.jsonl  c_*.jsonl                 (when they exist)
MyDrive/nsosyal-bstar/runs/m3_multihead/<date>/                   (--out; survives disconnects)
```

## 8. Preprocessing

None beyond the study's reader (`diagnosis/src/data_io.read_offenseval_tsv`: tab-safe, no
pandas) and BERTurk tokenisation, `max_len 128`, first tokens kept, no padding beyond the batch.
No normalisation of any kind (m2 is a parallel channel at inference, never a training
preprocessor; m2 spec §2).

## 9. Label construction

Binary: `OFF` → 1, `NOT` → 0 from the corpus. A: 0/1 per row from the label file (missing →
masked). B: one 0/1 per code from `codes` (missing → masked). C: index of the code, `CLEAN` →
NONE class (missing → masked). `training/m3_encoder/data.py` reports per-head coverage; every
metric is read against it.

## 10. Splits

Only the frozen split (`get_split` verifies corpus hash, ids, overlap, dev fingerprint
`034415af…`); the code raises if a split would be created. Dev is never augmented. The official
test set is never touched.

## 11. Leakage protections

Banned names refused; test set locked; split frozen; label files may only contain ids of the
corpus (others are ignored, and ignored counts are printed); no obfuscation augmentation in this
run (the design/held-out family rule of `diagnosis/src/obfuscation.py` applies if augmentation
is ever added).

## 12. Seeds

`--seed 42` (Python, NumPy, torch, CUDA; DataLoader generator seeded). Bootstrap seed 42.

## 13–14. Versions

Python 3.11–3.13 (Colab's default is fine). `torch==2.11.0+cu128`, `transformers==5.15.0`,
`numpy>=1.26`. CUDA 12.8 wheels. (The study's `run_config.json` environment row.)

## 15. Installation (Colab cell)

```bash
pip install -q torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -q transformers==5.15.0 numpy pyyaml
git clone https://github.com/MusaabAlt/nsosyal-bstar.git /content/nsosyal-bstar
cd /content/nsosyal-bstar/AI
```

## 16. Runtime

GPU runtime (A100 or L4). Mount Drive. `NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-bstar/data`
(the variable `diagnosis/config.py` honours).

## 17. Resources

~3 GB GPU memory at batch 32 × 128 tokens fp16 (BERT-base); ~2 GB RAM; ~1.5 GB disk per run
(`latest.pt` + `best.pt` + artifact). Study reference: 3 epochs on an L4 ≈ 25 min.

## 18. Training command

```bash
cd /content/nsosyal-bstar/AI
export NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-bstar/data
python -m training.m3_encoder.train \
  --out /content/drive/MyDrive/nsosyal-bstar/runs/m3_multihead/$(date +%F) \
  --labels-a /content/drive/MyDrive/nsosyal-bstar/labels/a_train_dev.jsonl \   # omit heads without labels
  --epochs 3 --batch-size 32 --lr 2e-5 --max-len 128 --warmup-ratio 0.1 --weight-decay 0.01 --seed 42 --fp16
```
Resume after a disconnect: add `--resume` (reads `<out>/latest.pt`).

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
| early stopping | none; best-of-3 by dev macro-F1 | study |
| checkpoints | `latest.pt` every epoch (resume), `best.pt` best epoch; best is exported | study |

## 27. Evaluation metrics

`training/m3_encoder/evaluate.py`: binary macro-F1, OFF recall / precision / FPR with 95 %
percentile-bootstrap CIs (1000 resamples) and the confusion matrix on the 4,764 dev rows; per code
P/R/F1/FPR with CIs for A, B, C over the labelled rows only, `insufficient_sample` when a code
has fewer than 20 positives (spec §9). Written to `<artifact>/dev_eval.json`.

## 28. Acceptance criteria

- Binary head: dev macro-F1 not below the frozen baseline's 0.8271 [0.8139, 0.8405] by more than
  the CI width (a regression means the extra heads hurt the shared encoder: report, do not ship).
- A / B / C heads: reported only where ≥ 20 positives per code; no acceptance number is claimed
  for a head without a human-labelled slice.
- The banned-dataset check (`modules/m3_encoder/DATASETS.md`) re-dated for this run.

## 29–30. Output files and naming

`<out>/artifact/m3-berturk-multihead-<YYYY-MM-DD>/` containing `weights.pt`, `heads.json`,
`config.json`, `tokenizer.json`, `tokenizer_config.json`, `sha256.txt`, `MANIFEST_ROW.md`,
`dev_eval.json`. Artifact id = directory name; use `--artifact-id` to override.

## 31. Provenance

`heads.json` records base model, seed, hyperparameters, split meta (fingerprint), label coverage,
history, date. `sha256.txt` lists every file. Keep the Colab notebook's printed log with the run.

## 32. Where to place the returned artifact

Copy the whole directory to `AI/artifacts/m3_encoder/<artifact_id>/` on the development machine
(git-ignored). Do not rename files.

## 33. MANIFEST changes

Append the row from `MANIFEST_ROW.md` to `AI/artifacts/MANIFEST.md`, replacing `TBD` in the
thresholds column with the derivation file produced in §34; add a change-log line.

## 34. Threshold / calibration work after training

Every artifact carries its own thresholds (m3 spec §8). Before any verdict uses the new artifact:
derive `binary_offensive` on the frozen dev split (CAL half) exactly as
`protocols/threshold_derivation_binary_offensive_stage1.md` did (r = 3), plus the A / B / C rows
where heads were trained (`protocols/templates/threshold_derivation.md`), and record the
decision-flip table between this artifact and the baseline. The shared rows are the owner's to
edit (CONTRIBUTING step 7).

## 35. Verification after installation

```bash
cd AI
export NSOSYAL_M3_ARTIFACT=artifacts/m3_encoder/<artifact_id>       # the module's multi-head override
python -m unittest modules.m3_encoder.test_unit tests.test_signal_interfaces tests.test_end_to_end
python -m training.m3_encoder.evaluate --artifact artifacts/m3_encoder/<artifact_id> --labels-a <...>
python -m modules.m3_encoder.eval
python -m eval.run_all --results-dir eval/results/<artifact_id>
```
Expected: sha256 verification passes; `signals.artifact` equals the new id; content scores appear
only for trained heads; the binary row of `dev_eval.json` matches what `evaluate` prints.

## 36. Failure / recovery

- `LeakageError`: a banned name, a created split, or a wrong fingerprint — stop; fix the inputs.
- CUDA OOM: `--batch-size 16 --grad-accum 2`.
- Disconnect: rerun the same command with `--resume`.
- Base model download blocked: pre-download `dbmdz/bert-base-turkish-cased` to Drive and pass
  `--base <that dir>`.
- Dev macro-F1 far above 0.83: look for leakage before celebrating (spec §11).

## 37. Estimated stages

Setup 5 min · data load 1 min · 3 epochs ≈ 25 min (L4) · dev eval 2 min · export 1 min.

## Smoke test (CPU, on the development machine, no GPU)

```bash
cd AI && python -m training.m3_encoder.train --out /tmp/m3smoke --smoke 32 --base artifacts/m3_encoder/tokenizer
```
uses the local tokenizer/config directory as the base (random-initialised encoder), trains two
steps and exports a `smoke-` artifact: proves the pipeline end to end without a network or a GPU.
