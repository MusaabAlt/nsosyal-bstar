# Pages Specification — Moderation Console

**Read `design-system.md` first.** This file says what each screen contains and
in what order. It never defines how a component looks — that lives in the
design system. Where the two appear to disagree, the design system wins.

Values marked `[OPEN]` are not yet known. Stop and ask rather than choosing
one.

---

## 0. The situation this is built for

A judge walks up to a laptop, types a sentence, and has about ninety seconds.
They are technical enough to ask a hard question and not patient enough to read
a dashboard. Every element on screen must earn its place inside those ninety
seconds.

The argument the screen has to make: this is not one classifier producing one
toxicity score. Offensive speech is split into sixteen categories, each with
its own engine, its own threshold and its own action. The screen must make that
visible without becoming a spreadsheet.

The three moments it is built for, in order of importance:

**B — the deliberate silence.** The judge types `Çantayı götürmek zorundayım`,
an innocent Turkish word containing a profane substring. The system stays quiet
and the screen explains that the silence was a decision. This matters more than
anything else on the screen. Anything can flag everything; showing that
precision is intentional and measured is what separates a real system from a
demo.

**A — the catch.** The judge types an insult with letters swapped (`s4l4k`). A
keyword filter misses it; we catch it, and the screen shows what was hidden.

**C — the side by side.** A plain keyword filter runs on the same sentence next
to our system, and the judge watches it pass `s4l4k` while ours catches it. One
screen, two verdicts, one sentence. Not built yet — the space is reserved and
rendered as unavailable.

---

## 1. Application shape

Two routes, reached from a fixed sidebar.

```
┌────────────┬──────────────────────────────────────────────────┐
│            │                                                  │
│ İçerik     │                                                  │
│ Moderasyon │                                                  │
│ Paneli     │                   content area                   │
│            │                   max 1280px                     │
│ Analiz     │                                                  │
│ Kategoriler│                                                  │
│            │                                      [Temsili    │
│            │                                        veri]     │
└────────────┴──────────────────────────────────────────────────┘
```

Sidebar heading is plain text, 14px weight 500, muted. No logo, no version, no
avatar, no settings icon.

Default route is `Analiz`. The operator opens the console and is one keystroke
from analysing a sentence — no dashboard, no welcome screen, nothing before it.

**There is no history page, no settings, no accounts and no charts.** They
serve an operator, not a ninety-second demo, and each one is a surface that
looks like filler under jury questioning.

`Kategoriler` is not a dashboard. It is the only surface where sixteen separate
thresholds are visible at all, which is the central claim of the project, and
the main screen cannot show them because the API returns only the categories
that fired.

---

## 2. Analiz

One route, three states, never two at once.

### 2.1 Idle

```
  Analiz

  ┌──────────────────────────────────────────────────────────┐
  │ Analiz edilecek metni girin                              │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
                                             0            [Analiz et]

  Gizlenmiş hakaret    Zararsız benzerlik    Kalıp yargı
```

The text area, the character counter, the primary button. Beneath, a row of
preset buttons in `secondary` variant.

Presets are labelled by **what they demonstrate**, not by their content. A
juror reading `Gizlenmiş hakaret` learns what is about to happen; reading the
insult itself is noise. Clicking a preset fills the text area and does not
submit — the operator still presses the button, so the judge sees the action.

There must be at least one preset per demo moment: an obfuscated insult, a
guard-suppressed false positive, a clean sentence.

`[OPEN]` — the preset strings themselves.

Nothing else is on the page. The area below is empty: no placeholder report, no
skeleton, no sample output.

### 2.2 Analysing

The button disables and its label becomes `Analiz ediliyor`. The progress
indicator appears directly beneath the text area.

If the response arrives in under 400ms, hold this state until 400ms has elapsed
and then reveal. The backend is faster than perception and without the hold the
screen appears not to have reacted. **The latency shown in the report is always
the real measured value** — only the moment of reveal is delayed, never the
number.

### 2.3 Report

The text area stays above, editable, so the operator can immediately try
another sentence. The report fills the area beneath, in two columns.

```
  ┌───────────────────────────────────┐  ┌──────────────────┐
  │  Değerlendirme tamamlanmadı       │  │ Kullanıcıya      │
  │  16 kategoriden 4'ü değerlendirildi│ │ görünen          │
  │                          318 ms   │  │                  │
  ├───────────────────────────────────┤  │  ( mock post )   │
  │  Anahtar kelime │ Bu sistem       │  │                  │
  │  modül hazır değil                │  └──────────────────┘
  ├───────────────────────────────────┤
  │ 1  Girdi                  geçti   │     360px fixed
  ├───────────────────────────────────┤
  │ 2  Karakter güvenliği     geçti   │
  ├───────────────────────────────────┤
  │ 3  Gizleme tespiti   tetiklendi   │
  │    ...                            │
  ├───────────────────────────────────┤
  │ ... stages 4 – 8 ...              │
  └───────────────────────────────────┘
```

