# VERIFICATION SWEEP — NSosyal B*, sections 1.1/1.2, 2.1/2.2, 3.1, 3.2, 4.1

**Date:** 2026-08-20
**Repo:** `nsosyal-bstar` (`C:\Projects\NSosyal`)
**Mode:** read-only. No training, evaluation or bootstrap was re-run. Every figure below
was read from a recorded artefact.
**Nothing was fixed, adjusted or reconciled.** Mismatches are reported as findings.

## Two notes before the items

**1. Item numbering collides.** The base sweep has items 1–8; the addendum also starts at
8. Both are answered below, as **§8 (repository link)** and **§8-ADD (software stack)**.

**2. The working tree changed during the sweep, and not by me.** At the start of this
session `git status --porcelain --untracked-files=no` was empty. It now reads:

```
A  NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx
```

The KYS template has been copied to the repo root and `git add`-ed (not committed; HEAD is
still `e0ce657`). Its sha256 is `5593d29b…89965a`, identical to the `Downloads` copy. I ran
no `git add`, no `cp` and no write of any kind — every command was `cat`/`grep`/`find`/
`git log`/read-only Python, plus one `pytest` run with `-p no:cacheprovider` and
`PYTHONDONTWRITEBYTECODE=1` so it created nothing. The staging happened outside my tool
calls. I have left it exactly as found.

---

# 1. INTERVAL SWEEP

**Discovered by enumeration, not from a supplied phase list.** 23 artefacts under `results/`
carry bootstrap/CI metadata. Values below are read from the artefacts.

| Artefact | alpha | ci_level | n_boot | seed |
|---|---|---|---|---|
| `results/01_baseline_berturk/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/01_baseline_berturk/run_config.json` | 0.05 | absent | 1000 | 42 |
| `results/02_failure_analysis/fn_tags.json` | absent | absent | absent | 42 |
| `results/02_failure_analysis/slice_sensitivity.json` | 0.05 | absent | 1000 | 42 |
| `results/03_defense/augmentation_review.json` | absent | absent | absent | 42 |
| `results/03_defense/comparison.json` | **absent** | absent | 1000 | 42 |
| `results/03_defense/run_1a/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/03_defense/run_1a1b/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/03_defense/run_1a1b_d/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/03_defense/run_raw/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/03_defense/train_oof_summary.json` | absent | absent | absent | 42 |
| `results/04_calibration/cal_eval_split.json` | absent | absent | absent | 42 |
| `results/04_calibration/calibration.json` | **absent** | absent | 1000 | 42 |
| `results/05_final_test/metrics.json` | 0.05 | absent | 1000 | 42 |
| `results/05_final_test/paired_deltas.json` | **absent** | absent | 1000 | 42 |
| `results/08_lexical_analysis/token_stats.json` | 0.05 † | absent | **10000** | **absent** |
| `results/09_deeper_analysis/stage_1/stage1_auc.json` | 0.05 | absent | **10000** | 42 |
| `results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json` | **absent** | absent | **10000** | 42 |
| `results/11_prior_correction/metrics.json` | 0.05 | absent | **10000** | 42 |
| `results/12_threshold_policy/c12_16_intervals.json` | 0.05 | absent | **10000** | 42 |
| `results/12_threshold_policy/metrics.json` | 0.05 | absent | **10000** | 42 |
| `results/15_deixis/cell_counts.json` | absent | absent | absent | 42 |
| `results/day1_report_rerun.json` | absent | absent | absent | 42 |

† `token_stats.json` records `thresholds.alpha_familywise = 0.05`, which is a
multiple-testing threshold, **not** a stated CI level. The CI block itself
(`step3.primary.diff_matched_ci`) records only `ci_low`, `ci_high`, `n_resamples: 10000` —
no alpha, no method.

**Global distinct values:** alpha `[0.05]` · n_boot `[1000, 10000]` · seed `[42]`.
No `ci_level` key exists in any artefact. **No BCa anywhere** (`grep -ril bca results/` → empty).

### Interval methods, verbatim

| Artefact | recorded method |
|---|---|
| `01/metrics.json` | `"independent (disjoint slices), percentile CI"` |
| `02/slice_sensitivity.json` | `"independent (disjoint slices), percentile CI"` |
| `05/metrics.json` | `"independent (disjoint slices), percentile CI"` |
| `09/stage_1/stage1_auc.json` | `"stratified over the four slice x gold cells, percentile interval"` |
| `09/stage_1b/stage1b_defense_auc.json` | `"paired: rows resampled once per replicate, both systems scored on the same rows"` — **interval type not named** |
| `11/metrics.json` | `"nonparametric, stratified over the four (slice x gold) EVAL cells 182/127/278/1795, … percentile interval"` |
| `12/c12_16_intervals.json` | `"interval_type": "percentile"` (per-quantity) |
| `12/metrics.json` | **no method string.** Structure recorded: `paired: true`, `strata` = 4 cells, `thresholds_refitted_inside_replicate: false` |
| `04/calibration.json` | **no method string, no alpha** |
| `08/token_stats.json` | **no method string** |

### Verdict — **NOT UNIFORM. MISMATCH.**

The gated sentence is *"Rapor boyunca verilen bütün aralıklar %95 önyükleme güven
aralığıdır"*. Against the artefacts:

- **One level — supportable but not fully recorded.** `alpha = 0.05` is the *only* level
  found anywhere; no artefact records a different one. But alpha is **absent** from four
  interval-bearing artefacts (`03/comparison.json`, `04/calibration.json`,
  `05/paired_deltas.json`, `09/stage_1b`). For those, 95% is an assumption, not a reading.
- **One method — NO.** Three distinct resampling schemes are recorded:
  *independent/disjoint-slice* (01, 02, 05), *stratified over four slice×gold cells*
  (09 stage 1, 11, 12), and *paired* (09 stage 1b, 12). "Percentile" is the interval type
  wherever one is named, but it is **not named at all** in 04, 08, 12/`metrics.json` and
  09/stage_1b.
- **Replicate count is not uniform:** **1000** for phases 01–05, **10000** for phases
  08, 09, 11, 12.

The sentence as written asserts uniformity the artefact set does not support. It should be
deleted or narrowed, per your own gate.

---

# 2. MODEL IDENTIFIER — **PASS**

`results/01_baseline_berturk/run_config.json`, line 53:

```json
"model": "dbmdz/bert-base-turkish-cased",
```

The cased variant is confirmed **from the run record**, not from a config default or README
prose. One note: the recorded key is **`model`**, not `model_name_or_path`. No key named
`model_name_or_path` exists in the artefact.

---

# 3. FIGURES — sections 1.1 and 1.2

### `results/day1_report.json`

| # | Report | Artefact value | Verdict |
|---|---|---|---|
| 3a | 31756 | `"n_rows": 31756` | **PASS** |
| 3b | 19,3 % | **percentage NOT RECORDED as a field** | see below |
| 3c | 6131 | `"off_total": 6131`, `"label_dist": {"NOT": 25625, "OFF": 6131}` | **PASS** |
| 3d | 3892 | `"lexicon_free_root": 3892` | **PASS** |
| 3e | 63,5 % | **proportion NOT RECORDED as a field** | see below |

**3b / 3e.** Neither percentage is stored anywhere in the artefact — only their integer
components are. Per the sweep rule I report them as **NOT RECORDED**. The components do
settle the "of 31756, not of 35284" question: `6131 / 31756` lands at 19.3 % and
`6131 / 35284` would give 17.4 %, so the report's denominator is the right one. The 63,5 %
likewise corresponds to `3892 / 6131`. Both are consistent, but neither was read as a value.

An independent corroboration exists for 3b: `results/08_lexical_analysis/token_stats.json`
records `base_rate.p_off_train_computed = 0.193057` — **but that is the train split (26992
rows), not the full 31756.** Do not cite it for this sentence.

`results/day1_report_rerun.json` reproduces every one of these values identically.

### Phase 01 — development set

Source: `results/01_baseline_berturk/metrics.json`

| # | Report | Artefact value | Verdict |
|---|---|---|---|
| 3f | 0,8930 | `berturk.lexicon_hit.off_recall = 0.8929577464788733` | **PASS** |
| 3g | 0,5628 | `berturk.lexicon_free.off_recall = 0.5628318584070796` | **PASS** |
| 3h | +0,3301 [+0,2771; +0,3827] | `recall_gap.delta = 0.33012588807179366`, `ci_low = 0.2771480590457781`, `ci_high = 0.3826950345077446` | **PASS** |

