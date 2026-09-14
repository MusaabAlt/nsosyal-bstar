# Orchestration handoff bundle — assembly report

**Date:** 2026-08-21
**Repo:** `nsosyal-bstar` (`C:\Projects\NSosyal`), branch `master`
**HEAD at time of assembly:** `6731345d5098aa37df99c8d1212d8258f3e0828a`
**Bundle written to:** `handoff_bundle/` (28 files, 3.1 MB) — **not committed**
**Companion file:** `handoff_bundle/MANIFEST.md` — the upload-facing manifest.
This file is the repo-side record of the same pass.

**Mode:** read-only. No tracked file was modified, staged or committed. The only
writes were `handoff_bundle/`, one build that went to `handoff_bundle/measure/`,
and this report.

**Rule applied throughout:** every claim names the path it came from. Where a
file or fact does not exist, this says so. Nothing was reconstructed from memory
or inferred from the drafts.

---

## 0. Headline

Four findings dominate everything else:

1. **The approved Turkish text is not in the repository** — §A1 state 3. Not in
   the working tree, not in any ignored file, not in any commit on any branch.
2. **The 450 words/page planning assumption is wrong by 1.83×.** Measured:
   **245.6 w/p**. This single number is the origin of the entire page crisis.
3. **`results/*/findings.json` never existed.** They are `findings.md`.
4. **`MASTER_HANDOFF_FULL.md` and `MASTER_PROMPT_REPORT_WRITING.md` are not in
   the repo at all**, so nothing could be checked against the handoff — including
   its own warning that it has been wrong seven times. Every contradiction
   recorded here is repo-internal: file vs file, or file vs measurement.

---

## 1. §A1 — the approved Turkish text: **state 3, not in the repository**

Sections 1.1, 1.2, 2.1 and 2.2 of the KYS template (the 30-point block) exist
nowhere in this repository.

Searches run, all negative:

```
git log --all --diff-filter=A --name-only -- 'report/**'
  -> only the four drafts + build_docx.py
git log --all --diff-filter=D --name-only
  -> empty; nothing was ever added under report/ and later moved or deleted
git grep -l -i "proje konusu\|katma değer ve yenilikçilik" $(git rev-list --all)
  -> exactly one path, in all 25 commits containing it:
     phases/10_sablon_mapping.md
find . -iname '*final*' -o -iname '*approved*' -o -iname 'CONTENT_*'
  -> nothing (search included ignored files)
```

`phases/10_sablon_mapping.md` is the KYS coverage map. It self-describes at
line 3 as *"a map, not a draft"* and contains no Turkish report prose. It is not
the approved text and was not treated as such.

`report/final/` does not exist. `report/` holds exactly the four drafts,
`build_docx.py`, and the gitignored `build/` output.

**Nothing was reconstructed.** `handoff_bundle/approved/` contains only a
`NOT_FOUND.md` recording this verdict — no prose. Recover the text from the
writing conversation.

### The numbering trap

The template's 1.1/1.2/2.1/2.2 (`phases/10_sablon_mapping.md:77,86,96,106`):

| § | Template heading | Points |
|---|---|---:|
| 1.1 | Proje Konusu ve amacı | 7 |
| 1.2 | Proje Kapsamı ve Yöntemi | 8 |
| 2.1 | Problem Tanımı ve Mevcut Çözümler | 7 |
| 2.2 | Çözüm Fikri, Özgünlük ve Yerlilik | 8 |

7 + 8 + 7 + 8 = **30 points**.

The raw drafts **also** number sections 1.1/1.2/2.1/2.2 — but they are *Veri
kümesi*, *Dondurulmuş sözlük ve eşleşme kuralı*, *Model ve eğitim
yapılandırması*, *Bölünmenin dondurulması*
(`report/01_veri_ve_deney_kurgusu.md:9,39`; `report/02_yontem.md:11,89`).
Different content entirely. **The two schemes must not be conflated** — and
conflating them is precisely what the §A2 fallback forced, which is why the
measurement below carries the label it does.

---

## 2. §A2 — words per page: **measured, ≈ 245.6 w/p**

Word/COM was available (Word 16.0.20228). This is a real measurement.

### What was measured

A1 came back empty, so per the fallback I measured **sections 1 and 2 of the raw
drafts** — `report/01_veri_ve_deney_kurgusu.md` + `report/02_yontem.md`.

