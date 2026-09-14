# Orchestration handoff bundle — MANIFEST

**Assembled:** 2026-08-21
**Repo:** `nsosyal-bstar` (`C:\Projects\NSosyal`), branch `master`, HEAD `6731345d5098aa37df99c8d1212d8258f3e0828a`
**Mode:** read-only. Nothing was modified, staged, committed or reformatted.
The only writes are this `handoff_bundle/` directory and one build (§A2), which
went to `handoff_bundle/measure/`, not to `report/build/`.

**Rule applied throughout:** every claim below names the path it came from.
Where a file or fact does not exist, this says so. Nothing was reconstructed
from memory or inferred from the drafts.

> **Two things I could not check.** `MASTER_HANDOFF_FULL.md` and
> `MASTER_PROMPT_REPORT_WRITING.md` **do not exist in this repository** — not in
> the working tree, not in any ignored file, not anywhere in git history. The
> brief says the receiving conversation already holds `MASTER_HANDOFF_FULL.md`.
> That means **I cannot check anything against it**, including its own warning
> that it has been wrong seven times. Every contradiction in §6 is therefore
> repo-internal: file vs file, or file vs measurement.

---

## 1. Files copied

| Bundle path | Source in repo | Bytes | Words | Last commit to source |
|---|---|---:|---:|---|
| `drafts/01_veri_ve_deney_kurgusu.md` | `report/01_veri_ve_deney_kurgusu.md` | 14 832 | 1 709 | `1db1354` 2026-08-17 |
| `drafts/02_yontem.md` | `report/02_yontem.md` | 20 547 | 2 253 | `3bc0d2e` 2026-08-19 |
| `drafts/04_bulgular.md` | `report/04_bulgular.md` | 42 762 | 5 052 | `1db1354` 2026-08-17 |
| `drafts/05_sinirliliklar.md` | `report/05_sinirliliklar.md` | 25 975 | 2 923 | `1db1354` 2026-08-17 |
| `protocols/01_baseline_diagnosis.md` | `phases/01_baseline_diagnosis.md` | 14 405 | 2 175 | `837c351` 2026-08-15 |
| `protocols/04_calibration.md` | `phases/04_calibration.md` | 6 907 | 1 095 | `7242352` 2026-08-16 |
| `protocols/08_lexical_analysis.md` | `phases/08_lexical_analysis.md` | 8 867 | 1 379 | `7ef51a0` 2026-08-17 |
| `protocols/09_deeper_analysis.md` | `phases/09_deeper_analysis.md` | 24 861 | 3 845 | `910d21e` 2026-08-17 |
| `protocols/11_prior_correction.md` | `phases/11_prior_correction.md` | 20 027 | 3 066 | `5ba53cd` 2026-08-18 |
| `protocols/12_threshold_policy.md` | `phases/12_threshold_policy.md` | 26 251 | 4 115 | `b0f2b0b` 2026-08-19 |
| `results_findings/02_failure_analysis__findings.md` | `results/02_failure_analysis/findings.md` | 12 180 | 1 946 | `a500d08` 2026-08-15 |
| `results_findings/03_defense__findings.md` | `results/03_defense/findings.md` | 8 255 | 1 322 | `19ce53c` 2026-08-16 |
| `results_findings/04_calibration__findings.md` | `results/04_calibration/findings.md` | 10 932 | 1 825 | `8012c71` 2026-08-16 |
| `results_findings/05_final_test__findings.md` | `results/05_final_test/findings.md` | 8 740 | 1 380 | `5604586` 2026-08-16 |
| `results_findings/08_lexical_analysis__findings.md` | `results/08_lexical_analysis/findings.md` | 17 982 | 3 001 | `3bc0d2e` 2026-08-19 |
| `results_findings/09_stage_1__findings.md` | `results/09_deeper_analysis/stage_1/findings.md` | 15 335 | 2 383 | `3bc0d2e` 2026-08-19 |
| `results_findings/09_stage_1b__findings.md` | `results/09_deeper_analysis/stage_1b/findings.md` | 8 354 | 1 294 | `09ce5f8` 2026-08-17 |
| `project_docs/PROJECT_HISTORY.md` | `docs/PROJECT_HISTORY.md` | 45 698 | 6 924 | `98e27c1` 2026-08-17 |
| `project_docs/REPORT_EVIDENCE.md` | `docs/REPORT_EVIDENCE.md` | 111 180 | 14 999 | `f7ab25c` 2026-08-19 |
| `project_docs/10_sablon_mapping.md` | `phases/10_sablon_mapping.md` | 36 032 | 5 666 | `3bc0d2e` 2026-08-19 |
| `project_docs/verification_sweep_2026_08_20.md` | `docs/verification_sweep_2026_08_20.md` | 61 359 | 8 508 | **UNTRACKED — never committed** |
| `demo/app.py` | `demo/app.py` | 18 629 | 1 882 | `4983422` 2026-08-19 |
| `demo/README.md` | `demo/README.md` | 7 073 | 1 023 | `e0ce657` 2026-08-20 |
| `demo/examples.json` | `demo/examples.json` | 2 455 | 295 | `5207fa6` 2026-08-16 |
| `approved/NOT_FOUND.md` | *(written by this pass — §A1 verdict, no prose)* | 1 528 | 219 | — |
| `measure/sections_1_2_standin.docx` | *(built by this pass — §A2)* | 2 487 033 | — | — |
| `measure/build_docx.py.copy` | `report/build_docx.py` | 25 461 | — | `f723b91` 2026-08-20 |

