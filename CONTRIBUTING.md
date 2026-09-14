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

## Per-module workflow

1. **Spec first.** Update `modules/<name>/spec.md`: purpose, catches, does NOT
   catch, contract, approach + named tools, forbidden shortcuts with reasons,
   metric, acceptance criteria. Get it reviewed before writing code.
2. **Fixtures.** Put dev items in `modules/<name>/fixtures/dev.jsonl` (format in
   `eval/harness.py`). Use `context` to feed upstream outputs so the module runs
   alone. Never put test-split items here.
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
      and `fpr_increase_on_clean` within budget.
- [ ] `spec.md` is filled and matches the implementation.
- [ ] New artifacts registered in `artifacts/MANIFEST.md`.
- [ ] No edit to `contracts/` unless explicitly requested.
