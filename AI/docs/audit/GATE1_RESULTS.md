# Gate 1 results — test infrastructure reliability

Verification Gate 1, 2026-09-17. Branch `audit/m1-m6`; the owner committed the Gate 0 documents
as `06520e4` during this gate, so the branch HEAD moved from `f063ddf` to `06520e4` with no code
change. Everything below was done on the working tree on top of that commit.

Scope discipline: only test and eval infrastructure changed. Untouched: every `modules/*/module.py`,
every `spec.md`, every ADR, `decision/thresholds.yaml`, `decision/*.py`, `pipeline/*.py`,
`contracts/`, `api/`, artifacts, fixtures, traps, datasets. The frozen questions Q1, Q2, Q3, Q5, Q6
were not answered; where a case depended on one it is labelled BLOCKED_BY_POLICY and not asserted.

---

## 1. Files changed

| file | kind | what |
|---|---|---|
| `AI/tests/test_binary_offensive.py` | **new** (12 tests) | Task 1: the real binary threshold at its boundary; the binary→counter path |
| `AI/tests/test_harness_gate1.py` | **new** (15 tests) | Tasks 2, 3, 7: harness degradation parity, binary trap observation and rule, stub reporting, pipeline-report binary block, provenance |
| `AI/tests/test_implementation_status.py` | **new** (5 tests) | Task 3: declared status vs `stub`, exact allowed skip set, stubs have no runnable behaviour test, m3 precondition |
| `AI/tests/test_signal_interfaces.py` | **new** (12 tests) | Task 4: m0→m1, m1→decision, m3→decision, pipeline→decision |
| `AI/tests/test_end_to_end.py` | **new** (7 tests) | Tasks 5, 6: six real-pipeline cases + bounded response, stage-named subTests, diagnostic dump |
| `AI/tests/test_pipeline.py` | modified (2 hunks) | Task 6 / G0-F: the m3 mask in `test_stub_modules_are_degraded_and_named` replaced by a named PRECONDITION failure; a stale "Five stub modules" comment corrected to three |
| `AI/eval/harness.py` | modified | Tasks 2, 3, 7: `degradation_record`, `observe`, `binary_fired`, `provenance`, `implementation_status`; `run_item` degrades like the pipeline; `check_traps` observations, `binary_fired`, `binary` rule; `evaluate` adds `implementation`, `degraded_items`, `provenance`; `summarize` prints status; `pipeline_budget_report` adds `binary_offensive_on_traps`, `trap_observations`, `degraded_modules`, `provenance` |
| `AI/eval/run_all.py` | modified | prints NOT VERIFIED modules, binary-fired traps, provenance line; `--results-dir` |
| `AI/eval/implementation_status.json` | **new** (data) | per-module declared status, `built`, `not_built`, `expected_skipped_tests`, `preconditions` |
| `AI/eval/README.md` | modified | documents the `binary` trap rule, the report blocks, HISTORICAL vs CURRENT results, `--results-dir` |
| `AI/docs/audit/TEST_SYSTEM_AUDIT.md` | modified | §6 Gate 1 mechanism updates, first observations, revised summary, remaining blind spots |
| `AI/docs/audit/VERIFICATION_PLAN.md` | modified | §8 Gate 0 criteria re-scored |
| `AI/docs/audit/GATE1_RESULTS.md` | **new** | this file |

Harness changes and the rule-4 / rule-6 scanners: `eval/` is scanned by
`tests/test_architecture.py` for numeric comparisons, threshold-named literals and decision-field
assignments, and `tests/` for stdlib-only imports. All architecture tests pass on the new code
(one adjustment was needed: the terlik availability probe in two test files uses
`importlib.util.find_spec`, not an import, because `tests/` is core).

---

## 2. Gap by gap

### 2.1 Binary boundary invisible to the suite (G0-B, ISSUE_TRIAGE G0-1)

- **Failure demonstrated before:** `grep 0.320188` over `tests/`, `modules/*/test_unit.py`,
  `eval/*.py`, `pipeline/*.py` → only `eval/m4_stage1b.py` (an offline integrity constant).
  `DecisionTest.setUp` overwrites every threshold; the binary tests inject 0.9 / 0.7 / 0.4.
