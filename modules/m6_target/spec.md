# m6_target - target resolution and doxing patterns

Type: **signal** | Status: STUB - contract only, no detection logic yet.

## Purpose

Resolve who a post is aimed at (Axis 3) with cheap rules, detect doxing (B4), and provide the SELF_DIRECTED and NON_HUMAN_TARGET guards before the fast-path check.

## What it catches

- Individual target: 2nd person agreement (-sın/-sin/-sun/-sün, -sınız), sen/siz/sana/seni, vocatives, @mentions.
- Group target: group noun gazetteer (nationality, religion, ethnicity, party, profession) with plural/collective forms.
- SELF_DIRECTED: 1st person copula on the insult ("ne salağım").
- NON_HUMAN_TARGET: object is a non-human gazetteer noun (film, maç, hava, trafik, bilgisayar).
- B4 doxing: TC kimlik no (checksum-validated), +90 5xx mobile numbers, TR IBAN (mod-97), address markers (Mah., Cad., Sok., No:), plates.

## What it deliberately does NOT catch

- Whether the post is abusive at all.
- Coreference across a thread.
- Named-entity recognition with a model.

## Input / output contract

- Declares `provides = {`target`, `content`, `guards`}`; anything else it returns is dropped by the pipeline.
- Input: `ctx.best_text("raw")`; gazetteers from `artifacts/`.
- Output: `target: TargetResult`; `content`: B4 `ContentScore` source `m6_target@raw`; `guards`: SELF_DIRECTED, NON_HUMAN_TARGET; evidence with PII MASKED.
- Never sets `threshold`, `fired`, `active` or `suppressed`; never mutates `ctx.text`.

## Approach and tools

- Standard library regex + suffix rules; gazetteers as data artifacts.
- TC kimlik checksum: d10 = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) mod 10, d11 = sum(d1..d10) mod 10.
- IBAN: ISO 13616 mod-97 check.
- Doxing score rises with co-occurrence of an identifier and a person reference or disclosure verb.

## Forbidden shortcuts

- **Any 11-digit number = TC kimlik** - order numbers and IDs collide; the checksum is mandatory.
- **Emitting raw PII in evidence, signals or notes** - results are logged and stored; mask all but the last 2 digits.
- **"sen" as proof of an individual target** - generic second person in proverbs and advice.
- **Inferring the author's group membership** - out of scope and a privacy harm.

## Metric

Target accuracy and macro-F1 over TargetType; B4 recall/precision/FPR with bootstrap CIs; guard precision; PII-masking check (zero unmasked identifiers in output); latency. Produced by `python -m modules.m6_target.eval` into `eval/results/m6_target.json`.

## Acceptance criteria

- PII-masking unit test passes.
- Zero trap regressions; p95 latency within budget.
- B4 metrics reported with CIs.
- Unit tests pass; `spec.md` is up to date; see the checklist in CONTRIBUTING.md.
