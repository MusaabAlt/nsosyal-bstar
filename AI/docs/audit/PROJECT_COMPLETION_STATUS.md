# Project completion status

Maintained from the MODULE VERIFICATION BASELINE onward (2026-09-17). One row per component,
updated at every commit that changes its state. Status vocabulary:
`NOT_STARTED` · `IN_PROGRESS` · `BLOCKED_BY_POLICY` · `BLOCKED_BY_DATA` ·
`WAITING_FOR_GPU_ARTIFACT` · `IMPLEMENTED_NOT_VERIFIED` · `VERIFIED`.

A component is VERIFIED only when its specified behaviour is implemented and its relevant
verification passes on the committed tree. A stub is never anything but NOT_STARTED or a BLOCKED
state. Partial modules carry two rows where the built and the unbuilt parts have different states.

Baseline: commit `9976eb4add53e0a708a8c17db3a5697d4c70f455` (`BASELINE_WORKTREE.md` §8.1). Suite at
baseline: 319 tests, OK, 4 skipped (the declared m2 ×2, m5, m6 skips). Reference evaluation:
`eval/results/baseline/` (CURRENT_REPRODUCIBLE_RESULT, 0 trap regressions, binary fires on traps
008 / 017 / 030 / 032, flip rate 0.0, stubs m2 / m5 / m6 NOT VERIFIED).

---

## 1. Status table

