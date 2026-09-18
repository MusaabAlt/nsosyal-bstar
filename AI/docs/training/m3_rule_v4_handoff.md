# Colab handoff — m3 multi-head retraining on pseudo-label **rule v4** (binary + A)

**State: READY_FOR_COLAB — not run.** Prepared 2026-09-18 after M1-PREC-1
(`protocols/m1_positive_matching_precision_protocol.md`) was pre-registered, implemented (m1 0.3.0)
and the A pseudo-labels regenerated as rule v4 (`c234cc0`). No GPU was used to prepare it. The
rule-v3 candidate (`m3-berturk-multihead-a-rule-v3-20260918-074806`, weights `41d98d7f…`) stays
the historical control: it is never overwritten, and its run directory is never written to.

## 1. What changes versus the rule-v3 run — and what does not

**Only the A pseudo-label files change** (same paths, rule-v4 bytes). The code path, base model,
hyperparameters, seed, frozen split, corpus, checkpoint rule and the evaluation-only use of the
500-row reference are identical to the rule-v3 run (`docs/training/runs/m3-berturk-multihead-a-rule-v3-20260918-074806.md`),
so the two candidates stay directly comparable.

| | rule-v3 run (history) | rule-v4 run (this handoff) |
|---|---|---|
| A supervision (train) | 1,528 positives / 26,992 | **1,177** positives / 26,992 |
| A agreement file (dev) | 257 positives / 4,764 | **217** positives / 4,764 |
| label bytes | git `7f5e003`: train `78d845a5…`, dev `8f4dcdfe…` | git `c234cc0`: train `0bfbd731…`, dev `50a94ba5…` |
| why | rule v3 taxonomy, m1 0.1.x matching | same taxonomy; m1 0.3.0 accepts a family-A match only as a real word of its root |

Row-by-row changes: `AI/eval/derived/m1_lexicon_rule_v4_flips.{json,md}` (train 360 positive →
negative and 9 negative → positive; dev 44 and 4).

## 2. Exact inputs

| input | value |
|---|---|
| repository | `MusaabAlt/nsosyal-bstar`, branch `audit/m1-m6` |
| **commit to check out** | **`c234cc0de4e9b303767548cac2b85e35fe7f2f0e`** (rule-v4 labels; code identical to `525bbff`; any later commit on the branch changes documents only and may be used if the label digests below match) |
| TRAIN A labels | `AI/eval/derived/m1_lexicon_train_seed42.json` — sha256 `0bfbd73118c661bbf41468da2c6ee951eaf9f591e8a2d81bfb221a14054504f2` — 26,992 rows, `a_label` 1 on 1,177, 0 masked, `a_label_rule.version` 4, `taxonomy_version` 3, taxonomy digest `5b8ebe315cd2217c4decc8b0180eb2027a62aa2718405356c2066a29a0375ce5` |
| DEV A labels (agreement only) | `AI/eval/derived/m1_lexicon_dev_seed42.json` — sha256 `50a94ba513b33e9b09f305af4619aa197a7c4311cca471a3c623978eab41a0dd` — 4,764 rows, `a_label` 1 on 217 |
| corpus (binary gold + text) | Drive `MyDrive/nsosyal-train/data/coltekin/offenseval-tr-training-v1.tsv`, sha256 `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa`, 31,756 rows |
| frozen split | `diagnosis/data/splits/split_seed42.json` (in the clone, repo root), sha256 `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2`, seed 42, dev fingerprint `034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4`, train fingerprint `29a2ea8bdc9730bf7a16f6c7e21d69dd3f33648b923f2829e8e2797876bbe931`; train 26,992 (OFF 5,211) / dev 4,764 (OFF 920) |
| evaluation reference (evaluation only) | Drive `MyDrive/nsosyal-train/labels/a_dev_ai_assisted_adjudicated.jsonl` + `.reference_provenance.json` — the 500-row AI-assisted, human-adjudicated dev reference, kind `ai-assisted-human-adjudicated`; never a training label, never a checkpoint criterion |
| base model | `dbmdz/bert-base-turkish-cased` (BERTurk), initialised from the base checkpoint |
| software | Colab Python 3.11–3.13; the preinstalled CUDA torch; `transformers==5.15.0` |
| locked test set | not on the mounted Drive, not read by anything here |

## 3. Hyperparameters (identical to the rule-v3 run)

| setting | value |
|---|---|
| epochs | 3 |
| batch size | 32 (`--grad-accum 1`) |
| learning rate | 2e-5, linear warmup 10 %, linear decay |
| weight decay | 0.01 |
| max grad norm | 1.0 (trainer default) |
| max length | 128 |
| precision | `--fp16` |
| seed | 42 |
| heads | binary + A (B, C untrained: no labels) |
| **checkpoint selection** | best **dev binary macro-F1** (`training/m3_encoder/train.py`, the `if f1 > best_f1` branch). The 500-row reference is evaluated for `dev_eval.json` only and has no path into selection |

## 4. Run id and artifact id

```text
RUN_ID      = rule-v4-<YYYYMMDD-HHMMSS>        (UTC time of the start, set by the cell)
RUN_DIR     = /content/drive/MyDrive/nsosyal-train/runs/m3_multihead/$RUN_ID
ARTIFACT_ID = m3-berturk-multihead-a-$RUN_ID   (e.g. m3-berturk-multihead-a-rule-v4-20260919-093000)
artifact    = $RUN_DIR/artifact/$ARTIFACT_ID/  (weights.pt, heads.json, config.json, tokenizer files,
              sha256.txt, MANIFEST_ROW.md, dev_eval.json)
```

The cell refuses an existing run directory. It never writes under `rule-v3-20260918-074806/` or the
first run's `2026-09-18/`.

