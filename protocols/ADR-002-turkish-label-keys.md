# ADR-002 — Turkish label map keyed by enum type

- **Status:** accepted
- **Date:** 2026-09-14
- **Scope:** `contracts/codes.py` (explicitly instructed contract edit), `tests/test_contracts.py`

## Context

`contracts/codes.py` defines its enums as `str` subclasses so values
serialise as plain strings. A side effect: members of *different* enums with
the same value are equal and hash equal. `ContentCode.CLEAN == Family.CLEAN`.

`TR_LABELS` was a plain `dict` literal containing both. The second entry
silently overwrote the first: the map held 54 entries instead of 55. Both
labels happened to be "Temiz", so nothing visible broke, but any future label
that differs between two same-valued members would be lost without an error.

## Decision

Per the explicit Phase 8 instruction to fix the collision, `contracts/` was
opened for this one change (ADR-001 requires an explicit instruction and an ADR
for any further contract edit):

- `TR_LABELS` is now an `EnumLabels` map keyed by `(enum type, value)`.
- Its public behaviour is unchanged: `TR_LABELS[member]`, `member in
  TR_LABELS`, `TR_LABELS.get(member)` and `tr_label(member)` work as before.
- A duplicate `(type, value)` pair raises at import time instead of silently
  overwriting.
- A bare string is not a key (`"CLEAN" in TR_LABELS` is `False`): labels are
  looked up by enum member only.

`tests/test_contracts.py::test_turkish_labels_do_not_collide_across_enums`
asserts 55 entries and that both `CLEAN` members are present.

The contract is re-frozen immediately after this change.
