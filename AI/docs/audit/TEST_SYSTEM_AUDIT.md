# Test-system audit — can the current verification system be trusted?

Verification Gate 0, 2026-09-17. Branch `audit/m1-m6` at `f063ddf` plus the working tree of
`BASELINE_WORKTREE.md`. Every statement below is read from the source of the mechanism itself
(`AI/tests/*.py`, `AI/modules/*/test_unit.py`, `AI/eval/harness.py`, `AI/eval/run_all.py`,
`AI/pipeline/contract_example.py`, `AI/scripts/check.sh`); line numbers refer to files under `AI/`.
No test was modified and none was added. Test counts are counts of `def test_` methods in source
(268 across 15 files), not a run.

The question for each mechanism is the same: what does it observe, what does it ignore, which
failures can it catch, which can it not, and can a passing result today be misleading.

---

## 1. Inventory

| mechanism | files | methods | what triggers it |
|---|---|---|---|
| Module unit tests, generic contract part | `modules/*/test_unit.py` (`*ContractTest` classes, plus `test_contract_shape`, `test_input_not_mutated`, `test_never_raises`) | 8 per module (m0 has its own 3 + 42 behaviour) | `unittest discover`, `check.sh` |
| Module unit tests, behaviour part | m0: 42, m1: 11, m3: 6 (5 need the artifact), m4: 1, m2 / m5 / m6: 2 / 1 / 1 all `@unittest.skip` | | same |
| Architecture tests | `tests/test_architecture.py` (17) | | same |
| Contract tests | `tests/test_contracts.py` (15); frozen-example gate `pipeline/contract_example.py --check` | | same; `check.sh` |
| Trap tests | `eval/traps/traps.jsonl` (23 at HEAD, 33 in the working tree) through `ModuleEvaluator.check_traps`; also `m1 test_collision_traps_never_fire` | | `eval.run_all`, `check.sh`; m1 unit test |
| Eval harness | `eval/harness.py::ModuleEvaluator` (per module, per code, bootstrap CIs, representation metrics, latency bands) | | `python -m modules.<m>.eval`, `eval.run_all` |
| Pipeline budget tests | `eval/harness.py::pipeline_budget_report` (flip rate, pipeline latency); `tests/test_harness.py::PipelineBudgetTest`, `LatencyBudgetTest` | 12 in `test_harness.py` | `eval.run_all`; unit suite |
| Decision-layer tests | `tests/test_decision.py` (45) | | unit suite |
| Integration tests | `tests/test_pipeline.py` (35), `tests/test_thread_counter.py` (20), `tests/test_api.py` (6) | | unit suite |
| End-to-end verdict tests | `test_default_pipeline_on_clean_sentence`, `test_stub_modules_are_degraded_and_named`, `ThreadPipelineTest` (double), `test_analyze_returns_contract`; `eval/testsuite/dev.jsonl` (2 format examples) | | unit suite; nothing reads `testsuite/` except `test_gold_data` |
| Gold-data hygiene | `tests/test_gold_data.py` (3) | | unit suite |
| Gate script | `scripts/check.sh`: unit + architecture → pipeline smoke → `eval.run_all` → contract example current → `contracts/` unchanged vs `BASE_REF` | | manual / pre-merge |

---

## 2. Mechanism by mechanism

### 2.1 Module unit tests — generic contract part

Present identically in m1–m6 (`test_name_matches_folder`, `test_provides_are_contract_fields`,
`test_process_returns_ok_module_output`, `test_output_stays_within_provides`,
`test_never_sets_decision_fields`, `test_contract_shape`, `test_input_not_mutated`,
`test_never_raises`); m0 has the last three.

- **Observes:** the module's name and `provides`; that `process()` returns an `ok` `ModuleOutput`
  with the right `module` / `version` / `latency_ms` types; that populated fields ⊆ `provides`; that
  no content / guard carries a decision-owned value; that `ctx` and an upstream signals dict are
  unchanged after a call on ten hostile inputs; that no hostile input raises.
- **Ignores:** everything the module is *for*. A module returning `ModuleOutput(notes=[…])` passes
  all eight. Spans, sources, scores, signals content and the specified outputs are not checked here.
- **Catches:** a module that raises, mutates input, sets `fired`/`threshold`, returns an undeclared
  field or the wrong `name`.
