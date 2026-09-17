# eval/

- `harness.py` — `ModuleEvaluator`: measures one module alone on its fixture,
  per code with bootstrap CIs, representation metrics, traps, latency.
  Latency is timed repeatedly (`--latency-repeats`, default 200 timings per item;
  `LATENCY_REPEATS` in scripts/check.sh) and the repeat count is recorded in the
  results next to every p50/p95. Budgets gate clean input; adversarial input is
  reported alongside.
- `run_all.py` — every registered module on its own fixture.
- `traps/traps.jsonl` — collision traps. Per trap:
  - `must_not_fire`: content codes that must never fire (`"*"` = any), checked for every module;
  - `expect`: output fields that must match exactly when the module produces them — "when
    produced": a module that emits nothing passes every `expect`, so it is not a presence check;
  - `form` / `guards`: `{"modules": [...], "must": [...], "must_not": [...]}` on the form
    patterns / guards a listed module emits (before thresholds). A `must` a stub cannot meet yet
    is reported as pending, not as a regression. Module owners add their own cases here;
  - `binary`: `{"modules": [...], "must_not_fire": true}` — the binary offensive score
    (`signals.decision.binary_offensive`, m3's `raw_score` against the derived threshold) must not
    fire for a listed module; a listed module that publishes no numeric score fails the rule.
    No committed trap carries this rule yet: whether the collision traps must also keep the
    binary score below its threshold is an open policy question (docs/audit/OPEN_QUESTIONS.md
    Q2, Q18). The harness still reports `binary_fired` for every trap, rule or not.
- `implementation_status.json` — per module: `STUB` / `PARTIAL` / `IMPLEMENTED`, what is
  `not_built`, the exact behaviour tests allowed to be skipped, and preconditions. Read by the
  harness (report block `implementation`) and pinned by `tests/test_implementation_status.py`:
  a stub's report says `NOT VERIFIED`, and an undeclared skip fails the suite.
- `testsuite/` — end-to-end gold set for the whole pipeline (format examples only today).
- `results/` — output of the harness. **Not committed.**

## What a result file records (Gate 1)

Every `<module>.json` written by the harness carries, next to the numbers:

- `implementation` — declared status, `not_built` list, and `scope`: a stub's numbers describe an
  empty module (`NOT VERIFIED`), a PARTIAL module's numbers never cover its `not_built` list;
- `degraded_items` — fixture items the module degraded (stub, `ok=False`, dropped output), by the
  same rules `Pipeline.analyze` uses; a stub degrades every item and its verdict is never clean;
- `traps.observations` — per trap, as separate facts: `content_fired`, `binary`
  (score / threshold / fired), `form_active`, `guards_active`, `guards_suppressed`, `degraded`,
  `post_offensive`, `verdict`, `driver`; plus `traps.binary_fired` (ids) and
  `traps.binary_observable`;
- `provenance` — `git_head`, `git_dirty`, sha256 of the fixture, the trap file, `thresholds.yaml`
  and `implementation_status.json`, the trap count, repeats and bootstrap size.

`pipeline.json` adds `binary_offensive_on_traps` (traps on which the binary score fired in the
full pipeline, and those flipped by the normalized channel — reported, not budgeted, because the
flip-rate budget is defined on content codes), `trap_observations`, `degraded_modules` and the
same `provenance`.

**HISTORICAL_RESULT vs CURRENT_REPRODUCIBLE_RESULT.** A result file without a `provenance`
block, or whose `provenance.git_dirty` is true, cannot be tied to a commit: read it as a
historical observation, never as a reference to compare against. A reference is a run whose
`git_head` is a commit, `git_dirty` is false, and whose input digests match that commit.
`python -m eval.run_all --results-dir <dir>` writes a current run elsewhere so a historical file is
never overwritten by accident.

## No result is committed before its protocol exists

A number in this repository is a claim. Before any result file for a stage is
committed, the protocol for that stage — decision rules, thresholds, failure
conditions, precision budget — must already be in `protocols/` and in version
control (see `modules/README.md`, "Freeze before you measure").

Until then `eval/results/*.json` is git-ignored: run the harness locally, read
the numbers, but do not commit them. When a protocol exists, commit the result
file it names explicitly (`git add -f`) in the same change that references the
protocol.
