# Module map — AI pipeline (m0–m6, decision layer, pipeline, thread counter, API, eval)

Audit reconstruction, 2026-09-17. Branch `audit/m1-m6`, HEAD `f063ddf` (2026-09-16), working tree
dirty (see §7). Nothing in this document is a fix; it records what the specs say, what the code
does, and where the two cannot be reconciled from the repository alone.

Legend used throughout the four audit files:

- **SPECIFIED** — stated in `AI/modules/<m>/spec.md`, an ADR in `AI/protocols/`, `AI/CLAUDE.md`,
  `AI/docs/HANDOVER.md` or `AI/decision/thresholds.yaml`.
- **IMPLEMENTED** — what the code on this branch actually does, read from source and checked by
  running it (unit suite: 268 tests, 4 skipped, all pass; `python -m pipeline.contract_example --check`
  exit 0; `AI/contracts/` byte-identical to `master`).
- **UNCERTAIN** — behaviour the repository does not pin down, or where two sources disagree.

Sources read for this map: `README.md`, `AI/CLAUDE.md`, `AI/README.md`, `AI/CONTRIBUTING.md`,
`AI/modules/README.md`, `AI/docs/HANDOVER.md`, ADR-001…ADR-007, the three protocols under
`AI/protocols/`, `AI/eval/README.md`, `AI/artifacts/MANIFEST.md`, `docs/team/*`, the seven specs, the
seven `module.py`, `contracts/*.py`, `decision/*`, `pipeline/*`, `api/main.py`, `eval/*.py`,
every `test_unit.py` and `AI/tests/*.py`, the committed eval results, `diagnosis/README.md`,
`diagnosis/phases/12_threshold_policy.md`, `diagnosis/results/12_threshold_policy/metrics.json`,
`diagnosis/src/models.py` and `git log` / `git diff`.

---

## 1. One-line summary per module

| id | type | owner (docs/team) | SPECIFIED purpose | IMPLEMENTED status on this branch | version | `provides` | `emits_spans` | `stub` |
|---|---|---|---|---|---|---|---|---|
| m0_charsafe | representation | Musaab (reference) | Remove invisible characters, map homoglyphs and styled Latin, Turkish-aware lowercase; produce `charsafe_text` + form evidence | Fully implemented | 0.2.0 | `charsafe_text`, `form` | False | no |
| m2_deobf | representation | Mohammed | Parallel de-obfuscation channel (`normalized_text`) with one `FormPattern` per repair; two tiers; never replaces raw | **STUB** — returns one note | 0.0.0 | `normalized_text`, `form` | False | **yes** |
| m6_target | signal | Abdullah (v1) | Target resolution (individual / group / non_human / none) + doxing `B4` by regex + gazetteer; publishes `target_type` / `target_confidence` for m1 | **STUB** — returns one note | 0.0.0 | `target`, `content` | True | **yes** |
| m1_lexicon | signal | Musaab | Morpheme-boundary profanity match on raw **and** normalized channel; `A1` carrier + `A4`; guards `SUBSTRING_COLLISION`, `HOMONYM`, `NON_HUMAN_TARGET`; signals `lexicon_hit*` | Implemented on `terlik` 0.1.0 balanced: `A1` carrier, `SUBSTRING_COLLISION`, `NON_HUMAN_TARGET`, all three `lexicon_hit*` signals. **`A4` and `HOMONYM` not built.** | 0.1.0 | `content`, `guards` | True | no |
| m3_encoder | detection | Abdullah | One BERTurk encoder, three heads (A on the `A1` carrier, B multi-label, C1–C5), both channels, publishes `raw_score` / `norm_score` / `artifact` | **PARTIAL** — wraps the frozen epoch-1 binary OFF/NOT checkpoint; publishes `raw_score` + `artifact` only; **no heads, no content scores, no normalized channel** | 0.1.0 | `content` | False | no |
| m4_implicit | detection (owns thresholds, not a model) | Musaab | C1–C5 thresholds + `binary_offensive` threshold + lexicon-free slice repair (stage 1 / 1b / 2). Emits no content (ADR-006) | Non-stub by owner decision; returns one note `C1–C5 not implemented yet`; stage 1 integrated, stage 1b measured and rejected, stage 2 not started | 0.1.0 | `content` | False | no |
| m5_sarcasm | detection | Abdullah | `D1` degrading sarcasm, own small / distilled model (ADR-003), gated on a Turkish sarcasm corpus (spec §2) | **STUB** — returns one note; entry gate unresolved, corpus unnamed | 0.0.0 | `content` | False | **yes** |