- **Cannot catch:** a stub; a module that emits nothing; a module that emits the wrong code or the
  wrong span; any behaviour regression.
- **Misleading pass?** Yes. For m2, m5 and m6 the entire non-skipped unit suite is this part
  (8 of 9–10 methods). A green run says "the stub is a well-formed stub", nothing more. m4's suite
  is this part plus one test that pins "not a stub, emits only its note".

### 2.2 Module unit tests — behaviour part

- **m0 (42 tests):** observes `charsafe_text`, `form.patterns` codes / confidences / spans,
  `_offsets` alignment, `charsafe_changed`, per-pass behaviour (invisible, combining marks, styled
  Latin, confusables, Turkish casing) and the accepted flag-pair gap. Catches essentially any
  behaviour change in the five passes. Cannot catch whether the *specified* three-step §4 is the
  intended design (Q14): the tests pin the code, not the spec. Not misleading for what it covers.
- **m1 (11 tests):** observes zero content on every trap plus a `SUBSTRING_COLLISION` per trap;
  boundary matching on inflected roots; collisions for roots inside clean words; `SIKINTI` /
  `APTALLAR`; channel tagging under the same-length assumption; flag-only path without an offset
  map; spans through m0 offsets; boolean signals on every input; a span on every item;
  `NON_HUMAN_TARGET` from a faked m6 signal; determinism. Catches regressions in what is built.
  Cannot catch: `A4` / `HOMONYM` absence (no test, no skip marker: the gap is invisible to the
  suite); a wrong score value (always 1.0, never asserted against a spec value); latency; the
  cross-channel veto (Q8); the 49 % collision base rate (Q20). `test_collision_traps_never_fire`
  reads the *working-tree* trap file, so its pass depends on uncommitted data (G0-10). Not
  misleading for what it asserts; misleading if read as "m1 spec §8 met".
- **m3 (6 tests, 5 gated on the artifact):** observes fail-closed on a missing artifact, no
  network at load, exactly `{raw_score, artifact}` with `raw_score ∈ [0, 1]` and empty content,
  independence from charsafe / normalized text, truncation note, determinism. Cannot catch: a
  wrong *value* of `raw_score` (only type and range are asserted; the artifact-equivalence check
  lives in the derivation protocol, not in a test); a silently changed checkpoint is caught by the
  sha256 in `_load`, not by a test; the absence of heads / `norm_score` / content (specified, not
  built, no skip marker). On a machine without the artifact 5 of 6 skip and the suite is green.
  Misleading if read as "m3 spec §4 met".
- **m4 (1 test):** pins non-stub + note only. Cannot observe stage 1 at all (the threshold lives in
  the yaml and is exercised nowhere with its real value, see §3).
- **m2 / m5 / m6:** every behaviour test is `@unittest.skip("TODO …")`. `unittest` exits 0 on
  skips; `check.sh` does not count them. A stub is invisible to the exit code.

### 2.3 Architecture tests (`tests/test_architecture.py`, 17)

- **Observes:** import graph between modules (rule 2) and the eval / test allow-lists; an AST scan
  for numeric comparisons, threshold-like names and float literals in ordering asserts in module
  code, `eval.py` and `test_unit.py` (rule 4); assignment of decision-owned fields outside
  `fusion.py`; stdlib-only core; per-module declared dependencies; module layout and the eight
  required spec sections (recommended ones warn); `emits_spans` declared everywhere; entry-point
  convention; m6 before m1; registry class names. Self-tests prove the scanners catch what they
  claim.
- **Ignores:** behaviour of any kind; the *content* of specs; signal keys and their consumers.
- **Catches:** a hidden threshold in a module, a cross-module import, a module writing `fired`, a
  registry reorder that puts m1 before m6.
- **Cannot catch:** a threshold hidden as a *data file* or a string; a signal-name mismatch
  between producer and consumer (e.g. `lexicon_hit` vs `lexicon_hit_raw`, Q13); a spec whose
  sections exist but say something the code does not do.
- **Misleading pass?** No, within its claim. It is a rules-as-code check and says so.

### 2.4 Contract tests (`tests/test_contracts.py`, 15) and the frozen-example gate

- **Observes:** enum completeness and Turkish labels; `ACTION_PRECEDENCE`; `fired()` / `top()` on a
  hand-built result; JSON round-trip; that both examples regenerate byte-identically and match the
  contract shape; `Context` read-only; `best_text` default; `BaseModule` exception wrapping and
  load failure.
