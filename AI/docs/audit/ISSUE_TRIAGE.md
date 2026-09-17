# Issue triage — Gate 0

Verification Gate 0, 2026-09-17. Branch `audit/m1-m6` at `f063ddf` plus the uncommitted working tree
inventoried in `BASELINE_WORKTREE.md`. Every open item from `OPEN_QUESTIONS.md` (Q1–Q33), every
`U-…` tag from `MODULE_CONTRACTS.md` / `PIPELINE_FLOW.md` that is not already folded into a Q, and
the new findings of this gate (`G0-…`, from `TEST_SYSTEM_AUDIT.md`) is classified into exactly one
primary category. Nothing here is a fix and no policy question is answered.

Categories:

| code | category | meaning |
|---|---|---|
| A | POLICY_DECISION_REQUIRED | a product / policy choice that cannot be inferred safely from code |
| B | CONTRACT_DECISION_REQUIRED | an interface or expected-behaviour ambiguity; no valid test oracle exists until it is resolved |
| C | TEST_INFRASTRUCTURE_GAP | the implementation may be testable, but the existing test / eval system cannot detect the relevant failure |
| D | IMPLEMENTATION_GAP | expected behaviour is clear; the implementation is missing, partial, stubbed or incorrect |
| E | DOCUMENTATION_DRIFT | behaviour is clear enough to test; documentation is stale or inconsistent |
| F | BLOCKED_BY_DATA_OR_EXTERNAL_RESOURCE | required data, corpus, labels, artifact or external resource does not exist yet |
| G | DEFERRED_NON_BLOCKING | real, but does not block verification of the current system |

Severity is carried over from `OPEN_QUESTIONS.md` (high = changes a verdict or a published number;
medium = blocks a specified deliverable or a measurement; low = documentation drift) and assigned
on the same scale for new items.

"Blocks testing" means: no correct test oracle can be written for the affected behaviour until the
item is resolved. "Blocks implementation" means: a module owner cannot finish the affected
deliverable without the decision or resource.

---