Supporting components (not modules, but they own behaviour the modules depend on):

| component | file | role |
|---|---|---|
| Contracts | `AI/contracts/{codes,schema,module_api}.py` | Frozen enums, result dataclasses, `Context` / `ModuleOutput` / `BaseModule` |
| Registry | `AI/modules/registry.py` | `PIPELINE_ORDER`: the only place that knows module order |
| Pipeline | `AI/pipeline/run.py` | Constructs modules, builds a `Context` per module, validates and merges outputs, degrades, calls the decision layer, CLI |
| Thread counter | `AI/pipeline/thread_counter.py` | Axis-4 in-memory sliding window of OFFENSIVE posts per `(sender_id, target_id)` |
| Decision layer | `AI/decision/thresholds.yaml`, `fusion.py`, `actions.py` | The only code that compares scores with thresholds and picks an action |
| API | `AI/api/main.py` | stdlib HTTP: `POST /analyze`, `GET /health`, `/playground`, `/dene` |
| Eval | `AI/eval/harness.py`, `run_all.py`, `m4_stage1b.py`, `m1_lexicon_dev_labels.py`, `traps/`, `frozen/`, `derived/` | Per-module measurement, traps, pipeline budgets, protocol-driven derivations |

---

## 2. Module order

**SPECIFIED and IMPLEMENTED (identical):** `AI/modules/registry.py:40-48`

```
m0_charsafe → m2_deobf → m6_target → m1_lexicon → m3_encoder → m4_implicit → m5_sarcasm → decision layer
```

Order rationale, as written in the registry docstring and confirmed by the code paths:

1. **m0 first** — every later module may read `ctx.charsafe_text`; m1 also reads m0's internal `_offsets`.
2. **m2 before m1** — m1 scans the normalized channel, so it must exist first (m1 spec §3).
3. **m6 before m1** — m1 raises `NON_HUMAN_TARGET` from m6's published `target_type` / `target_confidence` (ADR-005). Pinned by `tests/test_architecture.py::test_m6_runs_before_m1`.
4. **m1 before m3** — m1 is the guard producer and the fast-path input (the fast path is disabled, so today this ordering only matters for `ctx.signals` availability, which m3 does not use).
5. **m3 before m4** — m4 is specified to read m3's published signals (it reads nothing today).
6. **m5 last** — independent of everything (own model; reads `ctx.text` only).

The `fast_path` (`thresholds.yaml`) would stop after `requires = [m0, m2, m1, m6]` have run; it is
**disabled** (`enabled: false`) until its margin is derived. The pipeline still evaluates
`fusion.fast_path_hit` after every module (`pipeline/run.py:270-276`); with `enabled: false` it
always returns `False`.

The decision layer is not a module. It runs after the loop in two stages (`decide_post`, then the
thread counter, then `conclude`) — see `PIPELINE_FLOW.md` §4.

---

## 3. Who reads whom — the dependency matrix

Modules never import each other (rule 2, enforced by `tests/test_architecture.py`). Every dependency
below is carried by the pipeline through `Context` (`contracts/module_api.py:34-58`): `text`,
`charsafe_text`, `normalized_text`, `signals` (deep-frozen mapping keyed by module name), `trace_id`.

