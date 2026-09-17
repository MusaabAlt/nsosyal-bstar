# tr-moderation — session handover

Written 2026-09-14 at the end of the scaffolding and hardening session; updated the
same day at the end of session 2 (D1 gaps, thread counter, m0 enclosed/superscript Latin) and
session 3 (B2 reset in fusion, offensive-only repeats, clean/adversarial latency, deterministic example)
and session 4 (owner-written spec sections inserted, spec check 8+2, thread rule on offensive posts only,
repeated latency timings) and session 5 (handover-readiness audit; owner decisions on family A,
NON_HUMAN_TARGET, the C head, m4 stage 1, m6 NER, fixture keys, setup and process docs).
Session 4 found `spec.md` of m2, m3, m5 and m6 deleted from the working tree; they were restored from HEAD
and the uncommitted session-2 edits to m3 and m5 re-applied verbatim before the insertion.
Commit history: `6c6c8d4` (skeleton) … `79f27e5` (owner decisions), `f73ede0` (first handover), then the
sessions 2-5 commits from branch `handover/sessions-2-5`, merged into the pipeline's `main` and imported into this
repository under `AI/` with `git subtree add` (`git log f73ede0..8b52595`). Decision rows cite files and
ADRs rather than commit hashes.

---

## 1. Decisions made in this session

Policy decisions were taken by the project owner; implementation choices by the assistant.
Each row names where the decision is recorded.

### Architecture and contract

| # | Decision | Reference |
|---|---|---|
| 1 | `AI/modules/<m>/spec.md` are the existing design specs, the single source of truth; `AI/modules/README.md` is the module guide. | `31083aa` |
| 2 | Spec field names follow the frozen contract (`out.content`, `out.form.patterns`, `source = "<module>@<channel>"`); the contract wins over the specs. | `4b07bc6` |
| 3 | Guards are scoped: a guard suppresses a content score only from its own module, and only on overlapping spans when both carry one; never a whole family across the post. `ContentScore.span`, `GuardResult.span` and optional `GuardResult.source` were added in a one-time contract unfreeze. Guards run before fusion. | ADR-001, `6daa1c6` |
| 4 | Spans are enforced at runtime: every module declares `emits_spans`; a span-declaring (or undeclared) module's score or guard without a span is dropped and degrades the module. The no-span fallback exists only for `emits_spans = False`. | ADR-001 amendment, `3f3a6e1` |
| 5 | `TR_LABELS` is keyed by (enum type, value) so `ContentCode.CLEAN` and `Family.CLEAN` no longer collide. | ADR-002, `305e2dd` |
| 6 | `AI/contracts/fixtures/analysis_result.example.json` regenerated from a real run (explicit instruction). | ADR-002 amendment, `79f27e5` |
| 7 | D1 (degrading sarcasm) is m5's own model with its own artifact and thresholds; `head_sarcasm` removed from m3 (m3 has two heads, A and B). | ADR-003, `79f27e5` |
| 8 | Entry-point convention: `AI/modules/registry.py::PIPELINE_ORDER` names module classes by dotted path; no module-level `MODULE` instance. `REGISTRY` renamed to `PIPELINE_ORDER`. | `ed921f9` |
| 9 | Rule 2 covers imports between modules; `contracts` and `eval.harness` are shared infrastructure outside its scope. A module's `eval.py` may import `eval.harness`, its own `module.py`, `contracts` and the stdlib only (allow-lists as data in `AI/tests/test_architecture.py`). | AI/CLAUDE.md, `305e2dd` |
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
| 23 | No eval result is committed before its protocol exists; `AI/eval/results/*.json` is git-ignored. | `94ccd90`, `AI/eval/README.md` |
| 24 | Metrics are per code with bootstrap CIs, never pooled; fixed code list; representation modules also report capture rate per pattern and damage rate on clean text; fixture and trap latency are separate. | `94ccd90` |
| 25 | Traps assert content (`must_not_fire`), exact fields (`expect`) and emitted form patterns / guards per module (`must`, `must_not`). | `a2c1d04` |
| 26 | Every `test_unit.py` has `test_contract_shape`, `test_input_not_mutated`, `test_never_raises`. m0 criterion: "every uppercase `I` maps to `ı`" (`test_sikinti_never_yields_profane_root`). | `52ddc97` |
| 27 | Stub rule: a stub states WHAT is missing and points to spec.md; it never prescribes HOW. Skipped tests grounded in no spec were deleted. | `c0c38aa`, `79f27e5`, AI/CONTRIBUTING.md |
| 28 | Rule 4 is enforced by an AST scan: numeric literals or literal-bound names in comparisons, threshold-like names, float literals in ordering asserts; module `eval.py` and `test_unit.py` included; `AI/tests/` excluded by design. | `305e2dd` |
| 29 | `AI/scripts/check.sh` fails loudly when it cannot verify `AI/contracts/` is unchanged. | `305e2dd` |
| 30 | MANIFEST columns: `artifact_id \| format \| sha256 \| thresholds_file \| derived_on \| date` (+ owner, licence). | `ed921f9` |

