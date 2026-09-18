# M1 — Lexicon Signal

**Type:** signal (not a full detector)
**Owner:** Musaab

---

## 1. Objective

Produce a profanity signal that is **independent of the neural model**, and precise enough that it never fires on a clean word that happens to contain a profane substring.

This module exists for two reasons. First, it gives the decision layer a second opinion that fails in a different way than the model does. Second, it is the runtime lexicon signal; the evaluation set's `lexicon_hit` / `lexicon_free` slices — the split the entire project is built on — are not recomputed from it but read from `AI/eval/frozen/study_slice_dev.json`, produced once by the study's own matcher (owner decision, 2026-09-15). If this module is sloppy, every number downstream is wrong.

**Two lexicon files, two purposes — never merged** (owner decision, 2026-09-16):

| file | produced by | purpose | status |
|---|---|---|---|
| `AI/eval/frozen/study_slice_dev.json` | the study's karaliste matcher, once | **the** `lexicon_hit` / `lexicon_free` evaluation slice; every published M4 number (0.5628, +0.3301, 0.5180 → 0.6367) was measured against it | frozen: never recomputed, never replaced |
| `AI/eval/derived/m1_lexicon_dev_seed42.json` | this module (terlik) through m0 → m2 → m6 → m1, `AI/protocols/m1_lexicon_dev_labels_protocol.md` | pseudo-label *agreement* for M3's A head (never its evaluation) and comparison against the frozen slice | regenerable whenever M0, M1, M2, M6, terlik, zeyrek or the pipeline order changes (`python -m eval.m1_lexicon_labels --check`) |
| `AI/eval/derived/m1_lexicon_train_seed42.json` | the same generator on the TRAIN split, `AI/protocols/m1_lexicon_train_labels_protocol.md` | M3 A-head **training supervision** (`a_label`, owner decision 2026-09-18); the evaluation oracle is the human-labelled dev subset (`docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md`) | same |

The derived file never defines a slice, and the frozen file is never regenerated from this module. Replacing one with the other would silently change what the published M4 numbers mean.

---

## 2. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| Explicit profane roots with legal Turkish suffixes | abuse with no profane root (63.5% of cases) → M3/M4 |
| Profanity via sacred/religious concepts (after extension) | implied or coded abuse → M4 |
| Roots inside the normalized channel from M2 | sarcasm → M5 |

---

## 3. Contract

**Reads:** `ctx.text` **and** `ctx.normalized_text` — run on both, report both. `ctx.signals["m6_target"]` — the target M6 publishes (`target_type`, `target_confidence`).

