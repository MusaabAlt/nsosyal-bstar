**Assistant: before anything else, read `AI/CLAUDE.md`, `AI/modules/README.md`, `AI/contracts/schema.py` and `AI/contracts/codes.py`. This brief is NOT the source of truth: it was written from the repo at commit `6583e5c`, and wherever the code and this brief disagree, the code wins.**

# Amin — technical brief

You own `frontend/`, `backend/` (both empty scaffolds today) and `AI/api/`, whose tests live in `AI/tests/test_api.py`. This brief covers the response you render, the API you own, what the screen must show, the states it must handle, the rules it may not break, payloads to build against today, and how your work is accepted.

---

## 1. The frozen response contract

`POST /analyze` returns `AnalysisResult.to_dict()` from `AI/contracts/schema.py`. Dataclasses become JSON objects, enums become their string **value**, and spans (`tuple[int, int]`) become `[start, end]` lists.

### 1.1 `AnalysisResult` — top level

| field | JSON type | filled by | meaning |
|---|---|---|---|
| `text` | string | pipeline | the original input, unchanged |
| `verdict` | `Action` value or `null` | decision layer | `null` only when the decision layer itself failed |
| `form` | `FormResult` | modules + decision layer | obfuscation patterns observed (Axis 2) |
| `content` | list of `ContentScore` | modules + decision layer | one entry per content code **after channel fusion**: the highest fired score for that code, else the highest score, with its `source` and `span` (`decision/fusion.py` `fuse_channels`) |
| `target` | `TargetResult` or `null` | m6 | who is being hit (Axis 3) |
| `guards` | list of `GuardResult` | modules + decision layer | negative controls |
| `thread` | `ThreadSignal` or `null` | pipeline counter | `null` unless a thread block was passed; the API does not accept one today |
| `signals` | object | pipeline, modules, decision layer | typed `dict[str, Any]`, **not frozen**; see 1.3 |
| `explanation` | string | decision layer | exactly one Turkish sentence (`decision/actions.py` `explain`) |
| `latency_ms` | number | pipeline | whole analysis, milliseconds |
| `per_module_ms` | object | pipeline | module name → milliseconds |
| `fast_path` | boolean | pipeline | true when later modules were skipped (`fast_path.enabled: false` in `thresholds.yaml` today) |
| `trace_id` | string | pipeline | the caller's `trace_id`, or a generated one |
| `artifact_hash` | string | pipeline | sha256 over the decision config in use and every module name:version |
| `notes` | list of strings | everyone | English diagnostic lines prefixed `[module]`, `[pipeline]`, `[decision]`. Not screen text |

### 1.2 Nested objects

"Decision layer only" fields are set by `decision/fusion.py` and nowhere else. A module never sets them; the UI only reads them.

| object | field | JSON type | filled by |
|---|---|---|---|
| `FormResult` | `patterns` | list of `FormPattern` | modules |
| | `active` | list of `FormCode` values | decision layer only: codes whose confidence reaches `form.min_confidence` |
| `FormPattern` | `code` | `FormCode` value | module |
| | `confidence` | number in [0, 1] | module |
| | `evidence` | string | module |
| | `span` | `[start, end]` or `null` | module |
| | `source` | string, module name | module |
| `ContentScore` | `code` | `ContentCode` value | module |
| | `score` | number in [0, 1] | module |
| | `source` | `"<module>@raw"` or `"<module>@normalized"` | module |
| | `span` | `[start, end]` or `null` | module (`null` for whole-post scores: m3, m5) |
| | `threshold` | number or `null` | decision layer only |
| | `fired` | boolean or `null` | decision layer only; `null` = not decided |
| `TargetResult` | `type` | `TargetType` value | module |
| | `confidence` | number in [0, 1] | module |
| | `evidence` | string | module |
| | `span` | `[start, end]` or `null` | module |
| | `source` | string | module |
| `GuardResult` | `code` | `GuardCode` value | module |
| | `score` | number in [0, 1] | module |
| | `source` | string | module |
| | `evidence` | string | module |
| | `span` | `[start, end]` or `null` | module |
| | `threshold` | number or `null` | decision layer only |
| | `active` | boolean or `null` | decision layer only |
| | `suppressed` | list of `ContentCode` values | decision layer only |
| `ThreadSignal` | `thread_id` | string or `null` | pipeline |
| | `repeat_count` | integer | pipeline |
| | `window_posts` | integer | pipeline |
| | `same_target` | boolean or `null` | pipeline |
| | `source` | string | pipeline |
| | `threshold` | integer or `null` | decision layer only |
| | `fired` | boolean or `null` | decision layer only |

