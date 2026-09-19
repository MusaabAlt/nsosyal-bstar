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
- m5 does not read m3 embeddings and m3 does not publish them (both specs say so
  explicitly). A "middle path" - an m5 head on m3's hidden states - would bring
  the entanglement back, and no contract field can carry embeddings.
- "Small or distilled" is a constraint on the m5 owner, not a model choice: a
  second full BERT-sized pass per channel doubles encoder latency and memory on
  CPU. The m5 owner picks the model and records its measurement.

## Amendment — contract example regenerated (2026-09-14)

Applying this decision changed what a real run returns (no `head_sarcasm`, no
`channels` copy of the post), so `contracts/fixtures/analysis_result.example.json`
had to follow. `contracts/` is frozen; the project owner gave the explicit
instruction to regenerate that one file from a real current run (queue item 2.3).
It was regenerated, never hand-edited, first in commit `79f27e5` (recorded in
ADR-002's amendment) and again at the end of the following session so it
reflects that session's final state:

    python -m pipeline.run "Bu bir test cumlesi" --trace-id example-trace-id > contracts/fixtures/analysis_result.example.json

No other file in `contracts/` was touched. The contract is re-frozen immediately
after the regeneration.

## Amendment — the contract example is deterministic (2026-09-14)

- **Decided by:** project owner

**Decision.** Run-dependent values in `contracts/fixtures/analysis_result.example.json`
are frozen to a fixed sentinel: `latency_ms` and every `per_module_ms` value are
`0.0` (`pipeline/contract_example.py::LATENCY_SENTINEL_MS`). `artifact_hash` stays
real, and `trace_id` is the fixed `example-trace-id`.

**Reason.** Latency differs on every run, so each legitimate regeneration tripped
the `contracts/` gate in `scripts/check.sh`. A gate that fails on every legitimate
regeneration is a gate the team learns to ignore, which is worse than no gate.
Keeping `artifact_hash` real means a genuine change to the decision config or to
a module version still changes the example and still trips the gate.

**How.** The example is still produced by a real run, never edited by hand:

    python -m pipeline.contract_example --check   # exit 1 when the committed example is not current
    python -m pipeline.contract_example --write   # overwrite; only on an explicit owner instruction

This replaces the shell redirect in the amendment above (which also wrote CRLF on
Windows). `tests/test_contracts.py::test_example_regeneration_is_deterministic`
pins byte-identical output across two runs. `0.0` is a stand-in, not a
measurement; the example says nothing about latency.

## Amendment — both contract examples and the schema docstring (2026-09-14)

- **Decided by:** project owner (explicit instruction covering all three files)

`contracts/` was opened once more, for three files, on the owner's explicit
instruction:

- `contracts/fixtures/analysis_result.example.json` - regenerated from a real
  current run. It was stale after ADR-005 and ADR-006 (decision config hash,
  module order, `signals.decision.family_a`, m4 no longer a stub).
- `contracts/fixtures/module_output.example.json` - regenerated from a real run
  of the reference module `m0_charsafe` on `SIKINTI`. It was stale since the
  signals were renamed (`offsets` became the internal `_offsets`) and m0 became
  version `0.2.0`. `latency_ms` is frozen to the same `0.0` sentinel.
- `contracts/schema.py` - docstring only: a module-set `threshold`/`fired` is now
  reset by the decision layer (`decision/fusion.py::reset_decision_fields`), not
  stripped by the pipeline. No type or field changed.

Both examples come from `python -m pipeline.contract_example --write`, which now
generates both; `--check` (run by `scripts/check.sh`) covers both.

The contract is re-frozen immediately after this change.


## Amendment — analysis example after m1_lexicon implemented (2026-09-15)

- **Decided by:** project owner (explicit instruction, after reviewing the dry-run diff)

`contracts/fixtures/analysis_result.example.json` regenerated with
`python -m pipeline.contract_example --write`. It was stale because `m1_lexicon`
stopped being a stub (version `0.0.0` -> `0.1.0`). Every difference comes from that:

- `signals.m1_lexicon` now carries `lexicon_hit`, `lexicon_hit_raw`,
  `lexicon_hit_norm` (all false on the example sentence), `matched_roots`, `engine`.
- `m1_lexicon` is gone from `signals.pipeline.degraded`, the explanation and the
  pipeline notes.
- `artifact_hash` changed, from two inputs in the same commit: m1's version and
  m1's latency budget in `decision/thresholds.yaml`, which became per input length
  like m0's (owner decision, placeholders to measure on the demo machine).
  Verified: with m1 back at `0.0.0` and its budget back at `5` the hash reproduces
  the previous value exactly; nothing else in the decision config changed.

`contracts/fixtures/module_output.example.json` regenerated identically. No
contract code, type or field changed. The contract is re-frozen immediately after
this change.

## Amendment — analysis example after m3 wraps the baseline and binary_offensive is derived (2026-09-15)

- **Decided by:** project owner (explicit instruction)

`contracts/fixtures/analysis_result.example.json` regenerated with
`python -m pipeline.contract_example --write` after two owner-approved changes in the same
commit, and nothing else:

- `m3_encoder` 0.1.0 wraps the frozen epoch-1 BERTurk checkpoint
  (`m3-berturk-pytorch-fp32-epoch1`): `signals.m3_encoder` carries `raw_score` and
  `artifact`; m3 is gone from `signals.pipeline.degraded`, the explanation and the notes.
- `decision/thresholds.yaml`: `binary_offensive.threshold` 0.50 -> 0.320188, the
  `normalized` channel removed, artifact `thresholds-v0.1.0` (derived, `binary_offensive`
  only; `protocols/threshold_derivation_binary_offensive_stage1.md`). The example's
  `signals.decision.binary_offensive` shows the new threshold, the raw score and
  `fired: false`; `artifact_hash` changed with the config and m3's version.
- `decision/thresholds.yaml`: `budgets.latency_p95_ms` 150 -> 250, still a placeholder
  ("provisional; re-measure on the demo machine"; owner decision after m3 made the
  pipeline p95 185 ms). It changes only `artifact_hash` in the example.

The example now contains a model output (`raw_score`), so it is current only on a machine
that has the m3 artifact files (artifacts/MANIFEST.md) and torch 2.11.0 / transformers
5.15.0. Two consecutive generations were byte-identical on the machine that wrote it.
`module_output.example.json` regenerated identically. No contract code, type or field
changed. The contract is re-frozen immediately after this change.

## Amendment — contract example regenerated for the m4 note (2026-09-16)

- **Decided by:** project owner (explicit instruction for this one regeneration)

**Change.** `m4_implicit` now returns one plain note, `C1–C5 not implemented yet`, so a
reader of the result sees that the C family is not covered. m4 stays a non-stub module
that does not degrade the result (ADR-006 amendment unchanged): `signals.pipeline.degraded`
is still m2_deobf, m6_target, m5_sarcasm.

**Regenerated.** `contracts/fixtures/analysis_result.example.json`, with
`python -m pipeline.contract_example --write`, never by hand. The only difference is
the added line `"[m4_implicit] C1–C5 not implemented yet"` in `notes`. `artifact_hash`
is unchanged: no module version and no decision config changed.
`module_output.example.json` is unchanged. No other file in `contracts/` was touched.

**Gate.** The `contracts/ untouched` gate in `scripts/check.sh` fails for this commit
only, on the owner's explicit acceptance. Every other gate must pass. The contract is
re-frozen immediately after.

## Amendment — m5 Stage 1: a deterministic detector ahead of the gate (2026-09-19)

- **Decided by:** project owner (explicit approval for the TEKNOFEST prototype)

**Decision.** m5 ships a Stage-1 deterministic, high-precision detector for D1
(`protocols/m5_stage1_deterministic_protocol.md`, M5-S1; `modules/m5_sarcasm/module.py` 1.0.0):
four conjunctive rule families (scare-quoted praise, clause-final ironic `tabii`, congratulated
failure, the `(!)` irony mark), each requiring a second-person anchor, with exclusions for reported
speech, mentions, negation, questions, missing person anchor and explicit content (spec §3
precedence, read from m1's published `lexicon_hit`). `stub` is removed because detection logic
exists. D1 scores are `1.0` = "a rule is satisfied", not a probability.

**What does not change.** This ADR's decision stands: the neural D1 model is m5's own model with its
own artifact and thresholds, never a head on m3. It is Stage 2, gated by m5 spec §2, not trained and
not benchmarked; `training/m5_sarcasm/` and `docs/training/m5_sarcasm.md` are untouched.
`decision/thresholds.yaml` is untouched: `D1` stays threshold `0.50` / action `nudge`, both
PLACEHOLDER policy.

**Consequence.** m5 no longer degrades every result, so a clean verdict is reachable from the default
pipeline for the first time. The contract example is regenerated on the owner's instruction of the
same day.

## Amendment — contract example regenerated for rule-v4, m4 0.3.0 and m5 Stage 1 (2026-09-19)

- **Decided by:** project owner (explicit authorization of 2026-09-19 to run `--write` once the
  runtime changes were final)

`contracts/fixtures/analysis_result.example.json` regenerated with
`python -m pipeline.contract_example --write`, never by hand; `--check` exits 0 afterwards. Every
difference follows from the runtime: m3 is the deployed rule-v4 artifact (new scores, and its A head's
A1-carrier score on both channels, not fired), m4 0.3.0 and m5 1.0.0 publish their signals,
`signals.pipeline.degraded` is empty so the verdict is `clean` with its explanation,
`binary_offensive.threshold` is 0.445857971906662, and `artifact_hash` changed with the versions and
the config. `module_output.example.json` is unchanged. No contract code, type or field changed; the
contract is re-frozen.
