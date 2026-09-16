# Inference service contract (Python ⇄ Go)

The Python inference service (`AI/serving`, FastAPI) listens on `127.0.0.1:8001`
only. The Go backend is its only client and starts it (`python` in
`backend/config.yaml`). `cmd/mockinfer` implements the same contract with
sample data.

```bash
cd AI
pip install -r serving/requirements.txt -r modules/m1_lexicon/requirements.txt -r modules/m3_encoder/requirements.txt
python -m uvicorn serving.app:create_app --factory --host 127.0.0.1 --port 8001
```

## `POST /predict_batch`

Request:

```json
{ "items": [ { "id": "0192…uuid", "text": "Seni b1tireceğim" } ] }
```

- At most `queue.batch_max_size` items (16 by default).
- `id` is the comment id. Pass it to the pipeline as `trace_id`.
- `text` is exactly what the user typed. Never trim or normalize it.

Response `200`:

```json
{
  "artifact_hash": "57466e…",
  "results": [
    {
      "id": "0192…",
      "ok": true,
      "result": { "…": "AnalysisResult.to_dict(), AI/contracts/schema.py" },
      "normalization": {
        "text": "Seni bitireceğim",
        "changes": [
          { "code": "LEET", "from_span": [6, 7], "to_span": [6, 7], "from": "1", "to": "i" }
        ]
      }
    },
    { "id": "0193…", "ok": false, "error": "internal error: RuntimeError" }
  ]
}
```

| field | required | meaning |
|---|---|---|
| `artifact_hash` | yes | The model and threshold version. It must equal `result.artifact_hash`. The cache keys on it. |
| `results[].id` | yes | Matched by id, not by position. |
| `results[].ok` | yes | `false` fails only this item. The rest of the batch is unaffected. |
| `results[].result` | when ok | The frozen contract, unchanged. |
| `results[].normalization` | **optional** | m2's de-obfuscated text. Omit it, or send `null`, when m2 did not run. |
| `normalization.text` | yes | The whole normalized text. |
| `normalization.changes[].code` | yes | The `FormCode` that was undone. |
| `normalization.changes[].from_span` | yes | `[start, end)` in the **original** text, in code points (Python string indices). |
| `normalization.changes[].to_span` | yes | `[start, end)` in `normalization.text`, or `null` when characters were removed. |
| `normalization.changes[].from` / `to` | yes | The characters before and after. `to` is `""` when removed. |

`normalization` sits beside `result` on purpose. The `AnalysisResult` contract
is frozen and deliberately leaves the de-obfuscated text out
(HANDOVER decision 21). The screen shows it in stage 4 (Normalleştirme) only
when this optional field is present.

Other statuses:
- `503` (any body): the models are still loading. Go stops sending batches until `/health` says `ok`.
- `500`, or any other status: the whole batch failed. After repeated failures Go opens its circuit breaker.

## `GET /health`

```json
{
  "status": "ok",
  "artifact_hash": "57466e…",
  "degraded_modules": ["m2_deobf", "m6_target"],
  "capabilities": [
    { "code": "A1", "module": "m1_lexicon" },
    { "code": "binary_offensive", "module": "m3_encoder" }
  ],
  "representative": false
}
```

| field | meaning |
|---|---|
| `status` | `ok`, `loading` or `error`. Answer `loading` while models load, never a timeout. |
| `artifact_hash` | Same value as in batch responses. |
| `degraded_modules` | Modules that are stubs or failed to load. Kategoriler marks their categories `modül hazır değil`. |
| `capabilities` | What the AI can detect **today** and which module produces it (`AI/serving/capabilities.py`). Kategoriler lists only these, and "N kategoriden M'i değerlendirildi" counts only these. `binary_offensive` is the decision layer's channel-level offensive score, shown as "Genel saldırganlık". Update the list in the same change that makes a module emit a new code. |
| `representative` | `true` only for a service that returns sample data. The screen then shows the `Temsili veri` marker. The real service sends `false`. |

## Limits Go enforces

| limit | default | config key |
|---|---|---|
| batch call timeout | 10 s | `inference.batch_timeout` |
| health call timeout | 2 s | `inference.health_timeout` |
| failures before the breaker opens | 5 | `inference.breaker_failures` |
| breaker open period | 5 s | `inference.breaker_open_for` |
| startup grace while loading | 120 s | `python.startup_grace` |
