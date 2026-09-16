# Design System — Moderation Console

**Authority.** This file is the only source of visual decisions. If a value is
not defined here, it is not to be invented — ask. A component that does not
appear in section 4 does not exist; adding one means adding it here first.

This document exists because the interface will be built with AI assistance,
and AI defaults toward a recognisable generic look. Section 7 lists what that
look consists of and forbids it explicitly.

**Provenance.** Colour and component values are measured from the live NSosyal
application; the measurements are recorded in `nsosyal-design-tokens.md`. That
file is evidence. This file is the instruction.

**Scope.** Dark theme only. Desktop only, 1280px and above. Fully offline.

---

## 1. Principles

The product is an internal trust-and-safety tool operated by one person who
reads numbers and makes judgements, in front of a jury, on a projector. It is
not a consumer product and must not look like one.

**Neutral by default.** An idle screen is greyscale. Colour enters only where
it carries meaning — a verdict, a status, a focus ring. If a colour can be
removed without losing information, remove it.

**Structure over decoration.** Hierarchy comes from spacing, weight and
dividers. Never from shadows, gradients, coloured panels or rounded cards.

**Never colour alone.** Every state that is communicated by colour is also
communicated by a word. A juror six metres away, or colour-blind, must reach
the same conclusion.

---

## 2. Foundations

### 2.1 Colour

Declared once as CSS custom properties. Components reference the semantic name
only. A raw hex value inside a component is a build error.

```
/* surfaces */
--surface-page:        #1B1E26;
--surface-raised:      #171A21;
--surface-hover:       #242833;
--surface-selected:    #242833;

/* lines */
--border-default:      #242833;
--border-divider:      #252B3C;
--border-strong:       #363C4C;

/* text */
--text-primary:        #FAFAFA;
--text-body:           #DBDBDC;
--text-muted:          #A7AAB2;
--text-disabled:       #666C7B;
--text-on-accent:      #FFFFFF;

/* accent — interaction only, never decoration */
--accent:              #324BFF;
--accent-hover:        #40A9FF;
--accent-pressed:      #096DD9;
--accent-subtle:       rgba(50, 75, 255, 0.10);

/* semantic — meaning only */
--status-block:        #FF4D4F;
--status-block-bg:     rgba(255, 77, 79, 0.08);
--status-review:       #F5A623;
--status-review-bg:    rgba(245, 166, 35, 0.08);
--status-clean:        #52C41A;
--status-clean-bg:     rgba(82, 196, 26, 0.08);
--status-neutral:      #A7AAB2;
--status-incomplete:   #A7AAB2;
--status-incomplete-bg: rgba(167, 170, 178, 0.08);
```

`--status-review` is our own value. Every other colour is measured from
NSosyal.

**Colour budget.** At most three coloured elements visible at once, text
excluded. A fourth means one of them is decoration.

### 2.2 Typography

One family: **Inter**, self-hosted (see 9.2). No second family. No monospace
except where 4.11 permits it.

| Role | Size | Weight | Line height | Colour |
|---|---|---|---|---|
| Verdict | 40px | 600 | 1.15 | status colour |
| Metric (latency) | 32px | 500 | 1.2 | `--text-primary` |
| Page title | 20px | 600 | 1.3 | `--text-primary` |
| Section heading | 15px | 500 | 1.4 | `--text-primary` |
| Body | 16px | 400 | 1.6 | `--text-body` |
| Body small | 14px | 400 | 1.5 | `--text-body` |
| Label | 14px | 500 | 1.4 | `--text-muted` |
| Caption | 12px | 400 | 1.4 | `--text-muted` |

Nothing below 12px. Nothing above weight 600. Headings in **sentence case** —
`Tetiklenen kategori`, never `TETİKLENEN KATEGORİ`.

Prose lines do not exceed 80 characters.

### 2.3 Spacing

One scale, no value outside it:

```
4 · 8 · 12 · 16 · 24 · 32 · 48
```

8px inside a control · 12px label to field · 16px between related rows · 24px
between sections · 32px page padding · 48px between major regions.

### 2.4 Radius

```
--radius-control: 6px;   /* buttons, inputs, chips, evidence blocks */
--radius-none:    0;     /* rows, table cells, dividers, stages */
```

Two values. Rows are never rounded.

### 2.5 Borders and elevation