| component | slice | status | blocking decision / data / artifact | tests | commit |
|---|---|---|---|---|---|
| m0_charsafe | five passes, signals, offsets; spec §3 / §4 now describe the implemented passes and the `_offsets` interface | **VERIFIED** (2026-09-17): 46 unit tests, interface tests, e2e; uncontended eval: capture 1.0 per pattern, damage 0.0 on 35 clean items, 0/33 traps, every latency band within its placeholder budget; spec §7 fixture list checked (`SIKINTI`, `IŞIK`, `İSTANBUL` in mixed casing, zero-width, Cyrillic, 35 clean items, empty / space / 5000 chars) | Q3 (whether charsafe must precede m3) and Q14 (now closed by the spec update) were the only open rows; Q3 is policy and does not block m0 | 46 unit; 12 interface; 7 e2e | see log |
| m2_deobf | protection pass, tier 1 (LEET, REPEAT, SPACED, PUNCT_SPLIT, accent as HOMOGLYPH, PHONETIC), spans, `_offsets` (ADR-008), idempotency | **VERIFIED** (2026-09-17): 32 unit tests; generated per-pattern set (protocol `m2_obfuscation_eval_protocol.md`, 195 pairs): capture 1.0 per tier-1 pattern, damage 0.0 on 49 clean items, 0/33 traps, clean-to-dirty flip rate 0.0 on the full pipeline, latency within the 10 ms placeholder | — | 32 unit; e2e | see log |
| m2_deobf | tier 2 DEASCII (zeyrek-validated, ambiguity-safe), SUFFIX_ON_MASKED (reported, text unchanged) | IMPLEMENTED_NOT_VERIFIED for DEASCII: capture 0.71 [0.46, 0.92] on 14 generated pairs, below the spec §11 80 % line — a measured negative (README.md: the misses are the no-guessing rule); SUFFIX_ON_MASKED 1.0 | zeyrek 0.1.3 (MIT) declared in `modules/m2_deobf/requirements.txt`; tier 1 runs without it | 32 unit | see log |
| m2_deobf | ABBREV, VOWEL_DROP, WORD_MERGE, CHAR_DROP, DIALECT | NOT_STARTED, declared unhandled in v1 | need a Turkish lexicon / curated maps not in the repository (spec §3 allows declaring a pattern unhandled; README.md) | — | — |
| m2_deobf | EMOJI_SUB | BLOCKED_BY_DATA | curated emoji→word map for Turkish does not exist (spec §3, declared out of scope) | — | — |
| m2_deobf | normalized-channel offset interface (Q5, carrier) | **VERIFIED** on both sides (m2 publishes, m1 consumes; interface test pins the invariants) | ADR-008 proposed; owner to ratify | interface test | see log |
| m2_deobf | headline number (spec §8), real-obfuscation slice, human spot-check | BLOCKED_BY_DATA | needs m3 scoring both channels (after the m3 `norm_score` step) + a labelled paired set outside training data; the real slice and the spot-check are human tasks (protocol §5, §6) | — | — |
| m6_target | B4 doxing: mobile / landline, national ID (both checksum digits), IBAN mod-97, plates with a province code, address with a personal cue and no public-place cue, e-mail, social-profile links; every score spanned | **VERIFIED** on its fixtures (2026-09-17): 24 unit tests; eval B4 6/6 precision 1.0, near-misses (public address, event, failed checksums) do not fire, 0/33 traps, latency within the 5 ms placeholder | operating point declared in `protocols/m6_target_guideline.md` §3 | 24 unit; e2e | see log |
| m6_target | target resolution v1: @mentions, the frozen second-person deictic set (exact tokens, Turkish casing), vocatives, second-person endings, group / non-human gazetteers with suffix awareness and vowel harmony, precedence individual > group > non_human; published as `target` and `signals.target_type` / `target_confidence` | **VERIFIED** on its fixtures: individual 10/10, group 5/5, non_human 9/9; e2e: `Sen …` resolves individual and the carrier is assigned the configured individual code (ADR-005) | no hand-labelled slice yet (spec §8) | 24 unit; e2e | see log |
| m6_target | `siz`, institution vs members (incl. the `-deki(ler)` members form), religion vs followers, sports supporters | BLOCKED_BY_POLICY — v1 behaviour DECLARED in `protocols/m6_target_guideline.md` §2 and pinned by `test_declared_pending_rules` so it is visible, not decided | Q28: written rules by the owner | 24 unit | see log |
| m6_target | hand-labelled target slice, agreement number, confusion matrix | BLOCKED_BY_DATA | needs annotation | — | — |
| m1_lexicon | raw channel, A1 carrier, SUBSTRING_COLLISION, NON_HUMAN_TARGET (now fed by the real m6), HOMONYM, hit signals, dual-register words never fire | **VERIFIED** on its fixtures and traps (2026-09-17): 23 unit tests; eval 1.0 on A1 / SUBSTRING_COLLISION / HOMONYM / NON_HUMAN_TARGET, 0/33 traps, clean bands within budget; e2e non-human case proves m6 → m1 → guard suppression (verdict left to Q2) | Q12 (adversarial latency published, not accepted), Q16, Q20 remain owner judgements | 23 unit; 13 interface; 8 e2e | see log |
| m1_lexicon | normalized-channel spans through m2's offsets (ADR-008); match spans tightened to the matched word (terlik ran over a suffix-shaped next word and produced nested hits in spaced text) | **VERIFIED** (2026-09-17): unit tests with fixed m2 offsets, interface test with real m0 → m2 → m1, e2e two-channel assertions; eval unchanged (1.0 per code, 0/33 traps) | ADR-008 owner ratification | 21 unit; interface; e2e | see log |
| m1_lexicon | terlik vs karaliste comparison (spec §6, §8) | **VERIFIED**: pre-registered protocol, result committed (`eval/results/m1_terlik_vs_karaliste.json`): recall 0.392 vs 0.386 (Δ +0.007 [−0.022, +0.037]), FPR 0.026 vs 0.067 (Δ −0.042 [−0.050, −0.034]); 311 karaliste-only, 156 terlik-only rows | — | script + protocol | see log |
| m1_lexicon | HOMONYM guard (spec §3, §7) | **VERIFIED** for the declared table (`am` as a time abbreviation); table documented in README with its context rule | new entries need a source row | 23 unit | see log |
| m1_lexicon | A4 sacred-concept extension | BLOCKED_BY_DATA | owner-approved root table with sources (spec §4.3) — see `docs/blockers/` | — | — |
| m3_encoder | binary `raw_score` on `ctx.text` and `norm_score` on the normalized channel (frozen artifact); truncation notes + `truncated_differently`; sha256 verification; no network | **VERIFIED** on what exists (2026-09-17): 18 unit tests, interface tests (path / key / artifact id agreement, both channels), e2e consistency `fired == score >= t` on every case; publishing `norm_score` follows spec §4 and supersedes the 2026-09-15 note (no yaml row reads it: the decision layer stays raw-only) | Q3 (which text the raw channel scores) is the owner's | 18 unit; 13 interface; 8 e2e | see log |
| m3_encoder | multi-head artifact loader (`NSOSYAL_M3_ARTIFACT`): content from TRAINED heads only, per channel, sha256-verified, fail-closed on tamper | **VERIFIED** with a CPU smoke artifact (random-initialised encoder from the local config): `training/tests/test_training_m3.py` | — | 4 training tests | see log |
| m3_encoder | A head | BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT — training code complete (`training/m3_encoder`), handoff `docs/training/m3_encoder.md` | label source undecided (RESOURCES item 5, `docs/blockers/m3_head_labels.md`) | smoke test | see log |
| m3_encoder | B head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT — code and handoff complete | no B-labelled corpus (RESOURCES item 6, `docs/blockers/m3_head_labels.md`) | smoke test | see log |
| m3_encoder | C head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT — code and handoff complete | C slice being labelled, no date (RESOURCES item 7) | smoke test | see log |
| m3_encoder | banned-dataset written check (`DATASETS.md`), truncation policy declared in spec §5, corpus count corrected (Q17) | **VERIFIED** (documents exist, dated) | — | — | see log |
| m4_implicit | stage 1 (binary threshold) | VERIFIED at the decision layer | — | test_binary_offensive (12) | baseline |
| m4_implicit | stage 2 | BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT — handoff `docs/training/m4_stage2.md` written | pre-registered precision budget (Q23); labelled C slice; influence tooling on GPU | — | see log |
| m4_implicit | C1–C5 rows, fixture set | BLOCKED_BY_DATA | C head + labelled slice | — | — |
| m5_sarcasm | everything | BLOCKED_BY_DATA — training code (`training/m5_sarcasm`) and handoff `docs/training/m5_sarcasm.md` written; module stays a documented stub | entry gate: corpus not named / requested (Q27, `docs/blockers/m5_sarcasm_corpus_gate.md`) | — | see log |
| decision layer | fusion, guards, thread rule, family A, binary boundary | VERIFIED | placeholders remain placeholders (Q25) | 45 + 12 | baseline |
| pipeline / counter / API | mechanics | VERIFIED | — | 35 + 20 + 6 | baseline |
| eval infrastructure | Gate 1 observability | VERIFIED | — | 15 + 5 + 12 | baseline |
| full pipeline | end-to-end on real modules | IMPLEMENTED_NOT_VERIFIED | Q1, Q2, Q3 outcomes unjudged; stubs degrade every verdict | 7 e2e | baseline |

