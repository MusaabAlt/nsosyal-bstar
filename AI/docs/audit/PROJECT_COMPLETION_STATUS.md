# Project completion status

Maintained from the MODULE VERIFICATION BASELINE onward (2026-09-17). One row per component,
updated at every commit that changes its state. Status vocabulary:
`NOT_STARTED` · `IN_PROGRESS` · `BLOCKED_BY_POLICY` · `BLOCKED_BY_DATA` ·
`WAITING_FOR_GPU_ARTIFACT` · `IMPLEMENTED_NOT_VERIFIED` · `VERIFIED`.

A component is VERIFIED only when its specified behaviour is implemented and its relevant
verification passes on the committed tree. A stub is never anything but NOT_STARTED or a BLOCKED
state. Partial modules carry two rows where the built and the unbuilt parts have different states.

Current reference run (2026-09-18, commit `d7925decf7e8415851e9afc7173324038fdd145b`, `eval/results/post_m2_0_1_1/`,
CURRENT_REPRODUCIBLE_RESULT, `git_dirty` false, 50 latency repeats, 1000 bootstrap resamples, module versions
m0 0.2.0 / m2 **0.1.1** / m6 0.1.0 / m1 0.1.0 / m3 0.2.0 / m4 0.1.0 / m5 0.0.0): compared field by field with the
previous reference (`f6b48ed`, `post_m6/`), **every behavioural quantity is identical** — 0 trap regressions in every
module, no changed trap observation (verdict, content, guards, form, binary state) in any module or in the pipeline,
per-code metrics unchanged for m0 / m1 / m2 / m3 / m4 / m6, m2's representation metrics and `expect` (220 items,
exact match 0.982) unchanged, clean-to-dirty flip rate 0.0, the binary score still fires on traps 008 / 017 / 030 /
032 (Q2 / Q18), the only degraded module is `m5_sarcasm`. The m2 0.1.1 determinism fix changed no measured output.
Only latencies moved (machine noise, no code path changed for the fixtures): pipeline p50 108 / p95 195 ms over
18,150 runs (was 96 / 170; placeholder budget 250); m3's single clean fixture item p95 108.5 ms in this run versus
54 ms before, over its 80 ms placeholder — re-timed alone immediately afterwards at p95 63.7 ms (within), so it is
recorded as a transient, not a regression; m0's adversarial p95 15.8 ms (was 12.7; adversarial is reported, not
budgeted). Full suite: 394 tests OK, 1 skipped (m5); `pipeline.contract_example --check` exit 0.