## 5. Colab cells (GPU runtime, A100 or L4)

**Cell 1 — mount Drive, clone and check out the exact commit** (needs the `GH_TOKEN` secret,
fine-grained, Contents: read; the token-as-username form is rejected by GitHub):

```python
from google.colab import drive, userdata
import os, subprocess
drive.mount("/content/drive")
token = userdata.get("GH_TOKEN")
assert token, "GH_TOKEN secret missing or notebook access disabled"
repo = "/content/nsosyal-bstar"
url = f"https://x-access-token:{token}@github.com/MusaabAlt/nsosyal-bstar.git"
if not os.path.isdir(os.path.join(repo, ".git")):
    subprocess.run(["git", "clone", "-q", url, repo], check=True)
else:
    subprocess.run(["git", "-C", repo, "remote", "set-url", "origin", url], check=True)
subprocess.run(["git", "-C", repo, "fetch", "-q", "origin"], check=True)
TARGET = "c234cc0de4e9b303767548cac2b85e35fe7f2f0e"
subprocess.run(["git", "-C", repo, "checkout", "-q", TARGET], check=True)
head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
assert head == TARGET, head
print("HEAD", head)
```

**Cell 2 — pre-flight checks and training** (every check stops the cell on a mismatch):

```bash
%%bash
set -euo pipefail
cd /content/nsosyal-bstar/AI
test "$(git rev-parse HEAD)" = "c234cc0de4e9b303767548cac2b85e35fe7f2f0e" || { echo "ERROR: wrong commit"; exit 1; }
export NSOSYAL_DATA=/content/drive/MyDrive/nsosyal-train/data
LABELS=/content/drive/MyDrive/nsosyal-train/labels
REFERENCE="$LABELS/a_dev_ai_assisted_adjudicated.jsonl"
V3=/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/rule-v3-20260918-074806/artifact/m3-berturk-multihead-a-rule-v3-20260918-074806/weights.pt

# rule-v4 labels, byte-exact; corpus and split digests
sha256sum -c - <<EOF
0bfbd73118c661bbf41468da2c6ee951eaf9f591e8a2d81bfb221a14054504f2  eval/derived/m1_lexicon_train_seed42.json
50a94ba513b33e9b09f305af4619aa197a7c4311cca471a3c623978eab41a0dd  eval/derived/m1_lexicon_dev_seed42.json
8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa  $NSOSYAL_DATA/coltekin/offenseval-tr-training-v1.tsv
73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2  ../diagnosis/data/splits/split_seed42.json
41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145  $V3
EOF
python - <<'PY'
import json
for split, positives in (("train", 1177), ("dev", 217)):
    d = json.load(open(f"eval/derived/m1_lexicon_{split}_seed42.json", encoding="utf-8"))
    rule = d["a_label_rule"]
    assert (rule["version"], rule["taxonomy_version"], rule["matching_protocol"]["id"]) == (4, 3, "M1-PREC-1"), rule
    assert d["counts"]["a_label"] == positives and d["counts"]["a_label_null"] == 0, (split, d["counts"])
print("rule-v4 labels verified")
PY
test -f "$REFERENCE" && test -f "$LABELS/a_dev_ai_assisted_adjudicated.reference_provenance.json"
echo "pre-flight OK"

pip install -q transformers==5.15.0
RUN_ID="rule-v4-$(date -u +%Y%m%d-%H%M%S)"
RUN_DIR="/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/$RUN_ID"
ARTIFACT_ID="m3-berturk-multihead-a-$RUN_ID"
test ! -e "$RUN_DIR" || { echo "ERROR: run directory exists: $RUN_DIR"; exit 1; }
echo "RUN_ID=$RUN_ID  ARTIFACT_ID=$ARTIFACT_ID"

python -m training.m3_encoder.train \
  --out "$RUN_DIR" \
  --artifact-id "$ARTIFACT_ID" \
  --labels-a eval/derived/m1_lexicon_train_seed42.json \
  --labels-a eval/derived/m1_lexicon_dev_seed42.json \
  --labels-a-reference "$REFERENCE" \
  --labels-a-reference-kind ai-assisted-human-adjudicated \
  --epochs 3 --batch-size 32 --lr 2e-5 --max-len 128 --warmup-ratio 0.1 --weight-decay 0.01 --seed 42 --fp16

echo "41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145  $V3" | sha256sum -c -   # rule-v3 still untouched
find "$RUN_DIR/artifact" -type f -exec sha256sum {} \; | sort -k2
```

Disconnect: rerun Cell 1, then Cell 2 with the SAME `RUN_ID` and `--resume` (edit the `RUN_ID=` line
to the printed value and delete the `test ! -e` line for that rerun only).

## 6. What to return and how it is judged (no decision is taken inside the run)

- Return: the printed log, the artifact directory's file list with sha256, `heads.json`,
  `dev_eval.json`. `heads.json` must record `label_sources.a` = the two digests of §2.
- Binary acceptance (handoff `m3_encoder.md` §28): dev macro-F1 not below the baseline's 0.8271
  [0.8139, 0.8405] by more than the CI width; compare with the rule-v3 candidate's 0.8247.
- A head: reported against the 500-row AI-assisted, human-adjudicated reference at the 0.5
  reporting point, next to the rule-v3 candidate's tp 32 / fp 1 / fn 7 / tn 460 on the same rows —
  as "AI-assisted, human-adjudicated reference metrics", never as human-oracle accuracy.
- NOT part of this handoff: deriving any threshold, choosing the new candidate's A operating policy
  (A-OP-1 is scoped to the rule-v3 candidate; a policy for the rule-v4 candidate is an owner
  decision), promotion, `thresholds.yaml` or `MANIFEST.md` changes, M4 / M5.