**Writes:**
- `out.signals["lexicon_hit"]` — bool, true if any legitimate match on either channel, whatever the match's route
- `out.signals["lexicon_hit_raw"]` / `["lexicon_hit_norm"]` — per channel
- `out.signals["_matches"]` — PRIVATE (kept out of the response by the pipeline): every match with `root`, `channel`, original `span` and `route`, including matches that emit no content code; the pseudo-label generator reads matches from here
- `out.content` — one score of 1.0 per match, on the code its root is ROUTED to (`AI/protocols/m1_runtime_routing_protocol.md`, M1-ROUTE-1, owner approval 2026-09-18):
  - the 17 explicit obscene / profane roots of pseudo-label rule v3 → the family-A carrier `A1` (the decision layer assigns `A1`/`A2`/`A3` from M6's target, ADR-005); these are the ONLY lexical family-A roots. A match of one of them counts only as a real word of that root (`AI/protocols/m1_positive_matching_precision_protocol.md`, M1-PREC-1, pseudo-label rule v4, rules R1–R9); a rejected one is a `SUBSTRING_COLLISION` whose evidence names the rule
  - ordinary insults (100 roots) → `B1` (degradation); threats (7) → `B2`; curses / exclusion (9) → `B3`. B means "non-profane abuse; no profane root required": a deterministic lexical B code needs no trained B head. M6's target does not recode B codes
  - topic or neutral vocabulary (14 roots, e.g. `meme`, `fuhuş`, `kaşar`) → no content score: still a match, a hit and a matched root
  - `A4` when the sacred-concept extension exists
- `out.guards` — `SUBSTRING_COLLISION`, `HOMONYM`, and `NON_HUMAN_TARGET`: raised on each of this module's content scores when M6's published `target_type` is `non_human`, with `score` = M6's `target_confidence` and `span` = that match's span (ADR-005); `thresholds.yaml` decides which codes each guard may suppress (`NON_HUMAN_TARGET`: A1–A3 and B1; `HOMONYM`: A and B1)

**Every match and every guard carries `span`** — the `(start, end)` of the exact substring of the original text that triggered it (`ContentScore.span`, `GuardResult.span`), plus `GuardResult.source = "m1_lexicon"`. A match or guard with no span is a contract violation: the decision layer scopes guards by span overlap (ADR-001), and without spans a collision guard on `amcam` could clear a real insult elsewhere in the same post.

**Never sets** `threshold` or `fired`.

---

## 4. Approach

### 4.1 Morpheme-boundary matching

A root counts **only** when what follows it is a legal Turkish suffix boundary or the end of the token. Free substring search is banned.

The failure this prevents, concretely:

```
göt   ⊂ götürmek, götür        (to take/carry)
am    ⊂ amaç, amca, ambulans, amir, ampul
sik   ⊂ sikke, psikoloji, klasik
piç   ⊂ kerpiç
```

Turkish is agglutinative, so naive word-boundary checks fail too: `amacımız` and `götürdüler` extend the clean word with suffixes. You need morphological awareness, not a `\b` regex.

### 4.2 The hard/soft distinction

The Turkish community repository `90pixel/kufur-filtresi` splits its list into two files for exactly this reason: `soft.txt` holds terms to filter only as standalone words, `hard.txt` holds terms whose appearance inside any word is almost certainly profane. Adopt this two-tier structure. It is the Scunthorpe problem already solved by Turkish speakers — do not re-derive it.

### 4.3 Tool

**Use `terlik`** in `balanced` mode. It is a Turkish suffix engine: 147 roots × 83 suffixes generating over 10,000 forms, handles leet, separators, repetition and zero-width characters, ships three detection modes, MIT licensed, available on npm and PyPI.

**Extend it** with sacred-concept profanity. The community repository documents an open report that swearing with sacred concepts (`Allah`, `kitap`) is common in some regions and that the list includes some but misses others. This extension is your `A4` coverage and it is a genuine contribution — document every addition with its source.

---

## 5. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Free substring search | Produces the collisions listed above. This is the single most common failure in Turkish profanity filters. |
| Using `karaliste` as the reference list | Ad-hoc construction, documented religious false positives (`allah`, `allahsız`), and a licence contradiction between 3.0 and 4.0 across its own files, with ShareAlike that would infect derivatives. Keep it only as a historical comparison point. |
| Suppressing a guard when it fires | The guard firing **is** how precision gets measured. A guard that never fires proves nothing. |
| Presenting the lexicon engine as the project's contribution | `terlik` already exists, is open, and uses the same example strings your project uses. The contribution is measurement and integration, not the filter. |

---

## 6. Metrics this module must produce

- **Recall and FPR of the lexicon signal alone**, on the functional test set, with bootstrap confidence intervals.
- **Zero-firing proof on the trap list** (see `eval/traps/traps.jsonl`).
- **Coverage comparison**: `terlik` balanced vs the historical `karaliste`, recall and FPR side by side, plus a count of disagreement cases. This closes a licence and precision risk in the report.
- **Growth table** for the sacred-concept extension: how many roots added, and how much recall on `A4` moved.

---

## 7. Required fixtures

- All trap words, each asserted to produce **zero** positive.
- Profane roots with a range of legal suffixes, including uncommon ones — the published Turkish work notes that linear models failed when the profane token carried an unusual suffix.
- Sacred-concept cases for `A4`.
- Homonyms: `sikke` (coin), `am` used as an abbreviation.
- Dual-register words: `moruk`, `lan`, `oğlum` — these must **not** auto-fire; they are a documented source of annotation inconsistency.

---

## 8. Acceptance criteria

- [ ] Zero positives on the full trap list. Any regression fails the build.
- [ ] Every `ContentScore` and every `GuardResult` emitted carries the span of the exact substring that triggered it (ADR-001). A unit test asserts `span is not None` on every output item and that `text[start:end]` is the matched root or colliding word.
- [ ] Recall and FPR reported with CIs, on both the raw and normalized channels, separately.
- [ ] `out.signals` always carries `lexicon_hit`, `lexicon_hit_raw` and `lexicon_hit_norm` as booleans, on every input including empty and no-match inputs. The evaluation's lexicon-hit / lexicon-free slice is not defined by it but read from `AI/eval/frozen/study_slice_dev.json` (§1, owner decision 2026-09-15); M4's stage 1b (`threshold_when: {signal: m1_lexicon.lexicon_hit}`, ADR-006) resolves against it at runtime, and if the signal is missing the decision layer silently falls back to the scalar threshold. A unit test asserts all three keys are present and boolean.
- [ ] `SUBSTRING_COLLISION` guard fires and is counted whenever a root is found but the boundary test rejects it.
- [ ] Sacred-concept extension table committed, with a source for each added root.
- [ ] `terlik` vs `karaliste` comparison committed.
- [ ] p95 latency under **5 ms**.
- [ ] Licence of every list used is recorded in the module README.

---

## 9. Research pointers

- `terlik` — Turkish profanity engine, PyPI and npm. Read its mode definitions before choosing one.
- `90pixel/kufur-filtresi` — the soft/hard split.
- `ooguz/turkce-kufur-karaliste` — read the open issues, especially the sacred-concept report. Do **not** adopt the list itself.
- Turkish morphological analysers (Zemberek family) — for suffix legality. Note: use it for analysis only, never as a blind normalizer (see M2).

---

## 10. Definition of done

The trap list is green, the two-tier list structure is in place, both channels are reported, and the licence of every resource is written down.
