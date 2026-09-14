# How to work inside a module

Read this once, then read your own `spec.md`. Your spec is your reference while
coding and while researching — it already tells you the approach, the named
tools, and the mistakes that are known to fail on Turkish. You do not need to
re-derive the research; you need to implement inside the boundaries it sets.

---

## The seven rules

1. `contracts/` is **frozen**. If you think you need to change it, stop and raise it.
2. A module **never imports another module**. Only `pipeline/run.py` knows the order.
3. A module **never mutates** the original text.
4. A module **never applies a threshold** and never decides an action. Thresholds live only in `decision/thresholds.yaml`.
5. A module returns only its own part of the contract, as a `ModuleOutput`.
6. Heavy dependencies belong to the one module that needs them, in that module's own requirements file. The core stays standard-library plus `pyyaml`.
7. A module must be runnable, testable and measurable **alone**.

---

## Module types — your acceptance metric depends on this

| Type | Modules | Measured by |
|---|---|---|
| Representation | M0, M2 | capture rate per pattern, damage rate on clean text |
| Signal | M1, M6 | precision first, then recall; zero-firing proofs |
| Detection | M3, M4, M5 | precision/recall/F1 per code, with CIs |

Do not ask a representation module for an F1 score. Do not accept a detection
module without confidence intervals.

---

## Files you own

```
modules/<your_module>/
├── module.py        your implementation
├── spec.md          your reference — keep it updated as you learn
├── test_unit.py     unit tests
├── eval.py          standalone evaluation entrypoint
├── fixtures/        your test cases
└── requirements.txt only if you need heavy deps
```

You do not touch anything outside this folder, except adding your trap cases to
`eval/traps/`.

---

## Rules that apply to every number you produce

- **Confidence intervals, always.** A point estimate with no interval is not a result.
- **Decomposed, never averaged.** Per pattern, per code, per slice. An average hides the case that fails.
- **State the cost in the same sentence as the gain.** A recall improvement bought with precision is reported as one fact, not two.
- **Compare at equal coverage.** If your method defers more, it is not better at the same operating point.
- **Never touch the closed official test set.** The documented query count on it stays at one.
- **Freeze before you measure.** Decision rules, thresholds and failure conditions go into a protocol file in `protocols/` and into version control **before** the first number of that stage exists.
- **A negative result is a delivered result.** A module that tried, failed, and documented the failure with a confidence interval has done its job. A module with no number has not.

---

## Before you open a merge request

- [ ] Unit tests pass: `python -m unittest discover -p "test_*.py"`
- [ ] `python -m modules.<name>.eval` writes `eval/results/<name>.json`
- [ ] That file contains: metrics with CIs, p50/p95 latency, trap results
- [ ] Zero regressions on `eval/traps/`
- [ ] Latency inside the budget in `decision/thresholds.yaml`
- [ ] `spec.md` updated with what the module catches, what it deliberately does not, and its current number
- [ ] No import of another module
- [ ] No threshold anywhere in your code
- [ ] Licence recorded for every external resource you used