## 2. Log of work (newest first)

| date | component | what | tests | commit |
|---|---|---|---|---|
| 2026-09-17 | m3_encoder | both channels scored (norm_score, spec §4), truncated_differently signal, multi-head artifact loader with sha256 verification, spec §5 truncation policy and corpus count, DATASETS.md; training packages for m3 (multi-head) and m5 (sequential transfer) with CPU smoke test; Colab handoffs for m3 / m4 stage 2 / m5; blocker documents for A4, m3 labels, m5 corpus; contract example regenerated (fixtures only) | 18 unit + 4 training + 13 interface + 8 e2e; full suite 370 OK / 1 skipped | see below |
| 2026-09-17 | m1_lexicon | HOMONYM guard with a declared context table; dual-register fixtures; terlik-vs-karaliste comparison run under its protocol and committed; README records every list, the span rule and the comparison; e2e case for the m6 → m1 NON_HUMAN_TARGET path (Q2 verdict recorded, not judged) | 23 unit; eval 1.0 per code, 0/33 traps; 78 integration tests OK | see below |
| 2026-09-17 | m6_target | implemented from the stub: target resolution v1 (mentions, frozen deictic set, vocatives, endings, gazetteers `gazetteers/*.txt` with suffix awareness + vowel harmony, `-ki` members form excluded), B4 doxing with validated patterns; guideline with the three ambiguities declared PENDING; fixtures per spec §9; MANIFEST rows for the gazetteers; contract example regenerated (fixtures only) | 24 unit; full suite 359 OK / 1 skipped; eval 1.0 on every code, 0/33 traps | see below |
| 2026-09-17 | m1_lexicon | ADR-008 consumer side: normalized-channel spans through m2's `_offsets` (same-length fallback kept); span tightening: a terlik match containing a space is cut to the shortest token-boundary prefix terlik still matches, nested hits dropped (pre-existing span defect against spec §8, found by the interface test) | 21 unit + 13 interface + 7 e2e OK; eval 1.0 per code, 0/33 traps | see below |
| 2026-09-17 | m2_deobf | implemented from the stub: protection pass, tier 1 (LEET, REPEAT, SPACED, PUNCT_SPLIT, accent, PHONETIC), tier 2 (DEASCII via zeyrek validation with the declared ambiguities never resolved, SUFFIX_ON_MASKED reported), spans + `_offsets` (ADR-008), internal per-repair signals (decision #21); generated per-pattern fixtures under a pre-registered protocol; contract example regenerated (fixtures only) | 32 unit; full suite 341 OK / 2 skipped; capture 1.0 tier 1, DEASCII 0.71, damage 0.0, flip 0.0, 0/33 traps | see below |
| 2026-09-17 | m0_charsafe | verified against spec §7 / §8: fixture list complete, 46 unit tests (mixed-casing test added), uncontended eval within every band, 0/33 traps; spec §3 records `_offsets` and the signals, §4 describes the five implemented passes (Q14 closed) | 46 unit + 12 interface + 7 e2e OK | see below |
| 2026-09-17 | baseline | Gate 1.5 executed: commits A–E; reference eval run recorded (`BASELINE_WORKTREE.md` §8) | 319 OK / 4 skipped | `9976eb4` |

## 3. Interface decisions proposed by engineering (owner to ratify)

| id | decision | why the repository allows an engineering answer |
|---|---|---|
| ADR-008 (proposed) | m2 publishes `signals["_offsets"]` (original index of every character of `normalized_text`, m0's convention) and `offsets_identity`; m1 reads it for the normalized channel exactly as it reads m0's for the raw channel | ADR-001 already establishes the pattern ("m0 publishes offsets for guard producers"); the contract is untouched (signals are free-form); nothing about product policy changes |

## 4. Policy questions still open (not answered here)

Q1, Q2, Q3, Q5 (the contract half is the ADR-008 proposal; the policy half — whether normalized-channel hits fire codes — is unchanged), Q6, Q12, Q16, Q20, Q23, Q25, Q28.

## 5. GPU handoffs

Index: `AI/docs/training/GPU_HANDOFF.md` — m3 multi-head (`m3_encoder.md`), m4 stage 2 (`m4_stage2.md`), m5 sarcasm (`m5_sarcasm.md`); all blocked on data or policy, code complete for m3 and m5 (`AI/training/`).

## 6. Data blockers

`AI/docs/blockers/m1_a4_sacred_concepts.md`, `m3_head_labels.md`, `m5_sarcasm_corpus_gate.md`.