| consumer | reads from `Context` | producer | SPECIFIED? | IMPLEMENTED? |
|---|---|---|---|---|
| m0 | `text` | caller | yes | yes |
| m2 | `charsafe_text` (fallback `text`) | m0 | yes (m2 spec §6) | stub reads nothing |
| m6 | `text` (raw: mentions and formatting matter) | caller | yes (m6 spec §6) | stub reads nothing |
| m1 | `best_text(RAW)` = `charsafe_text` or `text` | m0 | spec says `ctx.text`; code reads charsafe (U-M1-1 in `MODULE_CONTRACTS.md`) | yes (`m1/module.py:106`) |
| m1 | `normalized_text` | m2 | yes (m1 spec §3) | yes, only when not `None` (`m1/module.py:108-109`); today always `None` |
| m1 | `signals["m0_charsafe"]["_offsets"]` | m0 | not in m1 spec; ADR-001 "Consequences" says m0 publishes offsets for guard producers | yes (`m1/module.py:186-187`) |
| m1 | `signals["m6_target"]["target_type"]`, `["target_confidence"]` | m6 | yes (ADR-005, m1 spec §3, m6 spec §6) | yes (`m1/module.py:209-215`); today m6 publishes `{}` |
| m3 | `text`, `normalized_text` | caller, m2 | yes (m3 spec §4) | reads **`text` only** (`m3/module.py:103,106`); deliberately not charsafe, not normalized |
| m4 | `signals["m3_encoder"]["raw_score" / "norm_score" / "artifact"]` | m3 | yes (m4 spec §5, ADR-006) | reads nothing (`m4/module.py:36-37`) |
| m5 | `text` | caller | yes (m5 spec §7) | stub reads nothing |
| decision | `result.content`, `result.guards`, `result.target`, `result.form`, `result.thread`, `result.signals` (all modules + `pipeline`) | all | yes | yes (`decision/fusion.py:429-460`) |
| decision | `signals["m3_encoder"]["raw_score"]` (via `binary_offensive.channels.raw`) | m3 | yes (thresholds.yaml) | yes (`fusion.py:235-255`) |
| decision | `signals["m1_lexicon"]["lexicon_hit"]` (stage 1b `threshold_when`) | m1 | specified as a variant, **not in force** | machinery exists (`fusion.py:201-211`); no config entry uses it |
| thread counter | answer of `post_is_offensive` after `decide_post`; `thread.window_seconds` | decision layer, config | yes (ADR-004) | yes (`pipeline/run.py:291-298`) |

Signals every module publishes today (public keys, i.e. not `_`-prefixed), from a real run:

| module | `signals[<module>]` today |
|---|---|
| m0 | `offsets_identity`, `invisible_removed`, `homoglyphs_mapped`, `charsafe_changed` (+ internal `_offsets`, stripped from the response) |
| m2 | `{}` |
| m6 | `{}` |
| m1 | `lexicon_hit`, `lexicon_hit_raw`, `lexicon_hit_norm`, `matched_roots`, `engine` |
| m3 | `raw_score`, `artifact` |
| m4 | `{}` |
| m5 | `{}` |
| pipeline | `degraded` (list of `{module, kinds, reasons}`), `emits_spans` (map) |
| decision | `family_a`, `threshold_branches`, `binary_offensive`, `channel_scores`, `post_offensive` |

---

## 4. What each module writes into the contract (data transferred downstream)