- **Change:** `tests/test_binary_offensive.py`. Reads `fusion.load_config()` unchanged; asserts the
  entry is stage 1 raw-only; the value equals `EVAL confusion at t = …` in
  `protocols/threshold_derivation_binary_offensive_stage1.md` and `m4_stage1b.EXPECTED["stage1_t"]`;
  `fired = score >= t` at `nextafter(t, 0)`, `t`, `nextafter(t, 1)`, the protocol's tie row
  `0.32018762826919556` (read from the protocol text, asserted `< t` and not fired), a sweep over
  `[0, t/2, t−ε, t, t+ε, (t+1)/2, 1]`; absent → `fired None`; `True`, `"0.9"`, `None`, `[0.9]` →
  `fired None`; `post_offensive` follows `fired`; with the binary as the only signal and nothing
  degraded, `verdict == Action(binary.action)` and `actions.resolve` driver is
  `"binary_offensive"` with the "genel saldırganlık skoru" explanation; deciding twice is stable.
- **Result after:** 12 / 12 pass. Mutation check (`/tmp/gate1/mutate.py`, in-memory patches only):
  `>` instead of `>=` → 9 failing assertions; yaml value drifted to 0.5 → 2 failing assertions
  (both record comparisons). The threshold itself was not changed.

### 2.2 `post_is_offensive` binary branch and the counter (G0-7)

- **Before:** `test_post_is_offensive` covered content, form-only and degraded-only;
  `ThreadPipelineTest` used a content-scoring double.
- **Change:** `BinaryThroughPipelineTest` in `tests/test_binary_offensive.py`: a double in m3's slot
  publishing `raw_score = t` through the real config and a `ThreadBlock` → `repeat_count` 1..3,
  `thread.fired` only on the third, verdict = the more severe of the binary and thread actions
  (computed with `actions.severity`); at `t − ε` nothing is ever counted.
- **After:** pass.

### 2.3 Traps blind to the binary score (G0-D, Q18)

- **Failure demonstrated before** (`/tmp/gate1/before.py`): a module double publishing
  `raw_score 0.99` on a `must_not_fire: ["*"]` trap → `{"regressions": 0, …}`, the string
  `binary` absent from the trap report.
- **Change:** `check_traps` records an observation per trap (`content_fired`, `content_scored`,
  `binary`, `form_active`, `guards_active`, `guards_suppressed`, `degraded`, `post_offensive`,
  `verdict`, `driver`), the `binary_fired` id list and `binary_observable`; a module-scoped
  `binary: {"modules": [...], "must_not_fire": true}` rule turns a fire into a regression and a
  listed module without a numeric score into a failure. `pipeline_budget_report` adds
  `binary_offensive_on_traps` (fired in the full pipeline; flipped by the channel) and
  `trap_observations`. Neither the content flip-rate budget nor the exit code changed.
- **After:** the same double now yields `binary_fired: ["t1"]`, the observation
  `content_fired [] / binary.fired true / verdict review / driver binary_offensive`. Tests:
  `TrapBinaryTest` (6) and `PipelineBudgetBinaryTest` (3) pass.
- **Not done, by policy:** no committed trap carries the `binary` rule. Whether the collision
  traps must keep m3's score below the threshold is Q2 / Q18.

### 2.4 Stubs healthy in the harness (G0-C, Q21 / G0-2)

- **Failure demonstrated before** (`/tmp/gate1/before.py`): `DeobfModule` (stub) evaluated → no
  `stub`, no `degraded` anywhere in the report; summary line indistinguishable from an implemented
  module.
- **Change:** `run_item` writes `signals.pipeline.degraded` from `degradation_record`, which mirrors
  the pipeline's three kinds; `evaluate` adds `implementation` (from
  `eval/implementation_status.json`, cross-checked with `stub`) and `degraded_items`; `summarize`
  prints `[STUB]`, `degraded_items=…` and a `** NOT VERIFIED **` line; `run_all` prints the
  NOT VERIFIED list.