- **Frozen-example gate** (`contract_example.py --check`): regenerates `analysis_result.example.json`
  from a real run on `"Bu bir test cumlesi"` (latency fields replaced by 0.0, `artifact_hash` real,
  m3 `raw_score` real at 0.0214…) and `module_output.example.json` from m0 on `SIKINTI`, and
  compares bytes.
- **Catches:** any change to the yaml, a module version bump, a change in m0's output on `SIKINTI`,
  a change in m3's probability on that one sentence, a change in the response shape or key order,
  a change in the degraded list or explanation for that sentence.
- **Cannot catch:** any behaviour on any other input. The example's verdict is `review` driven by
  degradation, so a wrong verdict on an offensive post is outside its reach. On a machine without
  the m3 artifact the gate fails for an environmental reason and reads like a contract failure
  (G0-8).
- **Misleading pass?** Only in the sense that "contract example current" is often read as "the
  pipeline is unchanged"; it is "the pipeline is unchanged on one clean sentence".

### 2.5 Trap tests (`eval/traps/traps.jsonl` via `check_traps`; m1's own trap test)

`check_traps` (`harness.py:407-451`) runs each trap through the module alone, merges into a fresh
result, runs `fusion.decide` and checks:

- `must_not_fire`: `{code for s in result.fired()}` — content codes marked fired **after**
  thresholds and guards, content only.
- `expect`: raw output fields, compared only when the module produced them (`got is not None`).
- `form` / `guards` with `modules: [...]`: codes the listed module **emitted** (before thresholds).
  A `must` a stub cannot meet is `pending`; `must_not` always applies.

Today all 33 traps are m0 / m1 collision traps: `must_not_fire: ["*"]`, m0 `form.must_not` (or
`must: [DOTLESS_I]` on the ten new ones), m1 `guards.must: [SUBSTRING_COLLISION]`.

- **Observes:** whether any content code fired; which form patterns m0 emitted; which guards m1
  emitted.
- **Ignores:** `signals.decision.binary_offensive` entirely; `result.verdict`; the `explanation`;
  `result.target`; the score value; spans; the notes. For m3, m4, m5, m6 and m2 a trap therefore
  reduces to "no content code fired", which is trivially true for modules that emit no content.
- **Catches:** m1 firing on a collision word; m0 mis-mapping a trap text; m1 forgetting the
  collision guard on a trap.
- **Cannot catch:** m3 scoring a trap word as OFF above 0.320188 (the verdict on that trap would be
  `review` in the real pipeline; the trap reports 0 regressions); a wrong span; a guard emitted on
  the wrong span; any behaviour of m2 / m5 / m6 (all `pending` or vacuous).
- **Misleading pass?** Yes, for every module except m0 and m1. The committed result files for
  m2–m6 say `traps 0/23 regressions` and this is the emptiness of the modules, not their
  correctness. For m3 in particular "0/23" coexists with a live threshold that the traps never
  look at (§3).

### 2.6 Eval harness (`ModuleEvaluator.evaluate`, `run_item`)

- **Observes:** per fixture item, the module's output merged through `Pipeline._merge` into a
  fresh result with the fixture's `context.signals` copied in, decided by `fusion.decide` with the
  real yaml; predicted = fired content codes ∪ `form.active` ∪ active guard codes ∪
  `target:<type>`; gold = `expected` / `expect_patterns`; per-code TP/FP/FN over the fixed
  `code_space(module)` with percentile-bootstrap CIs; capture rate and damage rate for
  representation modules; latency in `clean` / `adversarial` columns with per-length bands;
  `module_errors` when `ok` is false.
- **Ignores:** `signals.pipeline.degraded` — `run_item` writes `{"emits_spans": …}` only
  (`harness.py:258`), so no fixture run is ever degraded, a stub's clean item is a true negative
  and its verdict is `clean`; `binary_offensive` (computed inside `decide` when the fixture's
  signals carry `m3_encoder.raw_score`, but never added to `predicted`); the verdict; spans;
  score values.
- **Catches:** a module that fires the wrong code on a labelled item; a representation module that
  damages a clean item; latency over a clean band; `ok=False` on an item.