Three files were added beyond the brief's list because §5 answers rest on them:
`project_docs/10_sablon_mapping.md` (the KYS check-item map, the only place the
template's own section numbering is recorded), `project_docs/REPORT_EVIDENCE.md`
(every figure a report sentence could rest on), and
`project_docs/verification_sweep_2026_08_20.md`.

> **`verification_sweep_2026_08_20.md` is untracked.** The single most
> load-bearing analysis document in the repo — the source of the figure-readiness
> verdict, the correction-row recount and the six-protocol timestamp table — has
> never been committed. It exists only on this workstation.

---

## 2. Requested in §B but NOT FOUND

Each was searched in the working tree (including ignored files) **and** across
all of git history. All are absent, not merely uncommitted.

| # | Item | Status |
|---|---|---|
| 1 | `MASTER_PROMPT_REPORT_WRITING.md` — the style-rule list | **DOES NOT EXIST.** No file of that or any similar name. `find . -iname '*MASTER_PROMPT*'` and the same search over `git log --all --name-only` both return nothing. The nearest thing in the repo is `docs/claude_master_brief.md` (7 896 bytes), which is an engineering-conduct prompt, **not** a report style-rule list. It is not a substitute and was not copied as one. |
| 2 | `CONTENT_*.md` section-brief files | **NONE EXIST.** Zero files matching `CONTENT_*` anywhere, in tree or history. |
| 3 | `results/*/findings.json` | **NO SUCH FILE HAS EVER EXISTED.** The per-phase findings are **`findings.md`**, seven of them, all copied to `results_findings/`. `git log --all --name-only | grep findings` returns only the seven `.md` paths. The brief's `.json` is a wrong assumption, not a missing file. |
| 4 | Running bibliography for section 9 | **DOES NOT EXIST.** No `.bib` file; no `Kaynakça` or references section anywhere. `phases/10_sablon_mapping.md:225` records the check item *"Kaynakça eksiksiz listelenmiş"* as `NONE`: *"There is no bibliography in the repository."* `docs/REPORT_EVIDENCE.md:1749` states it directly: *"The repository has no bibliography and no in-text [n] citations."* The Çöltekin corpus — the data source for every measurement — is referenced by filename, SHA-256, project URL and HuggingFace id, but has **no bibliographic entry** (`REPORT_EVIDENCE.md:1736`). |
| 5 | Team roles for section 8.1 | **DOES NOT EXIST.** `phases/10_sablon_mapping.md:213–215` marks all three 8.1 check items `EXTERNAL`: team composition, member disciplines and team size are *"not recorded anywhere in the repo. Needs the lead."* Nothing to copy, with or without names. The template's no-names constraint is quoted at `10_sablon_mapping.md:217–219` and is not in dispute — there is simply no roles material of any kind. |
| 6 | UI/UX design notes, user-flow files, accessibility audit records | **NO DEDICATED FILE EXISTS.** No design-notes file, no user-flow diagram, no accessibility audit document. What exists instead, and was copied: `demo/README.md` (its *"What the screen shows"* and *"Why not Gradio or Streamlit"* sections) and `demo/app.py` itself, which **does** contain real accessibility constructs — see contradiction 3 in §6, which matters more than this row. |

Also absent, checked because the brief referenced it: `report/final/` does not
exist. `report/` holds exactly the four drafts, `build_docx.py`, and the
gitignored `build/` output.

---

## 3. §A1 — the approved Turkish text

### Verdict: **state 3 — not in the repository at all.**

Full evidence is in `approved/NOT_FOUND.md`. In brief:

- `git log --all --diff-filter=A --name-only -- 'report/**'` returns only the
  four drafts and `build_docx.py`. `--diff-filter=D` is empty — nothing under
  `report/` was ever added and later moved or deleted.
- `git grep -l -i "proje konusu\|katma değer ve yenilikçilik" $(git rev-list --all)`
  hits exactly one path, in all 25 commits that contain it:
  `phases/10_sablon_mapping.md`. That file self-describes as
  *"a map, not a draft"* (`10_sablon_mapping.md:3`) and contains no report prose.
- No `report/final/`, no `approved/`, no `CONTENT_*`, in tree or history.

Nothing was reconstructed. Recover it from the writing conversation.

### The numbering trap — read this before writing

The template's **1.1 / 1.2 / 2.1 / 2.2** (`phases/10_sablon_mapping.md:77,86,96,106`):

| § | Template heading | Points |
|---|---|---:|
| 1.1 | Proje Konusu ve amacı | 7 |
| 1.2 | Proje Kapsamı ve Yöntemi | 8 |
| 2.1 | Problem Tanımı ve Mevcut Çözümler | 7 |
| 2.2 | Çözüm Fikri, Özgünlük ve Yerlilik | 8 |

7 + 8 + 7 + 8 = **30 points**, matching the brief.

The raw drafts **also** number sections 1.1/1.2/2.1/2.2 — but they are
*Veri kümesi*, *Dondurulmuş sözlük ve eşleşme kuralı*,
*Model ve eğitim yapılandırması*, *Bölünmenin dondurulması*
(`report/01_veri_ve_deney_kurgusu.md:9,39`; `report/02_yontem.md:11,89`).
**Different content entirely.** The two schemes must not be conflated — and note
this is exactly what the §A2 fallback forced.

---

## 4. §A2 — the words-per-page correction ratio

**Word/COM was available** (Word 16.0.20228) and the measurement ran. It is a
real measurement, not an estimate.

### What was measured, and the label that matters

A1 came back empty, so per the brief's fallback I measured **sections 1 and 2 of
the raw drafts** — `report/01_veri_ve_deney_kurgusu.md` + `report/02_yontem.md`.

> **This is a stand-in for a different body of text.** As §3 shows, the drafts'
> sections 1–2 are the data/experiment setup and the method — *not* the
> template's Proje Konusu / Kapsam / Problem / Çözüm. The words-per-page **rate**
> transfers (same template, same styles, comparable table density); the **word
> counts do not**. Do not use 3 621 words as a target for the approved sections.

Built by importing `report/build_docx.py` unmodified and overriding its
`SOURCES` / `OUT` globals in memory, so the committed builder was not touched and
`report/build/report_draft.docx` was not overwritten. Output:
`measure/sections_1_2_standin.docx`.

### The measurement

Opened read-only, `Repaginate()` called, closed with `Saved = $true` so Word
never wrote to the file. Page count cross-checked the same three ways as the
44-page measurement:

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

**The control validates the instrument.** I re-measured the existing
`report/build/report_draft.docx` with the same freshly-written script and got
44 pages / 10 806 words / 76 873 characters / 36 tables — identical to the
2026-08-20 record. The scripts lost with the old scratchpad are reproduced
correctly; both are at `measure/` alongside the build harness.

### Words per page — derived

| Basis | Arithmetic | Rate |
|---|---|---:|
| Stand-in, Word's own count | 3 621 / 15 | **241.4 w/p** |
| Stand-in, python-docx count | 3 637 / 15 | 242.5 w/p |
| Full document, Word's own count | 10 806 / 44 | **245.6 w/p** |

**Stated answer: ≈ 241–246 words per page, and 245.6 w/p is the figure to plan
with** — it comes from the larger sample and from the document that actually has
to fit. The two independent samples agree within 1.7%, which is the useful
result: the rate is stable across different section mixes, so it can be trusted
for forecasting the approved sections.

### What that rate implies

- 27-page body budget × 245.6 = **≈ 6 631 words of body available**
- Current body: **10 806** Word-words
- Overshoot: **≈ 4 175 words — about 39% of the body must go**, if the cut is
  taken in text alone at the current table density

python-docx counts ~0.6% higher than Word (10 875 vs 10 806; 3 637 vs 3 621),
because Word does not count some table-cell and separator artifacts as words.
Either is fine for planning; do not mix them in one calculation.

---

## 5. §C — the nine answers

**C1 — Terminology: `ters olgusal` vs `karşı olgusal`.**
**Neither appears. The count is 0 and 0.** Across all four drafts: `ters olgusal`
0, `karşı olgusal` 0, and a widened search (bare `olgusal`, `karşıolgusal`,
`kontrafakt`, English `counterfactual`) returns zero in `report/`. The only file
in the repo containing either string is
`docs/verification_sweep_2026_08_20.md:321–338`, which is the sweep *reporting
this same absence*. **There is no ruling to make between two variants — the
concept is simply not named in the drafts.** If the approved text or section 3.1
needs the term, it is being introduced for the first time and the choice is free.

**C2 — Detoxify.**
**Not recorded — and stronger than that: the string "Detoxify" does not appear
anywhere in the repository**, in any file type, in the working tree or in any
commit in history. No vendor wording, no access date, no placeholder. There is
also no `erişim tarihi` / "accessed" convention recorded anywhere.

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
The tracked tree is clean; five untracked files remain, and this bundle adds a
sixth entry (`handoff_bundle/`) — see §8.

**C4 — The failing test.**
**Yes, still failing at HEAD.** Run just now:

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
working copy is identical to HEAD, so there is no uncommitted rewrite either. I
found no claim anywhere in the repo that a README rewrite was performed — so this
is "the README was never rewritten", not "the rewrite is uncommitted".

**C6 — Secret scan.**
**No.** No evidence of any full-history secret scan. No `gitleaks`,
`trufflehog`, `detect-secrets` or `git-secrets` config, output, log or mention
anywhere in the repo. The only match for "credential" is
`docs/repo_inventory_2026_08_17.md:615`, discussing `git config --get
credential.helper` while proving the remote is private — unrelated.
**A scan has not been run, and no tooling for one is present.**

**C7 — The three docx items: all three still OPEN, none applied.**
`report/build_docx.py` is byte-identical to its state at `f723b91` (`git diff
HEAD` empty; still the only commit that touched it), and
`report/build/report_draft.docx` still has sha256
`c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1` — the same
build recorded on 2026-08-20. Specifically:

- **Table borders** — still absent. `grep -c tblBorders report/build_docx.py` = **0**.
- **Heading 2 bold** — still removed. `build_docx.py:460` reads
  `set_style_font(h2, "Arial Black", 12, bold=False)`.
- **`cp:revision` / timestamps** — still inherited. `grep -c -i revision` = **0**;
  `clear_core_properties()` (`build_docx.py:342–347`) clears exactly the seven
  named fields and does not touch `revision`, `created` or `modified`. The
  stand-in built today still carries `<cp:revision>4</cp:revision>` and the
  2026-08-13 dates.

**C8 — Figures. The resume report is CORRECT; I confirm it.**
Only the **risk–coverage curve** is plottable from committed artefacts:
`results/04_calibration/calibration.json` → `variants.raw.risk_coverage`, 11 full
points (coverage, macro_f1, error_rate, n_auto, n_deferred, off_recall,
off_precision, threshold). The other two are **not** plottable:

- *Score distribution by slice* — `results/09_deeper_analysis/stage_1/stage1_auc.json`
  holds summary statistics only (`n`, `mean`, `q1`, `median`, `q3`,
  `share_below_0.5`). No score arrays. A box-plot is possible from the
  quartiles; a histogram or density is not.
- *ROC curves per slice* — the same file records AUC scalars and CIs but **no
  `fpr` / `tpr` arrays**.

Both missing figures need the raw per-row scores, which exist in exactly one
place: the gitignored `dev_predictions.csv`. **Two further blockers the resume
report does not mention: `matplotlib` is not installed in `.venv` and is not in
`requirements.txt`** (`verification_sweep:1216`).

**C9 — `dev_predictions.csv`: gitignored AND present locally.**

- Ignored by `.gitignore:41`, rule `results/**/*predictions*.csv` — confirmed by
  `git check-ignore -v`.
- Not tracked, and never was (`git ls-files --error-unmatch` fails; nothing in history).
- **Present locally** at `results/01_baseline_berturk/dev_predictions.csv`,
  **736 591 bytes**, mtime 2026-08-17 15:21, columns
  `row_id,text,gold,pred,confidence,slice` with `confidence` = P(OFF).
- Its integrity is pinned and verified `pass: true` in
  `results/12_threshold_policy/c12_16_intervals.json`, sha256
  `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346` — so the
  local copy is provably the right one.

**Net for C9:** section 3.2 and the demo fixture can be served **on this
workstation only**. A fresh clone does not have this file and cannot regenerate
it without a training run. It is a single-copy artefact whose loss is not
recoverable from the repository.

---

## 6. §D — contradictions found

Ranked by how much damage each would do if it reached the report unnoticed.
All are repo-internal; `MASTER_HANDOFF_FULL.md` was unavailable to check against.

### 1. The 450 words/page planning assumption is wrong by 1.83× — and it is the origin of the whole page crisis

`phases/10_sablon_mapping.md:232` converts word counts at **450 words/page** and
concludes `report/` totals **26.0 pages**, then *"26 + 3 = 29 of the 30 available
pages"*. The measured rate is **245.6 w/p** and the real count is **44 pages**.

The file does hedge — it calls the estimate *"conservative in one direction that
matters"* because of table density, and says *"Real page counts will be higher"*.
But "higher" was carrying an 18-page error, and the 29-of-30 conclusion reads as
"we just fit". **Any planning still resting on 450 w/p, or on the 26-page figure,
is wrong by a factor of 1.83.** This is the single most consequential number in
the bundle.

### 2. `results/*/findings.json` does not exist and never did — the brief's own assumption

The seven per-phase findings files are **`findings.md`**, not `.json`. Verified
in the tree and across all history. If any downstream tool, prompt or checklist
expects to parse `findings.json`, it will silently find nothing. Copied as `.md`
to `results_findings/`.

### 3. The 3.3 accessibility verdict of `NONE` is STALE — accessibility work exists and shipped

`phases/10_sablon_mapping.md:146` records *"Erişilebilirlik yaklaşımı
belirtilmiş"* as **`NONE`** — *"No accessibility material of any kind — no
contrast, keyboard, screen-reader, WCAG or assistive-technology consideration
anywhere in `demo/` or `report/`."*

`docs/RESULTS_LOG.md:54` (2026-08-19) records the opposite, and `demo/app.py`
confirms it in source at HEAD:

- `aria-live="polite"` and `tabindex="-1"` on the results region — `app.py:298`
- a bound `<label for="inp">` — `app.py:295`
- `:focus-visible` outline — `app.py:177`
- per-element `lang` marking, root `lang="en"` with Turkish content marked
  `lang='tr'` — `app.py:288, 246, 285, 296`
- `html.escape()` on the previously unescaped `examples.json` fields — `app.py:279–284`

`docs/repo_inventory_2026_08_17.md:510` flags this too: *"this partially
contradicts the stated answer"*, noting contrast ratios that *"happen to pass
WCAG AA for body text"*.

**This is worth up to 2 points that the map currently writes off as zero.**
But the claim must be bounded exactly as `RESULTS_LOG.md:54` bounds it:
*"Verified at renderer level only … the accessibility changes rest on source
inspection plus AST parse, not on rendered output or any screen reader. No
accessibility claim may be made in the report beyond 'implemented, verified by
source inspection' until the demo runs end-to-end."*

### 4. The correction-row count is stale in `PROJECT_HISTORY.md` — five vs seven

`docs/PROJECT_HISTORY.md` §5 opens *"Five correction rows exist in
`docs/RESULTS_LOG.md`."* There are now **seven** correction-type rows (six
`CORRECTION` + one `SPEC DEFECT`) — lines 29, 39, 42, 43, 46, 52, 56. The "five"
was true on 2026-08-17; two more were appended 2026-08-19 and PROJECT_HISTORY was
never updated. Already caught at `verification_sweep` §5b, repeated here because
`PROJECT_HISTORY.md` is in this bundle and still says five.

