# m3_encoder - shared BERTurk encoder with three heads

Type: **detection** | Status: STUB - contract only, no detection logic yet.

## Purpose

One contextual encoder forward pass per channel feeding three heads: content (A1-A4, B1-B5), target (Axis 3) and contextual guards. Publishes pooled embeddings so m4/m5 never need their own encoder.

## What it catches

- Content head: A1-A4 and B1-B5 multi-label scores, including abuse without lexicon words.
- Target head: individual / group / non_human / none.
- Guard head: NEGATION, QUOTE_COUNTERSPEECH, METADISCUSSION scores.

## What it deliberately does NOT catch

- C1-C5 (m4) and D1 (m5) - they consume this module's embeddings from signals.
- Obfuscation description (m0/m2).
- Thresholds on any head.

## Input / output contract

- Declares `provides = {`content`, `target`, `guards`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.best_text("raw")` and, when different, `ctx.best_text("normalized")`; model + tokenizer from `artifacts/`.
- Output: `content` with source `m3_encoder@raw|normalized`; `target`; `guards`; `signals = {embedding: {raw: [...], normalized: [...]}, truncated: bool}`.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Base model: dbmdz/bert-base-turkish-cased (BERTurk), fine-tuned offline with transformers + torch, heads trained jointly on one encoder.
- Export to ONNX and apply dynamic int8 quantization (onnxruntime) for CPU inference; load with local files only.
- Run on both channels, tag every score with its channel; the decision layer fuses.
- Long posts: head+tail windows, truncation recorded in notes/signals.

## Forbidden shortcuts

- **One encoder per head** - triples CPU latency; heads share one forward pass.
- **Downloading from the model hub at inference** - the system is offline; weights come from artifacts/ with a MANIFEST hash.
- **Lowercasing input or using an uncased model** - BERTurk is cased and str.lower() breaks Turkish I.
- **Training on normalized text only** - distribution shift on the raw channel; channels must stay separate.
- **sigmoid >= 0.5 inside the module** - rule 4: thresholds live in decision/thresholds.yaml.
- **Silent truncation** - no silent failures; report it.

## Metric

Per head: recall/precision/FPR (content, guards) and accuracy/macro-F1 (target) with bootstrap CIs, per channel; clean_to_dirty_flip_rate; CPU p50/p95 latency. Produced by `python -m modules.m3_encoder.eval` into `eval/results/m3_encoder.json`.

## Acceptance criteria

- Model artifact hash matches artifacts/MANIFEST.md.
- Zero trap regressions.
- p95 latency within budget on CPU, single process.
- Content metrics reported with CIs for both channels.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
