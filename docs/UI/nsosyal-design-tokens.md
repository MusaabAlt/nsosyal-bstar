# NSosyal Design Tokens — for the ATI-SOSYAL moderation UI

Source: measured directly from nsosyal.com (CSS custom properties + Tailwind
numbered scale, read from `document.styleSheets` in the live app, Sep 2026).
Every value below is either `[css]` (read from their stylesheet) or
`[measured]` (sampled from screenshots). Nothing here is invented.
Stack: Next.js + Tailwind + shadcn/ui variables layered under a custom
Ant-Design-style numbered scale (`gray-1..13`, `blue-*`, `red-*`, `green-*`,
`balance-*`, `geekblue-*`).

---

## 1. Brand

- **Primary / accent — `#324BFF`** (indigo). Confirmed three independent ways:
  `--primary: hsl(233,100%,60%)` [css], `bg-blue-8: rgb(50,75,255)` [css],
  and the loading-gradient stop `#324bff` [css]. This is the one accent color
  to use for our own primary actions / focus / links.
- **Secondary accent — `#07D0E0`** (cyan). Appears ONLY inside the brand
  gradient, never as a standalone fill. Use it only as a gradient partner to
  `#324BFF`, not as a solid color.
- **Brand gradient** `linear-gradient(90deg, #07d0e0 0%, #324bff 100%)` [css].
  Used on their progress bar and the loading-screen glow. Reuse for our own
  loading/progress indicator so it reads as "the same app."

## 2. Surfaces

| Token | Light | Dark | Source |
|---|---|---|---|
| Page / feed background | `#FFFFFF` (`gray-1`) | `#1B1E26` (`gray-13`) | css+measured |
| Elevated / secondary surface | `#FAFAFA` (`gray-2`) | `#171A21` | css / measured |
| Card / popover (shadcn token, near-black — likely unused on real UI) | `#FFFFFF` | `#020817` | css (`--card`) |
| Post separator line | `#ECECEF` (`gray-4`) | `#252B3C` | css / measured |
| Input border | `hsl(214.3 31.8% 91.4%)` | `hsl(224 18% 17%)` (`--input`) | css |
| Active-nav pill background | `#D6E4FF` (`geekblue-2`) | `#242833` (`--border`) | css / measured |

Structural note: **NSosyal posts are NOT cards.** No border, no radius, no
gap — full-width rows separated by a single 1–2px horizontal line
(`gray-4` light / a dark separator around `#252B3C`–`#1C2029`). Our own
"post preview" mock in the demo UI should follow this — do not wrap it in a
rounded bordered card, or it will look off-brand.

## 3. Text

| Token | Light | Dark | Source |
|---|---|---|---|
| Display name / section header | `#232732` (`gray-11/12` range) | `#FAFAFA`–`#FBFBFB` | measured |
| Body text | `#3A4154` | `#DBDBDC` | measured |
| Muted (@handle, timestamp) | `#A7AAB4` (~`balance-5` `#C4C6CC` family, darker) | `#A7AAB2` | measured |
| Foreground (shadcn token) | `hsl(222.2 84% 4.9%)` | `hsl(210 40% 98%)` | css |

Font: `"Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`
[css, `--font-sans`]. Base size 16px [measured].

## 4. Semantic colors (for OUR verdict system — closest NSosyal equivalents)

NSosyal has red and green scales but no gold/amber scale came back from
extraction, so amber below is our own choice, flagged as such.

| Verdict | Color | Source |
|---|---|---|
| **engelle / block** (danger) | `#FF4D4F` (`red-5`) fill, `#CF1322` (`red-7`) for text/icon-on-light | css |
| **incele / review** (warning) | `#F5A623` (amber) — **our own pick, not sourced from NSosyal** | ours |
| **temiz / clean** (success) | `#52C41A` (`green-6`) | css |
| **nudge / hassas içerik** | reuse NSosyal's own sensitive-content pattern (§6) — do not invent a new color for this state | — |
| destructive (shadcn token, for reference) | `hsl(0 84.2% 60.2%)` light / `hsl(0 62.8% 30.6%)` dark | css |

## 5. Components

**Primary button** — 40px tall (`h-10`), 18px horizontal padding, **14px
corner radius** (`rounded-[0.875rem]`, NOT the global 8px `--radius` — radius
is per-component), `text-sm` → `text-base` at `xl:`, 22px icons. Default fill
is the brand gradient (`primary-gradient-1`); on hover it cross-fades to flat
`blue-5` `rgb(64,169,255)` over 300ms; pressed state `blue-7`; disabled state
`gray-8` text on `geekblue-2` background. Rendered as a pill shape at small
sizes (183×29px measured). **Reuse this exact hover crossfade** — it's a free,
recognizable brand detail.

**Global radius token** `--radius: 0.5rem` (8px) [css] — used for inputs/misc,
NOT buttons.

**Compose box** — placeholder: *"Gönderi oluşturmak için..."* [measured].
Collapsed height ~104px [measured]. Toolbar icons left→right: media, poll
(bar-chart), content-warning (info-circle), emoji, schedule (calendar-clock),
close-replies (overlapping speech bubbles) [measured]. Character limit:
**still unknown** — not captured in any screenshot.

**Post interaction row** — icons left→right: comment, repost, **rocket**
(their "like," NOT a heart — corrected from an earlier wrong guess), analytics
(bar-chart), bookmark, share [measured]. Each sits in a ~63×25px hit target
[measured] with a `#232732` hover pill in dark mode [measured].

**Avatar** — 33px diameter [measured], round [measured].

**Sensitive-content overlay ("Hassas İçerik")** — exact wording: *"Bu
gönderide, bazı insanların saldırgan, kırıcı veya rahatsız edici bulabileceği
hassas içerikler var."* with a single **"Göster"** button [css, i18n string].
This is the closest existing NSosyal component to our own "nudge" verdict —
**reuse this pattern for our warning state** rather than inventing a new one.
Exact blur/scrim values: still unknown, screenshot pending.

## 6. Layout (measured at a 2047×1051 window)

- Centre feed column: 616px wide
- Right sidebar: 234px wide
- Gap between feed and right sidebar: 20px
- (Left nav width and left↔feed gap: only the visible icon bbox was
  measurable, not the true container — treat as approximate)

## 7. Report / moderation vocabulary (their own strings — reuse for verdict copy)

Report reasons: *Taciz veya zorbalık · Nefret söylemi veya ayrımcılık · Spam
veya sahte hesap · Müstehcen içerik · Şiddet veya tehdit · Diğer*
Complaint categories add: *Dezenformasyon, Kimliğe Bürünme, Çocuk Güvenliği*
Moderation queue statuses: *Açık / İnceleniyor / Çözüldü / Reddedildi*
Moderation actions: *Onayla, Reddet, Çöz, Gönderiyi gizle, Gizlemeyi kaldır*

---

## STILL MISSING (blocking before final spec / before Design phase)

1. **Hassas İçerik overlay visuals** — scrim color/opacity, blur amount,
   button styling. Need one screenshot of an actual sensitive post pre-reveal.
2. **Character limit** on compose box (number itself never appeared).
3. **Focus ring, shadow/elevation values** — not present in the extracted
   root/dark blocks at all; NSosyal may simply not use box-shadows.
4. Two logo SVGs (light + dark) — still not retrieved.
5. Full 16-code content-label list with Turkish names, from you (not
   NSosyal) — needed to build the legend/tooltip copy in our own UI.
6. What a failed/unavailable module returns from the API (missing key vs.
   null vs. error) — needed for the graceful-degradation states.
7. Demo logistics: projector res/light, one screen vs. operator+mirror.