**Spans** are `[start, end)` offsets into the ORIGINAL `text` (`schema.py` docstring), counted in Python string indices, which are Unicode code points. JavaScript string indices are UTF-16 code units, so for any text containing an emoji or another character outside the Basic Multilingual Plane, `text.slice(start, end)` highlights the wrong characters. Convert the offsets (for example with `Array.from(text)`) before slicing.

### 1.3 `signals` — what the code produces today

The contract types `signals` as `dict[str, Any]`. The keys below are what `pipeline/run.py` and `decision/fusion.py` produce at the commit above. They are not a frozen promise, so agree with Musaab before depending on one.

| key | shape | meaning |
|---|---|---|
| `signals.<module name>` | object | that module's published signals; keys starting with `_` never reach the response |
| `signals.pipeline.degraded` | list of `{module, kinds, reasons}` | every module that is a stub, failed, or returned invalid output. `kinds` values: `stub`, `failed`, `invalid_output` |
| `signals.pipeline.emits_spans` | object, module → boolean | whether that module's scores and guards must carry spans |
| `signals.decision.family_a` | object or `null` | how A1/A2/A3 was assigned from the target (ADR-005) |
| `signals.decision.threshold_branches` | list of `{code, source, threshold, branch, signal, signal_value}` | which threshold applied to each score, and why |
| `signals.decision.binary_offensive` | `{threshold, branch, signal, signal_value, channels: {raw: {score, fired}, normalized: {score, fired}}, fired, action}` | m3's channel-level binary offensive score and its decision |
| `signals.decision.channel_scores` | list of `ContentScore` objects | every score per channel **before** fusion: the raw and the normalized reading of the same code, side by side |
| `signals.decision.post_offensive` | boolean | whether this post counts as offensive for the repetition counter |

### 1.4 Enum values (`AI/contracts/codes.py`)

| enum | values |
|---|---|
| `ContentCode` | `A1`, `A2`, `A3`, `A4`, `B1`, `B2`, `B3`, `B4`, `B5`, `C1`, `C2`, `C3`, `C4`, `C5`, `D1`, `CLEAN` |
| `FormCode` | `LEET`, `SPACED`, `PUNCT_SPLIT`, `REPEAT`, `CHAR_DROP`, `WORD_MERGE`, `ABBREV`, `DEASCII`, `DOTLESS_I`, `VOWEL_DROP`, `SUFFIX_ON_MASKED`, `DIALECT`, `HOMOGLYPH`, `ZERO_WIDTH`, `EMOJI_SUB`, `PHONETIC` |
| `GuardCode` | `SUBSTRING_COLLISION`, `NEGATION`, `QUOTE_COUNTERSPEECH`, `METADISCUSSION`, `SELF_DIRECTED`, `FRIENDLY_BANTER`, `DUAL_REGISTER`, `HOMONYM`, `NON_HUMAN_TARGET` |
| `TargetType` | `individual`, `group`, `non_human`, `none` |
| `Level` | `post`, `thread` |
| `Action` | `block`, `escalate`, `review`, `nudge`, `clean` |
| `ModuleName` | `m0_charsafe`, `m1_lexicon`, `m2_deobf`, `m3_encoder`, `m4_implicit`, `m5_sarcasm`, `m6_target` |
| `Family` | `A`, `B`, `C`, `D`, `CLEAN` |

When several actions apply, the most severe wins, in `ACTION_PRECEDENCE` order: `block` > `escalate` > `review` > `nudge` > `clean`.

A content code's family is its first letter (`FAMILY` in `codes.py`): A explicit profanity, B non-lexical abuse, C implicit, D degrading sarcasm; `CLEAN` is its own family.

### 1.5 Turkish labels (`TR_LABELS` in `AI/contracts/codes.py`)

