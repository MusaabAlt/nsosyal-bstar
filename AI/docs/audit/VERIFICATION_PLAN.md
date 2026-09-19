# Verification plan — Gate 0

Verification Gate 0, 2026-09-17. Branch `audit/m1-m6` at `f063ddf` plus the working tree of
`BASELINE_WORKTREE.md`. Inputs: `ISSUE_TRIAGE.md`, `TEST_SYSTEM_AUDIT.md`, `TEST_ORACLE_MAP.md`.
This plan says what must be true before the first real module is tested, in which order the
modules are then verified, and why. It implements nothing.

---

## 1. Verification status per module and component

Status vocabulary: READY_FOR_BEHAVIOR_TESTING, READY_FOR_PARTIAL_TESTING, STUB_ONLY,
BLOCKED_BY_CONTRACT, BLOCKED_BY_POLICY, BLOCKED_BY_DATA. A module gets one primary status; the
"implemented / specified-not-built / blocked" columns keep the partial cases honest. Passing the
eight generic contract tests is not evidence for any status other than "well-formed".

| component | primary status | implemented and testable now | specified, not built (oracle exists, no subject) | blocked slice and by what |
|---|---|---|---|---|
| m0_charsafe | **READY_FOR_BEHAVIOR_TESTING** | five passes, signals, offsets, per-length latency, flag-pair gap; 42 behaviour tests exist | — | the *design* question of spec §4 vs five passes (Q14) and "before any model" (Q3) are policy / docs, not test blockers for m0 alone |
| m1_lexicon | **READY_FOR_PARTIAL_TESTING** | raw-channel boundary matching, `A1` carrier with spans through m0 offsets, `SUBSTRING_COLLISION`, `NON_HUMAN_TARGET` from a faked m6 signal, three boolean signals, traps, latency bands | `A4`, `HOMONYM`, sacred-concept table, terlik-vs-karaliste report, dual-register fixtures | normalized-channel spans (Q5, contract); input oracle wording (Q7, docs); latency criterion (Q12, policy); collision base rate (Q20, policy); two-tier judgement (Q16, policy) |
| m2_deobf | **STUB_ONLY** | nothing (returns one note) | everything in spec §4–§11 | before building: offset map (Q5, contract), evidence rule (Q14, contract), headline measurement home (U-M2-3) |
| m6_target | **STUB_ONLY** | nothing | everything in spec §2–§10 | before building: ambiguity rules (Q28, policy), two-route agreement (Q6, contract) |
| m3_encoder | **READY_FOR_PARTIAL_TESTING** | binary `raw_score` on `ctx.text`, artifact hash check, fail-closed, no network, truncation note, determinism; equivalence with the study's predictions (offline) | A head, B head, C head, normalized pass, `norm_score`, per-code metrics, decision-flip table | which text it must score (Q3, policy — affects the oracle for obfuscated input); heads (Q26 / U-M3-7, data) |
| m4_implicit | **READY_FOR_PARTIAL_TESTING** | stage 1 threshold as a *decision-layer* behaviour (boundary, `>=`, tie row, raw channel only, `review`); stage 1b rejection is on record | slice repair stages 2+; C1–C5 rows derivation; fixture set of spec §9 | binary observability in the harness (Q18, infrastructure); stage-2 budget (Q23, policy); fixture-slice test (Q15, contract) |
| m5_sarcasm | **STUB_ONLY** (and **BLOCKED_BY_DATA** for anything beyond the stub) | nothing | everything | corpus gate (Q27) |
| decision layer | **READY_FOR_BEHAVIOR_TESTING** for logic; **BLOCKED_BY_POLICY** for real-config verdicts | fusion, guards, thread rule, family-A assignment, reset, binary logic with injected thresholds | — | verdicts under the shipped yaml: Q1, Q2, Q4 (policy), Q25 (all placeholders) |
| pipeline (`run.py`, registry, contracts) | **READY_FOR_BEHAVIOR_TESTING** | loop, merge, validation, degradation, deep-freeze, fast path (disabled), CLI, API, contract example | — | none for mechanics; integration oracles for m1↔m3 text choice (Q3) and m6 routes (Q6) are policy / contract |
| thread counter | **READY_FOR_BEHAVIOR_TESTING** | window, receive time, self-directed exclusion, keying, sweep, CLI block | — | the binary-only-repeat path has no test (G0-7); `window_seconds` placeholder is policy (not a blocker) |
| eval harness / traps / budgets | **BLOCKED_BY_CONTRACT** as an *instrument* | the arithmetic (self-tested) | — | it cannot observe the binary fire, degradation or the verdict (Q18, G0-2, G0-4); its `expect` rule is "when produced" (G0-3). These are instrument gaps, resolved in Gate 0 |

