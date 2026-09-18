# Rule-v3 candidate — `m3-berturk-multihead-a-rule-v3-20260918-074806` (binary + A head)

**State:** trained, reviewed, A operating policy pre-registered (A-OP-1, fixed 0.50), metadata
correction prepared and validated. **Not promoted.** The binary threshold for this artifact is
not derived yet. The run directory on Drive is never overwritten; the historical rule-v1 run
(`m3-berturk-multihead-2026-09-18.md`) stays frozen.

## Identity

| | |
|---|---|
| artifact id | `m3-berturk-multihead-a-rule-v3-20260918-074806` |
| run directory (Drive) | `/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/rule-v3-20260918-074806/` |
| weights.pt sha256 | `41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145` |
| other exported files | config.json `78b32568…`, tokenizer.json `36c9681b…`, tokenizer_config.json `4e5738ad…`, heads.json `599b0d4b…` (as exported), MANIFEST_ROW.md `7a89244e…`, dev_eval.json `e1d8264b…` |
| trained at | `dba863233a354273415f68845f82e799a00dab70` (`audit/m1-m6`; the Colab cell asserted HEAD before training) |
| configuration | handoff §18: 3 epochs, batch 32, lr 2e-5, max_len 128, warmup 0.1, weight decay 0.01, max grad norm 1.0, seed 42, fp16; base `dbmdz/bert-base-turkish-cased` |
| checkpoint rule | best dev binary macro-F1 (the study's rule) → **best_epoch 0** |
| heads | binary trained, A trained, B untrained, C untrained |

## Training labels (history: these bytes, not later regenerations)

| file | rows | positives | sha256 | where |
|---|---|---|---|---|
| `m1_lexicon_train_seed42.json` (supervision) | 26,992 | 1,528 | `78d845a5fed8dd38441d9ef23f416b85ed8d2ba747d94f5943509550d9fc50c8` | git `7f5e003` |
| `m1_lexicon_dev_seed42.json` (agreement only) | 4,764 | 257 | `8f4dcdfeec707bd8cb9b52744ff6b72a675cdb94790b64d167b87c12fd603ee7` | git `7f5e003` |

Pseudo-label **rule v3** (`protocols/m1_lexicon_train_labels_protocol.md`, amendment (b)). The
working files were regenerated at `fa79d6d` after the m1 0.1.2 / m2 0.1.2 fixes: new bytes (train
`5f151d9d…`, dev `f26a0035…`), **identical `a_label` on every row** of both splits. The weights
were trained on the bytes above; `tests/test_m1_lexicon_labels.py` pins both facts.

## Evaluation at the reporting point 0.5 (export-time `dev_eval.json`, unchanged)

Binary head, 4,764 frozen dev rows, 1,000 bootstrap resamples:

| macro-F1 | OFF recall | OFF precision | FPR | tp / fp / fn / tn |
|---|---|---|---|---|
| 0.8247 [0.8108, 0.8377] | 0.7141 [0.6848, 0.7426] | 0.7196 [0.6908, 0.7467] | 0.0666 [0.0586, 0.0742] | 657 / 256 / 263 / 3,588 |

Baseline 0.8271 [0.8139, 0.8405]: a drop of 0.0024 inside the handoff §28 allowance (0.0266). Epoch
history (binary dev macro-F1 / train loss): 0.8247 / 0.506, 0.8166 / 0.306, 0.8204 / 0.212.

A head against the 500-row **AI-assisted, human-adjudicated** dev reference (evaluation only, NOT
a human oracle; 39 positives):

| tp | fp | fn | tn | precision | recall | F1 | FPR |
|---|---|---|---|---|---|---|---|
| 32 | 1 | 7 | 460 | 0.970 [0.889, 1.000] | 0.821 [0.690, 0.930] | 0.889 [0.800, 0.957] | 0.0022 [0.000, 0.0067] |

Rule-v1 candidate on the same rows: tp 35 / fp 20 / fn 4 / tn 441, precision 0.636, recall 0.897.
False positives fell from 20 to 1 with non-overlapping precision and FPR intervals; the recall
change is not resolvable with 39 positives.

Pseudo-label agreement (rule v3, 4,764 dev rows; agreement, NOT accuracy): precision 0.899, recall
0.763, F1 0.825, FPR 0.0049 (tp 196 / fp 22 / fn 61 / tn 4,485).

## Review verdict (2026-09-18) and gates

| gate | status |
|---|---|
| artifact technically valid | PASS (metadata correction below; weights untouched) |
| binary acceptance | PASS |
| A-head semantic validity | PASS (the insult false-positive class of rule v1 is gone) |
| A-head evaluation strength | NEEDS_WORK (39 positives; recall interval 0.69–0.93) |
| A operating point | SET by policy: **A-OP-1, fixed 0.50** (`protocols/m3_a_head_operating_policy.md`); not derived |
| binary threshold for this artifact | NOT DERIVED (next step, pre-registered r = 3 procedure) |
| production-promotable | BLOCKED: binary threshold; corrected metadata to install; owner promotion decision |

No GPU retraining is scientifically justified for this candidate.

## Metadata correction (prepared and validated; the Drive artifact is NOT overwritten)

The exported `heads.json` said "quality claims only against the human dev oracle" and published
`a_human` keys, although it records `a_evaluation_reference_kind: ai-assisted-human-adjudicated`.
Corrected WITHOUT retraining by `training/m3_encoder/correct_metadata.py` 1.0.0 (tool commit
`846646e`), run on a scratch copy of the artifact on the Colab runtime's local disk; Drive was only
read, and its eight files had identical digests before and after.

| file | exported | corrected |
|---|---|---|
| weights.pt | `41d98d7f…` | `41d98d7f…` (asserted equal: source before, source after, output) |
| heads.json | `599b0d4b…` | `897f7e95…` |
| dev_eval.json | `e1d8264b…` | `22736270…` (metric blocks unchanged) |
| sha256.txt | `72c330e3…` | `99634f2f…` (same five files; only the heads.json line changed) |
| metadata_correction.json | — | `f0fe2557…` |

The corrected copy passed `verify`, loaded through m3's own sha256-verifying loader, and gave
outputs identical to the exported copy on two neutral sentences. The exported originals, the
corrected metadata and the record are committed in
`m3-berturk-multihead-a-rule-v3-20260918-074806.metadata/`; a test re-derives the corrected files
from the originals byte for byte (`training/tests/test_correct_metadata.py`).

To install later, write the corrected copy NEXT TO the exported artifact, never over it:

```bash
cd /content/nsosyal-bstar/AI     # a commit containing training/m3_encoder/correct_metadata.py
RUN=/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/rule-v3-20260918-074806
python -m training.m3_encoder.correct_metadata correct \
  --artifact $RUN/artifact/m3-berturk-multihead-a-rule-v3-20260918-074806 \
  --out $RUN/artifact-corrected/m3-berturk-multihead-a-rule-v3-20260918-074806 \
  --expect-weights-sha256 41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145
```

## Standing rules

- The 500-row reference is evaluation only: never a training label, never a threshold source.
- The exported artifact directory on Drive is kept byte for byte; corrections are new directories.
- The test set was not used.
