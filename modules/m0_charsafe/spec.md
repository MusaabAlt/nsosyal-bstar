# m0_charsafe - character-level safety layer

Type: **representation** | Status: Implemented (reference module).

## Purpose

Give every downstream module a text in which invisible characters, cross-script lookalikes and the Turkish I casing problem can no longer hide or create a match. This is the reference implementation of the module contract.

## What it catches

- Unicode Cf/Cc characters (zero-width space/joiner, soft hyphen, bidi marks, BOM, control bytes) -> ZERO_WIDTH, with higher confidence when they split a word.
- Cyrillic/Greek lookalikes inside Latin tokens, or tokens made only of lookalikes -> HOMOGLYPH.
- Turkish casing: I -> ı, İ -> i, decomposed I/i + U+0307 -> i -> DOTLESS_I evidence (high confidence only for a capital I inside a lowercase word).

## What it deliberately does NOT catch

- Leet, spacing, punctuation splits, repeats, deasciified text: interpretation, belongs to m2_deobf's parallel channel.
- ASCII 'I' meant as 'İ' ("Istanbul"): that is DEASCII, m2's job; m0 applies Turkish rules literally.
- NFKC folding (fullwidth, ligatures): normalization, not safety.
- Genuine foreign-script words ("мир"): left untouched.
- Any content, target, guard or decision.

## Input / output contract

- Declares `provides = {`charsafe_text`, `form`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.text` (original).
- Output: `charsafe_text`; `form.patterns` (ZERO_WIDTH, HOMOGLYPH, DOTLESS_I; spans in ORIGINAL offsets); `signals = {offsets, invisible_removed, homoglyphs_mapped}` where `offsets[i]` is the original index of `charsafe_text[i]`.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Pass 1: strip maximal runs of Cf/Cc except \t \n \r; keep a ZWJ that joins emoji parts; one pattern per run.
- Pass 2: only if a non-ASCII, non-Turkish letter exists, map a small hand-checked confusables table per token, and only for mixed-script tokens or tokens made entirely of lookalikes.
- Pass 3: Turkish-aware lowercasing; one DOTLESS_I pattern per token where Turkish and default rules diverge.
- Standard library only (`unicodedata`). Offsets tracked through every pass.

## Forbidden shortcuts

- **`str.lower()` / `casefold()`** - turns SIKINTI into sikinti (a profanity-prefix collision) and İ into i + U+0307, breaking lexicon lookups.
- **Full Unicode confusables.txt** - maps letters of real languages and can touch Turkish letters; the table must stay small and visual-twin only.
- **Mapping confusables in pure-ASCII text or pure foreign-script tokens** - cannot contain an attack by construction / rewrites honest foreign words.
- **Deleting \n, \t, \r** - glues words into new collisions and destroys quote structure needed by QUOTE_COUNTERSPEECH.
- **Unidecode / NFKD accent stripping** - erases ç ğ ı ö ş ü, i.e. turns Turkish into deasciified text and creates collisions.

## Metric

Recall/precision/FPR over {ZERO_WIDTH, HOMOGLYPH, DOTLESS_I} with bootstrap CIs; exact-match rate of `charsafe_text` on items with `expect`; trap regressions; p50/p95 latency. Produced by `python -m modules.m0_charsafe.eval` into `eval/results/m0_charsafe.json`.

## Acceptance criteria

- `charsafe_text` exact match = 1.0 on the dev fixture.
- Zero trap regressions, including SIKINTI casing traps.
- p95 latency within `budgets.module_latency_p95_ms.m0_charsafe`.
- `len(signals.offsets) == len(charsafe_text)` for every item.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