Slice supports: `lexicon_hit` n=614 (355 OFF / 259 NOT), `lexicon_free` n=4150 (565 / 3585).

### Phase 05 — held-out test, single pass

Source: `results/05_final_test/metrics.json` → `systems.raw.recall_gap`

| # | Report | Artefact value | Verdict |
|---|---|---|---|
| 3i | +0,3970 [+0,3418; +0,4542] | `delta = 0.39699608293206257`, `ci_low = 0.3418000046134851`, `ci_high = 0.45420597387207523` | **PASS** |

`official_test_set_touched: true`, `single_pass: true`, `thresholds_re_derived_on_test: false`,
`n_test = 3528`.

### Phase 09 Stage 1 — development set

Source: `results/09_deeper_analysis/stage_1/stage1_auc.json` → `primary`

| # | Report | Artefact value | Verdict |
|---|---|---|---|
| 3j | 0,9306 | `auc_lexicon_hit = 0.930611` (CI 0.910239 – 0.949459) | **PASS** |
| 3k | 0,8962 | `auc_lexicon_free = 0.89615` (CI 0.882069 – 0.909484) | **PASS, with a rounding caveat** |

**3k caveat:** the recorded value `0.89615` sits exactly on the 4-decimal midpoint. It gives
`0,8962` under round-half-up and `0,8961` under banker's rounding. The report's `0,8962` is
defensible but is a rounding-convention choice, not a direct read. Recorded gap:
`0.034461` [0.010261, 0.058517], verdict `INTERMEDIATE`.

### Phase 12 — development set (EVAL half)

Source: `results/12_threshold_policy/c12_16_intervals.json` → `intervals`

| # | Report | Artefact value | Verdict |
|---|---|---|---|
| 3l | +0,1304 [+0,1000; +0,1609] | `d_recall`: `0.13043478260869568` [`0.10000000000000009`, `0.16086956521739137`] | **PASS** |
| 3m | +0,1727 [+0,1295; +0,2194] | `d_recall_free`: `0.17266187050359716` [`0.1294964028776978`, `0.21942446043165464`] | **PASS** |
| 3n | -0,1067 [-0,1630; -0,0484] | `d_gap`: `-0.10672780456953124` [`-0.1629773104593249`, `-0.0483832714048541`] | **PASS** |
| 3o | -0,1418 [-0,1723; -0,1131] | `d_precision`: `-0.14181617166691796` [`-0.172253772633705`, `-0.113144552676357`] | **PASS** |

All four: `interval_type: "percentile"`, `n_boot: 10000`, `alpha: 0.05`, `seed: 42`,
`excludes_zero: true`. **3l is verified here as requested, for section 4.1.**

**Scope caveat that affects how these four may be described.** The artefact says
`dev_only: true` and `"split": "EVAL only -- pooling to full dev declined by C12-16"` —
these are computed on the **EVAL half (n = 2382)**, not the full dev set (n = 4764).
Calling them "development set" figures without qualification overstates their base. The
same file also carries an explicit `ordering_disclosure`: the four quantities were fixed in
advance, but **their uncertainty was computed after the point estimates were published** —
*"This is estimation after the fact, not pre-registration."* That disclosure should travel
with any sentence citing these intervals.

---

# 4. BASELINE METRIC — 0,8271 — **PASS**

- **Which metric:** macro-F1. `berturk.overall.macro_f1 = 0.8270752670616224`.
- **Which split:** the **development set**, n = 4764 (support_off = 920; confusion
  tn 3631 / fp 213 / fn 285 / tp 635). **Not** the official test set.
- **Which phase:** Phase 01, `results/01_baseline_berturk/metrics.json`, run_id
  `01_baseline_berturk`.
- 95 % CI recorded: `[0.8138925991245577, 0.8404931829690758]` (n_boot 1000, alpha 0.05, seed 42).
- Checkpoint: `best.pt` = **epoch 1** (see §10).

**Caution for the sentence still behind the inline marker.** This is a *dev-set* macro-F1.
Published OffensEval-2020 TR figures are reported on the *official test set*. The
comparable held-out number from this project is in `results/05_final_test/metrics.json`,
not this one. Comparing 0,8271 to published test figures compares different splits.

---

# 5. METHOD CLAIMS ASSERTED AS FACT IN BODY PROSE

## 5a. Pre-registration protocol documents — report says SIX — **PASS**