Reading rule for the table: a STUB_ONLY module has no behaviour to verify; a status of
READY_FOR_PARTIAL_TESTING means the "implemented" column can be verified now and the
"specified, not built" column must be reported as NOT BUILT in every result, never as passing.

---

## 2. Isolated verification order (unit and contract level)

Principle: verify the instruments first, then the modules with no upstream dependency, then each
module with its upstream inputs *faked* from the upstream module's contract (not from the upstream
module's code), then the consumers of everything. A module is verified in isolation against its
oracle rows in `TEST_ORACLE_MAP.md`; unresolved rows are reported, not assumed.

| step | component | why here |
|---|---|---|
| 0 | test infrastructure (Gate 0 criteria, §6) | nothing measured before this is trustworthy: the binary fire, degradation and the verdict are outside every current measurement |
| 1 | contracts (`codes`, `schema`, `module_api`) | every oracle below is expressed in these types; they are frozen and tested; confirm the tests still describe the frozen files |
| 2 | decision layer, logic only (`fusion`, `actions`) with injected configs | it is the consumer of every module and the place where the verdict is made; its logic must be trusted before any module's output is interpreted through it. Add the boundary test for the real binary threshold here (G0-1) |
| 3 | thread counter alone (fake clock) | independent of every module; only consumes `post_is_offensive`, which step 2 fixes |
| 4 | pipeline mechanics with doubles (`_merge`, degradation, deep-freeze, span enforcement, CLI, API) | the host every module runs in; verified with doubles so no real module's bugs are conflated with host bugs |
| 5 | **m0_charsafe** | no upstream; the reference module; its `_offsets` signal is m1's only route to original spans, so its correctness is a precondition for m1's span oracle |
| 6 | **m1_lexicon**, raw channel, with `charsafe_text` and `_offsets` faked per m0's contract and `signals.m6_target` faked per m6 spec §6 | first real detector; depends on m0 (spans) and m6 (guard). Faking m6 is legitimate because m6 is a stub and its contract is written; report Q5 / Q7 / Q8 / Q12 / Q16 / Q20 as unresolved rows, do not answer them |
| 7 | **m3_encoder**, partial scope | independent of m1 and m2 at runtime (reads `ctx.text`); needs the artifact (precondition, not a skip); verify equivalence with the study's predictions as a *test*, not only offline (today it is protocol-only); report the heads as NOT BUILT |
| 8 | **m4_implicit** as a decision-layer behaviour | its only live deliverable is the yaml row; verify through step 2's boundary test plus the m4 unit test; report stages 2+ as NOT BUILT |
| 9 | m2_deobf, m6_target, m5_sarcasm as stubs | confirm each is a *well-formed stub*: `stub = True`, one note, no fields, degrades the pipeline, behaviour tests skipped with the reason. Record explicitly that this is all that was verified |
| 10 | eval harness and traps against a *known-answer* module double | the instrument re-verified after the Gate 0 changes: a double that emits a binary score above the threshold on a trap must produce a regression; a stub double must be reported as degraded |

Why m6 sits after m1 here although it runs before m1 in the pipeline: in isolation m6 is a stub
with nothing to verify, whereas m1's guard path can be verified now against m6's *contract*. In
the integration order (§3) the pipeline order is restored.

---

## 3. Integration verification order (pipeline dependency order)

The pipeline order is `m0 → m2 → m6 → m1 → m3 → m4 → m5 → decision`, then the thread counter,
then `conclude`. Integration verification follows the data, adding one producer at a time and
checking what the next consumer actually receives — with the real modules where they exist and
documented stubs where they do not.

