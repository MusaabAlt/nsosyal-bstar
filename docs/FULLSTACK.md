# Full stack: what was built on the `fullstack` branch

This document explains everything the `fullstack` branch added to the
repository (merged into `master` as pull request #1): the Go backend, the Vue
moderation panel and the FastAPI inference service in `AI/serving`. It is the
starting point for anyone who has to run, change or present that work.

More detail lives next to the code:

| Topic | File |
|---|---|
| Backend: running, configuration, endpoints | [`backend/README.md`](../backend/README.md) |
| Go ⇄ Python contract | [`backend/docs/inference-contract.md`](../backend/docs/inference-contract.md) |
| Frontend: pages, structure, commands | [`frontend/README.md`](../frontend/README.md) |
| Original console specification (history) | [`docs/UI/`](UI/README.md) |

---

## 1. The big picture

The demo runs on **one offline laptop**. Up to about 70 people on the room's
Wi-Fi send messages; a moderator watches the panel on the same laptop or on
a projector. Three processes run on the laptop:

```
 phones / laptops on the LAN                      the demo laptop
 ───────────────────────────        ┌────────────────────────────────────────────────┐
                                    │                                                │
   browser ── HTTP :8080 ─────────► │  Go server (backend/)                          │
                                    │   • serves the Vue panel (embedded in binary)  │
                                    │   • /api/*  REST API                           │
                                    │   • queue + micro-batching, cache, rate limits │
                                    │        │                       │               │
                                    │        │ HTTP 127.0.0.1:8001   │ SQL :5432     │
                                    │        ▼                       ▼               │
                                    │  Python inference         PostgreSQL           │
                                    │  (AI/serving, FastAPI)    comments, decisions, │
                                    │  runs AI/pipeline         moderator actions,   │
                                    │  started + watched by Go  request metrics      │
                                    └────────────────────────────────────────────────┘
```

- **Go server** (`backend/`): the only process the network can reach. It
  serves the panel and the API, protects the model from overload, stores
  everything in Postgres and starts the Python service itself.
- **Python inference service** (`AI/serving/`): a thin HTTP wrapper around
  `AI/pipeline`. Listens on localhost only. It decides nothing itself; it
  returns the pipeline's `AnalysisResult` unchanged.
- **PostgreSQL**: every analysed message, the decision the AI made, every
  moderator action and every request's timing.

### What happens when someone analyses a message

1. The browser sends `POST /api/comments {session_id, text}`.
2. Go checks the rate limit, the text and the session, then looks in its
   cache (key: exact text + model version).
3. On a cache miss the text joins a bounded queue. Workers group waiting
   texts into small batches and send each batch to Python
   (`POST /predict_batch`).
4. Python runs the pipeline and returns the `AnalysisResult`.
5. Go answers the browser at once with the result, a few display numbers
   (package `display`) and timings. The database write happens in the
   background, so a slow disk never slows the answer.
6. The panel reads the stored data through `/api/panel/*` for its
   dashboards, queue and history.

### The one rule everything follows

**Every number on screen is real, and nobody but the AI decides.**

- The decision layer in Python sets `verdict`, `fired`, `active` and
  `suppressed`. Go stores them and never recomputes them. The UI never
  compares a score with a threshold (a test in
  `frontend/src/design-rules.test.ts` enforces this).
- Counts, percentages and changes are computed by Go from stored rows.
- A value that does not exist is shown as unavailable (`veri yok`, `—`),
  never as `0`.
- The panel shows only the categories the AI can detect **today**
  (`AI/serving/capabilities.py`), not the sixteen codes the contract defines.

---

## 2. AI: the inference service (`AI/serving/`)

Added so the Go backend has a stable HTTP service to call. It does not touch
any module, the contracts or the thresholds.

| File | What it does |
|---|---|
| `app.py` | FastAPI app. `GET /health` and `POST /predict_batch`. Loads the pipeline in a background thread (BERTurk takes a while); until then `/health` says `loading` and `/predict_batch` answers `503`. Runs one analysis at a time (a lock), because the modules are not documented as thread-safe. One failing text never fails the batch. Runnable as `python serving/app.py` or with uvicorn. |
| `capabilities.py` | The list of what the AI detects today and which module produces it. Since m1's routing, m2 and m6 landed (2026-09-17): `A1` / `A2` / `A3` / `B1` / `B2` / `B3` from `m1_lexicon` (terlik; A2 and A3 are the A1 carrier after the decision layer applies m6's target, ADR-005), `B4` (doxing) from `m6_target`, and `binary_offensive` from `m3_encoder` (BERTurk), shown as "Genel saldırganlık". **Update this list in the same change that makes a module emit a new code.** |
| `normalization.py` | Turns m2's internal output into the optional `normalization` object of the Go contract. `to_span` is derived from m2's `_offsets` map (ADR-008); nothing is guessed and nothing enters the frozen result. |
| `requirements.txt` | fastapi, uvicorn, httpx (tests). Kept out of the AI core requirements on purpose. |
| `test_app.py` | Health, loading (503), results matched by id with the text unchanged, one failing item, load failure, oversized text. |