> **Labelled clearly: this is a stand-in for a different body of text.** The
> drafts' sections 1–2 are the data/experiment setup and the method, not the
> template's Proje Konusu / Kapsam / Problem / Çözüm. The words-per-page **rate**
> transfers (same template, same styles, comparable table density); the **word
> counts do not**. 3 621 words is not a target for the approved sections.

Built by importing `report/build_docx.py` unmodified and overriding its
`SOURCES` / `OUT` module globals in memory. The committed builder was not
touched and `report/build/report_draft.docx` was not overwritten — its sha256 is
still `c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1`.
Output went to `handoff_bundle/measure/sections_1_2_standin.docx`.

### The measurement

Opened read-only, `Repaginate()` called, closed with `Saved = $true` so Word
never wrote to the file. Cross-checked the same three ways as the 44-page
measurement:

| | stand-in (§1–2) | control (all four drafts) |
|---|---:|---:|
| `ComputeStatistics(wdStatisticPages)` | **15** | **44** |
| `Content.Information(wdActiveEndPageNumber)` | **15** | **44** |
| `BuiltInDocumentProperties('Number of pages')` | **15** | **44** |
| all three agree | **yes** | **yes** |
| Word word count | **3 621** | 10 806 |
| python-docx word count | **3 637** | 10 875 |
| Word characters | 26 382 | 76 873 |
| tables | 15 | 36 |

**The control validates the instrument.** The measurement scripts were lost with
the old scratchpad, so they were rewritten from the trap list in
`docs/docx_pipeline_state_2026_08_20.md` §7.5. Re-measuring the existing
`report/build/report_draft.docx` with the rewritten script returned
44 pages / 10 806 words / 76 873 characters / 36 tables — identical to the
2026-08-20 record. Both scripts now live at `handoff_bundle/measure/`.

Two of the recorded PS 5.1 traps were re-hit and are worth restating:
`powershell.exe` is not on PATH here (invoke with `& <path>.ps1`), and
`BuiltInDocumentProperties` needs **two-step** reflection — `InvokeMember('Item')`
then `InvokeMember('Value')` on the result. A single-step call returns empty and
silently breaks the third cross-check.

### Words per page — derived

| Basis | Arithmetic | Rate |
|---|---|---:|
| Stand-in, Word's own count | 3 621 / 15 | **241.4 w/p** |
| Stand-in, python-docx count | 3 637 / 15 | 242.5 w/p |
| Full document, Word's own count | 10 806 / 44 | **245.6 w/p** |

**Stated answer: ≈ 241–246 words per page. Plan with 245.6 w/p** — larger
sample, and it is the document that actually has to fit. The two independent
samples agree within 1.7%, which is the useful result: the rate is stable across
different section mixes, so it can be trusted for forecasting the approved text.

### What that rate implies

- 27-page body budget × 245.6 = **≈ 6 631 words of body available**
- Current body: **10 806** Word-words
- Overshoot: **≈ 4 175 words — about 39% of the body must go**, if the cut is
  taken in text alone at the current table density

python-docx counts ~0.6% higher than Word (10 875 vs 10 806; 3 637 vs 3 621),
because Word does not count some table-cell and separator artifacts as words.
Either is fine for planning; do not mix them in one calculation.

---

## 3. §B — what was collected, and what does not exist

### Collected (24 source files + 4 written/built by this pass)

| Group | Bundle path | Contents |
|---|---|---|
| Raw drafts | `drafts/` | the four files `build_docx.py` paginates: `01_veri_ve_deney_kurgusu.md`, `02_yontem.md`, `04_bulgular.md`, `05_sinirliliklar.md` (11 937 words total) |
| Pre-registrations | `protocols/` | the six protocol files — see §5 |
| Per-phase findings | `results_findings/` | seven `findings.md` (**not** `findings.json`) |
| Project docs | `project_docs/` | `PROJECT_HISTORY.md`, `REPORT_EVIDENCE.md`, `10_sablon_mapping.md`, `verification_sweep_2026_08_20.md` |
| Demo | `demo/` | `app.py`, `README.md`, `examples.json` |
| §A1 verdict | `approved/NOT_FOUND.md` | evidence only, no prose |
| §A2 artefacts | `measure/` | the stand-in `.docx` and a copy of the builder |

Three files were added beyond the brief's list because the §C answers rest on
them: `10_sablon_mapping.md` (the only place the template's own section
numbering is recorded), `REPORT_EVIDENCE.md`, and the verification sweep.

Full per-file table with sizes, word counts and last-touching commits is in
`handoff_bundle/MANIFEST.md` §1.