Related, and unverifiable from here: `RESULTS_LOG.md:52` refers to *"the same
kind as the eight previously recorded in this log"* — a different tally again,
and a different unit (controller errors, not correction rows). The brief says
`MASTER_HANDOFF_FULL.md` warns it *"has been wrong seven times"*. **Three
different counts — five, seven, eight — are in circulation for
overlapping-but-not-identical things. Pin the definition before citing any of
them in section 3.1.**

### 5. The most load-bearing analysis document in the repo is untracked

`docs/verification_sweep_2026_08_20.md` (61 359 bytes) has never been committed.
It is the sole source for the figure-readiness verdict (C8), the correction-row
recount (contradiction 4) and the six-protocol timestamp table (§7). So are
`docs/onboarding_readiness_audit_2026_08_18.md`,
`docs/docx_build_environment_check_2026_08_20.md`, the docx resume report and
`repo_conventions.md` (78 158 bytes). **Five substantial documents exist on one
workstation only.** Combined with C9's single-copy `dev_predictions.csv` and the
four unpushed commits, the project's unique-copy surface is larger than the
handoff implies.

### 6. Two figure blockers the 2026-08-20 resume report omits

The resume report says only the risk–coverage curve is plottable — correct, and
C8 confirms it. But it presents the gitignored `dev_predictions.csv` as the sole
obstacle. **`matplotlib` is neither installed in `.venv` nor listed in
`requirements.txt`** (`verification_sweep:1216`). No figure at all can be
rendered in this environment today, including the risk–coverage curve that is
otherwise data-ready.