| step | slice under test | producer → consumer contract checked | why here |
|---|---|---|---|
| I1 | m0 alone in `Pipeline` | caller text → `charsafe_text`, `signals.m0_charsafe._offsets` (internal), public counters; degraded list empty | first hop; establishes the channel every later module reads |
| I2 | m0 → m2 (stub) | `ctx.charsafe_text` reaches m2; `normalized_text` stays `None`; m2 listed as `stub`; verdict cannot be clean | fixes the "no normalized channel" baseline that m1 and m3 see today; documents that the flip-rate budget is 0 by construction |
| I3 | m0 → m2 → m6 (stub) | m6 receives raw text; `signals.m6_target == {}`; `result.target is None`; m6 listed as stub | establishes that family-A resolution will be `none → A1` (the Q1 precondition) |
| I4 | m0 → m2 → m6 → m1 | m1 reads charsafe + `_offsets`, maps spans to the original text; `signals.m6_target` empty ⇒ no `NON_HUMAN_TARGET`; `lexicon_hit_norm` false by absence | first detector in place; the flag-only path and the m6-guard path must be exercised with a *faked* m6 output injected through a test double in m6's slot (the pipeline's `modules=` parameter allows it) |
| I5 | … → m3 | m3 reads `ctx.text` (not charsafe); publishes `raw_score`, `artifact`; `m1` signals visible to m3 but unused | pins the Q3 behaviour as observed; the ZWSP probe from `PIPELINE_FLOW.md` §7 becomes a test with an explicit "known, unresolved" label |
| I6 | … → m4 | m4 receives `signals.m3_encoder`; emits its note; is *not* degraded | confirms ADR-006 amendment in the real pipeline |
| I7 | … → m5 (stub) | listed as stub; nothing else | completes the degraded set `{m2, m6, m5}` |
| I8 | decision on the real pipeline | `signals.decision.{family_a, binary_offensive, channel_scores, post_offensive}`; fused content; guards' `suppressed`; verdict and driver on a fixed post set (the six observed rows of `PIPELINE_FLOW.md` §7) | end-to-end verdict oracle; Q1 / Q2 outcomes are asserted as *observed* with an UNRESOLVED label until the owner decides |
| I9 | thread counter through the CLI / `analyze(thread_block=…)` | three offensive posts escalate on the third; a clean post afterwards reports history but does not fire; a binary-only offensive post counts (G0-7) | Axis 4 on the real pipeline |
| I10 | API | `POST /analyze` returns the same result as `analyze()`; error codes | outermost boundary |
| I11 | gates (`contract_example --check`, `check.sh`) on the committed baseline | byte-identical example; contracts unchanged; the eval run recorded with trap count and repeats | closes the loop on reproducibility (G0-6, G0-10) |

Dependencies this order respects explicitly:

- m2 before m1 and m3: `normalized_text` must exist (or be known absent) before either reads it.
- m6 before m1: `signals.m6_target.{target_type, target_confidence}` before m1's guard (ADR-005,
  `test_m6_runs_before_m1`).
- m1 before m3: only for the fast path (disabled) and signal visibility; m3 does not read m1.
- m3 before m4: m4 is specified to read m3's signals (reads nothing today).
- m5 last: independent.
- decision after all modules; counter between `decide_post` and `conclude`.

---

## 4. What "verified" will mean for a partial module

Every module report produced after Gate 0 must carry three lists, taken from
`TEST_ORACLE_MAP.md`: **verified** (oracle resolved, subject exists, test passed), **NOT BUILT**
(oracle exists, subject does not; the row is reported, never scored as pass), and **UNRESOLVED**
(oracle conflict; current behaviour pinned and labelled as a change detector). A stub's report has
an empty first list.

---

## 5. Sequence of the whole verification, after Gate 0

1. Gate 0 (this document §6) — instrument changes, baseline commit, one reference eval run.
2. Isolated order §2, steps 1–4 (contracts, decision logic, counter, pipeline mechanics).
3. m0 (§2 step 5), then m1 raw channel (§2 step 6), then m3 partial (§2 step 7), then m4 as decision
   behaviour (§2 step 8), then the three stubs as stubs (§2 step 9), then the instrument re-check
   (§2 step 10).
4. Integration order §3, I1–I11.
5. A written verdict per module in the four-list form of §4, and a list of the policy / contract
   decisions the owner still owes (`ISSUE_TRIAGE.md` §7).

Nothing in steps 2–5 changes production code, tests of behaviour, specs, ADRs or thresholds. Only
Gate 0 changes test infrastructure, and only after the owner accepts §6.

---

## 6. Gate 0 acceptance criteria

Gate 0 is passed when every criterion below is true on the committed baseline. Each names the
observable fact, the evidence that today it is false, and the *kind* of change that would make it
true (design only; nothing is implemented in this gate).

### G0-A. A wrong verdict is detectable

- **Must be true:** an end-to-end test on the real pipeline asserts, for a fixed set of posts, the
  fused content codes, the guards' `suppressed` lists, `signals.decision.binary_offensive.fired`,
  `signals.decision.family_a`, the verdict and the explanation driver. Any of them changing fails
  a test.
- **Today:** false. `test_default_pipeline_on_clean_sentence` asserts `review` and shape;
  `test_stub_modules_are_degraded_and_named` masks m3. The six observed rows of
  `PIPELINE_FLOW.md` §7 exist only as a hand-run table.
