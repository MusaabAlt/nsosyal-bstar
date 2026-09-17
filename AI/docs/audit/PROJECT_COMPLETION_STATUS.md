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
| m2_deobf | protection pass, tier 1 (LEET, REPEAT, SPACED, PUNCT_SPLIT, accent, PHONETIC) | NOT_STARTED | — | to add | — |
| m2_deobf | tier 2 DEASCII (morphology-validated, ambiguity-safe), SUFFIX_ON_MASKED | NOT_STARTED | — | to add | — |
| m2_deobf | ABBREV, VOWEL_DROP, WORD_MERGE, CHAR_DROP, DIALECT | NOT_STARTED | needs a Turkish lexicon / curated maps not in the repository; declared unhandled in v1 (spec §3 allows declaring a pattern unhandled) | — | — |
| m2_deobf | EMOJI_SUB | BLOCKED_BY_DATA | curated emoji→word map for Turkish does not exist (spec §3, declared out of scope) | — | — |
| m2_deobf | normalized-channel offset interface (Q5) | IN_PROGRESS | engineering proposal ADR-008 (see §3) | — | — |
| m2_deobf | headline number (spec §8) | BLOCKED_BY_DATA | needs m3 scoring both channels + a labelled paired set; real-obfuscation slice must be collected by a human | — | — |
| m6_target | B4 regex layer (phone, TC ID checksum, IBAN mod-97, plate, address with personal cue) | NOT_STARTED | — | to add | — |
| m6_target | target resolution v1 (mention, second person, group gazetteer, non-human nouns) | NOT_STARTED | — | to add | — |
| m6_target | `siz`, institution vs members, religion vs followers, sports supporters | BLOCKED_BY_POLICY | Q28: written rules by the owner | — | — |
| m6_target | hand-labelled target slice, agreement number, confusion matrix | BLOCKED_BY_DATA | needs annotation | — | — |
| m1_lexicon | raw channel, A1 carrier, SUBSTRING_COLLISION, NON_HUMAN_TARGET, hit signals | IMPLEMENTED_NOT_VERIFIED | — | 19 unit; interfaces; e2e | baseline |
| m1_lexicon | normalized-channel spans through m2's offsets | NOT_STARTED | after ADR-008 | — | — |
| m1_lexicon | terlik vs karaliste comparison (spec §6) | NOT_STARTED | protocol first; data present locally | — | — |
| m1_lexicon | HOMONYM guard (spec §3, §7) | NOT_STARTED | documented homonym table | — | — |
| m1_lexicon | A4 sacred-concept extension | BLOCKED_BY_DATA | owner-approved root table with sources (spec §4.3) — see `docs/blockers/` | — | — |
| m3_encoder | binary `raw_score` on the frozen artifact | IMPLEMENTED_NOT_VERIFIED | — | 14 unit; interfaces; e2e | baseline |
| m3_encoder | `norm_score` on the normalized channel | NOT_STARTED | after m2 | — | — |
| m3_encoder | A head | BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT | label source undecided (RESOURCES item 5); training code + handoff to build | — | — |
| m3_encoder | B head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT | no B-labelled corpus (RESOURCES item 6) | — | — |
| m3_encoder | C head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT | C slice being labelled, no date (RESOURCES item 7) | — | — |
| m3_encoder | banned-dataset written check, truncation policy in spec | NOT_STARTED | — | — | — |
| m4_implicit | stage 1 (binary threshold) | VERIFIED at the decision layer | — | test_binary_offensive (12) | baseline |
| m4_implicit | stage 2 | BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT | pre-registered precision budget (Q23); influence tooling on GPU | — | — |
| m4_implicit | C1–C5 rows, fixture set | BLOCKED_BY_DATA | C head + labelled slice | — | — |
| m5_sarcasm | everything | BLOCKED_BY_DATA | entry gate: corpus not named/requested (Q27) | — | — |
| decision layer | fusion, guards, thread rule, family A, binary boundary | VERIFIED | placeholders remain placeholders (Q25) | 45 + 12 | baseline |
| pipeline / counter / API | mechanics | VERIFIED | — | 35 + 20 + 6 | baseline |
| eval infrastructure | Gate 1 observability | VERIFIED | — | 15 + 5 + 12 | baseline |
| full pipeline | end-to-end on real modules | IMPLEMENTED_NOT_VERIFIED | Q1, Q2, Q3 outcomes unjudged; stubs degrade every verdict | 7 e2e | baseline |

## 2. Log of work (newest first)

| date | component | what | tests | commit |
|---|---|---|---|---|
| 2026-09-17 | m0_charsafe | verified against spec §7 / §8: fixture list complete, 46 unit tests (mixed-casing test added), uncontended eval within every band, 0/33 traps; spec §3 records `_offsets` and the signals, §4 describes the five implemented passes (Q14 closed) | 46 unit + 12 interface + 7 e2e OK | see below |
| 2026-09-17 | baseline | Gate 1.5 executed: commits A–E; reference eval run recorded (`BASELINE_WORKTREE.md` §8) | 319 OK / 4 skipped | `9976eb4` |

## 3. Interface decisions proposed by engineering (owner to ratify)

| id | decision | why the repository allows an engineering answer |
|---|---|---|
| ADR-008 (proposed) | m2 publishes `signals["_offsets"]` (original index of every character of `normalized_text`, m0's convention) and `offsets_identity`; m1 reads it for the normalized channel exactly as it reads m0's for the raw channel | ADR-001 already establishes the pattern ("m0 publishes offsets for guard producers"); the contract is untouched (signals are free-form); nothing about product policy changes |

## 4. Policy questions still open (not answered here)

Q1, Q2, Q3, Q5 (the contract half is the ADR-008 proposal; the policy half — whether normalized-channel hits fire codes — is unchanged), Q6, Q12, Q16, Q20, Q23, Q25, Q28.

## 5. GPU handoffs

None yet. Index: `AI/docs/training/GPU_HANDOFF.md` (created with the first handoff).

## 6. Data blockers

None yet written. Directory: `AI/docs/blockers/`.
