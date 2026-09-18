# Colab Pro+ handoff — m3_encoder multi-head fine-tune (binary + A; B / C when their data exists)

State (2026-09-18, fourth pass): **the rule-v3 retraining is DONE** —
`m3-berturk-multihead-a-rule-v3-20260918-074806` (weights `41d98d7f…`, trained at `dba8632`), reviewed,
not promoted (`docs/training/runs/m3-berturk-multihead-a-rule-v3-20260918-074806.md`). Its A
operating threshold is FIXED at 0.50 by the owner's pre-registered policy A-OP-1
(`protocols/m3_a_head_operating_policy.md`), not derived; its `binary_offensive` threshold is the
next step (§34). No further GPU run is needed for it. The §18 command below is kept as the record
of how it was trained. (Third pass: READY_FOR_COLAB under pseudo-label rule v3, the frozen
explicit A-head taxonomy; rule v2 was an intermediate taxonomy experiment, superseded.) The first GPU run (`m3-berturk-multihead-2026-09-18`, rule v1) is frozen as
history — TECHNICALLY_VALID_BUT_A_SEMANTICALLY_MISALIGNED, `docs/training/runs/m3-berturk-multihead-2026-09-18.md`
— and is never overwritten: the retraining uses a NEW run directory and a NEW artifact id (§18).
The Drive folder is `MyDrive/nsosyal-train/` (the repository and the Colab clone are still named
`nsosyal-bstar`). Owner decisions of
2026-09-18 (`docs/blockers/m3_head_labels.md`): HYBRID A-head strategy — training supervision is
the committed terlik-derived pseudo-label file on the frozen TRAIN split (rule v3: an explicit
list of 17 obscene / profane roots); A-head quality is measured only against an independent DEV evaluation reference
labelled under `docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md` v1.1. The reference that exists is
the 500-row **AI-assisted, human-adjudicated** one — not a human oracle — and it is evaluation
only; it is not required to run the training. B and C stay
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
| Çöltekin OffensEval-TR 2020 training corpus `offenseval-tr-training-v1.tsv` (31,756 rows, OFF/NOT; sha256 `8509c01c…`) | binary head; text of every row for all heads | on the dev machine and **on Drive** (`MyDrive/nsosyal-train/data/coltekin/`, digest verified after upload, 2026-09-18) | `NSOSYAL_DATA/coltekin/` |
| frozen split `diagnosis/data/splits/split_seed42.json` | train/dev | committed | in the clone (repo root, not `AI/`) |
| **A pseudo-labels, train:** `AI/eval/derived/m1_lexicon_train_seed42.json` (26,992 rows, field `a_label`, **rule v3**: 1,528 positive / 25,464 negative / 0 masked; rule v2 had 1,463 / 25,398 / 131 masked, rule v1 2,514 positives) | A-head TRAINING supervision: explicit obscene / profane roots only (the 17 POSITIVE roots of the protocol's rule-v3 amendment); no row is masked | **committed** (protocol `protocols/m1_lexicon_train_labels_protocol.md`) | in the clone |
| A pseudo-labels, dev: `AI/eval/derived/m1_lexicon_dev_seed42.json` (4,764 rows, `a_label`) | pseudo-label AGREEMENT reporting only — never the metric | committed | in the clone |
| **A human oracle:** `{"row_id","label"}` jsonl on DEV rows, exported by `python -m eval.a_head_dev_sample export` | the A head's evaluation metric (`dev_eval.json` → `a`) | **not yet** — pending human annotation | `labels/a_dev_human.jsonl` on Drive when it exists |
| **A evaluation reference (exists):** the 500-row AI-assisted, human-adjudicated dev reference `a_dev_ai_assisted_adjudicated.jsonl` (two AI annotators, 3 disagreements decided by the human owner; 39 positives) | evaluation only, via `--labels-a-reference … --labels-a-reference-kind ai-assisted-human-adjudicated`; **never** a training label, **never** passed as `--labels-a-human` | private, uncommitted (`AI/eval/annotation/private/`); copy it and its `.reference_provenance.json` to Drive `labels/` to evaluate on Colab | `labels/a_dev_ai_assisted_adjudicated.jsonl` |
| B labels jsonl `{"row_id","codes":[...]}` | B head | no | — |
| C labels jsonl `{"row_id","code"}` | C head | no (slice being labelled, no date) | — |

The trainer's `--labels-a` reads either format (derived `.json` → `a_label`; `.jsonl` → `label`),
may be repeated, and errors on conflicting labels; `--labels-a-human` is refused on a train row.

## 5. How to obtain each

- Corpus: already on Drive under `MyDrive/nsosyal-train/data/coltekin/`. Verify sha256 after mounting:
  `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa`.
- Pseudo-labels: in the clone. Confirm they are current before training:
  `python -m eval.m1_lexicon_labels --check eval/derived/m1_lexicon_train_seed42.json` (needs terlik
  and zeyrek installed to compare versions; on Colab skip it and rely on the commit's passing suite).
- Evaluation reference: the AI-assisted, human-adjudicated 500-row file lives (private) in
  `AI/eval/annotation/private/`; copy it to Drive `labels/` to evaluate on Colab. Without any
  reference the run still trains, and `dev_eval.json` says under `a` that no quality claim exists.
- The clone is private: Colab needs a valid `GH_TOKEN` secret (fine-grained, Contents: read), used
  as `https://x-access-token:<token>@github.com/…`; the token-as-username form is rejected.

## 6. Licences / access

Çöltekin corpus: OffensEval 2020 research distribution (as recorded by the study). Never
redistribute; never commit corpus text. The official test set is SPENT and locked
(`diagnosis/src/data_io.py`); it is not on the Drive you mount and nothing here reads it.
Banned: `Toygar/turkish-offensive-language-detection`, `Overfit-GM/turkish-toxic-language`
(refused by name in `training/m3_encoder/data.py`; `modules/m3_encoder/DATASETS.md`).

## 7. Drive layout

```
MyDrive/nsosyal-train/data/coltekin/offenseval-tr-training-v1.tsv     (required)
MyDrive/nsosyal-train/labels/a_dev_ai_assisted_adjudicated.jsonl       (optional: the AI-assisted, human-adjudicated evaluation reference)
MyDrive/nsosyal-train/labels/a_dev_human.jsonl                         (if a fully human-labelled oracle ever exists)
MyDrive/nsosyal-train/labels/b_*.jsonl  c_*.jsonl                       (when they exist)
MyDrive/nsosyal-train/runs/m3_multihead/2026-09-18/                     (FIRST run, rule v1: frozen history, never written to again)
MyDrive/nsosyal-train/runs/m3_multihead/<new run id>/                   (--out; survives disconnects)
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

GPU runtime (A100 or L4). Mount Drive. `NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-train/data`
(the variable `diagnosis/config.py` honours).

## 17. Resources

~3 GB GPU memory at batch 32 × 128 tokens fp16 (BERT-base); ~2 GB RAM; ~1.5 GB disk per run
(`latest.pt` + `best.pt` + artifact). Study reference: 3 epochs on an L4 ≈ 25 min.

## 18. Training command (binary + A head)

```bash
cd /content/nsosyal-bstar/AI
export NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-train/data
RUN_ID=rule-v3-$(date +%F)                       # a NEW run id: never the first run's 2026-09-18 folder
test ! -e /content/drive/MyDrive/nsosyal-train/runs/m3_multihead/$RUN_ID || { echo "run dir exists - pick another RUN_ID"; exit 1; }
python -m training.m3_encoder.train \
  --out /content/drive/MyDrive/nsosyal-train/runs/m3_multihead/$RUN_ID \
  --artifact-id m3-berturk-multihead-a-$RUN_ID \
  --labels-a eval/derived/m1_lexicon_train_seed42.json \
  --labels-a eval/derived/m1_lexicon_dev_seed42.json \
  --epochs 3 --batch-size 32 --lr 2e-5 --max-len 128 --warmup-ratio 0.1 --weight-decay 0.01 --seed 42 --fp16
```

- `--artifact-id` is mandatory for this run: the default id is date-based and would collide with
  the first artifact (`m3-berturk-multihead-2026-09-18`) on the same date.
- To evaluate against the 500-row reference in the same run, add
  `--labels-a-reference /content/drive/MyDrive/nsosyal-train/labels/a_dev_ai_assisted_adjudicated.jsonl
  --labels-a-reference-kind ai-assisted-human-adjudicated` (it can also be applied afterwards with
  `evaluate`, §35). `--labels-a-human` is reserved for a fully human-labelled oracle; the trainer
  refuses both together and refuses a reference without its kind.
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
- `a`: **the A-head metric, against the evaluation reference only**, stamped with the reference's
  true provenance: `oracle: "human"` for a fully human-labelled oracle, `oracle:
  "ai-assisted-human-adjudicated"` for the current 500-row reference (P/R/F1/FPR with CIs over the
  labelled rows, `insufficient_sample` under 20 positives). Without a reference: `oracle: null`
  and a note that no quality claim can be made. Numbers against the AI-assisted reference are
  reported as "AI-assisted human-adjudicated reference metrics", never as human-oracle accuracy.
- `a_pseudo_label_agreement`: the same quantities against the dev pseudo-labels, under its own
  key with the note "NOT accuracy". Never quoted as A-head quality.
- `b`, `c`: per code over the labelled rows only, when labels exist.

## 28. Acceptance criteria

- Binary head: dev macro-F1 not below the frozen baseline's 0.8271 [0.8139, 0.8405] by more than
  the CI width (a regression means the extra head hurt the shared encoder: report, do not ship).
  This is the comparison with the baseline's binary numbers (same rows, same reporting point).
- A head: a number is claimed **only** from `dev_eval.json` → `a` with a non-null `oracle` and
  ≥ 20 positives, reported with the reference's kind, n, agreement (guideline §5) and CI. The
  first candidate's reference numbers (precision 0.636, recall 0.897, tp 35 / fp 20 / fn 4 / tn 441)
  are the comparison point for the retrained head. No A threshold is derived: for the rule-v3
  candidate the owner pre-registered A-OP-1, a FIXED 0.50 operating point equal to the reporting
  point (`protocols/m3_a_head_operating_policy.md`).
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
`protocols/threshold_derivation_binary_offensive_stage1.md` did (r = 3), and record the
decision-flip table between this artifact and the baseline. The A operating point is NOT derived:
it is set by a pre-registered, versioned owner policy (A-OP-1 for the rule-v3 candidate: fixed
0.50), never fitted on pseudo-labels and never tuned on the 500-row reference. The shared rows are
the owner's to edit (CONTRIBUTING step 7).

## 35. Verification after installation

```bash
cd AI                                                                   # with AI/.venv
export NSOSYAL_M3_ARTIFACT=artifacts/m3_encoder/<artifact_id>            # the module's multi-head override
python -m unittest modules.m3_encoder.test_unit tests.test_signal_interfaces tests.test_end_to_end training.tests.test_training_m3
python -m training.m3_encoder.evaluate --artifact artifacts/m3_encoder/<artifact_id> \
    --labels-a eval/derived/m1_lexicon_dev_seed42.json \
    --labels-a-reference eval/annotation/private/a_dev_ai_assisted_adjudicated.jsonl \
    --labels-a-reference-kind ai-assisted-human-adjudicated
python -m modules.m3_encoder.eval
python -m eval.run_all --results-dir eval/results/<artifact_id>
```
Expected: sha256 verification passes; `signals.artifact` equals the new id; content scores appear
only for trained heads (A1 on both channels); the binary row of `dev_eval.json` matches what
`evaluate` prints; `a.oracle` states the reference's kind (`"ai-assisted-human-adjudicated"` here).

## 36. Failure / recovery

- `LeakageError`: a banned name, a created split, or a wrong fingerprint — stop; fix the inputs.
- `ValueError: ... evaluation-reference A labels fall on TRAIN rows`: the reference file is not a dev export.
- Published provenance written by an older exporter (`a_human` keys, "human dev oracle"): correct
  the metadata WITHOUT retraining with `python -m training.m3_encoder.correct_metadata` (it writes a
  new directory and asserts the weights digest).
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
