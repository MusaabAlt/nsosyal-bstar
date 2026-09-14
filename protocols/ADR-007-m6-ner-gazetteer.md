# ADR-007 — m6 named entities: gazetteer plus morphology for v1

- **Status:** accepted
- **Date:** 2026-09-14
- **Decided by:** project owner (open question written into m6's spec)
- **Scope:** `modules/m6_target/spec.md`

## Context

m6's doxing layer needs named entities (persons, places, institutions). The spec
listed three candidates - a gazetteer with morphological analysis, VNLP's Turkish
NER, and BERTurk-based NER models - and a note asking for a decision before the
m6 owner starts. That note also read project rule 6 as confining heavy
dependencies to one module (m3). That reading is wrong: CLAUDE.md and
`modules/README.md` say heavy dependencies belong to the module that needs them,
in its own `requirements.txt`, and `tests/test_architecture.py` accepts
dependencies a module declares.

## Decision

**Gazetteer plus morphology (`zeyrek` or Zemberek) for v1. No transformer NER, no
fourth encoder pass.**

## Reason

A transformer NER would add another encoder pass per request on the CPU demo
machine, on top of m3 and m5. The regex layer (Turkish phone, ID with checksum,
IBAN, plate and address formats) carries most of the doxing precision, and a
gazetteer covers the entity types doxing needs without a model.

## Consequences

- m6 spec: the named-entity layer states the v1 choice; the candidate table and
  the dependency note, including its reading of rule 6, are removed.
- m6 records the licence of every gazetteer source and of the analyser.
- A later move to a model-based NER is a new decision with its own ADR and latency
  budget.