## 1. Verdict-changing policy interactions

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| Q1 | A | high | decision, m6, m1 | With m6 a stub, every family-A hit resolves to `A1` whose placeholder action is `nudge`; `actions.resolve` upgrades only `clean` under degradation, so a degraded post can be published with a warning. Whether HANDOVER #16a ("a more severe verdict under degradation stands") covers a verdict that is more severe than clean only because the target module is missing is not written anywhere. | yes, for the verdict oracle of any A-family post while m6 is a stub | no | `decision/actions.py::resolve` (implemented); HANDOVER #15, #16a (policy text) | Owner decision recorded in an ADR or HANDOVER: does a target-dependent code count as "a more severe verdict" while its target producer is degraded? |
| Q2 | A | high | decision, m1, m3 | `binary_offensive` is "not suppressible by guards" (`thresholds.yaml` comment); the ADR-005 design case "insult at a film → clean + NON_HUMAN_TARGET" is reachable only when m3's binary score is below 0.320188. Precedence between the guard design and the study threshold is not decided. | yes, for the end-to-end oracle of a guarded non-human-target post | no | `thresholds.yaml` binary comment; ADR-005 §Consequences; `fusion.apply_guards` | Owner decision on precedence, recorded next to the binary row. |
| Q3 | A | high | m3, m0 | m3 scores `ctx.text` (owner decision, so the fitted threshold keeps its meaning); m0 spec §1 says charsafe must precede "any model". Two owner-level statements conflict on which text the model sees. | yes, for any m3 oracle on obfuscated input | no | m3 `module.py` docstring + `test_scores_original_text_not_charsafe_or_normalized` vs m0 spec §1 | Owner names the authoritative statement and records the known limitation (or the change) in m0 and m3 specs. |
| Q4 | A | medium | decision | `A1` = nudge, `binary_offensive` = review are both placeholders; their relative severity decides whether a lexical hit alone is nudged or reviewed. | no (tests pin their own actions) | no | `thresholds.yaml` categories / binary rows (both PLACEHOLDER) | Owner derives or confirms the two actions (HANDOVER #13, #68). |

## 2. Contract gaps between modules

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| Q5 (U-M1-2, U-M2-2) | B | high | m2, m1, m3 | No contract, spec or signal key carries an offset map from `normalized_text` to the original text. m1 emits spanned normalized-channel scores only under a same-length assumption; m3's spec needs the same map for channel-aligned truncation. | yes, for every normalized-channel oracle (m1 `@normalized` scores, m2 span rule, m3 `norm_score`) | yes, for m2 (what to publish) and for m1's normalized channel | m1 spec §3, m2 spec §6/§9, m3 spec §4, `m1/module.py:122` | Contract decision (Musaab approves, m2 owner proposes): where the map lives (`signals` key, contract field) and what a length-changing repair must publish. |
| Q6 (U-M6-1, U-M6-2) | B | medium | m6, m1, decision | m6's target reaches consumers by two routes (`result.target` validated + `family_a.target_min_confidence`; `signals.target_type/target_confidence` unvalidated + `guards.NON_HUMAN_TARGET.threshold`). No rule says which wins when they disagree. | yes, for the m6→m1→decision integration oracle | partly: the m6 owner cannot know whether the two publications must be identical | m6 spec §6, ADR-005, `fusion.family_a_code`, `m1/module.py:207-218` | Contract decision: one authoritative route or a written agreement rule, and whether the two placeholders are one number. |
| Q7 (U-M1-1) | E | low | m1, m0 | m1 spec §3 says "Reads `ctx.text`"; the code reads `charsafe_text` and m0's internal `_offsets`, which no spec names as an interface. The derived-labels protocol §4 states the actual behaviour. | no (behaviour is pinned by `test_spans_map_through_m0_offsets`) | no | protocol §4 (states it); m1 spec §3 (stale) | Spec edit proposed by m1 owner, approved by Musaab. Test oracle for the *input* is UNRESOLVED until then (see `TEST_ORACLE_MAP.md`). |
| Q8 (U-M1-6) | B | medium | m1, decision | `SUBSTRING_COLLISION` guards are deduplicated by span across channels and carry no channel; a collision on one channel can suppress a hit on the other. Whether a cross-channel veto is intended is unrecorded. | yes, but only once m2 produces a channel; today unobservable | no | ADR-001 (scoping by module and span, silent on channel); `m1/module.py:137-141` | m1 owner decision, recorded in m1 spec §3 or ADR-001 amendment. |
| Q9 (U-M1-3) | G | low | m1 | `lexicon_hit_*` may be `True` with no emitted score (flag-only path). Consumers today (stage 1b not in force, the counter via `fired()`) are unaffected; the protocol tolerates it. | no | no | protocol §3 check 6 | Deferred until a consumer of the flag exists that assumes "hit ⇒ fired code". |
| U-M6-4 | G | low | m6, pipeline | `signals.target_type` is specified as a `TargetType` value; `deep_freeze` deep-copies enums it does not allow-list; m1 compares with `== "non_human"`. Benign today, unpinned. | no | no | m6 spec §6; `pipeline/run.py::deep_freeze` | Deferred; a contract test can pin it when m6 is implemented. |
| U-DEC-3 | G | low | decision | `guards_order` credits the first applicable active guard; explanations name the collision guard when two guards overlap the same span. Explanation wording only. | no | no | `fusion.apply_guards`, `thresholds.yaml guards_order` | Deferred. |

## 3. Specification vs implementation drift

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| Q10 (U-M3-1) | E | medium | m3, docs | The m3 spec describes three heads on two channels; the module is a binary OFF/NOT wrapper. HANDOVER §2 (working tree) still lists m3 among the stubs; `CONTRIBUTING.md` says m1, m2, m3, m5, m6 are stubs; only `AI/README.md` says partial. | no for the implemented subset (pinned by m3 unit tests); yes for the specified-but-absent subset (no oracle for heads that do not exist) | no | `m3/module.py` docstring; `AI/README.md` | One status statement in m3 spec (owner-approved) and matching HANDOVER / CONTRIBUTING text. |
| Q11 (U-M3-3) | E | low | m3 | Truncation policy (128 tokens, first kept, note) lives in the docstring and the derivation protocol, not in spec §5; spec §9 cites 512. | no (pinned by `test_truncation_is_noted`, `MAX_LEN`) | no | protocol; module docstring | m3 owner spec edit, Musaab approves. |
| Q12 (U-M1-7) | A | medium | m1 | Three latency statements: spec §8 "p95 under 5 ms", `thresholds.yaml` per-length bands (3/10/30/140 ms, ADR-003 amendment), measured adversarial p95 ≈ 301 ms at 5000 chars. Which is the acceptance criterion and whether the adversarial overrun is accepted is not written. | yes, for the m1 latency acceptance oracle | no | `thresholds.yaml` (authoritative per HANDOVER #34 analogue for m0, not stated for m1); m1 spec §8 | Owner states the criterion and records the adversarial finding as accepted or not (HANDOVER #44 covers publication, not acceptance). |
| Q13 (U-M1-8, U-M4-4) | E | low | m1, m4 | Stage 1b condition signal is `lexicon_hit_raw` in the protocol and script, `lexicon_hit` in m1 spec §8, m4 spec §4 and the yaml comment. Not in force. | no | no (stage 1b is rejected) | `protocols/m4_stage1b_protocol.md` §3 (pre-registered, executed) | m4 owner aligns the spec wording; matters only if stage 1b is re-proposed. |
| Q14 (U-M0-1, U-M2-1) | E | low | m0, m2 | m0 spec §4 (three steps) vs five implemented passes; m2 spec §9 `text[start:end] == evidence` vs `FormPattern.evidence` free text in schema and m0. | m0: no (45 unit tests pin the passes). m2: yes — the span/evidence rule is an oracle m2's owner must know before building | no for m0; yes for m2's evidence format | m0 `module.py` + tests; m2 spec §9 vs `contracts/schema.py` | m0 owner spec update; for m2, Musaab decides whether the strict rule is m2-specific or the schema's meaning. |
| Q15 (U-M4-5) | B | low | m4 | m4 spec §9 requires a unit test that fixture `context.signals.m1_lexicon.lexicon_hit` equals m1's real output; rule 2 forbids m4's tests importing m1. | yes, for that one required test | no | m4 spec §9 vs `tests/test_architecture.py::test_modules_do_not_import_each_other` | Musaab decides: exemption, relocation to `AI/tests/`, or spec change. |
| Q16 (U-M1-4) | A | low | m1 | Spec §4.2 asks for an explicit two-tier hard/soft structure; the module uses terlik's `suffixable` flag plus a two-word `CLEAN_PREFIXES` whitelist. Whether that satisfies §4.2 and §10 is a judgement. | no (current behaviour is pinned) | yes, for the §10 definition-of-done | m1 spec §4.2, §10; `m1/README.md` | m1 owner proposes, Musaab approves. |
| Q17 (U-M3-6) | E | low | m3 | Spec §5 says 36,232 tweets; verified files hold 35,284. | no | no | RESOURCES.md open item 3 | Spec correction. |
| U-M3-4 | D | medium | m3, decision | `raw_score` is p(OFF) with no code; every family B/C/D finding by the model collapses to `review` with one explanation. This is the specified B/C heads not existing, not a defect in what exists. | no (the collapse is pinned by `test_binary_offensive_uses_signal_conditioned_threshold` semantics) | yes (needs labelled data, see Q26) | m3 spec §4; `thresholds.yaml` binary row | Same as Q26. |
| U-M3-7 | F | medium | m3, m1 | A-head gold does not exist (corpus is OFF/NOT); which output is compared with the baseline is undecided. | yes, for any A-head test | yes | RESOURCES.md item 5; protocol §1 | Owner decision on the A-head label source; then data. |

## 4. Measurement and test-infrastructure gaps

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| Q18 (U-M4-1, U-FLOW-3) | C | high | eval, m4, decision | `check_traps`, `run_item`'s predicted set and `pipeline_budget_report` all read `result.fired()` (content codes only). `binary_offensive` fires into the verdict and into `post_is_offensive` but is invisible to traps, per-code metrics and the flip-rate budget. See `TEST_SYSTEM_AUDIT.md` §3. | yes: no regression check exists for the one derived threshold | no | `eval/harness.py:265,428,525`; `actions.resolve`; `fusion.post_is_offensive` | A harness / trap extension that observes `signals.decision.binary_offensive` and the verdict (design in `VERIFICATION_PLAN.md` Gate 0 criteria; not implemented here). |
| G0-1 | C | high | decision, tests | No test in `AI/tests` or any `test_unit.py` references the derived value 0.320188 or a boundary input around it; `DecisionTest.setUp` overwrites every threshold with 0.5 and the binary tests inject their own config. The real config's binary boundary is therefore exercised by nothing except the contract example (one sentence at 0.021). | yes: a wrong boundary in the shipped yaml is undetectable by the suite | no | `protocols/threshold_derivation_binary_offensive_stage1.md` (value, `>=` rule, tie row 29308) | A boundary test against `fusion.load_config()` with scores at `t − ε`, `t`, `t + ε`, and the tie-row semantics. |
| Q21 / G0-2 | C | medium | eval, m2, m5, m6 | `ModuleEvaluator.run_item` sets `signals.pipeline = {emits_spans}` with no `degraded` key, so a stub is never degraded inside the harness; its clean fixture item becomes a true negative and its result file reads as healthy (traps 0/23, no failures). | yes: a stub result is indistinguishable from an implemented module's result | no | `eval/harness.py:256-258`; policy #15 (fail closed) | Harness marks stub / degraded runs explicitly in the report; `run_all` distinguishes them. |
| G0-3 | C | medium | eval | `_expect_failures` only compares a field when the module produced it (`got is not None`). A module that emits nothing passes every `expect` rule; no trap uses `expect` today, so the rule is dormant but its semantics make it unable to catch a missing output. | partly: `expect` cannot serve as a presence oracle | no | `eval/harness.py:273-280`; `eval/README.md` | Decide whether `expect` means "when produced" (documented) or "must be produced"; add a presence form if the latter is needed. |
| G0-4 | C | medium | integration, tests | `test_default_pipeline_on_clean_sentence` asserts only `verdict == review`, seven modules ran and the response shape. `test_stub_modules_are_degraded_and_named` filters m3 out of the degraded list (U-M3-5) so a machine without the artifact passes. Neither pins what a real post's fused content, binary fire state or explanation driver is. No end-to-end test asserts a non-degraded-driver verdict on the real pipeline. | yes: an end-to-end verdict regression on real modules is caught only if it changes `review` to something else | no | `tests/test_pipeline.py:64-95` | End-to-end verdict tests that assert `signals.decision.*`, the fused content and the driver on a fixed set of posts, with an explicit artifact-present precondition. |
| G0-5 | C | medium | eval, m2, m3, m4, m5, m6 | Per-module fixtures for m2–m6 contain one real clean item plus placeholders; the harness scores a 12–20-code space on one true negative. `eval/testsuite/dev.jsonl` holds two format examples and no gold. No per-code metric produced today for these modules measures anything. | yes, for any behaviour metric of m2–m6 | no | `modules/*/fixtures/cases.jsonl`; `eval/testsuite/README.md` | Real fixtures (owner-labelled, per the spec §"Required fixtures" of each module) and a real end-to-end gold set. Data, not code. |
| Q22 / G0-6 | C | low | eval | Local result files are a mixture: m0 / m1 produced against the 33-trap working-tree file with 5 / 20 repeats; m2–m6 against the 23-trap HEAD file with 200 repeats; `pipeline.json` against 23 traps. Only `m4_stage1b.json` is tracked. No result is a reference. | no, but every comparison must be re-run from one state | no | `eval/README.md` ("no result committed before its protocol") | One full `eval.run_all` on the committed baseline (after `BASELINE_WORKTREE.md` is acted on), recorded with its trap count and repeats. |
| G0-7 | C | low | thread counter, decision | `test_post_is_offensive` covers a fired content code, a form-only post and a degraded-only post. The `binary.fired` branch of `post_is_offensive` (a post that counts as a repeat only because of m3's score) is not covered by that test or by `ThreadPipelineTest`, which uses a content-scoring double. | partly: the counter's binary path has no direct oracle test | no | `fusion.post_is_offensive` docstring; ADR-004 amendment (#42, #52) | A decision-layer test with `raw_score ≥ t` and no content; a thread pipeline test with a binary-only double. |
| U-M4-3 | G | low | eval, m4 | `provides = {content}` on m4 makes the harness compute a 15-code space for a module that emits nothing by design. Cosmetic in the result file. | no | no | ADR-006 amendment | Deferred. |
| U-M3-5 / G0-8 | C | medium | m3, gate | The contract example embeds a real m3 `raw_score`; `scripts/check.sh` therefore cannot pass on a machine without the git-ignored 442 MB artifact, and `test_stub_modules_are_degraded_and_named` masks m3 to stay green there. The gate's pass/fail depends on an untracked file. | partly: results from a machine without the artifact are not comparable | no | ADR-003 amendment (#46: sentinel for latency, real `artifact_hash`); `contract_example.py` | Owner decision: precondition the gate on the artifact explicitly (fail loudly with a named reason) or make the example artifact-independent. Not decided here. |
| G0-9 | C | low | tests | The unit suite's count and skip count are not recorded in any tracked file that a gate compares against; HANDOVER says 255 / 10, this gate counts 268 methods and 5 skip markers (4 unconditional in m2 / m5 / m6, one conditional in m3). A silently skipped behaviour test reads as a pass in `check.sh` (`unittest` exits 0 on skips). | no | no | `scripts/check.sh` | Record the expected skip set; make an unexpected skip visible (e.g. `-v` diff or a skip budget). |
| Q19 (U-M1-9) | F | medium | m1, m3, m4 | terlik (runtime) and karaliste (frozen slice) disagree on about half of the karaliste hits; the specified terlik-vs-karaliste comparison exists only inside `m4_stage1b.json` and the derived-file header. Which lexicon labels m3's A head is undecided. | yes, for the A-head label oracle | yes, for m1 spec §6 deliverable and m3 A head | m1 spec §6; protocol §6 | Committed comparison report (m1 owner) and the owner's choice of label source. |
| Q20 (U-M1-5) | A | medium | m1 | 49 % of dev rows carry a `SUBSTRING_COLLISION` guard because the second collision pass fires on any token containing a folded terlik root (two-letter roots included). Spec §5 says guard firing is how precision is measured; a near-50 % base rate measures little. Whether to scope the pass is a design decision. | no for current behaviour (pinned by traps); yes for the precision metric's meaning | no | m1 spec §5; derived file `counts.rows_with_collision` | m1 owner decision, recorded in the spec (minimum root length or another rule). |
| Q23 | A | medium | m4 | No pre-registered stage-2 precision budget exists; m4 spec §10 requires it before the first stage-2 number. | no (stage 2 not started) | yes, stage 2 | m4 spec §10 | Owner commits the budget file. |
| Q24 | E | low | m1, eval | The derived-labels file was generated before its protocol was committed (`protocol.commit: null`); both are untracked. The protocol's sha256 in the file header equals the current protocol file's sha256, so the file is consistent with the protocol as it stands. | no | no | protocol §7 | m1 owner: commit protocol, then regenerate or accept, per the protocol's own rule. |

## 5. Blocked on data, decisions or resources (restated)

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| Q25 | A | high | decision, all | Every threshold, action and budget except `binary_offensive.threshold` is a placeholder. Any verdict-level test against the real yaml tests placeholders. | yes, for real-config verdict oracles (tests must pin their own numbers, as they do) | yes, per module DoD | `thresholds.yaml` PLACEHOLDER marks; `protocols/templates/threshold_derivation.md` | Derivations on dev per module owner; shared rows by the project owner. |
| Q26 | F | high | m3 | No "profanity present" gold, no B-labelled corpus, C slice unlabelled with no date. | yes | yes | RESOURCES.md items 4–7 | Data. |
| Q27 | F | medium | m5 | Turkish sarcasm corpus not named or requested; entry gate unresolved. | yes | yes | m5 spec §2 | m5 owner names and requests the corpus; gate record. |
| Q28 | A | medium | m6 | Written rules for `siz`, institution vs members, religion vs followers, sports-club supporters. | yes, for those cases | yes | m6 spec §4 | m6 owner writes the rules, Musaab approves. |
| Q29 | G | medium | m3, m4 | Stage 2 retrains m3's encoder and re-derives every m3 threshold. | no | no (stage 2 not started) | ADR-006 | Deferred to stage 2. |
| Q30 | G | low | API, thread counter | API thread side waits for `02_BACKEND_SPEC.md`; counter demo-scope limits have no spec home. | no | yes, API thread side | ADR-004; HANDOVER #38 | Owner commits the backend spec. |
| Q31 | G | low | eval | No frozen baseline for `fpr_increase_on_clean`. | no | no | HANDOVER #20 | Owner creates the baseline. |
| Q32 | D | low | m1, m6 | `A4`, `HOMONYM`, sacred-concept table, terlik-vs-karaliste report not built; gazetteer licences unrecorded. | no for what exists; the absent items have specs (m1 §4.3, §3) | yes | m1 spec §3, §4.3, §6, §8; ADR-007 | m1 owner builds them; A4 needs the owner-approved table. |
| Q33 | E | low | docs | HANDOVER §2 / §5 still say module owners are `_assign_`; every spec names an owner; `docs/team/README.md` is the assignment. | no | no | `docs/team/README.md`; spec headers | HANDOVER edit. |
| U-M2-3 | B | medium | m2, m3, decision | The m2 spec's headline number needs a detector scored on both channels plus a `norm_score` threshold; neither exists, and where that measurement lives is an open question in `docs/team/MOHAMMED.md`. | yes, for m2's headline metric | yes, for m2's DoD | m2 spec §8; MOHAMMED.md | Musaab decides where the two-channel measurement lives and who owns the `norm_score` row. |
| U-M5-2 | G | low | m5 | The 20 ms budget is a placeholder for a model that does not exist. | no | no | `thresholds.yaml` budgets | Deferred until an m5 candidate is measured. |
| U-M0-2 | — | — | m0, m3 | Same fact as Q3 (m0's protection does not reach m3). Folded into Q3. | | | | |
| U-DEC-1 | — | — | decision | Same fact as Q2. Folded into Q2. | | | | |
| U-DEC-2 | — | — | decision | Same fact as Q1. Folded into Q1. | | | | |

## 6. Baseline and environment observations (from `BASELINE_WORKTREE.md`)

| ID | Cat | Sev | Module(s) | Exact reason | Blocks testing | Blocks impl | Source of expected behaviour | What unblocks it |
|---|---|---|---|---|---|---|---|---|
| G0-10 | C | medium | all | The working tree carries five modified tracked files and three untracked project files that change what tests and traps see (10 more traps, 6 more m1 fixture items). Until they are committed or set aside, "the suite passes" describes an unreproducible state. | yes: any number produced now cannot be tied to a commit | no | `BASELINE_WORKTREE.md` | The owner commits the intentional changes (or stashes them) so HEAD is the baseline. |
| G0-11 | G | low | env | `core.autocrlf = true` on this machine; the project requires LF (`AI/.gitattributes`, HANDOVER §4.6: `check.sh` breaks under CRLF). `.gitattributes` should hold the line, but the setting is a standing risk for new files. | no | no | HANDOVER §4 | Verify line endings of every new file before commit. |
| G0-12 | G | low | env | The venv runs Python 3.14.0; the m3 requirements pin scikit-learn 1.6.1, which the team docs bound to Python 3.11–3.13. Inference works (torch and transformers import); training would not. | no | yes, m3 training on this machine | `docs/team/abdullah/*`; `m3/requirements.txt` | Environment choice for training; not a verification blocker. |

---

## 7. Summary counts

| category | items |
|---|---|
| A POLICY_DECISION_REQUIRED | Q1, Q2, Q3, Q4, Q12, Q16, Q20, Q23, Q25, Q28 |
| B CONTRACT_DECISION_REQUIRED | Q5, Q6, Q8, Q15, U-M2-3 |
| C TEST_INFRASTRUCTURE_GAP | Q18, G0-1, Q21/G0-2, G0-3, G0-4, G0-5, Q22/G0-6, G0-7, U-M3-5/G0-8, G0-9, G0-10 |
| D IMPLEMENTATION_GAP | U-M3-4, Q32 |
| E DOCUMENTATION_DRIFT | Q7, Q10, Q11, Q13, Q14, Q17, Q24, Q33 |
| F BLOCKED_BY_DATA_OR_EXTERNAL_RESOURCE | U-M3-7, Q19, Q26, Q27 |
| G DEFERRED_NON_BLOCKING | Q9, U-M6-4, U-DEC-3, U-M4-3, Q29, Q30, Q31, U-M5-2, G0-11, G0-12 |

Items that block a *test oracle* for behaviour that exists today (as opposed to behaviour that is
not built): Q1, Q2, Q3 (policy), Q5, Q6 (contract), Q18, G0-1, G0-2, G0-4, G0-10 (infrastructure).
Everything else blocks either an unbuilt deliverable or nothing.