- **Cannot catch:** a stub (looks healthy, Q21/G0-2); a wrong `raw_score` (m3's fixture has one
  clean item with `expected: []`, and the binary fire is not a predicted code, so even a
  `raw_score` of 0.99 on "Bugün hava çok güzel" yields no per-code FP); a wrong m1 score value
  (1.0 always fires at 0.5); a wrong threshold in the yaml (the yaml is the oracle *and* the input).
- **Misleading pass?** Yes for m2–m6: their fixtures hold one real clean item, every code has zero
  support, and the result file is structurally identical to a healthy one. Yes for m3 in the
  specific sense that the only live number it produces is not scored.

### 2.7 Pipeline budget tests (`pipeline_budget_report`; `test_harness.py`)

- **Flip rate:** for each trap, `without_channel.analyze(text).fired()` vs
  `with_channel.analyze(text).fired()`; a flip is "fired only with m2". Observes content codes
  only. Ignores the binary fire and the verdict. With m2 a stub the two pipelines are identical and
  the rate is 0.0 by construction. Cannot catch a future m2 whose repairs raise m3's score over the
  threshold on a clean trap (that flip would be verdict-visible, budget-invisible).
- **Pipeline latency:** whole pipeline over trap and fixture texts, `runs` repeats; p95 against
  `budgets.latency_p95_ms`. Observes wall-clock only. Not misleading; the placeholder budget is.
- **`test_harness.py`:** proves the harness's own arithmetic (per-code not pooled, fixed code list,
  representation metrics, separate trap latency, repeated timings, `must`/`must_not` semantics,
  stub-pending rule, flip counting, length bands, clean-gates / adversarial-published). These are
  self-tests of the measuring instrument and are sound for what they assert. They do not assert
  that `predicted` includes the binary fire or that a stub is marked degraded, because the harness
  does neither.

### 2.8 Decision-layer tests (`tests/test_decision.py`, 45)

- **Observes:** config load / validation failures; guard scoping by module and span with the
  ADR-001 fallback; max fusion across channels; most-severe action; `threshold_when` branches and
  fallback; binary offensive firing with an injected config (threshold 0.9 / 0.7 / 0.4 and two
  channels); absent scores do not fire; form active; thread rule (fires only on an offensive post,
  same target); fast path disabled by default and its hit logic; decision-field reset and idempotent
  `decide`; `post_is_offensive` for content / form-only / degraded-only; family-A assignment from
  the target with the low-confidence rule; the A4 exception; `NON_HUMAN_TARGET` suppression;
  stage 1 has no `threshold_when`.
- **Ignores:** the real yaml's numbers — `setUp` overwrites every category and guard threshold to
  0.5 and pins three actions; the binary tests replace the whole binary section. The derived
  0.320188 is referenced by no test (verified by grep over `tests/`, `modules/*/test_unit.py`,
  `eval/*.py`, `pipeline/*.py`). The `binary.fired` branch of `post_is_offensive` is not exercised
  (`test_post_is_offensive` uses A2 content, form only, degraded only). Degradation-driven upgrade
  is exercised in `test_pipeline.py`, not here.
- **Catches:** any logic regression in fusion, guards, thread rule, family-A assignment, reset.
- **Cannot catch:** a wrong or drifted value in `thresholds.yaml` (only shape is validated:
  `test_artifact_status_and_derived_on_must_agree`, `test_unread_keys_are_gone`); a wrong
  boundary rule at the real threshold (the `>=` vs `>` tie documented in the derivation protocol
  is tested nowhere); the Q1 / Q2 interactions (probes A and D in `PIPELINE_FLOW.md` §7 were
  run by hand, not by a test).
- **Misleading pass?** Not for logic. Misleading if read as "the shipped thresholds behave as
  derived": the suite deliberately never looks at them.

### 2.9 Integration tests (`test_pipeline.py`, `test_thread_counter.py`, `test_api.py`)

- **Observes:** module loop mechanics with doubles (`_Scorer`, `_Charsafe`, `_Spy`, `_Emit`,
  `_InitBoom`, `_SpanLexicon`, `_TextScorer`): charsafe and signals reach the next module; stubs
  are degraded and named; clean is reachable only without degradation; undeclared fields dropped;
  decision fields cleared; fast path skips (with an injected config that enables it); a failing /
  raising / unconstructible / bad-loading module degrades instead of aborting; NaN / None / out of
  range / wrong type / foreign source / bad span dropped as `invalid_output`; a severe verdict
  stands under degradation with the "incomplete" clause; signals are read-only; `_` keys stay out
  of the response; artifact hash covers the in-memory config; span enforcement; thread counting
  by receive time, window expiry, self-directed exclusion, per-instance state, refused timestamp;
  CLI thread block; API status codes and JSON on failure.