Borders 1px `--border-default`. Row dividers 1px `--border-divider`.

**No shadows anywhere**, including modals and dropdowns — those use 1px
`--border-strong`.

### 2.6 Motion

```
--motion-fast:   120ms ease-out;   /* hover, focus, press */
--motion-normal: 200ms ease-out;   /* expand, reveal */
```

Motion answers a user action or shows progress. Nothing else.

Prohibited: page-load entrance animations, fade-and-slide-up on sections,
looping animation, hover transforms that move elements, parallax.
`prefers-reduced-motion` disables all of it except the progress indicator.

### 2.7 Focus

Every interactive element shows a 2px solid `--accent` ring at 2px offset.
Never remove an outline without replacing it. The ring must be visible on a
projector, so it is never subtle.

---

## 3. Grid

Content column max 1280px, centred, 32px side padding.

Sidebar fixed 220px, full height, `--surface-raised`, 1px right border.

The analysis page splits the content area: report column flexible, consequence
column fixed 360px, 32px gutter.

---

## 4. Components

Each component defines its sizes and all of its states. No component may be
used in a size or state not listed here.

### 4.1 Button

| Variant | Background | Text | Border |
|---|---|---|---|
| `primary` | `--accent` | `--text-on-accent` | none |
| `secondary` | transparent | `--text-body` | 1px `--border-default` |
| `ghost` | transparent | `--text-muted` | none |

No destructive variant — nothing in this application deletes anything.

**Sizes.** `md` 36px tall, 16px horizontal padding, 14px text weight 500.
`sm` 28px tall, 12px padding, 13px text weight 500. No other size.

Radius `--radius-control`. Square-shouldered, never a pill.

**States.** Hover: `primary` → `--accent-hover`; `secondary` background →
`--surface-hover`; `ghost` text → `--text-body`. Pressed: `primary` →
`--accent-pressed`, no scale transform. Disabled: 50% opacity, `not-allowed`,
no hover response. Loading: label becomes the progressive form of the action
(`Analiz et` → `Analiz ediliyor`) and the button disables — **no spinner
inside the button**. Focus: ring per 2.7.

Text only, sentence case, no icons, no arrows appended.

### 4.2 Icon button

28×28px, transparent, `--radius-control`, inline SVG icon at 16px. Hover
background `--surface-hover`. Requires `aria-label`. Used only in the mock
social post interaction row.

### 4.3 Text area

Full column width. Minimum height 120px, vertically resizable only. Background
`--surface-raised`, 1px `--border-default`, `--radius-control`, 16px padding,
16px text.

Placeholder `--text-muted`. Focus replaces the border with 1px `--accent` plus
the ring. Character counter below-right at 12px `--text-muted`.

**The counter never blocks submission.** Input up to 5000 characters is
accepted. Past 1000 characters the counter turns `--status-review` as
information, not as an error, and display of the text truncates while the full
string is still submitted.

### 4.4 Text input

Single line, 36px tall, otherwise as 4.3.

### 4.5 Segmented control

Two to four options in one row, 1px `--border-default`, `--radius-control`,
dividers between segments. Each segment 32px tall, 12px padding, 13px weight
500, `--text-muted`. Selected: `--surface-selected` background,
`--text-primary` text. No sliding indicator.

### 4.6 Navigation item

40px tall, full sidebar width, 16px padding, 14px weight 500, `--text-muted`,
radius 0.

Selected: `--surface-selected` background, `--text-primary` text, 2px
`--accent` bar on the left edge. **This is the only left accent bar permitted
anywhere in the system.**

### 4.7 Status word

Status is a **word**, optionally preceded by a 6px dot. Never a dot alone,
never a filled pill badge.

| Meaning | Turkish | Colour |
|---|---|---|
| ran, nothing found | `geçti` | `--status-clean` |
| triggered | `tetiklendi` | `--status-block` |
| below its threshold | `eşik altında` | `--status-neutral` |
| not applicable to this input | `uygulanmadı` | `--status-neutral` |
| module not available | `modül hazır değil` | `--status-incomplete`, italic |
| returned nothing | `veri yok` | `--status-incomplete`, italic |

13px weight 500. The last two are distinct and must not be merged: one means
the module does not exist yet, the other means it ran and produced nothing.

### 4.8 Stage row

