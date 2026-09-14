# Contributing to tr-moderation

Read `CLAUDE.md` first. This file turns its rules into a workflow.

## The 7 rules

1. `contracts/` is FROZEN. Never edit it without an explicit instruction.
2. A module NEVER imports another module. Only `pipeline/run.py` (via
   `modules/registry.py`) knows the order. Use `ctx.signals` to consume
   another module's published work.
3. A module NEVER mutates the original text. `Context` is frozen; build new
   strings.
4. A module NEVER applies a threshold and NEVER decides an action. It fills
   `code/score/source`; the decision layer fills `threshold/fired`.
   Thresholds live only in `decision/thresholds.yaml`.
5. A module returns only its own part of the contract, as a `ModuleOutput`,
   limited to the fields it declares in `provides`. The pipeline drops the rest.
6. Standard library only in the core (`contracts`, `decision`, `pipeline`,
   `api`, `eval`, `modules/registry.py`), plus pyyaml. Heavy deps belong to one
   module and go in that module's own `requirements.txt`.
7. Every module must be runnable, testable and measurable ALONE.

Rules 2, 4, 5 and 6 are enforced by `tests/test_architecture.py` and at runtime
by the pipeline.

## Stub rule

Until a module is implemented its `module.py` is a stub. A stub may state WHAT
is missing (the outputs of its spec contract) and point to the spec.md sections
that govern it. It may not prescribe HOW: no approach, tool or algorithm in a
stub's docstring, TODOs or skipped tests. spec.md is the only source of truth.

## Per-module workflow

1. **Spec first.** Read `modules/README.md` and your `modules/<name>/spec.md`;
   the spec is the source of truth. Changes to it go through the spec owner.
2. **Fixtures.** Put cases in `modules/<name>/fixtures/` as named by your spec
   (`cases.jsonl` when it does not say; format in `eval/harness.py`). Use
   `context` to feed upstream outputs so the module runs alone. Never put
   test-split items here.
3. **Implement `_run` (and `_load`).** Subclass `BaseModule`; do not add
   try/except around the whole body - `BaseModule` reports failures uniformly.
   Catch expected, local failures yourself and explain them in `notes`.
   Docstring: what it catches AND what it deliberately does not. Comments
   explain WHY, especially where a rule prevents a known failure.
4. **Artifacts.** Lexicons, gazetteers and weights go under `artifacts/`, are
   loaded offline, and are registered with sha256 in `artifacts/MANIFEST.md`.
5. **Unit tests.** Replace the skipped behaviour tests in `test_unit.py`.
6. **Measure.** `python -m modules.<name>.eval` writes
   `eval/results/<name>.json`.
7. **Thresholds.** If the module needs new numbers, derive them on dev following
   `protocols/templates/threshold_derivation.md` and edit
   `decision/thresholds.yaml` in a separate, reviewed change.

Protocol templates in `protocols/templates/`, each used before the number it governs exists:
- `annotation_guideline.md` - before labelling any fixture or evaluation slice;
- `experiment_protocol.md` - before running a change you intend to report (hypothesis,
  success criteria and ablations written first);
- `threshold_derivation.md` - before deriving any value in `decision/thresholds.yaml`;
- `error_analysis.md` - after each evaluation, before proposing the next change.
8. **Run `scripts/check.sh`** before opening the merge request.

## Acceptance checklist (must pass before merge)

- [ ] `python -m unittest discover -p "test_*.py"` passes, including
      `tests/test_architecture.py`.
- [ ] `eval/results/<name>.json` is produced by the current code and contains
      recall / precision / F1 / FPR **per code, with bootstrap confidence
      intervals** (plus capture rate per pattern and damage rate for
      representation modules). It is committed only once its protocol exists
      in `protocols/` (see `eval/README.md`).
- [ ] **Zero trap regressions** (`traps.regressions == 0`).
- [ ] p95 latency within `budgets.module_latency_p95_ms.<name>`
      (`latency.within_budget == true`), and the pipeline stays within
      `budgets.latency_p95_ms`.
- [ ] If the module adds a normalized-channel signal: `clean_to_dirty_flip_rate`
      within budget (`python -m eval.run_all` reports it).
- [ ] `spec.md` is filled and matches the implementation.
- [ ] New artifacts registered in `artifacts/MANIFEST.md`.
- [ ] No edit to `contracts/` unless explicitly requested.