Six of the nine files in `phases/` are pre-registrations. Excluded, with reason:
`03_defense_design.md` (zero pre-registration language, committed as "Phase 03 step 1"),
`07_report.md` (report outline), `10_sablon_mapping.md` (self-described as *"a map, not a
draft"*).

| # | File | Entered VC at | Date | First numeric result of that phase | Predates? |
|---|---|---|---|---|---|
| 1 | `phases/01_baseline_diagnosis.md` | `197d953` | 2026-08-15 15:09:28 | `685d4af` 2026-08-15 19:29:33 | **YES** (+4h20m) |
| 2 | `phases/04_calibration.md` | `ab225ad` | 2026-08-16 13:34:34 | `8012c71` 2026-08-16 13:53:23 | **YES** (+19m) |
| 3 | `phases/08_lexical_analysis.md` | `b127d44` | 2026-08-17 12:42:25 | `7ef51a0` 2026-08-17 13:08:40 | **YES** (+26m) |
| 4 | `phases/09_deeper_analysis.md` | `bcb4b70` | 2026-08-17 15:24:00 | `120eead` 2026-08-17 15:37:17 | **YES** (+13m) |
| 5 | `phases/11_prior_correction.md` | `d589dba` | 2026-08-18 16:30:17 | `a96f02d` 2026-08-18 17:08:56 | **YES** (+38m) |
| 6 | `phases/12_threshold_policy.md` | `ec2fd3a` | 2026-08-18 18:06:47 | `d74acd9` 2026-08-19 11:37:55 | **YES** (+17h31m) |

All six pre-registrations predate the first recorded numeric result of their phase. The
claim of six is supported and the ordering holds in every case.

*One nuance the report should not lose:* the Phase 12 **C12-16 addendum** (the source of
figures 3l–3o) was committed at `b0f2b0b5` **after** the point estimates were published —
the file says so itself. The six-document claim is about the phase pre-registrations, not
about every clause inside them.

## 5b. Correction rows — report says FIVE — **MISMATCH**

`docs/RESULTS_LOG.md` currently contains **seven** correction-type rows: six marked
`**CORRECTION**` and one marked `**SPEC DEFECT**`.

| Line | Date | Row |
|---|---|---|
| 29 | 2026-08-16 | **CORRECTION to the Phase 03 framing** (supersedes the reading, not the numbers, of the 2026-08-15 Phase 03 rows) |
| 39 | 2026-08-17 | **CORRECTION — two confidence intervals mis-transcribed in the row above** (transcription error, not a result change) |
| 42 | 2026-08-17 | **CORRECTION — the central claim is narrowed in the report** (wording change forced by the Phase 09 Stage 1 result; no number changes) |
| **43** | 2026-08-17 | **SPEC DEFECT — Phase 09 C9-8 (matched operating points) does not do what it claims**; recorded, not rewritten |
| 46 | 2026-08-17 | **CORRECTION — what the intervention demonstrates is narrowed in the report** (wording change forced by the Phase 09 Stage 1b result; the gain itself is unchanged) |
| **52** | 2026-08-19 | **CORRECTION — the row above (line 51) is false at the commit it was appended to; the EOL defect was already FIXED, not deferred. LIMITATION CLOSED.** |
| **56** | 2026-08-19 | **CORRECTION — two figures entered a workstation design justification without traceable sources; caught before the report.** |

**Where the "five" comes from, and why it is now stale.** `docs/PROJECT_HISTORY.md` §5
opens: *"Five correction rows exist in `docs/RESULTS_LOG.md`."* It lists C1–C5 = lines 29,
39, 42, 43, 46 — and C4 is exactly the *"one which records a defect in a specification"*:

> **C4 — spec defect, C9-8** *(2026-08-17, commit `910d21e`)*. … Logged as a **SPEC DEFECT**
> rather than a correction because nothing measured was wrong; the specification was.

So the report's "FIVE, one of which records a defect in a specification" faithfully
reproduces PROJECT_HISTORY as it stood on **2026-08-17**. Two further correction rows were
appended on **2026-08-19** (lines 52 and 56), after that document was written.
PROJECT_HISTORY has not been updated. **Current count is seven** (six CORRECTION + one SPEC
DEFECT), or six if the SPEC DEFECT row is excluded by its own labelling — either way, not
five.

## 5c. Append-only in practice — **PASS**

`git log --numstat` over `docs/RESULTS_LOG.md`, all 27 commits. Every commit is
`+N / −0` — pure append — **except one**:

```
3bc0d2e 2026-08-19 Byte-stability: disable EOL conversion so recorded sha256 digests verify on any platform
50	50	docs/RESULTS_LOG.md
```

That one is a whole-file line-ending renormalisation, not a content edit. Verified two ways:

```
$ git diff 3bc0d2e^ 3bc0d2e --ignore-cr-at-eol --stat -- docs/RESULTS_LOG.md
(empty)

$ git show 3bc0d2e^:docs/RESULTS_LOG.md | tr -d '\r' | sha256sum
bb0a19cf8a519108c084122040d96d6aaefbd877ea739559acac19b0bc743c44 *-
$ git show 3bc0d2e:docs/RESULTS_LOG.md  | tr -d '\r' | sha256sum
bb0a19cf8a519108c084122040d96d6aaefbd877ea739559acac19b0bc743c44 *-
```

Identical content digests. **No earlier row has been edited in place.** The log is
append-only in practice, and the one apparent exception is fully accounted for.

## 5d. Test-set guard — **PASS**

- **Implementation:** `src/data_io.py`, in `load_coltekin_test(run_final_test=False, …)`
  (line 371), documented at line 374 as *"Anti-circularity guard (briefing S7.2): this is
  the single-use resource"*. It refuses to load without an explicit flag, reads
  `config.TEST_SPEND_RECORD` (line 395) and refuses if the set is already spent, and writes
  the open log (line 420).
- **Paths:** `config.py` lines 80–81 — `TEST_OPEN_LOG`, `TEST_SPEND_RECORD`.
- **Test:** `tests/test_test_set_guard.py`; also
  `tests/test_data_io.py::test_official_test_set_refuses_to_load_without_explicit_flag`.
- **Tracking:** `config.py`, `src/data_io.py`, `tests/test_test_set_guard.py` — all
  **tracked**, none gitignored (`git check-ignore` → not ignored). The claim that it
  *"travels with the repository"* holds.
- Its state records are committed too: `results/05_final_test/TEST_SET_OPENED.json` (176 B)
  and `TEST_SET_SPENT.json` (901 B).

---

# 6. TERMINOLOGY RENDERING — **NOT FOUND (all four files)**

Per-file counts, as required — no total, no winner picked:

| File | `ters olgusal` | `karşı olgusal` | `ters-olgusal` | `karşıt olgusal` | `counterfactual` |
|---|---|---|---|---|---|
| `report/01_veri_ve_deney_kurgusu.md` | 0 | 0 | 0 | 0 | 0 |
| `report/02_yontem.md` | 0 | 0 | 0 | 0 | 0 |
| `report/04_bulgular.md` | 0 | 0 | 0 | 0 | 0 |
| `report/05_sinirliliklar.md` | 0 | 0 | 0 | 0 | 0 |

A widened search for **any** rendering — `olgusal` on its own, `counterfact`,
`karşıolgusal`, `kontrafakt` — returns **zero matches across all four files**:

```
$ grep -rniE 'olgusal|counterfact|karşıolgusal|karsiolgusal|kontrafakt' report/
(no output)
```

**The four files do not disagree with one another — none of them contains the concept in
any form.** The term exists in the repo only in English, and only outside `report/`:

```
phase03_make_augmentation.py:2:  ... build the counterfactual augmentation, for REVIEW.
phases/03_defense_design.md:72: ## Component 1 — Counterfactual token augmentation
src/augment.py:1:               Counterfactual token augmentation -- component 1 ...
tests/test_augment.py:1:        Checks for the counterfactual augmentation operators ...
```

If the report is meant to name the augmentation in Turkish, that terminology decision has
not been made yet in these four files — there is nothing to reconcile, only something to
write.

---

# 7. LEXICON — `karaliste.txt`

Located at **`data/lexicon/karaliste.txt`** (5,988 bytes). It is the only copy in the repo.

## 7a. Entry count — report says 695 — **PASS on the recorded count, with a caveat**

```
wc -l (newline count)     : 697      (file does not end with a newline)
total lines (splitlines)  : 698
non-blank                 : 698
non-blank, non-comment    : 698
unique exact              : 696      duplicates: 'ananı', 'siktim'
unique casefolded         : 695      further duplicate: 'oç'
```

**695 is the casefold-unique count**, and it matches the recorded `lexicon_size: 695` in
`results/day1_report.json` and `lexicon_entries: 695` in `08/token_stats.json`. It is the
effective loaded size — `src/lexicon.py:44` builds a **set** after `tr_lower()`, which is
what collapses 698 raw lines to 695.

The caveat is only that "695 entries" is not the file's line count. If the report says
*"695 satırlık"* or *"695 lines"* that is wrong; *"695 entries"* / *"695 unique entries"* is
right.

## 7b. sha256 — **PASS**

```
$ sha256sum data/lexicon/karaliste.txt
0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b
```

**Matches the project's own recorded value in four independent places:**

| Where the recorded value lives | Field |
|---|---|
| `results/day1_report.json` | `"lexicon_sha256"` |
| `results/day1_report_rerun.json` | `"lexicon_sha256"` |
| `results/01_baseline_berturk/run_config.json` | `hashes.lexicon_sha256` and `preconditions.lexicon_sha256` (`passed: true`) |
| `results/12_threshold_policy/c12_16_intervals.json` | `provenance.gate` — sha256 **and** byte count (`expected 5988 / observed 5988`, `pass: true`) |
| `results/05_final_test/metrics.json` | `hashes.lexicon_sha256` |

**But the file itself is gitignored** — `.gitignore:12` (`data/**`). It is absent from a
fresh clone. See §13f.

## 7c. Licence — report says CC BY-SA 4.0 — **DOES NOT EXIST / MISMATCH**

```
$ find . -iname 'LICENSE*' -o -iname 'LICENCE*' -o -iname 'COPYING*'
(no output)
```

There is **no licence file anywhere in the repository**, and none accompanying the lexicon
(`data/lexicon/` contains only `.gitkeep` and `karaliste.txt`). A repo-wide search for
`CC BY-SA`, `CC-BY-SA` or `creativecommons` returns **no match** — every hit for "licen*"
is the English verb *"licenses"* in prose (e.g. *"Phase 11's answer does not license Phase
12"*).

**The report's "CC BY-SA 4.0" is not sourced from anything in this repository.** It is
absent, not contradicted — but it cannot be cited as read. `docs/phase_briefing.md:124`
records the instruction *"Freeze the lexicon before any measurement. Record commit hash +
license + date"*; **that record was never created.**

## 7d. Upstream and clone dates — **NOT RECORDED**

- upstream first-commit date — **NOT RECORDED**
- upstream latest-commit date — **NOT RECORDED**
- date the clone was taken — **NOT RECORDED as such**

No provenance record for the lexicon exists (same missing record as 7c). Determining the
upstream dates would require contacting GitHub, which is outside a read-only local sweep,
so I have not done it and report them absent rather than fetched.

The closest recorded proxies, offered as proxies and not as answers:
`data/lexicon/karaliste.txt` has filesystem mtime **2026-08-14 13:14**, and
`results/day1_report.json` records `"frozen_at": "2026-08-14T14:43:33"`. Both bound the
freeze to 14 Aug 2026; neither is a clone date and neither says anything about upstream.

## 7e. Upstream address, verbatim — **PASS**

```
https://github.com/ooguz/turkce-kufur-karaliste
```

Recorded in `README.md:128` (as `[turkce-kufur-karaliste](https://github.com/ooguz/turkce-kufur-karaliste)`,
noted *"frozen Day 1"*) and `docs/phase_briefing.md:97`. An alternate source is listed and
was not used: `https://github.com/d35k/Turkish-Swear-Words`.

---

# 8. REPOSITORY LINK AND HISTORY (base sweep — for 3.1)

## 8a. Remote, privacy, mirror

```
$ git remote -v
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (fetch)
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (push)
```

Exactly one remote. **No public mirror is configured** — there is no second remote, and no
mirror reference anywhere in the repo.

**Privacy: NOT VERIFIABLE from a read-only local sweep.** Whether
`github.com/MusaabAlt/nsosyal-bstar` is private is a server-side fact; confirming it means
an authenticated API call. I did not make one, and I did not create anything. So: *no
public mirror exists locally, and no evidence of one exists in the repo* — but I cannot
certify the remote's visibility setting from here. If you need that certified, run
`gh repo view MusaabAlt/nsosyal-bstar --json visibility` yourself.

## 8b. Commit count and date range

```
$ git rev-list --count master
67

FIRST: c33d1bd 2026-08-15 14:32:05 +0300  Project scaffold + ported Day 1 lexicon logic
LAST:  e0ce657 2026-08-20 01:25:47 +0300  deps and demo docs: state the actual runtime, drop gradio
```

**67 commits**, spanning **2026-08-15 → 2026-08-20** (5 days 11 hours).

## 8c. Real incremental history, not squashed or imported — **SUPPORTS the 3.1 sentence**

The history is genuinely incremental. Evidence:

- 67 commits across 6 calendar days, not one import commit.
- The first commit is a **scaffold** (`c33d1bd "Project scaffold + ported Day 1 lexicon
  logic"`), which is what a real project start looks like — not a bulk drop of finished work.
- Commit messages track a working process, in order: pre-registration → result → correction
  (`197d953` pre-registrations → `685d4af` Phase 01 result → `19ce53c` "Correct the Phase 03
  framing"), including commits that record failure and reversal (`5b080b5` "Phase 11 Run B:
  declined, logged as a decision", `9d3c8c6` "CORRECTION: EOL limitation was already
  closed…").
- `docs/RESULTS_LOG.md` alone was touched by 27 separate commits, 26 of them pure appends
  (§5c).
- Interleaved code/results/docs commits, with `--diff-filter=A` showing artefacts entering
  after their pre-registrations (§5a).

The check item *"commit geçmişiyle takip edilebilir bir geliştirme süreci"* is well
supported. A single import commit would not produce this shape, and this is not that.

## 8d. Top-level directories

```
.claude   .git   .idea   .pytest_cache   .venv   __pycache__
data   demo   docs   legacy   notebooks   phases   report   results   src   tests
```

Of these, the ones 3.1 can describe as project structure (the rest are tooling/venv):

| Directory | Contents |
|---|---|
| `data/` | corpora + frozen lexicon + splits (mostly gitignored — see 13f) |
| `demo/` | offline demo app and asset builder |
| `docs/` | RESULTS_LOG, PROJECT_HISTORY, REPORT_EVIDENCE, handoffs, audits |
| `legacy/` | ported Day 1 code |
| `notebooks/` | Colab runbooks |
| `phases/` | phase pre-registrations (§5a) |
| `report/` | the four Turkish report drafts |
| `results/` | committed experiment artefacts (§13e) |
| `src/` | library code (data_io, models, lexicon, calibration, evaluate, augment, …) |
| `tests/` | pytest suite (§13d) |

---

# 8-ADD. SOFTWARE STACK (addendum — two environments, reported separately)

## 8a-ADD. TRAINING environment — as recorded in the Phase 01 run artefact

`results/01_baseline_berturk/run_config.json` → `environment`:

```json
"environment": {
  "torch": "2.11.0+cu128",
  "cuda_available": true,
  "device_name": "NVIDIA L4",
  "transformers": "5.15.0",
  "scikit_learn": "1.6.1"
}
```

| Library | Logged version |
|---|---|
| torch | **2.11.0+cu128** |
| transformers | **5.15.0** |
| scikit-learn | **1.6.1** |
| **Python** | **NOT RECORDED** |

The run logged exactly three library versions. **Python version is NOT RECORDED** in the
Phase 01 artefact — no `python_version` key exists in `run_config.json` or `metrics.json`.
(For contrast, the *later* `results/04_calibration/cal_eval_split.json` does record
`"python_version": "3.14.0"` — but that is the 2026-08-18 local regeneration of the split
file, **not** the 2026-08-15 Colab training run. Do not cite it as the training Python.)

`results/05_final_test/metrics.json` records the identical `environment` block, so the test
pass ran on the same stack.

## 8b-ADD. INFERENCE/demo environment

**`requirements.txt`, verbatim:**

```
# Versions phase 01 actually resolved to on Colab, 2026-08-15 (recorded in
# results/01_baseline_berturk/run_config.json): torch 2.11.0+cu128,
# transformers 5.15.0, scikit-learn 1.6.1, on an NVIDIA L4.
# The floors below are what the code needs; the runbook pins transformers
# exactly and asserts torch/scikit-learn, so a later phase cannot silently
# land on a different major without it showing up in the log.

# --- Offline demo runtime (demo/app.py, demo/build_assets.py) ---
# These two are the entire third-party dependency set for the demo path,
# confirmed by AST walk of demo/app.py, demo/build_assets.py and
# src/lexicon.py. Everything else below is training/analysis only.
# Verified working 2026-08-20 on Python 3.14 (.venv) with stable PyPI
# wheels: torch 2.13.0+cpu, transformers 5.15.1. No source build required.
# NOTE: this is NOT the phase-01 environment recorded above. The demo
# loads a frozen state_dict and runs forward passes only.
transformers>=4.40
torch>=2.2

# --- Training and analysis only; not needed to run the demo ---
datasets>=2.19
scikit-learn>=1.4
numpy>=1.26
pandas>=2.2
python-dotenv>=1.0
pytest>=8.0

# gradio was removed 2026-08-20: demo/README.md argues against Gradio and
# Streamlit by name because both fetch web fonts and telemetry from CDNs,
# which breaks the offline guarantee. Pinning it contradicted that.
```

**Versions actually resolved in `.venv` (Python 3.14.0):**

| Package | Pinned floor | Resolved in `.venv` |
|---|---|---|
| torch | `>=2.2` | **2.13.0** |
| transformers | `>=4.40` | **5.15.1** |
| scikit-learn | `>=1.4` | **1.9.0** |
| numpy | `>=1.26` | **2.5.2** |
| pytest | `>=8.0` | **9.1.1** |
| **datasets** | `>=2.19` | **ABSENT from .venv** |
| **pandas** | `>=2.2` | **ABSENT from .venv** |
| **python-dotenv** | `>=1.0` | **ABSENT from .venv** |

Also present (transitive): tokenizers 0.22.2, safetensors 0.8.0, huggingface_hub 1.28.0,
scipy 1.18.0, regex 2026.7.19, tqdm 4.70.0, PyYAML 6.0.3, Jinja2 3.1.6, sympy 1.14.0,
networkx 3.6.1, filelock 3.32.3, rich 15.0.0, typer 0.27.1.

**Finding:** three packages `requirements.txt` declares are **not installed** in `.venv`.
They sit under the "training and analysis only" heading, so the demo path is unaffected and
the 415 passing tests do not touch them — but `pip install -r requirements.txt` into this
venv has not been run to completion, and any analysis script importing `pandas` or
`datasets` would fail here.

## 8c-ADD. Training hardware — **LOGGED, not inferred**

```json
"env": "colab",
"cuda_available": true,
"device_name": "NVIDIA L4"
```

- **Accelerator type: NVIDIA L4** — read from `run_config.json`, **logged**.
- **Count: NOT RECORDED.** The artefact records a single `device_name` string and no device
  count. One L4 is the natural reading of a single Colab session, but the artefact does not
  state a count, so I am not reporting one.
- Environment: `"env": "colab"`; paths confirm `/content/nsosyal-bstar` with checkpoints on
  Google Drive.
- Run window: `started_at 2026-08-15T16:12:34` → `finished_at 2026-08-15T16:18:18`.

## 8d-ADD. Inference hardware — **CPU-only is supported; no GPU required**

From `demo/app.py:372`:

```python
device = "cuda" if torch.cuda.is_available() else "cpu"
```

The demo selects CUDA when present and **falls back to CPU**; nothing requires an
accelerator. `demo/README.md` confirms it from the other side:

- line 50: *"2.13.0+cpu, transformers 5.15.1, no source build."*
- line 52: *"building the bundle needs no GPU and no compute"*
- line 149–150: *"**CPU works but is slow to load.** ~885 MB of fp32 weights take a while to
  read from disk; on CUDA it is a few seconds. The demo picks CUDA if available."*

So: **CPU-only runs, with a load-time penalty.** The demo loads a frozen `state_dict` and
runs forward passes only.

---

# 9. TRAINING CONFIGURATION — Phase 01, from the run record

Source: `results/01_baseline_berturk/run_config.json` → `hyperparams`, plus
`metrics.json` → `training_history`.

| Setting | Logged value |
|---|---|
| epochs run | **3** — and all three actually ran (`training_history` has entries for epochs 1, 2, 3) |
| batch size | **32** |
| learning rate | **2e-05** |
| **optimizer** | **NOT RECORDED** |
| **scheduler** | **NOT RECORDED** (type not logged) |
| warmup | **`warmup_ratio: 0.1`** — recorded |
| max sequence length | **128** (`max_len`) |
| weight decay | **0.01** |
| **gradient accumulation** | **NOT RECORDED** |
| mixed precision | **`fp16: true`** |
| random seed | **42** |
| threshold | 0.5 |
| class weighting | **`null`** — explicitly recorded as absent |

**Total wall-clock training time: NOT RECORDED as a single value.** What *is* recorded:

- per-epoch seconds in `training_history`: **91.4 / 91.8 / 91.4** s
- whole-run window: `started_at 16:12:34` → `finished_at 16:18:18` = **5 min 44 s**

The 5m44s covers the entire run (load, train, evaluate, bootstrap, write), not training
alone. Summing the three epoch timings would give 274.6 s, but that sum is my arithmetic,
not a recorded field — treat it as such.

**Early stopping: NOT USED, and no early-stopping criterion is recorded.** No such key
exists in `hyperparams`. All three configured epochs completed, which is itself
inconsistent with early stopping having fired. Checkpoint choice was made *after* training,
by selection rather than by stopping — see §10.

---

# 10. CHECKPOINT SELECTION

## 10a. Which checkpoint, and on what criterion

**`best.pt` = epoch 1.** Criterion: **best dev macro-F1**. `metrics.json` → `checkpoint_tie`:

> *"Epochs 1 and 3 tie at macro-F1 0.8270752670616224 with identical confusion matrices,
> but are different models: they disagree on 198/4764 dev rows (43 gold-OFF flips each way,
> 56 gold-NOT each way). Reported numbers and `dev_predictions.csv` come from best.pt =
> epoch 1."*

The tie-break — earliest epoch wins — is **implicit**. The artefact records *that* epoch 1
was taken, and that the two are genuinely different models, but does not state a
pre-registered tie-breaking rule. That is worth a sentence in the report rather than a
claim of a principled rule.

## 10b. Per-epoch validation trace — **RECORDED**

```json
"training_history": [
  {"epoch": 1, "train_loss": 0.3466165497969677,  "dev_macro_f1": 0.8270752670616224, "seconds": 91.4},
  {"epoch": 2, "train_loss": 0.21298542834147458, "dev_macro_f1": 0.8246369676730552, "seconds": 91.8},
  {"epoch": 3, "train_loss": 0.1359960284631399,  "dev_macro_f1": 0.8270752670616224, "seconds": 91.4}
]
```

Train loss falls monotonically (0.347 → 0.213 → 0.136) while dev macro-F1 does not improve
— it dips at epoch 2 and returns to exactly the epoch-1 value at epoch 3. That is the
overfitting-control story the report wants, and it is fully in the artefact.

## 10c. "Selected checkpoint is epoch 1" — **CONFIRMED**

Confirmed from `metrics.json` → `checkpoint_tie`, quoted above: *"Reported numbers and
dev_predictions.csv come from best.pt = epoch 1."* The project record is correct.

## 10d. Other overfitting controls — what the record shows, including absences

| Control | Recorded value |
|---|---|
| weight decay | **0.01** — present |
| warmup ratio | **0.1** — present |
| epochs capped at 3 | present (a de-facto control) |
| **dropout override** | **NOT RECORDED** — no key; model default assumed but not logged |
| **class weighting** | **`null`** — explicitly recorded as *not used* |
| **label smoothing** | **NOT RECORDED** — no key anywhere in the artefact |
| **early stopping** | **NOT RECORDED / not used** (§9) |

So the honest list is: weight decay 0.01, warmup 0.1, a 3-epoch cap, and post-hoc
checkpoint selection on dev macro-F1. Class weighting was deliberately off. Dropout and
label smoothing cannot be claimed either way — they are absent from the record.

---

# 11. DATA PREPROCESSING

## 11a. Steps applied before tokenisation, in order — **effectively none**

**File: `src/models.py`, function `encode()` (line 92).** This is the only thing between a
corpus row and the tokeniser:

```python
def encode(rows, tokenizer, max_len, with_labels=True):
    """Tokenise WITHOUT padding -- padding happens per batch in the collator, so
    a batch of short tweets does not pay for a 128-token pad."""
    enc = tokenizer(
        [r["text"] for r in rows],
        truncation=True,
        max_length=max_len,
        padding=False,
    )
```

In order: **(1)** read the row's `text` field verbatim → **(2)** HF tokenizer with
`truncation=True`, `max_length=128` → **(3)** `padding=False`, padding deferred to the
per-batch collator (`_make_loader`, line 110, via `tokenizer.pad`).

**No lowercasing, no normalisation, no stripping, no cleaning is applied to model input.**
The raw text goes straight to the tokeniser — which is correct for a **cased** checkpoint.

The only text handling anywhere upstream is in the TSV reader
(`src/data_io.py:read_offenseval_tsv`, line 49) and it is corpus-format repair, not
preprocessing: a tweet containing a literal tab has its middle fields rejoined with tabs
(`"text": "\t".join(parts[1:-1])`) rather than being dropped. The corpus itself already had
embedded newlines replaced by three spaces upstream (documented at `src/data_io.py:13`).

## 11b. Turkish-specific handling — **exists, but NOT on the model path**

`src/lexicon.py` lines 23–29:

```python
def tr_lower(s):
    """Turkish-aware lowercasing: I -> ı and İ -> i, before the normal lower().

    Python's str.lower() maps I -> i, which is correct for English and wrong
    """
    return s.replace("I", "ı").replace("İ", "i").lower()
```

- **Casing rule:** Turkish-aware lowercasing, dotted/dotless `i` handled explicitly —
  `I → ı`, `İ → i`, then `.lower()`.
- **Where it applies:** lexicon loading (`load_lexicon`, line 44) and slice tokenisation
  (`tokens()`, line 69, `re.findall(r"\w+", tr_lower(text))`).
- **Where it does NOT apply: the model.** The classifier receives raw cased text. `tr_lower`
  governs *slice assignment* (`lexicon_hit` vs `lexicon_free`) only.

This distinction matters for §3.2: the report must not say the text was lowercased before
training — it was not, and it would be wrong to, given `bert-base-turkish-**cased**`.

Other normalisation recorded in the same module: `SKIP = {"@user", "url"}` (line 61),
`MIN_ROOT_LEN = 3` (line 65), a censored-profanity pattern (line 102) and
`ABBREV_PROFANITY = {"aq", "mk", "amk", "oç", "sg", "sik", "siktir"}` (line 106). A known
quirk is preserved deliberately and documented at lines 54–57 (`\w+` strips `@` from
`@user`).

## 11c. Row filtering / deduplication — **none applied; 0 rows removed**

No deduplication exists anywhere in the load path. The only row-dropping rule is a
malformed-line guard in `read_offenseval_tsv`:

```python
if len(parts) < 3:
    print(f"  [warn] line {ln}: only {len(parts)} field(s) -- skipped")
    continue
```

**It removed nothing on this corpus**, which the recorded counts confirm arithmetically:
`day1_report.json` `n_rows = 31756`, and the split records `train 26992 + dev 4764 = 31756`.
Every corpus row survives into the split. **0 rows removed.**

## 11d. Label mapping, verbatim

`src/models.py` lines 38–39 — the training mapping:

```python
LABEL2ID = {"NOT": 0, "OFF": 1}
ID2LABEL = {0: "NOT", 1: "OFF"}
```

Used at line 105 (`item["labels"] = LABEL2ID[rows[i]["label"]]`), at lines 146–147 (passed
to the model config) and at line 176, where the reported score is
`torch.softmax(logits, dim=-1)[:, LABEL2ID["OFF"]]` — i.e. **`confidence` is P(OFF), not
max-class probability**. `cal_eval_split.json` independently confirms this:
`"score_meaning": "P(OFF), not max-class probability"`.

`src/data_io.py` lines 110–121 — the cross-corpus mapping (Mayda/Beyhan, never trained on):

```python
VALID_BINARY_LABELS = {"OFF", "NOT"}

LABEL_MAP_3TO2 = {
    "hate": "OFF",
    "offensive": "OFF",
    "none": "NOT",
}
```

`map_3way_to_binary` (line 123) normalises with `str(label).strip().lower()` and raises on
an unknown label rather than guessing (line 131).

---

# 12. SPLIT AND CLASS BALANCE

## 12a. Split ratio, seed, dev fingerprint

From `results/01_baseline_berturk/run_config.json` → `split`:

| Field | Value |
|---|---|
| `dev_fraction` | **0.15** (85/15 train/dev) |
| `seed` | **42** |
| `reused_existing_file` | `true` |
| `matches_regeneration` | `true` |
| **dev fingerprint** | **`034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4`** |

Short form `034415af3a23b388` is used as the gate value in phases 04, 11 and 12. The split
is stratified on the gold label — `src.data_io.stratified_split`, described in
`cal_eval_split.json` as *"sort by id, then random.Random(seed).shuffle, stratified on gold
label only"*. The split file `data/splits/split_seed42.json` (815,066 B) is committed by
explicit `.gitignore` exception.

## 12b. Row counts

| Split | Rows | Source |
|---|---|---|
| train | **26,992** (NOT 21,781 / OFF 5,211) | `run_config.json` → `split.counts.train` |
| dev | **4,764** (NOT 3,844 / OFF 920) | `run_config.json` → `split.counts.dev` |
| official test | **3,528** | `results/05_final_test/metrics.json` → `n_test` |
| *(train + dev)* | *31,756* | matches `day1_report.json` `n_rows` |

## 12c. Class balance and per-slice base rates

From `results/08_lexical_analysis/token_stats.json` → `class_balance` (train split is C8-1
scope; dev recorded alongside):

**TRAIN (n = 26,992)**

| Group | n | OFF | NOT | off_rate | OFF:NOT ratio |
|---|---:|---:|---:|---:|---:|
| overall | 26,992 | 5,211 | 21,781 | **0.193057** | 0.2392 |
| `lexicon_hit` | 3,404 | 1,884 | 1,520 | **0.553467** | 1.2395 |
| `lexicon_free` | 23,588 | 3,327 | 20,261 | **0.141046** | 0.1642 |

**DEV (n = 4,764)**

| Group | n | OFF | NOT | off_rate |
|---|---:|---:|---:|---:|
| overall | 4,764 | 920 | 3,844 | **0.193115** |
| `lexicon_hit` | 614 | 355 | 259 | **0.5781758957654723** |
| `lexicon_free` | 4,150 | 565 | 3,585 | **0.13614457831325302** |

Dev slice base rates cross-checked against `01/metrics.json` (`base_rate_off` fields) and
`09/stage_1/stage1_auc.json` (`base_rate`) — all three agree.

`base_rate.p_off_train_computed = 0.193057`, with `advisor_stated: 0.193`, `agrees: true`.

## 12d. CAL/EVAL halving of dev (phase 04)

From `results/04_calibration/cal_eval_split.json`:

| Field | Value |
|---|---|
| `n_dev` | 4,764 |
| `n_cal` | **2,382** |
| `n_eval` | **2,382** |
| `seed` | **42** |
| `dev_fingerprint` | `034415af3a23b388…a133b4` |
| `reproduction_checks_all_pass` | `true` (4 checks) |

**Stratified: yes — on the gold label only.** `id_order` records: *"as returned by
`src.data_io.stratified_split` (sort by id, then `random.Random(seed).shuffle`, stratified
on gold label only)"*. **It is not stratified by slice**, which is why the four slice×gold
EVAL cells come out uneven (182 / 127 / 278 / 1795, per `11/metrics.json` and
`12/c12_16_intervals.json`) and why later phases stratify their bootstraps over those cells
explicitly.

The file is a frozen row-id list (C11-2), regenerated by calling the source function
unmodified; it is *"insurance, not measurement: this file produces no number and licenses no
claim."* Threshold recorded: `0.663171`, from
`calibration.json → raw.operating_points.high_automation.threshold`.

---

# 13. REPOSITORY AND PROCESS EVIDENCE

## 13a. Remote URL, privacy

```
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (fetch)
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (push)
```

Local branch `master` tracks `origin/master` and is **level with it** (`git branch -vv`
shows `[origin/master]` with no ahead/behind marker).

**Privacy NOT VERIFIABLE offline** — see §8a. Nothing in the repository asserts the
visibility setting either way.

## 13b. Public mirror — **DOES NOT EXIST**

One remote only; no mirror remote, no mirror reference in any tracked file. The report
should state the link as **pending** rather than print a URL whose resolution I could not
confirm.

## 13c. Commit count, dates, ahead/behind

- **67 commits** on `master`.
- First: `c33d1bd` **2026-08-15 14:32:05 +0300**.
- Most recent: `e0ce657` **2026-08-20 01:25:47 +0300**.
- **Local `master` is not ahead of `origin/master`** — they are level.

*(Caveat: "level" is read from the local remote-tracking ref. Without a `git fetch` — a
network call I did not make — this reflects the last known state of `origin`, not a live
check.)*

## 13d. Test suite — **415 passed, 1 failed**

Run just now, not quoted from a previous report. Executed with
`PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider` so the run created no files:

```
$ .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q

FAILED tests/test_demo.py::test_render_result_escapes_html - KeyError: 'opera...
1 failed, 415 passed in 17.37s
```

**Total: 416 tests. 415 pass, 1 fails.** The failure, in full:

```
    def render_result(res):
        if not res["ok"]:
            return f"<p class='notes'>{html.escape(' / '.join(res['notes']))}</p>"

        sel = res["selective"]
>       op = STATE["operating_point"]
             ^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'operating_point'

demo\app.py:223: KeyError
```

`demo/app.py:223` reads `STATE["operating_point"]`, a key the test's fixture `STATE` does
not define. This is a **live failure in the demo path at HEAD**, on the most recent commit
(`e0ce657`, "demo: withhold model label at deferral; accessibility fixes"). Reporting it,
not fixing it. Any 3.1 sentence claiming a green suite is currently false.

## 13e. `results/` inventory — 38 committed artefacts

| Phase directory | Files |
|---|---|
| `results/01_baseline_berturk/` | `classification_report.txt` (2,005), `dev_predictions.csv` (736,591 — **gitignored**), `metrics.json` (5,524), `results_log_row.md` (1,900), `run_config.json` (2,330) |
| `results/02_failure_analysis/` | `findings.md` (12,180), `fn_tags.json` (4,372), `fp_function_tags.json` (6,136), `slice_sensitivity.json` (2,406) |
| `results/03_defense/` | `augmentation_review.json` (1,023), `comparison.json` (4,543), `findings.md` (8,255), `run_1a/metrics.json` (3,825), `run_1a1b/metrics.json` (3,832), `run_1a1b_d/metrics.json` (3,840), `run_raw/metrics.json` (3,271), `train_oof_summary.json` (1,111) |
| `results/04_calibration/` | `cal_eval_split.json` (69,676), `calibration.json` (46,790), `findings.md` (10,932) |
| `results/05_final_test/` | `findings.md` (8,740), `metrics.json` (20,114), `paired_deltas.json` (1,189), `raw_output.txt` (7,464), `TEST_SET_OPENED.json` (176), `TEST_SET_SPENT.json` (901) |
| `results/08_lexical_analysis/` | `findings.md` (17,982), `token_stats.json` (89,324) |
| `results/09_deeper_analysis/` | `stage_1/findings.md` (15,335), `stage_1/stage1_auc.json` (6,159), `stage_1b/findings.md` (8,354), `stage_1b/stage1b_defense_auc.json` (4,203) |
| `results/11_prior_correction/` | `metrics.json` (33,578) |
| `results/12_threshold_policy/` | `c12_16_intervals.json` (11,663), `metrics.json` (52,195) |
| `results/15_deixis/` | `cell_counts.json` (44,256) |
| `results/` (root) | `day1_report.json` (671), `day1_report_rerun.json` (686) |

**Phases with committed artefacts: 01, 02, 03, 04, 05, 08, 09, 11, 12, 15** (plus the two
day-1 reports). **Phases 06, 07, 10, 13, 14 have no `results/` directory** — consistent with
06/07/10 being documentation phases; 13 and 14 have neither a `phases/` file nor a
`results/` directory.

## 13f. Gitignored analysis inputs — absent from a fresh clone

Confirmed with `git status --porcelain --ignored`:

| Path | Size | Ignored by |
|---|---:|---|
| `data/coltekin/offenseval-tr-training-v1.tsv` | **4,101,728** | `.gitignore:12` `data/**` |
| `data/coltekin/offenseval-tr-testset-v1.tsv` | **449,553** | `data/**` |
| `data/coltekin/offenseval-tr-labela-v1.tsv` | **35,280** | `data/**` |
| `data/coltekin/readme-trainingset-tr.txt` | 1,339 | `data/**` |
| `data/coltekin/offenseval-annotation.txt` | 434 | `data/**` |
| **`data/lexicon/karaliste.txt`** | **5,988** | `data/**` |
| **`results/01_baseline_berturk/dev_predictions.csv`** | **736,591** | `.gitignore` `results/**/*predictions*.csv` |

Committed by explicit exception (so **present** in a fresh clone):
`data/splits/split_seed42.json` (815,066) and `data/deixis/address_tokens.json` (3,443).

**Consequence for 3.1 and for §15:** a fresh clone cannot reproduce any analysis that reads
the corpus, the lexicon, or per-row dev scores. The exclusions are deliberate and reasoned
in `.gitignore` (licensing, size, corpus text) — but they are real, and the per-row score
dump being absent is what blocks two of the three figures in §15a.

---

# 14. OPERATING POINTS AND SELECTIVE PREDICTION

## 14a. From `results/04_calibration/calibration.json` (variant `raw`)

**Fitted temperature:**

```json
"temperature_fit": {
  "temperature": 0.9948165193869881,
  "nll_before": 0.26164312590326666,
  "nll_after": 0.26163936785454145,
  "n_fit": 2382,
  "grid_best": 1.0,
  "search_lo": 0.05, "search_hi": 20.0, "at_boundary": false
}
```

Temperature **0.9948165193869881** — essentially 1.0, i.e. the raw model needed no
meaningful temperature correction. NLL barely moves (0.261643 → 0.261639).

**ECE at 15 bins, before and after:**

| | ECE | MCE | signed_gap | n |
|---|---|---|---|---|
| **before** | **0.02053844164567604** | 0.11843494594594595 | −0.009073424013434063 | 2,382 |
| **after** | **0.019074118554954684** | 0.12295188508860555 | −0.009663465409712938 | 2,382 |

(ECE at 10 and 20 bins is also recorded: before 0.01618815 / 0.02061165, after 0.01540523 /
0.02112985. Note ECE *rises* after calibration at 20 bins, and MCE rises at 15 — the
"improvement" is marginal and bin-count-dependent.)

**Operating points (thresholds selected on CAL, metrics measured on EVAL):**

| Point | threshold | rule |
|---|---|---|
| `high_automation` | **0.663171** | *"fixed at 90% coverage, declared in advance"* (`target_coverage: 0.9`) |
| `high_precision` | **0.80091** | *"largest grid coverage whose CAL error rate <= 5.0%"* |

`high_automation` on EVAL: coverage 0.9118387909319899, macro-F1 0.8504158585200146,
error_rate 0.07918968692449356, n_auto 2172, n_deferred 210, capture_lift 3.780952380952381.
`high_precision` on EVAL: coverage 0.8161209068010076, macro-F1 0.8755804766152671,
error_rate 0.058127572016460904, n_auto 1944, n_deferred 438, capture_lift 3.056440479983009.

## 14b. Dev risk–coverage curve, as recorded

`raw.risk_coverage`, 11 points over `coverage_grid = [1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7,
0.65, 0.6, 0.55, 0.5]`. First eight, verbatim:

| target | coverage | macro-F1 | error_rate | n_auto | n_deferred | threshold |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00 | 1.0 | 0.8270752670616224 | 0.10453400503778337 | 4,764 | 0 | 0.501639 |
| 0.95 | 0.9500419815281276 | 0.8466512411102995 | 0.08793636765355722 | 4,526 | 238 | — |
| 0.90 | 0.9000839630562553 | 0.8620662641989312 | 0.07392723880597014 | 4,288 | 476 | — |
| 0.85 | 0.8499160369437447 | 0.8713554960126241 | 0.06446036058285996 | 4,049 | 715 | — |
| 0.80 | 0.7999580184718724 | 0.8927359763054825 | 0.05116767252689583 | 3,811 | 953 | — |
| 0.75 | 0.75 | 0.9070245017381062 | 0.04086202071088721 | 3,573 | 1,191 | 0.855162 |
| 0.70 | 0.7000419815281276 | 0.9222405579843842 | 0.032083958020989505 | 3,335 | 1,429 | — |
| 0.65 | 0.6500839630562553 | 0.925165415413838 | 0.02970616725863739 | 3,097 | 1,667 | — |

At coverage 1.0 macro-F1 is 0.8270752670616224 — identical to the §4 baseline, as it must be.

## 14c. Phase 05 test artefact — `systems.raw.selective.high_automation`

| Quantity | Test value |
|---|---|
| threshold | **0.663171** (unchanged from dev) |
| **achieved coverage** | **0.9016439909297053** (CI 0.8925736961451247 – 0.9115646258503401) |
| **macro-F1** | **0.8485489582207839** (CI 0.8319970237545736 – 0.8653421645829655) |
| **error rate** | **0.08519333542911034** (CI 0.07523233983161494 – 0.09436328104603463) |
| **deferred fraction** | **347 / 3,528 = 0.0983560090702947** (`n_auto` 3,181, `n_deferred` 347) |
| **error-capture lift** | **3.5912595516978123** (`error_capture_share` 0.3532219570405728) |
| deferred_error_rate | 0.4265129682997118 |

**Thresholds carried from dev without re-derivation — CONFIRMED, three ways:**

1. `"thresholds_re_derived_on_test": false` (top level).
2. `systems.raw.selective.high_automation.threshold_provenance` = **"phase 04, selected on
   the dev CAL half"**.
3. `thresholds.source` = `.../results/04_calibration/calibration.json`, carrying
   `dev_fingerprint 034415af3a23b388…a133b4` — the same fingerprint recorded in phase 01.

Also recorded: `official_test_set_touched: true`, `single_pass: true`, and the corpus
digests (`test_sha256 9052784e…`, `gold_sha256 ae9b0837…`).

For `high_precision` on test: coverage 0.7981859410430839, macro-F1 0.8900293962474798,
error_rate 0.05433238636363636, n_deferred 712, capture_lift 3.1456919900244027.

## 14d. Per-slice deferral rates — dev and test

**`high_automation` (threshold 0.663171):**

| Split / source | `lexicon_hit` | `lexicon_free` |
|---|---:|---:|
| dev, **EVAL half** (`operating_points`) | **0.07119741100323625** (22/309) | **0.09068982151471297** (188/2,073) |
| dev, **full dev** (`deferral_full_dev`) | **0.09609120521172639** (59/614) | **0.09373493975903614** (389/4,150) |
| **test** (`systems.raw.selective`) | **0.09979633401221996** (49/491) | **0.09812314784326638** (298/3,037) |

**`high_precision` (threshold 0.80091), test:**

| | `lexicon_hit` | `lexicon_free` |
|---|---:|---:|
| test | **0.1955193482688391** (96/491) | **0.20283174185051037** (616/3,037) |

**This is the "deferral is slice-blind" result, and it holds on test.** On the full dev set
the two rates are 0.0961 vs 0.0937 and on test 0.0998 vs 0.0981 — a gap of well under half a
percentage point, against a recall gap of 33–40 points. The one place the rates diverge
noticeably (EVAL half: 0.0712 vs 0.0907) is the smaller n=309 `lexicon_hit` cell.

**Two cautions for section 4.1.** First, `by_slice` uses the key `share_of_dev` even inside
the **test** artefact — a copied field name, not a dev figure; do not read those rows as dev
values. Second, dev EVAL-half and full-dev deferral rates differ enough
(`lexicon_hit` 0.0712 vs 0.0961) that the report must say which one it is quoting.

---

# 15. FIGURE READINESS

## 15a. What is actually plottable from recorded artefacts

| Figure | Status | Path |
|---|---|---|
| **Risk–coverage curve** | **READY** — 11 full points | `results/04_calibration/calibration.json` → `variants.raw.risk_coverage` (coverage, macro_f1, error_rate, n_auto, n_deferred, off_recall, off_precision, threshold per point) |
| **Score distribution by slice** | **NOT PLOTTABLE from committed artefacts** | `results/09_deeper_analysis/stage_1/stage1_auc.json` → `score_distributions` holds **summary statistics only** — `n`, `mean`, `q1`, `median`, `q3`, `share_below_0.5` per slice×gold. No score arrays. |
| **ROC curves per slice** | **NOT PLOTTABLE from committed artefacts** | Same file records `auc_lexicon_hit`/`auc_lexicon_free` + CIs, but **no `fpr`/`tpr`/curve arrays** — `grep -oE '"(fpr\|tpr\|roc_curve\|curve\|y_score\|scores)"'` returns nothing. |

The raw per-row scores needed for both missing figures exist in exactly one place:

```
results/01_baseline_berturk/dev_predictions.csv   736,591 bytes
row_id,text,gold,pred,confidence,slice
```

— with `confidence` = P(OFF) — **but that file is gitignored** (`results/**/*predictions*.csv`,
§13f) and absent from a fresh clone. Its integrity is pinned
(sha256 `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346`, 736,591 bytes,
verified `pass: true` in `12/c12_16_intervals.json`), so the local copy is the right one —
but plotting from it means reading an untracked file.

**Net:** one of the three figures can be drawn from committed evidence alone; the other two
require the untracked prediction dump. Summary quartiles could support a box-plot of the
score distribution without raw scores, but not a histogram or density, and nothing supports
an ROC curve.

## 15b. matplotlib in `.venv` — **NOT IMPORTABLE**

```
$ .venv/Scripts/python.exe -c "import matplotlib; print(matplotlib.__version__)"
ModuleNotFoundError: No module named 'matplotlib'
```

Not installed, and **not listed in `requirements.txt`** either. Plotting would need an
install first. Nothing was plotted and nothing was installed.

---

# SUMMARY OF MISMATCHES AND ABSENCES

Returned as corrections to the writing conversation. Nothing here was fixed.

| # | Item | Finding |
|---|---|---|
| 1 | **Interval uniformity** | **MISMATCH.** Replicate counts differ (**1000** phases 01–05 vs **10000** phases 08/09/11/12); three distinct resampling methods (independent / stratified / paired); no method string at all in 04, 08, 12-`metrics.json`, 09-stage_1b; alpha absent from 4 artefacts. Level is 0.05 wherever recorded, and no other level exists. **The blanket "%95 önyükleme güven aralığı" sentence is not supported as written.** |
| 5b | **Correction row count** | **MISMATCH.** Report says **FIVE**; `docs/RESULTS_LOG.md` now holds **SEVEN** correction-type rows (6 `CORRECTION` + 1 `SPEC DEFECT`). The "five" matches `PROJECT_HISTORY.md` §5, which was written 2026-08-17; two more rows were appended 2026-08-19 and PROJECT_HISTORY was never updated. The "one records a defect in a specification" part is correct (C4 / line 43). |
| 6 | **Counterfactual terminology** | **NOT FOUND.** Zero occurrences of `ters olgusal`, `karşı olgusal`, or **any** rendering — including bare `olgusal` and English `counterfactual` — in all four report files. The four files do not disagree; the term is simply absent. |
| 7c | **Lexicon licence** | **DOES NOT EXIST.** No licence file anywhere in the repo; no `CC BY-SA` string anywhere. The report's "CC BY-SA 4.0" has no source in this repository. |
| 7d | **Upstream dates** | **NOT RECORDED.** Upstream first-commit, latest-commit and clone dates are all absent. `phase_briefing.md:124` required this record; it was never made. |
| 7a | **Lexicon entry count** | **PASS with caveat.** 695 = casefold-unique and matches every recorded value, but the file has **698** non-blank lines and **696** exact-unique. "695 entries" is right; "695 lines" would be wrong. |
| 3k | **ROC-AUC lexicon_free** | **PASS with caveat.** Recorded `0.89615` sits exactly on the 4-dp midpoint; `0,8962` is a rounding-convention choice, not a direct read. |
| 3b, 3e | **Percentages** | **NOT RECORDED as fields.** Only the integer components are stored. Both are consistent with the report's figures and with the `/31756` denominator. |
| 3l–3o | **Phase 12 scope** | **PASS on values; scope caveat.** Computed on the **EVAL half (n=2382)**, not full dev (n=4764). The artefact's own `ordering_disclosure` states the intervals were computed **after** the point estimates were published — *"estimation after the fact, not pre-registration."* |
| 4 | **0,8271** | **PASS**, but it is a **dev-set** macro-F1. Published OffensEval-TR figures are test-set. Comparing them compares different splits. |
| 13d | **Test suite** | **1 FAILING TEST** at HEAD: `tests/test_demo.py::test_render_result_escapes_html` — `KeyError: 'operating_point'` at `demo/app.py:223`. 415 pass. Any claim of a green suite is currently false. |
| 8b-ADD | **requirements.txt vs .venv** | `datasets`, `pandas`, `python-dotenv` are declared but **absent from `.venv`**. Demo path and the test suite are unaffected. |
| 8a-ADD | **Training Python version** | **NOT RECORDED** in the Phase 01 artefact. (`cal_eval_split.json`'s `python_version: 3.14.0` is the 2026-08-18 local regeneration, not the training run — do not cite it.) |
| 9 | **Training config gaps** | **NOT RECORDED:** optimizer, scheduler type, gradient accumulation, total wall-clock training time (only per-epoch seconds + a whole-run window). Early stopping not used. |
| 10d | **Overfitting controls** | Dropout override and label smoothing **NOT RECORDED**; class weighting explicitly `null`. Only weight decay 0.01, warmup 0.1, 3-epoch cap and post-hoc checkpoint selection can be claimed. |
| 10a | **Tie-break rule** | Epoch 1 confirmed, but epochs 1 and 3 **tie exactly** on macro-F1 with identical confusion matrices while disagreeing on 198/4764 rows. The earliest-epoch tie-break is **implicit**, not a recorded rule. |
| 8a / 13a-b | **Repo privacy** | **NOT VERIFIABLE** from a read-only local sweep. No public mirror exists locally and none is referenced. Report the link as **pending**, as planned. |
| 15 | **Figure readiness** | Risk–coverage curve is ready. **Score distributions and ROC curves cannot be plotted** from committed artefacts — only summary quartiles and AUC scalars are recorded; raw scores live in the **gitignored** `dev_predictions.csv`. **matplotlib is not installed** in `.venv` and is not in `requirements.txt`. |
| — | **Working tree changed** | `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` is now **staged** (`A`) at the repo root. It was not staged when this sweep began and I did not stage it. HEAD unchanged at `e0ce657`. Left as found. |

**Items passing clean:** 2 (model identifier), 3a/3c/3d/3f/3g/3h/3i/3j/3l/3m/3n/3o (figures),
5a (six pre-registrations, all predating their results), 5c (append-only confirmed, the one
50/50 commit is pure EOL renormalisation with identical content digests), 5d (guard tracked
and implemented in `src/data_io.py`), 7b (lexicon sha256 matches four recorded copies),
8b/8c/8d (67 commits, genuine incremental history, structure), 11 (preprocessing, casing,
no filtering, label maps), 12 (splits and balances), 14 (calibration, operating points,
risk–coverage, slice-blind deferral confirmed on test).
