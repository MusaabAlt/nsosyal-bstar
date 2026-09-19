# BLOCKER — m1 `A4` sacred-concept extension needs an owner-approved root table

- **Component:** `m1_lexicon`, code `A4` (profanity against the sacred), spec §2, §3, §4.3, §6, §8
- **State:** BLOCKED_BY_DATA (content knowledge; not an engineering gap)
- **Written:** 2026-09-17

## What the spec requires

- `A4` content scores from a **sacred-concept extension** of the terlik root list (spec §4.3),
  "document every addition with its source".
- A committed **sacred-concept table** with a source for each added root (spec §8), and a
  **growth table**: how many roots were added and how much `A4` recall moved (spec §6).
- `A4` fixtures (spec §7). `A4` is concept-based, never target-assigned (ADR-005).

## Why this cannot be built by engineering alone

The extension is a list of Turkish profane expressions built on sacred or religious concepts.
Which expressions count, and which are ordinary religious language, is exactly the false-positive
risk the spec warns about in `karaliste` (`allah`, `allahsız` flagged as profanity, spec §5). The
only sourced pointer in the repository is a community issue thread ("swearing with sacred concepts
is common in some regions"); no list, no examples and no annotation guideline exist in the repo,
and the project's own guideline template (`protocols/templates/annotation_guideline.md`) requires a
sealed definition before labelling. Inventing the list would put religious language in the
profanity lexicon on the assistant's authority.

## Exactly what is needed from the owner

1. **The table**, as `artifacts/m1_lexicon/a4_sacred_concepts.tsv`, one row per expression:
   `expression | reading (why it is profane, not devotional) | source (URL / corpus row / informant) | date`.
   Roots must be usable by the morpheme-boundary matcher: give the root form and, where the
   expression is multi-word, the exact phrase.
2. **The negative list**: devotional or ordinary uses of the same concepts that must NOT fire
   (`inşallah`, `Allah korusun`, `kitap okudum` …), at least as many rows as the positives.
3. **The licence** of every source (spec §8: licence of every list recorded in the README).
4. **The guideline** entry: the one-line rule that separates `A4` from `A1` and from clean
   religious speech, written into `protocols/` before any `A4` number (CONTRIBUTING step 7).

## What is already prepared on the engineering side

- The matcher integration point: m1's `_scan` handles a root list with suffix-aware matching
  through terlik; an extension list is loaded from `artifacts/` with a sha256 row in
  `artifacts/MANIFEST.md` once the table exists (CONTRIBUTING step 4).
- The eval harness reports per-code recall / precision / FPR with CIs, so the growth table is a
  before/after pair of `A4` rows.

## What happens meanwhile

`A4` stays absent from m1's output; every `A4` row in `thresholds.yaml` stays a placeholder;
`eval/implementation_status.json` lists it under `not_built` so no report can read as covering it.