### Session 2 (2026-09-14)

| # | Decision | Reference |
|---|---|---|
| 31 | m5 does not read m3 embeddings; m3 does not publish embeddings or hidden states. Stated in both specs so no "m5 head on m3 representations" middle path is invented. | m5 spec §6, m3 spec §4, ADR-003 |
| 32 | "Small or distilled" is a CONSTRAINT on the m5 owner, not a model choice: a second full BERT pass per channel doubles encoder latency and memory. The m5 owner picks and measures the model. | m5 spec §6, ADR-003 |
| 33 | ADR-003's reason is artifact entanglement, not latency. The contract example regeneration (explicit owner instruction) is recorded in ADR-003's amendment; regenerated again at the end of session 2. | ADR-003 amendment |
| 34 | m0 spec acceptance uses the per-length budgets from `thresholds.yaml` (authoritative); the "1 ms per sample" wording is gone. | m0 spec §8 |
| 35 | `AI/decision/actions.py::most_severe` deleted (no caller). `test_most_severe_action_wins` kept: it never called that function, it tests verdict resolution through `fusion.decide`. | `AI/decision/actions.py` |
| 36 | POLICY: the repetition counter stamps events with SERVER RECEIVE TIME; the contract does not change. Reasons: the contract was already opened twice (ADR-001, ADR-002), and a caller-supplied timestamp is forgeable (backdating stays under the escalation count). A thread block carrying a timestamp is rejected. | owner decision, ADR-004 |
| 37 | The counter (`AI/pipeline/thread_counter.py`) is in memory, keyed by `(sender_id, target_id)`, resets on restart: demo scope, not production. It reads `thread.window_seconds` (PLACEHOLDER, not derived) and passes `repeat_count` down; it never reads `min_repeats` - the comparison stays in `AI/decision/fusion.py`. | ADR-004 |
| 38 | The CLI accepts `--thread '{"sender_id", "target_id", "thread_id"?}'` and several texts, observed in order, so Axis 4 is testable before the API exists. `AI/api/` is untouched and unowned until the owner says otherwise; its thread side waits for `AI/docs/frontend/02_BACKEND_SPEC.md` to be committed. | `AI/pipeline/run.py`, owner instruction |
| 39 | m0 maps negative circled, negative squared, squared, parenthesized, superscript and subscript Latin letters and non-flag regional indicators as HOMOGLYPH (via one import-time lookup table). Superscript DIGITS are never mapped. A regional-indicator run made only of valid region pairs is left as flags - so a word spelled only from valid flag pairs passes (known gap, tested). | `AI/modules/m0_charsafe/module.py` |

### Session 3 (2026-09-14)