Install and run by hand (the Go server normally does this for you):

```bash
cd AI
../.venv/Scripts/python.exe -m pip install -r serving/requirements.txt -r modules/m1_lexicon/requirements.txt -r modules/m3_encoder/requirements.txt
../.venv/Scripts/python.exe -m uvicorn serving.app:create_app --factory --host 127.0.0.1 --port 8001
```

The full request/response shapes are in
[`backend/docs/inference-contract.md`](../backend/docs/inference-contract.md).

`normalization` (m2's de-obfuscated text) is sent since 2026-09-19. It travels
beside the result, never inside it: the `AnalysisResult` contract is frozen and
leaves the recovered text out on purpose (decision 17/21), so the service asks
the pipeline for it through `Pipeline.analyze_with_internals` and shapes it in
`serving/normalization.py`.

**Interpreter note:** m2's tier 2 (DEASCII) needs `zeyrek`, which only `AI/.venv`
has. Under the repository-root `.venv` the service still runs, `tier2_enabled`
is `false`, and the panel's "Kontrol edilen diğer N kalıpta eşleşme yok" line
correctly counts six checked patterns instead of eight.

---

## 3. Backend (`backend/`, Go)

### Packages

| Package | Responsibility |
|---|---|
| `cmd/server` | Entry point. Wires everything together; shuts down in order (HTTP → queue → DB writer → Python → pool). |
| `cmd/migrate` | Apply or roll back the schema by hand (`up`, `down`, `reset`, `status`). |
| `cmd/mockinfer` | A stand-in for the Python service that returns the sample payloads. For development and load tests without the model. |
| `internal/config` | Defaults → `config.yaml` → `.env` → environment variables (`queue.size` → `NSOSYAL_QUEUE_SIZE`). |
| `internal/queue` | Bounded queue + micro-batching workers. Full queue → `503 queue_full` at once. |
| `internal/inference` | HTTP client for Python with a circuit breaker; caches the last `/health`. |
| `internal/supervisor` | Starts the Python service from the project venv, health-checks it, restarts it with backoff, kills the whole process tree. If something already answers on :8001 it only watches it. |
| `internal/cache` | LRU of results, keyed by sha256(exact text) + artifact hash. The text is never normalised for the key: `s4l4k` and `salak` must stay different. |
| `internal/store` | Postgres pool, embedded migrations, read queries, the async batched writer (COPY in batches, one bad row never loses the batch), and the panel queries (`panel.go`). |
| `internal/display` | The few numbers the screen shows that the result does not carry ("2 kategoriden 2'si değerlendirildi", margins, hidden categories). Counts and subtracts only. |
| `internal/categories` | Category rows for the panel: threshold and action from `AI/decision/thresholds.yaml` (re-read when the file changes), live/stub status from Python's health. |
| `internal/metrics` | In-memory latency windows (p50/p95/p99) for the last 5 minutes. |
| `internal/http/middleware` | Panic recovery, request logging, per-IP rate limits (POST = analyse limit, GET = read limit), request deadline, dev CORS. |
| `internal/http/handlers` | The endpoints (`handlers.go`, `panel.go`). |
| `internal/http/respond` | One JSON error shape: `{"error": {"code", "message", "retry_after_ms"}}`. |
| `web` | The built Vue panel embedded into the binary with `go:embed`. |

### Database

| Table | Written by | Holds |
|---|---|---|
| `sessions` | `POST /api/sessions` | Anonymous nickname + IP. No passwords, no accounts. |
| `comments` | async writer | Text, sha256, full `AnalysisResult` as JSON, latency, cache flag. |
| `analysis_results` | async writer | One row per content code: score, threshold, fired, engine, source. |
| `moderation_decisions` | async writer | The AI's verdict, fired codes, active guards, degraded flag, explanation. |
| `moderator_actions` | `POST /api/panel/actions` | What a moderator did: `approve`, `hide`, `remove`, `queue`, `false_positive`. Migration `00002`. |
| `request_metrics` | async writer | Every API request's path, status and latency. |

Migrations are embedded in the binary and run on start
(`database.migrate_on_start: true`).

### Endpoints

Original API:

| Method & path | Purpose |
|---|---|
| `POST /api/sessions` | Create an anonymous session `{nickname}`. |
| `POST /api/comments` | Analyse a text `{session_id, text}` → result, display numbers, timing, comment id. |
| `GET /api/comments` | Feed, newest first, cursor pagination. |
| `GET /api/moderation/flagged` | Non-clean comments with per-type reasons. |
| `GET /api/stats` | DB counts, latency, queue, cache and writer stats. |
| `GET /api/health` | Go, Python and Postgres status. Always `200` while Go is up. |
| `GET /api/categories` | Categories the AI detects today, with threshold, action, module and status. |

Panel API (added for the ATI-SOSYAL panel, `handlers/panel.go`):

| Method & path | Purpose |
|---|---|
| `GET /api/panel/overview?range=live\|today\|week` | KPIs with change against the previous period, per-category time series, escape patterns, queue counts, system facts. Cached 1 s. |
| `GET /api/panel/items?status&detected&code&q&limit&cursor` | Analysed messages with their result and latest moderator action. |
| `GET /api/panel/items/{id}` | One message, its moderator history and the sender's previous 3 messages. |
| `GET /api/panel/queue-counts` | Pending, pending-and-detected, reviewed, automatic. |
| `POST /api/panel/actions` | Record an action for 1–100 comment ids. `404` if none is stored yet (retry). |
| `GET /api/panel/events?kind&q&limit&cursor` | History: moderator actions and the system's detections. |
| `GET /api/panel/metrics` | Per-minute request counts and latency for 30 minutes, requests/s, error rate, active devices, slow flag. |

### Definitions the panel relies on

These are decisions, written down so nobody has to reverse-engineer them:

- **Detected** = the decision layer fired at least one content code *or* the
  binary offensive score. The verdict is not used, because while `m5_sarcasm`
  is a stub every result is degraded and a clean sentence still ends on
  `review`.
- **Queue status** of a comment:
  - `reviewed` – its latest moderator action is approve, hide or remove;
  - `pending` – its latest action is queue or false_positive, or it has no
    action and the verdict is `review`, `escalate` or missing;
  - `auto` – no action and the verdict is `block` or `nudge`.
- **Automatic action** = verdict `block` or `nudge`.
- **İnsan incelemesi** = verdict `review` + `escalate`, and its share is **of
  everything analysed**, not of the detections. The six verdict buckets
  partition the analysed rows exactly (one SQL row set, one window predicate,
  `final_action` CHECK-constrained to five values plus NULL), so the numerator
  is a subset of the denominator and the share cannot pass 100 %. Over
  `detected` it could, and did: the fail-closed rule hands a comment that fired
  *nothing* to a person, so it counts here while being absent from `detected`,
  and the card read "tespitlerin %125,0'i" until 2026-09-20. Go computes both
  the count and the share (`human_review` in `panel/overview`); the screen only
  formats them.
- **Human review band** (`AI/decision/thresholds.yaml`
  `binary_offensive.review_band`, added 2026-09-20 at the project owner's
  request). A comment that fired no content code used to go to a moderator
  whenever the general offensive score crossed its threshold — any score, all
  the way to 1.00 — so on a quiet window every single detection went to a
  person. The
  channel now asks for a person only while its score sits **between 0.30 and
  0.70**, the range where a moderator can still change the outcome; above
  0.70 the score is decisive on its own and the content is blocked without a
  person, below 0.30 the author is nudged. `AI/decision/actions.py` applies
  it, `backend/cmd/seed` mirrors it for the demo feed, and both read the edges
  and the replacement actions from that one file.
  The band replaces **only** an action that asks for a person, and it bands
  the general offensive channel **only**: `A4`, `B2`, `B4` and `C3` are marked
  "STAYS HUMAN" in `thresholds.yaml` on purpose, and a high score is not a
  reason to overrule that. Deleting the `review_band` block restores the flat
  policy exactly.
- **"Üretilebilen N kategoriden M'i değerlendirildi"** (Canlı Analiz) counts
  what ran out of what the AI can produce **today**, not out of the contract's
  fifteen codes. Unqualified it used to read as "the whole assessment
  completed" directly under a verdict saying the opposite: `m5_sarcasm` is a
  stub, so every result is degraded, yet m5 owns no category in that list
  (D1 is excluded from capabilities *because* m5 is a stub), so the count never
  showed a shortfall. The line now names its own universe and carries the gap
  beside it — "8 kategori henüz üretilmiyor", counted from the contract exactly
  as the moderation classes are. The two are deliberately separate sentences:
  A4, B5 and C1–C5 are simply unbuilt and belong to no degraded list, and only
  D1 is owned by the module the block names.
- **Change %** compares the part of the window that has passed with the same
  length of time just before it. `null` when the earlier period is empty.
- **Active devices** = distinct IPs that sent a comment in the last 5 minutes
  (people who only read are not counted).
- **Slow** = analysis p95 over 200 ms in the last 5 minutes.
- Time windows: `live` = last hour in 5-minute buckets, `today` = since local
  midnight in 1-hour buckets, `week` = last 7 days in 1-day buckets.

---

## 4. Frontend (`frontend/`, Vue 3)

The frontend went through two designs on this branch.

1. **First:** a two-page "moderation console" (Analiz with a nine-stage
   report, and Kategoriler), built strictly from `docs/UI/`. That spec is
   kept in `docs/UI/` as history.
2. **Now:** the **ATI-SOSYAL Moderasyon Paneli**, from the claude.ai/design
   project "ATI-SOSYAL Paneli". It uses NSosyal's own look: pill sidebar,
   brand gradient, cards, dark and light mode. Every value comes from the
   Go API; the frontend holds no sample data of its own. For a presentation
   the *database* can be filled with an invented feed instead (see "Demo
   mode" in section 5) — the screens do not know the difference, because
   the queries behind them are the same.

### Pages

| Route | Page | Shows | Data |
|---|---|---|---|
| `/` | Genel Bakış | Headline card (total analysed, detected + share, automatic actions, general offensive signal, moderator actions), prominent **İnsan incelemesi** card, one card per moderation class (A / B / C / D) with a row for every category the *contract* puts in it, category distribution bars, moderation status (Temiz / Uyarı / İnceleme / Engellendi / Tamamlanmadı), and a recent-activity table where every row opens **Neden?**. Tabs: Canlı, Bugün (default), 7 Gün. | `panel/overview`, `panel/items` |
| `/analiz` | Canlı Analiz | Composer with presets → normalization strip, one result card per category (score, threshold marker, fired or not, action, module time), the evidence panels of pages-spec stages 3 / 6 / 7 (Gizleme tespiti, Hedef, Koruyucu kontroller — `DetectionEvidence.vue`), explanation with highlighted spans, final decision with "Yanlış pozitif bildir" and "Kuyruğa ekle". | `POST /api/comments`, `categories`, `panel/actions` |
| `/kuyruk` | Moderasyon Kuyruğu | Tabs Bekleyen / İncelenen / Otomatik işlenen, filters (only detected, category, search), list with checkboxes and bulk actions, detail panel (scores table, system decision, previous messages, history). Keys A / H / R. | `panel/items`, `panel/items/{id}`, `panel/queue-counts`, `panel/actions` |
| `/motorlar` | Tespit Motorları | One card per category: module, status, threshold, default action, whether the threshold is derived or a placeholder, today's count and trend. | `panel/overview?range=today` |
| `/kurallar` | Kurallar & Eşikler | Read-only table of every category's threshold and action, with the source file. | `categories` |
| `/gecmis` | Olay Geçmişi | Moderator actions and system detections grouped by day; tabs Tümü / Moderatör / Sistem; header search lands here; CSV export. | `panel/events` |
| `/saglik` | Sistem Sağlığı | Devices, requests/s, p95 latency, error rate; latency and request charts; Go / Postgres / model / queue status; warning banners. | `health`, `stats`, `panel/metrics` |

**Neden?** (`components/panel/WhyDialog.vue`) is the decision's evidence: the
message, the verdict and its Turkish explanation, one line per pipeline module
saying what it contributed and how long it took, every category the encoder
scored with its threshold and outcome (fired / below threshold / suppressed by
a guard), and the guards themselves with the codes they cleared. It reads the
stored result only; it derives nothing.

**All four moderation classes are always on the page.** The server counts a
category only while the inference service reports it in `/health`
(`AI/serving/capabilities.py`), so before 2026-09-20 the two classes it does
not produce yet simply vanished and the panel looked as if it knew about two
kinds of abuse. The class list now comes from the contract
(`labels.generated.json`), and a code the AI does not produce shows **`—`
"henüz üretilmiyor"**, never `0`: zero means the code was looked for and not
found, and the panel may not claim a measurement that was never taken. A class
with no live code at all (C örtük saldırganlık, D aşağılayıcı ironi today)
carries the line "Bu sınıfın modülü henüz devrede değil"; a partly live class
(A, missing A4) carries "1 kod henüz ölçülmüyor". When the server reports no
category at all the AI is unreachable, which is not the same as "not built
yet", and the section falls back to its error line instead.

Always visible: the sidebar (with the pending badge), the header search, the
**Sistem durumu** rail on wide screens, the **Canlı Akış** dock with the
newest messages, the dark/light switch (remembered per browser) and the
**Temsili veri** marker whenever the model service reports sample data.

Pages poll every 3–10 seconds and pause while the browser tab is hidden.

**Deliberately not built** (no real data behind them): Gizlenmiş Küfür
Sözlüğü, Değerlendirme, Ayarlar, per-engine F1 / precision / recall,
restart buttons, user accounts.

### On a phone

The panel is used in a hand as well as on a projector, so every page has a
layout below 900px and again below 600px. Nothing is hidden on a small screen:
the same numbers are there, in one column.

- **Shell.** The sidebar becomes an off-canvas drawer behind a menu button in
  the header — seven navigation items with long Turkish labels do not survive
  being squeezed into a rail, and the drawer keeps the labels, the analyse CTA
  and the theme switch exactly as they are on a desktop. The header stacks:
  title row, the search when it is asked for, then the page's tabs as a
  sideways strip. The **Canlı Akış** dock becomes a full-width bar along the
  bottom edge and starts collapsed, and the **Temsili veri** marker rides with
  the page title instead of sitting under the dock.
- **Tables become cards.** A table of eight columns cannot be read on a 360px
  screen and a sideways scrollbar is not a design. `Kurallar & Eşikler` and the
  queue's score table use the shared `.table--stack` pattern: one card per row,
  each value keeping its column heading beside it. The Genel Bakış activity
  table gets a layout of its own — message, then its categories, then who /
  what / when on one line, then a full-width **Neden?**.
- **Queue.** Selecting a message scrolls its detail panel into view, because
  stacked it sits below thirty list items. The category filters are one
  sideways strip rather than four wrapped lines.
- **Neden?** opens as a bottom sheet rather than a centred dialog.
- Controls are 38–40px tall for a thumb, inputs are 16px so iOS Safari does not
  zoom the page on focus, and the breakpoints live in `styles/tokens.css`
  (`--page-gutter`, `--header-height`).

### Rules kept from the original spec

- Works fully offline: Inter is bundled, icons are inline SVG, and
  `npm run check:offline` fails the build on any external URL.
- Spans are code-point offsets (`src/lib/spans.ts`), so emoji never shift a
  highlight.
- The UI reads `fired`, never compares scores with thresholds, never sums
  or averages scores (enforced by `design-rules.test.ts`).
- A degraded result is never shown as clean: the final decision says
  "Değerlendirme tamamlanmadı" and lists the modules that did not run.

---

## 5. Running it

First time, on the demo laptop (Windows, Git Bash):

```bash
# Python venv for the AI service (from the repo root)
python -m venv .venv
cd AI && ../.venv/Scripts/python.exe -m pip install -r requirements.txt -r serving/requirements.txt \
  -r modules/m1_lexicon/requirements.txt -r modules/m3_encoder/requirements.txt && cd ..

# Postgres: a local install, or `make db-up` in backend/ (Docker, port 5433)
cp backend/.env.example backend/.env      # put the real database URL in it

cd frontend && npm install && cd ..
```

Every time:

```bash
cd backend
make build                 # builds the panel into web/dist, then bin/nsosyal-server.exe
bin/nsosyal-server.exe     # migrates, starts Python, serves http://<laptop-ip>:8080
```

During development: `make run` in `backend/` plus `npm run dev` in
`frontend/` (http://127.0.0.1:5173, proxies `/api` to the Go server).

### Demo mode: a full panel without an audience

For a presentation the panel needs a feed behind it. Two commands provide one
without touching the model:

```bash
cd backend
make demo-mock             # mock inference on :8001, every category reported live
make demo-seed             # DESTRUCTIVE: replaces the database with the demo feed
make run
```

- `cmd/seed` writes an invented feed (`cmd/seed/samples.go`): invented
  nicknames, invented posts, ~40 000 comments over 14 days following a daily
  traffic curve. No real NSosyal user or message goes through it. The rows have
  the same shape the running system writes, so the panel's numbers are still
  counted from stored data by the same queries — nothing on screen is a
  placeholder. Flags: `-days`, `-comments`, `-seed` (the same seed gives the
  same feed), `-degraded-pct`, `-artifact`.
- `-reset` truncates `comments`, `sessions`, `moderation_decisions`,
  `analysis_results`, `moderator_actions` and `request_metrics`. Without it the
  command refuses to run on a database that already holds comments.
- `mockinfer -demo` reports every category in `thresholds.yaml` as live, so the
  panel shows one card per moderation class. Without `-demo` it reports what the
  real service reports today (m1's A1–B3, m6's B4 and `binary_offensive`).
- Pass `-artifact <hash>` from the inference service's `/health` if you want
  **Model sürümü** on screen to match the service that is running.
- Two weeks of data is the default on purpose: the "7 Gün" range compares
  itself with the week before it, and a window with nothing behind it shows an
  absurd change percentage.

**Port 8080 on this laptop is taken by Apache.** Set
`NSOSYAL_SERVER_ADDR=0.0.0.0:8090` in `backend/.env`, and
`API_PROXY_TARGET=http://127.0.0.1:8090` in `frontend/.env.local` for the dev
server. Check the port before every demo.

### Tests

```bash
cd backend && go test ./...                         # unit tests (Postgres tests skipped)
cd backend && make test-integration                 # + Postgres tests, on the nsosyal_test database
cd frontend && npm test && npm run typecheck
cd AI && ../.venv/Scripts/python.exe -m unittest serving.test_app
cd backend && make run-loadtest   # then, in another terminal: make loadtest  (k6, 150 users)
```

---

## 6. Known limits and open items

- **`m5_sarcasm` is the one remaining stub.** m2 and m6 landed on 2026-09-17
  and m4 is not a stub (it has nothing to score until m3's C head exists), so
  the pipeline now produces obfuscation patterns, a recovered text, a target
  and B1–B4 alongside A1–A3. One stub is still enough to mark every result
  incomplete and keep `clean` unreachable (fail closed), so a harmless sentence
  still ends on `review`; a real detection now reaches `nudge`, `escalate` or
  `block` on its own. D1 and C1–C5 are not produced.
- **Presets** still fire no category on the real model. `Seni b1tireceğim` and
  `amcam geldi` now produce real evidence on the stage panels (LEET + an
  individual target; `SUBSTRING_COLLISION`), but no content code reaches its
  threshold, so the result cards stay empty. A sentence that fires end to end
  today is `s4l4k herif, sen ne anlarsın` (B1, LEET, individual target). The
  preset texts double as the mock payload keys (`frontend/src/api/mocks/`), so
  changing one means adding its payload too — owner's call, in
  `frontend/src/api/presets.ts`.
- **The human review band is placeholder policy.** 0.30 / 0.70 were chosen by
  the project owner, not derived on the dev split, and they have the same
  standing as every `action` in `thresholds.yaml`: they need sign-off and
  derivation before they are anything but policy. The derived threshold the
  band sits on (0.320188) is untouched — the band changes which *action*
  follows a fire, never whether the channel fires.
- **Fail-closed still sends clean sentences to a person.** The band only
  governs the offensive channel. While `m5_sarcasm` is a stub every result is
  degraded, and `actions.DEGRADED_ACTION` turns a would-be `clean` verdict into
  `review` (owner policy, Phase 9). That is the other reason the queue fills,
  and it is deliberate: it goes away when the last stub is implemented, not by
  tuning a number.
- **Moderator identity** is the browser's anonymous session nickname
  ("Operatör"); there are no accounts.
- **Thresholds cannot be edited from the panel.** They live in
  `AI/decision/thresholds.yaml` and belong to the decision layer's owner.
  `A1`'s threshold is still a placeholder there.
- **History categories:** a system event lists its fired content codes;
  when only the binary offensive score fired it shows "Genel saldırganlık".
