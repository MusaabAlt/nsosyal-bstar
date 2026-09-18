# BLOCKER — m1 matching precision on the rule-v3 POSITIVE roots (label noise)

- **Component:** `m1_lexicon` matching of the 17 rule-v3 POSITIVE (family-A) roots; the A-head
  pseudo-labels derived from it (`eval/derived/m1_lexicon_{train,dev}_seed42.json`)
- **State:** OPEN — found 2026-09-18 during the runtime-routing review, deliberately NOT addressed
  by M1-ROUTE-1 (`protocols/m1_runtime_routing_protocol.md` §5 scopes its fixes to EXCLUDED roots
  so that every A pseudo-label stays identical)
- **Written:** 2026-09-18

## What was found (no fix applied)

Some rule-v3 positive labels rest on spurious m1 matches, not on a POSITIVE root written as a
word. Measured on the frozen splits during the review (upper bounds: a row is counted when it has
no plain-word POSITIVE match; some of these rows are legitimate, e.g. the hashtags `#orospu`,
`#gavat`, or genuine spaced obfuscation):

| mechanism | examples | train rows | dev rows |
|---|---|---|---|
| digit tokens read as leet | `6-7`, `67`, `59`, `566` → `göt` / `sg` | ~46 | ~5 |
| edge punctuation defeating the clean-word rules | `...Amin`, `(Amin)`, `#AMİN`, `ama!`, `‘amca`, `sıkı.`, `sıkma...` → an obscene root | ~25 | ~7 |
| letters split across words | `A mı`, `ama en`, `A M` → `am` | ~68 | ~6 |
| total rows without a plain-word POSITIVE match | | ≤ 140 of 1,528 positives | ≤ 18 of 257 |

They also reach users at runtime as family-A hits (e.g. `A mı`, `6-7` → A1).

## Why it is a separate task

Any fix changes A pseudo-labels (1 → 0 on the spurious rows), so it needs its own pre-registered
m1 protocol, a row-by-row label report, and an open update of the history test that pins the
rule-v3 artifact's training labels (`tests/test_m1_lexicon_labels.py`). The rule-v3 artifact
(`m3-berturk-multihead-a-rule-v3-20260918-074806`) was trained on these labels; its measured false-
positive rate on the AI-assisted, human-adjudicated reference is 1 / 461, so the head did not
visibly learn the noise. Whether the corrected labels justify a later retraining is an owner
decision after the fix is measured.

## What unblocks it

A pre-registered matching-precision protocol for POSITIVE roots (candidate rules: a digit-only
token is never a root; the clean-word rules apply after stripping edge punctuation; the
split-across-words rule of M1-ROUTE-1 §5 extended to POSITIVE roots), committed before the code,
then the regeneration and the label-change report.