| # | Decision | Reference |
|---|---|---|
| 40 | B2, option (a): decision-owned fields (`threshold`, `fired`, `active`, `suppressed`) are reset by `fusion.reset_decision_fields` at the start of every decision and assigned ONLY in `AI/decision/fusion.py`, with no exception. `AI/pipeline/run.py` detects and notes, never assigns. Protects direct callers of `decide()`; deciding twice gives the same answer. Fusion resets fields it owns and does not branch on which module ran. The fast-path check ignores module-set `fired`. Enforced by `AI/tests/test_architecture.py::test_only_fusion_assigns_decision_owned_fields`. | owner decision, `AI/decision/fusion.py` |
| 41 | POLICY: only OFFENSIVE posts count as repeats, and self-directed posts (`sender_id == target_id`) never count. Reason: in the bullying literature repetition is one of three elements with intent and power imbalance; counting every post measures conversation frequency - two friends who talk a lot would escalate. | owner decision, ADR-004 amendment |
| 42 | Applying #41: fusion runs in two stages, `decide_post` (reset, thresholds, binary, guards, fusion, form) and `conclude` (thread rule, verdict, explanation); `decide` = both. The pipeline asks `fusion.post_is_offensive` between them and passes the answer to the counter. `post_offensive` = a content code fired after guards, or binary offensive fired; form patterns and degradation never count (assistant's reading, to confirm - see §5). Recorded as `signals.decision.post_offensive`. The server receive time is taken with `ThreadCounter.now()` at arrival. | ADR-004 amendment |
| 43 | POLICY: the thread explanation is sender-to-target across threads: "Aynı gönderenin aynı hedefe yönelik N saldırgan mesajı nedeniyle içerik ...". | owner decision, `AI/decision/actions.py` |
| 44 | POLICY: latency budgets are for CLEAN input. Adversarial input is measured and reported alongside, never hidden: module eval output has `latency.clean` and `latency.adversarial` columns (same bands), `within_budget` from clean only, and `adversarial_over_budget` as a published finding. Clean = `expect_clean: true`, or no `expect_clean` and no gold codes. m0 fixture gained clean and adversarial items at 280, 1000 and 5000 chars so every band is measured. | owner decision, `AI/eval/harness.py`, AI/CONTRIBUTING.md |
| 45 | POLICY: the flag-pair gap is accepted and recorded as a known, tested limitation in m0 spec §2. Squared and subscript mappings stay in scope. | owner decision, m0 spec §2 |
| 46 | POLICY: the contract example is deterministic. `latency_ms` and `per_module_ms` are frozen to the sentinel `0.0`; `artifact_hash` stays real so a genuine config or module-version change still trips the gate. Generated with `python -m pipeline.contract_example` (`--check`, `--write` only on explicit instruction). Reason: a gate that fails on every legitimate regeneration is one the team learns to ignore. | owner decision, ADR-003 amendment |
| 47 | m0 version bumped to `0.2.0` (behaviour changed in session 2), so `artifact_hash` distinguishes it. | `AI/modules/m0_charsafe/module.py` |

### Session 4 (2026-09-14)