### Requested but **NOT FOUND** — searched in tree (incl. ignored) and full history

| # | Item | Status |
|---|---|---|
| 1 | `MASTER_PROMPT_REPORT_WRITING.md` | **DOES NOT EXIST.** No file of that or any similar name, in tree or history. The nearest thing is `docs/claude_master_brief.md` (7 896 bytes) — an engineering-conduct prompt, **not** a report style-rule list. It is not a substitute and was not copied as one. |
| 2 | `CONTENT_*.md` section briefs | **NONE EXIST.** Zero matches anywhere. |
| 3 | `results/*/findings.json` | **NEVER EXISTED.** Seven `findings.md` instead. `git log --all --name-only \| grep findings` returns only `.md` paths. |
| 4 | Bibliography for section 9 | **DOES NOT EXIST.** No `.bib`, no `Kaynakça`, no references section. `phases/10_sablon_mapping.md:225` marks the check item `NONE`: *"There is no bibliography in the repository."* `docs/REPORT_EVIDENCE.md:1749`: *"The repository has no bibliography and no in-text [n] citations."* The Çöltekin corpus — the data source for every measurement — is referenced by filename, SHA-256, project URL and HuggingFace id, but has **no bibliographic entry** (`REPORT_EVIDENCE.md:1736`). |
| 5 | Team roles for 8.1 | **DOES NOT EXIST.** `phases/10_sablon_mapping.md:213–215` marks all three 8.1 items `EXTERNAL` — composition, disciplines and size are *"not recorded anywhere in the repo. Needs the lead."* Nothing to copy, with or without names. The template's no-names constraint (`:217–219`) is not in dispute; there is simply no roles material of any kind. |
| 6 | UI/UX notes, user flows, accessibility audit | **NO DEDICATED FILE EXISTS.** What exists instead: `demo/README.md` and `demo/app.py`, which **does** carry real accessibility constructs — see contradiction 3 in §4. |

---

## 4. §D — contradictions found

Ranked by how much damage each would do if it reached the report unnoticed.

### 1. The 450 words/page assumption is wrong by 1.83× — the origin of the page crisis

`phases/10_sablon_mapping.md:232` converts word counts at **450 words/page** and
concludes `report/` totals **26.0 pages**, then *"26 + 3 = 29 of the 30
available pages"*. Measured rate is **245.6 w/p**; the real count is **44 pages**.

The file does hedge — it calls the estimate *"conservative in one direction that
matters"* because of table density, and warns *"Real page counts will be higher
than these figures, not lower."* But "higher" was carrying an **18-page error**,
and the 29-of-30 conclusion reads as "we just fit." **Any planning still resting
on 450 w/p, or on the 26-page figure, is wrong by a factor of 1.83.**

### 2. `results/*/findings.json` does not exist and never did

The seven per-phase findings files are **`findings.md`**. Verified in the tree
and across all history. If any downstream tool, prompt or checklist expects to
parse `findings.json`, it will silently find nothing.

### 3. The 3.3 accessibility verdict of `NONE` is STALE — the work exists and shipped

`phases/10_sablon_mapping.md:146` records *"Erişilebilirlik yaklaşımı
belirtilmiş"* as **`NONE`** — *"No accessibility material of any kind — no
contrast, keyboard, screen-reader, WCAG or assistive-technology consideration
anywhere in `demo/` or `report/`."*

`docs/RESULTS_LOG.md:54` (2026-08-19) records the opposite, and `demo/app.py`
confirms it in source at HEAD:

- `aria-live="polite"` and `tabindex="-1"` on the results region — `app.py:298`
- a bound `<label for="inp">` — `app.py:295`
- `:focus-visible` outline — `app.py:177`
- per-element `lang` marking, root `lang="en"` with Turkish content `lang='tr'` —
  `app.py:288, 246, 285, 296`
- `html.escape()` on the previously unescaped `examples.json` fields —
  `app.py:279–284`

`docs/repo_inventory_2026_08_17.md:510` flags it too: *"this partially
contradicts the stated answer"*, noting contrast ratios that *"happen to pass
WCAG AA for body text"*.

**This is worth up to 2 points the map currently writes off as zero.** But the
claim must be bounded exactly as `RESULTS_LOG.md:54` bounds it: *"Verified at
renderer level only … the accessibility changes rest on source inspection plus
AST parse, not on rendered output or any screen reader. No accessibility claim
may be made in the report beyond 'implemented, verified by source inspection'
until the demo runs end-to-end."*

