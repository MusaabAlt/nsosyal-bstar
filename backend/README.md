# NSosyal backend (Go)

One executable for the live demo: it serves the moderation panel and the REST
API on one port, starts and supervises the Python inference service, and
stores everything in PostgreSQL. The whole-system overview is in
[`docs/FULLSTACK.md`](../docs/FULLSTACK.md); this file is the practical guide.

## Requirements

- Go 1.27 or newer
- PostgreSQL (a local install on 5432, or `make db-up` for Docker on 5433)
- The project venv `../.venv` with the AI service installed (`make ai-setup`)
- Node.js, only to build the panel (`make frontend`)

## Run

```bash
cp .env.example .env     # set NSOSYAL_DATABASE_URL (and NSOSYAL_SERVER_ADDR if 8080 is taken)
make run                 # go run ./cmd/server: migrates, starts Python, serves the panel and /api
```

The log prints the LAN addresses to open, for example
`open="http://192.168.1.118:8080"`.

| Command | What |
|---|---|
| `make build` | Build the panel into `web/dist`, then `bin/nsosyal-server.exe` (one file for the demo laptop). |
| `make frontend` | Only rebuild the panel into `web/dist` (checked for external URLs). |
| `make mock` | Run `cmd/mockinfer` on :8001 instead of the real model (sample payloads). Go uses it if it is already running. |
| `make ai` | Run the real Python service by hand (normally Go starts it). |
| `make migrate-up` / `migrate-down` / `migrate-reset` / `migrate-status` | Schema by hand. |
| `make test` | Go unit tests + frontend tests. Postgres tests are skipped. |
| `make test-integration` | All tests including Postgres, against `nsosyal_test` (tables are dropped). |
| `make run-loadtest` then `make loadtest` | Server with rate limits raised, then k6 with 150 users. |

> **This laptop:** Apache already listens on 8080. Put
> `NSOSYAL_SERVER_ADDR=0.0.0.0:8090` in `.env`, and check the port before
> every demo.

## Configuration

`config.yaml` holds every limit with a comment. Any value can be overridden
by an environment variable or `.env` named after its path:
`queue.batch_max_wait` → `NSOSYAL_QUEUE_BATCH_MAX_WAIT`. Real environment
variables win over `.env`.

Main groups: `server` (address, timeouts, body and text size), `queue`
(size, workers, batch size and wait), `inference` and `python` (Python
service URL, timeouts, breaker, how to start it), `rate_limit` (per IP;
POST uses the analyse limit, GET the read limit), `cache`, `database`,
`writer`, `decision.thresholds_file`, `log`.

## Layout

```
cmd/server        entry point and graceful shutdown
cmd/migrate       schema by hand
cmd/mockinfer     stand-in Python service with sample payloads
internal/config   defaults, config.yaml, .env, environment
internal/queue    bounded queue and micro-batching workers
internal/inference  Python client and circuit breaker
internal/supervisor starts, watches and restarts Python
internal/cache    result LRU (exact text + model version)
internal/store    pool, migrations, queries, async writer, panel queries
internal/display  display numbers the result does not carry
internal/categories  thresholds and actions from AI/decision/thresholds.yaml
internal/metrics  in-memory latency percentiles
internal/http     router, middleware, handlers, error format
web               embedded panel (web/dist is built, not edited)
loadtest          k6 script
docs              inference-contract.md (Go ⇄ Python)
```

## API

Errors always have one shape:
`{"error": {"code": "queue_full", "message": "...", "retry_after_ms": 2000}}`.
Codes: `bad_request`, `invalid_text`, `invalid_nickname`, `unknown_session`,
`body_too_large`, `not_found`, `rate_limited`, `queue_full`, `model_loading`,
`model_unavailable`, `model_error`, `timeout`, `shutting_down`,
`database_unavailable`, `internal_error`.

### Analysis and status

| Endpoint | Request → response |
|---|---|
| `POST /api/sessions` | `{nickname}` (1–32 chars) → `201 {id, nickname, created_at}` |
| `POST /api/comments` | `{session_id, text}` (≤ 5000 chars) → `201 {comment: {id, session_id, created_at}, result, normalization, display, representative, timing}` |
| `GET /api/comments?limit&cursor` | Feed, newest first → `{items, next_cursor}` |
| `GET /api/moderation/flagged?limit&cursor` | Non-clean comments with fired reasons |
| `GET /api/stats` | DB counts, latency (request, queue wait, model), queue, cache, writer, uptime |
| `GET /api/health` | `{status: ok\|degraded, go, python, postgres, queue, writer}`; always 200 while Go runs |
| `GET /api/categories` | `{source, categories: [{code, family, threshold, action, derived, status, module}], representative}` |

`result` is the pipeline's `AnalysisResult` exactly as Python sent it. Go
never changes `verdict`, `fired`, `active` or `suppressed`.

### Moderation panel (`internal/http/handlers/panel.go`)

| Endpoint | Request → response |
|---|---|
| `GET /api/panel/overview?range=live\|today\|week` | `{range, start, now, bucket_seconds, bucket_starts, analysed, detected, automatic, queue, categories[+total, buckets], patterns, system, representative}`. Each KPI is `{value, previous, change_pct, share_pct?}`. |
| `GET /api/panel/items?status=pending\|reviewed\|auto&detected=true&code=A1&q=text&limit&cursor` | `{items: [{id, nickname, text, created_at, final_action, fired_types, guards_active, degraded, explanation, detected, status, latest_action, latest_action_at, latency_ms, result}], next_cursor}` |
| `GET /api/panel/items/{id}` | `{item, actions: [{action, nickname, created_at}], previous: [3 earlier items from the same sender]}` or `404` |
| `GET /api/panel/queue-counts` | `{pending, pending_detected, reviewed, auto}` |
| `POST /api/panel/actions` | `{comment_ids: [1..100], action: approve\|hide\|remove\|queue\|false_positive, session_id?}` → `{recorded, missing}`; `404` when none of the ids is stored yet |
| `GET /api/panel/events?kind=moderator\|system&q&limit&cursor` | `{items: [{kind, key, created_at, action, actor, comment_id, author, text, fired_types, detected, degraded, explanation}], next_cursor}` |
| `GET /api/panel/metrics` | 30 one-minute buckets for analyses and all requests (`requests, errors, p50_ms, p95_ms`), `requests_per_second`, `error_rate_pct`, `active_devices`, `latency`, `slow` |

How the panel's words are defined (detected, pending, automatic, change %,
active devices, slow) is written down in
[`docs/FULLSTACK.md` §3](../docs/FULLSTACK.md#definitions-the-panel-relies-on).

## Database

Migrations live in `internal/store/migrations/` and are embedded in the
binary.

| Migration | Tables |
|---|---|
| `00001_init.sql` | `sessions`, `comments` (full result JSON), `analysis_results` (one row per content code), `moderation_decisions` (the AI's verdict), `request_metrics` |
| `00002_moderator_actions.sql` | `moderator_actions` (`approve`, `hide`, `remove`, `queue`, `false_positive`) |

Comments and decisions are written in the background in batches; a
moderator action can therefore return `404` for a comment analysed a
split second earlier. The panel retries automatically.

## Resilience, in one list

- Full queue → immediate `503 queue_full`, never a hang.
- Model loading → `503 model_loading`; the breaker opens after repeated failures.
- Python dies or hangs → the supervisor restarts it with backoff.
- Postgres slow or down → answers still go out; writes retry, then drop and count.
- Panics → `500` for that request only.
- Per-IP rate limits; request deadline; ordered shutdown that drains the queue and flushes writes.
