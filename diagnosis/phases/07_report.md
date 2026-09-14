# Phase 07 — technical report: outline and evidence map

Opened 16 Aug 2026. Due **24 Aug 2026, 17:00 TSİ**. Carries 35% Teknik Yeterlilik.
Language: Turkish.

## Template status

**The KYS rapor şablonu is NOT in this repository.** Verified: no file matching
`sablon|şablon|kys|rapor|template` among the 74 tracked files; `docs/` holds only
the master brief, handoff, setup prompt, phase briefing and results log; no
PDF/DOCX/ODT/RTF anywhere in the tree; nothing ever added under such a name in
git history.

**The section numbering below is therefore provisional and is derived from our
own evidence, not from a guessed template.** When the şablon arrives, this map
gets re-cut against its real headings. Nothing is drafted until then. What does
*not* change is the evidence inventory in the right-hand column — that is fixed
by what we measured.

The one structural constraint that is genuinely binding comes from
`docs/phase_briefing.md` §8 (the comparison matrix) and §9 (eight required
outputs); both are tracked below.

---

## Evidence inventory (everything we can cite)

| # | Source | Holds |
|---|---|---|
| E1 | `results/day1_report.json`, `day1_report_rerun.json` | Day 1 gate: 3,892 / 6,131 OFF (63%) evade the frozen filter; corpus + lexicon sha256; 16/16 fields reproduce |
| E2 | `results/01_baseline_berturk/metrics.json` | keyword filter and BERTurk on dev, all CIs, per-slice confusion, split identity |
| E3 | `phases/01_baseline_diagnosis.md` | pre-registered three-way decision rule + power basis; OFF-recall-only constraint |
| E4 | `results/02_failure_analysis/findings.md` + 3 JSONs | annotation-noise correction, FP function taxonomy, slice sensitivity, checkpoint stability |
| E5 | `phases/03_defense_design.md` | constraints C1–C4, D/H disjointness |
| E6 | `results/03_defense/augmentation_review.json` | 1a yield 382/5,211 (7%), skip reasons, three defects caught by reading |
| E7 | `results/03_defense/findings.md`, `comparison.json` | four attributable runs, paired deltas, H-perturbed dev column |
| E8 | `phases/04_calibration.md` | pre-registered C4-1…C4-8 |
| E9 | `results/04_calibration/calibration.json` + `findings.md` | temperature, ECE, reliability bins, risk–coverage, 2 operating points, deferral by slice |
| E10 | `results/05_final_test/metrics.json`, `paired_deltas.json`, `findings.md`, `raw_output.txt` | the single-pass official test numbers |
| E11 | `results/05_final_test/TEST_SET_{OPENED,SPENT}.json` | single-use accounting, both opens |
| E12 | `demo/README.md`, `app.py`, `examples.json` | offline demo, 885.9 MB bundle, verification record |
| E13 | `docs/RESULTS_LOG.md` | 20 chronological entries incl. two correction rows |
| E14 | test suite (110 tests), `phase0*.py` drivers | reproducibility apparatus |

---

## Provisional outline → evidence

### 1. Özet
Claim: a keyword filter misses 63% of Turkish offensive content; a fine-tuned
transformer does not fix it (33pp dev / **40pp test** recall gap); the fix that
was designed for it works as a component but not as a system; a calibrated
review layer converts the residual weakness into a routing policy.
**Evidence:** E1, E2, E10, E9. **Status: SOLID.**

### 2. Problem tanımı ve motivasyon
Turkish agglutination + obfuscation; reviewer-tool framing (never per-account
scoring, per competition constraints).
**Evidence:** E1 (the 63% figure is the motivating measurement). **SOLID.**

### 3. İlgili çalışmalar
CITA, ToxiCloakCN, robustness (arXiv 2203.11331), selective prediction, Çöltekin
2020, BRUMS BERTurk ≈0.786, ConvBERTurk ≈82, Adalı & Eryiğit.
**Evidence:** briefing §10 list only. **⚠ GAP G6 — see below. No citation figure
has been verified against its primary source, and the briefing explicitly
forbids using secondary-source numbers in the report.**