### 4. Three different counts are in circulation — five, seven, eight

`docs/PROJECT_HISTORY.md` §5 opens *"Five correction rows exist in
`docs/RESULTS_LOG.md`."* There are now **seven** correction-type rows (six
`CORRECTION` + one `SPEC DEFECT`) — lines 29, 39, 42, 43, 46, 52, 56. The "five"
was true on 2026-08-17; two more were appended 2026-08-19 and PROJECT_HISTORY was
never updated.

Separately, `RESULTS_LOG.md:52` refers to *"the same kind as the **eight**
previously recorded in this log"* — a different tally **and a different unit**
(controller errors, not correction rows). And the brief states that
`MASTER_HANDOFF_FULL.md` warns it has been wrong **seven** times, which could not
be checked because that file is not in the repo.

**Pin the definition before citing any of these numbers in section 3.1.**

### 5. Five substantial documents exist on one workstation only

`docs/verification_sweep_2026_08_20.md` (61 359 bytes) has **never been
committed** — and it is the sole source for the figure-readiness verdict, the
correction-row recount and the six-protocol timestamp table. The same is true of
`docs/onboarding_readiness_audit_2026_08_18.md`,
`docs/docx_build_environment_check_2026_08_20.md`,
`docs/docx_pipeline_resume_report_2026_08_20.md` and `repo_conventions.md`
(78 158 bytes).

Combined with the single-copy `dev_predictions.csv` (§5, C9) and the four
unpushed commits, **the project's unique-copy surface is larger than the handoff
implies.**

### 6. Two figure blockers the 2026-08-20 resume report omits

The resume report correctly says only the risk–coverage curve is plottable, but
presents the gitignored `dev_predictions.csv` as the sole obstacle.
**`matplotlib` is neither installed in `.venv` nor listed in
`requirements.txt`** (`verification_sweep:1216`). **No figure at all can be
rendered in this environment today**, including the risk–coverage curve that is
otherwise data-ready.

### 7. Minor: the resume report's "ahead by 3"

`docs/docx_pipeline_state_2026_08_20.md` records master as ahead of origin by 3.
It is **4** — the state doc was itself committed afterwards as `6731345`.

### Checked and found NOT contradictory

Recorded so nobody re-litigates them:

- **The 27-page body budget is consistent.** `phases/10_sablon_mapping.md:250`
  states a 30-page cap with 3 pages reserved for cover, contents and
  bibliography → 27 of body, exactly as the resume report says.
- **The four drafts' byte sizes match the state doc's census exactly**
  (14 832 / 20 547 / 42 762 / 25 975). An intermediate reading of 20 216 bytes
  for `02_yontem.md` was a `read_text()` newline-translation artifact on my side,
  not a discrepancy in the file.

---

## 5. §C — the nine answers

**C1 — Terminology (`ters olgusal` vs `karşı olgusal`).**
**Neither appears. The count is 0 and 0.** Across all four drafts both render as
zero, and a widened search — bare `olgusal`, `karşıolgusal`, `kontrafakt`,
English `counterfactual` — also returns zero in `report/`. The only file in the
repo containing either string is `docs/verification_sweep_2026_08_20.md:321–338`,
which is the sweep *reporting this same absence*. **There is no ruling to make
between two variants; the concept is simply not named in the drafts.** If the
approved text or section 3.1 needs the term, it is being introduced for the first
time and the choice is free.

**C2 — Detoxify.**
**Not recorded — and stronger: the string "Detoxify" does not appear anywhere in
the repository**, in any file type, in the working tree or in any commit in
history. No vendor wording, no access date, no placeholder. There is also no
`erişim tarihi` / "accessed" convention recorded anywhere.

**C3 — Repo state.**

```
$ git status -sb
## master...origin/master [ahead 4]
?? docs/docx_build_environment_check_2026_08_20.md
?? docs/docx_pipeline_resume_report_2026_08_20.md
?? docs/onboarding_readiness_audit_2026_08_18.md
?? docs/verification_sweep_2026_08_20.md
?? repo_conventions.md
```

HEAD = `6731345d5098aa37df99c8d1212d8258f3e0828a`.
**The four commits are NOT pushed** — `origin/master` is still at `e0ce657`.
The tracked tree is clean. (After this pass, `handoff_bundle/` and this report
appear as two further untracked entries.)

**C4 — The failing test.**
**Yes, still failing at HEAD.** Run during this pass:

```
FAILED tests/test_demo.py::test_render_result_escapes_html - KeyError: 'operating_point'
1 failed, 415 passed in 14.91s
```

