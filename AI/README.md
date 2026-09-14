# tr-moderation

Turkish offensive-content moderation. Modular: every category of offensive
speech gets its own engine, its own threshold and its own action. Runs fully
offline on CPU - no platform API, no network call at inference.

**Status: skeleton.** Contracts, decision layer, pipeline, evaluation harness
and the reference module `m0_charsafe` are implemented. `m4_implicit` emits
nothing yet by design (C1-C5 come from m3's C head, ADR-006); m1, m2, m3, m5 and m6 are
documented stubs, and every number in `decision/thresholds.yaml` is a
placeholder until derived on dev.

## Quick start

```bash
python -m pip install -r requirements.txt      # pyyaml only
python -m pipeline.run "Bu bir test cumlesi"   # prints the full contract JSON
python -m pipeline.run "a" "b" "c" --thread '{"sender_id": "u1", "target_id": "u2"}'   # Axis 4 path (ADR-004)
python -m unittest discover -p "test_*.py"
python -m modules.m0_charsafe.eval             # writes eval/results/m0_charsafe.json
python -m eval.run_all                         # every module on its dev fixture
python -m api.main --port 8080                 # POST /analyze {"text": "..."}
BASE_REF=<commit> bash scripts/check.sh        # everything above, pre-merge (see CONTRIBUTING.md, Setup)
```

## How a post flows

```
text ─► m0_charsafe ─► m2_deobf ─► m6_target ─► m1_lexicon ─┬─► m3_encoder ─► m4_implicit ─► m5_sarcasm
        (charsafe)     (parallel    (target,     (raw+norm,  │   (3 heads A/B/C, (C thresholds, (D1, own model)
                        channel)     published)   guards)     │    both channels)  slice repair)
                                                  fast path ─┘ (would skip the rest when decisive; disabled
                                                               until its margin is derived on dev)
                                   ─► decision/fusion.py: fuse channels → thresholds → guards → thread → verdict
```

Modules emit scores (`code/score/source`); only `decision/` compares them with
thresholds and picks an action (`block > escalate > review > nudge > clean`).

## Layout

| path | what |
|---|---|
| `contracts/` | FROZEN code books (`codes.py`), result dataclasses (`schema.py`), module interface (`module_api.py`), example JSON |
| `modules/` | `registry.py` (`PIPELINE_ORDER`: ordered module classes) + one folder per module: `module.py`, `spec.md`, `test_unit.py`, `eval.py`, `fixtures/cases.jsonl` |
| `decision/` | `thresholds.yaml` (the only place for numbers), `fusion.py`, `actions.py` |
| `pipeline/` | `run.py` - orchestration + CLI |
| `api/` | `main.py` - stdlib HTTP API |
| `eval/` | `harness.py` (metrics, bootstrap CIs, traps, latency), `run_all.py`, `traps/`, `testsuite/`, `results/` |
| `artifacts/` | `MANIFEST.md` - hashes of lexicons, gazetteers, weights |
| `protocols/templates/` | annotation, threshold derivation, experiment and error-analysis templates |
| `tests/` | contract, decision, pipeline and architecture-rule tests |
| `scripts/check.sh` | pre-merge check |

See `CLAUDE.md` for the rules and `CONTRIBUTING.md` for the workflow.