### 4. Veri ve deneysel kurgu
Çöltekin OffensEval-TR; role separation; stratified 85/15 split seed 42;
dev fingerprint `034415af3a23b388`; train 26,992 / dev 4,764; test 3,528
(2,812 NOT / 716 OFF); frozen 695-entry lexicon; anti-circularity rules.
**Evidence:** E2, E10, E3, E5, E8. **SOLID.**

### 5. Yöntem
- **5.1 Sözlük süzgeci** — `hit_root`, `MIN_ROOT_LEN=3`, Turkish casing. E1, E2.
- **5.2 BERTurk** — `dbmdz/bert-base-turkish-cased`, 3 epochs, lr 2e-5, batch 32,
  max_len 128, fp16, no class weighting, no threshold tuning. E2 (`run_config.json`).
- **5.3 Savunma** — 1a masking (structural filter, 382 rows ×3), 1b insertion
  (~2,000, patterns from out-of-fold *training* errors only, C1), D-family
  obfuscation disjoint from H. E5, E6, E7.
- **5.4 Kalibrasyon + seçici tahmin** — temperature on the CAL half; threshold
  from CAL, metrics from EVAL. E8, E9.
**Status: SOLID.**

### 6. Bulgular

| § | Content | Key numbers | Evidence | Status |
|---|---|---|---|---|
| 6.1 | Temel çizgi ve boşluk | keyword dev macro-F1 0.6799 [0.6621, 0.6969]; BERTurk 0.8271 [0.8139, 0.8405]; hit 0.8930 vs free 0.5628; **gap +0.3301 [+0.2771, +0.3827]** | E2, E3 | SOLID |
| 6.2 | Hata analizi | noise **10%** (unbiased 40/247) vs 23.3% (biased top-60) — the correction is itself a result; 95/213 FP profanity-bearing, **84/95 (88%) perform no offensive act**; 43/47 lexicon_hit FP not directed; sensitivity: gap *widens* to +0.3662 when suspect roots excluded | E4 | SOLID |
| 6.3 | Savunma | four runs; `lexicon_free` +0.0336 [+0.0052, +0.0662] dev; macro-F1 flat; 1b's target FP rate rose 0.1815→0.1931; H-transfer +0.0141 | E6, E7 | SOLID |
| 6.4 | Kalibrasyon / risk–kapsam | raw **T=0.9948, ECE 0.0205** (needs none); defense **T=1.9732, ECE 0.0786**; curve 100%→50%; **deferral is slice-blind** (9.4% vs 9.6%) | E9 | SOLID |
| 6.5 | Resmî test | keyword 0.6657; raw **0.8095 [0.7930, 0.8261]**; defense 0.8093; **gap +0.3970 [+0.3418, +0.4542]**; paired `lexicon_free` +0.0358 [+0.0043, +0.0665] | E10 | SOLID |
| 6.6 | Karşılaştırma matrisi (§8) | — | — | **⚠ PARTIAL — G1, G2, G3** |

### 7. Operasyonel sistem
The pivotal sentence the briefing asks for, in the two declared forms, **on the
official test set**:
> "%90.2 otomatik kapsamda sistem 0.8485 macro-F1 / %8.52 hata ile çalışır ve
> %9.8'i insan incelemesine devreder."
> "%79.8 otomatik kapsamda 0.8900 macro-F1 / %5.43 hata; %20.2 devredilir."

Plus error concentration 3.59× / 3.15×, and the demo.
**Evidence:** E9, E10, E12. **SOLID.**

### 8. Sınırlılıklar
Annotation convention (Çöltekin adopted as given, ~13/40 of the unbiased sample
is politician/institution criticism); slice contamination (248/614 suspect-only,
direction measured and conservative); the 1b positional-cue limitation stated at
precision, not mitigated; H-family weakness (costs raw only 0.0149 macro-F1);
proxy no-profanity FP count ≠ manual 118; checkpoint tie (epochs 1 and 3).
**Evidence:** E4, E7, E9, E10. **SOLID — this is a strength section, not an
apology; every limitation is quantified.**

