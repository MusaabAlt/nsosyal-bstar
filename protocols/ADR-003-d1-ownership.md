# ADR-003 — D1 (degrading sarcasm) is m5's own model

- **Status:** accepted
- **Date:** 2026-09-14
- **Decided by:** project owner (policy decision; options prepared in the re-audit, Phase 13.2)
- **Scope:** `modules/m3_encoder/spec.md`, `modules/m5_sarcasm/spec.md`, CLAUDE.md, README.md, registry docs

## Context

The m3 spec drew D1 as `head_sarcasm` on the shared BERTurk encoder; the m5 spec
claimed D1 as its own module. Two options were presented:

- **A — head inside m3:** one encoder pass, near-zero extra latency; but every
  sarcasm experiment is a new m3 artifact, which (m3 spec §5) forces threshold
  re-derivation for families A and B, and m5 stops being runnable alone.
- **B — m5 its own model:** a second encoder pass (latency and memory), but an
  independent artifact, independent thresholds, and a failed gate simply
  disables m5.

## Decision

**Option B.** m5 is its own model with its own artifact, MANIFEST row and
thresholds. `head_sarcasm` is removed from m3's spec and contract; m3 has two
heads (A single-label, B multi-label).

## Reason

Under Option A the weakest, gated part of the project could destabilise the
strongest: a sarcasm experiment would force re-derivation of the A and B
thresholds. Option B keeps rule 7 clean and lets a failed entry gate disable m5
with zero impact on m3. Latency is solvable with a small or distilled model;
artifact entanglement is not.

## Consequences

- m3 spec: title, objective, diagram and definition of done say two heads.
- m5 spec §5: own model, own artifact and thresholds, own requirements file when
  implemented (rule 6 is per module).
- `decision/thresholds.yaml` `budgets.module_latency_p95_ms.m5_sarcasm` stays a
  placeholder to be met by a small or distilled model.
