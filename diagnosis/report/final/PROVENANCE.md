# `report/final/` — provenance and figure traceability

## What this directory holds

The **approved** Turkish text of KYS template sections 1.1, 1.2, 2.1 and 2.2
(7 + 8 + 7 + 8 = 30 scored points), plus the bibliography those sections cite.
None of it is a draft and none of it was written here.

| File | Template sections |
|---|---|
| `01_proje_tanimi.md` | 1.1 Proje Konusu ve Amacı; 1.2 Proje Kapsamı ve Yöntemi |
| `02_problem_ve_cozum.md` | 2.1 Problem Tanımı ve Mevcut Çözümler; 2.2 Çözüm Fikri, Özgünlük ve Yerlilik |
| `09_kaynakca_partial.md` | KAYNAKÇA — **partial**, five fields unfilled; see open item 2 |

**Do not conflate this numbering with the drafts'.** `report/01_veri_ve_deney_kurgusu.md`
also has sections numbered 1.1/1.2/2.1/2.2 — those are *Veri kümesi*, *Dondurulmuş
sözlük*, *Model ve eğitim yapılandırması*, *Bölünmenin dondurulması*, which is
different content entirely. See `handoff_bundle/approved/NOT_FOUND.md`.

## Origin

**Supplied by the project lead from the writing conversation, 2026-08-23.**
Committed **verbatim**: no word, figure, citation number or punctuation mark was
altered, added or removed.

It arrived in two supplies on the same day, both recorded here because the second
changed a value in the first:

- **Supply 1**, commit `8fbb608` (02:32) — sections 1.1, 1.2, 2.1, 2.2.
- **Supply 2**, this commit — the same four sections with **one** correction, plus
  the bibliography block, which supply 1 did not contain.

The whole of supply 2 was diffed against what supply 1 had committed. **The four
sub-sections differ in exactly one line**, and it is the one the lead named: the
comparison table's review date, `20.08.2026` → `23.08.2026` (`02_problem_ve_cozum.md`
line 22). The lead's note: today's date is correct, and 20.08.2026 was carried over
in error from the sweep file's header. Every other byte of 1.1, 1.2, 2.1 and 2.2 is
unchanged — verified by `diff`, not by reading.

There is **no Dehghan citation in this project**, per the lead. Confirmed: a
case-insensitive search over the repository returns no match, and none was added.

Three mechanical decisions, all content-neutral, all recorded here rather than
performed silently:

1. **The pasted block was split at chapter boundaries** — 1.1/1.2 in one file,
   2.1/2.2 in another, the bibliography in a third at the filename the lead
   specified. This matches the one-file-per-chapter convention already used by
   `report/*.md`. No prose crossed a boundary and no heading was invented.
2. **The trailing length note was not included.** The lead's closing paragraph
   (word count, page estimate, the carry-forward warnings) is editorial
   correspondence about the text, not text of the report.
3. **Headings carry `##` markers rather than the `**bold**` of the paste.** The
   heading *text* is untouched and exact; only the Markdown that makes it a
   heading differs. `##` is what supply 1 committed, what `report/*.md` uses, and
   what any Markdown-to-docx step will need in order to see a heading at all.
   Reverting to bold is a one-character change per heading if the lead prefers it.

No H1 chapter headings exist in the approved block, so none were added. They will
have to come from the template when these sections are assembled.

The provenance note at the top of `09_kaynakca_partial.md` is an HTML comment: it
does not render, and it is not report text.

## Figure traceability (master prompt §0, NUMBER RULE)

Every experimental figure in the approved text, read out of the repository
artefact named — not from memory. Verified 2026-08-23.

**Supply 2 changed no figure.** Its single edit is the 2.1 table's review date, an
access date rather than a measurement, so the whole table below carries over
untouched. This is established by `diff` over the two supplies, not by re-reading
the prose.

| Figure as written | Artefact | Recorded value | |
|---|---|---|---|
| 31.756 gönderi | `results/day1_report.json` `n_rows` | 31756 | ✓ |
| saldırgan oranı %19,3 | same, `label_dist.OFF` / `n_rows` | 6131/31756 = 0,193072 | ✓ |
| 6.131 saldırgan etiketli | same, `label_dist.OFF` | 6131 | ✓ |
| 3.892'si | same, `lexicon_free_root` | 3892 | ✓ |
| yani %63,5'i | same, 3892/6131 | 0,634806 | ✓ |
| 695 girdilik sözlük | same, `lexicon_size` | 695 | ✓ |
| geri çağırma 0,8930 (`lexicon_hit`) | `results/09_deeper_analysis/stage_1/stage1_auc.json` `matched_operating_points.reference_lexicon_hit_at_0.5.recall` | 0,8929577 | ✓ |
| geri çağırma 0,5628 (`lexicon_free`) | same, `reference_lexicon_free_at_0.5.recall` | 0,5628319 | ✓ |
| fark +0,3301 | `results/01_baseline_berturk/metrics.json`; `results/02_failure_analysis/slice_sensitivity.json` | 0,33012589 | ✓ |
| [+0,2771; +0,3827] | same | 0,27714806 / 0,38269503 | ✓ |
| test farkı +0,3970 | `results/05_final_test/metrics.json` `.systems.raw.recall_gap.delta` | 0,39699608 | ✓ |
| [+0,3418; +0,4542] | same, `.ci_low` / `.ci_high` | 0,34180000 / 0,45420597 | ✓ |
| ROC-AUC 0,8962 (`lexicon_free`) | `stage1_auc.json` `primary.auc_lexicon_free` | 0,89615 | ✓ |
| ROC-AUC 0,9306 (`lexicon_hit`) | same, `primary.auc_lexicon_hit` | 0,930611 | ✓ |
| EVAL yarısı n = 2.382 | `results/12_threshold_policy/c12_16_intervals.json` `provenance.strata` "EVAL rows" | 2382 | ✓ |
| geri çağırma +0,1727 | same, `.intervals.d_recall_free.point_estimate` | 0,17266187 | ✓ |
| [+0,1295; +0,2194] | same | 0,12949640 / 0,21942446 | ✓ |
| fark −0,1067 | same, `.intervals.d_gap.point_estimate` | −0,10672780 | ✓ |
| [−0,1630; −0,0484] | same | −0,16297731 / −0,04838327 | ✓ |
| kesinlik bedeli −0,1418 | same, `.intervals.d_precision.point_estimate` | −0,14181617 | ✓ |
| [−0,1723; −0,1131] | same | −0,17225377 / −0,11314455 | ✓ |
| taban çizgisi %82,71 makro-F1 | `results/01_baseline_berturk/metrics.json` | 0,82707527 | ✓ |
| altı düzeltme satırı | `docs/RESULTS_LOG.md` | 6 rows | ✓ |
| bir spesifikasyon kusuru kaydı | `docs/RESULTS_LOG.md` line 43, "SPEC DEFECT" | 1 row | ✓ |
| altı ön kayıt protokolü | `phases/` | **7** | ⚠ see below |