### 9. Yöntemsel titizlik (rigor / reproducibility)
Pre-registration before results (E3, E8, commits dated before any number);
append-only log with two correction rows (E13); single-use test accounting with
**both opens recorded, including the crashed one** (E11); 110 tests; frozen
fingerprint on every result; deltas with CIs reported regardless of sign.
**Evidence:** E3, E8, E11, E13, E14. **SOLID — and differentiating.**

### 10. Sonuç
Component works / system does not; the gap replicates and is the real finding;
the operational answer is the review layer, not a better classifier.
**Evidence:** E7 (corrected), E10, E9. **SOLID.**

---

## Gaps — flagged, not written around

### G1 — ConvBERTurk: NO EVIDENCE, and now unfixable on test
Briefing §8 row 3 and §9 items 1 and 4 ("is the failure pattern general across
both models, or specific?") require ConvBERTurk. It was cut from scope early and
never run. **Critically: the official test set is SPENT, so ConvBERTurk can never
receive a test-set number.** Even if trained now, it could only ever appear as a
dev row.

Options: (a) train on dev only and present the matrix row as dev-only, clearly
marked, answering §9 item 4 at dev level; (b) delete the row and state the scope
cut explicitly. **Recommendation: (b), with one sentence saying the
generality-across-architectures question is open.** (a) costs ~1 GPU-hour and
buys a row that cannot be compared to the others' test column.

### G2 — Mayda / Beyhan cross-corpus: NO EVIDENCE, no data on disk
Briefing §8 columns 2–3 and §9 item 5. `data/mayda/` and `data/beyhan/` contain
only zero-byte `.gitkeep`; neither corpus is mentioned anywhere in the log or any
findings file. These were never acquired.

Options: (a) acquire and run — this is *clean*, it conflicts with no spend rule
and would genuinely strengthen the generalisation claim; (b) cut the columns and
state it. **Recommendation: (a) if there is a day for it, since it is the only
gap that is both fillable and evidentially valuable; otherwise (b).**

### G3 — Held-out obfuscation on the official test set: not measurable now
We have the H column on **dev** for four BERTurk variants (E7): H-perturbed
macro-F1 0.8122 / 0.8079 / 0.8085 / 0.8124 and OFF-recall 0.6565 / 0.6261 /
0.6652 / 0.6793. We do **not** have it for the keyword filter or on test.

A technical note that is a judgment call for the project lead, not mine:
`test_predictions.csv` retains the test *text*, so H could be applied and the
models re-run without calling `load_coltekin_test`. **That would nevertheless be
a second measurement on the official test set, which is precisely what the spend
rule exists to prevent.** Recommendation: report the H column on dev only, and
say so.

### G4 — Related-work figures unverified
Briefing §10 closes with: *"Any figure copied into the technical report must be
re-verified from its primary source before writing — secondary-source numbers are
for orientation only."* **No citation in that list has been verified.** BRUMS
≈0.786, ConvBERTurk ≈82, and every arXiv identifier are currently
orientation-only and may not be written as-is. This needs network access and is a
prerequisite for §3, not a drafting detail.

### G5 — Quotable failure examples not in the committed record
§9 item 2 asks for "the actual most-confident false-negative texts".
`fp_function_tags.json` carries `note_text_withheld` — the tag files hold ids and
tags, not corpus text. The 8 rows extracted for the demo (`demo/examples.json`)
are real, tagged, and quotable; more can be pulled the same way from the Drive
mirror. **Minor, fillable in minutes — but it must be done before §6.2 is drafted.**

### G6 — Operating points: 2 declared, briefing says "2–3"
Not a gap in evidence, a wording choice. Two are declared and both are measured
on test. A third could be read off the existing curve at no cost if a
higher-automation point is wanted.

---

## Sequencing before any prose

1. **Project lead supplies the KYS şablonu** → re-cut this outline to its headings.
2. Decide G1 and G2 (scope cuts vs. one more day of work). These change the
   matrix's shape and therefore §6.6.
3. Verify the §3 citations from primary sources (G4) — blocking for §3.
4. Pull ~6 more quotable rows for §6.2 (G5).
5. Then draft, section by section, each against its evidence row above.

Nothing in steps 2–4 requires touching the official test set.