- **Change kind:** new end-to-end tests under `AI/tests/` with an explicit artifact precondition
  (fail with a named reason, not skip); the Q1 / Q2 rows carry an UNRESOLVED label in their name
  or docstring so a policy decision later changes the expectation deliberately.

### G0-B. A wrong threshold boundary is detectable

- **Must be true:** a test loads the *real* yaml and asserts the binary boundary: `t − ε` does not
  fire, `t` fires (`>=`), `t + ε` fires; the tie-row semantics from the derivation protocol are
  stated in the test; the threshold value equals the one recorded in the derivation file.
- **Today:** false. No test references 0.320188; decision tests overwrite every threshold.
- **Change kind:** one decision-layer test reading `fusion.load_config()` and the derivation file's
  recorded value. The value itself is not changed.

### G0-C. Degraded or stub behaviour cannot appear healthy

- **Must be true:** (i) the per-module harness marks a run from a `stub = True` module (or a run
  where `_merge` reported problems, or `ok = False`) as degraded in the result file, and
  `run_all`'s summary line says so; (ii) the unit suite's expected skip set is recorded and an
  unexpected skip is visible; (iii) a stub's result file cannot show "traps 0/N" without the word
  `stub` next to it.
- **Today:** false. `run_item` writes no `degraded`; `unittest` exits 0 on skips; the m2 / m5 / m6
  result files are structurally healthy.
