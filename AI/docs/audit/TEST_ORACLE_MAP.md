# Test-oracle map — where expected behaviour is written

Verification Gate 0, 2026-09-17. For every module and component: the repository source that states
what the EXPECTED behaviour is, so that a test written against it tests the intent and not the
current code. Only repository evidence is used (specs, ADRs, `thresholds.yaml`, `AI/CLAUDE.md`,
`AI/docs/HANDOVER.md`, protocols, contracts, team docs). Where two authoritative sources conflict,
the row is marked **TEST ORACLE UNRESOLVED** and points at the triage item; no source is chosen.

Legend for the "oracle" column:

- `spec §n` — `AI/modules/<m>/spec.md`
- `ADR-n` — `AI/protocols/ADR-00n-*.md`
- `yaml` — `AI/decision/thresholds.yaml`
- `HANDOVER #n` — decision row in `AI/docs/HANDOVER.md`
- `CLAUDE rule n` — `AI/CLAUDE.md` non-negotiable rule
- `protocol` — a file under `AI/protocols/`
- `contract` — `AI/contracts/{codes,schema,module_api}.py`
- **CODE-ONLY** — the only statement of the behaviour is the implementation or its unit test; there
  is no independent oracle, so a test can pin current behaviour but cannot judge it.
- **NOT BUILT** — specified, no implementation; the oracle exists, the subject does not.