Previous reference run (2026-09-17, commit `f6b48ed6a6a64ea39174eaee28efb973fb56b7f0`, `eval/results/post_m6/`,
50 repeats): 0 trap regressions; flip rate 0.0; pipeline p95 170 ms; binary fires on traps 008 / 017 / 030 / 032;
only `m5_sarcasm` degraded. Full suite then: 370 tests OK, 1 skipped.

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
| m2_deobf | tier 2 DEASCII (zeyrek-validated, ambiguity-safe), SUFFIX_ON_MASKED (reported, text unchanged) | IMPLEMENTED_NOT_VERIFIED for DEASCII: capture 0.71 [0.46, 0.92] on 14 generated pairs, below the spec §11 80 % line — a measured negative (README.md: the misses are the no-guessing rule); SUFFIX_ON_MASKED 1.0. **0.1.1 (2026-09-18):** the tier-2 latency guard was history-dependent (a post's repairs depended on the posts processed before it, through the cross-post parse cache); found by the train-split label generator's determinism check, fixed (guard charged per distinct word of the post), pinned by a cold-vs-warm test; contract example `artifact_hash` regenerated | zeyrek 0.1.3 (MIT) declared in `modules/m2_deobf/requirements.txt`; tier 1 runs without it | 33 unit | see log |
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
| m1_lexicon | terlik vs karaliste comparison (spec §6, §8) | **VERIFIED**: pre-registered protocol, result committed (`eval/results/m1_terlik_vs_karaliste.json`), re-run 2026-09-18 on the implemented m0/m2/m6/m1 with identical headline numbers: recall 0.392 vs 0.386 (Δ +0.007 [−0.022, +0.037]), FPR 0.026 vs 0.067 (Δ −0.042 [−0.050, −0.034]); 311 karaliste-only, 156 terlik-only rows; added block `terlik_any_channel` (amendment): the normalized channel adds 0 hits on dev (4 raw-only rows) | — | script + protocol | see log |
| m1_lexicon | derived label files, dev + TRAIN (`eval/derived/m1_lexicon_{dev,train}_seed42.json`, generator `eval/m1_lexicon_labels.py` 2.0.0) | **VERIFIED** (2026-09-18): both generated after their protocols from a clean tree, `--check` current at HEAD, disjoint halves of the frozen split, no test-set row possible (paths refused, ids ⊂ corpus), deterministic (two passes byte-identical), provenance (git HEAD, dirty state, versions, digests). dev: 459 hits / 455 both / 4 raw-only / 0 normalized-only, `a_label` 459; train: 2,578 hits / 2,558 both / 19 raw-only / 1 normalized-only, `a_label` 2,578; `norm_hit_unmapped` 0 in both | — | 11 unit (synthetic corpus, injected m2) + committed-file currency test | see log |
| m1_lexicon | HOMONYM guard (spec §3, §7) | **VERIFIED** for the declared table (`am` as a time abbreviation); table documented in README with its context rule | new entries need a source row | 23 unit | see log |
| m1_lexicon | A4 sacred-concept extension | BLOCKED_BY_DATA | owner-approved root table with sources (spec §4.3) — see `docs/blockers/` | — | — |
| m3_encoder | binary `raw_score` on `ctx.text` and `norm_score` on the normalized channel (frozen artifact); truncation notes + `truncated_differently`; sha256 verification; no network | **VERIFIED** on what exists (2026-09-17): 18 unit tests, interface tests (path / key / artifact id agreement, both channels), e2e consistency `fired == score >= t` on every case; publishing `norm_score` follows spec §4 and supersedes the 2026-09-15 note (no yaml row reads it: the decision layer stays raw-only) | Q3 (which text the raw channel scores) is the owner's | 18 unit; 13 interface; 8 e2e | see log |
| m3_encoder | multi-head artifact loader (`NSOSYAL_M3_ARTIFACT`): content from TRAINED heads only, per channel, sha256-verified, fail-closed on tamper | **VERIFIED** with a CPU smoke artifact (random-initialised encoder from the local config): `training/tests/test_training_m3.py` | — | 4 training tests | see log |
| m3_encoder | A head — first GPU candidate (rule v1, historical) | **TECHNICALLY_VALID_BUT_A_SEMANTICALLY_MISALIGNED** (frozen history, `docs/training/runs/m3-berturk-multihead-2026-09-18.md`): binary macro-F1 0.8267 (baseline 0.8271); A head vs the AI-assisted, human-adjudicated 500-row reference precision 0.636 / recall 0.897 — it reproduced rule-v1 supervision, which counted ordinary insults as profanity. No A threshold derived, not promoted, run preserved on Drive | — | — | see log |
| m3_encoder | A head — rule-v3 candidate (current) | **TRAINED, REVIEWED, NOT PROMOTED** (2026-09-18, fourth pass): `m3-berturk-multihead-a-rule-v3-20260918-074806`, weights `41d98d7f…`, trained at `dba8632` on the rule-v3 files at `7f5e003`; binary macro-F1 0.8247 [0.8108, 0.8377] (baseline 0.8271, drop inside the allowance); A head vs the 500-row AI-assisted, human-adjudicated reference at 0.5: tp 32 / fp 1 / fn 7 / tn 460, precision 0.970 [0.889, 1.0], recall 0.821 [0.690, 0.930] (rule v1: 35 / 20 / 4 / 441). Gates: technically valid PASS, binary PASS, A semantic PASS, A evaluation strength NEEDS_WORK (39 positives). Metadata correction prepared and validated without retraining (weights byte-identical), Drive not overwritten. Run record `docs/training/runs/m3-berturk-multihead-a-rule-v3-20260918-074806.md` | binary threshold for this artifact; owner promotion decision | correct_metadata 10, training 11 | see log |
| m3_encoder | A head — retraining path (rule v3) | DONE (third pass, kept for the record): **WAITING_FOR_GPU_ARTIFACT, READY_FOR_COLAB** (2026-09-18, third pass): pseudo-label **rule v3** — the frozen A pseudo-label definition, A = an explicit obscene / profane lexical root, an explicit list of 17 POSITIVE / 130 EXCLUDED roots, no REVIEW — committed at `abbd313`, then the training labels were regenerated from it: train 1,528 positive / 25,464 negative / 0 masked; dev 257 positive / 4,507 negative / 0 masked; new run id and artifact id mandatory; the evaluation reference enters with its true provenance kind | the GPU run | generator 20, training 8 | see log |
| m3_encoder | A head — rule v2 (intermediate, superseded) | taxonomy experiment: classes from terlik's category metadata (21 POSITIVE / 115 EXCLUDED / 11 REVIEW masked); train 1,463 / 25,398 / 131 masked. Superseded by rule v3; files preserved in git at `87bc41d` | — | — | see log |
| m3_encoder | A head — training path (first pass, superseded) | WAITING_FOR_GPU_ARTIFACT, READY_FOR_COLAB (2026-09-18): owner decided the HYBRID strategy (`docs/blockers/m3_head_labels.md`); pseudo-labels on the frozen TRAIN split committed (`eval/derived/m1_lexicon_train_seed42.json`, 26,992 rows, 2,578 positives = 9.55 %, generated under `protocols/m1_lexicon_train_labels_protocol.md`); trainer takes `--labels-a` (pseudo, supervision) and `--labels-a-human` (oracle, dev only); handoff `docs/training/m3_encoder.md` corrected to the repository | Drive upload of the corpus (RESOURCES item 1) and the GPU run | 7 training tests; 11 generator tests | see log |
| m3_encoder | A head — evaluation reference | **AI-assisted, human-adjudicated, evaluation only** (2026-09-18): the 500-row seed-42 dev sample (`eval/annotation/a_head_dev_sample_seed42_n500.ids.json`, guideline v1.1) labelled by two AI annotators (Claude/Fable, Gemini; 497 / 500 agreement, Cohen's κ 0.958), the 3 disagreements decided by the human owner; 39 positive / 461 negative; private and uncommitted (`eval/annotation/private/`, sha256 `931c606b…`). NOT a human oracle; never a training label; never a source of rule edits. Enters the evaluator only as `--labels-a-reference … --labels-a-reference-kind ai-assisted-human-adjudicated` | — | 6 sampler tests; training 8 | see log |
| m3_encoder | A head — threshold and production | **A operating threshold FIXED at 0.50 by policy A-OP-1** (owner, 2026-09-18, `protocols/m3_a_head_operating_policy.md`): a versioned policy, NOT derived, no threshold curve inspected; M3 A complements M1 A1 on the shared family-A carrier and thresholds (all 0.50). **Binary threshold for the rule-v3 artifact NOT DERIVED yet** (pre-registered r = 3 procedure, CAL half). **Production unchanged**: the m3 artifact in use is still the binary-only baseline `m3-berturk-pytorch-fp32-epoch1`; `thresholds.yaml` and `artifacts/MANIFEST.md` untouched; no candidate promoted. Open architecture gap: M1's A1 also fires on the 130 rule-v3 EXCLUDED ordinary insults; no separate generic-insult signal exists (B1 untrained) | derive the binary threshold for this artifact; owner: promotion, and the A1-carrier gap | — | — |
| m3_encoder | B head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT — code and handoff complete | no B-labelled corpus (RESOURCES item 6, `docs/blockers/m3_head_labels.md`) | smoke test | see log |
| m3_encoder | C head | BLOCKED_BY_DATA + WAITING_FOR_GPU_ARTIFACT — code and handoff complete | C slice being labelled, no date (RESOURCES item 7) | smoke test | see log |
| m3_encoder | banned-dataset written check (`DATASETS.md`), truncation policy declared in spec §5, corpus count corrected (Q17) | **VERIFIED** (documents exist, dated) | — | — | see log |
| m4_implicit | stage 1 (binary threshold) | VERIFIED at the decision layer | — | test_binary_offensive (12) | baseline |
| m4_implicit | stage 2 | BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT — handoff `docs/training/m4_stage2.md` written | pre-registered precision budget (Q23); labelled C slice; influence tooling on GPU | — | see log |
| m4_implicit | C1–C5 rows, fixture set | BLOCKED_BY_DATA | C head + labelled slice | — | — |
| m5_sarcasm | everything | BLOCKED_BY_DATA — training code (`training/m5_sarcasm`) and handoff `docs/training/m5_sarcasm.md` written; module stays a documented stub | entry gate: corpus not named / requested (Q27, `docs/blockers/m5_sarcasm_corpus_gate.md`) | — | see log |
| decision layer | fusion, guards, thread rule, family A, binary boundary | VERIFIED; now exercised by real producers: two-channel fusion (m1 raw + normalized), ADR-005 assignment from a real m6 target, NON_HUMAN_TARGET and HOMONYM suppression by span | placeholders remain placeholders (Q25); Q1, Q2, Q4 verdict policy | 45 + 12; 8 e2e | see log |
| pipeline / counter / API | mechanics | VERIFIED | — | 35 + 20 + 6 | baseline |
| eval infrastructure | Gate 1 observability | VERIFIED | — | 15 + 5 + 12 | baseline |
| full pipeline | end-to-end on real m0, m2, m6, m1, m3 (+ m4 note, m5 stub) | **VERIFIED for the connected behaviour** (2026-09-17): 8 e2e cases with stage-named assertions; reference run above; every verdict still `review`-or-worse because m5 degrades the result (fail closed) | Q1, Q2, Q3 outcomes recorded, not judged; m5 stub keeps every verdict degraded | 8 e2e; run_all | see log |

## 1a. Session handoff (2026-09-18, end of the A-head preparation session)

**Branch / HEAD:** `audit/m1-m6`, see `git log` (commits of 2026-09-18 listed in §2); working tree
clean; no process running. Verification at this HEAD (with **`AI/.venv`**, the project
interpreter — CONTRIBUTING.md "Interpreter"): full suite OK / 1 skipped (the declared m5 skip),
`python -m pipeline.contract_example --check` exit 0, both derived label files `--check` CURRENT.
Fresh reference run `eval/results/post_m2_0_1_1/` at `d7925de` (git-ignored like every named run;
recorded above): identical behaviour to `f6b48ed`, latencies within budget except one transient
m3 timing that re-timed within budget. The repository is measured and clean for the Colab run.

**A-head preparation (owner decisions 2026-09-18, all executed locally):**
- HYBRID strategy recorded (`docs/blockers/m3_head_labels.md`): terlik pseudo-labels train, human dev
  subset evaluates; `AI/training/` ratified; karaliste / OFF-NOT / baseline predictions excluded.
- Train-split generator + protocol; dev file regenerated on the implemented m2/m6; comparison re-run.
- Trainer: `--labels-a` (repeatable, derived-format aware), `--labels-a-human` (dev only), `a` vs
  `a_pseudo_label_agreement` kept apart; label provenance in `heads.json`.
- Annotation package: guideline v1.1 + annotator instructions + sampler (draw / check / adjudicate / export), private dir ignored; the 500-row dev pilot is drawn and ready for two annotators.
- m2 0.1.1: history-dependent tier-2 guard fixed (found by the generator's determinism check).
- Q18 reconciled: instrument side implemented (Gate 1), remaining half is policy (Q2).

**Next executable dependency (updated 2026-09-18, fourth pass):** the `binary_offensive` threshold
of the rule-v3 artifact `m3-berturk-multihead-a-rule-v3-20260918-074806`, derived exactly as
`protocols/threshold_derivation_binary_offensive_stage1.md` (pre-registered r = 3 cost rule, fitted
on the frozen dev split's CAL half, reported on EVAL, bootstrap 10,000 / seed 42), from a new
derivation protocol filled from `protocols/templates/threshold_derivation.md` before any number. It
needs this artifact's raw-channel p(OFF) on the 4,764 dev rows; no repository command produces
that for a new artifact yet (the study's phase-12 script reads the baseline's stored predictions).
The A operating point is already set (A-OP-1, fixed 0.50). No GPU retraining is needed.

*(third pass, kept for the record)* the binary + A-head RETRAINING on Colab under pseudo-label
rule v3 — done: `rule-v3-20260918-074806`.

*(2026-09-17 handoff, kept for the record)* HEAD was `d6a6640`; 370 tests OK / 1 skipped;
reference run `eval/results/post_m6/` at `f6b48ed`.

**Module states**

| state | modules / slices |
|---|---|
| VERIFIED | m0 (all); m2 tier 1, protection pass, spans, offsets; m6 target resolution v1 and B4 on its fixtures; m1 raw + normalized channels, SUBSTRING_COLLISION, HOMONYM, NON_HUMAN_TARGET, terlik-vs-karaliste comparison; m3 binary scoring on both channels, artifact verification, multi-head loader (smoke artifact); m4 stage 1; decision layer; pipeline / counter / API; eval infrastructure; end-to-end connection of the real modules |
| PARTIAL (implemented, measured negative or unbuilt slices declared) | m2 DEASCII (0.71 capture, no-guessing rule) and the five lexicon-dependent patterns declared unhandled; m6 without a name gazetteer or a labelled slice; m1 without A4; m3 without trained heads |
| BLOCKED_BY_POLICY | m6 ambiguities (Q28, behaviour declared pending); m3 A-head label source; m4 stage-2 precision budget (Q23); every placeholder threshold / action (Q25); verdict questions Q1, Q2, Q3; ADR-008 and `training/` placement await ratification |
| BLOCKED_BY_DATA | m1 A4 table; m3 B corpus and C slice; m5 corpus (entry gate); m6 hand-labelled target slice; m2 real-obfuscation slice and human spot-check; m2 lexicons for ABBREV / VOWEL_DROP / WORD_MERGE / CHAR_DROP / DIALECT |
| WAITING_FOR_GPU_ARTIFACT | m3 multi-head fine-tune (code + handoff complete); m4 stage 2 (procedure written); m5 sequential transfer (code + handoff complete) |

**Human decisions still required**

| id | decision | where it is parked |
|---|---|---|
| Q1 | verdict while a target-dependent code is assigned under degradation (nudge vs review) | `OPEN_QUESTIONS.md`; e2e cases exclude it |
| Q2 | binary_offensive vs guard precedence — concrete instance: the binary score fires on clean collision traps 008 / 017 / 030 / 032 (`review`); should a guard or the trap rule reach it? | `TEST_SYSTEM_AUDIT.md` §6.2; `binary` trap rule exists, attached to nothing |
| Q3 | m3 raw channel scores `ctx.text`, not charsafe; m0 spec §1 says charsafe precedes any model | e2e ZWSP case records the state without judging |
| Q5 | ratify ADR-008 (normalized-channel offset map) — implemented on both sides | `protocols/ADR-008-normalized-channel-offsets.md` |
| Q6 | m6's two target routes (`result.target` vs `signals.target_*`) and the two placeholders on the same confidence | `MODULE_CONTRACTS.md` U-M6-1/2 |
| Q28 | `siz`, institution vs members (incl. `-deki` forms), religion vs followers, sports supporters | `protocols/m6_target_guideline.md` §2 (v1 behaviour declared PENDING) |
| Q23 | pre-registered stage-2 precision budget | `docs/training/m4_stage2.md` |
| Q25 | derive every placeholder threshold / action on dev | `thresholds.yaml` |
| A-head labels | **DECIDED 2026-09-18** (HYBRID: terlik pseudo-labels train, human dev subset evaluates; binary head compared with the baseline at the 0.5 reporting point). Remaining human work: label the dev sample (`docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md`) | `docs/blockers/m3_head_labels.md` |
| m5 gate | name and request the sarcasm corpus | `docs/blockers/m5_sarcasm_corpus_gate.md` |
| A4 table | owner-approved sacred-concept roots with sources | `docs/blockers/m1_a4_sacred_concepts.md` |
| training placement | **RATIFIED 2026-09-18**: `AI/training/` is the official home of training code | `training/README.md` |
| Q12 / Q16 / Q20 | m1 latency criterion, two-tier judgement, collision base rate | `OPEN_QUESTIONS.md` |

**Next executable dependency:** the m3 A-head run on Colab (`docs/training/m3_encoder.md`) the
moment the A-label decision lands; independently of that decision, the binary head alone can be
trained with the same command (no `--labels-*`) to validate the handoff end to end on a GPU.
Everything else locally executable in this phase is done.

**Nothing lives only in the chat:** every finding, decision proposal, measured number and
blocker is in the audit documents (`docs/audit/`), the protocols, the blockers, the handoffs,
the READMEs and the commit messages listed in §2.

## 2. Log of work (newest first)

| date | component | what | tests | commit |
|---|---|---|---|---|
| 2026-09-18 | m3 A head / m1 / m2 / training | Fourth pass after the rule-v3 run. **A-OP-1** pre-registered by the owner: the rule-v3 candidate's A operating threshold is FIXED at 0.50 (not derived; 39 reference positives; reporting point = operating point; no instability fallback); M3 A complements M1 A1. **m2 0.1.2**: a word-final "!" is punctuation, not a leet "i" (`Amiiin!` / `Amin!` no longer reach A1; m1's guard not broadened). **m1 0.1.2**: collision-evidence roots in a fixed order (was hash-seed dependent). Label files regenerated: **0 A labels changed** (train 0 / 26,992, dev 0 / 4,764); the artifact's training bytes preserved at `7f5e003` and pinned by a test. **Training provenance**: wording built from the resolved reference kind (`training/m3_encoder/provenance.py`); published `a_human` keys renamed `a_reference`; no stamping "human" by omission. **correct_metadata** 1.0.0: metadata-only correction; the rule-v3 artifact's metadata corrected on a scratch copy (weights `41d98d7f…` byte-identical; Drive not overwritten; record committed). Excluded insult roots verified still in the lexicon (M1 A1), with the no-generic-insult-signal gap recorded | m2 34, m1 25, generator 21, training 11, correct_metadata 10, end-to-end +1, full suite | this pass's commits |
| 2026-09-18 | m3 A head / labels | Pseudo-label **rule v3** frozen before generation (protocol amendment (b)): A = an explicit obscene / profane lexical root; explicit, versioned list of 17 POSITIVE / 130 EXCLUDED roots, REVIEW empty (owner decisions: kahpe, sürtük, kaltak, kancık excluded; pezevenk, gavat positive; kevaşe excluded). Generator 4.0.0 stops on an unexpected dictionary condition and records a taxonomy digest. Training labels regenerated from rule v3: train 1,528 positive / 25,464 negative / 0 masked; dev 257 positive / 4,507 negative / 0 masked. Leakage proof re-run: every label re-derivable from the committed protocol list alone; an audited DEV rerun opened no reference, annotator, prediction or test file. Rule v1 candidate historical; rule v2 intermediate; A threshold NOT DERIVED; production artifact unchanged. Open findings, not fixed here: (1) `amin!` with one `!` attached still reaches A1 through m2's LEET channel (`!` read as `i` gives `amini`); m1's guard is deliberately not broadened; 0 corpus rows affected; (2) m1 joins collision-evidence roots from a set, so their order in the evidence text varies with the Python hash seed (labels unaffected) | generator 20, m1 24, training 8, full suite | `abbd313`, `2eb1005`, `7f5e003`, + this docs commit |
| 2026-09-18 | m3 A head / m1 / labels | First GPU run executed on Colab L4 (5 min 53 s) and reviewed; the 500-row dev sample annotated by two AI systems and adjudicated by the owner (AI-assisted, human-adjudicated reference, 39 positives). Finding: the A head reproduced rule-v1 supervision (ordinary insults as profanity) → candidate frozen as TECHNICALLY_VALID_BUT_A_SEMANTICALLY_MISALIGNED. m1 0.1.1: `amin` (amen) no longer fires the obscene root `am` (whole-word clean rule, traps 034/035). Pseudo-label rule v2 pre-registered from terlik category metadata + guideline text, then generated; leakage proof recorded (generator cannot reach the reference; classes re-derivable from taxonomy alone). Evaluator stamps the reference's true provenance kind. Retraining handoff updated (Drive root `nsosyal-train`, new run id) | m1 24, generator 14, training 8, full suite | `c24406b`, `17ee9c3`, `4ac2abe`, + the labels commit |
| 2026-09-18 | m3 A head / annotation | guideline v1.0 → **v1.1** on the owner's decision (explicit profanity only; ordinary insults `aptal` / `salak` / `eşek herif` are `0` unless the post also carries a genuine profane root), resolving v1.0's §3 / §9 contradiction before any row was labelled; `ANNOTATOR_INSTRUCTIONS.md` added; the 500-row seed-42 dev pilot redrawn under v1.1 with the **same 500 ids** (ids sha256 `9e4ab82f…` unchanged; only the pinned guideline digest moved `87a8314a…` → `72e61d19…`); templates stay private | sampler 6, architecture 17 | `68963dd` (guideline + instructions), then the sample record |
| 2026-09-18 | full pipeline | fresh reference evaluation after m2 0.1.1 (`eval/results/post_m2_0_1_1/`, head `d7925de`, dirty=false, 50 repeats, n_boot 1000): field-by-field identical behaviour to `f6b48ed` (traps, observations, per-code, representation, flip rate, binary-on-traps, degraded); latency-only differences, m3 transient re-timed within budget; status paragraph updated | run_all exit 0; 394 OK / 1 skipped; contract check exit 0 | see log |
| 2026-09-18 | m1 labels / m3 A head / m2 / docs | A-head preparation on the owner's decisions: shared train/dev label generator with the `a_label` rule, protocols (train pre-registered, dev and comparison amended); dev regenerated and TRAIN file generated (26,992 rows) from a clean tree; terlik-vs-karaliste re-run with `terlik_any_channel`; trainer hybrid path (`--labels-a` / `--labels-a-human`, agreement vs oracle apart, label provenance); annotation package (guideline v1.0, sampler); m2 0.1.1 determinism fix + contract example hash; handoff corrected; interpreter declared; Q18 reconciled; status updated | generator 11, sampler 6, training 7, m2 33; full suite OK / 1 skipped | `6e45225`, `d46f4e9`, `2072497`, `a6347f5`, + the derived-files commit |
| 2026-09-17 | full pipeline | reference evaluation on the implemented state (`eval/results/post_m6/`, head `f6b48ed`, dirty=false): 0 regressions, flip 0.0, p95 170 ms, only m5 degraded; docs (README, CONTRIBUTING, HANDOVER, MANIFEST) corrected to the current state | run_all exit 0 | `f6b48ed` |
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

Q1, Q2, Q3, Q5 (the contract half is the ADR-008 proposal; the *label* half was decided on 2026-09-18 for the A-head pseudo-label; the *runtime* half — whether normalized-channel hits fire codes — is unchanged), Q6, Q12, Q16, Q18 (now policy only: which traps carry the `binary` rule, whether binary flips are budgeted — the instrument exists), Q20, Q23, Q25, Q28.

## 5. GPU handoffs

Index: `AI/docs/training/GPU_HANDOFF.md` — m3 multi-head (`m3_encoder.md`, **READY_FOR_COLAB for binary + A head** since 2026-09-18; B / C still blocked on data), m4 stage 2 (`m4_stage2.md`, blocked on policy + data), m5 sarcasm (`m5_sarcasm.md`, blocked on data); code complete for m3 and m5 (`AI/training/`, ratified).

## 6. Data blockers

`AI/docs/blockers/m1_a4_sacred_concepts.md`, `m3_head_labels.md` (A head decided; the human dev
oracle is the remaining data item — annotation package in `AI/docs/annotation/` and
`eval/a_head_dev_sample.py`), `m5_sarcasm_corpus_gate.md`.
