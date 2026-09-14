# eval/

- `harness.py` — `ModuleEvaluator`: measures one module alone on its fixture,
  per code with bootstrap CIs, representation metrics, traps, latency.
- `run_all.py` — every registered module on its own fixture.
- `traps/traps.jsonl` — collision traps that must never fire.
- `testsuite/` — end-to-end gold set for the whole pipeline.
- `results/` — output of the harness. **Not committed.**

## No result is committed before its protocol exists

A number in this repository is a claim. Before any result file for a stage is
committed, the protocol for that stage — decision rules, thresholds, failure
conditions, precision budget — must already be in `protocols/` and in version
control (see `modules/README.md`, "Freeze before you measure").

Until then `eval/results/*.json` is git-ignored: run the harness locally, read
the numbers, but do not commit them. When a protocol exists, commit the result
file it names explicitly (`git add -f`) in the same change that references the
protocol.
