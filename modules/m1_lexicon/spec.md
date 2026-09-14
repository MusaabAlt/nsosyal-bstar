# M1 — Lexicon Signal

**Type:** signal (not a full detector)
**Owner:** _assign_

---

## 1. Objective

Produce a profanity signal that is **independent of the neural model**, and precise enough that it never fires on a clean word that happens to contain a profane substring.

This module exists for two reasons. First, it gives the decision layer a second opinion that fails in a different way than the model does. Second, it is the instrument that splits the evaluation set into the `lexicon_hit` and `lexicon_free` slices — the split the entire project is built on. If this module is sloppy, every number downstream is wrong.

---

## 2. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| Explicit profane roots with legal Turkish suffixes | abuse with no profane root (63.5% of cases) → M3/M4 |
| Profanity via sacred/religious concepts (after extension) | implied or coded abuse → M4 |
| Roots inside the normalized channel from M2 | sarcasm → M5 |

---

## 3. Contract

**Reads:** `ctx.text` **and** `ctx.normalized_text` — run on both, report both.

**Writes:**
- `out.signals["lexicon_hit"]` — bool, true if any legitimate match on either channel
- `out.signals["lexicon_hit_raw"]` / `["lexicon_hit_norm"]` — per channel
- `out.content_scores` — scores for `A1`–`A4`
- `out.guards` — `SUBSTRING_COLLISION`, `HOMONYM`

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
- [ ] Recall and FPR reported with CIs, on both the raw and normalized channels, separately.
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