**The verdict and the latency sit at the top, not the bottom.** They are the
largest elements on screen and the judge reads them in the first second. The
stages beneath are the evidence for that verdict, read in the order the
pipeline ran.

Directly under the verdict, the comparison pair (design system 4.14), reserved
and rendered as unavailable until the baseline filter exists.

Then nine stage rows in sequence. Numbering is justified because the pipeline
genuinely executes in this order; nothing else in the application is numbered.

---

#### Stage 1 · `Girdi`

The submitted text exactly as typed, in evidence text, with its character count
beside it. No analysis. This stage exists so the jury can see that what was
analysed is exactly what was typed.

For input beyond roughly 600 characters, display truncates with a control to
expand; the full string was still submitted and analysed.

Status always `geçti`.

#### Stage 2 · `Karakter güvenliği`

Zero-width characters, homoglyphs, control characters.

Found — each rendered in position within the string, highlighted, with its
Unicode name beside it.
None — one line: `Şüpheli karakter bulunamadı`.

#### Stage 3 · `Gizleme tespiti`

Moment A. It answers, per pattern, whether that disguise was used.

One row per detected pattern: the Turkish pattern name, the exact substring
that triggered it, and the module's confidence in that detection to two
decimals.

Patterns checked but not matched are not listed individually. Beneath the list,
one line: `Kontrol edilen diğer N kalıpta eşleşme yok`, N from the response.

The disguises a juror is most likely to type, and what this stage must name for
each: `s4l4k` leetspeak · `s.a.l.a.k` punctuation split · `maaaaaal` character
repetition · `amq` abbreviation substitution.

`[OPEN]` — the complete pattern code list with Turkish labels.

#### Stage 4 · `Normalleştirme`

The most persuasive moment in the build. Give it room; this is the one place
where vertical generosity beats density.

Three elements stacked: the original string in evidence text with the removed
or substituted characters highlighted; one line stating what changed
(`4 ayırıcı karakter kaldırıldı`); the recovered string with the recovered root
highlighted.

Then, when the API supplies both, the score pair (design system 4.10): the
model's score on the raw text and on the recovered text, side by side. Those
two numbers explain the entire project without a sentence.

`[OPEN]` — whether the response carries a pre-normalisation score. If it does
not, this element is omitted entirely; it is never computed by the interface.

#### Stage 5 · `İçerik sınıflandırma`

One threshold bar (design system 4.9) per category returned. The API returns
only categories that fired plus near-misses, so the list is short by design.

Fired categories first, then near-misses, each ordered by score descending.

Beneath the list, one line accounting for the remainder:
`Eşik altındaki N kategori gösterilmiyor`, linking to `Kategoriler`.

Sixteen rows of scores must never render by default.

#### Stage 6 · `Hedef`

Target type in Turkish — `birey`, `grup`, `insan dışı`, `yok` — and the
evidence substring that identified it, highlighted in position within the text.

#### Stage 7 · `Koruyucu kontroller`

Moment B, and the stage that proves precision. **It carries more visual weight
than stage 3**, and at least as much as stage 5. A stage that looks empty here
undersells half the system: an empty result with no explanation reads as "the
system did nothing".

A guard fired — its Turkish name, and a full sentence naming what it prevented.
For substring collision specifically: the innocent word rendered in evidence
text with the profane substring underlined inside it, and a sentence stating
plainly that the system recognised the containing word and chose not to flag
it.

No guard fired — one line: `Hiçbir koruyucu kontrol tetiklenmedi`.

`[OPEN]` — the guard code list with Turkish labels, and whether the response
identifies the specific substring and containing word or only that a guard
fired. Without the specifics, this moment cannot be shown at full strength.

#### Stage 8 · `Zincir değerlendirmesi`

Sender-to-target repetition count and whether escalation applied. For a single
post with no thread context: status `uygulanmadı`, with one line explaining
that this input was evaluated as a single post.

`[OPEN]` — how a thread is submitted, and whether thread mode appears in the
demo at all. If it does not, the stage still renders, permanently
`uygulanmadı`.

#### Stage 9 · `Karar gerekçesi`

Not a second verdict — the verdict is already at the top. This stage states in
one or two plain sentences which stages produced the outcome, naming them, so
the conclusion is traceable to something visible above it rather than asserted.

---

### 2.4 Incomplete evaluation — the common case

Most detection modules are still stubs, so **most results today are incomplete
rather than clean**. This is the state the interface renders most often and it
is designed first, not last.

When any module did not run, the verdict at the top is the incomplete
evaluation block (design system 4.12): `Değerlendirme tamamlanmadı`, the names
of the parts that did not run, and the line
`16 kategoriden N'i değerlendirildi`.

Each stage whose module is a stub shows status `modül hazır değil`, distinct
from `veri yok`, which means the module ran and found nothing.

It is never green and never says `Temiz`. A confident pass rendered over twelve
modules that never ran is the single worst failure this interface can produce,
and the one a hard question from a judge will expose immediately.

Handled well, this state is a credibility asset rather than damage control: a
system that names what it has not yet evaluated reads as honest engineering.

