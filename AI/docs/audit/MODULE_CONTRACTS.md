# Module contracts — SPECIFIED vs IMPLEMENTED vs UNCERTAIN

Audit reconstruction, 2026-09-17, branch `audit/m1-m6` at `f063ddf` plus the uncommitted working
tree. For each module: the contract the specs and ADRs demand, what `module.py` does, and what
neither settles. Line numbers refer to files under `AI/`. Items tagged `U-<module>-<n>` are
cross-referenced from `OPEN_QUESTIONS.md`.

The shared contract every module implements (`contracts/module_api.py`):

- Input: a frozen `Context(text, charsafe_text, normalized_text, signals, config, trace_id)`.
  `signals` is a `MappingProxyType` of deep-frozen copies of earlier modules' `out.signals`, keyed by
  module name. `best_text(RAW)` returns `charsafe_text` or `text`; `best_text(NORMALIZED)` returns
  `normalized_text` if present, otherwise the raw choice.
- Output: a `ModuleOutput` whose populated contract fields must be a subset of the class attribute
  `provides` (subset of `{charsafe_text, normalized_text, form, content, target, guards, thread}`);
  `signals` and `notes` are always allowed. `BaseModule.process` wraps `_load` / `_run` so that any
  exception becomes `ok=False` plus a note, and stamps `module`, `version`, `latency_ms`.
- Rules (CLAUDE.md 1–7): frozen contracts; no cross-module import; never mutate `ctx.text`; never
  apply a threshold or decide an action; return only declared fields; stdlib core; runnable alone.

---

## m0_charsafe (reference module; in scope only as m1's input)