| enum | value | Turkish label |
|---|---|---|
| `ContentCode` | `A1` | Hedefsiz küfür |
| `ContentCode` | `A2` | Bireye yönelik küfür |
| `ContentCode` | `A3` | Gruba yönelik küfür |
| `ContentCode` | `A4` | Kutsal değerlere yönelik küfür |
| `ContentCode` | `B1` | Aşağılama |
| `ContentCode` | `B2` | Tehdit |
| `ContentCode` | `B3` | Lanetleme / dışlama |
| `ContentCode` | `B4` | Kişisel bilgi ifşası (doxing) |
| `ContentCode` | `B5` | Cinsel saldırganlık |
| `ContentCode` | `C1` | Kalıp yargı |
| `ContentCode` | `C2` | Aşağılık atfetme |
| `ContentCode` | `C3` | Kodlu dil |
| `ContentCode` | `C4` | Kışkırtma |
| `ContentCode` | `C5` | Karalama / iftira |
| `ContentCode` | `D1` | Aşağılayıcı alay |
| `ContentCode` | `CLEAN` | Temiz |
| `Family` | `A` | Açık küfür |
| `Family` | `B` | Sözcük dışı saldırganlık |
| `Family` | `C` | Örtük saldırganlık |
| `Family` | `D` | Aşağılayıcı ironi |
| `Family` | `CLEAN` | Temiz |
| `FormCode` | `LEET` | Rakam/sembol ikamesi |
| `FormCode` | `SPACED` | Harf arası boşluk |
| `FormCode` | `PUNCT_SPLIT` | Noktalama ile bölme |
| `FormCode` | `REPEAT` | Harf tekrarı |
| `FormCode` | `CHAR_DROP` | Harf düşürme |
| `FormCode` | `WORD_MERGE` | Sözcük birleştirme |
| `FormCode` | `ABBREV` | Kısaltma |
| `FormCode` | `DEASCII` | Türkçe karaktersiz yazım |
| `FormCode` | `DOTLESS_I` | Noktalı/noktasız i oyunu |
| `FormCode` | `VOWEL_DROP` | Ünlü düşürme |
| `FormCode` | `SUFFIX_ON_MASKED` | Maskelenmiş köke ek |
| `FormCode` | `DIALECT` | Ağız / yöresel yazım |
| `FormCode` | `HOMOGLYPH` | Benzer görünümlü karakter |
| `FormCode` | `ZERO_WIDTH` | Görünmez karakter |
| `FormCode` | `EMOJI_SUB` | Emoji ikamesi |
| `FormCode` | `PHONETIC` | Sesletime dayalı yazım |
| `GuardCode` | `SUBSTRING_COLLISION` | Alt dizi çakışması |
| `GuardCode` | `NEGATION` | Olumsuzlama |
| `GuardCode` | `QUOTE_COUNTERSPEECH` | Alıntı / karşı söylem |
| `GuardCode` | `METADISCUSSION` | Dil üzerine tartışma |
| `GuardCode` | `SELF_DIRECTED` | Kendine yönelik |
| `GuardCode` | `FRIENDLY_BANTER` | Dostça takılma |
| `GuardCode` | `DUAL_REGISTER` | Çift anlamlı kullanım |
| `GuardCode` | `HOMONYM` | Eş sesli sözcük |
| `GuardCode` | `NON_HUMAN_TARGET` | İnsan dışı hedef |
| `TargetType` | `individual` | Birey |
| `TargetType` | `group` | Grup |
| `TargetType` | `non_human` | İnsan dışı |
| `TargetType` | `none` | Hedef yok |
| `Action` | `block` | Engelle |
| `Action` | `escalate` | Üst incelemeye ilet |
| `Action` | `review` | İncelemeye al |
| `Action` | `nudge` | Uyar |
| `Action` | `clean` | Temiz |

**There is no `label_tr` field in the response.** These labels exist only in `codes.py`; the API sends codes. How the UI gets them — for example a copy generated from `codes.py` at build time, or something the API serves — is an open question for Musaab. Adding a field to the response is a contract change.

---

## 2. The API you own: `AI/api/main.py`

It runs on the Python standard library (`http.server.ThreadingHTTPServer`), not FastAPI. Rule 6 keeps the core — `contracts`, `decision`, `pipeline`, `api`, `eval` — on the standard library plus pyyaml, and `AI/tests/test_architecture.py` fails the build on any other import there.

```bash
cd AI
python -m api.main --host 127.0.0.1 --port 8080
```