Precedence rule used to *flag* conflicts (not to resolve them): HANDOVER #2 says the frozen
contract wins over the specs for field names; HANDOVER #1 says the specs are the single source of
truth for design; `yaml` is authoritative for every number (HANDOVER #34, CLAUDE rule 4). Where a
spec, an ADR and the yaml disagree on a *number*, the yaml is the oracle and the spec is drift.
Where they disagree on *behaviour*, the row is unresolved.

---

## m0_charsafe

| behaviour | oracle | status |
|---|---|---|
| Reads `ctx.text`; writes `charsafe_text`, one `FormPattern` per transformation with evidence, `signals.charsafe_changed` | spec §3; contract `FormPattern` | resolved |
| May emit `ZERO_WIDTH`, `HOMOGLYPH`, `DOTLESS_I` only | spec §2, §3; contract `FormCode` | resolved |
| `SIKINTI` never yields a profane root; every uppercase `I` → `ı`, `İ` → `i` | spec §8; HANDOVER #26; ADR-002 context | resolved |
| Zero modification on clean ASCII Turkish; every change has evidence | spec §8 | resolved |
| Styled Latin (fullwidth, mathematical, circled, squared, parenthesized, negative, super/subscript, small capitals, non-flag regional indicators) mapped as `HOMOGLYPH`; superscript digits never mapped | spec §2 (Catches, HANDOVER #55); HANDOVER #39 | resolved |
| Flag-pair gap: a run made only of valid region pairs is left as flags | spec §2 (known limitation); HANDOVER #45 | resolved (accepted) |
| Small capital `ɪ` → `I` → `ı` | HANDOVER #16g | resolved |
| Layout controls (`\t\n\r`) kept; emoji ZWJ sequences kept and not reported; combining marks: canonical composition kept, marks stuffed on Latin stripped, other scripts kept | **CODE-ONLY** (`module.py`, `test_unit.py`); spec §4 lists three steps that do not mention these | **TEST ORACLE UNRESOLVED** — Q14 / U-M0-1: spec §4 vs implemented passes; a test can pin the code, not judge it |
| `_offsets` internal signal, `offsets_identity`, counts | ADR-001 Consequences (m0 publishes offsets for guard producers); HANDOVER #21 (`_` keys internal) | resolved for existence; the key name and format are **CODE-ONLY** (no spec names `_offsets`, Q7) |
| Latency per length: 64→0.25, 280→1, 1000→4, 5000→25 ms, clean input only | yaml `budgets.module_latency_p95_ms.m0_charsafe`; spec §8 (HANDOVER #34); HANDOVER #44 | resolved (placeholders, but authoritative) |
| Whether charsafe must precede *every* model | spec §1 ("before any model sees it") vs m3 owner decision (m3 scores `ctx.text`) | **TEST ORACLE UNRESOLVED** — Q3 |

## m2_deobf

| behaviour | oracle | status |
|---|---|---|
| Reads `charsafe_text` (fallback `text`); writes `normalized_text` + one `FormPattern` per repair; never content; never replaces raw | spec §6; CLAUDE rule 3 | resolved, **NOT BUILT** |
| Patterns in scope (`LEET`, `REPEAT`, `SPACED`, `PUNCT_SPLIT`, `CHAR_DROP`, `WORD_MERGE`, `ABBREV`, `DEASCII`, `VOWEL_DROP`, `SUFFIX_ON_MASKED`, `DIALECT`, `PHONETIC`); `EMOJI_SUB` out of scope v1 | spec §4; contract `FormCode` | resolved, NOT BUILT |
| Two tiers; tier 2 behind the over-correction budget; protection pass first | spec §5, §8 | resolved, NOT BUILT |
| `sık` / `sik` ambiguity never rule-resolved | spec §7 | resolved, NOT BUILT |
| Idempotent `f(f(x)) == f(x)` | spec §9 / §11 | resolved, NOT BUILT |
| `text[start:end] == evidence` for every pattern | spec §9 vs contract `FormPattern.evidence` (free text) and m0's descriptive evidence | **TEST ORACLE UNRESOLVED** — Q14 / U-M2-1 |
| Offset map from `normalized_text` back to the original for m1 spans and m3 truncation | no source names a carrier; m1 spec §3, m3 spec §4 need it | **TEST ORACLE UNRESOLVED** — Q5 |
| `clean_to_dirty_flip_rate ≤ 0.01` over the trap list, measured with vs without the channel | yaml `budgets`; spec §8; `pipeline_budget_report` | resolved for the definition (content flips); whether binary flips count is **UNRESOLVED** (Q18 extension) |
| Headline number (recall drop A→B under pattern P; channel recovers C points) | spec §8; needs m3 on both channels + `norm_score` threshold | **TEST ORACLE UNRESOLVED** — U-M2-3 (where the measurement lives) |
| Leakage rule: evaluation generator ≠ training augmentation generator | spec §10 | resolved, NOT BUILT |
| Latency 10 ms p95 | yaml | resolved (placeholder) |

## m6_target

| behaviour | oracle | status |
|---|---|---|
| Reads `ctx.text` (raw); writes `target: TargetResult(type, confidence, evidence, span?)`, `signals.target_type` / `target_confidence`, content `B4` with span | spec §6; ADR-005; contract `TargetResult`, `TargetType` | resolved, **NOT BUILT** |
| Provides no guards (moved to m1) | ADR-005; HANDOVER #57; spec §6 | resolved (ADR-001 text still says m6 produces guards — historical, superseded by ADR-005) |
| Never resolves a non-human target as individual / group | spec §2, §7 | resolved, NOT BUILT |
| Never identifies, verifies or enriches the person behind an identifier | spec §7 | resolved, NOT BUILT |
| Regex layer (phone, national ID checksum, IBAN `TR…`, plates, addresses) + gazetteer + morphology (`zeyrek` / Zemberek); no transformer NER in v1 | spec §5 (Named tools); ADR-007; HANDOVER #60 | resolved, NOT BUILT |
| `B4` precision before recall | spec §5, §10 | resolved, NOT BUILT |
| `siz`, institution vs members, religion vs followers, sports-club supporters | spec §4 requires written rules; none written | **TEST ORACLE UNRESOLVED** — Q28 (no rule to test against) |
| Which of `result.target` and `signals.target_*` is authoritative when they disagree; whether `family_a.target_min_confidence` and `guards.NON_HUMAN_TARGET.threshold` are one number | no source | **TEST ORACLE UNRESOLVED** — Q6 |
| `signals.target_type` is a `TargetType` value (enum vs string through `deep_freeze`) | spec §6; contract | resolved in text, unpinned (U-M6-4) |
| Latency 5 ms p95 | yaml | resolved (placeholder) |

## m1_lexicon

| behaviour | oracle | status |
|---|---|---|
| Input channel: `ctx.text` per spec §3; `charsafe_text` (+ m0 `_offsets`) per protocol §4 and code | spec §3 vs `protocols/m1_lexicon_dev_labels_protocol.md` §4 | **TEST ORACLE UNRESOLVED** — Q7 (documentation drift, but the input oracle is what a test must assert) |
| Runs on `normalized_text` when present; reports both channels | spec §3; ADR-001 | resolved (behaviour); spans on the normalized channel **UNRESOLVED** (Q5) |
| Family-A profanity emitted on the `A1` carrier only; never A2/A3 | ADR-005; HANDOVER #56; spec §3 | resolved |
| `A4` sacred-concept extension with a committed source table | spec §3, §4.3, §8 | resolved, **NOT BUILT** |
| Guards `SUBSTRING_COLLISION`, `HOMONYM`, `NON_HUMAN_TARGET`, each with the exact span and `source = "m1_lexicon"` | spec §3; ADR-001 + amendment (spans required, `emits_spans = True`); HANDOVER #4, #16e | resolved; `HOMONYM` NOT BUILT |
| `NON_HUMAN_TARGET` raised on own family-A matches from m6's `target_type == non_human`, score = m6 confidence, span = the match | ADR-005; HANDOVER #57; spec §3 | resolved |
| Collision guard fires whenever the boundary test rejects a root | spec §8 | resolved for *whether*; the second pass firing on any token containing any folded root (49 % base rate) is **UNRESOLVED** as design — Q20 |
| Cross-channel deduplication of collision guards by span (a collision on one channel vetoes a hit on the other) | **CODE-ONLY** (`module.py:137-141`); ADR-001 silent on channel | **TEST ORACLE UNRESOLVED** — Q8 |
| Signals `lexicon_hit`, `lexicon_hit_raw`, `lexicon_hit_norm` present and boolean on every input | spec §3, §8; protocol §3 | resolved |
| `lexicon_hit_*` may be true with no emitted score (flag-only) | protocol §3 check 6 | resolved (tolerated) |
| Morpheme-boundary matching, free substring search banned; terlik balanced; `karaliste` never a reference | spec §4.1, §4.3, §5; HANDOVER m1 bullet | resolved |
| Two-tier hard/soft structure "in place" | spec §4.2, §10 vs terlik `suffixable` + `CLEAN_PREFIXES` | **TEST ORACLE UNRESOLVED** — Q16 (a judgement the owner has not recorded) |
| Dual-register words (`moruk`, `lan`, `oğlum`) never auto-fire | spec §7 | resolved oracle; no fixture (untested) |
| Score value of a hit | no source states a value; code emits 1.0 | **CODE-ONLY** |
| Zero positives on the trap list | spec §8; `eval/traps/traps.jsonl` (33 in working tree, 23 at HEAD) | resolved; the trap *set* is baseline-dependent (G0-10) |
| Latency: spec §8 "p95 under 5 ms" vs yaml per-length bands 3/10/30/140 ms (ADR-003 amendment) vs measured adversarial ≈ 301 ms | yaml is authoritative for numbers (CLAUDE rule 4, HANDOVER #34 analogue); the acceptance of the adversarial overrun is policy | **TEST ORACLE UNRESOLVED** — Q12 (criterion for acceptance) |
| Evaluation slice is `eval/frozen/study_slice_dev.json` (karaliste), never recomputed from m1; derived labels are not a slice | spec §1 (+ uncommitted §1 table); protocol §1, §6; frozen file `_README` | resolved |
| terlik-vs-karaliste comparison committed; recall / FPR with CIs on both channels | spec §6, §8 | resolved oracle, **NOT BUILT** deliverable (Q19) |
| Stage-1b condition signal name (`lexicon_hit` vs `lexicon_hit_raw`) | spec §8 / m4 spec §4 / yaml comment vs protocol §3 + script | **TEST ORACLE UNRESOLVED** — Q13 (dormant) |

## m3_encoder

| behaviour | oracle | status |
|---|---|---|
| One BERTurk encoder, three heads (A on the `A1` carrier, B multi-label B1/B2/B3/B5, C1–C5), both channels, `source = m3_encoder@raw|@normalized`, signals `raw_score`, `norm_score`, `artifact` | spec §4; ADR-005; ADR-006 | resolved oracle; heads, `norm_score`, content **NOT BUILT** |
| D1 is not an m3 head; no embeddings published | ADR-003; spec §4, §6; HANDOVER #7, #31 | resolved |
| Publishes exactly `{raw_score, artifact}` and no content in the current partial state | `module.py` docstring; `AI/README.md`; team docs 2026-09-15 | **CODE-ONLY** for the partial state (no spec status line, Q10) |
| Scores `ctx.text`, not `charsafe_text` or `normalized_text` | owner decision recorded in `module.py` docstring and `test_scores_original_text_not_charsafe_or_normalized` vs m0 spec §1 and m3 spec §4 (both channels) | **TEST ORACLE UNRESOLVED** — Q3 |
| Truncation: 128 tokens, first kept, note emitted | `module.py` (`MAX_LEN`), `protocols/threshold_derivation_binary_offensive_stage1.md` vs spec §9 (says the policy must be declared in §5; cites 512) | **TEST ORACLE UNRESOLVED** for the *documented* policy — Q11; the implemented policy is pinned |
| Artifact: sha256-verified checkpoint `m3-berturk-pytorch-fp32-epoch1`; MANIFEST row; no network at load; heavy deps in module `requirements.txt` | spec §8; `artifacts/MANIFEST.md`; CLAUDE rule 6; `test_no_network_at_load` | resolved |
| `raw_score` equals the study's `dev_predictions.csv` probability (0 flips, max Δp 2.25e-06) | derivation protocol (artifact-equivalence check) | resolved, offline only (no regression test) |
| Per-code metrics with CIs on both channels; frozen-baseline comparison; decision-flip table | spec §7, §10 | resolved oracle, NOT BUILT |
| Banned datasets, leakage check, hydration loss | spec §5, §10 | resolved oracle, NOT BUILT |
| A-head gold label source | RESOURCES.md item 5; protocol §1 proposes terlik labels | **TEST ORACLE UNRESOLVED** — U-M3-7 |
| Latency 80 ms p95 | yaml | resolved (placeholder) |

## m4_implicit

| behaviour | oracle | status |
|---|---|---|
| Emits no content; C1–C5 are m3's; m4 owns the C1–C5 and `binary_offensive` rows and the slice repair | ADR-006 + amendment; HANDOVER #58, #66; spec §5 | resolved |
| Non-stub that returns one note; does not degrade the result | ADR-006 amendment; `test_not_a_stub_and_emits_only_its_note` | resolved |
| Reads only `signals.m3_encoder.{raw_score, norm_score, artifact}` | spec §5 | resolved oracle; code reads nothing (consistent while nothing is needed) |
| Stage 1: one global cost-derived threshold 0.320188, raw channel, `>=` in fusion, tie row 29308 recorded | yaml `binary_offensive`; `protocols/threshold_derivation_binary_offensive_stage1.md`; ADR-006; spec §4 | resolved — **the only derived oracle in the system** |
| Stage 1b: adopted only after measurement at equal coverage; result KEEP stage 1 | `protocols/m4_stage1b_protocol.md`; `eval/results/m4_stage1b.json` (tracked) | resolved (rejected) |
| Stage 2: pre-registered precision budget before the first number | spec §10 | resolved oracle; budget **NOT WRITTEN** (Q23) |
| `binary_offensive.action = review` | yaml (PLACEHOLDER policy, owner: stays review); HANDOVER #13 | resolved as policy; relative severity vs `A1 = nudge` **UNRESOLVED** (Q4) |
| Binary not suppressible by guards | yaml comment | resolved as written; precedence vs ADR-005 design **UNRESOLVED** (Q2) |
| Fixture slice by `context.signals.m1_lexicon.lexicon_hit`; unit test that it equals m1's real output | spec §9 vs CLAUDE rule 2 | **TEST ORACLE UNRESOLVED** — Q15 |
| Baseline numbers (lexicon-free recall 0.5628 dev; stage 1 EVAL 0.5180 → 0.6367 at precision 0.7512 → 0.6509) | spec §2; derivation protocol; `diagnosis/results/12_threshold_policy/metrics.json` | resolved |
| Latency 20 ms p95 | yaml | resolved (placeholder) |

## m5_sarcasm

| behaviour | oracle | status |
|---|---|---|
| Entry gate: name and request the Turkish sarcasm corpus first; three outcomes | spec §2 | resolved oracle; **gate not executed** (Q27) |
| Reads `ctx.text`; writes content `D1` only; own model, artifact, MANIFEST row, thresholds row, `requirements.txt`; small or distilled; never reads m3 embeddings | spec §6, §7; ADR-003; HANDOVER #7, #10, #31, #32 | resolved, **NOT BUILT** |
| D1 only with polarity inversion; explicit content wins over D1 | spec §5 | resolved, NOT BUILT |
| Precision on the benign-sarcasm control set gates acceptance | spec §8, §12 | resolved, NOT BUILT |
| Fixtures carry `inversion_span` (unit tests assert it; harness ignores it) | spec §11; HANDOVER #61 | resolved |
| Latency 20 ms p95 | yaml | resolved (placeholder for a non-existent model, U-M5-2) |

## Decision layer (`decision/fusion.py`, `decision/actions.py`, `thresholds.yaml`)

| behaviour | oracle | status |
|---|---|---|
| Modules never threshold or decide; only the decision layer sets `threshold / fired / active / suppressed`; reset at the start of every decision | CLAUDE rule 4; HANDOVER #40; `contracts/schema.py` docstring | resolved |
| Family A assigned from the target before thresholds: none→A1, individual→A2, group→A3, non_human→A1; `target_min_confidence` gate | ADR-005 + amendment; yaml `family_a`; HANDOVER #56, #67 | resolved (values placeholder) |
| Per-code thresholds; `threshold_when` with scalar fallback and recorded branch | yaml; HANDOVER #12 | resolved |
| Guards suppress only their own module's scores, on overlapping spans when both carry one; no-span fallback only for `emits_spans = False`; `guards_order` | ADR-001 + amendment; yaml `guards`, `guards_order`; HANDOVER #3, #4, #17 | resolved |
| Fusion `max` over channels, fired-first; `form.active` by `min_confidence` | yaml `fusion`, `form` | resolved |
| Verdict = most severe of fired actions, binary, thread; `clean` under degradation → `review`; more severe stands with "ancak değerlendirme eksik" | HANDOVER #15, #16a; `actions.py` | resolved as written; whether a *target-dependent* `nudge` counts as "more severe" **UNRESOLVED** (Q1) |
| Explanations in Turkish, one sentence, named drivers | HANDOVER #43; `actions.py` | resolved |
| `post_offensive` = a content code fired after guards or binary fired; form and degradation never count | ADR-004 amendment; HANDOVER #42, #52 | resolved |
| Fast path disabled until margin derived; `requires = [m0, m2, m1, m6]` | yaml `fast_path`; HANDOVER #18 | resolved |
| Every category / guard threshold and action except the binary threshold | yaml (all PLACEHOLDER) | resolved as *current values*; **no derived oracle exists** (Q25) — tests must pin their own numbers, as they do |
| `binary_offensive` boundary: `score >= 0.320188` fires (study used `>`; tie row documented) | yaml comment; derivation protocol | resolved |
| Verdict `None` on decision-layer failure | HANDOVER #14 | resolved |

## Pipeline (`pipeline/run.py`, `modules/registry.py`, `contracts/module_api.py`)

| behaviour | oracle | status |
|---|---|---|
| Order m0 → m2 → m6 → m1 → m3 → m4 → m5; m6 before m1 | `registry.py` (the single owner of order, CLAUDE); ADR-005; `test_m6_runs_before_m1` | resolved |
| Each module gets a fresh frozen `Context` with deep-frozen earlier signals; text never mutated; `charsafe_text` / `normalized_text` propagated only if declared | CLAUDE rules 2, 3, 5; contract `Context`; HANDOVER #8 | resolved |
| Output validation: types, enums, finite score in [0, 1], span inside text, `source` naming the module, span required when `emits_spans` true or undeclared; drop + note + degrade `invalid_output` | ADR-001 amendment; HANDOVER #4, #16b–e | resolved |
| Stub / failed / unavailable / invalid → `signals.pipeline.degraded`, "DEGRADED" note first, clean unreachable | HANDOVER #15, #16 | resolved |
| Construction or load failure → `UnavailableModule`, pipeline continues | CLAUDE (entry points paragraph); HANDOVER #8 | resolved |
| Bounded response: no channel texts, `_` keys stripped; deterministic contract example with 0.0 latency sentinels and real `artifact_hash` | HANDOVER #21, #46, #65; ADR-003 amendment | resolved |
| `artifact_hash` covers the in-memory config and module versions | `run.py:65-74`; HANDOVER #46, #47 | resolved |
| Which text each downstream module must consume (m1: charsafe; m3: raw) | see m1 Q7 and m3 Q3 rows | **TEST ORACLE UNRESOLVED** at the integration level (Q3) |
| Two-route target publication (result field vs signals) | see m6 Q6 row | **TEST ORACLE UNRESOLVED** |
| API: `POST /analyze`, 400 / 413 / 500 JSON, no thread support | `api/main.py` docstring; HANDOVER #38 | resolved; thread side waits for `02_BACKEND_SPEC.md` (Q30) |

## Thread counter (`pipeline/thread_counter.py`; Axis 4)

| behaviour | oracle | status |
|---|---|---|
| Time-windowed, not post-count bounded; `window_posts` removed | HANDOVER #19; ADR-004 | resolved |
| Server receive time stamps events; caller-supplied timestamp refused | ADR-004; HANDOVER #36 | resolved |
| Only offensive, non-self-directed posts count; keyed by `(sender_id, target_id)`; in memory, resets on restart (demo scope) | ADR-004 amendment; HANDOVER #37, #41, #52 | resolved |
| Thread rule fires only when THIS post is offensive; `repeat_count` still reported on a clean post | HANDOVER #53; `fusion.apply_thread` | resolved |
| `repeat_count` counts events in `(t − window, t]` including this post; `min_repeats` compared only in fusion | ADR-004; yaml `thread` | resolved |
| `window_seconds = 600`, `min_repeats = 3`, action `escalate` | yaml (PLACEHOLDER) | resolved as current values; not derived (HANDOVER §5) |
| Explanation "Aynı gönderenin aynı hedefe yönelik N saldırgan mesajı …" | HANDOVER #43 | resolved |
| A binary-only offensive post counts as a repeat | follows from ADR-004 amendment (#52: "or binary offensive fired") | resolved oracle; no test (G0-7) |

---

## Unresolved oracles, collected

| # | component | conflict | triage |
|---|---|---|---|
| 1 | m0 | spec §4 three steps vs five implemented passes | Q14 |
| 2 | m0 / m3 / pipeline | "charsafe before any model" vs "m3 scores raw text" | Q3 |
| 3 | m2 | `text[start:end] == evidence` vs free-text evidence in the contract and m0 | Q14 |
| 4 | m2 / m1 / m3 | no carrier for the normalized-channel offset map | Q5 |
| 5 | m2 | where the two-channel headline measurement lives | U-M2-3 |
| 6 | m6 | ambiguity rules not written | Q28 |
| 7 | m6 / m1 / decision | two target routes, two thresholds | Q6 |
| 8 | m1 | input is `ctx.text` (spec) or charsafe (protocol, code) | Q7 |
| 9 | m1 | cross-channel collision veto | Q8 |
| 10 | m1 | two-tier structure satisfied or not | Q16 |
| 11 | m1 | collision base rate as a precision measure | Q20 |
| 12 | m1 | latency criterion and adversarial acceptance | Q12 |
| 13 | m1 / m4 | stage-1b condition signal name | Q13 |
| 14 | m3 | truncation policy location and the 512 figure | Q11 |
| 15 | m3 | A-head label source | U-M3-7 |
| 16 | m3 | no status statement for the partial state | Q10 |
| 17 | m4 | fixture-slice test vs rule 2 | Q15 |
| 18 | decision | degraded `nudge` from a missing target module | Q1 |
| 19 | decision | binary not suppressible vs ADR-005 clean case | Q2 |
| 20 | decision | `A1 = nudge` vs `binary = review` ordering | Q4 |

Every other row has one oracle. Rows marked NOT BUILT have an oracle and no subject; rows marked
CODE-ONLY have a subject and no oracle beyond the code — a test on them is a change detector, not
a correctness check, and should be labelled as such when written.