| module | contract fields written (IMPLEMENTED) | scores / codes | spans | notes emitted |
|---|---|---|---|---|
| m0 | `charsafe_text`; `form.patterns` (`ZERO_WIDTH`, `HOMOGLYPH`, `DOTLESS_I`, confidences 0.05–0.95 as evidence strength); signals above | none | every pattern has a span into the original text | none |
| m2 | nothing | none | — | `stub: detection not implemented` |
| m6 | nothing | none | — | `stub: detection not implemented` |
| m1 | `content`: one `ContentScore(A1, 1.0, "m1_lexicon@raw" or "@normalized", span)` per distinct matched span; `guards`: `SUBSTRING_COLLISION` (1.0, source `m1_lexicon`, span of the colliding word, evidence text) and `NON_HUMAN_TARGET` (score = m6 confidence, one per A1 span); signals above | `A1` only; score is always `1.0` | required and always present on emitted items; items without a map to original offsets are **not emitted** | `<channel>: N match(es), M collision(s) without a map to original offsets; flag reported, no span items emitted` when spans cannot be produced; `m6_target target_confidence … is not a number` |
| m3 | signals `raw_score` (float p(OFF)), `artifact` (`m3-berturk-pytorch-fp32-epoch1`) | none | — | `truncated: N tokens, scored the first 128` |
| m4 | nothing | none | — | `C1–C5 not implemented yet` |
| m5 | nothing | none | — | `stub: detection not implemented` |

Decision-owned fields (`threshold`, `fired`, `active`, `suppressed`, `form.active`,
`thread.threshold` / `fired`) are **never** written by a module; if one does, the pipeline notes it
and `fusion.reset_decision_fields` clears it (`fusion.py:377-406`). Enforced statically by
`test_only_fusion_assigns_decision_owned_fields`.

---

## 5. Thresholds and actions that apply to each module's output (from `AI/decision/thresholds.yaml`)

`artifact.id = thresholds-v0.1.0`, `status: derived` — **derived covers `binary_offensive` only**;
every other number is a placeholder.

| output | threshold | action | status | applied where |
|---|---|---|---|---|
| m1 `A1` → resolved to `A1` / `A2` / `A3` from m6's target (`family_a.by_target`: none→A1, individual→A2, group→A3, non_human→A1; `target_min_confidence: 0.50`) | 0.50 each | A1 **nudge**, A2 **review**, A3 **block** | placeholder | `fusion.resolve_family_a` then `apply_thresholds` |
| m1 `A4` (not built) | 0.50 | review | placeholder | — |
| m3 B-head `B1,B2,B3,B5` (not built); m6 `B4` (not built) | 0.50 | B1 review, B2 escalate, B3 review, B4 escalate, B5 block | placeholder | — |
| m3 C-head `C1–C5` (not built; rows owned by the project owner) | 0.50 | C1 review, C2 review, C3 review, C4 escalate, C5 review | placeholder | — |
| m5 `D1` (not built) | 0.50 | nudge | placeholder | — |
| m3 `raw_score` (`binary_offensive`, raw channel only) | **0.320188** | review (placeholder policy) | **derived** (stage 1, r = 3, CAL half of the frozen dev split, artifact `m3-berturk-pytorch-fp32-epoch1`) | `fusion.apply_binary_offensive`; not suppressible by guards |
| m1 guard `SUBSTRING_COLLISION` | 0.50 | suppresses family `A` | placeholder | `fusion.apply_guards`, ADR-001 scoping |
| m1 guard `HOMONYM` (not built) | 0.50 | suppresses family `A` | placeholder | — |
| m1 guard `NON_HUMAN_TARGET` | 0.50 | suppresses `A1, A2, A3` | placeholder | — |
| form patterns (m0, m2) | `form.min_confidence: 0.50` | none (form never decides) | placeholder | `fusion.apply_form` → `form.active` |
| thread | `window_seconds: 600`, `min_repeats: 3`, `same_target_required: true`, `enabled: true` | escalate | placeholder | `fusion.apply_thread` (only on an offensive post) |
| fast path | `margin: 0.30`, `requires: [m0, m2, m1, m6]` | skip remaining modules | **disabled** | `fusion.fast_path_hit` |
| any degraded module | — | a would-be `clean` becomes **review** (`actions.DEGRADED_ACTION`) | policy | `actions.resolve` |

