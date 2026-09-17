# Colab Pro+ handoff — m5_sarcasm: sequential transfer for D1 on its own small model

State: **BLOCKED_BY_DATA** — the entry gate (`docs/blockers/m5_sarcasm_corpus_gate.md`, m5 spec
§2) is unresolved: the Turkish sarcasm corpus is not named, not requested, not obtained, and no
D1-labelled or control data exists. The code (`training/m5_sarcasm/train.py`) is complete and
smoke-tested on CPU; this handoff runs unchanged once the data exists.

## 1. Purpose

`D1` — abuse delivered through a literally positive sentence (polarity inversion). Sequential
transfer: pre-train on sarcasm, fine-tune on D1 (spec §6). Own artifact, own thresholds row,
never a head on m3 (ADR-003).

## 2. Consumer

`AI/modules/m5_sarcasm/module.py` (to be written against the artifact format below): loads
`weights.pt` + `heads.json` + tokenizer, verifies sha256, publishes one `ContentScore(D1, p, "m5_sarcasm@raw")`
per post from `ctx.text` (raw punctuation and casing carry the markers, spec §7).

## 3. Architecture / base checkpoint

- Base: a **small or distilled** Turkish encoder (spec §6 constraint; the choice and its
  measured latency against `budgets.module_latency_p95_ms.m5_sarcasm` are the m5 owner's).
  Candidates to measure, in order: `dbmdz/distilbert-base-turkish-cased` (66 M parameters),
  `dbmdz/electra-small-turkish-cased-discriminator` (14 M). Do not use `bert-base` (a second full
  pass per request doubles CPU latency, spec §6).
- Two linear heads on the pooled output: `sarcasm` (stage 1), `d1` (stage 2); only `d1` is
  published.

## 4. Datasets

| set | format | role |
|---|---|---|
| sarcasm / irony corpus (gate outcome) | jsonl `{"text","label"}` 1 = sarcastic | stage 1 |
| D1 train / dev | jsonl `{"text","label","inversion_span":[s,e]}`; every positive carries the span (spec §11; the trainer refuses otherwise) | stage 2 |
| benign-sarcasm control set (objects, weather, software, traffic, a match result), size comparable to the positives | jsonl `{"text","label":0}` | precision gate (spec §8, §10) |
| sincere-praise negatives, C-boundary negatives, A-boundary cases, reported-speech cases | inside D1 train / dev with label 0 (A-boundary: label 0 for D1; the A code is m1's) | negatives (spec §11) |

## 5. Obtaining them

Corpus: request from its authors (owner action; the name is recorded in the spec §2 when
identified). D1 slice and control set: in-house annotation under the polarity-inversion rule
(spec §5) with the guideline template; agreement reported per function.

## 6. Licences

Recorded in `modules/m5_sarcasm/GATE_RECORD.md` (name, version, size, date, licence); copied into
the artifact by `--gate-record`. Never commit corpus text.

## 7. Drive layout

```
MyDrive/nsosyal-bstar/data/sarcasm/<corpus>.jsonl
MyDrive/nsosyal-bstar/labels/d1_train.jsonl  d1_dev.jsonl  d1_control.jsonl
MyDrive/nsosyal-bstar/runs/m5_sarcasm/<date>/
```

## 8–11. Preprocessing, labels, splits, leakage

Raw text, no normalisation (spec §11 "raw-text sensitivity"). D1 label 1 only with an inversion
span. Train / dev split of the D1 slice fixed by file, never re-split; the control set is never
used for training a threshold. No overlap between the sarcasm corpus and the D1 dev rows
(checked by text hash in the trainer when both are given — to add when data exists).

## 12–17. Seeds, versions, install, runtime, resources

Seed 42. `torch==2.11.0+cu128`, `transformers==5.15.0`. Install and runtime as `m3_encoder.md`
§15–16. A distilled model at batch 32 needs < 2 GB GPU memory; minutes per stage.

## 18. Training command

```bash
cd /content/nsosyal-bstar/AI
python -m training.m5_sarcasm.train --out /content/drive/MyDrive/nsosyal-bstar/runs/m5_sarcasm/$(date +%F) \
  --base dbmdz/distilbert-base-turkish-cased \
  --stage1 /content/drive/MyDrive/nsosyal-bstar/data/sarcasm/<corpus>.jsonl \
  --stage2-train /content/drive/MyDrive/nsosyal-bstar/labels/d1_train.jsonl \
  --stage2-dev   /content/drive/MyDrive/nsosyal-bstar/labels/d1_dev.jsonl \
  --control      /content/drive/MyDrive/nsosyal-bstar/labels/d1_control.jsonl \
  --gate-record  modules/m5_sarcasm/GATE_RECORD.md --epochs1 3 --epochs2 5 --batch-size 32 --lr 2e-5 --seed 42 --fp16
```

## 19–26. Hyperparameters

Stage 1: 3 epochs, lr 2e-5, warmup 10 %, weight decay 0.01, BCE loss. Stage 2: 5 epochs, same;
no class weighting (the control set gates precision instead); checkpoint = final stage-2 weights
(small data; report every epoch's dev numbers in `heads.json`).

## 27. Metrics

Precision on the control set **first** (with CI), then D1 recall / precision on dev with CIs,
per-epoch history; the D1↔C confusion count is computed by the module's eval once C fixtures
exist. Reporting point 0.5; the `D1` threshold row is derived on dev afterwards.

## 28. Acceptance

Control-set precision above the gate the owner writes into the protocol before the run; results
labelled exploratory if the fallback dataset was used; agreement number published however low
(spec §12).

## 29–33. Outputs

`<out>/artifact/m5-sarcasm-d1-<date>/` with `weights.pt`, `heads.json` (meta + final metrics),
tokenizer files, `sha256.txt`, `GATE_RECORD.md`. Place under `AI/artifacts/m5_sarcasm/<id>/`;
add the MANIFEST row (`m5-sarcasm` placeholder row exists) with the real sha256.

## 34. Threshold after training

Derive the `D1` row on dev (`protocols/templates/threshold_derivation.md`); the m5 owner may
propose it (CONTRIBUTING step 7). Measure latency on the demo machine against the budget.

## 35. Verification

```bash
cd AI && python -m unittest modules.m5_sarcasm.test_unit && python -m modules.m5_sarcasm.eval
```

## 36–37. Failure and stages

Trainer refuses D1 positives without an inversion span — fix the labels, not the check.
Stages: setup 5 min · stage 1 ≈ 5 min · stage 2 ≈ 3 min · eval 1 min.

## Smoke test (CPU)

```bash
cd AI && python -m training.m5_sarcasm.train --out /tmp/m5smoke --base artifacts/m3_encoder/tokenizer \
  --stage2-train <8-row jsonl> --stage2-dev <same> --smoke 8
```
(random-initialised encoder from the local BERTurk config; proves the code path only).