| # | Decision | Reference |
|---|---|---|
| 48 | Owner-written spec sections inserted verbatim into m2-m6 (checked character for character), sections renumbered from 1, cross-references fixed (m6 4.1-4.3, the m4 open-question note's "§4", stub docstrings, registry, harness). The ADDITIONS files were deleted after insertion: two sources of truth is the defect that cost a remediation round. ADRs keep the section numbers of their time. | owner instruction |
| 49 | The m4 stage-1 contradiction and the m6 NER dependency conflict are in their specs as written, unresolved: open questions for the owner, not instructions. | owner instruction, m4 / m6 spec final sections |
| 50 | m2 order follows the renumbering table: Required fixtures §9, Leakage rule §10 - the leakage rule constrains how the evaluation set is built, so it reads after the fixtures. | owner decision |
| 51 | Spec check: EIGHT sections required (Objective, What it catches / does not catch, Contract, Forbidden — with reasons, Metrics this module must produce, Required fixtures, Acceptance criteria, Definition of done); "Approach" and "Research pointers" RECOMMENDED - a missing one emits `SpecSectionWarning`, never a failure. Prose is not edited to satisfy an automated check (m4's "What it must do" is the better title). | owner decision, `AI/tests/test_architecture.py`, AI/CONTRIBUTING.md |
| 52 | POLICY (confirmed): "offensive" for the counter = a content code fired after guards, or binary offensive fired; a review caused only by stubs/degradation does not count - otherwise the counter measures how unfinished the system is. | owner decision, ADR-004 amendment |
| 53 | POLICY: the thread rule fires only when THIS post is offensive. Escalation is an action on this post; escalating a benign message because of earlier ones acts on the person rather than the content. Repetition raises severity of an offensive post, never creates it. `repeat_count` on a clean post still reports history as a fact. | owner decision, ADR-004 amendment, `fusion.apply_thread` |
| 54 | POLICY: latency is timed repeatedly - one run per item reported as "p95" is a fabricated statistic. Default 200 timings per item (`--latency-repeats`, `LATENCY_REPEATS` in check.sh), also used for pipeline latency; `latency.repeats`, `n_items` and `n` (timings) are recorded next to every p50/p95. The count is a harness setting like `--n-boot`, not a `thresholds.yaml` value, so changing it never changes `artifact_hash` or the frozen example. | owner decision, `AI/eval/harness.py`, AI/eval/README.md |
| 55 | m0 spec §2 Catches lists styled Latin letters. `AI/scripts/check.sh` runs `python -m pipeline.contract_example --check` before the `AI/contracts/` gate. | owner decision |

### Session 5 (2026-09-14)

| # | Decision | Reference |
|---|---|---|
| 56 | POLICY: family A is assigned from the target. m1 and m3 report "profanity present" on the `A1` carrier (the contract has no generic A code); the decision layer assigns no target -> A1, individual -> A2, group -> A3 before any threshold, in `fusion.resolve_family_a`. A4 stays with m1. `family_a.by_target.non_human` (A1) and `family_a.target_min_confidence` are placeholders the owner did not decide. | owner decision, ADR-005 |
| 57 | POLICY: `NON_HUMAN_TARGET` moves from m6 to m1, which raises it on its own family-A matches from m6's published `target_type` / `target_confidence`; it suppresses `[A1, A2, A3]`. m6 no longer provides guards. `PIPELINE_ORDER` runs m6 before m1. | owner decision, ADR-005 |
| 58 | POLICY: C1-C5 are a third head on m3's encoder; m4 owns the C1-C5 and `binary_offensive` thresholds and the slice repair, not a model, and reads only `raw_score`, `norm_score`, `artifact`. | owner decision, ADR-006 |
| 59 | POLICY: m4 stage 1 is the single global cost-derived threshold, exactly as measured; `threshold_when` on `binary_offensive` is removed and becomes stage 1b, measured against stage 1 at equal coverage before replacing it. The open-question note is removed from m4's spec. | owner decision, ADR-006 |
| 60 | POLICY: m6 named entities are gazetteer plus morphology for v1; no transformer NER, no fourth encoder pass. The note and its wrong reading of rule 6 are removed. | owner decision, ADR-007 |
| 61 | Fixture key names in the m2-m5 specs follow `AI/eval/harness.py` (`expected`, `expect_patterns`, `expect`, `context`, `expect_clean`); m4's slice is `context.signals.m1_lexicon.lexicon_hit`; m5's `inversion_span` stays as an annotation not read by the harness. Every module's fixture file is `fixtures/cases.jsonl` (the stubs' `dev.jsonl` renamed; the harness fallback removed). | owner decision |
| 62 | Stale references fixed: `thresholds.yaml` (m2 §8, guard comments), `AI/artifacts/MANIFEST.md` (m3 §8, §5), `AI/eval/testsuite/README.md`, README flow diagram (order, three heads, fast path disabled), `AI/modules/README.md` latency line. | owner decision |
| 63 | AI/CONTRIBUTING.md has a Setup section (venv, install, commands in order, `BASE_REF=$(git merge-base HEAD master) bash AI/scripts/check.sh`) and a paragraph on fail-closed and why every verdict is `review` today. | owner decision |
| 64 | PROCESS: a module owner proposes spec changes and Osama approves them; a module owner may edit their own category rows in `AI/decision/thresholds.yaml` (derived on dev, separate reviewed change). AI/CONTRIBUTING.md and `AI/modules/README.md` say so. | owner decision |

### Final batch (2026-09-14)

| # | Decision | Reference |
|---|---|---|
| 65 | CONTRACTS (explicit owner instruction): both examples regenerated from real current runs (`python -m pipeline.contract_example --write`, which now generates `module_output.example.json` too, from m0 on `SIKINTI`), and the `AI/contracts/schema.py` docstring says the decision layer resets module-set decision fields. `AI/contracts/` is frozen again. | ADR-003 amendment |
| 66 | m4 is a NON-STUB module that emits nothing yet; `provides` stays `content`. A stub there made every verdict `review` and hid the fail-closed behaviour the project demonstrates. | owner decision, ADR-006 amendment |
| 67 | POLICY: `family_a.by_target.non_human` stays `A1` (owner-confirmed); `family_a.target_min_confidence` stays a marked placeholder. | owner decision, ADR-005 amendment |
| 68 | PROCESS: the shared threshold rows A1-A3 and C1-C5 are owned by the project owner, not by a module owner. | owner decision, AI/CONTRIBUTING.md |

---

## 2. Current state

**Done and working**
- Contracts (`AI/contracts/`), frozen and owned by Musaab; changes only through an ADR (ADR-001, ADR-002 so far).
- Decision layer: fusion, per-module guard scoping, signal-conditioned thresholds, thread rule, fail-closed verdicts, Turkish explanations.
- Pipeline: safe construction, loading and processing; output validation; span enforcement; deep-frozen signals; bounded response; CLI.
- HTTP API (`AI/api/main.py`), stdlib only, JSON on every failure. No thread support yet (decision #38).
- Axis 4 thread path reachable from the CLI: in-memory counter of offensive, non-self-directed posts, server receive time (ADR-004). While m1-m6 are stubs no post is offensive, so from the CLI it runs but never counts; counting is tested with a scoring test double.
- Decision-owned fields assigned only in `AI/decision/fusion.py` (B2 closed, decision #40).
- Evaluation harness: per-code CIs, representation metrics, traps with form/guard rules, per-length latency bands in clean and adversarial columns, pipeline budgets (flip rate, latency).
- `m0_charsafe` fully implemented (reference module).
- `m1_lexicon` implemented on terlik 0.1.0 balanced (not a stub): A1 carrier, SUBSTRING_COLLISION and NON_HUMAN_TARGET with spans. A4 and HOMONYM not built. Per-row dev labels in `AI/eval/derived/m1_lexicon_dev_seed42.json` (`AI/protocols/m1_lexicon_dev_labels_protocol.md`); the evaluation slice stays `AI/eval/frozen/study_slice_dev.json`.
- Architecture tests for rules 2, 4 (thresholds and decision-field assignment), 6 and 7, span declarations and the entry-point convention.
- 255 tests; 10 skipped behaviour tests that belong to unimplemented modules. The spec check warns (does not fail) that m2, m3, m4 and m6 have no section titled "Approach" and m5 has no "Research pointers".
- Audit status: re-run `BASE_REF=$(git merge-base HEAD master) bash AI/scripts/check.sh` rather than trusting a
  recorded result. The base is `origin/master` (the script's default); against it at `b6a0e1f`, after the import
  under `AI/`, every gate passed, including "contract example current" and the `AI/contracts/` gate. The earlier
  base `f73ede0` no longer applies: that commit predates the `AI/` prefix, so its contracts sit at `contracts/`
  and the gate run against it reports every contract file as added, not only the three changed on the owner's
  explicit instruction (decision #65).

**Stubbed (declare `stub = True`; every result is degraded, verdict `review`)**
- m2_deobf, m3_encoder, m5_sarcasm (gated by its spec §2), m6_target.
- m4_implicit is NOT a stub: it emits nothing by design (C1-C5 come from m3, decision #66).

**Blocked on the project owner**
- Owner-written spec sections are inserted in m2-m6 ("What it catches / does not catch", "Required fixtures", named tools); two of them carry open questions for the owner (see §5).
- All thresholds, actions and budgets in `AI/decision/thresholds.yaml` are placeholders until derived on dev.
- Module owners are `_assign_` in every spec.

---

## 3. Commands

Run from `AI/` with the project venv (`python -m pip install -r requirements.txt` installs pyyaml).

```bash
python -m pipeline.run "Bu bir test cumlesi"          # full contract JSON (add --compact for one line)
python -m pipeline.run "a" "b" "c" --compact --thread '{"sender_id": "u1", "target_id": "u2"}'   # Axis 4 (JSON array)
python -m pipeline.contract_example --check           # 0 when the frozen contract example is current (check.sh runs it)
python -m eval.run_all --latency-repeats 50           # fewer timings for a quick local run (default 200)
python -m unittest discover -p "test_*.py"            # all tests (add -v for names)
python -m modules.m0_charsafe.eval                    # one module alone; writes eval/results/m0_charsafe.json
python -m eval.run_all                                # every module + pipeline budgets
python -m api.main --port 8080                        # POST /analyze {"text": "..."}
BASE_REF=<commit> bash scripts/check.sh               # pre-merge check; fails without a base ref
```

---

## 4. Conventions a new session must not violate

1. **`AI/contracts/` is frozen and owned by Musaab.** Never edit it without an explicit instruction; every such change gets an ADR in `AI/protocols/` and the contract is re-frozen immediately after.
2. **No threshold outside `AI/decision/thresholds.yaml`.** Modules emit `code / score / source / span`; only the decision layer sets `threshold / fired / active / suppressed`. Tests must not hide thresholds either (the AST scan checks module tests).
3. **No cross-module imports.** Only `AI/modules/registry.py::PIPELINE_ORDER` knows order; modules share work only through `ctx.signals`.
4. **Policy is proposed, not decided.** Anything that changes what the system concludes about content — verdicts, actions, what counts as degraded or clean, guard ownership, escalation rules — is presented to the owner with options. Implementation choices are fine to make.
5. **Spans are required where declared.** A module with `emits_spans = True` (m1, m6) puts the exact triggering span on every score and guard; one without a span is dropped and the module degrades.
6. Also binding: fail closed (never clean while degraded); a stub never prescribes HOW; no result committed before its protocol; a module never mutates `ctx.text`; heavy dependencies only in the owning module's `requirements.txt`; files use LF line endings (`AI/.gitattributes`; `AI/scripts/check.sh` breaks under CRLF).

---

## 5. Open questions

| Question | Owner |
|---|---|
| LEFT OPEN (module owners): m3 scores at a non-human target stay unsuppressed - m1's `NON_HUMAN_TARGET` guard cannot suppress another module's scores under ADR-001 (profanity only m3 detects, and B1/B2). | m1 / m3 owners |
| LEFT OPEN (module owners): stage 2 retrains m3's encoder, which carries families A, B and C, so a new m3 artifact forces re-derivation of every m3 threshold - the coupling ADR-003 removed for D1 (ADR-006). | m3 / m4 owners |
| LEFT OPEN (module owners): m4's slice repair cannot be measured by its own eval - the harness does not read `binary_offensive`. | m4 owner |
| LEFT OPEN (module owners): m0 spec §4 does not describe the implemented passes (layout controls and emoji ZWJ kept, combining marks, styled Latin); m2 spec §9 requires `text[start:end]` to equal `evidence`, which is free text in the schema and in m0. | m0 / m2 owners (spec changes approved by Osama) |
| `thread.window_seconds` is an arbitrary placeholder; derive it. | Project owner |
| The counter's demo-scope limits (in memory, per process, resets on restart, ids unverified) are recorded in ADR-004 and the counter docstring; there is no committed spec to state them in. Add them to `AI/docs/frontend/02_BACKEND_SPEC.md` when it is committed. | Project owner |
| API thread side: implement per `AI/docs/frontend/02_BACKEND_SPEC.md` once committed. | Owner to confirm owner of `AI/api/` |
| `AI/contracts/fixtures/module_output.example.json` is stale (shows `offsets`); regenerating it needs an explicit instruction. | Osama |
| When is the frozen baseline created, so `fpr_increase_on_clean` can return (decision #20)? | Project owner |
| m5 entry gate: availability of the Turkish sarcasm corpus (spec §2). | m5 owner |
| m1: confirm `terlik` availability and licence offline (spec §4.3, §8). | m1 owner |
| m6: written rules for `siz`, institution vs members, religion vs followers (spec §4). | m6 owner |
| Every placeholder in `AI/decision/thresholds.yaml` (thresholds, actions, budgets, fast-path margin) must be derived on dev with `AI/protocols/templates/threshold_derivation.md`. | Each module owner; actions: project owner |
| Module owners are `_assign_` in all seven specs. | Project owner |

---

## 6. If you are a fresh session, read these files in this order

1. `AI/CLAUDE.md` — rules, axes, modules, entry points, commands.
2. `AI/docs/HANDOVER.md` — this file.
3. `AI/modules/README.md` — how to work inside a module.
4. `AI/CONTRIBUTING.md` — stub rule, workflow, acceptance checklist, protocol templates.
5. `AI/protocols/ADR-001-guard-scoping.md` through `ADR-007-m6-ner-gazetteer.md`, in order.
6. `AI/contracts/codes.py`, `AI/contracts/schema.py`, `AI/contracts/module_api.py`.
7. `AI/decision/thresholds.yaml`, then `AI/decision/fusion.py` and `AI/decision/actions.py`.
8. `AI/pipeline/run.py` and `AI/modules/registry.py`.
9. `AI/modules/m0_charsafe/` — the reference module (module, spec, tests, fixtures).
10. `AI/modules/<the module you work on>/spec.md`.
11. `AI/eval/README.md`, `AI/eval/harness.py`, `AI/eval/traps/traps.jsonl`.
12. `AI/tests/test_architecture.py` — the rules as code.