**SPECIFIED** (`modules/m0_charsafe/spec.md`, ADR-001 amendment, HANDOVER #22, #39, #45, #47)

- Reads `ctx.text`. Writes `charsafe_text`, one `FormPattern` per transformation with `evidence`,
  `signals["charsafe_changed"]`. May emit `ZERO_WIDTH`, `HOMOGLYPH`, `DOTLESS_I`.
- Approach in spec §4: (1) delete every `Cf` / `Cc`, (2) confusables only when non-ASCII present,
  (3) `I→ı`, `İ→i` then `.lower()`.
- Acceptance: `SIKINTI` never yields `sik`; zero modification on clean ASCII Turkish; every change
  has evidence; per-length latency bands from `thresholds.yaml` (64: 0.25 ms … 5000: 25 ms).

**IMPLEMENTED** (`modules/m0_charsafe/module.py`, v0.2.0, `emits_spans = False`)

- Five passes, in order: `_strip_invisible` (Cf/Cc except `\t\n\r`, plus Hangul fillers and braille
  blank; emoji ZWJ between emoji parts kept and not reported; leading BOM low confidence),
  `_handle_combining_marks` (canonical composition kept, marks stuffed onto Latin letters stripped,
  other scripts' marks kept), `_map_styled_latin` (fullwidth, mathematical, circled, squared,
  parenthesized, negative circled/squared, super/subscript letters, small capitals, regional
  indicators that do not form flags), `_map_confusables` (small curated Cyrillic/Greek/Latin table,
  only tokens mixing Latin or made entirely of lookalikes), `_turkish_lower`.
- Signals: `_offsets` (internal, original index of every charsafe character), `offsets_identity`,
  `invisible_removed`, `homoglyphs_mapped`, `charsafe_changed`.
- Known, tested gap: a word spelled only from valid flag pairs passes.

**UNCERTAIN**

- U-M0-1 (already in HANDOVER §5): spec §4 describes three steps; the code runs five passes with
  behaviour the spec does not mention (layout controls kept, emoji ZWJ kept, combining marks,
  styled Latin). Spec and code disagree on the "what", not only the "how".
- U-M0-2: m0 spec §1 says the goal is to stop the text lying "before any model sees it", but m3
  scores `ctx.text`, not `charsafe_text` (see m3 below). The protection m0 provides reaches m1 and
  m2 only.

---

## m1_lexicon

**SPECIFIED** (`modules/m1_lexicon/spec.md` incl. uncommitted §1 table, ADR-001, ADR-005, ADR-006,
`protocols/m1_lexicon_dev_labels_protocol.md`, HANDOVER #56–#57)

- Reads `ctx.text` **and** `ctx.normalized_text` ("run on both, report both") and
  `ctx.signals["m6_target"]` (`target_type`, `target_confidence`).
- Writes:
  - `signals.lexicon_hit` (bool, any legitimate match on either channel), `lexicon_hit_raw`,
    `lexicon_hit_norm` — present and boolean on every input, including empty.
  - `content`: family-A profanity on the `A1` carrier (decision layer assigns A1/A2/A3 from m6's
    target, ADR-005) and `A4` (sacred-concept extension).
  - `guards`: `SUBSTRING_COLLISION`, `HOMONYM`, `NON_HUMAN_TARGET` (the last raised on each own
    family-A match when m6's published type is `non_human`, score = m6's confidence, span = that
    match's span).
  - Every match and every guard carries the span of the exact triggering substring and
    `GuardResult.source = "m1_lexicon"`; a spanless item is a contract violation.
- Method: morpheme-boundary matching (`terlik` balanced mode), free substring search banned, the
  two-tier hard/soft list structure of `90pixel/kufur-filtresi`, sacred-concept extension for `A4`,
  `karaliste` never used as reference.
- Metrics owed: recall and FPR of the signal alone with CIs, on both channels separately;
  zero-firing proof on traps; terlik vs karaliste coverage comparison; A4 growth table.
- Acceptance §8: zero positives on the trap list; spans on every item with `text[start:end]` equal
  to the matched root or colliding word; three boolean signals always present; collision guard fires
  whenever the boundary test rejects a root; sacred-concept table committed; terlik vs karaliste
  comparison committed; **p95 latency under 5 ms**; licences recorded.
- Slice rule: the evaluation `lexicon_hit` / `lexicon_free` slice is `eval/frozen/study_slice_dev.json`
  (karaliste), never recomputed from m1; `eval/derived/m1_lexicon_dev_seed42.json` is regenerable
  per-row labels for m3's A head and for comparison, never a slice.

**IMPLEMENTED** (`modules/m1_lexicon/module.py`, v0.1.0, `provides = {content, guards}`,
`emits_spans = True`; `requirements.txt`: `terlik==0.1.0`, MIT)

- `_load` (94–103): imports terlik or raises `RuntimeError` (→ `ok=False`, module degraded
  "failed"); builds the engine in balanced mode; warms the cache; keeps a folded, length-sorted
  list of terlik's roots for the collision pass.
- `_run` (105–155): channels = `{raw: ctx.best_text(RAW)}` plus `{normalized: ctx.normalized_text}`
  when not `None`. For each channel `_scan` (158–178):
  1. `tr_lower` (index-preserving Turkish lowercase, 60–73), then `terlik.get_matches`.
  2. A match whose word starts with a `CLEAN_PREFIXES` entry (`amca`, `sikinti`) longer than the
     matched root is a collision, not a hit (48–55, 165–169).
  3. Every other `\w+` token that contains a folded root as a substring and was not already a hit
     or collision becomes a `SUBSTRING_COLLISION` (170–177).
- Offsets (181–204): raw channel maps through m0's `_offsets` when `charsafe_text` differs from
  `text` and the lengths match; identity when equal; otherwise `None`. The normalized channel
  reuses the raw map **only when `len(normalized_text) == len(raw_text)`** (122); otherwise no map.
  With no map the channel's flag is still set, a note is written, and **no content score or
  collision guard is emitted for that channel** (123–127).
- Content: one `ContentScore(A1, 1.0, f"m1_lexicon@{channel}", span)` per distinct original span
  (130–135). Score is constant `1.0`.
- Guards: `SUBSTRING_COLLISION(1.0, "m1_lexicon", evidence, span)` per distinct collision span,
  deduplicated across channels by span (`collisions.setdefault`, 137, 139–141);
  `NON_HUMAN_TARGET(float(target_confidence), "m1_lexicon", "m6_target: non_human", span)` per
  content span when m6's `target_type == "non_human"` and the confidence is numeric (207–218).
- Signals: `lexicon_hit = raw or norm`, `lexicon_hit_raw`, `lexicon_hit_norm`, `matched_roots`
  (sorted union over channels), `engine = "terlik 0.1.0 balanced"`.
- Not built: `A4`, `HOMONYM`, sacred-concept table, terlik-vs-karaliste comparison report
  (`README.md` "Not built yet").
- Tests (`test_unit.py`): contract shape, input not mutated, never raises, all traps produce no
  content and a `SUBSTRING_COLLISION`, inflected roots match on the boundary, clean words with a
  root inside are collisions, `SIKINTI` clean / `APTALLAR` hit, channel tagging, flag-only on an
  unmappable normalized channel, spans through m0 offsets, boolean signals on every input, span on
  every item, `NON_HUMAN_TARGET` from a faked m6 signal, determinism.
- Measured (`eval/results/m1_lexicon.json`, local run, 20 repeats, 17 fixture items): A1 8/8,
  SUBSTRING_COLLISION 6/6, NON_HUMAN_TARGET 1/1, 0 FP; 33 traps, 0 regressions; clean p95 within
  the per-length bands (0.39 / 2.5 / 8.1 / 39.7 ms); **adversarial p95 301 ms on the 5000-char
  adversarial item (over budget, published finding)**.
- Derived labels on the frozen dev split (`eval/derived/…seed42.json`): 459 / 4,764 rows hit
  (terlik) vs 614 in the frozen karaliste slice; **2,356 rows (49 %) carry at least one
  `SUBSTRING_COLLISION`**; normalized channel `available: false`.

**UNCERTAIN**

- U-M1-1: spec §3 says "Reads `ctx.text`"; the code reads `ctx.best_text(RAW)`, i.e. m0's charsafe
  text, and maps spans back through `_offsets`. The derived-labels protocol §4 states this openly
  ("raw = m0's charsafe text, not the untouched original") but the spec was not updated.
- U-M1-2: the normalized channel can only ever yield spanned scores when m2 produces a text of the
  **same length** as the raw channel and the code then assumes position-for-position alignment
  (122). No offset map for m2's channel exists in any contract or spec. When m2 ships, either every
  length-changing repair makes m1's normalized hits flag-only (never a fired code), or same-length
  but re-ordered repairs produce wrong spans. `test_scores_tagged_with_channel` encodes the
  same-length assumption (`"a.p.t.a.l"` vs `"aptal...."`).
- U-M1-3: `lexicon_hit_raw` / `lexicon_hit_norm` can be `True` with no `ContentScore` emitted (the
  flag-only path). Consumers that assume "hit ⇒ a fired A code" (the thread counter does not, the
  stage-1b condition would not) should know. The derived-labels protocol §3 check 6 tolerates it.
- U-M1-4: spec §4.2 asks for the explicit two-tier hard/soft structure; the README says terlik's
  per-root `suffixable` flag *is* that split, and the module adds a hard-coded `CLEAN_PREFIXES`
  whitelist of two words (`amca`, `sikinti`) as its own exception list. Whether this satisfies §4.2
  and §10 ("the two-tier list structure is in place") is a judgement the owner has not recorded.
- U-M1-5: the second collision pass fires on any token containing a terlik root as a substring,
  after folding. Roots as short as two letters (`am`) make 49 % of dev rows carry a collision guard.
  Under ADR-001 scoping the guard is harmless to other spans, but spec §5 says "the guard firing
  **is** how precision gets measured" — with a 49 % base rate the guard count measures little.
- U-M1-6: a collision guard from one channel can suppress a hit from the other channel on the same
  original span (guards are deduplicated by span and carry no channel; `fusion.guard_applies` only
  checks same module + overlap). Verified with the decision layer alone (probe G in
  `PIPELINE_FLOW.md` §8). No test covers a cross-channel disagreement.
- U-M1-7: spec §8 "p95 latency under 5 ms" vs `thresholds.yaml` per-length bands (3 / 10 / 30 / 140
  ms, owner decision recorded in ADR-003's amendment) vs measured adversarial p95 of 301 ms.
- U-M1-8: the stage-1b condition signal is `lexicon_hit_raw` in the protocol and the script, but
  `lexicon_hit` in spec §8 and in the `thresholds.yaml` comment. Not in force, so no runtime
  effect, but the two documents name different signals.
- U-M1-9: terlik's coverage differs materially from the frozen karaliste slice (on EVAL: 161 of 309
  karaliste hits are terlik-free; 67 terlik hits are karaliste-free). Spec §6 asks for this
  comparison as a committed deliverable; today it exists only as a 2×2 table inside
  `eval/results/m4_stage1b.json` and as counts in the derived file header.

**Expected failure modes**

- terlik missing → `ok=False` on every call → module degraded "failed" → every verdict `review`.
- Obfuscation m0 does not undo (leet, spacing beyond terlik's own tolerance, deascii) → no hit;
  spec routes these to m2, which is a stub.
- Profanity through sacred concepts (`A4`) → not detected.
- Dual-register words (`moruk`, `lan`, `oğlum`): spec §7 says they must not auto-fire; whether
  terlik balanced contains them is not tested here (no fixture).
- A root inside a word terlik reads as root + legal suffix that is actually a clean word (the
  `amca` case) → false `A1` unless listed in `CLEAN_PREFIXES`. The whitelist has two entries.
- Every hit scores `1.0`, so any threshold below 1.0 fires; precision of the signal is entirely in
  the matcher, never in the threshold.

---

## m2_deobf

**SPECIFIED** (`modules/m2_deobf/spec.md`, m1 spec §3, m3 spec §1/§4, thresholds.yaml `fusion` and
`budgets.clean_to_dirty_flip_rate`, HANDOVER #44, #50)

- Reads `ctx.charsafe_text` (fallback `ctx.text`). Writes `normalized_text` and one `FormPattern`
  per transformation with `evidence` and `span` into the original text. Never writes content;
  never replaces `ctx.text`.
- Patterns in scope: `LEET`, `REPEAT`, `SPACED`, `PUNCT_SPLIT`, `CHAR_DROP`, `WORD_MERGE`, `ABBREV`,
  `DEASCII`, `VOWEL_DROP`, `SUFFIX_ON_MASKED`, `DIALECT`, `PHONETIC`; `EMOJI_SUB` declared out of
  scope for v1. `sık` / `sik` and similar ambiguities must not be rule-resolved.
- Two tiers: tier 1 conservative character rules always on; tier 2 dictionary / morphology repairs
  disable-able behind the over-correction budget (`clean_to_dirty_flip_rate 0.01`, measured on the
  trap list). A protection pass (URLs, mentions, hashtags, brands, proper nouns) before repairs.
- Idempotent (`f(f(x)) == f(x)`); `text[start:end] == evidence` for every pattern; the leakage rule
  (§10) separates the evaluation generator from any training augmentation generator.
- Consumers: m1 scans the normalized channel; m3 is specified to score it (`norm_score`, `@normalized`
  content); `fusion.strategy: max` over `channels: [raw, normalized]`; `pipeline_budget_report`
  measures flip rate by running the pipeline with and without m2.

**IMPLEMENTED** (`modules/m2_deobf/module.py`, v0.0.0, `stub = True`, `provides = {normalized_text, form}`,
`emits_spans = False`)

- `_run` returns `ModuleOutput(notes=["stub: detection not implemented"])`. Nothing else.
- Effect on the system: `ctx.normalized_text` is `None` for every later module; m1 never scans a
  second channel; `lexicon_hit_norm` is always `False`; the module is listed in
  `signals.pipeline.degraded` with kind `stub` on every request; verdict can never be `clean`.
- Fixture: one real clean item, two placeholders. Unit tests: the shared contract tests; two
  behaviour tests skipped.

**UNCERTAIN**

- U-M2-1 (already in HANDOVER §5): spec §9 requires `text[start:end] == evidence`; `FormPattern.evidence`
  is free text in the schema and in m0 (m0 writes descriptive evidence such as
  `'SIKINTI' -> 'sıkıntı' (…)`). Either m2 follows a stricter rule than m0 or the spec is wrong.
- U-M2-2: no contract field carries a per-character offset map from `normalized_text` back to the
  original. m1 (U-M1-2) and the m3 spec's "truncate both channels at the same character offset"
  both need one. `signals` could carry it (m0 uses an internal `_offsets`), but no spec names a key.
- U-M2-3: the m2 spec's headline number ("recall drops from A to B under pattern P; the channel
  recovers C points") needs a detector scored on both channels plus the decision layer; m3 scores
  only the raw channel today and no `norm_score` threshold exists. `docs/team/MOHAMMED.md` says
  where that measurement lives is an open question for Musaab.

**Expected failure modes (specified, not observable yet)**

- Over-correction: a tier-2 repair turning a clean word into a profane one (the documented Turkish
  F1 drop) → policed by `clean_to_dirty_flip_rate`.
- Damage to proper nouns, brands, mentions, URLs without the protection pass.
- Rule-resolving `DEASCII` ambiguity (`sık` vs `sik`) → forbidden.

---

## m3_encoder

**SPECIFIED** (`modules/m3_encoder/spec.md`, ADR-003, ADR-005, ADR-006, `artifacts/MANIFEST.md`,
`protocols/threshold_derivation_binary_offensive_stage1.md`, `docs/team/abdullah/*`)

- One `dbmdz/bert-base-turkish-cased` encoder fine-tuned on a frozen split; three heads: A ("profanity
  present", emitted on the `A1` carrier, never A2/A3/A4), B multi-label (`B1`, `B2`, `B3`, `B5`;
  `B4` is m6's), C (`C1`–`C5`, thresholds owned by m4).
- Reads `ctx.text` and `ctx.normalized_text`; runs **twice per request**; writes one `ContentScore`
  per code and channel with `source = "m3_encoder@raw"` / `"@normalized"`, plus signals
  `raw_score`, `norm_score`, `artifact`.
- Never sets `threshold` / `fired`; never fuses channels; never calibrates; never publishes
  embeddings; D1 is not a head (ADR-003).
- Truncation policy must be declared in §5 and tested; a note whenever truncation occurred.
- Artifact discipline: every deployable artifact has a MANIFEST row with sha256 and its own
  thresholds file, derived on that artifact; decision-flip rate per export artifact; banned datasets
  (`Toygar/…`, `Overfit-GM/…`) with a written leakage check.
- Acceptance: per-code metrics with CIs on both channels, frozen-baseline comparison, latency on the
  demo machine, decision-flip table, MANIFEST row, hydration loss for tweet-ID datasets, banned
  dataset proof, heavy deps confined to `modules/m3_encoder/requirements.txt`.
- Team docs (2026-09-15): the A, B and C heads are **deferred** — no labelled data exists; m3
  inference wraps the epoch-1 baseline; Python 3.11–3.13 because of the pinned scikit-learn.

**IMPLEMENTED** (`modules/m3_encoder/module.py`, v0.1.0, `provides = {content}`, `emits_spans = False`;
`requirements.txt`: `torch==2.11.0`, `transformers==5.15.0`, `scikit-learn==1.6.1`)

- `_load` (78–99): resolves checkpoint and tokenizer paths (env overrides), fails with
  `FileNotFoundError` if any file is missing, verifies sha256 of the checkpoint
  (`43a20d55…d4ca`) and of `config.json` / `tokenizer.json` / `tokenizer_config.json`, raises
  `ValueError` on mismatch (→ `ok=False`, degraded "failed"). Loads
  `AutoModelForSequenceClassification.from_config` + `state["model"]` with `strict=True`, FP32, CPU,
  eval mode. `local_files_only=True`; `test_no_network_at_load` patches `socket.connect`.
- `_run` (101–111): tokenizes `ctx.text` once to count tokens (note if > 128), encodes with
  `truncation=True, max_length=128, padding=False`, softmax index 1 = OFF. Returns
  `signals={"raw_score": p_off, "artifact": "m3-berturk-pytorch-fp32-epoch1"}` and **no content**.
  Mirrors `diagnosis/src/models.py::predict` (batch padding there; single unpadded item here —
  equivalent under an all-ones attention mask).
- Deliberately (docstring, owner decisions 2026-09-15): no content scores ("OFF is not profanity
  present"); no `norm_score`; scores `ctx.text`, **not** `charsafe_text` (BERTurk is cased, m0
  lowercases, the threshold was fitted on original text).
- Artifact equivalence recorded in the stage-1 derivation protocol: 4,764 dev rows through
  `EncoderModule.process`, 0 label flips vs `dev_predictions.csv`, max |Δp| 2.25e-06.
- Tests: contract tests; missing artifact fails closed; no network; publishes exactly
  `{raw_score, artifact}` and empty content; scores original text regardless of channels;
  truncation noted; deterministic. Artifact-dependent tests skip without the files.
- Measured (`eval/results/m3_encoder.json`, 200 repeats, one scored item): p50 37.7 ms, p95 58.0 ms
  (budget 80); traps 0/23 — trivially, since m3 emits no content and traps check content only.

**UNCERTAIN**

- U-M3-1: spec §4 contract vs implementation: no `norm_score`, no `@normalized` pass, no heads, no
  content. Spec is the target design; `README.md`, MANIFEST and team docs describe the partial
  state; `spec.md` itself carries no "current status" line, and HANDOVER §2 (working tree) still
  lists m3 as a stub.
- U-M3-2: which text m3 scores. Spec §4 says `ctx.text`; m0 spec §1 says charsafe must precede any
  model. Verified: `"ap​tal herif"` reaches BERT with the zero-width space inside the word
  (it still scored 0.969 in the probe, but nothing guarantees that for other invisible or homoglyph
  attacks). m1 sees the cleaned text, m3 does not.
- U-M3-3: the truncation policy (128 tokens, first tokens kept, note emitted) is stated in the
  module docstring and in the derivation protocol, not in spec §5 as spec §9 requires. Spec §9 also
  cites 512 as BERTurk's maximum, while the study and the module use 128.
- U-M3-4: `raw_score` is p(OFF) from a binary OFF/NOT classifier. The decision layer treats it as
  `binary_offensive` (review). Nothing maps it to a content code, so a threat, a doxing post or
  implicit abuse the model flags all become the same `review` with the explanation "genel
  saldırganlık skoru". The specified per-code B/C outputs do not exist.
- U-M3-5: `test_stub_modules_are_degraded_and_named` filters m3 out of the degraded list so that
  machines without the git-ignored artifact still pass; on such a machine every verdict is `review`
  with m3 listed as `failed`, and `scripts/check.sh`'s contract-example gate fails (the example
  embeds a real `raw_score`). `docs/team/abdullah/START_HERE.md` says every team member needs the
  artifact for that reason.
- U-M3-6: the m3 spec §5 says 36,232 Çöltekin tweets; the verified files hold 31,756 + 3,528
  (RESOURCES.md open item 3).
- U-M3-7: A-head gold: the corpus has OFF/NOT only; "profanity present" has no human label. The
  derived terlik labels are proposed as training labels (protocol §1), but which output is compared
  with the baseline's binary numbers is undecided (RESOURCES.md item 5). B-head data: none found
  (item 6). C slice: being labelled, no date (item 7).

**Expected failure modes**

- Artifact files absent or altered → `ok=False` every request → degraded "failed".
- Post longer than 128 tokens → judged on its first 128 tokens; note only.
- Anything only m2 would repair, plus invisible characters and homoglyphs → reach the model as-is.
- Family B / C / D content → today only visible through the binary score; no code, no per-code
  threshold, no per-code action.

---

## m4_implicit

**SPECIFIED** (`modules/m4_implicit/spec.md`, ADR-006 + amendment, `protocols/m4_stage1b_protocol.md`,
`protocols/threshold_derivation_binary_offensive_stage1.md`, HANDOVER #58–#59, #66, #68)

- Objective: raise recall on the lexicon-free slice without retraining beyond what is budgeted.
  Baseline numbers frozen in spec §2 (lexicon-free recall 0.5628 dev; stage 1 repair 0.5180 →
  0.6367 on EVAL at precision 0.7512 → 0.6509).
- Reads `ctx.signals["m3_encoder"]` (`raw_score`, `norm_score`, `artifact`) and nothing else.
  Writes **no content scores**; C1–C5 are m3's content. Deliverables are the `C1`–`C5` and
  `binary_offensive` rows of `thresholds.yaml` and the slice repair.
- Stage 1: one global cost-derived threshold on m3's binary score, no lexicon at inference (the
  study's S1b). Stage 1b: the same threshold conditioned on m1's lexicon signal, adopted only after
  measurement against stage 1 at equal coverage. Stage 2: influence-function hardening; retrains
  m3's encoder (an m3 artifact under m3's discipline); pre-registered precision budget before the
  first stage-2 number.
- Fixtures carry `context.signals.m1_lexicon.lexicon_hit` and `context.signals.m3_encoder.*`; slice
  defined by the signal, never by the category; boundary pairs B/C and C/D; negative controls
  (counter-speech, meta-discussion, self-criticism, factual group statements, negation).
- Acceptance: stage 1 integrated and re-verified; stage 1b measured before replacing stage 1;
  stage-2 budget committed first; recall/precision in one sentence; risk–coverage at equal coverage;
  labelled slice with agreement; official test set query count stays at one.

**IMPLEMENTED** (`modules/m4_implicit/module.py`, v0.1.0, **not** a stub, `provides = {content}`,
`emits_spans = False`)

- `_run` returns `ModuleOutput(notes=["C1–C5 not implemented yet"])`. Does not read `ctx.signals`.
  Does not degrade the result (ADR-006 amendment); `test_not_a_stub_and_emits_only_its_note` pins
  this.
- Stage 1 **integrated**: `thresholds.yaml` `binary_offensive.threshold: 0.320188`, raw channel
  only, action `review`; derivation file records CAL/EVAL halves, r = 3, EVAL confusion
  tp 343 / fp 184 / fn 117 / tn 1,738, artifact-equivalence check, the `>` vs `>=` tie row (dev row
  29308 scores 0.32018762… at full precision, below the rounded threshold under both rules).
- Stage 1b **measured and rejected** (`eval/results/m4_stage1b.json`, protocol commit `37a7a1c`,
  run at `f063ddf`): terlik-conditioned `t_hit 0.102285` / `t_free 0.341456` at stage 1's CAL flag
  count 594 (gap 0); primary (frozen karaliste slice) lexicon-free recall Δ = −0.0036, 95 % CI
  [−0.027, +0.019]; precision drop −0.0095 (i.e. a small gain); verdict `KEEP stage 1`. Note: the
  EVAL half was already used by the study, so the CI is conditional on that reuse.
- Stage 2: not started; no precision budget file exists for it (only the stage-1b budget 0.02).
- Fixture: one clean item, one placeholder. `eval/results/m4_implicit.json`: no code has support.

**UNCERTAIN**

- U-M4-1 (HANDOVER §5): the harness scores content, form, guards and target; it does not read
  `binary_offensive`, so m4's only live deliverable cannot be measured by `python -m modules.m4_implicit.eval`.
  The same blindness extends to traps (`must_not_fire` checks `result.fired()`, content only) and
  to the flip-rate budget.
- U-M4-2 (HANDOVER §5): stage 2 retrains m3's encoder, which carries A, B and C; a new m3 artifact
  forces re-derivation of every m3 threshold.
- U-M4-3: `provides = {content}` is kept "because every module's unit tests require a non-empty
  provides" (ADR-006), so the harness computes a 15-code content space for a module that by design
  emits nothing.
- U-M4-4: the spec's stage-1b text conditions on `m1_lexicon.lexicon_hit`; the protocol used
  `lexicon_hit_raw` (owner decision B). If stage 1b is ever re-proposed after m2 ships, the two
  signals diverge.
- U-M4-5: spec §9 requires a unit test asserting that each fixture's `context.signals.m1_lexicon.lexicon_hit`
  matches what m1 actually returns on that text — that would need m1 from m4's tests, which rule 2
  forbids. No such test exists; the requirement as written cannot be met without an exemption.

**Expected failure modes**

- The single global threshold trades precision for lexicon-free recall by design (0.7512 → 0.6509);
  any consumer expecting the 0.5 baseline precision will see more `review`.
- With m1's signal now terlik-based, a future stage 1b would be conditioned on a slice that
  disagrees with the frozen karaliste slice on roughly half of the karaliste hits (U-M1-9).

---

## m5_sarcasm

**SPECIFIED** (`modules/m5_sarcasm/spec.md`, ADR-003, HANDOVER #7, #31–#32)

- Gated: identify and request the Turkish sarcasm corpus first; granted → full plan; refused →
  smaller public irony dataset, results labelled exploratory; neither → drop the D1 claim.
- Reads `ctx.text` (raw punctuation and casing carry the markers). Writes `content` for `D1` only.
- Own model, own artifact and MANIFEST row, own thresholds row (`D1`), own `requirements.txt`; must
  be small or distilled; never reads m3 embeddings.
- Labelling rule: D1 only when a literally positive element exists (polarity inversion); no
  inversion → C. Explicit content wins over D1 (single-label axis).
- Precision on the benign-sarcasm control set gates acceptance, not recall; D1↔C confusion count;
  agreement number published however low.
- Fixtures carry `inversion_span` (asserted by m5's unit tests, ignored by the harness).

**IMPLEMENTED** (`modules/m5_sarcasm/module.py`, v0.0.0, `stub = True`, `provides = {content}`,
`emits_spans = False`)

- `_run` returns `ModuleOutput(notes=["stub: detection not implemented"])`. Degrades every result.
- Entry gate: the corpus is not named anywhere in the repo (`docs/team/abdullah/START_HERE.md`
  task 1; RESOURCES.md item 10). No gate record file exists.
- Fixture: one clean item, one placeholder; one behaviour test skipped.

**UNCERTAIN**

- U-M5-1: the spec describes the corpus by properties (1,515 samples, 0.73 / 0.76 accuracy) but
  not by name; the gate cannot be evaluated until it is identified.
- U-M5-2: `budgets.module_latency_p95_ms.m5_sarcasm: 20` is a placeholder for a model that does not
  exist; the "small or distilled" constraint has no measured candidate.

**Expected failure modes (specified)**

- Benign sarcasm at objects / software / weather firing as D1 → forbidden by the control set.
- D1 absorbing family C → forbidden by the polarity-inversion rule.
- Reported sarcasm (quoting) firing → must not.

---

## m6_target

**SPECIFIED** (`modules/m6_target/spec.md`, ADR-001, ADR-005 + amendment, ADR-007, HANDOVER #11,
#57, #60)

- Reads `ctx.text` (raw). Writes `target` (`TargetResult(type, confidence, evidence, span?)`),
  `signals["target_type"]` (a `TargetType` value) and `signals["target_confidence"]` for m1, and
  `content` `B4` with a span on every score.
- Does **not** provide guards (moved to m1, ADR-005). Never resolves a non-human target as
  individual or group. Never identifies, verifies or enriches the person behind an identifier.
- Method: regex layer for Turkish formats (phone, national ID with checksum, IBAN `TR…`, plates,
  address conventions) plus a gazetteer with morphological analysis (`zeyrek` or Zemberek) for
  entities; no transformer NER in v1 (ADR-007). Precision before recall for `B4`.
- Three ambiguities must be resolved by written rules: `siz`, institution vs members, religion vs
  followers (coordinate with m1's `A4`).
- Consumers: `fusion.resolve_family_a` (via `result.target`, gated by `family_a.target_min_confidence
  0.50`), `fusion.fast_path_hit` (same assignment), m1's `NON_HUMAN_TARGET` (via signals, gated
  only by `guards.NON_HUMAN_TARGET.threshold 0.50` on the confidence m1 copies into the guard).

**IMPLEMENTED** (`modules/m6_target/module.py`, v0.0.0, `stub = True`, `provides = {target, content}`,
`emits_spans = True`)

- `_run` returns `ModuleOutput(notes=["stub: detection not implemented"])`. Degrades every result.
- Effect: `result.target` is always `None` → every family-A hit resolves as `A1` (action `nudge`);
  `signals["m6_target"]` is `{}` → m1 never raises `NON_HUMAN_TARGET`; `B4` never scores.
- Fixture: two real items expecting nothing, one placeholder; one behaviour test skipped.

**UNCERTAIN**

- U-M6-1: two channels carry the same fact — `result.target` (a `TargetResult`, validated by
  `Pipeline._merge`: confidence in [0, 1], span inside text) and `signals.target_type` /
  `target_confidence` (raw, never validated). If m6 emits an invalid `target` (dropped, module
  degraded) but valid signals, m1 raises `NON_HUMAN_TARGET` while fusion resolves the target as
  `none`. Nothing checks they agree; no spec says which wins.
- U-M6-2: `family_a.target_min_confidence` (fusion) and `guards.NON_HUMAN_TARGET.threshold` (guard)
  are two placeholders applied to the same confidence; a value between them makes fusion ignore the
  target while m1's guard still suppresses.
- U-M6-3: the three ambiguity rules (`siz`, institution, religion) are still open (HANDOVER §5); the
  sports-club-supporters position is undecided.
- U-M6-4: `signals["target_type"]` is specified as a `TargetType` value; `pipeline.deep_freeze`
  deep-copies enum instances not in its allow-list (`ModuleName`, `ContentCode`, `FormCode`,
  `GuardCode`); m1 compares with `== "non_human"`, which works for a `str` enum, so the type
  mismatch is benign today but unpinned.

**Expected failure modes**

- A non-human target resolved as individual → "this program is terrible" becomes `A2` (review) or,
  as group, `A3` (block) — spec §7 lists this as the failure to avoid.
- A false `B4` on a public business address → escalates a benign post (action `escalate`).
- While a stub: every targeted insult is judged as untargeted (`A1`, `nudge`), see `OPEN_QUESTIONS.md` Q1.

---

## Decision layer contract (as the modules' consumer)

**SPECIFIED** (CLAUDE.md rule 4, `thresholds.yaml`, ADR-001, ADR-004, ADR-005, ADR-006,
`decision/fusion.py` docstring, `decision/actions.py` docstring)

Order: (0) reset decision-owned fields, assign A1/A2/A3 from the target; (1) thresholds per score,
signal-conditioned when configured; (2) guards as suppressors in `guards_order`, scoped per ADR-001;
(3) fuse channels/sources per code (`max`, fired-first); (4) form active codes; (5) thread rule on
offensive posts only; (6) verdict = most severe of fired codes' actions, `binary_offensive`, thread,
then fail-closed upgrade of `clean` to `review`.

**IMPLEMENTED** — `fusion.decide_post` (429–448) and `fusion.conclude` (451–460) do exactly that;
`actions.resolve` (58–76) and `actions.explain` (98–107) produce the verdict and the one-sentence
Turkish explanation. `validate_config` (45–106) fails at load on any malformed section.

**UNCERTAIN**

- U-DEC-1: `binary_offensive` is "not suppressible by guards" (yaml comment). Verified: with m6
  resolving `non_human` and m1's guard suppressing `A1`, the binary score still fires → `review`.
  The design "insult at a film → CLEAN + NON_HUMAN_TARGET" is reachable only when m3's binary score
  stays below 0.320188 on the same text.
- U-DEC-2: severity precedence makes `nudge` "more severe" than `clean`, so under degradation an
  `A1`-only post is **published with a warning** (`nudge`), not reviewed. Verified (probe A).
- U-DEC-3: `guards_order` credits the first active guard that applies; with `SUBSTRING_COLLISION`
  before `NON_HUMAN_TARGET`, explanations name the collision guard when both overlap the same span.

---

## Pipeline contract (as the modules' host)

See `PIPELINE_FLOW.md` §3 for the merge and validation rules. Summary of what a module can rely on:

- It is constructed once per `Pipeline`, `load()` is called once; a constructor or load failure
  makes it an `UnavailableModule` reported as degraded "failed" on every request.
- It receives a fresh `Context` per request with the deep-frozen signals of every module that ran
  before it (including failed ones, whose signals are `{}`).
- Its `charsafe_text` / `normalized_text` is only propagated if declared in `provides`.
- Each `ContentScore` / `GuardResult` is validated: correct dataclass and enum, finite score in
  [0, 1], span inside the original text, `source` naming this module (required for content,
  optional for guards / form), and a span present when `emits_spans` is `True` or undeclared. Any
  failure drops the item, adds a note and degrades the module (`invalid_output`).
- `stub = True` degrades the module on every request even when its output is valid.
