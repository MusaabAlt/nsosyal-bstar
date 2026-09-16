# Moderation console (frontend)

Vue 3 + Vuetify + Tailwind. Every visual decision comes from `docs/UI/`
(`design-system.md` is binding). Runs fully offline: Inter is bundled, icons
are inline SVG.

```bash
npm install
npm run dev              # http://127.0.0.1:5173 (proxies /api to the Go backend on :8080)
npm test                 # unit, component and design-rule tests
npm run build            # type-check + production build into dist/
npm run check:offline    # fails if dist/ references any external host
node scripts/gen-labels.mjs   # regenerate Turkish labels after AI/contracts/codes.py changes
```

## Where things are

| Path | What |
|---|---|
| `src/styles/tokens.css` | design tokens (design-system 2), the only place colours are defined |
| `src/components/ui/` | the design-system components (section 4), each built once |
| `src/components/report/` | the nine report stages and the consequence column (pages-spec 2) |
| `src/report/model.ts` | reads an AnalysisResult into what the screen shows; makes no decisions |
| `src/copy.ts` | every Turkish string that is not from the API or the contract labels |
| `src/contract/` | contract types and labels generated from `AI/contracts/codes.py` |
| `src/api/` | data sources: sample payloads (`mockSource.ts`) and the Go API |

## Preview states with sample data

`/?mock=network`, `?mock=400`, `?mock=404`, `?mock=413`, `?mock=500`,
`?mock=decision-null`. Presets cover flagged, guard-suppressed and clean;
any other text returns the degraded payload.

## Open values

- `--sensitive-blur` and `--sensitive-scrim` in `tokens.css` are provisional:
  the NSosyal overlay values were never measured.
- Kategoriler shows definition, threshold, action and module status as
  `veri yok` until the API serves them.