- **Ignores:** real module behaviour (every behavioural assertion uses a double); the real yaml
  (tests inject `A1 → block`, fast path enabled, etc.); the binary score path through the counter.
- **Catches:** almost any regression in `Pipeline.analyze`, `_merge`, `deep_freeze`, the counter,
  the CLI parsing and the API's error handling.
- **Cannot catch:** a wrong verdict on a real post through real modules (only the two default
  pipeline tests use real modules, and they assert `review` and shape); a real-module integration
  mismatch such as m1 reading a signal key m6 will not publish, or the two-route target
  disagreement (Q6); the Q1 nudge outcome.
- **Misleading pass?** `test_default_pipeline_on_clean_sentence` carries the comment "Five stub
  modules" (there are three) and asserts `review`, which any degraded state produces. It passes
  with or without the m3 artifact, with m1 present or failing, and with any verdict-changing
  regression that still lands on `review`. `test_stub_modules_are_degraded_and_named` explicitly
  removes m3 from what it checks. Both are green in states that differ materially.

### 2.10 End-to-end verdict tests and the gold set

- There is no end-to-end gold set. `eval/testsuite/dev.jsonl` contains two format examples
  (`annotators: 0`, `source: format-example`) and nothing reads it except the code-hygiene test.
- The only real-module end-to-end assertions are the two default-pipeline tests above, the API
  contract test (shape only) and the contract-example gate (one clean sentence).
- The verdict-changing behaviours observed in `PIPELINE_FLOW.md` §7 (binary drives `review` on
  `Onlar aptallar`; A1 at `[6,14]`; collision guard on `amcam`; ZWSP reaching BERT; thread
  escalate on the third repeat; threat sentence invisible) exist as a hand-run table, not as tests.
- **Misleading pass?** There is nothing to pass. The absence is the finding.

### 2.11 Gold-data hygiene (`test_gold_data.py`)

Observes that every code in fixtures, traps and testsuite exists in the code books and that trap
module names are real. Catches a typo that would create an unpredictable label. Cannot catch a
wrong label. Sound and narrow.

### 2.12 The gate script (`scripts/check.sh`)

Runs, in order: unit + architecture; pipeline smoke (one sentence, output discarded);
`eval.run_all` (exit 1 on any trap regression or a budget breach); contract example current;
`contracts/` unchanged vs `BASE_REF`. It does not: count skips; compare eval numbers with a
reference (it only checks regressions and budgets); require the m3 artifact explicitly (it fails
indirectly through the example gate); check line endings; check that the working tree is clean.
A green `check.sh` today certifies: no crash, no trap firing a content code, flip rate 0 (by
construction), latency under a placeholder, one clean sentence unchanged, contracts untouched.

---

## 3. The specific finding: `binary_offensive` is verdict-relevant and measurement-invisible

Where the binary score is **read**:

| consumer | reads it | effect |
|---|---|---|
| `fusion.apply_binary_offensive` (decide_post step 1b) | yes | `signals.decision.binary_offensive = {threshold, channels, fired, action, …}` |
| `actions.resolve` | yes | if fired, verdict ≥ `review` (`binary_offensive.action`) |
| `actions.explain` | yes | "genel saldırganlık skoru" driver |
| `fusion.post_is_offensive` | yes | a binary-only post counts as a repeat for the thread counter |
| `fusion.fast_path_hit` | no (disabled anyway) | — |

Where the binary score is **checked**:

| mechanism | sees `binary_offensive`? | evidence |
|---|---|---|
| `check_traps` `must_not_fire` | no — `result.fired()` only | `harness.py:428` |
| `check_traps` `expect` / `form` / `guards` | no | `harness.py:429-445` |
| `ModuleEvaluator.run_item` predicted set | no — computed by `decide`, not added | `harness.py:265-270` |
| per-code metrics / CIs | no — no code exists for it in `code_space` | `harness.py:88-100` |
| `pipeline_budget_report` flip rate | no — `.fired()` on both runs | `harness.py:525` |
| `tests/test_decision.py` | logic only, with injected thresholds 0.9 / 0.7 / 0.4 | `test_decision.py:240-258` |
| `tests/test_decision.py::test_binary_offensive_stage_1_is_one_global_threshold` | shape only (`threshold_when` absent) | `:416-418` |
| `tests/test_pipeline.py` | no assertion on it | — |
| `test_post_is_offensive` | content / form / degraded branches; not the binary branch | `test_decision.py:342-352` |
| m3 `test_unit.py` | `raw_score` type and range; never the threshold | `:143-150` |
| contract example gate | one value (0.0214 on the clean sentence), which does not fire | `analysis_result.example.json:29` |
| derivation protocol / `eval.m4_stage1b` | yes, offline, on the dev split; not a regression mechanism | `eval/m4_stage1b.py:58` |

Consequences a verifier must accept as fact today:

1. A trap word that BERTurk scores above 0.320188 passes "0 regressions" while the real pipeline
   returns `review` for it with the binary driver. No trap is known to do this; nothing would tell
   us if one did.
2. The value 0.320188, its `>=` rule, and the documented tie row are protected only by the yaml
   text and the one-sentence example. Changing the threshold to 0.5 would trip the example gate
   (via `artifact_hash`), which is a change detector, not a correctness check: the gate would
   equally trip on a *correct* re-derivation, and the team is told to regenerate on config change.
3. `post_is_offensive`'s binary branch feeds escalation; it has no test.
4. The per-module m3 result file (`traps 0/23`, one clean item, latency within 80 ms) is
   structurally indistinguishable from a result for a module whose score is random.

---

## 4. Summary table

| mechanism | observes | ignores | can catch | cannot catch | passing result misleading today? |
|---|---|---|---|---|---|
| generic contract unit tests | shape, ok, provides, no decision fields, no mutation, no raise | all behaviour | crash, mutation, undeclared field | stub, wrong output, wrong span | **yes** (m2, m5, m6, m4 are green on this alone) |
| m0 behaviour tests | every pass and signal | spec §4 vs code (Q14) | any m0 change | design intent drift | no |
| m1 behaviour tests | traps, boundaries, spans, signals, m6 guard | A4 / HOMONYM absence, score value, latency, cross-channel veto | m1 regressions | unbuilt deliverables | partly (reads uncommitted traps) |
| m3 behaviour tests | fail-closed, no network, signal set, range, text choice, truncation | score value, heads absence | crash, network, wrong signal keys | wrong probability, missing heads | **yes** without the artifact (5/6 skip) |
| m4 / m2 / m5 / m6 behaviour tests | m4: note only; others skipped | everything | nothing behavioural | everything | **yes** |
| architecture tests | import graph, AST thresholds, decision-field assignment, deps, layout, spans declared, order | behaviour, signal names | rule violations | semantic mismatches | no |
| contract tests + example gate | enums, schema, one clean sentence byte-for-byte | every other input | shape and config drift | wrong verdicts | partly ("current" ≠ "correct") |
| traps | fired content, m0 patterns, m1 guards | binary, verdict, spans, target | m0 / m1 collision regressions | m3 firing on a trap, m2/m5/m6 anything | **yes** for m2–m6 |
| eval harness | per-code fired / active / target vs gold, latency | degraded, binary, verdict, spans | wrong code on labelled items | stub, wrong `raw_score`, yaml drift | **yes** for m2–m6 and for m3's live output |
| flip-rate budget | content flips with vs without m2 | binary flips | future content flips | future binary flips | by construction 0.0 while m2 is a stub |
| latency budgets | wall-clock | — | overruns of placeholders | — | no (budgets are placeholders) |
| decision tests | fusion / guard / thread / reset / family-A logic | real yaml values, binary→counter branch, real boundary | logic regressions | value drift, boundary rule | no for logic; **yes** if read as "shipped thresholds verified" |
| integration tests (doubles) | pipeline mechanics, degradation, validation, counter, CLI, API errors | real modules, real yaml | mechanics regressions | real-module mismatches (Q6), Q1 | no for mechanics |
| end-to-end verdict tests | `review` + shape on one sentence | everything else | a regression that leaves `review` | any regression that still yields `review` | **yes** |
| gold set | none exists | — | — | — | n/a |
| check.sh | all of the above, exit codes | skips, reference numbers, artifact presence, tree cleanliness | what the above catch | what the above miss | **yes**, as a "system verified" signal |

