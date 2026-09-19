# Open questions — what the repository does not settle

Audit reconstruction, 2026-09-17, branch `audit/m1-m6` at `f063ddf` plus the uncommitted working
tree. Each entry states the evidence, who the specs make responsible, and whether it was already
recorded (HANDOVER §5, an ADR, a team doc) or is new in this audit. No entry proposes a fix; the
"impact" column says what a verifier will observe if the question stays open. Tags `U-…` point at
the detailed entries in `MODULE_CONTRACTS.md` and `PIPELINE_FLOW.md`.

Severity is the auditor's reading of the impact on the verdict a real post receives today or on a
number the project publishes: **high** changes a verdict or a published number; **medium** blocks a
specified deliverable or a measurement; **low** is documentation drift.

---

## A. Verdict-changing interactions (new in this audit unless marked)

| # | question | evidence | severity | owner | recorded before? |
|---|---|---|---|---|---|
| Q1 | While m6 is a stub, every family-A hit is assigned `A1` and `A1`'s placeholder action is **nudge**. A post that m1 flags and m3 scores below 0.320188 is therefore *published with a warning* even though the result is degraded and the same post would be `A2` → review or `A3` → block once m6 resolves the target. Is "a more severe verdict under degradation stands" (HANDOVER #16a) meant to cover a verdict that is more severe than clean only because the target module is missing? | Probe A in `PIPELINE_FLOW.md` §7: verdict `nudge`, explanation "kullanıcı uyarılarak yayımlandı; ancak değerlendirme eksik çünkü m6_target henüz uygulanmadı". `actions.resolve` upgrades only `clean`. | high | project owner (policy) | no |
| Q2 | `binary_offensive` is not suppressible by any guard, so the ADR-005 / annotation-guideline case "insult at a film → CLEAN + NON_HUMAN_TARGET" is reachable only when m3's binary score stays below the threshold on that text. On a text the model scores as OFF (likely for most insults), the m1 guard suppresses `A1` and the verdict is still `review`. Is that the intended precedence between the guard design and the study's threshold? | Probe D: A1 suppressed, verdict review, driver binary. `thresholds.yaml` comment "Not suppressible by guards". ADR-005 amendment leaves m3 scores at a non-human target open for m1 / m3 owners; this audit extends it to `binary_offensive`. | high | project owner; m1 / m3 owners | partially (HANDOVER §5 row 1 covers m3 content scores, not the binary score) |
| Q3 | m3 scores `ctx.text`, not `charsafe_text` (owner decision so the fitted threshold keeps its meaning). m0's stated objective is to stop character-level attacks "before any model sees it". Which document is authoritative, and is the trade-off (invisible characters, homoglyphs and styled Latin reach BERT unchanged) accepted and recorded as a known limitation of the current artifact? | `m3/module.py:16-17`, `test_scores_original_text_not_charsafe_or_normalized`; m0 spec §1; probe with `ap​tal herif` (U-M0-2, U-M3-2). | high | project owner; m0 / m3 owners | no |
| Q4 | Under the placeholder actions, `A1` = nudge while `binary_offensive` = review. Any lexical profanity that m3 also flags is reviewed; one m3 misses is nudged. Is the ordering "lexicon hit alone < model hit" intended, or an artifact of two placeholders? | Probes A and B. | medium | project owner (actions are policy, HANDOVER #13, #68) | no |

---

## B. Contract gaps between modules

| # | question | evidence | severity | owner | recorded before? |
|---|---|---|---|---|---|
| Q5 | No contract or spec defines an offset map from m2's `normalized_text` back to the original text. m1 emits spanned scores for the normalized channel only when the normalized text has the **same length** as the raw channel and then assumes 1:1 alignment; otherwise the hit is flag-only and can never fire. m3's spec asks to "truncate both channels at the same character offset", which needs the same map. What carries it? **Update 2026-09-18:** the carrier is ADR-008 (implemented on both sides, PROPOSED, owner to ratify). The **label** half is decided: the A-head pseudo-label counts a normalized-only hit when it carries a valid span (`protocols/m1_lexicon_train_labels_protocol.md` §5). The **runtime** half — whether a normalized-only hit fires a code at inference — remains open and unchanged (`fusion.strategy: max` as configured). | `m1/module.py:122-127`, `test_scores_tagged_with_channel`, `test_normalized_channel_without_offset_map_reports_flag_only`; m2 spec §6 lists no signal (U-M1-2, U-M2-2). | high (blocks the parallel-channel design m2 exists for) | m2 owner proposes, Musaab approves; m1 owner | partially (ADR-008; label half decided 2026-09-18) |
| Q6 | m6's target reaches consumers by two routes with two thresholds: `result.target` (validated by the pipeline, gated by `family_a.target_min_confidence`) and `signals.target_type` / `target_confidence` (unvalidated, gated by `guards.NON_HUMAN_TARGET.threshold` after m1 copies it into the guard). Which route is authoritative when they disagree, and should the two placeholders be one number? | `fusion.family_a_code`, `m1/module.py:207-218`, `Pipeline._merge` target checks (U-M6-1, U-M6-2). | medium | project owner; m6 / m1 owners | no |
| Q7 | m1 spec §3 says it reads `ctx.text`; the code reads m0's `charsafe_text` and maps spans through m0's internal `_offsets`, a signal no spec names as an interface. Should the m1 spec and the m0 contract (§3 "Writes") record `_offsets` and the charsafe input? | `m1/module.py:106,186-187`; protocol §4 "raw = m0's charsafe text" (U-M1-1). | low | m1 / m0 owners, Musaab approves | partially (protocol states it; spec does not) |
| Q8 | A `SUBSTRING_COLLISION` guard is deduplicated by span across channels and carries no channel, so a collision found on one channel suppresses a hit on the other channel at the same span. Is a cross-channel veto intended? | Probe G; `m1/module.py:137-141`; `fusion.guard_applies` (U-M1-6). | medium (only observable once m2 ships) | m1 owner | no |
| Q9 | `lexicon_hit_raw` / `lexicon_hit_norm` may be `True` with no emitted score (no offset map). Do consumers of the flag (stage 1b, m3 A-head labels, the counter's notion of "offensive") accept "hit but nothing fired"? | `m1/module.py:120-127`; protocol §3 check 6 (U-M1-3). | low | m1 owner | partially (protocol tolerates it) |

---

## C. Specification vs implementation drift

| # | question | evidence | severity | owner | recorded before? |
|---|---|---|---|---|---|
| Q10 | m3 spec §4 (three heads, both channels, `norm_score`, content per code) describes a module that does not exist; the implemented module is a binary OFF/NOT wrapper. The spec carries no status note; HANDOVER §2 (working tree) still lists m3 among the stubs; `CONTRIBUTING.md` says m1, m2, m3, m5, m6 are stubs; `README.md` says m3 is partial. Which document states the current state? | `m3/module.py` docstring; `AI/README.md`; HANDOVER §2 "Stubbed" list; CONTRIBUTING "Why every verdict is review today" (U-M3-1). | low (docs) / medium (a new session reading HANDOVER will be wrong about m3) | Musaab | no |
| Q11 | m3's truncation policy (128 tokens, first kept, note) is in the module docstring and the derivation protocol, not in spec §5 as §9 requires; spec §9 also states 512 as the maximum. | `m3/module.py:52-53`; m3 spec §5, §9 (U-M3-3). | low | m3 owner, Musaab approves | no |
| Q12 | m1 spec §8 "p95 latency under 5 ms" vs `thresholds.yaml` per-length bands (3 / 10 / 30 / 140 ms) adopted by owner decision, vs a measured adversarial p95 of ~301 ms on a 5000-char adversarial item. Which is the acceptance criterion, and is the adversarial overrun accepted? | ADR-003 amendment (m1 budget per length); `eval/results/m1_lexicon.json` `latency.adversarial` (U-M1-7). | medium | m1 owner; project owner (budget) | partially (HANDOVER #44 makes adversarial overruns a published finding) |
| Q13 | Stage 1b's condition signal: `lexicon_hit_raw` in the protocol and the script, `lexicon_hit` in m1 spec §8, m4 spec §4 and the `thresholds.yaml` comment. Not in force today, but if stage 1b is re-proposed after m2 ships the two diverge. | `protocols/m4_stage1b_protocol.md` §3; `eval/m4_stage1b.py:74`; m1 spec §8 (U-M1-8, U-M4-4). | low | m4 owner | no |
| Q14 | m0 spec §4 (three steps) does not describe the five implemented passes; m2 spec §9 requires `text[start:end] == evidence`, which m0's own evidence format does not satisfy. | HANDOVER §5 row 4 (U-M0-1, U-M2-1). | low | m0 / m2 owners, Musaab approves | **yes** (HANDOVER §5) |
| Q15 | m4 spec §9 requires a unit test that each fixture's `context.signals.m1_lexicon.lexicon_hit` equals what m1 returns on that text. Rule 2 forbids m4's tests from importing m1. Which rule yields? | m4 spec §9 "Slice discipline"; `tests/test_architecture.py::test_modules_do_not_import_each_other` (U-M4-5). | low | Musaab | no |
| Q16 | m1 spec §4.2 asks for the two-tier hard / soft structure; the module relies on terlik's `suffixable` flag plus a hard-coded two-word `CLEAN_PREFIXES` whitelist. Does that meet §4.2 and §10 ("the two-tier list structure is in place")? | `m1/module.py:48-55`; `m1/README.md` (U-M1-4). | low | m1 owner, Musaab approves | no |
| Q17 | m3 spec §5 says 36,232 Çöltekin tweets; the verified files hold 31,756 + 3,528 = 35,284. | `docs/team/abdullah/RESOURCES.md` open item 3 (U-M3-6). | low | Musaab | **yes** (RESOURCES.md) |

---

## D. Measurement gaps

| # | question | evidence | severity | owner | recorded before? |
|---|---|---|---|---|---|
| Q18 | *(as found in the audit)* The harness, the traps and the flip-rate budget all read `result.fired()` (content codes only); `binary_offensive` was invisible to every automated measurement. **Resolved on the instrument side by Gate 1 (verified 2026-09-18 against the code and `tests/test_harness_gate1.py`):** `check_traps` records one observation per trap with the binary state (`observations[].binary`, `binary_fired`, `binary_observable`), accepts a module-scoped `binary: {modules, must_not_fire}` trap rule, and `pipeline_budget_report` reports `binary_offensive_on_traps` (`fired_with_channel_trap_ids`, `flipped_by_channel_trap_ids`, `budgeted: false`). **What remains is policy, not a gap:** no committed trap carries the `binary` rule and binary flips are reported but not budgeted, because whether a binary fire on a clean collision trap is a regression is Q2. Reading this row as "the binary score is invisible" is stale. | `eval/harness.py::observe`, `check_traps`, `pipeline_budget_report`; `tests/test_harness_gate1.py`; `eval/README.md`; `TEST_SYSTEM_AUDIT.md` §… | medium (policy: which traps carry the rule, whether binary flips are budgeted) | project owner (Q2); m4 owner | yes (GATE1_RESULTS §2.3, TEST_SYSTEM_AUDIT) |
| Q19 | m1's runtime signal (terlik) and the frozen evaluation slice (karaliste) disagree on roughly half of the karaliste hits (EVAL: 161 of 309 karaliste hits are terlik-free; 67 terlik hits are karaliste-free; dev: 459 vs 614 hits). The spec owes a committed terlik-vs-karaliste comparison; today the comparison exists only as a 2×2 table inside `m4_stage1b.json` and counts in the derived-file header. Which lexicon will label m3's A head, and what does the slice difference do to the "63.5 % lexicon-free" story? **Update 2026-09-18:** the comparison is committed (`eval/results/m1_terlik_vs_karaliste.json`, re-run on the implemented m2/m6: terlik recall 0.392 vs 0.386, FPR 0.025 vs 0.067; the normalized channel adds no hit on dev); terlik labels the A head (owner decision, `docs/blockers/m3_head_labels.md`); the "63.5 %" story keeps karaliste's frozen slice and is untouched. Open only for the report wording. | `eval/results/m4_stage1b.json` `slice_agreement_eval`; derived file `counts`; m1 spec §6 (U-M1-9). | low | project owner (report) | yes (comparison committed; label decision recorded) |
| Q20 | 49 % of dev rows carry a `SUBSTRING_COLLISION` guard because the second collision pass fires on any token containing a folded terlik root (two-letter roots included). The spec says guard firing is how precision is measured. Is a near-50 % base rate acceptable, or should the pass be scoped (e.g. minimum root length)? | derived file `counts.rows_with_collision = 2356 / 4764`; `m1/module.py:170-177` (U-M1-5). | medium | m1 owner | no |
| Q21 | Per-module eval of a stub is vacuous (the harness never degrades, so the clean item is a true negative and traps pass). `m2`, `m5`, `m6` result files therefore look healthy. Should `run_all` mark stub results as such? | `eval/results/m{2,5,6}.json`; `harness.run_item` sets no `degraded`. | low | Musaab | no |
| Q22 | The committed `eval/results/*.json` for m0 / m1 were produced with 5 / 20 latency repeats against the 33-trap working-tree file; m2–m6 with 200 repeats against the 23-trap HEAD file. Only `m4_stage1b.json` is tracked. Which run is the reference before the trap additions are committed? | file headers (`latency.repeats`, `traps.n`); `git ls-files AI/eval/results`. | low | Musaab | no |
| Q23 | Stage 2 has no pre-registered precision budget yet; the only budget on record (0.02) belongs to stage 1b. m4 spec §10 requires the stage-2 budget committed before the first stage-2 number. | `protocols/` listing. | medium (blocks stage 2) | m4 owner | implicitly (spec) |
| Q24 | *(closed 2026-09-18)* The m1 derived-labels file was generated before its protocol was committed. Both files (dev and train) are now generated after their protocols, from a clean tree, with `committed_and_unchanged: true`, and `tests/test_m1_lexicon_labels.py` fails the suite if a committed derived file is stale or was generated against an uncommitted protocol. | `eval/derived/*.json` headers; `python -m eval.m1_lexicon_labels --check`. | closed | m1 owner | yes |

---

## E. Items blocked on decisions or data (already recorded; restated for completeness)

| # | item | where recorded |
|---|---|---|
| Q25 | Every placeholder in `thresholds.yaml` (all category thresholds and actions, guard thresholds, `form.min_confidence`, `family_a.target_min_confidence`, fast-path margin, all budgets, `thread.window_seconds`, `min_repeats`) must be derived on dev with `protocols/templates/threshold_derivation.md`; shared rows A1–A3 and C1–C5 are the project owner's. | HANDOVER §5; CONTRIBUTING step 7 |
| Q26 | m3 A / B / C heads: **A decided 2026-09-18** (terlik pseudo-labels train, human dev subset evaluates; `docs/blockers/m3_head_labels.md`) — the human dev subset is the remaining data item; no B-labelled corpus found; C slice being labelled with no date. Training-code location **ratified**: `AI/training/` (`training/README.md`). | `docs/team/abdullah/RESOURCES.md` items 4–7; ABDULLAH.md; `docs/blockers/m3_head_labels.md` |
| Q27 | m5 entry gate: the Turkish sarcasm corpus is not yet named or requested. | START_HERE.md task 1; RESOURCES.md item 10 |
| Q28 | m6 written rules for `siz`, institution vs members, religion vs followers; sports-club supporters position. | HANDOVER §5; m6 spec §4 |
| Q29 | Stage 2 retrains m3's encoder and would force re-derivation of every m3 threshold (the coupling ADR-003 removed for D1). | HANDOVER §5; ADR-006 |
| Q30 | API thread side waits for `AI/docs/frontend/02_BACKEND_SPEC.md`; the counter's demo-scope limits have no committed spec to live in. | HANDOVER §5; ADR-004 |
| Q31 | Frozen baseline for `fpr_increase_on_clean` (decision #20) does not exist. | HANDOVER §5 |
| Q32 | m1: terlik licence confirmed offline (README says MIT); A4 sacred-concept extension and HOMONYM not built; m6 named-entity gazetteer licences to record. | m1 README; HANDOVER §5; ADR-007 |
| Q33 | Module owners are assigned in `docs/team/README.md` but every spec header except m0–m6's "Owner" line was `_assign_` at handover time; the specs now name owners (Musaab, Mohammed, Abdullah). HANDOVER §5 still lists "Module owners are `_assign_`". | HANDOVER §5 (stale) |

---

## F. Operational observations (not questions, but a verifier should know)

- The full unit suite passed on this machine (268 tests, 4 skipped, ~53 s) with Python 3.14.0 in
  `AI/.venv`, although the m3 requirements pin scikit-learn 1.6.1 which the team docs say needs
  Python 3.11–3.13 (torch and transformers imported fine; scikit-learn is training-only).
- `python -m pipeline.contract_example --check` exits 0; `AI/contracts/` is byte-identical to
  `master`.
- Every `Pipeline()` construction hashes the 442 MB checkpoint and builds BERT on CPU; tests, the
  CLI, the API and the harness all pay it. `scripts/check.sh` cannot pass on a machine without the
  git-ignored artifact (the frozen example embeds a real `raw_score`).
- The `m2_deobf/spec.md` working-tree change replaces a `---` rule with `--`; it reads as an
  accidental edit.
- HANDOVER "255 tests; 10 skipped" is stale (268 / 4).
- ADR-001 and HANDOVER #17 still describe m6 as a guard producer; ADR-005 / HANDOVER #57 moved
  `NON_HUMAN_TARGET` to m1. The ADRs keep their history by design; a reader must read them in order.