| request | response |
|---|---|
| `GET /health` | `200` `{"status": "ok", "artifact_hash": "..."}` |
| `POST /analyze` with a JSON object `{"text": "...", "trace_id": "..."}` (`trace_id` optional) | `200` and the full contract of section 1 |
| invalid or negative `Content-Length`, body not UTF-8 JSON, body not an object, `text` not a string, `trace_id` not a string | `400` `{"error": "..."}` |
| body larger than `MAX_BODY_BYTES` (64 KiB) | `413` `{"error": "body too large"}` |
| any other path | `404` `{"error": "not found"}` |
| anything unexpected, including a pipeline exception | `500` `{"error": "internal error: <ExceptionType>"}` |

**Known defects: status in the repo today.**

| defect | status at `6583e5c` |
|---|---|
| `Content-Length` parsed outside the try block | **Already fixed.** `_parse_request` converts it inside `try` and answers `400`; covered by `test_invalid_content_length_gets_400`. |
| The analyze call unwrapped, so a pipeline exception drops the connection instead of returning 500 | **Already fixed.** `do_POST` runs inside `_guarded`, which answers `500` JSON; covered by `test_pipeline_failure_gets_500_json`. |

Keep both tests green; there is nothing left to fix for these two. Other gaps are visible in the code; each one needs a decision with Musaab, not a fix on your own:

