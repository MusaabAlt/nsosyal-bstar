# legacy/ — superseded, do not run

Kept for provenance only. Nothing here is imported by `src/`, and none of it
should be executed — the briefing already records stray old script versions as
a source of real errors.

| File | What it was | Superseded by |
|---|---|---|
| `day1_gate.py` | first Turkish-language Day 1 gate | `day1_gate_en.py` + `src/` |
| `day1_gate2.py` | second iteration, pre-slice-refinement | `day1_gate_en.py` + `src/` |
| `main.py` | PyCharm's generated sample script | — |

The verified Day 1 logic now lives in `src/data_io.py` and `src/lexicon.py`,
with `day1_gate_en.py` as a thin driver. That port is checked against the frozen
record by `tests/_verify_day1_reproduction.py`.