`[OPEN]` — how many of the sixteen categories genuinely run today, and what the
response looks like for the ones that do not. This determines how much of the
build is this state.

### 2.5 Consequence column

Fixed 360px, right. Heading `Kullanıcıya görünen`.

Renders the analysed text as an end user would see it on NSosyal: round 33px
avatar, display name, handle, timestamp, body text, and the interaction row —
comment, repost, rocket, chart, bookmark, share. Full-width row with a
`--border-divider` beneath, no radius, no card.

**This column contains no numbers.** It answers "so what happens to the post",
and it is where a non-technical juror looks.

By verdict:

- `Temiz` — the post renders normally.
- `Uyarı` / `İncele` — the post renders with a muted line above it saying it
  was queued for review.
- `Hassas içerik` — the body renders behind NSosyal's own sensitive-content
  treatment: blurred body, scrim, the exact string `Bu gönderide, bazı
  insanların saldırgan, kırıcı veya rahatsız edici bulabileceği hassas
  içerikler var.` and one `Göster` button revealing it on click.
  `[OPEN]` — blur radius and scrim opacity, to be measured from the live app.
- `Engelle` — the post does not render; one muted line says it was not
  published.
- `Değerlendirme tamamlanmadı` — the post renders normally with a muted line
  above it stating the evaluation did not complete. It must not imply the post
  was cleared.

---

## 3. Kategoriler

A static reference listing all sixteen content categories with their
thresholds.

It exists for one reason: the API returns only fired categories and
near-misses, so `Analiz` can never display all sixteen. Without this page there
is nowhere to show a juror that sixteen independent thresholds exist, which is
the central claim of the project. When a judge asks what the categories are,
the operator clicks one item in the sidebar.

A table: code, Turkish label, one-line definition, threshold, the action firing
it produces, and whether that module is live or still a stub.

Grouped into the four families with a plain heading above each group. The
grouping is a real taxonomy, not a visual device, so it carries information.

No scores appear here — no analysis has run. Thresholds only.

`[OPEN]` — the sixteen codes with exact Turkish labels, definitions, current
thresholds and resulting actions. **This page cannot be built at all until that
list exists.** It is the single largest content gap in the project.

---

## 4. Behaviour across the application

**Missing data.** If a response section is absent, its stage renders `veri yok`
or `modül hazır değil` and one line naming what produced no output. It never
renders `0.00`.

`[OPEN]` — the exact shape of a failed or stubbed module in the response: key
absent, `null`, empty collection, or request error. Every rule in this section
depends on knowing this.

**Backend unreachable.** The report area shows an error state (design system
4.18): one line saying the analysis service did not respond, and a
`Tekrar dene` button.

**Long input.** Up to 5000 characters is accepted and submitted in full;
display truncates. Submission is never blocked by length.

**Mixed scripts.** A string mixing Arabic, Latin and Cyrillic must render and
submit without breaking layout or alignment.

**Empty input.** The submit button is disabled. No validation message appears
before the operator has done anything wrong.

---

## 5. Build order

1. Tokens, shell, routing, self-hosted font, inline icons.
2. `Analiz` idle state.
3. **The incomplete evaluation state**, end to end. It is the most common
   output and defines how every stage degrades. Building it first prevents the
   whole interface being designed around a clean path that rarely occurs.
4. Stage row, then stages 1, 2 and the verdict — the skeleton.
5. **Threshold bar and stage 5.** The hardest component and the one carrying
   the argument. If it is wrong, nothing else matters.
6. Stage 7, the guards. Moment B outranks moment A.
7. Stages 3 and 4, the obfuscation reveal and the score pair.
8. Consequence column.
9. Comparison pair, rendered unavailable.
10. `Kategoriler`, once the sixteen-code list arrives.
11. Error states, long input, mixed scripts. Last in order, but budget real
    time — these are what fail in front of a jury.

Stop at every `[OPEN]` rather than choosing a value.

---

## 6. Open items, ordered by how much they block

1. How many of the sixteen categories run today, and what the response contains
   for the ones that do not. Determines the shape of the whole build.
2. The sixteen codes with Turkish labels, definitions and thresholds. Blocks
   `Kategoriler` entirely and stage 5's copy.
3. The failure and stub shape per response section. Blocks all degradation
   states.
4. Three real, unedited JSON responses from actual runs — an obfuscated insult,
   a guard-suppressed false positive, a clean sentence. Build against these,
   not against a described schema.
5. Obfuscation pattern codes with Turkish labels.
6. Guard codes with Turkish labels, and whether substring collision reports the
   specific substring and containing word.
7. Whether the response carries a pre-normalisation score, enabling the score
   pair.
8. Endpoint URL, method, request shape.
9. Preset demo strings.
10. Thread submission mechanics, and whether thread mode is demonstrated.
11. Whether a baseline keyword filter can run on the same input.
12. Sensitive-content blur and scrim values.
13. Projector resolution, and whether the operator has a separate screen.
