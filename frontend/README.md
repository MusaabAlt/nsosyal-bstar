# ATI-SOSYAL Moderasyon Paneli (frontend)

Vue 3 + Vue Router + Vuetify (application root) + Tailwind (base layer),
TypeScript. The look follows the claude.ai/design project "ATI-SOSYAL
Paneli" (NSosyal's own colours, dark and light). Every number on screen comes
from the Go backend; there is no sample-data mode. System overview:
[`docs/FULLSTACK.md`](../docs/FULLSTACK.md).

Runs fully offline: Inter is bundled, icons are inline SVG, and the build
fails if it references an external host.

## Commands

```bash
npm install
npm run dev              # http://127.0.0.1:5173, proxies /api to the Go server (:8080)
npm test                 # unit tests + design rules
npm run typecheck
npm run build            # type-check + production build into dist/
npm run build:backend    # build into ../backend/web/dist (embedded in the Go binary) + offline check
node scripts/gen-labels.mjs   # regenerate Turkish labels after AI/contracts/codes.py changes
```

If the Go server is not on 8080 (on this laptop Apache holds 8080), create
`.env.local` (git-ignored) with `API_PROXY_TARGET=http://127.0.0.1:8090`.

## Pages

| Route | Page | API it reads |
|---|---|---|
| `/` | Genel Bakış: KPIs, engine cards, chart, escape patterns, recent detections | `/api/panel/overview`, `/api/panel/items` |
| `/analiz` | Canlı Analiz: analyse a sentence, per-category results, final decision | `POST /api/comments`, `/api/categories`, `/api/panel/actions` |
| `/kuyruk` | Moderasyon Kuyruğu: tabs, filters, bulk actions, detail panel, keys A/H/R | `/api/panel/items`, `/api/panel/items/{id}`, `/api/panel/queue-counts`, `/api/panel/actions` |
| `/motorlar` | Tespit Motorları: one card per category the AI runs | `/api/panel/overview?range=today` |
| `/kurallar` | Kurallar & Eşikler: thresholds and actions, read-only | `/api/categories` |
| `/gecmis` | Olay Geçmişi: moderator and system events by day, search (`?q=`), CSV export | `/api/panel/events` |
| `/saglik` | Sistem Sağlığı: services, latency and request charts | `/api/health`, `/api/stats`, `/api/panel/metrics` |

`/kategoriler` (the old page) redirects to `/kurallar`. Links carry state in
the URL: `/kuyruk?id=<comment>&code=A1&status=reviewed&all=1`.

## Where things are

| Path | What |
|---|---|
| `src/styles/tokens.css` | All colours, radii and fonts; dark by default, `html.light` for light. Components use these variables only. |
| `src/styles/main.css` | Base styles and shared classes: `.card`, `.chip`, `.btn` (+ `--secondary`, `--danger`, `--solid`, `--brand`, `--ghost`), `.table`, `.progress`. |
| `src/components/AppShell.vue` | Sidebar, header (title, `#page-tabs` target, search, avatar), rail, dock, theme switch. |
| `src/components/SystemRail.vue`, `LiveDock.vue` | Sistem durumu and Canlı Akış. |
| `src/components/panel/` | Page building blocks: `PageTabs` (teleports into the header), `KpiTile`, `Sparkline`, `LineChart`, `CategoryChip`, `HighlightedText`, `DetectionRow`, `ModeratorActions`, `StatusDot`, `EmptyState`. |
| `src/components/icons.ts`, `Icon.vue` | Inline SVG icon paths. |
| `src/views/` | One file per page. |
| `src/api/panel.ts` | Typed fetchers for `/api/panel/*`, health, stats, categories; `recordAction` retries a `404` while a new comment is still being stored. |
| `src/api/httpSource.ts` | Anonymous session + `POST /api/comments`. |
| `src/api/presets.ts` | Preset sentences on Canlı Analiz. |
| `src/api/mocks/`, `mockSource.ts` | Sample payloads, **used by tests only**. |
| `src/report/model.ts` | Reads an `AnalysisResult` (verdict word, per-category rows, module states); decides nothing. |
| `src/report/useAnalysis.ts` | idle → analysing → report / error, with a 400 ms minimum so the change is visible. |
| `src/lib/categories.ts` | Category label, family, colour and icon; `firedCategories()` reads what fired. |
| `src/lib/spans.ts` | Code-point spans → highlighted segments (emoji-safe). |
| `src/lib/format.ts` | Turkish number, percent, change and time formatting; missing values stay `null`. |
| `src/composables/` | `usePoll` (pauses while the tab is hidden), `useTheme`, `useLiveOverview` (shared by the badge and the rail). |
| `src/copy.ts` | Every Turkish string that is not from the API or the generated labels. |
| `src/contract/` | Contract types and labels generated from `AI/contracts/codes.py`. |

## Rules the tests enforce (`src/design-rules.test.ts`)

- No hex colours inside components: use the tokens.
- No emoji in the interface and no remote URLs.
- The UI never compares a score with a threshold, never assigns `fired`,
  `active`, `suppressed` or `verdict`, and never sums or averages scores.

Also by convention: a missing value is shown as unavailable, never as `0`;
a degraded result is never shown as clean.

## Categories and colours

The panel lists only what the AI detects today (`AI/serving/capabilities.py`,
served through `/api/categories`). When a module starts emitting a new code,
it appears everywhere without a frontend change. Colours follow the family:
A red, B pink, C orange, D blue, and the model's general offensive score
("Genel saldırganlık") purple.