### 7. Minor: the resume report's "ahead by 3"

`docs/docx_pipeline_state_2026_08_20.md` records master as ahead of origin by 3.
It is **4** — the state doc was itself committed afterwards as `6731345`. Already
noted at the top of the resume report; repeated only so the receiving
conversation does not treat "3" as current.

### Checked and found NOT contradictory

Recorded so nobody re-litigates them. The 27-page body budget is consistent:
`phases/10_sablon_mapping.md:250` states a 30-page cap with 3 pages reserved for
cover, contents and bibliography, giving 27 of body, exactly as the resume report
says. And the four drafts' byte sizes match the state doc's census exactly
(14 832 / 20 547 / 42 762 / 25 975).

---

## 7. §B — the six pre-registration protocols, with both timestamps

Section 3.1's provenance argument rests on this margin, so both ends are given as
commit SHA + author timestamp. **I verified each independently** with
`git log --all --follow --diff-filter=A` rather than relaying
`verification_sweep` §5a; all six agree with it.

| # | Protocol file | Protocol commit | Protocol timestamp | First result commit | Result timestamp | Margin |
|---|---|---|---|---|---|---|
| 1 | `phases/01_baseline_diagnosis.md` | `197d953` | 2026-08-15 15:09:28 +03 | `685d4af` | 2026-08-15 19:29:33 +03 | **+4h 20m 05s** |
| 2 | `phases/04_calibration.md` | `ab225ad` | 2026-08-16 13:34:34 +03 | `8012c71` | 2026-08-16 13:53:23 +03 | **+18m 49s** |
| 3 | `phases/08_lexical_analysis.md` | `b127d44` | 2026-08-17 12:42:25 +03 | `7ef51a0` | 2026-08-17 13:08:40 +03 | **+26m 15s** |
| 4 | `phases/09_deeper_analysis.md` | `bcb4b70` | 2026-08-17 15:24:00 +03 | `120eead` | 2026-08-17 15:37:17 +03 | **+13m 17s** |
| 5 | `phases/11_prior_correction.md` | `d589dba` | 2026-08-18 16:30:17 +03 | `a96f02d` | 2026-08-18 17:08:56 +03 | **+38m 39s** |
| 6 | `phases/12_threshold_policy.md` | `ec2fd3a` | 2026-08-18 18:06:47 +03 | `d74acd9` | 2026-08-19 11:37:55 +03 | **+17h 31m 08s** |

