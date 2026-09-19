# Pipeline flow — how one post travels from text to verdict

Audit reconstruction, 2026-09-17, branch `audit/m1-m6` at `f063ddf` plus the uncommitted working
tree. Line numbers refer to files under `AI/`. Everything in §1–§7 is IMPLEMENTED behaviour read
from the code and confirmed by running it; SPECIFIED-only steps are marked; UNCERTAIN points are
tagged `U-FLOW-<n>` and collected in `OPEN_QUESTIONS.md`.

---

## 1. Startup (once per process)

`Pipeline.__init__` (`pipeline/run.py:198-216`):

1. Load and validate `decision/thresholds.yaml` (`fusion.load_config` → `validate_config`). A
   malformed config raises at startup — by design, loudly.
2. `build_modules_safely(registry.PIPELINE_ORDER)` (109–125): for each enabled entry, import the
   class by dotted path, construct it, call `load()`. A constructor or load exception is caught and
   the slot is filled with an `UnavailableModule` (92–106) that reports `ok=False` with the error
   on every request. Today this is where m1 imports terlik and m3 hashes and loads BERT.
3. `artifact_hash = sha256(canonical JSON of the in-memory config) + "|name:version"` for every
   module (65–74). It changes when any threshold, action, budget or module version changes.
4. A `ThreadCounter(config["thread"])` is created per `Pipeline` (in memory, resets on restart).

Entry points that build a `Pipeline`: `python -m pipeline.run` (CLI), `api.main` (HTTP),
`pipeline.contract_example`, `eval.harness.pipeline_budget_report`, `eval.m4_stage1b`,
`eval.m1_lexicon_dev_labels`, and the tests. The per-module harness constructs one module only
(`registry.build`).

---

## 2. Per request — the module loop

`Pipeline.analyze(text, thread=None, trace_id=None, thread_block=None)` (218–304):

```
received_at = counter.now()      # only when a thread_block is given (ADR-004: server receive time)
result = AnalysisResult(text, thread, trace_id or uuid4, artifact_hash)
charsafe_text = None; normalized_text = None; signals = {}; degraded = {}

for every module with stub == True: degrade(module, "stub", "stub: no detection logic yet")

for module in modules (registry order):
    ctx = Context(text, charsafe_text, normalized_text, deep_freeze(signals), trace_id)
    out = safe_process(module, ctx)              # never raises; ok=False + note on any failure
    if not out.ok: degrade(module, "failed", notes)
    for problem in _merge(result, out, module): degrade(module, "invalid_output", problem)
    if "charsafe_text" in provides and out.charsafe_text is not None: charsafe_text = out.charsafe_text
    if "normalized_text" in provides and out.normalized_text is not None: normalized_text = out.normalized_text
    signals[module] = out.signals                # even when ok=False ({} then)
    if remaining modules and fast_path.requires ⊆ ran and fast_path_hit(...): note + break   # disabled today
```

What each module sees today (IMPLEMENTED, from a real run):

| step | module | `charsafe_text` seen | `normalized_text` seen | `signals` keys seen |
|---|---|---|---|---|
| 1 | m0 | `None` | `None` | `{}` |
| 2 | m2 | m0 output | `None` | `m0_charsafe` |
| 3 | m6 | m0 output | `None` (m2 stub) | `m0_charsafe`, `m2_deobf` |
| 4 | m1 | m0 output | `None` | + `m6_target` (`{}`) |
| 5 | m3 | m0 output (ignored) | `None` (ignored) | + `m1_lexicon` |
| 6 | m4 | m0 output | `None` | + `m3_encoder` |
| 7 | m5 | m0 output | `None` | + `m4_implicit` |

`deep_freeze` (77–89) gives each module a read-only deep copy: a module can neither mutate another
module's payload nor observe later mutations by the producer (`test_module_cannot_mutate_another_modules_signals`).

---

## 3. Merge and validation of one module's output

