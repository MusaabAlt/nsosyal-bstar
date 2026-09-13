# m4_implicit - implicit abuse (C1-C5)

Type: **detection** | Status: STUB - contract only, no detection logic yet.

## Purpose

Detect implicit offensive speech - stereotype, inferiority attribution, coded language, incitement, defamation - with calibrated scores (threshold repair) and a model hardened against identity-term shortcuts (influence hardening).

## What it catches

- C1 stereotype, C2 inferiority attribution, C3 coded language, C4 incitement, C5 defamation.

## What it deliberately does NOT catch

- Explicit profanity or overt threats (m1, m3).
- Mere mention of a group, or counter-speech about a stereotype (guards suppress; the model must not learn identity terms as signal).
- Degrading sarcasm (m5).

## Input / output contract

- Declares `provides = {`content`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.signals["m3_encoder"]["embedding"]` per channel (never an import of m3); head weights + calibrators from `artifacts/`.
- Output: `content`: C1-C5 `ContentScore` with source `m4_implicit@raw|normalized`, scores calibrated.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Head on m3's pooled embedding (numpy inference).
- Threshold repair: per-class isotonic regression or temperature scaling (scikit-learn, offline) fit on a dev calibration fold, so thresholds in thresholds.yaml mean the same thing across classes; eval proposes candidate thresholds in eval/results, a human copies them.
- Influence hardening: estimate training-example influence (TracIn-style gradient similarity on the head) to find examples where identity terms alone drive C predictions; relabel/remove and add counterfactual identity-term swaps.
- Verify with a counterfactual set: swapping group names must not move scores.

## Forbidden shortcuts

- **Identity-term keyword lists as a detector** - a group mention is not a stereotype; fires on counter-speech and on the groups themselves.
- **Calibrating on test** - leaks; calibration uses a dev fold only.
- **Writing thresholds.yaml from code** - threshold derivation is a reviewed protocol, not a side effect.
- **Importing m3** - rule 2; read embeddings from ctx.signals.
- **Treating missing m3 signals as clean** - no silent failures; return nothing and add a note (e.g. after a fast path).

## Metric

C1-C5 recall/precision/FPR with bootstrap CIs; expected calibration error before/after repair; counterfactual identity-swap flip rate; latency. Produced by `python -m modules.m4_implicit.eval` into `eval/results/m4_implicit.json`.

## Acceptance criteria

- ECE after repair reported and lower than before on dev.
- Counterfactual flip rate reported with CI.
- Zero trap regressions; p95 latency within budget.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