Same failure as recorded on 2026-08-20: `KeyError: 'operating_point'` at
`demo/app.py:223`, where `render_result` reads `STATE["operating_point"]` — a key
the test's synthetic state does not carry. Counts unchanged: **1 failed,
415 passed.** Any claim of a green suite is false.

**C5 — README.**
**No.** `README.md`'s last commit is `a3c4eb4` *"README: Phase 0 remote created
and pushed"*, **2026-08-15T15:16:32**, which is **67 commits behind HEAD**. The
working copy is identical to HEAD, so there is no uncommitted rewrite either. No
claim that a README rewrite was performed appears anywhere in the repo — so this
is "never rewritten", not "rewrite uncommitted".

**C6 — Secret scan.**
**No.** No evidence of any full-history secret scan. No `gitleaks`,
`trufflehog`, `detect-secrets` or `git-secrets` config, output, log or mention
anywhere. The only match for "credential" is
`docs/repo_inventory_2026_08_17.md:615`, discussing `git config --get
credential.helper` while proving the remote is private — unrelated. **A scan has
not been run, and no tooling for one is present.**

**C7 — Table borders / H2 bold / `cp:revision`: all three still OPEN.**
`report/build_docx.py` is byte-identical to its state at `f723b91` (`git diff
HEAD` empty; still the only commit that touched it), and
`report/build/report_draft.docx` still carries sha256
`c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1` — the build
recorded on 2026-08-20.

- **Table borders** — still absent. `grep -c tblBorders report/build_docx.py` = **0**.
- **Heading 2 bold** — still removed. `build_docx.py:460`:
  `set_style_font(h2, "Arial Black", 12, bold=False)`.
- **`cp:revision` / timestamps** — still inherited. `grep -c -i revision` = **0**;
  `clear_core_properties()` (`build_docx.py:342–347`) clears exactly the seven
  named fields and does not touch `revision`, `created` or `modified`. The
  stand-in built today still carries `<cp:revision>4</cp:revision>` and the
  2026-08-13 dates.

**C8 — Figures. The resume report is correct; confirmed.**
Only the **risk–coverage curve** is plottable from committed artefacts:
`results/04_calibration/calibration.json` → `variants.raw.risk_coverage`,
11 full points (coverage, macro_f1, error_rate, n_auto, n_deferred, off_recall,
off_precision, threshold). The other two are not:

- *Score distribution by slice* — `results/09_deeper_analysis/stage_1/stage1_auc.json`
  holds summary statistics only (`n`, `mean`, `q1`, `median`, `q3`,
  `share_below_0.5`). No score arrays. A box-plot is possible from the quartiles;
  a histogram or density is not.
- *ROC curves per slice* — the same file records AUC scalars and CIs but **no
  `fpr` / `tpr` arrays**.

Both need the raw per-row scores, which exist in exactly one place: the
gitignored `dev_predictions.csv`. Plus the matplotlib blocker in §4.6.

**C9 — `dev_predictions.csv`: gitignored AND present locally.**

- Ignored by `.gitignore:41`, rule `results/**/*predictions*.csv` — confirmed by
  `git check-ignore -v`.
- Not tracked, and never was (`git ls-files --error-unmatch` fails; nothing in
  history).
- **Present locally** at `results/01_baseline_berturk/dev_predictions.csv`,
  **736 591 bytes**, mtime 2026-08-17 15:21, columns
  `row_id,text,gold,pred,confidence,slice` with `confidence` = P(OFF).
- Integrity pinned and verified `pass: true` in
  `results/12_threshold_policy/c12_16_intervals.json`, sha256
  `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346` — the local
  copy is provably the right one.

**Net:** section 3.2 and the demo fixture can be served **on this workstation
only**. A fresh clone does not have this file and cannot regenerate it without a
training run.

---

## 6. The six pre-registration protocols, with both timestamps

Section 3.1's provenance argument rests on this margin, so both ends are given as
commit SHA + author timestamp. **Each was verified independently** with
`git log --all --follow --diff-filter=A`, not relayed from
`verification_sweep` §5a; all six agree with it.

