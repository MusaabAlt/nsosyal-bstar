# tr-moderation — session handover

Written 2026-09-14 at the end of the scaffolding and hardening session.
Commit history: `6c6c8d4` (skeleton) … `79f27e5` (owner decisions), plus the commit that adds this file.

---

## 1. Decisions made in this session

Policy decisions were taken by the project owner; implementation choices by the assistant.
Each row names where the decision is recorded.

### Architecture and contract

| # | Decision | Reference |
|---|---|---|
| 1 | `modules/<m>/spec.md` are the existing design specs, the single source of truth; `modules/README.md` is the module guide. | `31083aa` |
| 2 | Spec field names follow the frozen contract (`out.content`, `out.form.patterns`, `source = "<module>@<channel>"`); the contract wins over the specs. | `4b07bc6` |
| 3 | Guards are scoped: a guard suppresses a content score only from its own module, and only on overlapping spans when both carry one; never a whole family across the post. `ContentScore.span`, `GuardResult.span` and optional `GuardResult.source` were added in a one-time contract unfreeze. Guards run before fusion. | ADR-001, `6daa1c6` |
| 4 | Spans are enforced at runtime: every module declares `emits_spans`; a span-declaring (or undeclared) module's score or guard without a span is dropped and degrades the module. The no-span fallback exists only for `emits_spans = False`. | ADR-001 amendment, `3f3a6e1` |
| 5 | `TR_LABELS` is keyed by (enum type, value) so `ContentCode.CLEAN` and `Family.CLEAN` no longer collide. | ADR-002, `305e2dd` |
| 6 | `contracts/fixtures/analysis_result.example.json` regenerated from a real run (explicit instruction). | ADR-002 amendment, `79f27e5` |
| 7 | D1 (degrading sarcasm) is m5's own model with its own artifact and thresholds; `head_sarcasm` removed from m3 (m3 has two heads, A and B). | ADR-003, `79f27e5` |
| 8 | Entry-point convention: `modules/registry.py::PIPELINE_ORDER` names module classes by dotted path; no module-level `MODULE` instance. `REGISTRY` renamed to `PIPELINE_ORDER`. | `ed921f9` |
| 9 | Rule 2 covers imports between modules; `contracts` and `eval.harness` are shared infrastructure outside its scope. A module's `eval.py` may import `eval.harness`, its own `module.py`, `contracts` and the stdlib only (allow-lists as data in `tests/test_architecture.py`). | CLAUDE.md, `305e2dd` |
| 10 | Heavy dependencies are declared per module; today only m3 has a requirements file. m5 gets its own when implemented (follows from #7). | `dcd297a`, ADR-003 |
| 11 | m6 is the only owner of `target`. m3 and m5 provide `content` only, as their spec contracts say. | `dcd297a`, `c0c38aa` |

### Decision layer and policy

| # | Decision | Reference |
|---|---|---|
| 12 | Signal-conditioned thresholds: `threshold_when: {signal, true, false}` with scalar fallback; the branch taken is recorded in `signals.decision.threshold_branches`. `binary_offensive` entry for m3's channel-level scores. | `e48f142` |
| 13 | POLICY: `binary_offensive` fires into the verdict with action `review` (placeholder). Kept by the owner. | `e48f142` |
| 14 | POLICY: decision-layer failure yields `verdict = None` with a "karar verilemedi" explanation. Kept by the owner. | `305e2dd` |
| 15 | POLICY: fail closed. Any degraded module — stub, failure, unavailable, construction failure, invalid output — means the system cannot judge; a would-be clean verdict becomes `review`; `signals.pipeline.degraded` lists module, kinds and reasons; the explanation states the judgement is incomplete. | `b435ae3` |
| 16 | POLICY (owner-confirmed interpretations): (a) a more severe verdict under degradation stands, with "ancak değerlendirme eksik" added; (b) wrong types, a `source` naming another module, invalid or missing spans and undeclared fields degrade too; (c) scores and confidences are valid only in [0, 1]; (d) undeclared `emits_spans` means spans required; (e) a spanless guard is dropped, a fully spanless m1 output ends in `review`; (f) a trap `must` a stub cannot meet is pending, not a regression; (g) small capital `ɪ` maps to `I`, then to `ı`. | owner confirmation, `b435ae3`, `3f3a6e1`, `a2c1d04` |
| 17 | Only guards a spec contract gives a producer are configured: SUBSTRING_COLLISION, HOMONYM (m1), NON_HUMAN_TARGET (m6). QUOTE_COUNTERSPEECH, METADISCUSSION, NEGATION, SELF_DIRECTED, DUAL_REGISTER, FRIENDLY_BANTER removed: no producer, no guard. A configured guard must appear in `guards_order`. | `a2c1d04`, owner decision |
| 18 | Fast path disabled until its margin is derived on dev; `requires` = guard producers (m1, m6) and their inputs (m0, m2). | `94ccd90`, `a2c1d04` |
| 19 | POLICY: repetition is time-windowed, not bounded by a post count; `window_posts` removed. | owner decision, `79f27e5` |
| 20 | POLICY: `fpr_increase_on_clean` stays removed until a frozen baseline exists, then returns (noted in `thresholds.yaml`). | owner decision, `79f27e5` |
| 21 | POLICY: the response stays bounded — no `signals.channels` (charsafe / normalized text) in it; `trace_id` is enough for auditability. `_`-prefixed signal keys are internal (e.g. m0 `_offsets`). | owner decision, `a2c1d04`, `79f27e5` |
| 22 | m0 latency budgets are per input length: ≤64 chars 0.25 ms, ≤280 chars 1 ms, ≤1000 chars 4 ms, ≤5000 chars 25 ms (placeholders, measured on the dev machine). | owner decision, `79f27e5` |

### Measurement and tests

| # | Decision | Reference |
|---|---|---|
| 23 | No eval result is committed before its protocol exists; `eval/results/*.json` is git-ignored. | `94ccd90`, `eval/README.md` |
| 24 | Metrics are per code with bootstrap CIs, never pooled; fixed code list; representation modules also report capture rate per pattern and damage rate on clean text; fixture and trap latency are separate. | `94ccd90` |
| 25 | Traps assert content (`must_not_fire`), exact fields (`expect`) and emitted form patterns / guards per module (`must`, `must_not`). | `a2c1d04` |
| 26 | Every `test_unit.py` has `test_contract_shape`, `test_input_not_mutated`, `test_never_raises`. m0 criterion: "every uppercase `I` maps to `ı`" (`test_sikinti_never_yields_profane_root`). | `52ddc97` |
| 27 | Stub rule: a stub states WHAT is missing and points to spec.md; it never prescribes HOW. Skipped tests grounded in no spec were deleted. | `c0c38aa`, `79f27e5`, CONTRIBUTING.md |
| 28 | Rule 4 is enforced by an AST scan: numeric literals or literal-bound names in comparisons, threshold-like names, float literals in ordering asserts; module `eval.py` and `test_unit.py` included; `tests/` excluded by design. | `305e2dd` |
| 29 | `scripts/check.sh` fails loudly when it cannot verify `contracts/` is unchanged. | `305e2dd` |
| 30 | MANIFEST columns: `artifact_id \| format \| sha256 \| thresholds_file \| derived_on \| date` (+ owner, licence). | `ed921f9` |

---

## 2. Current state

**Done and working**
- Contracts (`contracts/`), frozen; changes only through ADR-001 and ADR-002.
- Decision layer: fusion, per-module guard scoping, signal-conditioned thresholds, thread rule, fail-closed verdicts, Turkish explanations.
- Pipeline: safe construction, loading and processing; output validation; span enforcement; deep-frozen signals; bounded response; CLI.
- HTTP API (`api/main.py`), stdlib only, JSON on every failure.
- Evaluation harness: per-code CIs, representation metrics, traps with form/guard rules, per-length latency bands, pipeline budgets (flip rate, latency).
- `m0_charsafe` fully implemented (reference module).
- Architecture tests for rules 2, 4, 6 and 7, span declarations and the entry-point convention.
- 205 tests; 9 skipped behaviour tests that belong to unimplemented modules.

**Stubbed (declare `stub = True`; every result is degraded, verdict `review`)**
- m1_lexicon, m2_deobf, m3_encoder, m4_implicit, m5_sarcasm (gated by its spec §2), m6_target.

**Blocked on the project owner**
- Missing spec sections (see §5). The owner writes these.
- All thresholds, actions and budgets in `decision/thresholds.yaml` are placeholders until derived on dev.
- Module owners are `_assign_` in every spec.

---

## 3. Commands

Run from the repository root with the project venv (`python -m pip install -r requirements.txt` installs pyyaml).

```bash
python -m pipeline.run "Bu bir test cumlesi"          # full contract JSON (add --compact for one line)
python -m unittest discover -p "test_*.py"            # all tests (add -v for names)
python -m modules.m0_charsafe.eval                    # one module alone; writes eval/results/m0_charsafe.json
python -m eval.run_all                                # every module + pipeline budgets
python -m api.main --port 8080                        # POST /analyze {"text": "..."}
BASE_REF=<commit> bash scripts/check.sh               # pre-merge check; fails without a base ref
```

---

## 4. Conventions a new session must not violate

1. **`contracts/` is frozen and owned by Osama.** Never edit it without an explicit instruction; every such change gets an ADR in `protocols/` and the contract is re-frozen immediately after.
2. **No threshold outside `decision/thresholds.yaml`.** Modules emit `code / score / source / span`; only the decision layer sets `threshold / fired / active / suppressed`. Tests must not hide thresholds either (the AST scan checks module tests).
3. **No cross-module imports.** Only `modules/registry.py::PIPELINE_ORDER` knows order; modules share work only through `ctx.signals`.
4. **Policy is proposed, not decided.** Anything that changes what the system concludes about content — verdicts, actions, what counts as degraded or clean, guard ownership, escalation rules — is presented to the owner with options. Implementation choices are fine to make.
5. **Spans are required where declared.** A module with `emits_spans = True` (m1, m6) puts the exact triggering span on every score and guard; one without a span is dropped and the module degrades.
6. Also binding: fail closed (never clean while degraded); a stub never prescribes HOW; no result committed before its protocol; a module never mutates `ctx.text`; heavy dependencies only in the owning module's `requirements.txt`; files use LF line endings (`.gitattributes`; `scripts/check.sh` breaks under CRLF).

---

## 5. Open questions

| Question | Owner |
|---|---|
| Missing spec sections — m2: does not catch, approach with named tools, required fixtures; m3: does not catch, required fixtures; m4: does not catch, required fixtures, a named tool; m5: does not catch, required fixtures; m6: does not catch, a named tool. | Project owner (spec author) |
| m0 spec.md acceptance still says "p95 latency under 1 ms per sample"; the budget is now per length in `thresholds.yaml` (decision #22). The criterion needs rewording. | Project owner (spec author) |
| Time-windowed repetition (decision #19): window length and time source are not defined, and `ThreadSignal` has no time field — a contract change. The thread signal is also not reachable from the CLI or API today. | Project owner (policy) + Osama (contract) |
| `contracts/fixtures/module_output.example.json` is stale (shows `offsets`); regenerating it needs an explicit instruction. | Osama |
| When is the frozen baseline created, so `fpr_increase_on_clean` can return (decision #20)? | Project owner |
| The pipeline itself clears module-set `threshold/fired/active` (`pipeline/run.py`) as enforcement; the literal audit rule says only `decision/fusion.py` assigns them. Accept as interpretation or move the clearing? | Project owner |
| m0 fixture has no items between 65 and 1000 characters, so the 280- and 1000-char latency bands are unmeasured. | m0 owner |
| m0 still passes negative-squared, parenthesized, regional-indicator and superscript Latin letters without a pattern — in scope or not? | m0 owner / project owner |
| m5 entry gate: availability of the Turkish sarcasm corpus (spec §2). | m5 owner |
| m1: confirm `terlik` availability and licence offline (spec §4.3, §8). | m1 owner |
| m6: written rules for `siz`, institution vs members, religion vs followers (spec §3). | m6 owner |
| Every placeholder in `decision/thresholds.yaml` (thresholds, actions, budgets, fast-path margin) must be derived on dev with `protocols/templates/threshold_derivation.md`. | Each module owner; actions: project owner |
| Module owners are `_assign_` in all seven specs. | Project owner |

---

## 6. If you are a fresh session, read these files in this order

1. `CLAUDE.md` — rules, axes, modules, entry points, commands.
2. `docs/HANDOVER.md` — this file.
3. `modules/README.md` — how to work inside a module.
4. `CONTRIBUTING.md` — stub rule, workflow, acceptance checklist, protocol templates.
5. `protocols/ADR-001-guard-scoping.md`, `ADR-002-turkish-label-keys.md`, `ADR-003-d1-ownership.md`.
6. `contracts/codes.py`, `contracts/schema.py`, `contracts/module_api.py`.
7. `decision/thresholds.yaml`, then `decision/fusion.py` and `decision/actions.py`.
8. `pipeline/run.py` and `modules/registry.py`.
9. `modules/m0_charsafe/` — the reference module (module, spec, tests, fixtures).
10. `modules/<the module you work on>/spec.md`.
11. `eval/README.md`, `eval/harness.py`, `eval/traps/traps.jsonl`.
12. `tests/test_architecture.py` — the rules as code.
