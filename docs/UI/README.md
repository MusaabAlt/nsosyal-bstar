# Handover — Moderation Console UI

Three files. Read them in this order.

1. **`design-system.md`** — the binding reference. Colours, type, spacing,
   every component with all its states, and a list of prohibitions. Nothing may
   be designed outside this file. If a value is not in it, ask rather than
   choose.

2. **`pages-spec.md`** — what each screen contains and in what order. Two
   routes: `Analiz` and `Kategoriler`. It never defines how a component looks;
   that is the design system's job.

3. **`nsosyal-design-tokens.md`** — evidence. Every colour and measurement was
   read from the live NSosyal application. Keep it for provenance; you will not
   normally need to open it.

## Why these files are written this way

The interface will be built with AI assistance, and AI-assisted builds drift
toward a recognisable generic look: all-caps labels, rounded cards with soft
shadows, gradient decoration, monospace for small numbers, arrows on buttons.
Section 7 of the design system names those patterns and forbids each one. Treat
that section as a checklist before every commit, not as advice.

## Two things that will break the demo if missed

**Offline.** The room has no network. Inter must be self-hosted as bundled
`.woff2`, icons must be inline SVG. Test by disabling the network entirely and
reloading; if anything changes appearance, it is a defect.

**Every number comes from the API.** The interface computes nothing — no
averages, no percentages, no derived confidence. A missing value renders as
unavailable, never as `0.00`. A zero and a missing value look identical to a
juror and one of them is untrue.

## Before writing code

Seven answers are needed. The first three block the build.

1. How many of the sixteen categories genuinely run today, and what the
   response contains for the ones that do not.
2. The sixteen codes with exact Turkish labels, definitions and thresholds.
3. The shape of a stubbed or failed module in the response: key absent, `null`,
   empty collection, or request error.
4. Three real, unedited JSON responses from actual runs — an obfuscated insult,
   a guard-suppressed false positive, a clean sentence.
5. The obfuscation pattern codes and guard codes, with Turkish labels.
6. Endpoint URL, method, request body shape.
7. The preset demo strings.

Build against the real responses, not against a schema described in prose.
Where a `[OPEN]` marker appears in either specification, stop there.

## Build order

It is set out at the end of `pages-spec.md` and it is not the obvious one. The
incomplete-evaluation state is built third, before the clean path, because most
modules are still stubs and incomplete is the output the screen will render
most often. Building the clean path first produces an interface designed around
a case that rarely occurs.