---

## 5. What this means for Gate 0

The mechanisms are internally sound: each asserts what it says it asserts, and the harness's own
self-tests prove its arithmetic. The blind spots are structural, not bugs:

- the only live derived threshold is outside every regression path (§3);
- stubs and empty modules are healthy in every measurement channel except the pipeline's own
  `degraded` list, which no eval reads;
- real-module end-to-end behaviour is asserted on one clean sentence;
- decision tests pin their own thresholds, so the shipped yaml is validated for shape only;
- the results directory mixes runs from two trap-file versions and two repeat counts, and the unit
  suite's trap test reads uncommitted data.

The acceptance criteria that follow from this are in `VERIFICATION_PLAN.md` §6.

---

## 6. Gate 1 — what changed in the verification system (2026-09-17)

Gate 1 changed test and eval infrastructure only. No module, spec, ADR, threshold, action,
artifact or dataset was touched; `AI/contracts/` is unchanged. Details, commands and evidence are
in `GATE1_RESULTS.md`; this section updates the mechanism-by-mechanism picture of §2–§4.

### 6.1 Mechanism updates

| mechanism | before Gate 1 (§2) | after Gate 1 |
|---|---|---|
| decision-layer tests | real yaml validated for shape only; 0.320188 referenced by no test | `tests/test_binary_offensive.py` loads the shipped yaml unchanged and pins: the value equals the derivation record and the stage-1b integrity constant; `fired = score >= t` at `t − ε`, `t`, `t + ε`, the protocol's tie row (0.32018762826919556, below `t`), a sweep over [0, 1], absent and non-numeric scores; `post_offensive`; the verdict and driver when the binary is the only signal; idempotence. Mutation-checked: an exclusive rule fails 9 assertions, a drifted value fails 2 |
| thread counter | the `binary.fired` branch of `post_is_offensive` untested | a binary-only double drives the counter through the real config: three posts at `t` escalate on the third; a post at `t − ε` is never counted |
| traps | content codes only; the binary fire invisible | `check_traps` records one **observation** per trap with SEPARATE facts (`content_fired`, `binary {score, threshold, fired}`, `form_active`, `guards_active`, `guards_suppressed`, `degraded`, `post_offensive`, `verdict`, `driver`), lists `binary_fired` ids and `binary_observable`, and accepts a module-scoped `binary: {modules, must_not_fire}` rule. No committed trap carries the rule (policy, Q2 / Q18): the fact is observable, the expectation is not invented |
| eval harness | stubs never degraded; result files healthy | `run_item` degrades a stub, an `ok=False` output and dropped items exactly as `Pipeline.analyze` does (`degradation_record`, pinned equal to the pipeline's entry); every report carries `implementation` (declared status, `not_built`, `scope` = `NOT VERIFIED` for a stub), `degraded_items` and `provenance` (commit, dirty flag, input digests, repeats, bootstrap size); `summarize` prints the status, `degraded_items` and `binary_fired` on the first line and a `** NOT VERIFIED **` line for stubs |
| pipeline budget report | content flips only | `binary_offensive_on_traps` (fired in the full pipeline; flipped by the channel), `trap_observations`, `degraded_modules`, `provenance`. Reported, not budgeted (the budget is defined on content codes) |
| `run_all` | one summary line per module | prints `NOT VERIFIED (...)` for stubs, the binary-fired trap ids, the provenance line with `CURRENT_REPRODUCIBLE_RESULT` / `NOT REPRODUCIBLE`; `--results-dir` writes elsewhere than `eval/results/` so historical files are never overwritten |
| skip accounting | `unittest` exits 0 on skips; no expected set | `eval/implementation_status.json` declares status, `not_built`, `expected_skipped_tests` and `preconditions` per module; `tests/test_implementation_status.py` fails on any other skip, on a declared status that disagrees with `stub`, on a stub with a runnable behaviour test, and on a missing m3 artifact (named PRECONDITION failure, not a skip) |
| interface tests | none | `tests/test_signal_interfaces.py`: m0 `_offsets` invariants and the frozen form m1 reads; m0 signal key set; m1 hit signals present / boolean / consistent on every input and readable by the stage-1b consumer; the yaml channel path splits into m3's name and a key m3 publishes; the artifact id agrees across yaml, MANIFEST and module; m3 publishes exactly `{raw_score, artifact}` and the decision layer reads it; `signals.pipeline` and `signals.decision` key sets and types |
| end-to-end verdict tests | one clean sentence; m3 masked | `tests/test_end_to_end.py`: six real-pipeline cases plus a bounded-response check, every assertion in a stage-named subTest (MODULE_OUTPUT, INTERFACE_CONTRACT, PIPELINE_MERGE, DEGRADATION, DECISION_THRESHOLD, GUARD_APPLICATION, FINAL_ACTION) with a diagnostic dump on failure; expected verdicts computed from the config with `actions.severity`; m3 probabilities labelled CURRENT_ARTIFACT_OBSERVATION; Q1 / Q2 / Q3 / Q5 / Q6 cases excluded or recorded without judgement. Mutation-checked: guard over-suppression names GUARD_APPLICATION, a silenced binary names DECISION_THRESHOLD/binary, lost spans name PIPELINE_MERGE |
| `test_stub_modules_are_degraded_and_named` | filtered m3 out | a degraded non-stub module is a named PRECONDITION failure |

### 6.2 What the new instruments observed on this machine (first run)

- **The binary score fires on 4 of the 33 collision traps** in the full pipeline and in m3's
  own evaluation: `trap-008` "sikke" (0.984), `trap-017` "Eski sikke koleksiyonu" (0.493),
  `trap-030` "SİKKE" (0.442), `trap-032` "KLASİK" (0.658). On each, no content code fires, the
  `SUBSTRING_COLLISION` guard is active, and the verdict is `review` driven by
  `binary_offensive`. Before Gate 1 every one of these read as "0 regressions". Whether this is a
  regression is Q2 / Q18 (BLOCKED_BY_POLICY); it is now a recorded production observation of
  artifact `m3-berturk-pytorch-fp32-epoch1`, not fixed.
- Every stub report now says `NOT VERIFIED` and `degraded_items = n_scored`.
- Provenance on this machine: `git_dirty = true` (the baseline is still uncommitted), so every
  number produced here is a HISTORICAL observation, not a reference (`GATE1_RESULTS.md` §7).

### 6.3 Summary table, revised rows only

| mechanism | can now catch | still cannot catch | passing result misleading? |
|---|---|---|---|
| decision tests | a wrong binary boundary rule; a drifted binary value; the binary→counter path | wrong placeholder values (they have no oracle, Q25) | no |
| traps | a binary fire on any trap (observed, and asserted where a rule is present) | a wrong span on an emitted guard; anything from m2 / m5 / m6 (still empty) | no longer for the binary; still vacuous for stubs, and now says so |
| eval harness | a stub or failed module (degraded, `NOT VERIFIED`); the binary state per fixture item and trap | a wrong `raw_score` value on a labelled item (no labelled m3 fixture exists) | no: the report states its own scope |
| flip-rate budget | binary flips (reported) | — (budgeting them is a policy decision) | by construction 0.0 while m2 is a stub, stated in the report |
| integration / end-to-end | a wrong verdict, driver, fused content, span, guard effect, degraded set or binary state on six real posts, with the stage named | Q1 / Q2 / Q3 outcomes (excluded by policy); any post outside the six | no |
| skip accounting | an unexpected skip; a missing artifact turned into a skip | — | no |
| interface tests | a renamed or missing signal key, a wrong type, an artifact-id mismatch | the m2 offset map (Q5, no contract) and m6's two routes (Q6) | no |
| check.sh | everything above through the unit suite and `run_all` | a dirty tree (provenance says so, the exit code does not) | partly: the exit code is unchanged; the printed lines are not |

### 6.4 Remaining blind spots after Gate 1

1. m2, m5, m6 are still empty: every instrument now *says* so, none can verify them.
2. No labelled fixture for m3, m4, m2, m5, m6 (one clean item each) and no end-to-end gold set;
   the six end-to-end cases are connection tests, not a measurement.
3. The `binary` trap rule exists but is attached to no trap; the four observed fires stay a
   published fact until the owner decides Q2 / Q18.
4. `check.sh`'s exit code still ignores the dirty flag and the binary-fired count.
5. The pipeline latency number of the Gate 1 run (p95 383 ms over 3 repeats, taken while the unit
   suite ran concurrently) is not a measurement; it is recorded only as a run that exercised the
   report, and it made `run_all` exit 1 on the placeholder budget.