Cross-check, unprompted and passing: `day1_report.json` records the frozen lexicon
at sha256 `0f5a05f5…ce20b`, which is byte-identical to the `lexicon/karaliste.txt`
in the demo bundle and to the digest the phase-12 provenance gate verified. The
695 entries cited in 1.1 and the 695 entries the demo loads are the same file.

The ordering disclosure stated in 1.1 ("Dört büyüklük önceden sabitlenmiştir;
güven aralıkları ise nokta tahminleri yayımlandıktan sonra hesaplanmıştır") and
its scope limit in 1.2 (Aşama 12'nin sonradan eklenen aralık hesabı) both match
`c12_16_intervals.json` `ordering_disclosure` and `dev_only_note` in substance.
These two sentences are load-bearing against a juror who opens the repository and
must not be trimmed for length.

### Figures NOT traceable here, because they are literature, not measurement

Outside the repository by nature; each is carried on its own citation and was not
re-derived: 58,5 milyon / %66,7 / 77,3 milyon / %88,3 `[12]`; 35.284 belge and
%19,4 `[2]`; %97,19 alt grup ROC-AUC and 14.000 örnek `[16]`; %82,76 and %81,0
`[8]`; on dil `[5,6]`; 31 Aralık 2026 `[14]`; 5651 sayılı Kanun `[13]`.

## Open items carried into this directory

1. **The protocol count.** The text states six pre-registration protocols, all
   committed before their phase's first number. The repository contains **seven**
   protocol documents that fix decision rules and produce numbers — phases 01, 03,
   04, 08, 09, 11 and 12 — and **all seven pass the ordering test** against git
   history, phase 08 included once its rename from `phases/06_lexical_analysis.md`
   is followed. The number six matches the six-row table at `report/02_yontem.md`
   §2.5, but that table counts phase 09 twice (Stages 1 and 1b) and omits phases 11
   and 12 — and phase 12 is the pre-registration that governs the C12-16 quantities
   quoted in 1.1. The true claim is stronger than the written one. **Not changed:
   the text is approved and the correction is the lead's to make.**
2. **The bibliography is committed but partial.** Supply 2 closed the larger half
   of this item: `09_kaynakca_partial.md` now defines `[1]`–`[16]`, each exactly
   once, and **every bracket used in 1.1/1.2/2.1/2.2 resolves** — checked
   mechanically, not by eye. What remains open:
   - **Five unfilled fields**, carried in the entries as placeholders. `[1]` has
     no access address. `[3]`, `[14]`, `[15]` and `[16]` have no publication date.
     `[3]`'s blank date is the one the lead flagged by name; the other three are
     the same class of gap and are listed here so they are not mistaken for
     complete entries.
   - **`[15]` is defined but never cited.** Azure AI Content Safety is named in
     the 2.1 table without a bracket, so nothing in the approved text points at
     `[15]`. Either the table gains the bracket or the entry is dropped — the
     lead's call, and not changed here.
   - **`[17]`–`[19]` deliberately do not exist.** AWS Comprehend, OpenAI
     omni-moderation and YSS Shield are named in the table but carry no bracket
     because their entries cannot be completed. The numbering was closed up rather
     than left with gaps, so a reader finding `[16]` last is seeing the intended
     end of the list, not a truncation.
   - **None of the sixteen entries was re-verified against its source here.** They
     are committed as supplied. §0 governs experimental figures against repository
     artefacts; a bibliography is neither, and re-deriving it is a separate task.
3. **The page estimate is unverified here.** The lead's 4,05-of-27 figure was not
   reproduced: `report/build_docx.py` `SOURCES` names the four drafts only and
   does not read `report/final/`, so this text has never been paginated in the KYS
   template geometry. Building it would require editing that list. The estimate
   also predates the bibliography, which adds a page-consuming file the 1.941-word
   count did not include.
4. **`%97,19` and the Detoxify bias concession share one source** (the Detoxify
   README). Per the lead: cite one and you cite the other, and neither may be
   loosely paraphrased.