The repeating unit of the report. Full width, no card, no radius, no
background, 1px `--border-divider` beneath, 16px vertical padding.

Header line: stage number 14px `--text-muted`; stage name 15px weight 500
`--text-primary`; status word (4.7); duration right-aligned 13px
`--text-muted`, formatted `2.4 ms`.

Body 12px below the header, indented to the stage name.

**A stage never collapses to nothing.** A stage with no findings still renders
one line of 14px `--text-muted` saying what was not found. The operator must
be able to tell "ran and found nothing" from "did not run".

### 4.9 Threshold bar

The component that carries the project's argument. It shows one category
against **its own** threshold.

4px tall, full column width, `--radius-none`, track `--surface-hover`.

Fill from the left, width proportional to the score on 0–1. Fill is
`--status-block` when the category fired, `--status-neutral` when it did not.

**The threshold tick:** 2px wide, 10px tall, drawn on the bar at the
threshold's own position in `--text-primary`, extending 3px above and below
the track so it is unmistakably a separate object from the fill.

Above the bar: category label 15px weight 500 left; score 15px weight 500
right, in the fill colour, two decimals.
Under the tick: `eşik 0.62` at 12px `--text-muted`.
Beneath: one sentence at 14px `--text-body` stating the relationship in words,
`Skor kendi eşiğini 0.32 puan aşıyor`.

The design must make 0.42-fired-at-threshold-0.40 and
0.42-not-fired-at-threshold-0.55 visibly different at a glance.

**Prohibited:** aggregating categories into one bar, an average, a combined
confidence score, or any single global threshold. The system's claim is that
no global threshold exists; rendering one contradicts the product.

### 4.10 Score pair

Two numbers side by side: the model's score on the raw text, and on the
recovered text after de-obfuscation.

Each rendered at 32px weight 500 with a 14px `--text-muted` label beneath
(`ham metin`, `çözülmüş metin`). The left number in `--text-muted`, the right
in `--status-block` when it crosses its threshold. Between them, a plain arrow
glyph at 24px `--text-muted`.

These two numbers explain the entire project without a sentence. Render them
only when the API supplies both — never compute one.

### 4.11 Verdict block

Full width. Background the status background token, 1px border in the status
colour, `--radius-control`, 24px padding. **No left accent bar.**

Verdict word at 40px weight 600 in the status colour, and beneath it one
sentence at 16px `--text-body` naming the stage that produced the outcome.

Words: `Engelle` · `İncele` · `Hassas içerik` · `Uyarı` · `Temiz` ·
`Değerlendirme tamamlanmadı`.

### 4.12 Incomplete evaluation block

**The most frequently rendered state in this build**, because most detection
modules are still stubs. It is a first-class state, never a variation of a
pass.

Rendered as a verdict block using `--status-incomplete` and the word
`Değerlendirme tamamlanmadı`. Beneath the word, in place of the single
sentence: a plain list of which parts did not run, by name, in
`--text-body` at 16px, and one line stating how many of the sixteen categories
were evaluated — `16 kategoriden 4'ü değerlendirildi`.

It must never be green, never say `Temiz`, and never borrow the clean colour.
A jury reading a confident pass over twelve modules that never ran is the
single worst failure this interface can produce.

### 4.13 Evidence text

The only permitted monospace, because character-level alignment carries
meaning. System monospace stack at 15px, `--text-body`, background
`--surface-raised`, 12px padding, `--radius-control`.

Highlighted characters: background at 20% opacity of `--status-block`, text
unchanged.

Underline is reserved for exactly one purpose: marking a profane substring
inside an innocent word when a guard suppresses it. 1px underline in
`--status-clean`.

### 4.14 Comparison pair

Two verdicts on the same sentence, side by side: a plain keyword filter and
our system. Two equal columns separated by a 1px `--border-default` vertical
rule, each with a 14px `--text-muted` label above (`Anahtar kelime filtresi`,
`Bu sistem`) and a verdict word beneath at 24px weight 600.

**Not yet built.** Reserve the space and render it with both columns in the
`modül hazır değil` state until the baseline filter exists. Do not fabricate a
baseline verdict.

### 4.15 Table

Header 40px, 13px weight 500 `--text-muted`, 1px bottom `--border-default`,
sticky. Body rows 44px, 14px `--text-body`, 1px `--border-divider` beneath, no
radius, no zebra striping. Numeric columns right-aligned with tabular figures.