- **Change kind:** harness reporting (`signals.pipeline.degraded` populated in `run_item` from the
  same rules the pipeline uses; a `degraded` block in the report; `summarize` prints it) and a skip
  accounting in `check.sh` or a test. Fail-closed policy (#15) is not changed; it is *observed*.

### G0-D. `binary_offensive` is observable by regression verification

- **Must be true:** (i) traps can assert on `signals.decision.binary_offensive.fired` (a
  `must_not_fire_binary` or equivalent rule, or a general verdict assertion), and the current 33
  traps are run once with that rule to learn whether any of them fires today; (ii) the per-module
  harness reports, for m3, the binary fire per fixture item (as a pseudo-code or a separate block);
  (iii) the flip-rate budget counts a binary flip as a flip, or a second flip rate is reported for
  the binary; (iv) `post_is_offensive`'s binary branch has a unit test.
- **Today:** false on all four (`TEST_SYSTEM_AUDIT.md` §3).
- **Change kind:** harness and trap-format extension (documented in `eval/README.md`), one
  decision test, one thread-pipeline test with a binary-only double. The threshold, its action and
  the "not suppressible" rule are not touched.

### G0-E. Module output and interface mismatches are detectable

- **Must be true:** (i) for every producer → consumer signal pair in `MODULE_MAP.md` §3, a test
  asserts the key names and value types the consumer reads against what the producer's contract
  says it publishes (m0 `_offsets` → m1; m6 `target_type` / `target_confidence` → m1; m3
  `raw_score` → yaml `binary_offensive.channels.raw`; m1 `lexicon_hit*` → stage-1b protocol); a
  renamed key on either side fails; (ii) the `expect` trap rule's "when produced" semantics is
  documented, or a presence form exists, so an absent output can be asserted (G0-3).
- **Today:** partly. Types and enums are validated in `_merge`; key names between modules are not
  checked anywhere (Q13 shows the drift can already happen in documents).
- **Change kind:** contract-level tests in `AI/tests/` (allowed to import any module: they are
  outside rule 2's module scope, as `test_architecture.py` already is) that read the yaml paths
  and the module constants; no module code changes.

### G0-F. Integration failures are distinguishable from module failures

- **Must be true:** (i) every integration test that uses real modules states its preconditions
  (artifact present, terlik importable) and fails with a named reason when they are missing,
  instead of skipping or masking (the m3 filter in `test_stub_modules_are_degraded_and_named`
  goes away or becomes a precondition); (ii) module unit tests never read data outside the module
  except the committed trap file at a pinned path and count (m1's trap test today reads the
  working tree); (iii) the result files carry the trap count, repeats, git HEAD and dirty flag so
  two runs are comparable (the derived-labels file already does this; the harness reports do not
  record HEAD).
- **Today:** false on (i) and (iii); (ii) is true in structure and false in the current tree.
- **Change kind:** test preconditions, a provenance block in harness reports, and the baseline
  commit of `BASELINE_WORKTREE.md`.

### G0-G. The baseline is reproducible

- **Must be true:** the working tree is clean at a named commit that contains the intentional
  changes (traps 024–033, the six m1 fixture items, the m1 spec table, the HANDOVER edits, the
  protocol, the script and — per the protocol's own rule — the derived file in a later commit),
  the accidental `--` edit reverted by its owner, the audit outputs committed or kept aside
  deliberately, and one `eval.run_all` recorded against that commit with its trap count and
  repeats.
- **Today:** false (`BASELINE_WORKTREE.md`).
- **Change kind:** owner's commit decisions; no content change by the auditor.

### Gate 0 verdict today

| criterion | status |
|---|---|
| G0-A wrong verdict detectable | FAIL |
| G0-B wrong boundary detectable | FAIL |
| G0-C degraded cannot look healthy | FAIL |
| G0-D binary observable | FAIL |
| G0-E interface mismatches detectable | PARTIAL (types yes, key names no) |
| G0-F integration vs module failures distinguishable | FAIL |
| G0-G reproducible baseline | FAIL |

**Gate 0: FAIL.** Module testing must not start until G0-B, G0-C, G0-D and G0-G are true; G0-A,
G0-E and G0-F must be true before the integration order (§3) starts.

---

## 7. First component to verify once Gate 0 passes

**The decision layer with the real binary boundary (G0-B), then m0.**

- The decision layer is the consumer of everything and the place the only derived number lives;
  until its boundary is pinned against the real yaml, no module's output can be interpreted.
- m0 is the only module whose oracle rows are all resolved except two documentation / policy
  questions (Q14, Q3), whose behaviour tests are exhaustive, and whose `_offsets` output is the
  precondition for m1's span oracle. Verifying it first gives m1 a trusted input.
- m1 follows immediately: it is the first real detector, its raw-channel behaviour is fully
  specified, and every unresolved row (Q5, Q7, Q8, Q12, Q16, Q20) can be reported without
  blocking the resolved ones.

m3 is deliberately third: it is testable, but its oracle on obfuscated input (Q3) and its only
live output's observability (G0-D) both depend on Gate 0 and on an owner decision.

---

## 8. Gate 1 outcome (2026-09-17) — Gate 0 criteria re-scored

Gate 1 changed only test and eval infrastructure (`GATE1_RESULTS.md` lists every file). The
criteria of §6, re-scored against the working tree after Gate 1:

| criterion | status after Gate 1 | evidence |
|---|---|---|
| G0-A wrong verdict detectable | **PASS** | `tests/test_end_to_end.py`: six real-pipeline posts assert fused content, spans, guard effects, `family_a`, `binary_offensive`, `post_offensive`, verdict, driver and explanation, each in a stage-named subTest; mutation checks name the originating stage |
| G0-B wrong boundary detectable | **PASS** | `tests/test_binary_offensive.py` against the unmodified yaml: `t − ε` / `t` / `t + ε`, the tie row, the value vs the derivation record; mutation checks fail on an exclusive rule and on a drifted value |
| G0-C degraded cannot look healthy | **PASS** | harness degrades exactly as the pipeline (pinned equal); reports carry `implementation.scope = NOT VERIFIED` for stubs and `degraded_items`; `tests/test_implementation_status.py` pins the allowed skip set and fails on a missing m3 artifact |
| G0-D binary observable | **PASS** | trap observations + `binary_fired`, the `binary` trap rule, `binary_offensive_on_traps` in the pipeline report, `post_is_offensive` binary branch through the counter. First run: fires on 4 of 33 traps (`TEST_SYSTEM_AUDIT.md` §6.2) |
| G0-E interface mismatches detectable | **PASS** (within the interfaces that have an oracle) | `tests/test_signal_interfaces.py`; Q5 and Q6 interfaces deliberately not defined |
| G0-F integration vs module failures distinguishable | **PASS** | stage-named subTests with a diagnostic dump; preconditions FAIL with a named reason instead of skipping; the m3 mask in `test_stub_modules_are_degraded_and_named` removed; reports carry provenance |
| G0-G reproducible baseline | **FAIL** (owner action) | the tree is still dirty: the five project files and three untracked project files of `BASELINE_WORKTREE.md` are uncommitted, now joined by the Gate 1 files; `provenance.git_dirty = true` on every number produced. The Gate 0 documents were committed by the owner as `06520e4` |

**Gate 1 verdict: PASS on the infrastructure criteria (G0-A to G0-F), FAIL on G0-G.** Module
verification can start on the *instrument* side; every number it produces stays a historical
observation until the owner commits the baseline and one reference run is recorded
(`BASELINE_WORKTREE.md` §6, `eval/README.md` "HISTORICAL_RESULT vs CURRENT_REPRODUCIBLE_RESULT").

Adjustment to §2 / §3 ordering: none. The first components to verify remain the decision layer
(now already pinned at its real boundary) and m0; the four binary fires on collision traps are
handed to the owner as a Q2 / Q18 decision before m3's verification is scored.