All six protocols precede the first numeric result of their phase. Commit
subjects confirm the roles — e.g. `ab225ad` *"Phase 04 pre-registration:
calibration split, ECE definition, operating-point protocol"* → `8012c71`
*"Phase 04 results: raw needs no calibration…"*.

**Three caveats that belong with these numbers:**

1. **Row 3 requires `--follow`.** `phases/08_lexical_analysis.md` entered version
   control as **`phases/06_…`** (`b127d44`, subject *"Phase 06 pre-registration:
   word-level lexical dependence"*) and was renumbered because the demo already
   held 06. A plain `git log -- phases/08_…` reports the **rename** commit
   `7ef51a0` as the add, which would collapse the margin to zero and make the
   pre-registration look simultaneous with its own result. Use `--follow`.
2. **Three of the nine `phases/` files are not pre-registrations** and are
   correctly excluded: `03_defense_design.md` (no pre-registration language,
   committed as "Phase 03 step 1"), `07_report.md` (report outline),
   `10_sablon_mapping.md` (*"a map, not a draft"*).
3. **The Phase 12 C12-16 addendum is not covered by row 6.** It was committed at
   `b0f2b0b` **after** the point estimates were published, and its own artefact
   says so: *"estimation after the fact, not pre-registration."* It is the source
   of figures 3l–3o. The six-document claim is about the phase pre-registrations,
   not about every clause inside them.

---

## 8. Handling notes

- **`handoff_bundle/` is NOT gitignored.** The brief assumed it was; it is not.
  I did not edit `.gitignore` (read-only). The directory therefore **appears as
  untracked in `git status`**. Nothing here is staged or committed. Either add
  the ignore rule or delete the directory after upload.
- `measure/sections_1_2_standin.docx` is **2.49 MB** — it carries the template's
  five embedded fonts and two unreferenced media files, as every build from this
  template does. Drop it if upload size matters; the numbers are all in §4.
- Word COM was closed cleanly. `tasklist /FI "IMAGENAME eq WINWORD.EXE"` reports
  no running instances, before and after.
- Nothing under `report/`, `results/`, `phases/` or `docs/` was modified.
  `report/build/report_draft.docx` was **not** rebuilt or overwritten — the §A2
  build went to `handoff_bundle/measure/`.