- No thread block is accepted (HANDOVER decision #38). It waits for `docs/frontend/02_BACKEND_SPEC.md`, which is not in the repo.
- No CORS headers. A page served from a different origin cannot call the API.
- No authentication and no TLS, by design (module docstring): meant to sit behind a gateway.
- One `Pipeline` per server process; the repetition counter lives in memory and resets on restart (ADR-004).
- How `backend/` relates to `AI/api/` is not recorded anywhere in the repo.

---

## 3. What the screen must show

| the screen must show | read it from |
|---|---|
| Pass or fail | `verdict` (its Turkish label) and `explanation`, verbatim |
| How fast | `latency_ms`; `per_module_ms` for detail |
| If flagged: which category | each `content[]` entry with `fired: true`: its `code` label |
| …with its own score AND its own threshold beside it | `score` and `threshold` **of that same entry**. When the verdict was driven by the binary score, `signals.decision.binary_offensive` carries its own `threshold` and per-channel `score` |
| If obfuscated: which pattern | `form.active`, and each `form.patterns[]` entry: `code` label, `evidence`, `span` |
| …and what the text looked like de-obfuscated | **Not in the response.** `pipeline/run.py` leaves the de-obfuscated text out on purpose to keep the response bounded (HANDOVER decision #21). What the response does carry: each pattern's `evidence` and `span` in the original text, and the raw and normalized scores of the same code in `signals.decision.channel_scores`. Showing the full de-obfuscated sentence is a question for Musaab |
| If a guard fired: that the silence was deliberate | each `guards[]` entry with `active: true`: its `code` label, `evidence`, `span` and `suppressed` codes. The suppressed `content[]` entry shows `fired: false`, and `explanation` names the guard |

---

## 4. The design tension you must solve

Scores differ enormously between families. Each code has its own threshold; family A and B and C come from different heads or from a lexicon, D from a separate model, and the binary offensive score is yet another probability. Two things are therefore forbidden:

- **Averaging them into one confidence bar.** A C-family score and an A-family score do not mean the same thing, and an average hides the one code that fired.
- **Dumping sixteen rows of numbers** (every `ContentCode` except `CLEAN`) on a non-technical judge.

Three directions to put in front of Musaab. **Decide one with him before you build.**

| direction | what it looks like | for | against |
|---|---|---|---|
| **A. Verdict card, fired codes only** | Large verdict and explanation. Below it only codes that fired or were suppressed, each with its score marked against its own threshold on its own scale. Everything else behind a details view. | Simplest for a judge; easiest to read from six metres; nothing to misread. | Near-misses are hidden; a clean result is an almost empty screen. |
| **B. Family lanes** | One lane per family (A, B, C, D), each with its own threshold line, showing that family's top code and how many others it scored. | Shows at a glance that each family is judged separately, which is the project's argument. | More on screen; lanes must not look comparable to each other; the D lane stays empty while m5 is gated. |
| **C. Text first** | The original text large, with spans highlighted (form patterns, lexicon matches, guard evidence); the verdict beside it; selecting a highlight shows its code, score and threshold. | Strongest for the live obfuscation demo: the judge sees where the evasion was. | Whole-post scores (m3, m5 emit no spans) need a separate place; span offsets need the code-point conversion in 1.2. |

---

## 5. The five states

Each state is read from fields the pipeline and decision layer already set. The UI never compares a score with a threshold to find one. States combine: a flagged post can also be degraded, and a guard can fire on one code while another code fires. Render the combination; do not pick one.

| state | how to recognise it | what must be visible |
|---|---|---|
| **1. degraded** (first) | `signals.pipeline.degraded` is not empty | the verdict (`review` when it would otherwise have been clean; a more severe verdict stands), `explanation` verbatim, every degraded module by name with its `kinds` |
| **2. error** | HTTP status other than 200, a network failure, or `verdict: null` (the decision layer failed; `explanation` begins "Karar verilemedi: karar katmanında") | that no judgement was made, and why, in words a judge can read; never a blank or frozen screen |
| **3. guard-fired** | a `guards[]` entry with `active: true` and a non-empty `suppressed` | the guard, what it suppressed, its evidence, and that the silence was deliberate |
| **4. flagged** | `verdict` is not `clean` | section 3: category label, its score and its own threshold, patterns if any |
| **5. clean** | `verdict` is `clean` and `signals.pipeline.degraded` is empty | the verdict, the explanation, the latency |

**Degraded comes first because it is what you will see every day.** With the default pipeline today, m1, m2, m3, m5 and m6 are stubs, m0 is implemented and m4 emits nothing by design. Every ordinary post comes back `review` with those five modules listed. Clean is not reachable from the default pipeline until the stubs are implemented. That is fail-closed behaviour, not a bug (`AI/CONTRIBUTING.md`, "Why every verdict is `review` today").

---

## 6. Hard rules

1. **No decision logic in the UI, ever.** The UI never derives `verdict`, `fired`, `active` or `suppressed`.
2. **No threshold comparison.** Show the `threshold` the payload carries beside the `score`; never compute which is larger. Every value in `thresholds.yaml` is a placeholder today. Whether the screen must say so is a question for Musaab.
3. **No invented numbers.** Every number on screen comes from the payload. No hard-coded, sample or animated values. The test-double scores in section 7 are never shown as results.
4. **Turkish on screen comes from the Turkish labels (1.5) and `explanation`.** The response carries codes, not labels (see 1.5). Any other Turkish text on screen is a question for Musaab.
5. **Fully offline.** No CDN, no remote font, no analytics, no external request of any kind.
6. **Readable on a projector from six metres.**

---

## 7. Mock payloads to build against today

Generated on 2026-09-14 from the repo at commit `6583e5c`, by running the real code. `trace_id` was fixed per payload; `latency_ms`, `per_module_ms` and `artifact_hash` differ on every run.

| state | how it was produced | are the scores real? |
|---|---|---|
| degraded | the real default pipeline, all seven modules as they are today: `Pipeline().analyze("Bu bir test cumlesi")` | no scores exist; everything else is real |
| clean | the real pipeline and decision layer with only the real `m0_charsafe`, so no stub is in the run | no scores exist; everything else is real |
| flagged | the real pipeline and decision layer with test-double m2 and m3 modules returning fixed values, built the way `AI/tests/test_pipeline.py` builds them | **no: fixed test-double values** |
| guard-fired | the real pipeline and decision layer with a test-double m1 returning a fixed score and guard | **no: fixed test-double values** |
| error | the real API handler: a bad request, `/health`, and a pipeline that raises | real responses |

To regenerate the live ones yourself: `python -m pipeline.run "Bu bir test cumlesi" --trace-id mock-degraded` from `AI/`, and the API responses with `python -m api.main` and `curl`.

### 7.1 degraded

```json
{
  "text": "Bu bir test cumlesi",
  "verdict": "review",
  "form": {
    "patterns": [],
    "active": []
  },
  "content": [],
  "target": null,
  "guards": [],
  "thread": null,
  "signals": {
    "m0_charsafe": {
      "offsets_identity": true,
      "invisible_removed": 0,
      "homoglyphs_mapped": 0,
      "charsafe_changed": false
    },
    "m2_deobf": {},
    "m6_target": {},
    "m1_lexicon": {},
    "m3_encoder": {},
    "m4_implicit": {},
    "m5_sarcasm": {},
    "pipeline": {
      "degraded": [
        {
          "module": "m2_deobf",
          "kinds": [
            "stub"
          ],
          "reasons": [
            "stub: no detection logic yet"
          ]
        },
        {
          "module": "m6_target",
          "kinds": [
            "stub"
          ],
          "reasons": [
            "stub: no detection logic yet"
          ]
        },
        {
          "module": "m1_lexicon",
          "kinds": [
            "stub"
          ],
          "reasons": [
            "stub: no detection logic yet"
          ]
        },
        {
          "module": "m3_encoder",
          "kinds": [
            "stub"
          ],
          "reasons": [
            "stub: no detection logic yet"
          ]
        },
        {
          "module": "m5_sarcasm",
          "kinds": [
            "stub"
          ],
          "reasons": [
            "stub: no detection logic yet"
          ]
        }
      ],
      "emits_spans": {
        "m0_charsafe": false,
        "m2_deobf": false,
        "m6_target": true,
        "m1_lexicon": true,
        "m3_encoder": false,
        "m4_implicit": false,
        "m5_sarcasm": false
      }
    },
    "decision": {
      "family_a": null,
      "threshold_branches": [],
      "binary_offensive": {
        "threshold": 0.5,
        "branch": "scalar",
        "signal": null,
        "signal_value": null,
        "channels": {
          "raw": {
            "score": null,
            "fired": null
          },
          "normalized": {
            "score": null,
            "fired": null
          }
        },
        "fired": null,
        "action": "review"
      },
      "channel_scores": [],
      "post_offensive": false
    }
  },
  "explanation": "Karar verilemedi, içerik temiz sayılmadı ve incelemeye alındı: değerlendirme eksik çünkü m2_deobf henüz uygulanmadı, m6_target henüz uygulanmadı, m1_lexicon henüz uygulanmadı, m3_encoder henüz uygulanmadı, m5_sarcasm henüz uygulanmadı.",
  "latency_ms": 0.4658999969251454,
  "per_module_ms": {
    "m0_charsafe": 0.08140003774315119,
    "m2_deobf": 0.006699992809444666,
    "m6_target": 0.004099973011761904,
    "m1_lexicon": 0.00300002284348011,
    "m3_encoder": 0.003500026650726795,
    "m4_implicit": 0.0030999653972685337,
    "m5_sarcasm": 0.0025999615900218487
  },
  "fast_path": false,
  "trace_id": "mock-degraded",
  "artifact_hash": "5a2fa46738f645f2fa08d27bba1950cdbde19021c0b5ee8c5b658251dddd5381",
  "notes": [
    "[pipeline] DEGRADED - judgement incomplete, clean is not reachable: m2_deobf (stub), m6_target (stub), m1_lexicon (stub), m3_encoder (stub), m5_sarcasm (stub)",
    "[m2_deobf] stub: detection not implemented",
    "[m6_target] stub: detection not implemented",
    "[m1_lexicon] stub: detection not implemented",
    "[m3_encoder] stub: detection not implemented",
    "[m5_sarcasm] stub: detection not implemented"
  ]
}
```

### 7.2 clean

```json
{
  "text": "Bu bir test cumlesi",
  "verdict": "clean",
  "form": {
    "patterns": [],
    "active": []
  },
  "content": [],
  "target": null,
  "guards": [],
  "thread": null,
  "signals": {
    "m0_charsafe": {
      "offsets_identity": true,
      "invisible_removed": 0,
      "homoglyphs_mapped": 0,
      "charsafe_changed": false
    },
    "pipeline": {
      "degraded": [],
      "emits_spans": {
        "m0_charsafe": false
      }
    },
    "decision": {
      "family_a": null,
      "threshold_branches": [],
      "binary_offensive": {
        "threshold": 0.5,
        "branch": "scalar",
        "signal": null,
        "signal_value": null,
        "channels": {
          "raw": {
            "score": null,
            "fired": null
          },
          "normalized": {
            "score": null,
            "fired": null
          }
        },
        "fired": null,
        "action": "review"
      },
      "channel_scores": [],
      "post_offensive": false
    }
  },
  "explanation": "İçerikte eşiği aşan saldırgan bir kategori bulunmadı.",
  "latency_ms": 0.26349996915087104,
  "per_module_ms": {
    "m0_charsafe": 0.10210002074018121
  },
  "fast_path": false,
  "trace_id": "mock-clean",
  "artifact_hash": "5779a6499c1170a8a5cd19219127769413606b05efa05e0f11b31d3a3a229d87",
  "notes": []
}
```

### 7.3 flagged (test-double scores)

```json
{
  "text": "Seni b1tireceğim",
  "verdict": "escalate",
  "form": {
    "patterns": [
      {
        "code": "LEET",
        "confidence": 0.9,
        "evidence": "1",
        "span": [
          6,
          7
        ],
        "source": "m2_deobf"
      }
    ],
    "active": [
      "LEET"
    ]
  },
  "content": [
    {
      "code": "B2",
      "score": 0.87,
      "source": "m3_encoder@normalized",
      "span": null,
      "threshold": 0.5,
      "fired": true
    },
    {
      "code": "C4",
      "score": 0.12,
      "source": "m3_encoder@raw",
      "span": null,
      "threshold": 0.5,
      "fired": false
    }
  ],
  "target": null,
  "guards": [],
  "thread": null,
  "signals": {
    "m0_charsafe": {
      "offsets_identity": true,
      "invisible_removed": 0,
      "homoglyphs_mapped": 0,
      "charsafe_changed": false
    },
    "m2_deobf": {},
    "m3_encoder": {
      "raw_score": 0.44,
      "norm_score": 0.81,
      "artifact": "test-double"
    },
    "pipeline": {
      "degraded": [],
      "emits_spans": {
        "m0_charsafe": false,
        "m2_deobf": false,
        "m3_encoder": false
      }
    },
    "decision": {
      "family_a": null,
      "threshold_branches": [
        {
          "code": "B2",
          "source": "m3_encoder@raw",
          "threshold": 0.5,
          "branch": "scalar",
          "signal": null,
          "signal_value": null
        },
        {
          "code": "B2",
          "source": "m3_encoder@normalized",
          "threshold": 0.5,
          "branch": "scalar",
          "signal": null,
          "signal_value": null
        },
        {
          "code": "C4",
          "source": "m3_encoder@raw",
          "threshold": 0.5,
          "branch": "scalar",
          "signal": null,
          "signal_value": null
        }
      ],
      "binary_offensive": {
        "threshold": 0.5,
        "branch": "scalar",
        "signal": null,
        "signal_value": null,
        "channels": {
          "raw": {
            "score": 0.44,
            "fired": false
          },
          "normalized": {
            "score": 0.81,
            "fired": true
          }
        },
        "fired": true,
        "action": "review"
      },
      "channel_scores": [
        {
          "code": "B2",
          "score": 0.41,
          "source": "m3_encoder@raw",
          "span": null,
          "threshold": 0.5,
          "fired": false
        },
        {
          "code": "B2",
          "score": 0.87,
          "source": "m3_encoder@normalized",
          "span": null,
          "threshold": 0.5,
          "fired": true
        },
        {
          "code": "C4",
          "score": 0.12,
          "source": "m3_encoder@raw",
          "span": null,
          "threshold": 0.5,
          "fired": false
        }
      ],
      "post_offensive": true
    }
  },
  "explanation": "İçerik 'Tehdit' (B2) nedeniyle üst incelemeye iletildi.",
  "latency_ms": 0.32699998700991273,
  "per_module_ms": {
    "m0_charsafe": 0.05619996227324009,
    "m2_deobf": 0.028600043151527643,
    "m3_encoder": 0.009300012607127428
  },
  "fast_path": false,
  "trace_id": "mock-flagged",
  "artifact_hash": "57466e1738c99c48ae87ba537df93c268d446b3cf4a258669ff3611f5bf6fe63",
  "notes": []
}
```

### 7.4 guard-fired (test-double scores)

```json
{
  "text": "amcam geldi",
  "verdict": "clean",
  "form": {
    "patterns": [],
    "active": []
  },
  "content": [
    {
      "code": "A1",
      "score": 0.72,
      "source": "m1_lexicon@raw",
      "span": [
        0,
        2
      ],
      "threshold": 0.5,
      "fired": false
    }
  ],
  "target": null,
  "guards": [
    {
      "code": "SUBSTRING_COLLISION",
      "score": 0.95,
      "source": "m1_lexicon",
      "evidence": "amcam",
      "span": [
        0,
        5
      ],
      "threshold": 0.5,
      "active": true,
      "suppressed": [
        "A1"
      ]
    }
  ],
  "thread": null,
  "signals": {
    "m0_charsafe": {
      "offsets_identity": true,
      "invisible_removed": 0,
      "homoglyphs_mapped": 0,
      "charsafe_changed": false
    },
    "m1_lexicon": {
      "lexicon_hit": false,
      "lexicon_hit_raw": false,
      "lexicon_hit_norm": false
    },
    "pipeline": {
      "degraded": [],
      "emits_spans": {
        "m0_charsafe": false,
        "m1_lexicon": true
      }
    },
    "decision": {
      "family_a": {
        "target": "none",
        "confidence": null,
        "min_confidence": 0.5,
        "resolved_as": "none",
        "code": "A1"
      },
      "threshold_branches": [
        {
          "code": "A1",
          "source": "m1_lexicon@raw",
          "threshold": 0.5,
          "branch": "scalar",
          "signal": null,
          "signal_value": null
        }
      ],
      "binary_offensive": {
        "threshold": 0.5,
        "branch": "scalar",
        "signal": null,
        "signal_value": null,
        "channels": {
          "raw": {
            "score": null,
            "fired": null
          },
          "normalized": {
            "score": null,
            "fired": null
          }
        },
        "fired": null,
        "action": "review"
      },
      "channel_scores": [
        {
          "code": "A1",
          "score": 0.72,
          "source": "m1_lexicon@raw",
          "span": [
            0,
            2
          ],
          "threshold": 0.5,
          "fired": false
        }
      ],
      "post_offensive": false
    }
  },
  "explanation": "'Hedefsiz küfür' (A1) sinyali 'Alt dizi çakışması' koruması nedeniyle bastırıldı, içerik temiz kabul edildi.",
  "latency_ms": 0.23419997887685895,
  "per_module_ms": {
    "m0_charsafe": 0.048200017772614956,
    "m1_lexicon": 0.01190003240481019
  },
  "fast_path": false,
  "trace_id": "mock-guard",
  "artifact_hash": "b246927b240fcae1752a19a0459674e488c802b2edd0245dfcb51c9898b67977",
  "notes": [
    "[decision] A1 from m1_lexicon@raw span=(0, 2) suppressed by guard SUBSTRING_COLLISION from m1_lexicon span=(0, 5)"
  ]
}
```

### 7.5 error (status and body of each response)

```json
{
  "400_bad_request": {
    "status": 400,
    "body": {
      "error": "text must be a string"
    }
  },
  "200_health": {
    "status": 200,
    "body": {
      "status": "ok",
      "artifact_hash": "5a2fa46738f645f2fa08d27bba1950cdbde19021c0b5ee8c5b658251dddd5381"
    }
  },
  "500_pipeline_failure": {
    "status": 500,
    "body": {
      "error": "internal error: RuntimeError"
    }
  }
}
```

---

## 8. Acceptance criteria and evidence

**Accepted when:**

- All five states render correctly from the five mock payloads, and degraded and error also from the live API.
- Degraded: every module in `signals.pipeline.degraded` is named on screen with its kind; `explanation` is shown verbatim; the verdict is never styled as a pass.
- Flagged: each fired code shows its Turkish label, its score and its own threshold, taken from the same entry; no averaged score appears anywhere.
- Obfuscated: each pattern's label and evidence are shown, and span highlights are correct on text containing an emoji.
- Guard-fired: the guard's label, its evidence and the suppressed code are visible, and the screen says the silence was deliberate.
- Error: `400`, `413`, `404`, `500`, a network failure and `verdict: null` each produce a readable state.
- The frontend contains no threshold comparison and no verdict derivation (reviewed by Musaab).
- Works with the network disconnected; the built frontend references no external host.
- Readable from six metres on the demo projector.
- `python -m unittest discover -p "test_*.py"` and `scripts/check.sh` are green, and `AI/tests/test_api.py` still covers the `400` and `500` cases.
- The layout direction was agreed with Musaab before it was built.

**Evidence you hand in:**

- A screenshot of each of the five states, taken with the network disconnected.
- A photo or short video of the screen from six metres on the projector.
- The output of the test suite and of `scripts/check.sh`.
- The command and output of a search of the built frontend for external URLs.
- The written layout decision agreed with Musaab.
- A list of every response field the screen reads, mapped to where it is shown, so review against the contract is mechanical.