| # | Protocol file | Protocol commit | Protocol timestamp | First result commit | Result timestamp | Margin |
|---|---|---|---|---|---|---|
| 1 | `phases/01_baseline_diagnosis.md` | `197d953` | 2026-08-15 15:09:28 +03 | `685d4af` | 2026-08-15 19:29:33 +03 | **+4h 20m 05s** |
| 2 | `phases/04_calibration.md` | `ab225ad` | 2026-08-16 13:34:34 +03 | `8012c71` | 2026-08-16 13:53:23 +03 | **+18m 49s** |
| 3 | `phases/08_lexical_analysis.md` | `b127d44` | 2026-08-17 12:42:25 +03 | `7ef51a0` | 2026-08-17 13:08:40 +03 | **+26m 15s** |
| 4 | `phases/09_deeper_analysis.md` | `bcb4b70` | 2026-08-17 15:24:00 +03 | `120eead` | 2026-08-17 15:37:17 +03 | **+13m 17s** |
| 5 | `phases/11_prior_correction.md` | `d589dba` | 2026-08-18 16:30:17 +03 | `a96f02d` | 2026-08-18 17:08:56 +03 | **+38m 39s** |
| 6 | `phases/12_threshold_policy.md` | `ec2fd3a` | 2026-08-18 18:06:47 +03 | `d74acd9` | 2026-08-19 11:37:55 +03 | **+17h 31m 08s** |

All six precede the first numeric result of their phase. Commit subjects confirm
the roles — e.g. `ab225ad` *"Phase 04 pre-registration: calibration split, ECE
definition, operating-point protocol"* → `8012c71` *"Phase 04 results: raw needs
no calibration…"*.

**Three caveats that belong with these numbers:**

1. **Row 3 requires `--follow`.** `phases/08_lexical_analysis.md` entered version
   control as **`phases/06_…`** (`b127d44`, subject *"Phase 06 pre-registration:
   word-level lexical dependence"*) and was renumbered because the demo already
   held 06. A plain `git log -- phases/08_…` reports the **rename** commit
   `7ef51a0` as the add — which collapses the margin to zero and makes the
   pre-registration look simultaneous with its own result.
2. **Three of the nine `phases/` files are not pre-registrations** and are
   correctly excluded: `03_defense_design.md` (no pre-registration language,
   committed as "Phase 03 step 1"), `07_report.md` (report outline),
   `10_sablon_mapping.md` (*"a map, not a draft"*).
3. **The Phase 12 C12-16 addendum is not covered by row 6.** It was committed at
   `b0f2b0b` **after** the point estimates were published, and its own artefact
   says so: *"estimation after the fact, not pre-registration."* It is the source
   of figures 3l–3o. The six-document claim is about the phase pre-registrations,
   not every clause inside them.

---

## 7. Read-only compliance and handling notes

Verified at the end of the pass:

```
$ git diff --cached --stat      -> empty   (nothing staged)
$ git diff --stat HEAD          -> empty   (no tracked file modified)
$ sha256sum report/build/report_draft.docx
  c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1   (unchanged)
```

- Nothing under `report/`, `results/`, `phases/` or `docs/` was modified. The
  §A2 build went to `handoff_bundle/measure/`, **not** to `report/build/`.
- **`handoff_bundle/` is NOT gitignored.** The brief assumed it was; it is not,
  and `.gitignore` was not edited. The directory therefore appears as untracked
  in `git status`. Nothing in it is staged or committed. Either add the ignore
  rule or delete the directory after upload.
- `handoff_bundle/measure/sections_1_2_standin.docx` is **2.49 MB** — it carries
  the template's five embedded fonts and two unreferenced media files, as every
  build from this template does. Drop it if upload size matters; all the numbers
  are in §2.
- Word COM closed cleanly. `tasklist /FI "IMAGENAME eq WINWORD.EXE"` reported no
  running instances both before and after the measurement.

---

## 8. What remains

Unchanged from the 2026-08-20 resume report, plus what this pass adds:

1. **Recover the approved Turkish text** from the writing conversation — it is
   not in the repo and blocks the 30-point block.
2. **Close the page gap.** 44 pages against a 27-page body budget; at the
   measured 245.6 w/p that is **≈ 4 175 words, about 39% of the body**.
3. **Three docx items still open** — table borders, Heading 2 bold, template
   timestamp residue.
4. **Push the four commits**, and decide whether the five untracked documents
   and `dev_predictions.csv` should stop being single-copy.
5. **Fix or record `test_render_result_escapes_html`** — 1 failed / 415 passed
   at HEAD.
6. **Decide the terminology** for *counterfactual* (currently absent entirely),
   and **resolve the Detoxify vendor wording and access date** (absent entirely).
7. **Run a full-history secret scan** before any public mirror — none has been run.
8. **Install matplotlib** if any figure is to be rendered at all.