Budgets (also placeholders): `clean_to_dirty_flip_rate 0.01`; pipeline `latency_p95_ms 250`; per
module p95 ms — m0 `{64: 0.25, 280: 1, 1000: 4, 5000: 25}`, m1 `{64: 3, 280: 10, 1000: 30, 5000: 140}`,
m2 10, m3 80, m4 20, m5 20, m6 5.

---

## 6. Side effects, per component

| component | side effects (IMPLEMENTED) |
|---|---|
| m0 | none (pure) |
| m1 | `_load`: imports `terlik`, constructs `Terlik(TerlikOptions(mode="balanced"))`, warms the pattern cache (`get_matches("warmup")`), builds a folded root list; seconds on first construction. Pure afterwards. |
| m3 | `_load`: reads `AI/artifacts/m3_encoder/berturk_epoch1.pt` (442 MB) and the tokenizer dir (or `NSOSYAL_M3_CHECKPOINT` / `NSOSYAL_M3_TOKENIZER`), **sha256-hashes every file on every construction**, imports torch/transformers, builds BERT on CPU in FP32. No network (tested). Every `Pipeline()` — CLI, API start, each test that builds a default pipeline, `contract_example`, `run_all` — pays this. The unit suite takes about 53 s mostly for this reason. |
| m2, m4, m5, m6 | none |
| pipeline | keeps the `ThreadCounter` state in memory per `Pipeline` instance; nothing on disk |
| thread counter | in-memory dict `(sender_id, target_id) → sorted receive times`; sweeps quiet keys once per window; resets on restart |
| decision layer | mutates the `AnalysisResult` in place (recodes A1→A2/A3, sets decision-owned fields, replaces `result.content` with the fused list) |
| API | none beyond the pipeline; no auth, no TLS |
| eval harness | writes `AI/eval/results/<module>.json` (git-ignored except `m4_stage1b.json`, force-added under its protocol) |
| `eval.m1_lexicon_dev_labels` | reads the corpus and split under `diagnosis/data/` (not in git), writes `AI/eval/derived/m1_lexicon_dev_seed42.json` (1.1 MB, currently **untracked**) |
| `eval.m4_stage1b` | reads `diagnosis/results/01_baseline_berturk/dev_predictions.csv` (not in git), `cal_eval_split.json`, the frozen slice; runs m0 / m2 / m6 / m1 over 4,764 rows; writes `AI/eval/results/m4_stage1b.json` |

---

## 7. State of the working tree at audit time

`git status` (uncommitted, not part of HEAD `f063ddf`):

- `M AI/docs/HANDOVER.md` — adds the m1 "implemented" bullet, renames the contract owner Osama→Musaab in §4; **still lists m3 among the stubs in §2** (stale against `m3/module.py` 0.1.0).
- `M AI/eval/traps/traps.jsonl` — traps 024–033 added (inflected / uppercase collision words). The committed eval results for m2–m6 were produced against the 23-trap file; the m0 / m1 results against the 33-trap file.
- `M AI/modules/m1_lexicon/fixtures/cases.jsonl` — six long clean / adversarial items (280 / 1000 / 5000 chars) for the per-length latency bands.
- `M AI/modules/m1_lexicon/spec.md` — §1 gains the "two lexicon files, never merged" table.
- `M AI/modules/m2_deobf/spec.md` — a `---` horizontal rule became `--` (looks accidental).
- `?? AI/eval/derived/m1_lexicon_dev_seed42.json`, `?? AI/eval/m1_lexicon_dev_labels.py`, `?? AI/protocols/m1_lexicon_dev_labels_protocol.md` — the derived-labels protocol, script and output. The derived file's header records `protocol.commit: null` and `committed_and_unchanged: false`, i.e. it was generated before its protocol was committed; the protocol itself says the file is committed only after the protocol, in a later commit.

`AI/contracts/` is unchanged against both HEAD and `master`.
