# M0 — Character Safety

**Type:** representation (not a detector)
**Owner:** Musaab
**Status:** reference implementation — copy its shape, not its rules

---

## 1. Objective

Stop the text from lying at the character level before any model sees it.

Three attack families are in scope:

1. **Invisible characters** — zero-width space/joiner, bidirectional overrides, control characters. The text looks identical to a human and is completely different to a tokenizer.
2. **Homoglyphs** — a Cyrillic `а` inside a Latin word. Visually identical, different codepoint, so every lexicon and every tokenizer misses it.
3. **The Turkish casing bug** — most Unicode software uppercases `ı` to `I` but lowercases `I` to `i` unless the locale is Turkish. This silently changes the letter and the round trip is lost.

The third one is not an attack; it is a bug that **creates false positives out of clean text**. `SIKINTI` ("trouble") lowercased with English rules becomes `sikinti`, which contains a profane root. This is the single most important thing this module prevents.

---

## 2. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| Zero-width and control characters | leetspeak (`s4l4k`) → M2 |
| Bidi override marks | letter repetition → M2 |
| Cross-script look-alike letters | spacing/punctuation splits → M2 |
| Turkish dotted/dotless casing errors | anything semantic → M3/M4 |
| Styled Latin letters: fullwidth, mathematical, circled, squared, negative circled/squared, parenthesized, superscript and subscript letters, small capitals, regional indicators that are not flags (`HOMOGLYPH`) | accent normalisation (`áptal` → `aptal`) → M2 |

M0 does **not** decide whether text is offensive. It has no opinion on content.

**Known, tested limitation — words spelled from flag pairs.** Styled Latin letters, including regional indicator letters (🇦🇵🇹🇦🇱), are mapped to plain letters as `HOMOGLYPH`. A pair of regional indicators is also a flag (🇹🇷), which is ordinary in Turkish posts, so a run made only of valid region pairs is left untouched. Consequence: a word spelled entirely from valid flag pairs (for example `SI` + `KE`) passes m0 unmapped, because it is indistinguishable from a row of flags. An odd-length run, or one containing any pair that is not a region, is mapped. Accepted by the project owner; pinned by `test_word_spelled_only_from_valid_flag_pairs_passes` in `test_unit.py`, so a change in either direction is deliberate.

---

## 3. Contract

**Reads:** `ctx.text` (never mutated)

**Writes:**
- `out.charsafe_text` — the cleaned string
- `out.form.patterns` — one `FormPattern` per transformation applied
- `out.signals["charsafe_changed"]` — bool

**FormCodes this module may emit:** `ZERO_WIDTH`, `HOMOGLYPH`, `DOTLESS_I`

Every `FormPattern` must carry `evidence`. A transformation that leaves no evidence is a contract violation — a decision must always be traceable back to the input.

---

## 4. Approach

Run in this exact order:

**Step 1 — invisible characters.** Delete every character whose Unicode general category is `Cf` or `Cc`. Use `unicodedata.category()`. Record how many were removed as evidence.

**Step 2 — homoglyphs, conditionally.** Only run this if the text contains at least one non-ASCII character. Map a small, curated confusables table. Start from the Unicode confusables file and keep only single-character, cross-script mappings for the Latin letters used in Turkish.

**Step 3 — Turkish-aware lowercase.** Map `I` → `ı` and `İ` → `i` explicitly before calling `.lower()`.

---

## 5. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Multi-character confusables like `rn` → `m` | Documented UTS#39 trap. It corrupts legitimate ASCII words and turns clean text into garbage. |
| Running confusables on pure-ASCII text | Nothing to fix; all downside, no upside. |
| Plain `.lower()` without Turkish mapping | Creates the `SIKINTI` → `sikinti` false positive. |
| Unconditional NFKC normalization | Collapses distinctions the Turkish alphabet relies on. If used at all, gate it behind the non-ASCII check and log it. |
| Silent transformation | Every change emits a `FormPattern`. |

---

## 6. Metrics this module must produce

- **Detection rate per family**: what fraction of injected zero-width / homoglyph / casing cases are caught. Report the three separately, never as one average.
- **Damage rate on clean text**: fraction of clean Turkish inputs where `charsafe_text != text.lower()` in a way that changes a word. Target: zero.
- **Latency**: p50 and p95 in ms, measured on the demo machine.

---

## 7. Required fixtures

`fixtures/cases.jsonl` — one JSON object per line: `{"text": ..., "expect_patterns": [...], "expect_clean": true|false}`

Must include at minimum:
- `SIKINTI`, `IŞIK`, `İSTANBUL` in mixed casing
- a word with an injected zero-width space in the middle
- a word with one Cyrillic letter substituted
- 20+ clean Turkish sentences that must come out unchanged
- an empty string, a single space, and a 5000-character string

---

## 8. Acceptance criteria

- [ ] Every uppercase `I` maps to `ı`, so `SIKINTI` written with uppercase `I` never produces a string containing `sik`. Dedicated unit test, named explicitly: `test_sikinti_never_yields_profane_root`. Input typed with a lowercase dotted `i` is outside this criterion; m0 does not guess.
- [ ] Zero modification on a clean pure-ASCII Turkish sentence.
- [ ] Every transformation emits a `FormPattern` with non-null `evidence`.
- [ ] p95 latency within the per-length budget in `decision/thresholds.yaml` (`budgets.module_latency_p95_ms.m0_charsafe`), which is authoritative. At the time of writing: ≤64 chars **0.25 ms**, ≤280 chars **1 ms**, ≤1000 chars **4 ms**, ≤5000 chars **25 ms**. These were measured on the development machine and are due for re-measurement on the demo machine; a single per-sample figure is not used because m0 is linear in input length.
- [ ] Unit tests cover all three families plus empty / whitespace / very long input.
- [ ] `eval/results/m0_charsafe.json` produced with the three detection rates and the damage rate.
- [ ] Module never raises; errors are caught and reported in `notes`.

---

## 9. Research pointers

- Boucher et al., *Bad Characters: Imperceptible NLP Attacks*, IEEE S&P 2022 — the source for invisible-character and reordering attacks.
- Unicode UTS#39 confusables data file.
- The Turkish dotted/dotless I problem is documented as a defect in IBM Base Services and PostgreSQL; search those for concrete failure reports.

---

## 10. Definition of done

The module runs, the tests pass, the eval file exists, and a teammate who did not write it can read this spec plus the docstring and explain why the confusables step is conditional.
