# m5_sarcasm - degrading sarcasm (D1)

Type: **detection** | Status: STUB - contract only, no detection logic yet.

## Purpose

Detect sarcasm used to degrade (D1) via sequential transfer: learn sarcasm first from a sarcasm corpus, then specialise to degrading sarcasm. Also provides FRIENDLY_BANTER guard evidence.

## What it catches

- D1 degrading sarcasm.
- FRIENDLY_BANTER guard: ironic but non-degrading exchanges.

## What it deliberately does NOT catch

- Sarcasm that degrades no one: sarcasm is not D1.
- Explicit abuse (A/B) and implicit stereotypes (C).

## Input / output contract

- Declares `provides = {`content`, `guards`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.signals["m3_encoder"]["embedding"]` per channel; head weights from `artifacts/`.
- Output: `content`: D1 `ContentScore` with source `m5_sarcasm@raw|normalized`; `guards`: FRIENDLY_BANTER.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Stage 1: train a head on m3 embeddings on a Turkish sarcasm/irony corpus (choice, license and hash recorded in artifacts/MANIFEST.md).
- Stage 2: continue training on D1 labels (sequential transfer); report the ablation against stage-2-only training.
- Inference with numpy; training offline.

## Forbidden shortcuts

- **Equating sarcasm with D1** - irony is not abuse; D1 requires degradation.
- **Emoji / punctuation heuristics** - "🙂", "(!)", "!!!" are style, not evidence; they fire on friendly posts.
- **Skipping stage 1** - the D1 set is small; transfer is the method.
- **Leaking sarcasm-corpus test items into D1 dev** - inflates transfer gains.
- **Importing m3** - rule 2; read embeddings from ctx.signals.

## Metric

D1 recall/precision/FPR with bootstrap CIs; stage-1 transfer ablation; FRIENDLY_BANTER guard precision; latency. Produced by `python -m modules.m5_sarcasm.eval` into `eval/results/m5_sarcasm.json`.

## Acceptance criteria

- Transfer ablation reported with CIs.
- Zero trap regressions; p95 latency within budget.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
