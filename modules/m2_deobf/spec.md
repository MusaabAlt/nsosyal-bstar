# m2_deobf - parallel de-obfuscation channel

Type: **representation** | Status: STUB - contract only, no detection logic yet.

## Purpose

Produce a SECOND, de-obfuscated reading of the text as a parallel channel, and describe the obfuscation (Axis 2). It never replaces the raw channel: blind normalization lowered F1 on Turkish.

## What it catches

- LEET, SPACED, PUNCT_SPLIT, REPEAT, CHAR_DROP, WORD_MERGE, ABBREV, DEASCII, VOWEL_DROP, SUFFIX_ON_MASKED, DIALECT, EMOJI_SUB, PHONETIC.

## What it deliberately does NOT catch

- ZERO_WIDTH, HOMOGLYPH, DOTLESS_I (m0).
- Whether the de-obfuscated text is offensive: no content scores, ever. Obfuscation is never a content category.

## Input / output contract

- Declares `provides = {`normalized_text`, `form`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.best_text("raw")` (charsafe text).
- Output: `normalized_text`; `form.patterns` with spans in ORIGINAL offsets (via m0's `signals.offsets`); `signals = {alignment, alternatives}` keeping ambiguous candidates.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Per token, generate candidates (leet table, repeat collapse >=3 -> 2, single-letter run joining, punctuation removal inside tokens, deasciification, vowel restoration).
- Rank candidates with a Turkish unigram frequency list and dictionary membership (data artifacts), pick the best path, keep top alternatives in signals.
- Deasciification with a port of the pattern-based Turkish deasciifier (Yuret & de la Maza pattern tables), standard library only.
- Emit a FormPattern for every applied rewrite with the rule as evidence.

## Forbidden shortcuts

- **Overwriting `text` or `charsafe_text`** - blind normalization lowered F1 on Turkish; the raw channel must stay intact and both channels are scored.
- **Collapsing every repeat to one letter** - Turkish has legitimate doubles (saat, dikkat, anne, hakkı).
- **Unconditional deasciification** - ambiguous forms (sik/şık, kurt/Kürt) flip meaning; keep alternatives.
- **Spell-correcting toward the profanity lexicon** - manufactures hits from clean words (sikke, amca).
- **Joining any single letters across a sentence** - merges real one-letter words; join only uniform runs.
- **Emitting content scores** - m2 describes form only.

## Metric

Recall/precision/FPR per FormCode with bootstrap CIs; `clean_to_dirty_flip_rate` (clean dev items whose pipeline verdict changes when the normalized channel is added); trap regressions; latency. Produced by `python -m modules.m2_deobf.eval` into `eval/results/m2_deobf.json`.

## Acceptance criteria

- `clean_to_dirty_flip_rate` within budget, measured at pipeline level on dev.
- Zero trap regressions.
- Raw channel byte-identical before/after the module (unit test).
- p95 latency within budget.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
