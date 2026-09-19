# tr-moderation

Turkish offensive-content moderation. Modular: every category of offensive
speech gets its own engine, its own threshold and its own action. Runs fully
offline on CPU - no platform API, no network call at inference.

**Status (2026-09-19, `docs/audit/PROJECT_COMPLETION_STATUS.md`).** Contracts,
decision layer, pipeline, evaluation harness and `m0_charsafe` are implemented and
verified. `m2_deobf` runs (protection pass, tier 1, zeyrek-validated DEASCII; the
lexicon-dependent patterns are declared unhandled). `m6_target` v1 runs (target
resolution and B4 doxing; the three documented ambiguities are declared pending the
owner). `m1_lexicon` runs on terlik on both channels with SUBSTRING_COLLISION,
HOMONYM and NON_HUMAN_TARGET (A4 needs an owner-approved table). `m3_encoder` runs
the deployed rule-v4 multi-head artifact `m3-berturk-multihead-a-rule-v4-20260918-163728`
(pinned weights sha256 `dc7fe306…0b76`, git-ignored, copied from Drive; no fallback): the binary
head scores both channels (`raw_score`, `norm_score`) and the trained A head publishes the A1
carrier; the B and C heads are NOT trained. `m4_implicit` runs stage 1: it reads m3's
published scores and publishes what the `binary_offensive` row it owns thresholds (input,
the artifact and protocol the threshold was derived for, cross-channel gap); it emits no
content score - C1-C5 come from m3's C head, which has no labels (ADR-006 and its
2026-09-19 amendments). `m5_sarcasm` runs Stage 1: a deterministic, rule-based D1 detector,
not a trained model and not benchmarked (`protocols/m5_stage1_deterministic_protocol.md`);
no module is a stub, so a clean verdict is reachable. In `decision/thresholds.yaml` the
`binary_offensive` threshold (0.445857971906662) is derived for rule-v4; every other number
is a placeholder until derived on dev.

## Quick start

Run from `AI/`.

```bash
python -m pip install -r requirements.txt      # pyyaml only; the full suite also needs the module requirements
                                               # (terlik, zeyrek, torch/transformers) - use AI/.venv, see CONTRIBUTING.md "Interpreter"
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