`Pipeline._merge` (306–422) — every rule below drops the offending item, appends a
`[pipeline] <module>: dropped …` note and marks the module degraded with kind `invalid_output`:

| check | applies to | rule |
|---|---|---|
| `notes` is a list, `signals` is a dict | all | replaced by `[]` / `{}` if not |
| undeclared fields | all | `populated_fields() − provides` → dropped (rule 5) |
| text fields are `str` | `charsafe_text`, `normalized_text` | else dropped |
| form patterns | `form` | must be `FormPattern` with a `FormCode`; confidence finite in [0, 1]; span inside text; `source` empty or this module |
| `form.active` set by a module | `form` | not merged; note only |
| content scores | `content` | must be `ContentScore` with a `ContentCode`; score finite in [0, 1] (NaN / None / 1.5 / −0.2 are errors, never clean); span inside text; `source` **required** and must name this module; **span required** when `emits_spans` is `True` or undeclared |
| guards | `guards` | same as content except `source` optional (defaults to the module name) |
| target | `target` | `TargetResult` with a `TargetType`; confidence in [0, 1]; span inside text; a second module's target overrides the first with a note |
| thread | `thread` | `ThreadSignal` with int `repeat_count` |
| decision-owned fields set by a module | content, guards, thread | note only; `fusion.reset_decision_fields` clears them later |

Any `ok=False` or any dropped item adds `[pipeline] <module> failed or returned invalid output; result is degraded`.

Degradation kinds (`DEGRADED_STUB`, `DEGRADED_FAILED`, `DEGRADED_INVALID`) accumulate per module in
`signals.pipeline.degraded = [{module, kinds, reasons}]`; a construction / load failure shows as
`failed` with the exception text.

---

## 4. After the loop — response shaping, then the decision layer

