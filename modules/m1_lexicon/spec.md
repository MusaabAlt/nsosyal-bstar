# m1_lexicon - morpheme-boundary profanity lexicon

Type: **signal** | Status: STUB - contract only, no detection logic yet.

## Purpose

High-precision lexical signal for explicit profanity (A1-A4), matched on morpheme boundaries on both the raw and the normalized channel, plus guard evidence that explains near-misses.

## What it catches

- Lexicon roots followed by a valid Turkish suffix chain (vowel harmony, consonant alternation, buffer letters) -> A1-A4 scores.
- A4 via entries tagged sacred; A3 via entries tagged as group slurs; A2 only from the morphology of the matched word itself (e.g. 2nd person agreement on the profane form); otherwise A1.
- SUBSTRING_COLLISION guard when a root occurs inside a known clean word (amca, sikke, psikoloji).
- HOMONYM guard when a surface form has both a profane and a clean reading; DUAL_REGISTER guard for entries tagged as friendly in informal register.

## What it deliberately does NOT catch

- Obfuscated spellings on the raw channel: m1 reads m2's normalized channel instead of doing fuzzy matching itself.
- Implicit abuse (C), sarcasm (D), threats or degradation without a lexicon word (B).
- Target resolution beyond the matched word's own morphology (m6 / m3 target head).

## Input / output contract

- Declares `provides = {`content`, `guards`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.best_text("raw")` and `ctx.best_text("normalized")`; lexicon artifact from `artifacts/` (hash in MANIFEST.md).
- Output: `content`: `ContentScore(code, score, source="m1_lexicon@raw|normalized")`; `guards`: SUBSTRING_COLLISION, HOMONYM, DUAL_REGISTER; `signals.hits`: [{root, surface, span, channel, suffixes}].
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Tokenize with a Turkish-aware regex; for each token parse root + suffix chain with a hand-written morphotactic automaton (stdlib).
- A match requires token == root + valid suffix chain. Never `token.startswith(root)`.
- Lexicon is versioned data (root, tags, register, known clean words sharing the prefix), not code.
- Optional build-time only: zeyrek (Python port of Zemberek morphology) to generate/validate inflection tables. Never at runtime.
- Score = per-entry certainty from the lexicon artifact; the decision layer thresholds it.

## Forbidden shortcuts

- **Substring match (`root in text`)** - fires on amca, ambulans, amir, ampul, sikke, psikoloji, klasik - the trap file exists for this.
- **`\b` regex word boundary as the only rule** - agglutinated forms are one token; boundaries must be morpheme boundaries.
- **`str.lower()`** - SIKINTI -> sikinti; use charsafe_text from m0.
- **Snowball/Porter-style stemming** - over-stems clean words onto profane roots.
- **Fuzzy / edit-distance matching** - on short roots it explodes FPR; de-obfuscation is m2's parallel channel.
- **Setting threshold/fired or choosing an action** - rule 4.

## Metric

Recall/precision/FPR for A1-A4 with bootstrap CIs, per channel; trap regressions; p50/p95 latency. Produced by `python -m modules.m1_lexicon.eval` into `eval/results/m1_lexicon.json`.

## Acceptance criteria

- Zero trap regressions (every collision trap).
- Precision CI lower bound reported for A1-A4 on dev.
- Normalized-channel contribution does not exceed `budgets.clean_to_dirty_flip_rate`.
- p95 latency within budget.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