### 4.16 Progress indicator

2px tall, full container width, `--surface-hover` track, filled with the
NSosyal brand gradient `linear-gradient(90deg, #07d0e0, #324bff)`.

**The only gradient permitted anywhere in the application**, and only here,
because it encodes progress. No spinners exist in this system: the backend
responds in tens of milliseconds and a spinner implies waiting, contradicting
the performance claim the demo makes.

### 4.17 Empty state

One line of 14px `--text-muted` stating plainly what is absent, plus where
applicable one `secondary` button offering the action that fills it. No
illustration, no icon, no heading.

### 4.18 Error state

One line of 16px `--text-body` stating what failed in plain terms, and one
`secondary` button naming the retry action. No red banner, no alert dialog, no
apology, no error code the operator cannot act on.

### 4.19 Demo marker

While mock data is rendered, a fixed chip at bottom-right: 12px
`--status-review` text, 1px `--status-review` border, transparent background,
`--radius-control`, 8px padding. Text: `Temsili veri`.

Removed by one flag when real data is wired. It must never read
`DEMO — TEMSİLİ VERİ`.

---

## 5. Language

Turkish on screen. English for code, comments, identifiers, file names.

Sentence case everywhere. No ALL-CAPS labels. No emoji.

Buttons name what happens: `Analiz et`, `Göster`, `Tekrar dene`. A verb keeps
its form through the flow — `Analiz et` leads to `Analiz ediliyor`.

Errors say what happened and what to do. They do not apologise and are never
vague.

Numbers: scores to two decimals, latency to one decimal with the unit as a
separate smaller element. Never invent, round up or pad a number the backend
did not return.

---

## 6. Numbers rule

Every number on screen comes from the API response. The interface computes
nothing — no averages, no percentages, no derived confidence, no totals.

A missing value renders as unavailable (4.7), never as `0.00`. A zero and a
missing value are indistinguishable to a juror and one of them is untrue.

---

## 7. Prohibitions

Each of these is a build failure, not a style disagreement. They are listed
because they are the defaults an AI-assisted build drifts toward.

1. ALL-CAPS labels above content.
2. The `WORD — fragment` pattern with a spaced em dash.
3. Monospace outside 4.13.
4. Any gradient outside 4.16.
5. Any `box-shadow`.
6. Rounded cards as the page's structural unit.
7. Arrows appended to button text.
8. Coloured left accent bars, except the navigation indicator in 4.6.
9. Entrance animations on page load.
10. Emoji.
11. Any logo, wordmark or brand icon.
12. Raw hex values inside components.
13. A combined, averaged or global confidence score.
14. Rendering `0.00` where the response contained no value.
15. Numbered markers on content that is not an ordered sequence. The analysis
    stages are a genuine sequence and may be numbered; nothing else may.
16. Colour carrying meaning without an accompanying word.
17. A green pass rendered while modules did not run.

---

## 8. Quality floor

Contrast at least 4.5:1 for all text including muted, verified rather than
assumed. Full keyboard operability with visible focus. Semantic HTML — `table`
for tables, `button` for buttons. `prefers-reduced-motion` respected.

Readable from six metres on a projector in a lit room.

Must not break on a 5000-character input or on text mixing scripts, including
Arabic, Latin and Cyrillic in one string.

---

## 9. Implementation

### 9.1 Structure

Tokens live in one `tokens.css` as custom properties. Components import
nothing else for colour.

Every component in section 4 is built once and reused. A second button
implementation anywhere in the codebase is a defect.

Recommended base: **shadcn/ui**, since NSosyal itself is built on it and the
token names already align, then overridden to match this document. Building
from scratch is acceptable; matching this document is not optional either way.

### 9.2 Offline — hard requirement

The demo room has no network. Anything fetched at runtime will fail in front
of the jury.

- Inter must be self-hosted as local `.woff2` files, bundled. No Google Fonts
  link, no `@import` from a remote origin.
- Icons must be inline SVG in the source. No icon package loaded at runtime,
  no icon CDN, no sprite fetched over the network.
- No remote CSS, no analytics, no telemetry, no font-display fallback that
  depends on a network round trip.
- Verify by disabling the network entirely and reloading. If anything changes
  appearance, it is a defect.
