# ADR-001 — Guard scoping by module and span

- **Status:** accepted
- **Date:** 2026-09-14
- **Scope:** `contracts/schema.py` (deliberate one-time unfreeze), `decision/fusion.py`, `modules/m1_lexicon/spec.md`, `modules/m6_target/spec.md`

## Context: the exploit

Guards are negative controls that suppress a positive decision. Until this
decision, `decision/fusion.py` let an active guard clear **every** fired
content code in the families its config lists, across the **whole post**,
regardless of which module raised it or which words triggered it.

Demonstrated during the audit of commit `4b07bc6`, in memory:

- m1_lexicon emits `A2 = 0.99` for an insult, and a `SUBSTRING_COLLISION`
  guard (`0.99`) for the innocent word `amcam` elsewhere in the same post.
- Verdict: **clean** — "'Bireye yönelik küfür' (A2) sinyali 'Alt dizi
  çakışması' koruması nedeniyle bastırıldı, içerik temiz kabul edildi."

Once m1 is live, appending `amcam` (or `sikke`, `klasik`, ...) to any insult
clears family A. Anyone can demonstrate it.

Module identity alone cannot fix this: the profane root and the innocent
collision both come from m1. Span overlap is what separates "`göt` inside
`götürmek`" from "an insult that also happens to contain `amcam`".

## Decision

### Contract change (one decision, both fields)

`contracts/` was opened **deliberately and once** for exactly these two
optional, backward-compatible fields:

1. `GuardResult.span: Span | None = None` — exact substring of the original
   text that triggered the guard; `GuardResult.source` became optional
   (`= ""`), naming the module that raised it.
2. `ContentScore.span: Span | None = None` — placed after `source`; exact
   substring of the original text that triggered the score.

The contract is **re-frozen immediately after this change**. Any further
edit to `contracts/` needs a new explicit instruction and a new ADR.

### Suppression rule

A guard suppresses a content score only if **all** of these hold:

1. the guard is active (score ≥ its threshold in `thresholds.yaml`);
2. the score's code or family is in that guard's `suppresses` list;
3. the guard's source module is the module that produced the score
   (`"m1_lexicon@raw"` → module `m1_lexicon`); a guard with no source
   suppresses nothing;
4. if both sides carry a span, the spans overlap;
5. if either side has no span, fall back to same-module suppression — only for a module that
   declares `emits_spans = False` (see Amendment).

A guard never suppresses across modules, and never suppresses a whole family
across the whole post.

### Ordering inside the decision layer

Thresholds and guards are applied to each per-module, per-channel score
**before** channel/source fusion. Fusion keeps one score per code, and
applying guards after it would let an m1 guard erase an independent m3 score
for the same code — cross-module suppression by the back door. Fusion now
prefers the strongest still-fired score, so a suppressed score never hides a
fired one.

### Obligation on modules

Because rule 5 falls back to same-module suppression, a module that omits
spans reopens the exploit for itself. Emitting spans is therefore an
**acceptance criterion**, not an option: every match and every guard of
m1_lexicon, and every guard and B4 score of m6_target (the modules whose
specs raise guards), must carry the span of the exact triggering substring.
A match or guard with no span is a contract violation.

## Amendment — runtime span enforcement (2026-09-14, Phase 10)

**Why:** the re-audit showed the rule-5 fallback had become a bypass. A module
that simply omitted spans got same-module suppression back, and the original
exploit returned (insult + `amcam` without spans → clean). A requirement that
lives only in spec.md is not a requirement.

**Decision:**

1. Every module declares, as a class attribute, whether its content scores and
   guards carry spans: `emits_spans = True | False`. The architecture test
   requires the declaration on every registered module. m1_lexicon and
   m6_target declare `True`; m0, m2 (emit no scores or guards), m3, m4 and m5
   (whole-post scores) declare `False`.
2. At runtime the pipeline drops any content score or guard without a span from
   a module that declares `True` — or declares nothing, since the fallback must
   be opted into. The drop is recorded in notes, the item is never applied, and
   the module is marked degraded (Phase 9).
3. The no-span same-module fallback survives only for modules that explicitly
   declare `emits_spans = False`. The decision layer checks this again
   (`guard_applies` reads `signals.pipeline.emits_spans`, which the pipeline and
   the eval harness both set). A caller that builds an AnalysisResult by hand
   without that signal gets the old fallback; only pipeline/harness results
   are covered.

**Consequence for the exploit:** insult + `amcam` now ends in block both with
spans (the guard does not overlap the insult) and with a spanless guard (the
guard is dropped and never applied); a fully spanless m1 output is dropped
entirely and ends in review, never clean
(`tests/test_pipeline.py::SpanEnforcementTest`).

## Consequences

- `tests/test_decision.py::test_guard_suppresses_family` was replaced by
  `test_guard_suppresses_only_overlapping_same_module_score`, plus tests for
  the exploit (`test_insult_plus_unrelated_collision_still_blocks`),
  cross-module isolation, both fallback paths, a guard without source, and
  fusion not hiding another module's score.
- `signals.decision.channel_scores` now records span, threshold and fired for
  every pre-fusion score, so every suppression is auditable.
- Modules that raise guards must be able to compute original-text offsets
  (m0 publishes `signals.m0_charsafe.offsets` for this).
