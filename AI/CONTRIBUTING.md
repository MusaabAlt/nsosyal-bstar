# Contributing to tr-moderation

Read `CLAUDE.md` first. This file turns its rules into a workflow.

## Setup

Python 3.11 or newer. Run everything from `AI/`.

```bash
# 1. virtual environment
python -m venv .venv
source .venv/bin/activate              # Windows, Git Bash: source .venv/Scripts/activate
                                       # Windows, PowerShell: .venv\Scripts\Activate.ps1

# 2. install - the core needs pyyaml only; a module's heavy dependencies are in its own requirements.txt
python -m pip install -r requirements.txt

# 3. the commands, in order
python -m unittest discover -p "test_*.py"      # all tests (the skipped ones belong to stub modules)
python -m pipeline.run "Bu bir test cumlesi"    # one analysis, full contract JSON (add --compact)
python -m modules.m0_charsafe.eval              # one module alone -> eval/results/m0_charsafe.json
python -m eval.run_all                          # every module on its fixture + pipeline budgets

# 4. pre-merge check, with an explicit base to compare contracts/ against
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```

`scripts/check.sh` needs a base ref. Without `BASE_REF` it compares against
`origin/master`; if that ref does not exist locally the check fails - on
purpose, because it cannot prove `AI/contracts/` is unchanged. On
Windows run it from Git Bash; it needs LF line endings (`.gitattributes`).

## Why every verdict is `review` today

The system **fails closed**. A module that is a stub, fails, is unavailable or
returns invalid output makes the result *degraded*, and a degraded result is
never `clean`: a verdict that would have been clean becomes `review`, and a more
severe verdict stands with "ancak değerlendirme eksik" added (`pipeline/run.py`,
`decision/actions.py`). `m0_charsafe` is implemented and `m4_implicit` is a
non-stub that emits nothing yet (C1–C5 come from m3, ADR-006); m1, m2, m3, m5 and
m6 are stubs (`stub = True`), so every result is degraded today. That is why every ordinary
post comes back as `review`, with `signals.pipeline.degraded` naming the stub
modules and the Turkish explanation saying the judgement is incomplete. This is
by design: silence from an unimplemented module is not evidence that a post is
clean. Every number in `decision/thresholds.yaml` is a placeholder as well.

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
   the spec is the source of truth. A module owner **proposes** changes to their
   spec; Osama **approves** them. Do not edit a spec without that approval.
2. **Fixtures.** Put cases in `modules/<name>/fixtures/cases.jsonl` (format and
   key names in `eval/harness.py`). Use
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
7. **Thresholds.** A module owner **may** edit their own category rows in
   `decision/thresholds.yaml`. Derive the numbers on dev following
   `protocols/templates/threshold_derivation.md` and make the edit in a separate,
   reviewed change. The shared rows **A1–A3** (fed by m1 and m3, assigned from
   m6's target) and **C1–C5** (scored by m3, repaired by m4) are owned by the
   project owner, not by a module owner.

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
- [ ] p95 latency on CLEAN input within `budgets.module_latency_p95_ms.<name>`
      (`latency.within_budget == true`), and the pipeline stays within
      `budgets.latency_p95_ms`. Adversarial input is reported alongside
      (`latency.adversarial`, `latency.adversarial_over_budget`); an overrun there
      is a finding to publish, not a merge blocker to hide.
- [ ] If the module adds a normalized-channel signal: `clean_to_dirty_flip_rate`
      within budget (`python -m eval.run_all` reports it).
- [ ] `spec.md` is filled and matches the implementation. EIGHT sections are
      required (a missing one fails `test_module_layout_and_specs`): Objective,
      What it catches / does not catch, Contract, Forbidden — with reasons,
      Metrics this module must produce, Required fixtures, Acceptance criteria,
      Definition of done. TWO are recommended (a missing one only warns):
      Approach, Research pointers. A spec is never reworded just to satisfy the check.
- [ ] New artifacts registered in `artifacts/MANIFEST.md`.
- [ ] No edit to `contracts/` unless explicitly requested.