- **After:** `m2_deobf [STUB]: … degraded_items=1 …` + `** NOT VERIFIED: stub - … **` (same for
  m5, m6 in the full run). `test_harness_degrades_exactly_as_the_pipeline_does` pins the harness
  entry equal to `Pipeline.analyze`'s for a stub, a raising module, an invalid-output module and a
  healthy one. A stub's per-item verdict is `review`, never `clean`; the predicted set for scoring
  is unchanged.

### 2.5 Skipped behaviour tests indistinguishable from passing ones (G0-C, G0-9)

- **Before:** m2 / m5 / m6 behaviour tests `@unittest.skip`; m3's five behaviour tests
  `skipUnless(artifact)`; `unittest` exits 0 on skips; nothing records the expected set.
- **Change:** `eval/implementation_status.json` declares `expected_skipped_tests` per module;
  `tests/test_implementation_status.py` loads each `test_unit.py` through the unittest loader and
  fails on any skip outside the declared set, on a STUB declaration that disagrees with the `stub`
  flag, on a stub with a runnable behaviour test, on a PARTIAL module without a `not_built` list,
  and on a missing m3 artifact (PRECONDITION failure with the declared preconditions in the
  message).
- **After:** 5 / 5 pass with the artifact present (m3's expected skip set is empty and holds).

### 2.6 Producer / consumer interfaces unchecked (G0-E)

- **Before:** nothing compared signal key names across a module boundary.
- **Change:** `tests/test_signal_interfaces.py` (12 tests). m0→m1: signal key set
  `{_offsets, offsets_identity, invisible_removed, homoglyphs_mapped, charsafe_changed}`, types,
  `_offsets` invariants (length = charsafe length, ints, in range, non-decreasing, identity flag
  consistent) on nine inputs, the frozen tuple form m1 receives through the pipeline and
  `LexiconModule._raw_offsets` reading it, `_offsets` absent from the response, and a real m1 span
  landing on the original `"ap​tal"`. m1→decision: the three hit signals present and boolean
  on every input, `lexicon_hit == raw or norm`, `lexicon_hit_norm` false without a channel, the
  stage-1b script reading `"lexicon_hit_raw"` and `fusion.lookup_signal` resolving all three.
  m3→decision: the yaml path splits into m3's name and `raw_score`; `ARTIFACT_ID` appears in the
  yaml's validity statement and as a MANIFEST row; the real module publishes exactly
  `{raw_score, artifact}`, no `norm_score`, and `decide` reads it on the single `raw` channel.
  pipeline→decision: `signals.pipeline` keys, degraded entry shape and kinds, `emits_spans` map,
  `actions.degraded_modules` reading it; `signals.decision` keys.
- **After:** 12 / 12 pass. Q5 (m2 offset map) and Q6 (m6 routes) deliberately not defined.

### 2.7 No real end-to-end observability (G0-A, G0-4)

- **Before:** one clean sentence asserting `review` and shape; m3 masked.
- **Change:** `tests/test_end_to_end.py` on the real registry and config:
  1. `"Bu bir test cumlesi"` — no hit, no content, no guards, binary not fired
     (CURRENT_ARTIFACT_OBSERVATION; the frozen contract example pins 0.021), degraded exactly
     `[m2, m6, m5]` as stubs, verdict `review` driven by `degraded`, explanation names the stubs.
  2. `"Onlar aptallar"` — `A1` from `m1_lexicon@raw` at `(6, 14)` = `"aptallar"`, `family_a`
     resolved as `none` → the configured `none` code, threshold from the config, binary fired,
     nothing suppressed, `post_offensive`, verdict = the more severe of the A1 and binary actions,
     driver accordingly.
  3. `"SIKINTI YOK"` — `DOTLESS_I` pattern, `charsafe_changed`, no hit, `SUBSTRING_COLLISION` at
     `(0, 7)` active with nothing to suppress, `form.active` recomputed from the config, binary
     not fired, verdict `review` / `degraded`.
  4. `"Sen bir gerizekalısın, amcam da öyle"` — `A1` at `(8, 21)`, collision guard at `(23, 28)`,
     guard active, `suppressed == []` (ADR-001 non-overlap), score still fired, binary fired,
     verdict as in 2.
  5. `"ap​tal herif"` — `ZERO_WIDTH` at `(2, 3)`, `offsets_identity` false, one invisible
     removed, `A1` at `(0, 6)` = `"ap​tal"` in the ORIGINAL text, `ZERO_WIDTH` active, score
     fired. Binary state and verdict recorded, NOT asserted (Q3).
  6. Three `"Onlar aptallar"` posts from `u1` to `u2` — `repeat_count` 1..3, thread fires on the
     third, first verdict as in 2, third = the more severe of A1 / binary / thread actions; a clean
     post afterwards keeps `repeat_count 3`, does not fire, verdict `review`.
  7. Bounded, serialisable response.
  Every assertion runs in `subTest(stage=…)`; a failure message carries `diagnose(result)`.
- **After:** 7 / 7 pass. Mutation check (`/tmp/gate1/mutate_e2e.py`): guards suppressing every
  score → the only failure is `stage='GUARD_APPLICATION'`; binary silenced → `DECISION_THRESHOLD/
  binary`, `DECISION_THRESHOLD/binary consistency`, `FINAL_ACTION`; spans lost in fusion →
  `PIPELINE_MERGE`. One restructuring was needed for this: `channel_scores.fired` is recorded
  after guards run, so "fired" assertions moved to the GUARD_APPLICATION stage and the threshold
  stage asserts `score.threshold` and `score >= threshold` instead.

### 2.8 Reproducibility (G0-G, Q22 / G0-6, G0-10)

- **Before:** result files carried no commit or digest; local files mixed 23- and 33-trap runs and
  5 / 20 / 200 repeats; the m1 unit trap test reads the working-tree trap file.
- **Change:** `provenance` block in every module report and in `pipeline.json` (`git_head`,
  `git_dirty`, `git_untracked_under_ai`, python version, sha256 of fixture / traps / thresholds /
  status file, `traps_n`, `latency_repeats`, `n_boot`); `run_all --results-dir`; `run_all` prints
  `CURRENT_REPRODUCIBLE_RESULT` only when `git_dirty` is false; `eval/README.md` defines the two
  classes.
- **Not done, on purpose:** the historical files in `eval/results/` were not overwritten or
  normalised; the Gate 1 run went to a temporary directory. Their classification is in §7.

---

## 3. Test results

Commands (from `AI/`, project venv Python 3.14.0):

```
python -m unittest tests.test_binary_offensive -v                     # 12 ok
python -m unittest tests.test_harness_gate1 tests.test_implementation_status tests.test_signal_interfaces
                                                                     # 31 ok after the ordering fix in implementation_status (see §5)
python -m unittest tests.test_end_to_end tests.test_pipeline          # 42 ok
python -m unittest tests.test_architecture tests.test_harness         # 29 ok (rule 4 / rule 6 scanners accept the new eval code)
python -m unittest discover -p "test_*.py" -v                         # full suite, see below
python -m eval.run_all --latency-repeats 3 --n-boot 100 --results-dir <temp>   # exercised the reports; exit 1 on the latency placeholder (see §7)
```

Full suite after Gate 1 (`/tmp/gate1/suite.log`): **319 tests, OK, 4 skipped, exit 0** in 72 s.
Before Gate 1: 268 tests, 4 skipped. The 51 added tests are the five new files. The four skips are
exactly the declared set in `eval/implementation_status.json` (m2 ×2, m5 ×1, m6 ×1); m3's five
artifact-gated tests ran because the artifact is present, and `test_implementation_status.py` would
fail rather than let them skip.

Mutation checks (in-memory patches, nothing on disk):

| mutation | file | outcome |
|---|---|---|
| binary rule `>` instead of `>=` | `/tmp/gate1/mutate.py` | 9 assertions fail |
| binary threshold drifted to 0.5 | `/tmp/gate1/mutate.py` | 2 assertions fail (derivation record, stage-1b constant) |
| guards suppress every fired score | `/tmp/gate1/mutate_e2e.py` | fails at `GUARD_APPLICATION` only |
| binary never fires | `/tmp/gate1/mutate_e2e.py` | fails at `DECISION_THRESHOLD/binary`, `…/binary consistency`, `FINAL_ACTION` |
| spans dropped in fusion | `/tmp/gate1/mutate_e2e.py` | fails at `PIPELINE_MERGE` only |
| binary double on a trap, before the change | `/tmp/gate1/before.py` | `regressions 0`, no `binary` in the report |
| same, after | `/tmp/gate1/before.py` | `binary_fired ["t1"]`, observation with `driver binary_offensive` |
| stub evaluated, before | `/tmp/gate1/before.py` | no `stub` / `degraded` in the report |
| same, after | `/tmp/gate1/before.py` | `[STUB] … degraded_items=1`, `NOT VERIFIED` |

---

## 4. Is `binary_offensive` now fully observable?

Observable in every mechanism that decides or measures:

| mechanism | observes the binary state | asserts on it |
|---|---|---|
| decision tests (`test_binary_offensive.py`) | yes, at the real boundary | yes |
| thread counter | yes (binary-only double) | yes |
| traps (`check_traps`) | yes: per-trap observation, `binary_fired`, `binary_observable` | only where a trap carries a `binary` rule — none committed (policy) |
| per-module harness reports | yes (traps section; the fixture predicted set is unchanged by design) | no gold exists for it |
| pipeline budget report | yes: `binary_offensive_on_traps`, `trap_observations` | reported, not budgeted (policy) |
| end-to-end tests | yes, with the consistency `fired == score >= t` on every case and the observed state on five | yes (observed state labelled CURRENT_ARTIFACT_OBSERVATION) |
| interface tests | yes: path, key, artifact id, channel set | yes |
| `check.sh` exit code | no change | no |

Remaining gap: the fixture-level per-code metrics still have no code for the binary and no
labelled m3 fixture; a wrong `raw_score` on a labelled sentence would be visible only through the
trap observations and the six end-to-end pins. That needs data, not infrastructure.

---

## 5. Can stubs still produce misleading green evaluation?

No, in the sense that mattered: every stub result now states `NOT VERIFIED`, degrades every
item, and its verdict is never `clean`; `run_all` lists the stubs by name; an undeclared skip
fails the suite; the declared status cannot disagree with the `stub` flag without failing.

Yes, in a narrower sense that is unchanged by design: `run_all`'s exit code still counts trap
regressions and budgets only, so a green `check.sh` still means "no crash, no content regression,
budgets met" and not "verified". The printed output and the report files say what was measured;
the exit code was not turned into a verification verdict because that is a process decision
(HANDOVER #15 allows stubs to exist).

One self-correction during the gate: `implementation_status` first reported a stub whose
declaration was wrong as `NOT VERIFIED` (stub check first). The data error must win, so the
order was changed to report `INCONSISTENT` first; `test_implementation_status_disagreeing_with_the_stub_flag_is_reported`
pins it.

---

## 6. Production observations exposed and intentionally NOT fixed

1. **m3's binary score fires on four collision traps.** In the full pipeline and in m3's own
   evaluation: `trap-008` "sikke" (raw_score 0.984), `trap-017` "Eski sikke koleksiyonu" (0.493),
   `trap-030` "SİKKE" (0.442), `trap-032` "KLASİK" (0.658); threshold 0.320188. On each: no content
   code fires, the `SUBSTRING_COLLISION` guard is active, verdict `review`, driver
   `binary_offensive`. These are clean Turkish words ("coin", "classic") that the OFF/NOT model
   scores as offensive. Before Gate 1 they read as `traps 0/33`. Not fixed: whether a binary fire on
   a collision trap is a regression is Q2 / Q18; whether the artifact should be re-thresholded or
   the guard should reach the binary score is a policy and model question. Recorded as
   BLOCKED_BY_POLICY with the evidence in `TEST_SYSTEM_AUDIT.md` §6.2.
2. **m1 adversarial latency remains over budget** (5000-char adversarial item p95 ≈ 338 ms on
   this run, band budget 140 ms; `adversarial_over_budget = True`), as the Gate 0 audit recorded
   (Q12). Published, not hidden, not fixed.
3. **Pipeline latency p95 over the 250 ms placeholder** in both Gate 1 runs: 383 ms with 3
   repeats while the unit suite ran concurrently, and 283 ms (p50 48.6 ms) with 3 repeats
   uncontended. The historical 200-repeat run measured 128.6 ms. Three repeats per text make the
   p95 the fifteenth-slowest of 303 timings and include first-run effects; the budget is a
   placeholder (Q25). Recorded so the exit code 1 of those runs is not misread; not a Gate 1
   subject and not fixed. The binary-fired trap set was identical in the uncontended run.
4. No other production defect surfaced: the six end-to-end cases behaved as the repository says
   they should, with the Q1 / Q2 / Q3 outcomes left unjudged.

---

## 7. Reproducibility classification

| result | classification | reason |
|---|---|---|
| `eval/results/m0_charsafe.json`, `m1_lexicon.json` (2026-09-16, 33 traps, 5 / 20 repeats) | HISTORICAL_RESULT | no provenance block; produced against the uncommitted trap file |
| `eval/results/m2_deobf.json`, `m3_encoder.json`, `m4_implicit.json`, `m5_sarcasm.json`, `m6_target.json` (2026-09-16, 23 traps, 200 repeats) | HISTORICAL_RESULT | no provenance; produced against the HEAD trap file; stubs among them read healthy under the old harness |
| `eval/results/pipeline.json` (2026-09-16, 23 traps, 200 repeats) | HISTORICAL_RESULT | no provenance; latency 128.6 ms p95 is the only uncontended pipeline latency on record |
| `eval/results/m4_stage1b.json` (tracked, protocol-bound) | HISTORICAL_RESULT, protocol-verified | its own integrity hashes; unaffected by this gate |
| Gate 1 run in a temporary directory (`--results-dir`, 33 traps, 3 repeats, `git_dirty = true`) | NOT REPRODUCIBLE (dirty tree); exercised the new reports only | provenance recorded; latency contaminated by concurrency |

None of the historical files was modified, moved or regenerated. The first
CURRENT_REPRODUCIBLE_RESULT requires the owner to commit the baseline (`BASELINE_WORKTREE.md` §6,
now also including the Gate 1 files) and run `python -m eval.run_all` once on that commit.

Tests that depend on working-tree data: `modules/m1_lexicon/test_unit.py::test_collision_traps_never_fire`
reads `eval/traps/traps.jsonl` as it is on disk (33 traps today, 23 at HEAD). The new
`tests/test_end_to_end.py` and `tests/test_signal_interfaces.py` read no data file except the
committed derivation protocol and `thresholds.yaml`. The suite is deterministic for a given tree;
what the tree is remains the owner's commit decision.

---

## 8. Policy-blocked cases (recorded, not decided)

| case | question | where it is parked |
|---|---|---|
| binary fires on collision traps 008 / 017 / 030 / 032 | Q2 / Q18: is a binary fire on a clean collision word a regression, and can a guard reach it? | `binary_fired` in every trap report; the `binary` rule exists and is attached to nothing |
| A-family hit that m3 scores below `t` while m6 is a stub | Q1: nudge under degradation | no end-to-end case asserts it |
| non-human target + binary fire | Q2 | no case (m6 is a stub anyway) |
| verdict on `"ap​tal herif"` | Q3: m3 scores raw text | end-to-end case 5 asserts m0 → m1 only; binary state recorded |
| normalized-channel spans | Q5 | no interface test; not defined |
| m6 result-field vs signals route | Q6 | no interface test; not defined |

---

## 9. Gate 1 verdict against the Gate 0 criteria

| criterion | status |
|---|---|
| G0-A wrong verdict detectable | PASS |
| G0-B wrong boundary detectable | PASS |
| G0-C degraded / stub cannot look healthy | PASS |
| G0-D binary observable by regression verification | PASS (observed everywhere; asserted where policy allows) |
| G0-E interface mismatches detectable | PASS for the interfaces with an oracle |
| G0-F integration vs module failures distinguishable | PASS |
| G0-G reproducible baseline | FAIL — owner commit pending |

**Gate 1: PASS on infrastructure (G0-A–F); the baseline criterion G0-G stays FAIL until the owner
commits.** m0 verification has not started.