1. `result.signals[module] = public_signals(out.signals)` — keys starting with `_` (m0's `_offsets`)
   are stripped so the response does not grow with the post (278–281). No copy of
   `charsafe_text` / `normalized_text` goes into the response (HANDOVER #21).
2. `result.signals["pipeline"] = {"degraded": [...], "emits_spans": {module: bool}}`.
3. If anything is degraded, a `[pipeline] DEGRADED - judgement incomplete, clean is not reachable: …`
   note is inserted first.
4. Decision, wrapped in one `try` (290–302): any exception → `verdict = None`, explanation
   `"Karar verilemedi: karar katmanında bir hata oluştu…"`, note with the exception.

### 4.1 `fusion.decide_post` (429–448) — steps 0–4

| step | function | what happens | writes |
|---|---|---|---|
| 0a | `reset_decision_fields` (377–406) | clears `threshold` / `fired` on every content score, `threshold` / `active` / `suppressed` on every guard, `form.active`, `thread.threshold` / `fired`; one note per offending source | `notes` |
| 0b | `resolve_family_a` (128–139) | if any score is A1 / A2 / A3: pick the post's A code from `result.target` — target `None` or confidence `< family_a.target_min_confidence` → `none`; then `by_target[none→A1, individual→A2, group→A3, non_human→A1]`; **recodes every A1 / A2 / A3 score in place** (a module that emitted A2 / A3 gets a note) | `signals.decision.family_a` (or `None` when no A score) |
| 1 | `apply_thresholds` (215–232) | per non-CLEAN score: `threshold = categories[code].threshold` (or the `threshold_when` branch resolved from a bool signal, scalar fallback with a note); `fired = score >= threshold`; a code missing from config never fires (note) | `score.threshold`, `score.fired`, `signals.decision.threshold_branches` |
| 1b | `apply_binary_offensive` (235–255) | for each configured channel path (`raw: m3_encoder.raw_score`), read the signal; non-numeric → `{score: None, fired: None}`; `fired = value >= 0.320188`; overall `fired = any(present channels)` or `None` when no channel present | `signals.decision.binary_offensive = {threshold, branch, signal, signal_value, channels, fired, action}` |
| 2 | `apply_guards` (304–330) | every guard gets `threshold` and `active = score >= guards[code].threshold` (unknown guard code → inactive + note). Then in `guards_order` (SUBSTRING_COLLISION, HOMONYM, NON_HUMAN_TARGET), for each **fired** score the first active guard for which `guard_applies` holds sets `fired = False`, records the code in `guard.suppressed`, notes it | `guard.threshold/active/suppressed`, `score.fired`, notes |
| — | `guard_applies` (283–301) | same module (`module_of(source)`); guard's `suppresses` covers the code or its family; both spans present → must overlap; a missing span → suppress only if `signals.pipeline.emits_spans[module]` is `False` (ADR-001 fallback); a guard with empty `source` never applies | — |
| 2' | audit | `signals.decision.channel_scores` = every pre-fusion score with span / threshold / fired | signals |
| 3 | `fuse_channels` (143–162) | one score per code: the highest **fired** score if any fired, else the highest overall; `source` and `span` of the winner kept; `fired = bool(any fired)` | `result.content` replaced |
| 4 | `apply_form` (259–261) | `form.active` = codes whose best confidence `>= form.min_confidence` | `form.active` |
| 4' | `post_is_offensive` (420–426) | `bool(result.fired()) or binary.fired` | `signals.decision.post_offensive` |

### 4.2 Thread counting (only with a `thread_block`)

`result.thread = counter.observe(block, received_at, post_is_offensive(result))` (`run.py:292-297`;
`thread_counter.py:94-115`): self-directed (`sender_id == target_id`) → never recorded,
`repeat_count 0`, note; else if offensive, insert `received_at` into the key's sorted list;
`repeat_count` = events in `(received_at − window_seconds, received_at]`, this post included when
counted; posts received later are not this post's history. `same_target = True` always (the key
includes the target), `window_posts = 0` always, `source = "pipeline.thread_counter"`.

### 4.3 `fusion.conclude` (451–460) — step 5 and the verdict

| step | function | what happens |
|---|---|---|
| 5 | `apply_thread` (334–347) | `thread.threshold = min_repeats (3)`; `fired = enabled and post_offensive and repeat_count >= 3 and (same_target or not same_target_required)` |
| 6 | `actions.resolve` (58–76) | verdict starts `clean`; for fired content scores (highest score first) take the more severe configured action; then `binary_offensive.action` (`review`) if it fired; then `thread.action` (`escalate`) if the thread rule fired; finally, if the verdict is still `clean` and anything is degraded → `review` (driver `"degraded"`) |
| 6' | `actions.explain` (98–107) | one Turkish sentence: degraded-driver form `"Karar verilemedi, içerik temiz sayılmadı ve incelemeye alındı: değerlendirme eksik çünkü …"`; otherwise the base sentence (`… nedeniyle engellendi / üst incelemeye iletildi / incelemeye alındı / kullanıcı uyarılarak yayımlandı`, or the suppression sentence, or `"İçerikte eşiği aşan saldırgan bir kategori bulunmadı"`) with `"; ancak değerlendirme eksik çünkü …"` appended when degraded |

Severity order (`ACTION_PRECEDENCE`): block > escalate > review > nudge > clean.

`result.latency_ms` is stamped last; `per_module_ms` was filled during the loop.

---

## 5. Entry points and what they pass in

| entry | inputs | thread support | notes |
|---|---|---|---|
| CLI `python -m pipeline.run "t1" ["t2" …] [--compact] [--trace-id ID] [--thread JSON]` | texts in order | yes: `ThreadBlock.from_dict` rejects unknown keys (a `timestamp` is refused, ADR-004) and empty ids; all texts share the block | prints one object or a JSON array |
| HTTP `POST /analyze {"text", "trace_id"?}` (`api/main.py`) | `text` (str), optional `trace_id` (str) | **no** (HANDOVER #38: waits for `docs/frontend/02_BACKEND_SPEC.md`) | 400 on bad JSON / types / Content-Length, 413 over 64 KiB, 500 with the exception type; `/health` returns `artifact_hash`; `/playground` and `/dene` are static pages |
| `Pipeline.analyze(text, thread=ThreadSignal)` | a ready `ThreadSignal` | used by tests / harness | `thread` and `thread_block` are mutually exclusive |

---

## 6. Evaluation flow (how the numbers are produced)

### 6.1 Per-module harness (`eval/harness.py::ModuleEvaluator`)

For each fixture item: build a `Context` from `text` and the optional `context` block
(`charsafe_text`, `normalized_text`, `signals`), call `safe_process` once (scored run) plus
`latency_repeats` timed runs, then `Pipeline._merge` into a fresh `AnalysisResult`, copy the
fixture's `context.signals` and the module's own signals into `result.signals`, set
`signals.pipeline.emits_spans` (no `degraded` key), and run `fusion.decide`. Predicted codes =
fired content codes ∪ `form.active` ∪ active guard codes ∪ `target:<type>`. Metrics are per code
over the fixed `code_space(module)` (derived from `provides`), with percentile-bootstrap CIs;
representation modules also get capture rate per pattern and damage rate on clean items; latency
is reported in `clean` and `adversarial` columns with the per-length bands from the config, and
`within_budget` reads the clean column only.

Consequences worth knowing:

- A stub is never "degraded" in the harness, so its clean fixture item counts as a true negative and
  its result file looks healthy (`m2`, `m5`, `m6` results: zero support everywhere, traps 0/23).
- Traps (`check_traps`, 384–422): `must_not_fire` is evaluated on `result.fired()` (content only),
  `expect` on raw module output fields, `form` / `guards` `must` / `must_not` on the codes the
  listed module **emitted** (before thresholds). A `must` a stub cannot meet is `pending`.
  `binary_offensive` is never checked by a trap (U-FLOW-3).

### 6.2 Pipeline budgets (`pipeline_budget_report`, `eval/run_all.py`)

Flip rate: run every trap through the full pipeline with m2 replaced by `NoNormalizedChannel` and
with the real m2; a trap counts as flipped when only the with-channel run has a fired content
code. Latency: the whole pipeline over every trap and fixture text, `runs` repeats. Exit 1 on any
trap regression or a budget breach. Last committed run (`eval/results/pipeline.json`): flip rate
0.0 over 23 traps; p95 128.6 ms over 85 texts × 200 (budget 250).

### 6.3 Protocol-driven derivations

- `eval.m4_stage1b` (runs `protocols/m4_stage1b_protocol.md`): hashes its inputs, refits stage 1
  on CAL and requires `t = 0.320188` and the recorded EVAL confusion, computes m1's
  `lexicon_hit_raw` for all 4,764 dev rows through a four-module pipeline (m0, m2, m6, m1), fits
  `t_hit` / `t_free` at stage 1's CAL flag count, evaluates on EVAL, paired bootstrap, decides by the
  pre-registered rule. Result: `KEEP stage 1`.
- `eval.m1_lexicon_dev_labels` (runs `protocols/m1_lexicon_dev_labels_protocol.md`): same
  four-module pipeline over the dev split, seven integrity checks, two generations must be
  byte-identical, writes the regenerable derived-labels file.

### 6.4 Gates (`scripts/check.sh`)

unit + architecture tests → pipeline smoke → `eval.run_all` (traps, CIs, latency, budgets) →
`contract_example --check` (both examples must regenerate byte-identically; the analysis example
embeds a real m3 `raw_score`, so the gate needs the m3 artifact) → `git diff` of `AI/contracts/`
against `BASE_REF` (default `origin/master`; fails when the ref is missing).

---

## 7. Observed behaviour on this branch (real runs, 2026-09-17)

Full pipeline, default config, m3 artifact present:

| input | m1 | m3 `raw_score` | binary fired | fused content | guards | verdict | explanation driver |
|---|---|---|---|---|---|---|---|
| `Bu bir test cumlesi` | no hit | 0.021 | no | — | — | **review** | degraded (m2, m6, m5 stubs) |
| `Onlar aptallar` | A1 `[6,14]` | 0.866 | yes | A1 fired (→ A1, no target) | — | **review** | binary_offensive; "ancak değerlendirme eksik" |
| `Sen bir gerizekalısın, amcam da öyle` | A1 `[8,21]` | 0.973 | yes | A1 fired | SUBSTRING_COLLISION `[23,28]` active, suppresses nothing (no overlap) | **review** | binary_offensive |
| `ap​tal herif` | A1 `[0,6]` (through m0 offsets) | 0.969 (model saw the ZWSP) | yes | A1 fired | — | **review** | binary_offensive; `form.active = [ZERO_WIDTH]` |
| `SIKINTI YOK` | no hit; collision on `SIKINTI` | 0.045 | no | — | SUBSTRING_COLLISION `[0,7]` active | **review** | degraded; `DOTLESS_I` at 0.10 not active |
| `Seni bitireceğim, evini biliyorum` (threat, no profanity) | no hit | 0.017 | no | — | — | **review** | degraded — the B2 content is invisible to today's system |

Thread path (`ThreadBlock("u1","u2","t1")`, window 600 s, `min_repeats 3`): three `Onlar aptallar`
posts give `repeat_count` 1, 2, 3 and the third is **escalate** ("Aynı gönderenin aynı hedefe
yönelik 3 saldırgan mesajı …; ancak değerlendirme eksik …"); a following `Bu bir test cumlesi`
reports `repeat_count 3`, `fired False`, verdict review (degraded).

Decision layer alone (no model; `AnalysisResult` built by hand, default config):

| probe | setup | verdict | note |
|---|---|---|---|
| A | m1 A1 hit, `raw_score 0.10`, m6 degraded | **nudge** — "kullanıcı uyarılarak yayımlandı; ancak değerlendirme eksik" | U-DEC-2 |
| B | as A but `raw_score 0.90` | review (binary) | |
| C | m6 `non_human` 0.9, m1 A1 + `NON_HUMAN_TARGET` guard, `raw_score 0.10`, nothing degraded | **clean** — A1 suppressed | the ADR-005 design case |
| D | as C but `raw_score 0.90` | **review** (binary) — A1 still suppressed | U-DEC-1 |
| E | m6 `individual` 0.9, m1 A1 | review (A2) | |
| F | m6 `group` 0.9, m1 A1 | **block** (A3) | |
| G | m1 A1 and a same-span `SUBSTRING_COLLISION` from m1 | clean — A1 suppressed | U-M1-6 |

---

## 8. State transferred between components — the complete list

| from → to | carrier | content |
|---|---|---|
| caller → pipeline | `analyze()` args | `text`, optional `trace_id`, optional `ThreadBlock(sender_id, target_id, thread_id)` or `ThreadSignal` |
| m0 → m2, m6, m1 (m3, m4, m5 receive but ignore) | `Context.charsafe_text` | cleaned, Turkish-lowercased text |
| m0 → m1 | `Context.signals.m0_charsafe._offsets` | original index of each charsafe character |
| m0 → decision / response | `form.patterns`; public signals | evidence of ZERO_WIDTH / HOMOGLYPH / DOTLESS_I with spans; counters |
| m2 → m1, m3 (specified; nothing today) | `Context.normalized_text`, `form.patterns` | parallel channel text and repair evidence |
| m6 → m1 (specified; `{}` today) | `Context.signals.m6_target.{target_type,target_confidence}` | the resolved target |
| m6 → decision (specified; `None` today) | `result.target` | `TargetResult` used to assign A1 / A2 / A3 |
| m6 → decision (specified; nothing today) | `content` `B4` with span | doxing |
| m1 → decision | `content` `A1@raw` / `@normalized` (score 1.0, span); `guards` SUBSTRING_COLLISION / NON_HUMAN_TARGET (span) | profanity carrier and its negative controls |
| m1 → decision (stage 1b, not in force), → derived labels, → m4 protocol | `signals.m1_lexicon.{lexicon_hit, lexicon_hit_raw, lexicon_hit_norm, matched_roots, engine}` | lexicon signal |
| m3 → decision | `signals.m3_encoder.raw_score` | p(OFF) thresholded as `binary_offensive` |
| m3 → response | `signals.m3_encoder.artifact` | artifact id for reproducibility |
| m3 → m4 (specified; unused) | `signals.m3_encoder.*` | |
| m3 → decision (specified; nothing today) | `content` A1 carrier, B1–B3 / B5, C1–C5 per channel | |
| m5 → decision (specified; nothing today) | `content` `D1` | |
| every module → response | `notes`, `per_module_ms`, public `signals` | audit trail |
| pipeline → decision | `signals.pipeline.{degraded, emits_spans}` | fail-closed input and ADR-001 fallback control |
| decision → pipeline → counter | `post_is_offensive(result)` | whether this post counts as a repeat |
| counter → decision | `result.thread` (`ThreadSignal(repeat_count, same_target=True, thread_id, source)`) | window history |
| decision → response | `verdict`, `explanation`, decision-owned fields, `signals.decision.*`, fused `content` | |

---

## 9. End-to-end failure modes (IMPLEMENTED unless marked)

| situation | what the system does | evidence |
|---|---|---|
| any module is a stub (m2, m6, m5 today) | listed in `signals.pipeline.degraded`; a would-be clean verdict becomes review; explanation says which modules are unfinished | every run in §7 |
| a module's constructor or `load` raises (e.g. terlik not installed, m3 artifact missing or hash mismatch) | `UnavailableModule`, degraded `failed` on every request; the rest of the pipeline runs | `test_module_construction_failure_does_not_crash`, `test_missing_artifact_fails_closed` |
| a module's `_run` raises | `ok=False` with `ExceptionType: message (file:line)`; degraded `failed` | `test_failing_module_degrades_not_aborts` |
| a module returns garbage (wrong type, NaN, out-of-range, bad span, foreign `source`, undeclared field, spanless item from a span-emitting module) | item dropped with a note; degraded `invalid_output` | `RobustnessTest`, `SpanEnforcementTest` |
| a module sets decision-owned fields | note; reset by fusion; the same answer on a second `decide` | `test_direct_caller_preset_fields_are_reset` |
| the decision layer raises (broken config injected after validation) | `verdict = None`, "Karar verilemedi: karar katmanında bir hata oluştu" | `test_decision_failure_does_not_crash` |
| a module mutates `ctx.signals` | `TypeError` inside the module → its own failure; the producer's payload is untouched | `test_module_cannot_mutate_another_modules_signals` |
| the caller sends a thread `timestamp` | CLI usage error (exit 2) | `test_caller_supplied_time_is_refused` |
| API bad body / oversize / handler exception | 400 / 413 / 500 JSON; the connection is never dropped | `tests/test_api.py` |
| post longer than 128 BERTurk tokens | m3 scores the first 128 tokens and notes it; m1 scans everything | `test_truncation_is_noted` |
| **content in families B, C, D, or A4** | no module produces the code; only m3's binary score can react, as `review` (SPECIFIED gap, IMPLEMENTED consequence) | §7 threat example |
| **invisible characters / homoglyphs in the post** | m0 cleans them for m1 and m2; **m3 scores the raw post** (U-M3-2) | §7 `ap​tal` example |
| **profanity aimed at an object while m3 also flags the post** | m1's `NON_HUMAN_TARGET` suppresses the A code, the binary score still yields review (U-DEC-1) | probe D |
| **profanity while m6 is degraded** | assigned A1 → `nudge` (published with a warning) unless the binary score fires (U-DEC-2) | probe A |
| a lexicon hit on the normalized channel with a length-changing repair (future m2) | flag only; no score, no fired code (U-M1-2) | `test_normalized_channel_without_offset_map_reports_flag_only` |
| restart of the process | all thread history lost (ADR-004 demo scope) | `test_state_is_per_instance_so_a_restart_starts_empty` |
