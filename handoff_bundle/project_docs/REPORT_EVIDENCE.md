# NSosyal B* — Report Evidence Extract

Every recorded figure a report sentence could rest on, transcribed from a
committed artifact, with its source, its scope and its status.

**This file interprets nothing.** It ranks nothing, recommends nothing and
summarises nothing. Where two committed places carry different values for the
same quantity, both are printed and the disagreement is flagged; none is
silently resolved. Nulls, insufficient results, failed predictions and declared
limitations are required content and are present in full.

Built at commit `9d3c8c6` (`docs/RESULTS_LOG.md` at 53 lines: header lines 1–10,
table header 11–12, data rows 13–53).

---

## How to read the tags

Every figure carries three tags.

**SRC** — where the number was read from. Either a `docs/RESULTS_LOG.md` line
number (`RL:41`) or a file plus a JSON key path (`results/.../metrics.json#primary.signed_gap`),
or a pre-registration file plus clause and commit.

**SCOPE** — one of:

- `[TEST]` — measured on the official Çöltekin test set (3,528 rows), in the
  single permitted pass of 2026-08-16. That set is now SPENT.
- `[DEV-ONLY]` — the official test set was **not** involved. The exact
  denominator varies and is stated with each figure: full dev (4,764), the EVAL
  half (2,382), the CAL half (2,382), or the training split (26,992). **Tagging
  convention flagged:** the task specifies a binary `[TEST]` / `[DEV-ONLY]` tag,
  but Phase 08's statistics are computed on the **training split**, which is
  neither dev nor test. Those are tagged `[DEV-ONLY]` in the sense "test set not
  involved", with `(train split)` stated in the figure text. This is an
  interpretation of the tag, recorded here rather than applied silently.
- `[SCOPE UNCLEAR]` — used where a source does not fix the scope. No figure in
  this file required it; the one place scope needed care is noted in A2 §A2.4.

**STATUS** — zero or more of `[PRE-REGISTERED]`, `[POST-HOC]`,
`[DESCRIPTIVE, NO CI]`, `[VERDICT]`, `[CORRECTED]`, `[SUPERSEDED]`.

**Conflicting values are flagged inline** with the marker `⚑ CONFLICT`. They
occur at: A2 §A2.6 (two intervals for the same Phase 08 quantities), A2 §A2.8
(two intervals for `lexicon_free` ROC-AUC), and F §F.7 / D §D.9 (the EOL
limitation, line 51 against line 52).

**No corpus row text appears in this file.** Verified by substring test against
all 4,764 `text` cells of `results/01_baseline_berturk/dev_predictions.csv`
(the only column with cells of 15 characters or more).

---

# A. HEADLINE CLAIMS

Nothing appears in both A1 and A2.

## A1 — [TEST]

Every figure below was measured in the single permitted pass over the official
Çöltekin test set, `results/05_final_test/`, run 2026-08-16T11:10:34 at commit
`9af62f9`. Thresholds were **read** from `results/04_calibration/calibration.json`
and never re-derived on test (`thresholds_re_derived_on_test: false`).

### A1.1 Test-set composition

| quantity | value |
|---|---|
| rows | 3,528 |
| gold NOT / gold OFF | 2,812 / 716 |
| `lexicon_hit` / `lexicon_free` | 491 / 3,037 |
| `lexicon_hit` base rate OFF | 0.5478615071283096 |
| `lexicon_free` base rate OFF | 0.14718472176489958 |

SRC `RL:25` · `results/05_final_test/metrics.json#n_test, #systems.raw.lexicon_hit.n, #systems.raw.lexicon_free.n, #...base_rate_off` · SCOPE `[TEST]` · STATUS `[DESCRIPTIVE, NO CI]`

Input digests: test `9052784e13248e58658e34a4f86a3463ef8b2594d2feb289e4b29bba2866b437`,
gold `ae9b0837e948c3d9c3a147d2a415989a4940a7756d5821b3289276574941c9e3`,
lexicon `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b`.
SRC `results/05_final_test/metrics.json#hashes` · SCOPE `[TEST]`

### A1.2 THE HEADLINE — the recall gap replicates on held-out data

**BERTurk raw, OFF-recall gap (`lexicon_hit` − `lexicon_free`) = +0.39699608293206257,
95% CI [+0.3418000046134851, +0.45420597387207523], excludes zero.**

SRC `RL:25` · `results/05_final_test/metrics.json#systems.raw.recall_gap` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`

Pre-registered as the decision rule in `phases/01_baseline_diagnosis.md`
("Pre-registered decision rule", three outcomes on the bootstrap CI of the
OFF-recall gap), committed `197d953` (2026-08-15) before any BERTurk number
existed. The primary evaluation metric — `lexicon_free` OFF-recall — is declared
in `report/01_veri_ve_deney_kurgusu.md` §1.7 (commit `28ff263`).

Component slice recalls, raw:

| slice | OFF-recall | 95% CI | confusion (tn/fp/fn/tp) |
|---|---|---|---|
| `lexicon_hit` (n 491, 269 OFF) | 0.9070631970260223 | [0.8709616092235987, 0.9386973180076629] | 184 / 38 / 25 / 244 |
| `lexicon_free` (n 3,037, 447 OFF) | 0.5100671140939598 | [0.4627873202740519, 0.5545582226762003] | 2453 / 137 / 219 / 228 |

SRC `results/05_final_test/metrics.json#systems.raw.lexicon_hit, #systems.raw.lexicon_free` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`

### A1.3 Overall system numbers on test

| system | macro-F1 | 95% CI | OFF-recall | OFF-precision | confusion (tn/fp/fn/tp) |
|---|---|---|---|---|---|
| keyword filter | 0.6656773483114045 | [0.6455966137498054, 0.6856687315266815] | 0.3756983240223464 | 0.5478615071283096 | 2590 / 222 / 447 / 269 |
| BERTurk raw | 0.8094953592079137 | [0.7930282081563444, 0.8260747184564081] | 0.659217877094972 | 0.7295208655332303 | 2637 / 175 / 244 / 472 |
| +1a+1b+D | 0.8093070714467672 | [0.7926631186735028, 0.8255143727034392] | 0.6717877094972067 | 0.7168405365126677 | 2622 / 190 / 235 / 481 |

Raw OFF-recall CI [0.625, 0.6939669794892551]; defense OFF-recall CI
[0.6382638334663474, 0.707288862620257].

SRC `RL:25` · `results/05_final_test/metrics.json#systems.*` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`

Defense slice recalls: `lexicon_hit` 0.8810408921933085
[0.839203036053131, 0.9169833962060061]; `lexicon_free` 0.5458612975391499
[0.5020962403132899, 0.5898607193811006]; gap +0.3351795946541586
[+0.2802649215805608, +0.3964343644719989], excludes zero.
SRC `results/05_final_test/metrics.json#systems.1a1b_d` · SCOPE `[TEST]`

Keyword-filter gap = **1.0000** with CI [1.0, 1.0). Recorded as **definitional,
not a finding** — the slice boundary is the filter's own decision rule.
SRC `RL:25` · `results/05_final_test/metrics.json#systems.keyword.recall_gap` · SCOPE `[TEST]` · STATUS `[DESCRIPTIVE, NO CI]`

### A1.4 The intervention on test — paired deltas (+1a+1b+D minus raw)

Computed on the saved single-pass predictions; the test set was **not** reopened.
1,000 paired bootstrap resamples, seed 42, identical rows.

| quantity | delta | 95% CI | excludes zero |
|---|---|---|---|
| macro-F1 | −0.00018828776114654389 | [−0.012867950543002823, +0.011817360328561061] | no |
| OFF-recall | +0.012569832402234637 | [−0.012556739834174777, +0.036443924074188956] | no |
| OFF-precision | −0.012680329020562597 | [−0.03967078421600962, +0.010935740220897699] | no |
| `lexicon_hit` OFF-recall | −0.02602230483271384 | [−0.0592647666253615, +0.007692307692307668] | no |
| **`lexicon_free` OFF-recall** | **+0.03579418344519014** | **[+0.004321093698047141, +0.06652254249815226]** | **yes** |

SRC `RL:27` · `results/05_final_test/paired_deltas.json#deltas_defense_minus_raw` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`

### A1.5 Selective prediction at the frozen dev thresholds

Thresholds 0.663171 / 0.80091 (raw) and 0.865618 / 0.987655 (+1a+1b+D), all
selected on the dev CAL half in Phase 04 and applied unchanged.

| system / point | coverage | macro-F1 | error rate | capture lift |
|---|---|---|---|---|
| raw, high-automation | 0.9016439909297053 | 0.8485489582207839 | 0.08519333542911034 | 3.5912595516978123 |
| raw, high-precision | 0.7981859410430839 | 0.8900293962474798 | 0.05433238636363636 | 3.1456919900244027 |
| +1a+1b+D, high-automation | 0.911281179138322 | 0.843249290365670 | 0.09082426127527216 | 3.5273369667355756 |
| +1a+1b+D, high-precision | 0.710884353741497 | 0.910834 | 0.045454545454545456 | 2.5310 |

Raw high-automation CIs: coverage [0.8925736961451247, 0.9115646258503401],
macro-F1 [0.8319970237545736, 0.8653421645829655], error
[0.07523233983161494, 0.09436328104603463].
Raw high-precision CIs: macro-F1 [0.8740703188795215, 0.9074922116303366],
error [0.04573888115741614, 0.06276304795440299].

SRC `RL:26` · `results/05_final_test/metrics.json#systems.raw.selective, #systems.1a1b_d.selective` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`

**Threshold transfer, dev EVAL → test coverage:** raw −1.02pp (0.911839 →
0.901644) and −1.79pp (0.816121 → 0.798186); defense −0.26pp (0.913938 →
0.911281) and −0.70pp (0.717884 → 0.710884).
SRC `RL:26`, `RL:49` · `results/05_final_test/metrics.json#thresholds.points.*.dev_coverage` vs `#systems.*.selective.*.coverage` · SCOPE `[TEST]` · STATUS `[DESCRIPTIVE, NO CI]`

**Operational cost of the defense's miscalibration:** to reach the error level
raw reaches at 20.2% deferral, the defense variant must defer 28.9%.
SRC `RL:27` · derived from `#systems.*.selective.high_precision.coverage` · SCOPE `[TEST]` · STATUS `[DESCRIPTIVE, NO CI]`

### A1.6 Slice-blindness of deferral — replicates on test (null)

| point | `lexicon_free` deferral | `lexicon_hit` deferral | free share of queue | free share of test |
|---|---|---|---|---|
| high-automation | 0.098123 | 0.099796 | 0.858790 | 0.860828 |
| high-precision | 0.202832 | 0.195519 | 0.865169 | 0.860828 |

SRC `RL:26` · `results/05_final_test/metrics.json#systems.raw.selective.*.by_slice` · SCOPE `[TEST]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]` (replicates the Phase 04 null, see E §E.1)

### A1.7 Test-set single-use accounting

Opened twice: 2026-08-16T11:09:00 (crashed before any forward pass, an
`AttributeError` on `Tee.isatty` from transformers while loading the first
checkpoint; no predictions, no numbers) and 2026-08-16T11:10:36 (the complete
run). Spend record written 11:11:44.

SRC `RL:28` · `results/05_final_test/TEST_SET_OPENED.json` (2 entries), `results/05_final_test/TEST_SET_SPENT.json#spent_at` · SCOPE `[TEST]` · STATUS `[DESCRIPTIVE, NO CI]`

---

## A2 — [DEV-ONLY]

The official test set was not involved in any figure below.

### A2.1 Frozen split and corpus (full dev / full corpus)

| quantity | value |
|---|---|
| corpus rows | 31,756 (25,625 NOT / 6,131 OFF) |
| corpus sha256 | `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa` |
| lexicon entries / sha256 | 695 / `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` |
| Day-1 gate: `lexicon_free` OFF of total OFF | 3,892 / 6,131 (16/16 frozen fields reproduce) |
| `lexicon_hit_literal` / `lexicon_hit_root` | 1,787 / 2,239 (agglutination delta 452) |
| split seed 42, dev fraction 0.15 | train 26,992 (5,211 OFF) / dev 4,764 (920 OFF) |
| dev fingerprint | `034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4` |
| dev slices | `lexicon_hit` 614 (355 OFF, 259 NOT) · `lexicon_free` 4,150 (565 OFF, 3,585 NOT) |
| dev slice base rates | 0.578176 · 0.136145 |

SRC `RL:13`, `RL:14` · `results/day1_report.json`, `results/day1_report_rerun.json`, `data/splits/split_seed42.json`, `results/01_baseline_berturk/run_config.json#split` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.2 Phase 01 — BERTurk baseline on dev (full dev, 4,764)

Model `dbmdz/bert-base-turkish-cased`, seed 42, 3 epochs, L4, commit `837c351`.
Hyperparameters: batch 32, lr 2e-05, max_len 128, warmup 0.1, weight decay 0.01,
fp16, **class_weighting `null`**, **threshold 0.5**.

| quantity | value | 95% CI |
|---|---|---|
| macro-F1 | 0.8270752670616224 | [0.8138925991245577, 0.8404931829690758] |
| OFF-recall | 0.6902173913043478 | [0.6603335876514874, 0.7191433437118332] |
| OFF-precision | 0.7488207547169812 | — |
| confusion (tn/fp/fn/tp) | 3631 / 213 / 285 / 635 | — |
| `lexicon_hit` OFF-recall | 0.8929577464788733 | [0.8617812985609081, 0.9247963091922006] |
| `lexicon_free` OFF-recall | 0.5628318584070796 | [0.5210336958632744, 0.600994905085022] |
| **recall gap** | **+0.33012588807179366** | **[+0.2771480590457781, +0.3826950345077446]**, excludes zero |

SRC `RL:15` · `results/01_baseline_berturk/metrics.json#berturk` · SCOPE `[DEV-ONLY]` (full dev) · STATUS `[PRE-REGISTERED]`

**The shortcut runs in both directions.** False-positive rate on gold-NOT rows:
`lexicon_hit` 0.18146718146718147 (47/259) vs `lexicon_free` 0.04630404463040446
(166/3585), ratio 3.9190352142159375.
SRC `RL:15` · `#lexical_shortcut_both_directions` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

Keyword filter on dev: macro-F1 0.6798824672611369
[0.6621096152425808, 0.6969206661974825], OFF-recall 0.3858695652173913
[0.35387843630127414, 0.41870350690754515], OFF-precision 0.5781758957654723.
SRC `RL:14`, `RL:15` · `#keyword_filter` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

**Checkpoint tie, recorded:** epochs 1 and 3 tie at macro-F1 0.8270752670616224
with identical confusion matrices but disagree on **198 of 4,764** dev rows (43
gold-OFF flips each way, 56 gold-NOT each way). All reported numbers and
`dev_predictions.csv` come from `best.pt` = **epoch 1**.
SRC `RL:15` · `#checkpoint_tie` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

Training history: epoch 1 loss 0.3466165497969677 / dev macro-F1 0.8270752670616224;
epoch 2 0.21298542834147458 / 0.8246369676730552; epoch 3 0.1359960284631399 / 0.8270752670616224.
SRC `#training_history` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.3 Phase 02 — failure analysis and slice-contamination sensitivity

Manual reading of all **285 FN** and all **213 FP** in `dev_predictions.csv`
(`best.pt` = epoch 1).

- Annotation-noise rate **corrected to ~10%**, not the Day-1 30–35%: top-60 FN by
  confidence 23% mislabeled; unbiased random 40 of the 247 `lexicon_free` FN
  (seed 42) **10%** mislabeled, 35% genuine implicit offense, 2.5% surface
  evasion, 52.5% ambiguous. SRC `RL:16` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]` (supersedes the Day-1 estimate recorded at `RL:15#stated_limitation`)
- FP side: **95 of 213 (45%)** contain a profanity token; of those **84 (88%)
  perform no offensive act** — 26 non-directed, 19 filler, 16 sense-collision,
  9 meta-discussion, 6 negated, 5 quoted, 3 self-directed; 11 are directed
  insults where gold looks wrong. Of the 47 `lexicon_hit` FP, **43 (91%)** are
  not a directed offensive use. SRC `RL:16` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`
- Checkpoint stability: **0/60** top FN and **1/40** top FP are
  checkpoint-specific; the 43 CS false negatives sit at the boundary (median
  p_OFF 0.4017 vs 0.1724 stable). SRC `RL:16` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Slice-contamination sensitivity (SENS-3 lineage).** 248 of 614 hit-slice rows
(40.4%) are suspect-only — 151 exact matches to a suspect entry, 97 prefix-only;
gold split 175 NOT / 73 OFF, against 84 NOT / 282 OFF for the 366 retained.

| definition | hit recall | free recall | gap | 95% CI |
|---|---|---|---|---|
| as reported (frozen) | 0.8929577464788733 | 0.5628318584070796 | +0.33012588807179366 | [+0.2771480590457781, +0.3826950345077446] |
| 248 suspect-only excluded | 0.9291 | 0.5628 | **+0.3662** | [+0.3187, +0.4169] |

Shift **+0.0361**; CI excludes zero in both.
SRC `RL:17` · `results/02_failure_analysis/slice_sensitivity.json#as_reported_frozen_definition, #sensitivity_suspect_only_excluded, #delta_shift` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]` (robustness check; the reported headline stays +0.3301)

### A2.4 Phase 03 — the four defense runs (full dev)

| quantity | raw | +1a | +1a+1b | +1a+1b+D |
|---|---|---|---|---|
| macro-F1 | 0.8270752670616224 | 0.8243983668796604 | 0.8172956237971718 | 0.820163145136936 |
| OFF-recall | 0.6902173913043478 | 0.6619565217391304 | 0.6782608695652174 | 0.6945652173913044 |
| OFF-precision | 0.7488207547169812 | 0.7699115044247787 | 0.7289719626168224 | 0.7228506787330317 |
| `lexicon_free` OFF-recall | 0.5628318584070796 | 0.5203539823008849 | 0.584070796460177 | 0.5964601769911504 |
| `lexicon_hit` OFF-recall | 0.8929577464788733 | 0.8873239436619719 | 0.828169014084507 | 0.8507042253521127 |
| `lexicon_hit` FP rate | 0.18146718146718147 | 0.17374517374517376 | 0.18532818532818532 | 0.19305019305019305 |
| recall gap | +0.33012588807179366 | +0.36696996136108695 | +0.24409821762433004 | +0.25424404836096226 |
| FPs total / no-profanity | 213 / 185 | 182 / 156 | 232 / 205 | 245 / 215 |
| H-perturbed OFF-recall | 0.6565217391304348 | 0.6260869565217392 | 0.6652173913043479 | 0.6793478260869565 |
| H-perturbed macro-F1 | 0.8121680224890755 | 0.8078604179727448 | 0.808465038644363 | 0.8124248386210018 |

SRC `RL:20` · `results/03_defense/comparison.json#runs`, `results/03_defense/run_*/metrics.json#heldout_obfuscation_H_dev` · SCOPE `[DEV-ONLY]` (full dev; H-perturbed = 614 rows perturbed under a family never trained on) · STATUS `[DESCRIPTIVE, NO CI]`

**Paired deltas vs raw** (1,000 resamples, seed 42, paired, 4,764 rows):

| variant | quantity | delta | 95% CI | excludes zero |
|---|---|---|---|---|
| +1a | macro-F1 | −0.002676900181961983 | [−0.01246915322244021, +0.0065457471347365225] | no |
| +1a | `lexicon_free` OFF-R | **−0.04247787610619469** | **[−0.07220601729369132, −0.010982622029133735]** | **yes** |
| +1a | `lexicon_hit` OFF-R | −0.005633802816901401 | [−0.03099030443282923, +0.01939192828562638] | no |
| +1a+1b | macro-F1 | −0.009779643264450577 | [−0.020786935006238304, +0.0006268120845404403] | no |
| +1a+1b | `lexicon_free` OFF-R | +0.0212389380530974 | [−0.008655984015201186, +0.05017975126311701] | no |
| +1a+1b | `lexicon_hit` OFF-R | **−0.06478873239436622** | **[−0.09779128893051883, −0.03150969585298338]** | **yes** |
| +1a+1b+D | macro-F1 | −0.006912121924686376 | [−0.01845930461090125, +0.005174732498733941] | no |
| +1a+1b+D | `lexicon_free` OFF-R | **+0.03362831858407078** | **[+0.005233136699419122, +0.06617711108833776]** | **yes** |
| +1a+1b+D | `lexicon_hit` OFF-R | **−0.04225352112676062** | **[−0.07777857829010572, −0.010924554909219123]** | **yes** |

SRC `RL:20`, `RL:29`, `RL:32` · `results/03_defense/comparison.json#deltas_vs_raw` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

**Note on `comparison.json` provenance (not a scope problem, a recovery record).**
This file was regenerated on 2026-08-16 by re-running `phase03_compare.py`
against the four saved dev prediction dumps on the Drive mirror (seed 42, 1,000
resamples), because the original output lived only in an ephemeral Colab clone.
The regenerated deltas reproduce the published table exactly. Recorded as a
recovery, not a re-measurement.
SRC `RL:32` · commit `8691303` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

Phase 03 step 1 (out-of-fold, 5-fold stratified CV inside the training split,
seed 42, all 26,992 rows): OOF macro-F1 **0.8230**, OFF-recall 0.6985,
OFF-precision 0.7280; 1,360 FP (251 `lexicon_hit` / 1,109 `lexicon_free`), 1,571
FN. Function tagging of a seeded random 60 of the 251 hit FPs: sense-collision
52%, non-directed 18%, filler 17%, quoted 5%, meta 3%, negated/self/directed 5%.
SRC `RL:18` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[DESCRIPTIVE, NO CI]`

Phase 03 step 2 (augmentation review gate): 1a yield **382 of 5,211 gold-OFF
rows (7%)**. Skips: 3,716 no profanity token, 545 no second-person address, 296
multiple profanity tokens, 209 filler-only, 50 too little residual, 13 insult
head. 1b raised to 2,000; 1a upsampled ×3.
SRC `RL:19` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[DESCRIPTIVE, NO CI]`

### A2.5 Phase 04 — calibration, risk-coverage, operating points

CAL/EVAL = 2,382 / 2,382 stratified halving of dev, seed 42.

| quantity | raw | +1a+1b+D |
|---|---|---|
| fitted temperature T | 0.9948165193869881 | 1.9731501284219068 |
| NLL before → after | 0.26164312590326666 → 0.26163936785454145 | 0.38310494726301275 → 0.2914050836130504 |
| ECE(15) before → after | 0.02053844164567604 → 0.019074118554954684 | 0.07856318219983208 → 0.026965557911279803 |
| ECE(10) before → after | 0.01618815449202298 → 0.01540522837113413 | — |
| ECE(20) before → after | 0.020611647355163815 → **0.02112985484106817** (worse) | — |
| MCE(15) before → after | 0.11843494594594595 → 0.12295188508860555 | 0.3487 → 0.2056 |
| signed gap (15 bins) | −0.009073424013434063 | −0.0739 |
| saturated rows at 6dp | 0 (dev, CAL, EVAL) | 0 |

SRC `RL:22` · `results/04_calibration/calibration.json#variants.raw.temperature_fit, #variants.raw.ece, #defense_vs_raw` · SCOPE `[DEV-ONLY]` (EVAL half, 2,382) · STATUS `[PRE-REGISTERED]`

Defense variant puts **1,958 of 2,382** EVAL rows in the top bin at 0.9943
confidence for 0.9372 accuracy. SRC `RL:22` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Temperature invariance of risk-coverage verified exactly**: max absolute
difference **0.00e+00**, both variants.
SRC `RL:23` · `#variants.*.rc_invariance_check` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]` (registered as a prediction in `phases/04_calibration.md` @ `ab225ad`; see C §C.1)

Operating points, raw (threshold selected on CAL, metrics on EVAL):

| point | threshold | coverage | macro-F1 | error rate | capture lift |
|---|---|---|---|---|---|
| high-automation (90% target) | 0.663171 | 0.9118387909319899 | 0.8504158585200146 | 0.07918968692449356 | 3.780952380952381 |
| high-precision (CAL error ≤ 5%) | 0.80091 | 0.8161209068010076 | 0.8755804766152671 | 0.058127572016460904 | 3.056440479983009 |

CIs, high-automation: coverage [0.9005037783375315, 0.9235936188077246],
macro-F1 [0.8286904200612458, 0.8720922794288068], error
[0.06806472675590995, 0.08994193035109556]. High-precision: macro-F1
[0.8522377638077904, 0.8963198012605136], error
[0.04812997504435943, 0.06836756497470788].
SRC `RL:23` · `#variants.raw.operating_points` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[PRE-REGISTERED]`

Deferred 8.8% carry **33.3%** of all errors (3.78× lift); 41.0% error inside the
queue against 7.9% outside.
SRC `RL:23` · `#variants.raw.operating_points.high_automation.error_capture_share, .deferred_error_rate, .error_rate` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[DESCRIPTIVE, NO CI]`

Risk-coverage curve, raw, **full dev**: 100% → 0.8270752670616224 / 10.453%;
95% → 0.8466512411102995 / 8.794%; 90% → 0.8620662641989312 / 7.393%;
85% → 0.8713554960126241 / 6.446%; 80% → 0.8927359763054825 / 5.117%;
75% → 0.9070245017381062 / 4.086%; 70% → 0.9222405579843842 / 3.208%;
65% → 0.925165415413838 / 2.971%; 60% → 0.9354193212274898 / 2.519%;
55% → 0.9438106493380425 / 2.176%; 50% → 0.9496689058090311 / 1.931%.
SRC `RL:23` · `#variants.raw.risk_coverage` · SCOPE `[DEV-ONLY]` (full dev) · STATUS `[DESCRIPTIVE, NO CI]`

The ≤5%-error rule picks 80% coverage for raw and **70%** for the defense
variant. SRC `RL:23` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.6 Phase 08 — word-level lexical dependence (training split)

Statistics on the 26,992 training rows. Dev supplied only the 118 Phase-02
`NOPROF` row ids. Test set not opened.

Computed training base rate **0.193057** (advisor's stated 0.193 confirmed, not
assumed). Bonferroni z threshold |z| ≥ **3.66226** (200 tests, two-sided α 0.05)
plus a 1.5× effect floor.
SRC `RL:34` · `results/08_lexical_analysis/token_stats.json#base_rate, #thresholds` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[PRE-REGISTERED]`

Top-200 group sizes: **lexicon 2**, off-skew non-lexicon **19**, unremarkable
**174**, not-skew **5**.
SRC `RL:34` · `#group_sizes` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[PRE-REGISTERED]`

Selected token statistics: `amk` P(OFF|t) 0.95539, z 31.6779, df 269 (in
lexicon); `aq` 0.986047, z 29.4593, df 215 (**not** matched by `hit_root` — see
D §D.6); `allah` 0.2784, z 5.59 (in lexicon); `sizin` 0.453333, z 12.7699, df
375; `bunlar` 0.4592, df 233; `lan` 0.4332; `sen` 0.2993; `adam` 0.3630; `siz`
0.3479; `senin` 0.3371. Strong-NOT: `güzel` 0.1102, `günaydın` 0.0512, `mutlu`,
`bugün`, `zor`.
SRC `RL:34`, `RL:40` · `#ranked_table_top200` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[PRE-REGISTERED]`

By the linear-weighted secondary (excess OFF rows) the top entries are `user`
(+282.0) and `bu` (+255.1), both **unremarkable** under the declared thresholds.
SRC `RL:34` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[PRE-REGISTERED]`

**Step 3 — do the 118 no-profanity FPs carry those tokens?** A = the 118
Phase-02 `NOPROF` false positives (dev); B = 3,631 dev true negatives, reweighted
to A's (lexicon-hit × token-count-quartile) distribution, edges [10, 16, 26].

| comparison | rate A | rate B matched | difference | 95% CI | verdict |
|---|---|---|---|---|---|
| **Group 2 (pre-registered primary)** | 0.3983050847457627 (47/118) | 0.1917177392618066 | **+0.2065873454839561** | **[+0.1216381832340992, +0.29602714339282143]** | **SUPPORT** |
| Group 2, unmatched | 0.3983050847457627 | 0.16221426604241257 | +0.23609081870335014 | [+0.14990500819216818, +0.32683407708573536] | — |
| Wider pool (df ≥ 30, 104 tokens) | 0.6016949152542372 (71/118) | 0.29999321161050485 | +0.3017017036437324 | **[+0.21552472010606866, +0.3871950928743718]** | SUPPORT |
| **Group-3 control (strong-NOT)** | 0.0847457627118644 | 0.08792525660876847 | **−0.0031794938969040704** | **[−0.04999744218659659, +0.050615789980609525]** | **null** |

SRC `RL:35`, `RL:39` · `#step3.primary`, `#sensitivities.wider_pool`, `#sensitivities.group3_control` · SCOPE `[DEV-ONLY]` (A and B from dev; token statistics from train) · STATUS `[PRE-REGISTERED]` for the primary, `[CORRECTED]` for the two intervals below

> ⚑ **CONFLICT — two different intervals are on record for two of these
> quantities.** `RL:35` (2026-08-17) logged the **wider pool** as
> `+0.3017 [+0.2187, +0.3784]` and the **group-3 control** as
> `−0.0032 [−0.0454, +0.0429]`. Those were read from a **200-resample smoke
> run**. The correct values, from the final **10,000-resample** run in
> `token_stats.json`, are `+0.3017 [+0.2155, +0.3872]` and
> `−0.0032 [−0.0500, +0.0506]`. Both point estimates were correct; both
> corrected intervals are **wider**. The correction is recorded at `RL:39`;
> `RL:35` is left as written under the append-only rule. **Both values are
> printed here; neither is silently picked. The report must use the
> `token_stats.json` values.**

A rows are longer than B: mean 19.135593220338983 vs 14.40484714954558; median
16.0 vs 11. SRC `#sensitivities.token_count` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

Independent join checks: **6** of the 118 sit on lexicon-hit rows, exactly
matching Phase 02's separately-recorded `counts_lexicon_hit_47` NOPROF count of
6; and `aq` appears in **zero** of the 118.
SRC `RL:35` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Residual, stated as required:** **47 of the 118 (39.8%)** carry no strongly
skewed token at any vocabulary tested and remain unexplained.
SRC `RL:35`, `RL:40` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Composition of the effect — POST-HOC, no verdict field emitted.**

| subset | tokens | rows of 118 | difference (matched) | 95% CI |
|---|---|---|---|---|
| top-200 person/address deixis | 10 | 36 | +0.19648104569117925 | [+0.11491938918890132, +0.2837017401471388] |
| top-200 political/religious/identity | 2 (`oy`, `türk`) | 3 | +0.01107036022786898 | [−0.013803600059914406, +0.0437282947503795] |
| wider person deixis | 24 | 40 | +0.21059644954154347 | [+0.12628968494930826, +0.29818517629322805] |
| wider political/religious/identity | 26 | 23 | +0.14938212714727367 | [+0.08250771934787658, +0.2224235440700296] |

The token sets are disjoint but the rows are not — **9 of the 118 carry both**,
so the counts do not add.
SRC `RL:36`, `RL:40` · `#posthoc_exploratory.subsets` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

Five of the 19 group-2 tokens are second-person pronouns (`sen`, `senin`, `siz`,
`sizin`, `sizi`); ten of 19 are one address/deixis family (adding `lan`, `bak`,
`adam`, `bunlar`, `onlar`).
SRC `RL:36`, `RL:40` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[POST-HOC]`

**Class balance (descriptive):**

| split | overall | `lexicon_hit` | `lexicon_free` |
|---|---|---|---|
| train (26,992) | 0.193057 (1:4.18) | 3,404 rows, 0.553467 (1:0.81) | 23,588 rows, 0.141046 (1:6.09) |
| dev (4,764) | 0.193115 | 614 rows, 0.578176 | 4,150 rows, 0.136145 |

Slice-conditional prior ratio **3.92×**.
SRC `RL:37` · `#class_balance` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.7 Phase 08 — the `MIN_ROOT_LEN` blind spot (a bound, not a measurement)

Five karaliste entries are shorter than `MIN_ROOT_LEN = 3` (`ag`, `am`, `aq`,
`oc`, `oç`), so `hit_root` can never fire on them.

| quantity | value |
|---|---|
| gold-OFF `lexicon_free` dev rows | 565 |
| of which carrying a short entry | **28** (share 0.049558) |
| reported `lexicon_free` OFF-recall | 0.5628318584070796 (318/565) |
| upper-bound recall on the remainder | **0.540037** (290/537) |
| upper-bound gap | **+0.352921** |

SRC `RL:38` · `#posthoc_exploratory.min_root_len_blind_spot` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`, explicitly `is_a_bound_not_a_measurement: true`

### A2.8 Phase 09 Stage 1 — threshold-free slice comparison (ROC-AUC)

10,000 stratified bootstrap replicates, seed 42. Bands fixed in advance from a
Hanley–McNeil design calculation on the frozen denominators: LARGE 0.05,
SMALL 0.02.

| quantity | value | 95% CI |
|---|---|---|
| ROC-AUC `lexicon_hit` | 0.930611 | [0.910239, 0.949459] |
| ROC-AUC `lexicon_free` | 0.89615 | [0.882069, 0.909484] |
| **gap G** | **+0.034461** | **[+0.010261, +0.058517]** |

**Pre-registered verdict: `INTERMEDIATE`** — the interval excludes zero but G
falls in the 0.02–0.05 band declared inconclusive in advance.
SRC `RL:41` · `results/09_deeper_analysis/stage_1/stage1_auc.json#primary` · SCOPE `[DEV-ONLY]` (full dev) · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

> ⚑ **CONFLICT — two intervals on record for `lexicon_free` ROC-AUC.** Stage 1
> reports 0.89615 with CI **[0.882069, 0.909484]** (stratified bootstrap).
> Stage 1b's control arm reports the same point estimate 0.89615 with CI
> **[0.881992, 0.909395]** (paired bootstrap: rows resampled once per replicate,
> both systems scored on the same rows). The point estimates agree; the
> intervals differ because the resampling schemes differ. Both are printed; a
> report sentence must name which scheme it quotes.
> SRC `stage1_auc.json#primary.auc_lexicon_free_ci` vs `stage1b_defense_auc.json#slices.lexicon_free.auc_control_ci`

Score distributions, gold-OFF:

| slice | n | mean | Q1 | median | Q3 | share ≤ 0.5 |
|---|---|---|---|---|---|---|
| `lexicon_hit` | 355 | 0.85243 | 0.843863 | **0.96504** | 0.987183 | **0.107042** |
| `lexicon_free` | 565 | 0.528521 | 0.216247 | **0.586072** | 0.819269 | **0.437168** |

Gold-NOT: `lexicon_hit` n 259, mean 0.243809, median 0.105739, share ≤ 0.5
0.818533; `lexicon_free` n 3,585, mean 0.09991, median 0.031292, share ≤ 0.5
0.953696.
SRC `RL:41` · `#score_distributions` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

Average precision `lexicon_hit` 0.947725, `lexicon_free` 0.647942 — **C9-9:
base-rate sensitive, inadmissible to the verdict**.
SRC `RL:41` · `#average_precision` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

Sensitivities:

| sensitivity | AUC hit | AUC free | gap | shift vs primary |
|---|---|---|---|---|
| S1, `MIN_ROOT_LEN` leak removed (28 rows) | 0.930611 | 0.890749 | +0.039861 | +0.0054 |
| S1b symmetric — **NOT pre-registered** | 0.930611 | 0.890749 | +0.039862 | — |
| **S2, suspect-root rows removed (248)** | 0.902313 | 0.89615 | **+0.006164** | **−0.028297** |
| S3, tie credit 0 | 0.930611 | 0.896149 | +0.034461 | — |
| S3, tie credit 1 | 0.930611 | 0.89615 | +0.034461 | — |

SRC `RL:41` · `#sensitivities` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]` (except S1b, tagged `NOT PREREGISTERED` in the file itself)

The four **matched-operating-point** figures — `lexicon_free` recall 0.968141592920354
[0.950442, 0.982301] at `lexicon_hit`'s flagging rate 0.5928 (precision
0.22235772357723577); 0.2088495575221239 [0.077876, 0.284956] at matched
precision; and the two reverse-direction figures (`lexicon_hit` recall
0.9915492957746479 at matched precision, and flag rate 0.11726384364820847 at
precision 0.9861111111111112) — arise from a **defective specification** and
**do not enter the report**. See D §D.5.
SRC `RL:41`, `RL:43` · `#matched_operating_points` · SCOPE `[DEV-ONLY]` · STATUS `[SUPERSEDED]`

### A2.9 Phase 09 Stage 1b — the intervention's gain is threshold crossing

Control `run_raw` (sha256 `a2f5bddf…a6346`, byte-identical to the Phase-01 dump);
treatment `run_1a1b_d` (sha256 `e525eaabeaf30f55469bf9a16e13ed9363b1a72b04f9adbada01b59ade6bbd4a`).
Paired bootstrap, 10,000 replicates, seed 42. Pre-registered SMALL_DELTA floor **0.01**.

| slice | AUC control | AUC treatment | ΔAUC | 95% CI | verdict |
|---|---|---|---|---|---|
| `lexicon_free` (PRIMARY) | 0.89615 | 0.890562 | **−0.005587** | **[−0.013387, +0.002366]** | **`FLAT`** |
| `lexicon_hit` (CONTROL) | 0.930611 | 0.90521 | **−0.025401** | **[−0.042863, −0.008646]** | **`ORDERING WORSENED`** |

Treatment CIs: `lexicon_free` [0.87508, 0.905164]; `lexicon_hit`
[0.880434, 0.928512].
SRC `RL:44` · `results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json#slices` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

**The whole reported dev effect is 19 rows crossing the threshold.**

| slice / gold | NOT→OFF | OFF→NOT | net |
|---|---|---|---|
| `lexicon_free`, gold OFF | 52 | 33 | **+19** (19/565 = +0.0336283) |
| `lexicon_free`, gold NOT | 83 | 54 | +29 |
| `lexicon_hit`, gold OFF | 13 | 28 | **−15** (−15/355 = −0.0422535) |
| `lexicon_hit`, gold NOT | 14 | 11 | +3 |

Gold-NOT nets +29 and +3 sum to +32, matching the recorded 213 → 245 false
positives. Both recall deltas are reproduced exactly to ten decimals.
SRC `RL:44`, `RL:46` · `#slices.*.crossings_gold_OFF, .crossings_gold_NOT` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

**The movement is polarisation, not a uniform shift.** `lexicon_free` gold-OFF:
median 0.586072 → **0.78176**, Q1 **falls** 0.216247 → 0.077588, Q3 rises
0.819269 → **0.992129**; share ≤ 0.5 0.437168 → 0.40354. `lexicon_hit` gold-OFF:
median 0.96504 → 0.996745, Q1 0.843863 → 0.938349, share ≤ 0.5 0.107042 → 0.149296.
SRC `RL:44`, `RL:46` · `#slices.*.score_distribution_control, .score_distribution_treatment` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Slice AUC gap narrows +0.034461 → +0.014648** (delta −0.019813), driven by
`lexicon_hit` falling 0.930611 → 0.90521, not by `lexicon_free` rising — it fell
too, to 0.890562.
SRC `RL:44`, `RL:46` · `#slice_auc_gap` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### A2.10 Phase 11 Run A — the sub-threshold band is base-rate-correct

`cal_eval_split.json` sha256 `6d1e3ed7…af899`. Bootstrap 10,000 replicates, seed
42, stratified over the four EVAL cells **182 / 127 / 278 / 1795**, band
membership recomputed inside each replicate.

**PRIMARY (C11-4), `SG_free_low`** — signed calibration gap over EVAL
`lexicon_free` rows with p_OFF < 0.5:

| quantity | value |
|---|---|
| signed gap | **−0.004566951787648971** |
| 95% CI | **[−0.01280704635421828, +0.0035463379479318186]** |
| realized n | **1,846** (design projection 1,831) |
| gold-OFF in band | 134 |
| empirical OFF rate in band | 0.07258938244853738 |
| mean p_OFF in band | 0.07715633423618634 |
| ECE(10) in band | 0.013283245395449634 |
| realized half-width | **±0.00817669215107505** (design ±0.0115) |
| rows at p_OFF = 0.5 exactly | 0 |
| **branch 2 → VERDICT** | **`BASE-RATE-CORRECT`** |

C11-4 identity verified: binned = closed form, absolute difference ≤ 1e-12
(closed form −0.00456695178764896).
SRC `RL:47` · `results/11_prior_correction/metrics.json#primary` · SCOPE `[DEV-ONLY]` (EVAL half) · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

Descriptive, EVAL, 10 bins:

| slice | n | gold OFF | base rate | mean p | ECE(10) | whole-slice SignedGap |
|---|---|---|---|---|---|---|
| `lexicon_free` | 2,073 | 278 | 0.13410516160154365 | 0.14934360154365656 | **0.023000272069464558** | −0.015238439942112882 |
| `lexicon_hit` | 309 | 182 | 0.5889967637540453 | 0.5769836375404531 | **0.0313912168284789** | +0.012013126213592287 |

SRC `RL:47` · `#descriptive` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[DESCRIPTIVE, NO CI]`

Calibration-fairness gap ECE_hit − ECE_free = **+0.008390944759014345**,
95% CI [−0.00016516026711894084, +0.05287089302556213], bootstrap mean
**+0.025100061787565985**. The file records in its own text that binned ECE is
positively biased in small samples, so the percentile interval is **not centred
on the point estimate and is not trustworthy as a location estimate**.
SRC `RL:47` · `#calibration_fairness_gap` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[PRE-REGISTERED]`

C11-11 S1 bin-count sensitivity: ECE `free` 0.0230 / 0.0284 / 0.0290 and `hit`
0.0314 / 0.0572 / 0.0585 at 10 / 15 / 20 bins; SignedGap bin-count invariant.
SRC `RL:47` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

Two items recorded, **neither promoted**:

1. Observed `SG_global` on EVAL is **−0.0117**; of the observed `SG_free` =
   −0.0152 about −0.0135 is the global term and ≈ −0.0018 is slice structure.
   Whole-slice `SG_free` = −0.0152 [−0.0236, −0.0070] excludes zero and **C11-13
   forbids promoting it** in place of a branch-2 primary.
   SRC `RL:47` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`
2. **Post-hoc, exploratory, no verdict:** every `lexicon_free` bin above 0.4
   carries a negative gap, largest at [0.8, 0.9) (**−0.179**) and [0.9, 1.0)
   (**−0.138**); arithmetic on the rounded bins puts mean predicted probability
   in the flagged region near **0.74** against an empirical rate near **0.63**.
   Recorded as **not a finding** without a pre-registered test.
   SRC `RL:47` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

Addendum-1 correction to the above bin figures: the actual `lexicon_free` gaps
above 0.5 are **−0.1362, −0.0140, −0.0334, −0.1791, −0.1375**; C12-1's summary
"−0.13 to −0.18" over-stated them. See D §D.8.
SRC `phases/12_threshold_policy.md` Addendum 1 item 4 @ `584292c` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### A2.11 Phase 12 — a single cost-derived threshold is sufficient

Four systems, all thresholds fitted on CAL, all scored on EVAL. Cost
`(FP + r·FN)/N`, primary `r = 3`, frontier `r ∈ {1, 2, 3, 5, 10}`. Paired
bootstrap 10,000 replicates, seed 42, stratified over the four EVAL cells
182 / 127 / 278 / 1795; thresholds fixed by CAL per C12-6.

Provenance gate: 25 checks, all eight Phase-01 figures, dev fingerprint
`034415af3a23b388`, `cal_eval_split.json` sha256 `6d1e3ed7…af899`. C12-4
correctness check PASS: `t*(r=1) = 0.5` exactly, and S1a reproduces S0's EVAL
confusion exactly (tp 302 / fp 100 / fn 158 / tn 1822, n_flagged 402,
n_gold_off 460).

**PRIMARY (C12-5), S2 vs S1b at r = 3:**

| quantity | value |
|---|---|
| ΔCost_rel | **+0.04112149532710281** |
| 95% CI | **[−0.0159585106382979, +0.1048387096774194]** |
| discordant EVAL rows d | **80** (79 of 80 in `lexicon_free`) |
| realized relative half-width | **0.06039861015785865** |
| Cost_S1b | 0.22460117548278757 (tp 343 / fp 184 / fn 117 / tn 1738) |
| Cost_S2 | 0.23383711167086482 (tp 318 / fp 131 / fn 142 / tn 1791) |
| branch 5 reachable at this resolution | **true** |
| **branch 2 → VERDICT** | **`SINGLE-THRESHOLD-SUFFICIENT`** |

SRC `RL:49` · `results/12_threshold_policy/metrics.json#primary` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

Fitted thresholds on CAL:

| r | S1a analytic | S1b | S2 `t_hit` | S2 `t_free` |
|---|---|---|---|---|
| 1 | 0.5 | 0.584312 | 0.494651 | 0.584312 |
| 2 | 0.3333333333333333 | 0.507305 | 0.415888 | 0.507305 |
| **3** | **0.25** | **0.320188** | **0.303421** | **0.439296** |
| 5 | 0.16666666666666666 | 0.211486 | 0.096532 | 0.211486 |
| 10 | 0.09090909090909091 | 0.101077 | 0.096532 | 0.107818 |

**C12-3 internal control: the fitted single threshold exceeds the analytic `t*`
at every r.** S1a is cheaper at r = 3 only; S1b is cheaper at r = 1, 2, 10.
SRC `RL:49` · `#fitted_thresholds_CAL`, `#descriptive.frontier` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

**C12-9 threshold stability** (refit inside 10,000 CAL bootstrap replicates,
r = 3):

| threshold | median | Q25 | Q75 | IQR | p5 | p95 | boot min | boot max |
|---|---|---|---|---|---|---|---|---|
| `t_hit` | 0.303421 | 0.292172 | 0.415888 | **0.123716** | 0.129509 | 0.494651 | 0.070504 | 0.69867 |
| `t_free` | 0.423573 | 0.349156 | 0.456957 | 0.107801 | **0.299916** | **0.509108** | 0.165745 | 0.584312 |

The C12-9 instability rule is IQR of `t_hit` against a limit of 0.20; observed
0.123716, so **S2 is not flagged unstable**. The rule "may qualify the verdict;
may not overturn it".
SRC `RL:49` · `#threshold_stability_C12_9` · SCOPE `[DEV-ONLY]` (CAL) · STATUS `[PRE-REGISTERED]`

**C12-8 descriptive frontier at r = 3, EVAL — pre-registered as descriptive,
with no intervals:**

| system | cost | OFF-recall | `free` recall | `hit` recall | gap | OFF-precision | rows flagged |
|---|---|---|---|---|---|---|---|
| S0 (0.5) | 0.240974 | 0.656522 | 0.517986 | 0.868132 | +0.350146 | 0.751244 | 402 |
| **S1a (t\* = 0.25)** | **0.220823** | **0.786957** | **0.690647** | 0.934066 | **+0.243418** | **0.609428** | 594 |
| S1b (0.320188) | 0.224601 | 0.745652 | 0.636691 | 0.912088 | +0.275397 | 0.650854 | 527 |
| S2 (0.303421 / 0.439296) | 0.233837 | 0.691304 | 0.546763 | 0.912088 | **+0.365325** | 0.708241 | 449 |

SRC `RL:49` · `#descriptive.frontier.3` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[PRE-REGISTERED]`, `[DESCRIPTIVE, NO CI]`

**SENS-2** (`MIN_ROOT_LEN` leak; 28 rows dropped full dev — 18 CAL, 10 EVAL —
matching the pre-registered count): ΔCost_rel **+0.04112149532710269**, CI
[−0.014598540145985385, +0.10429622472381], d = 80, half-width 0.059447382434897694,
verdict `SINGLE-THRESHOLD-SUFFICIENT`. Reproduces the primary to six decimals.

**SENS-3** (suspect-root contamination; 248 rows dropped full dev — 119 CAL, 129
EVAL): d = **23** → **branch 0, `INSUFFICIENT`**; point estimate
**−0.02471482889733837**, CI [−0.05984642683744477, +0.007952286282306134] —
**opposite in sign to the primary**. Fitted thresholds shift to S1b 0.439296,
`t_hit` 0.078505, `t_free` 0.439296.
SRC `RL:49` · `#sensitivities_C12_11` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]` (SENS-3 is a second `INSUFFICIENT`, see E §E.3)

Descriptive matched-flag-count view (labelled `descriptive_only`, `no_verdict`):
S1b's CAL flag count at r = 3 is 594; S2 reaches exactly 594 at r' = 3.334,
difference 0, achieved at 866 grid points.
SRC `#descriptive.matched_flag_count_view` · SCOPE `[DEV-ONLY]` (CAL) · STATUS `[DESCRIPTIVE, NO CI]`

### A2.12 Phase 12 / C12-16 — intervals on the S1a-vs-S0 headline

Computed **after** the point estimates were published. Both arms zero-parameter,
so the C12-6 caveat about excluded threshold-selection variance does **not**
apply. Paired nonparametric bootstrap, stratified over the four EVAL cells
182 / 127 / 278 / 1795, 10,000 replicates, seed 42, percentile, α = 0.05.

| quantity | point estimate | 95% CI | half-width | boot SE |
|---|---|---|---|---|
| `d_recall` | +0.13043478260869568 | [+0.10000000000000009, +0.16086956521739137] | 0.030434782608695643 | 0.015428721980963178 |
| `d_recall_free` | +0.17266187050359716 | [+0.1294964028776978, +0.21942446043165464] | 0.044964028776978415 | 0.022639408602634314 |
| **`d_gap`** | **−0.10672780456953124** | **[−0.1629773104593249, −0.0483832714048541]** | 0.0572970195272354 | 0.029357504354971115 |
| `d_precision` | −0.14181617166691796 | [−0.172253772633705, −0.113144552676357] | 0.029554609978674005 | — |

All four exclude zero.
SRC `RL:50` · `results/12_threshold_policy/c12_16_intervals.json#intervals` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[POST-HOC]` (quantities fixed in advance by C12-8 and C12-4; **uncertainty computed late**), `[DESCRIPTIVE, NO CI]` no longer applies to these four

**Structural determination, recorded on the figures themselves:** because
`t*(r = 3) = 0.25 < 0.5`, S1a's flagged set **strictly nests** S0's — verified
directly, **zero rows flagged by S0 but not S1a**. S0 catches 302 of 460 EVAL
gold-OFF and flags 402; S1a catches 362 and flags 594. Realized discordant
gold-OFF count **exactly 60**, matching the design figure. The recall gain split
**48 of 278** free against **12 of 182** hit.
SRC `RL:50` · `#discordance`, `#arms_on_EVAL` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

Point-estimate reproduction against the committed run: largest absolute
deviation **2.17e-07** against a six-decimal tolerance of 5e-07; no flags.
SRC `RL:50` · `#point_estimate_reproduction` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

Arms on EVAL: S1a OFF-recall 0.7869565217391304, free 0.6906474820143885, gap
0.24341845205154555, precision 0.6094276094276094; S0 0.6565217391304348,
0.5179856115107914, 0.3501462566210768, 0.7512437810945274.
SRC `#arms_on_EVAL` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.13 Phase 15 step 1 — address-flag cell counts (counts only)

No calibration quantity, no signed gap, no ECE, no AUC, no recall and no verdict
exists for Phase 15. See E §E.4.

Matching rule: **exact token match** against `src.lexicon.tokens()` output —
**not** `hit_root`, **not** prefix matching. Primary set 7 tokens
(`sana, sen, senin, siz, size, sizi, sizin`), from Stage 4 of
`phases/09_deeper_analysis.md`. Sensitivity sets: extended 20 tokens,
third-person deictic 5 tokens (`lan, bak, adam, bunlar, onlar`).

Address prevalence:

| half | slice | full slice | share | in band (p_OFF < 0.5) | share |
|---|---|---|---|---|---|
| EVAL | `lexicon_free` | 235 / 2,073 | 0.11336227689339122 | 177 / 1,846 | **0.09588299024918744** |
| EVAL | `lexicon_hit` | 63 / 309 | 0.20388349514563106 | **22 / 134** | 0.16417910447761194 |
| CAL | `lexicon_free` | 234 / 2,077 | 0.11266249398170439 | 172 / 1,820 | 0.0945054945054945 |
| CAL | `lexicon_hit` | 50 / 305 | 0.16393442622950818 | 17 / 116 | 0.14655172413793102 |

EVAL 8 cells, primary token set, as (n, of which in band):

| cell | n | in band |
|---|---|---|
| `lexicon_free` × address × OFF | 59 | 21 |
| `lexicon_free` × address × NOT | 176 | 156 |
| `lexicon_free` × no_address × OFF | 219 | 113 |
| `lexicon_free` × no_address × NOT | 1,619 | 1,556 |
| `lexicon_hit` × address × OFF | 46 | 8 |
| `lexicon_hit` × address × NOT | 17 | 14 |
| `lexicon_hit` × no_address × OFF | 136 | 16 |
| `lexicon_hit` × no_address × NOT | 110 | 96 |

Zero rows at p_OFF = 0.5 exactly in every cell, both halves, all three token
sets. EVAL and CAL slice and band totals reproduce Phase 11 Run A and C11-2
exactly (EVAL by-slice-by-gold 182 / 127 / 278 / 1795; EVAL `lexicon_free` band
1,846; EVAL `lexicon_hit` band 134).

SRC `RL:53` · `results/15_deixis/cell_counts.json#counts.EVAL.primary`, `#counts.CAL.primary` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

Generated at git HEAD `5ba53cdce45525dc3aadf32df7d77989dd4eb42d`,
2026-08-18T14:53:53+00:00, Python 3.14.0.
SRC `#environment` · SCOPE `[DEV-ONLY]`

### A2.14 Phase 06 — offline demo

Asset bundle **885.9 MB**: two 442.5 MB fp32 checkpoints (raw, +1a+1b+D), 0.8 MB
tokenizer, the 695-entry lexicon, and the frozen operating point (threshold
**0.6632**). Two consecutive cold starts of both the selftest and the live HTTP
server: byte-identical output. Hostile input set (empty, whitespace, emoji-only,
English, 100k chars, control characters, XSS payload, malformed JSON POST) all
handled. **110 tests pass** at that commit.
SRC `RL:31` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### A2.15 Test-suite counts through the project

110 (Phase 06) → 150 (Phase 09 Stage 1, 24 new tests) → 416 (after the Phase 12
run; 38 new tests were added at Phase 15 step 1). Suite at the current HEAD:
**416 passed, 0 failed**.
SRC `RL:31`, `RL:41`, `RL:49`, `RL:53` · observed `python -m pytest -q` at `9d3c8c6` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

---

# B. PROVENANCE CHAIN

Every pre-registration and addendum commit, in order. Dates are author dates.

| # | SHA | date | what it specified or fixed | before / after |
|---|---|---|---|---|
| 1 | `c33d1bd` | 2026-08-15 | Project scaffold + ported Day 1 lexicon logic | first commit; before it, nothing |
| 2 | `197d953` | 2026-08-15 | **Phase 1 scaffold + pre-registrations**: split, metrics, BERTurk training. Contains the pre-registered decision rule (three outcomes on the gap CI) and the pre-registered constraint that per-slice comparison is **OFF-recall only** | after `41a2a7f`/`a3c4eb4`; **before any BERTurk number existed** |
| 3 | `837c351` | 2026-08-15 | Hard GPU gate before training; mirror refuses to lose `dev_predictions.csv`. This is the commit recorded in `metrics.json#git_sha` for the baseline run | before `685d4af` |
| 4 | `685d4af` | 2026-08-15 | Phase 01 result: gap survives (outcome 1) | after the run |
| 5 | `3063681` → `a500d08` | 2026-08-15 | Phase 02 failure analysis, then Phase 02 close (slice-contamination sensitivity, convention ruling) | between Phase 01 and Phase 03 |
| 6 | `5203ec5` → `9aa00cd` → `00b9139` → `00c6521` → `e92d306` | 2026-08-15 | Phase 03 steps 1–4 and results | before Phase 04 |
| 7 | **`ab225ad`** | 2026-08-16 | **Phase 04 pre-registration**: CAL/EVAL split, ECE definition, operating-point protocol; registers the temperature-invariance prediction | **committed before any calibration number existed**; followed by `7242352` (module) then `8012c71` (results) |
| 8 | `4ee938f` → `9af62f9` → `5604586` → `f918ba7` | 2026-08-16 | Phase 05: single-use accounting, the `Tee` fix after the first aborted open, results, paired deltas | `9af62f9` is the commit recorded in `results/05_final_test/metrics.json#git_sha` |
| 9 | `19ce53c` | 2026-08-16 | Correction to the Phase 03 framing: the component works, the system does not | after the Phase 05 test measurement |
| 10 | `5207fa6` → `e02b6ee` | 2026-08-16 | Phase 06 offline demo and its verification record | — |
| 11 | `05de1fa` | 2026-08-16 | Phase 07: report outline and evidence map; four gaps flagged | — |
| 12 | `8691303` | 2026-08-16 | Continuation brief + **recovery of the Phase 03 machine-readable evidence** | see D §D.4 |
| 13 | **`b127d44`** | 2026-08-17 | **Phase 08 pre-registration** — word-level lexical dependence (committed as `phases/06_…`, later renumbered because the demo already held 06). Declares document-frequency counting, top-200 pool, binomial z primary, excess-OFF-rows secondary, \|z\| ≥ 3.6623, 1.5× effect floor, `hit_root` for membership, and the matched-comparison design | **before any token count existed**; followed by `7ef51a0` (results) then `4fb4132` (promotion + two CI corrections) |
| 14 | `bcb4b70` | 2026-08-17 | Phase 09 spec placed as received (six stages, staged authorisation) | before the Stage 1 pre-registration |
| 15 | **`12afa74`** | 2026-08-17 | **Phase 09 Stage 1 pre-registration** (C9-1…C9-11): AUC primary, LARGE 0.05 / SMALL 0.02 from a Hanley–McNeil design calculation on frozen denominators | **before any number existed**; followed by `120eead` (results) |
| 16 | **`910d21e`** | 2026-08-17 | **C9-8 spec-defect addendum + Stage 1b pre-registration** (C9-12…C9-17), including the four-branch rule, the 0.01 floor and the C9-16 control prediction | after Stage 1 results; **before any Stage 1b number existed** |
| 17 | `6b4a451` | 2026-08-17 | Narrow the central claim in the report; Stage 1b coded but **BLOCKED** (Drive mount failed unattended twice) | recorded in `stage1b_defense_auc.json#git_sha` |
| 18 | `09ce5f8` → `1db1354` | 2026-08-17 | Stage 1b results, then the report narrowing applied to §4.6, §4.7, §5.4 | — |
| 19 | `c67eabe`, `98e27c1`, `b902c32` | 2026-08-17/18 | Phase 10 KYS coverage map; PROJECT_HISTORY; repo inventory snapshot | documentation, no measurement |
| 20 | **`d589dbad`** | 2026-08-18 | **Phase 11 pre-registration** (C11-1…C11-14) **+ the frozen CAL/EVAL split**. Includes the C11-7 verdict rule, the C11-4 identity, and the C11-12 recorded prediction | **before any Phase 11 number existed**; the `cal_eval_split.json` blob is `108599c280162ab3ad17a283d0e59a464e665031` |
| 21 | **`a96f02d`** | 2026-08-18 | **Phase 11 Run A results**: `BASE-RATE-CORRECT`; C11-12 prediction **failed** | immediately after `d589dbad` |
| 22 | **`5ba53cd`** | 2026-08-18 | **Phase 11 addendum**: C11-2's self-hash clause is defective (a file cannot contain its own digest). Original left intact; the digest is recorded outside the file in three places | immediately after `a96f02d`; this is the HEAD recorded in `cell_counts.json#environment.git_head` |
| 23 | `95d20de` | 2026-08-18 | **Phase 15 frozen address flag** (Stage 4 seven-token set, exact match): `.gitignore` exception, `data/deixis/address_tokens.json`, `src/phase15_deixis.py`, `tests/test_phase15_address.py`. **Did not contain `cell_counts.json`** — see D §D.7 | after `5ba53cd`, before `ec2fd3a7` |
| 24 | **`ec2fd3a7`** | 2026-08-18 | **Phase 12 pre-registration** (C12-1…C12-15): slice-conditional vs single cost-optimal threshold. One file, 366 insertions | **before any Phase 12 number existed** |
| 25 | **`584292c`** | 2026-08-19 | **Phase 12 Addendum 1** — defects recorded, C12-1…C12-15 intact: (1) S1/S2 naming collision → SENS-1/2/3; (2) `Cost_S1b ≈ 0.27` wrong arithmetic, SE denominator corrected; (3) the corrected table under-powers branch 5, declared not corrected; (4) "bins above 0.5 run −0.13 to −0.18" over-states Run A; (5) C12-9's Phase 15 citation pointed at a document that does not exist | after `ec2fd3a7`, before any Phase 12 number |
| 26 | `e44b19a0` | 2026-08-19 | **Phase 15 step 1 cell counts committed** — `results/15_deixis/cell_counts.json`, sha256 `facd3544…210a` | between Addendum 1 and Addendum 2 |
| 27 | **`2b4391bf`** | 2026-08-19 | **Phase 12 Addendum 2** — two corrections to Addendum 1: (a) the heading says "four defects", the body numbers five; the correct count is **five**; (b) Addendum 1 item 5's locator `95d20de4` was wrong — the counts file resolves to `e44b19a0` | after `e44b19a0`; still before any Phase 12 number |
| 28 | **`d74acd93`** | 2026-08-19 | **Phase 12 results**: `SINGLE-THRESHOLD-SUFFICIENT`; C12-10's prediction **held**. Carries the four S1a-vs-S0 quantities as **bare point estimates** | after Addendum 2 |
| 29 | **`b0f2b0b5`** | 2026-08-19 | **Phase 12 Addendum 3 / C12-16** — authorises intervals on the S1a-vs-S0 headline, **committed after `d74acd93`**. The ordering is the point: the quantities were fixed in advance, the uncertainty was computed late | **after** the point estimates were published |
| 30 | **`355d6b18`** | 2026-08-19 | C12-16 interval results | after `b0f2b0b5` |
| 31 | **`3bc0d2e`** | 2026-08-19 12:10:08 +0300 | **Byte-stability**: created `.gitattributes` (`* -text`, 284 bytes) and renormalised 19 files (+79,013 / −79,008), so that committed blobs are byte-identical to working copies and **no recorded digest changed** | after `355d6b18` |
| 32 | `f451777` | 2026-08-19 12:17:17 +0300 | `RL:51` — the EOL limitation recorded as **deferred**. **False at this commit**; see D §D.9 | 7 minutes after `3bc0d2e` |
| 33 | `9d3c8c6` | 2026-08-19 12:31:51 +0300 | `RL:52` (correction superseding `RL:51`) and `RL:53` (the missing Phase 15 step 1 row) | current HEAD |

SRC `git log --oneline --all`, `git log -1 --format='%h %ad %s'` per commit, `git show --stat 3bc0d2e`, `phases/*.md` addendum headings · SCOPE `[DEV-ONLY]` (no test-set involvement in any commit after `f918ba7`) · STATUS `[DESCRIPTIVE, NO CI]`

**Pre-registration files, as committed:** `phases/01_baseline_diagnosis.md`,
`03_defense_design.md`, `04_calibration.md`, `07_report.md`,
`08_lexical_analysis.md`, `09_deeper_analysis.md`, `10_sablon_mapping.md`,
`11_prior_correction.md`, `12_threshold_policy.md`. **There is no
`phases/15_*.md`.**

---

# C. PREDICTIONS

Every recorded prediction, with its outcome. Both directions.

### C.1 Phase 04 — risk-coverage is invariant to temperature scaling — **HELD**

Registered in `phases/04_calibration.md` @ `ab225ad`, stated as the reason a
false "calibration improved selective prediction" claim cannot be made by
accident. Observed: invariance verified **exactly**, max absolute difference
**0.00e+00**, both variants.
SRC `RL:21`, `RL:23` · `results/04_calibration/calibration.json#variants.*.rc_invariance_check` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.2 Phase 04 — the 6dp rounding limitation would bind — **DID NOT BIND**

Registered in advance that 6dp dumps may compress the extreme logit tail.
Observed: **zero saturated rows** in either variant, dev / CAL / EVAL. Reported
as such rather than dropped.
SRC `RL:21`, `RL:22` · `#variants.*.saturated_rows` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.3 Phase 08 — the interpretation was registered both ways — **SUPPORT fired**

`phases/08_lexical_analysis.md` @ `b127d44` registered that SUPPORT requires a
positive difference whose CI excludes zero, and that anything else is NO
SUPPORT. Observed on the pre-registered primary: **+0.2066
[+0.1216, +0.2960] → SUPPORT**.
SRC `RL:33`, `RL:35` · `#step3.verdict` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

### C.4 Phase 08 — the advisor's content hypothesis (political/identity) — **FAILED at the registered resolution**

At the top-200 band only two such tokens exist (`oy`, `türk`) and they show
**+0.0111 [−0.0138, +0.0437] — NO SUPPORT**. The effect emerges only after
widening the vocabulary to df ≥ 30 (26 tokens, +0.1494 [+0.0825, +0.2224]), and
even there person deixis is the larger contributor (40 rows vs 23).
SRC `RL:36`, `RL:40` · `#posthoc_exploratory.subsets` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]` for the subsetting; the top-200 band result is at the pre-registered resolution

### C.5 Phase 09 Stage 1 — the C9-4 design calculation predicted the resolution — **HELD**

The design predicted ±0.03–0.04 for denominators 355/259 and 565/3585. Observed:
the CI **spans all three pre-registered bands**, exactly that resolution.
SRC `RL:41` · `phases/09_deeper_analysis.md` C9-4 @ `12afa74` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.6 Phase 09 Stage 1b — C9-16's control prediction — **FAILED**

C9-16 predicted, before the run, that a global score shift would leave
`lexicon_hit` AUC **flat** while its recall fell. Observed: ordering there
measurably **worsened** — ΔAUC −0.025401 [−0.042863, −0.008646], interval
excludes zero, verdict `ORDERING WORSENED`.
SRC `RL:44` · `stage1b_defense_auc.json#slices.lexicon_hit` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

C9-14 named overconfidence (fitted T = 1.9731501284219068 vs 0.9948165193869881,
ECE 3.8×) as the likely mechanism **before** the run; it is reported as
**consistent with**, explicitly **not** as demonstrated by.
SRC `RL:44`, `RL:46` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.7 Phase 11 — C11-12's recorded prediction — **FAILED**

Recorded before the number: "`SG_free_low` will be positive but below 0.05 —
branch 4, `INTERMEDIATE` — and the substantive content will be in the shape of
the reliability curve rather than in the mean."

Observed: **−0.004566951787648971**, branch **2**, verdict `BASE-RATE-CORRECT`.
**Wrong side of zero and the wrong branch.** `prediction_held: false`.
SRC `RL:47` · `results/11_prior_correction/metrics.json#prediction_C11_12` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

### C.8 Phase 11 — the Surana pattern would replicate — **NOT REPLICATED**

Our calibration-fairness gap **+0.0084 [−0.0002, +0.0529]** against Surana's
**+0.029…+0.134 with every subgroup CI excluding zero**. A slice defined by
profanity-lexicon membership does not inherit the miscalibration that
identity-defined subgroups show.
SRC `RL:47` · `#calibration_fairness_gap.comparable_to` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.9 Phase 12 — C12-10's recorded prediction — **HELD**

Recorded: "ΔCost_rel falls inside SMALL — branch 2 or 3,
`SINGLE-THRESHOLD-SUFFICIENT`." Observed: branch **2**, verdict
`SINGLE-THRESHOLD-SUFFICIENT`. `held: true`.
SRC `RL:49` · `results/12_threshold_policy/metrics.json#prediction_C12_10` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

### C.10 Phase 12 — Addendum 1 item 3 predicted branch 5 would be unreachable — **DID NOT BIND**

Addendum 1 declared the corrected power table under-powers branch 5 and
deliberately did **not** move the band, requiring instead that the run report
the realized `d` and half-width. Observed: realized d = 80, realized relative
half-width **0.0604**, below the LARGE band 0.10 — **branch 5 was reachable**.
SRC `RL:49` · `#primary.resolution_C12_7_addendum1_item3` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.11 Phase 12 — C12-3's internal control on the Elkan argument — **DIVERGED**

C12-3 set up the fitted-vs-analytic threshold comparison as a control on C12-1's
theory, with the stated consequence that a material divergence **weakens** the
Elkan argument. Observed: the fitted threshold exceeds the analytic `t*` at
**every** r (0.584/0.500, 0.507/0.333, 0.320/0.250, 0.211/0.167, 0.101/0.091).
Per C12-3's own terms this weakens rather than confirms.
SRC `RL:49` · `#fitted_thresholds_CAL` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### C.12 Phase 15 — the controller's projected address prevalence — **CAME IN BELOW**

Projected 10–20% of the `lexicon_free` band. Realized **9.6%** (177/1,846),
giving a design half-width on the primary contrast of **±0.049 on EVAL alone**
and a pooled half-width of **±0.034**.
SRC `RL:53` · `results/15_deixis/cell_counts.json#counts.EVAL.primary.prevalence` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

---

# D. CORRECTIONS AND DEFECTS

Every CORRECTION, SPEC DEFECT, LIMITATION and addendum row, with what was wrong
and what replaced it.

### D.1 Day-1 annotation-noise estimate corrected (Phase 02)

**Wrong:** ~30–35% of the `lexicon_free` slice is annotation noise, carried as a
limitation on the Phase-01 headline.
**Replaced by:** ~10%. The Day-1 figure was a methodological artifact of
confidence-sorting — reading the most-confidently-wrong rows selects for label
noise, so that estimate cannot be generalised to the slice.
SRC `RL:15#stated_limitation`, `RL:16` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### D.2 CORRECTION to the Phase 03 framing (2026-08-16, `19ce53c`)

**Wrong:** the heading treated the `lexicon_free` gain as cancelled by an equal
and opposite `lexicon_hit` loss — the honest reading of dev alone, where the
loss (−0.0423 [−0.0778, −0.0109]) excluded zero.
**Replaced by:** "the component works, the system does not." On test the same
loss is −0.0260 [−0.0593, +0.0077] and does not reach significance; the cost
appears instead as a diffuse precision penalty (−0.0127 [−0.0397, +0.0109]).
**Unchanged and not softened:** 1b failed its own stated purpose (`lexicon_hit`
FP rate rose 0.1815 → 0.1931; +30 no-profanity FPs), and the variant is badly
miscalibrated. Earlier rows left as written.
SRC `RL:29` · `results/03_defense/findings.md` verdict section (superseded wording quoted in place) · SCOPE `[TEST]` and `[DEV-ONLY]` (the correction spans both) · STATUS `[CORRECTED]`, `[SUPERSEDED]` for the original wording

### D.3 Dev-to-test gap-widening: what is and is not established

`lexicon_hit` recall **rose** 0.8929577464788733 → 0.9070631970260223 (+1.4pp);
`lexicon_free` recall **fell** 0.5628318584070796 → 0.5100671140939598 (−5.3pp);
gap +0.3301 → +0.3970 (+6.7pp). **The dev and test intervals OVERLAP over
[+0.3418, +0.3827], so the widening itself is NOT an established difference.**
Both statements are to be reported together.
SRC `RL:25`, `RL:30` · SCOPE `[TEST]` (test values) and `[DEV-ONLY]` (dev values) · STATUS `[CORRECTED]` (records a reading, adds no measurement)

### D.4 Evidence-completeness defect — Phase 03 machine-readable records were missing

**Wrong:** `phase03_compare.py` writes to the results directory but has no mirror
step, so `comparison.json`, `train_oof_summary.json` and the four
`run_*/metrics.json` lived only in an ephemeral Colab clone.
**Replaced by:** regeneration from the four saved dev prediction dumps on the
Drive mirror at a fixed seed. Regenerated deltas reproduce the published table
exactly. Recorded as a recovery, not a re-measurement.
SRC `RL:32` · commit `8691303` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### D.5 SPEC DEFECT — Phase 09 C9-8 (matched operating points)

**Wrong:** C9-8 described matched precision and matched flagging rate as "two
different ways of removing the threshold confound."
**What is actually true:** they remove the **threshold** confound and leave the
**base-rate** confound fully intact. Precision depends on the base rate
directly; recall at a fixed flagging rate does too. Between slices at 57.8% and
13.6% neither comparison can be evidence about ranking quality.
**Consequence:** four figures **withdrawn as evidence** and barred from the
report (0.9681, 0.2088, and the two reverse-direction figures). They stay in
`stage1_auc.json` and in the stage findings, labelled as arising from a
defective specification. **ROC-AUC survives intact as the only base-rate-free
comparison in the stage.**
**Discipline:** C9-8 left exactly as committed; a dated addendum in
`phases/09_deeper_analysis.md` states the defect.
SRC `RL:43` · `phases/09_deeper_analysis.md` "Addendum, 2026-08-17 — C9-8 was defective" @ `910d21e` · SCOPE `[DEV-ONLY]` · STATUS `[SUPERSEDED]`

### D.6 New limitation — the `MIN_ROOT_LEN` blind spot

**Wrong (as an unstated assumption):** that `hit_root` can fire on every
karaliste entry.
**What is actually true:** five entries are shorter than `MIN_ROOT_LEN = 3`
(`ag`, `am`, `aq`, `oc`, `oç`) and can **never** fire, so rows carrying them are
filed `lexicon_free`. 28 of 565 gold-OFF `lexicon_free` dev rows (4.96%) carry
one; `aq` alone has P(OFF|t) = 0.986047 in training.
**Direction:** this is the **opposite** leak to the one Phase 02 measured. Both
known slice-definition defects move the headline in the **same conservative
direction** — the reported +0.3301 understates the gap under either correction.
**Not fixed:** the lexicon and `MIN_ROOT_LEN` stay frozen; recorded as a
limitation.
SRC `RL:38` · `token_stats.json#posthoc_exploratory.min_root_len_blind_spot` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`, `[CORRECTED]` (refines, does not contradict, `RL:17`)

### D.7 CORRECTION — two confidence intervals mis-transcribed (Phase 08)

**Wrong:** `RL:35` quoted two CIs from a **200-resample smoke run**.
**Replaced by:** the final **10,000-resample** values (see the ⚑ CONFLICT block
in A2 §A2.6). Both point estimates were correct; both corrected intervals are
**wider**. The wider-pool interval still excludes zero (SUPPORT stands) and the
control interval still contains zero (the null stands, now more comfortably).
**The direction matters and is recorded:** the mistake made both results look
*more* precise than the run supports — the direction that flatters the work — so
it was corrected explicitly. Every other Phase 08 figure was re-verified against
the JSON in the same sweep and matched.
**Root cause recorded:** the smoke run and the final run were viewed in the same
session and the earlier figures were carried forward; the automated
findings-vs-record checker now covers CI bounds, not only point estimates.
SRC `RL:39` · `results/08_lexical_analysis/findings.md` corrected in place · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`; `RL:35` is `[SUPERSEDED]` for those two intervals only

### D.8 CORRECTION — the central claim narrowed in the report (twice)

**First narrowing (Phase 09 Stage 1, `RL:42`).**
**Wrong:** §4.3 read *"model, saldırgan SÖZCÜK DAĞARCIĞINI algılamakta, saldırgan
EYLEMİ değil"* — the model detects offensive vocabulary, not the offensive act.
**Contradicted by:** ROC-AUC 0.89615 in `lexicon_free`.
**Supported claim that replaced it:** scores are systematically **depressed** in
that slice — gold-OFF median 0.586072 against 0.96504, and 43.7% at or below 0.5
against 10.7% — so at a fixed threshold the model fails to **flag** it. "The
diagnosis is not withdrawn — it is relocated from discrimination to decision."
The pre-registered verdict was `INTERMEDIATE`, so C9-6's wholesale-narrowing
branch did **not** fire.
SRC `RL:42` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

**Second narrowing (Phase 09 Stage 1b, `RL:46`).**
**Wrong:** sentences implying the augmentation taught the model to detect
offense without profanity.
**Supported claim that replaced it:** the augmentation moved **19 gold-OFF rows**
across the fixed 0.5 threshold in `lexicon_free`. An ordering improvement large
enough to explain it is **excluded, not merely unproven** — ΔAUC −0.005587 with
upper bound **+0.002366** against the pre-registered **0.01** floor. Nor is it a
uniform recalibration: the control slice **worsened**.
**Three limits travel with the claim wherever it appears:** the mechanism is a
**correlate, not a cause** (no ablation was run); **component attribution is
unknown** (only the combined `+1a+1b+D` run was compared, so 1a, 1b and D cannot
be separated); and the **+0.0358 test-set gain is unmeasured** by this analysis,
which is dev-only.
SRC `RL:46` · SCOPE `[DEV-ONLY]` for the analysis, `[TEST]` for the unmeasured gain · STATUS `[CORRECTED]`

### D.9 Phase 11 addendum — C11-2's self-hash clause is defective

**Wrong:** C11-2 requires `cal_eval_split.json` to hold "its own sha256". A file
cannot contain its own digest; the requirement is unsatisfiable as written.
**What stands in its place:** the digest is recorded **outside** the file in
three places, all from the commit session of 2026-08-18 — sha256
`6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899`, git blob
`108599c280162ab3ad17a283d0e59a464e665031`, commit
`d589dbad65f071b7a98f1124717f97d27fa5940c`. The file carries a `self_sha256`
field stating the impossibility and pointing at the addendum.
**A drafting defect in the specification, not a finding.** All four C11-2
reproduction checks passed on the committed artifact, and the Run A provenance
gate re-verified the digest independently at run time.
SRC `phases/11_prior_correction.md` "Addendum, 2026-08-18" @ `5ba53cd` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### D.10 Phase 12 Addendum 1 — five defects (heading says four)

@ `584292c`, all found **before any Phase 12 number existed**; C12-1…C12-15 left
exactly as committed.

1. **`S1` and `S2` each named two different objects.** C12-3 defines systems
   S0/S1a/S1b/S2; C12-11 labelled its sensitivities S1/S2/S3. Binding convention
   from there: systems keep S0/S1a/S1b/S2; sensitivities are renamed **SENS-1**
   (cost frontier), **SENS-2** (`MIN_ROOT_LEN` leak), **SENS-3** (suspect-root
   contamination). A naming defect, not a change to any comparison.
2. **`Cost_S1b ≈ 0.27` in C12-7 was wrong arithmetic.** S0 costs
   `(213 + 3·285)/4764 = 0.2242` on full dev and `(100 + 3·158)/2382 = 0.2410`
   on EVAL, which is the relevant scoring set. Corrected relative half-widths
   against 0.241: d = 40 → SE 0.0080, ±0.065; d = 100 → 0.0126, ±0.103;
   d = 200 → 0.0178, ±0.145. **The SE column was correct; only the denominator
   was wrong.**
3. **The corrected table under-powers branch 5, and the bias is declared rather
   than corrected.** At d = 100 the half-width (±0.103) meets the LARGE band
   (0.10). The band was **not** moved, because any replacement would be chosen
   knowing which direction favours the recorded prediction. A reporting
   requirement was added in its place. Outcome: see C §C.10.
4. **"bins above 0.5 run −0.13 to −0.18" (C12-1) over-states Run A.** The actual
   `lexicon_free` gaps above 0.5 are **−0.1362, −0.0140, −0.0334, −0.1791,
   −0.1375**. Two of the five sit well outside the stated range. C12-1's point
   survives on the [0.4, 0.5) gap of −0.162 and on bins [0.8, 0.9) and
   [0.9, 1.0).
5. **C12-9's citation of Phase 15 pointed at a document that does not exist.**
   There is no Phase 15 pre-registration; the address × `lexicon_hit` band cell
   of **n = 22** is recorded in `results/15_deixis/cell_counts.json` and the
   decision not to run that control was taken by the project lead on 2026-08-19.

SRC `phases/12_threshold_policy.md` Addendum 1 @ `584292c` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### D.11 Phase 12 Addendum 2 — two corrections to Addendum 1

@ `2b4391bf`. Addendum 1 left exactly as committed.

**(a)** Addendum 1's heading says "four defects"; its body numbers five. Items 1,
2, 4 and 5 were reported by Claude Code; item 3 was added afterwards by the
controller and the heading was not recounted. **The correct count is five.**

**(b)** Addendum 1 item 5 cites `cell_counts.json` at commit `95d20de4`. **That
file was not in that commit.** `95d20de4` contains four paths — `.gitignore`,
`data/deixis/address_tokens.json`, `src/phase15_deixis.py`,
`tests/test_phase15_address.py`. The counts file existed on disk and untracked,
holding `lexicon_hit × address × band = 22`. It is now committed at **`e44b19a0`**,
sha256 `facd3544c2ad28f63297219ca2a050e5c9626a323c304ad18e49d65757ee210a`.
**C12-9's citation resolves to that commit.** The number it relies on is
unchanged; only the locator was wrong.

SRC `phases/12_threshold_policy.md` Addendum 2 @ `2b4391bf` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### D.12 Phase 12 process defect — the verdict test was not committed

`tests/test_phase12_verdict.py` was named in the `ec2fd3a7` commit instruction
but **was not committed** (that commit contains one file, 366 insertions).
C12-7's requirement that the verdict rule be unit-tested **before the data
loads** was therefore satisfied only within the run session, by the same agent
that authored the module — **the independence is lost**. The branch assignment
has been hand-verified: d = 80 ≥ 40; ci_low = −0.0160 not > 0;
−0.0160 ≤ 0 ≤ +0.1048 → branch 2.
SRC `RL:49` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### D.13 Phase 12 Addendum 3 / C12-16 — ordering disclosed, not concealed

The Phase 12 row carrying the four S1a-vs-S0 quantities as bare point estimates
was committed at **`d74acd93`**; the C12-16 clause authorising intervals was
committed **afterwards** at **`b0f2b0b5`**; the run followed. The *quantities*
were fixed in advance by C12-8 and by C12-4's designation of r = 3 as primary;
only their *uncertainty* was computed late. The file states in its own text:
**"This is estimation after the fact, not pre-registration."**
SRC `RL:50` · `c12_16_intervals.json#ordering_disclosure` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

### D.14 LIMITATION CLOSED — the Drive mirror is byte-verified

`<drive>/results/01_baseline_berturk/dev_predictions.csv` → **736,591 bytes,
sha256 `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346`** —
byte-identical to the local analysis copy. In the same sweep: `run_raw` carries
the **same** sha256 as the Phase-01 baseline dump (so the Phase-03 control and
the Phase-01 baseline are **one file, not two runs that agree**), and
`run_1a1b_d` hashes to
`e525eaabeaf30f55469bf9a16e13ed9363b1a72b04f9adbada01b59ade6bbd4a`. This is why
the Stage 1b control's slice AUC gap (+0.034461) equals Stage 1's to six
decimals — a consistency check passed, not a coincidence.
SRC `RL:45` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]` (closes a limitation logged earlier the same day)

### D.15 CONTROLLER ERROR — the EOL limitation was recorded as deferred when it had already been fixed

> ⚑ **CONFLICT — `RL:51` against `RL:52`. Both are printed; `RL:51` is
> `[SUPERSEDED]`.**

**`RL:51` (`f451777`, 2026-08-19 12:17:17 +0300) states:** 18 of **121** tracked
files have working-tree sha256 ≠ committed-blob sha256, exactly the 18 files
containing CRLF; `cal_eval_split.json` blob is `eb0e6aee…c140` against a recorded
`6d1e3ed7…af899`; **no `.gitattributes` exists anywhere in the tree**; the fix —
a `.gitattributes` containing `* -text` plus `git add --renormalize .` — is
**known and deferred, not applied**.
SRC `RL:51` · SCOPE `[DEV-ONLY]` · STATUS **`[SUPERSEDED]`**

**`RL:52` (`9d3c8c6`) records what is true at HEAD:** the fix landed at
**`3bc0d2e`, 2026-08-19 12:10:08 +0300 — seven minutes before `RL:51` was
committed.** `3bc0d2e` created `.gitattributes` (284 bytes, content `* -text`)
and renormalised 19 files (+79,013 / −79,008). At HEAD: **122 tracked files, 18
still containing CRLF on disk, and 0 working-tree/blob mismatches.** Every
recorded digest now verifies as its committed blob. `core.autocrlf` remains
`true` at system level and unset local/global — which `RL:51` states accurately —
but `* -text` now overrides it.

**Every figure in `RL:51` was correct at `355d6b1` and is incorrect at HEAD.**
The diagnostic behind it ran before `3bc0d2e`; the controller then wrote a
deferral row without verifying whether the fix task — which the controller had
itself written and sent — had already been executed. Recorded as a controller
error of the same kind as the eight previously recorded in this log: **asserting
a state of the world rather than verifying it.** `RL:51` is left exactly as
committed under the append-only rule.

**The one claim in `RL:51` that survives unchanged:** `dev_predictions.csv` and
`karaliste.txt` are untracked and restored from the Drive mirror, so the
repository alone still cannot re-run the analysis.

SRC `RL:52` · `git show --stat 3bc0d2e`; full tracked-file scan at HEAD · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

---

# E. NULLS, INSUFFICIENTS, AND THINGS DECLARED BUT NOT RUN

### E.1 Phase 04 — deferral by slice: **NULL RESULT**

Confidence-based deferral is **error-selective but slice-blind**. It does not
preferentially route `lexicon_free` errors to humans.

| point | `lexicon_free` deferral | `lexicon_hit` deferral | free share of queue | free share of dev |
|---|---|---|---|---|
| raw, high-automation | 0.09373493975903614 | 0.09609120521172639 | 0.8683035714285714 | 0.8711167086481948 |
| raw, high-precision | **0.18602409638554218** | **0.23127035830618892** (ordering reverses) | 0.8446389496717724 | 0.8711167086481948 |

Residual auto-path error is **higher** on `lexicon_hit`: 0.10990990990990991 vs
0.07152353097580431 (high-automation). +1a+1b+D behaves the same (8.8% vs 12.5%).

**Note on denominator, so the figures are not mis-sourced:** these deferral
figures come from `#variants.raw.deferral_full_dev` (full dev, 4,764 rows), while
the operating-point headline figures in A2 §A2.5 come from
`#variants.raw.operating_points` (EVAL half, 2,382). Different denominators, not
a disagreement.

**Two qualifications recorded in both directions:** operationally a reviewer
still spends most of their time on implicit offense; and after deferral
`lexicon_hit` is the worse residual slice, because its error rate is dominated
by the 18.1% FP rate rather than by the recall gap.

**"The hoped-for link from the Phase 02 diagnosis to a working mechanism does not
exist, and is reported as a null."**
SRC `RL:24` · `results/04_calibration/calibration.json#variants.raw.deferral_full_dev` · SCOPE `[DEV-ONLY]` (full dev) · STATUS `[VERDICT]` (null); replicated on test — see A1 §A1.6

### E.2 Phase 11 — the control returned **INSUFFICIENT**

**CONTROL (C11-9), `SG_hit_low`:** +0.03954049253731342, 95% CI
[−0.014396843291377309, +0.08993778541842995], realized n = **134** against the
C11-7 floor of **400** → **branch 0, `INSUFFICIENT`**. Design half-width ±0.0625,
realized ±0.05216731435490363. Gold-OFF in band 24; OFF rate 0.1791044776119403
against mean p 0.13956398507462686.

**Consequence, recorded and not softened:** slice-**specificity** is **not
established and cannot be claimed at this evaluation-set size.** C11-9 named
this in advance as the anticipated case — "can refute a large effect, cannot
resolve a small one" — and C11-7 requires it be **reported as a resolution limit
with the realized n, not reframed as a null**.
SRC `RL:47` · `results/11_prior_correction/metrics.json#control` · SCOPE `[DEV-ONLY]` (EVAL) · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

### E.3 Phase 12 — SENS-3 returned **INSUFFICIENT**, with the point estimate opposite in sign

d = **23** against the floor of 40 → **branch 0, `INSUFFICIENT`**; point estimate
**−0.02471482889733837** [−0.05984642683744477, +0.007952286282306134].
Recorded consequence: **the verdict is stable, the point estimate is not.**
SRC `RL:49` · `#sensitivities_C12_11.SENS-3.primary` · SCOPE `[DEV-ONLY]` (EVAL, 2,253 rows after 129 dropped) · STATUS `[PRE-REGISTERED]`, `[VERDICT]`

### E.4 Phase 15 — **never pre-registered, never run; no address-conditional measurement exists**

Stated plainly, as required:

- **Phase 15 has NO pre-registration.** No `phases/15_*.md` exists in the
  repository. (Verified directly: `phases/` holds 01, 03, 04, 07, 08, 09, 10,
  11, 12 only.)
- **Phase 15 was NOT run.** No signed gap, no ECE, no AUC, no recall and no
  verdict was ever computed for any address-conditional quantity, and none may
  be reported.
- **No address-conditional measurement exists anywhere in the repository.**
  `results/15_deixis/cell_counts.json` states this in its own text: *"No
  calibration quantity, no signed gap, no ECE, no AUC, no recall, no mean p_OFF,
  no per-cell OFF rate expressed as a calibration figure, and no verdict appears
  in this file. Integers, shares of those integers, and hashes."*
- What exists: the frozen address flag (`data/deixis/address_tokens.json`, sha256
  `90c880c1…af91`, commit `95d20de4`) and the frozen cell counts
  (`results/15_deixis/cell_counts.json`, sha256 `facd3544…210a`, 44,256 bytes,
  commit `e44b19a0`). Committed artifacts only.

SRC `RL:53` · `results/15_deixis/cell_counts.json#counts_only`; `ls phases/` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**The `lexicon_hit` × address control: n = 22, declared INSUFFICIENT-by-construction
and NOT run.** The declaration is in **C12-9 of `phases/12_threshold_policy.md`
@ `ec2fd3a7`**; its citation was corrected in **Addendum 1 item 5 @ `584292c`**,
and the locator was corrected again in **Addendum 2 (b) @ `2b4391bf`** to point
at `results/15_deixis/cell_counts.json` @ **`e44b19a0`**, where the number
`lexicon_hit × address × band = 22` is recorded
(`#counts.EVAL.primary.margins.by_slice_x_address."lexicon_hit|address".n_band_p_off_lt_0.5`).
SRC `RL:53`, `phases/12_threshold_policy.md` C12-9 + Addendum 1 item 5 + Addendum 2 (b) · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[CORRECTED]`

**Why counts were produced before any verdict band was fixed, recorded
deliberately:** C9-4 and C11-6 require thresholds derived from a design
calculation on frozen denominators, and the address-cell size appeared nowhere
in the record. Realized prevalence 9.6% of the `lexicon_free` band came in
**below** the projected 10–20%, giving a design half-width of **±0.049 on EVAL
alone** — which would have forced a LARGE band near 0.13, close to unable to
return anything but a null.
SRC `RL:53` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Two rulings recorded:** the measurement was to be **pooled CAL+EVAL** (Phase 15
fits nothing, so the split does no methodological work; pooled half-width
**±0.034**), reporting both denominators explicitly since the pooled aggregate is
**not** Run A's −0.0046; and `tr_lower` was **kept unchanged**, so all-caps
`SIZIN` lowercases to `sızın` and does not flag.
SRC `RL:53` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

**Halted** by decision of the project lead on 2026-08-19 in favour of Phase 12
and the technical report: the primary is modestly powered even pooled, the
control is dead by construction, and the phase fits nothing that could reach the
demo. **Recorded as upside, not a gap: no report claim depends on it.**
Reopening requires a pre-registration committed before any Phase 15 number
exists.
SRC `RL:53` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### E.5 Phase 11 Run B (C11-10) — **declined by the project lead; a decision, not an omission**

C11-10 of `phases/11_prior_correction.md` (committed `d589dbad`) pre-registers
**three** post-hoc treatments, each fitted on CAL and scored on EVAL:

1. **Saerens EM prior correction**, run unsupervised on the slice's EVAL scores.
   Source prior = the **training** prior of that slice (`hit` 0.5535, `free`
   0.1410), not the dev prior; the EM-estimated prior to be reported against the
   known EVAL prior (`hit` 0.5890, `free` 0.1341). **Limitation stated in
   advance:** EM prior estimation is biased when the classifier is
   miscalibrated, which is the condition under test.
2. **Per-slice Platt scaling**, fitted on that slice's CAL rows.
3. **Per-slice isotonic regression.**

**None was run. No numbers exist for C11-10 and none are reported anywhere.**
The figures that would have been produced are per-slice ECE and SignedGap before
and after each treatment.

**Grounds recorded:** Run A returned `BASE-RATE-CORRECT` on the primary, so
post-hoc recalibration has little to repair in the region the phase exists to
study, and C11-13 forbids promoting any C11-10 treatment to primary in place of
a branch-2 result. The remaining value of Run B was **closure of the
pre-registered phase, not treatment** — plus a demonstration of the C11-10
arithmetic that rescaling toward the slice-conditional prior (`free` 0.1410,
`hit` 0.5535, against a global 0.1931) pushes `lexicon_free` scores **down** and
**widens** the recall gap. That arithmetic is stated in the committed
pre-registration and does not require a run.

**Binding on the report:** "Any future report text must state that these
treatments were specified and deliberately not run — they may not be described
as inapplicable, as superseded, or as absent from the design." C11-10 remains
pre-registered and unrun.
SRC `RL:48` · `phases/11_prior_correction.md` C11-10 @ `d589dbad`; `results/11_prior_correction/metrics.json#not_run_in_this_stage.C11-10` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### E.6 Phase 09 — stages declared and not run

- **Stages 2–4 not started; stages 5–6 need GPU and separate authorisation.**
  Stopped after Stage 1 as instructed. SRC `RL:41`
- **Stage 1b was BLOCKED and did not run at `910d21e`** — it needs `run_raw` and
  `run_1a1b_d` prediction dumps, which survive only on the Drive mirror, and
  `drive.mount` failed unattended twice. **No substitute input was used**
  (C9-12 forbids standing the Phase-01 dump in for `run_raw`). It ran later, at
  `09ce5f8`, once the mount was unblocked. SRC `RL:43`, `RL:44`
- **Stage 2 is not authorised.** SRC `RL:44`, `RL:46`

SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### E.7 Phase 11 — the C11-11 sensitivities not run in Run A

S2 (`MIN_ROOT_LEN` leak) and S3 (suspect-root contamination) were **not run** in
Run A. S1 (bin count) **is** reported, per slice.
SRC `results/11_prior_correction/metrics.json#not_run_in_this_stage.C11-11` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### E.8 Not reported by pre-registered constraint

`results/11_prior_correction/metrics.json#not_reported` lists, verbatim:
per-slice macro-F1; per-slice accuracy (both by the Phase-01 pre-registered
constraint, base rates 57.8% vs 13.6%); recall at any threshold other than the
frozen 0.5; and any threshold derived from anything measured there — **nothing
in Phase 11 is an operating point (C11-14)**.

`results/12_threshold_policy/metrics.json#not_run_in_this_stage` lists: no
retraining, no forward pass, no GPU (C12-15); no new corpus, no new labels,
lexicon and `MIN_ROOT_LEN` frozen; **no test-set measurement of any kind**; no
per-slice macro-F1 and no per-slice accuracy (C12-2); **no cross-slice
operating-point match (C12-5 spec defect)**; and no `findings.md` and no
RESULTS_LOG row — the controller drafts both.

`results/12_threshold_policy/c12_16_intervals.json#not_run_in_this_stage` lists:
**no verdict and no branch rule — C12-16 defines none**; no other r; no other
system pair; **no pooling to full dev** (declined by C12-16 because it would
have moved a published point estimate); **no multiplicity correction** — these
are estimation intervals, not tests.

SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### E.9 Ranking-quality contributions that remain inseparable

**Whether the downward score shift in `lexicon_free` is correct calibration to a
13.6% base rate or genuine under-confidence is NOT separable** by the Stage 1
analysis: the CI spans all three pre-registered bands. The report carries this
as its own numbered limitation (§5.12).
SRC `RL:41`, `RL:42` · SCOPE `[DEV-ONLY]` · STATUS `[VERDICT]` (`INTERMEDIATE`)

**Not established by Stage 1b:** why the scores moved (correlate, not
demonstrated cause); which of 1a / 1b / D is responsible (only the combined run
was compared); and whether the same mechanism produced the **+0.0358 test gain**
— that is dev-only and **unmeasured**. No attribution or ablation was run.
SRC `RL:44`, `RL:46` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### E.10 Unmeasured: the contribution of class imbalance

Training is 1:4.18 against the positive class with **no class weighting** and a
threshold fixed at **0.5**, and **no class-weighted or threshold-tuned variant
was ever trained**, so imbalance's contribution to the 0.5628 `lexicon_free`
recall figure is **unmeasured**. Recorded as "the strongest form of the
advisor's point and a real gap in the study."

Recorded in the same row, as a three-part answer: **on the gap between slices —
no**, one model, one threshold, two disjoint subsets, and a global imbalance
depresses both slices alike and cannot create a differential; **on the
slice-conditional priors — the question dissolves**, P(OFF) is 0.553467 given a
lexicon hit vs 0.141046 given none, and "learned the prior attached to profanity
tokens" and "depends on profanity tokens" are the same statement at different
levels of description. **Nothing in this project distinguishes them and the
report must not claim otherwise.**
SRC `RL:37` · `token_stats.json#class_balance` · SCOPE `[DEV-ONLY]` (train split) · STATUS `[DESCRIPTIVE, NO CI]`

---

# F. CEILINGS AND LIMITATIONS

Every standing constraint.

### F.1 The official test set is SPENT

Used for its single permitted measurement on 2026-08-16.
`results/05_final_test/TEST_SET_SPENT.json` exists and
`src.data_io.load_coltekin_test` refuses while it does, on this machine and on
any clone of that commit. Deleting the record is a project-lead decision that
must be logged in `docs/RESULTS_LOG.md`.

**C12-14 binds absolutely: no threshold selected in Phase 12 can ever receive an
independent held-out number.** It may be wired into the offline demo; it may
**not** carry any generalisation claim, and no sentence may state or imply it
will hold on unseen data. Phase 05's dev→test coverage transfer is background
about the **Phase-04** thresholds and is **not** validation of the Phase-12 ones.
SRC `RL:25`, `RL:28`, `RL:49`, `RL:50` · `results/12_threshold_policy/metrics.json#ceilings_C12_14` · SCOPE `[TEST]` and `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### F.2 One seed

Seed 42 throughout: the split, the training run, every bootstrap. No seed sweep
was run.
SRC `RL:49`, `RL:50` · `#ceilings_C12_14[3]`, `results/11_prior_correction/metrics.json#ceilings_C11_14` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### F.3 One checkpoint

`best.pt` = **epoch 1**. Epochs 1 and 3 tie exactly on macro-F1 with identical
confusion matrices but disagree on **198 of 4,764** dev rows; up to 43 of the 285
false negatives are checkpoint-specific. Every analysis in the project is tied to
epoch 1, which produced `dev_predictions.csv`.
SRC `RL:15`, `RL:49`, `RL:50` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### F.4 Same-corpus

Train, dev and test all come from the Çöltekin OffensEval-2020 TR corpus. No
cross-corpus or cross-domain evaluation exists.
SRC `RL:49`, `RL:50` · `#ceilings_C12_14[3]` · SCOPE `[TEST]` and `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### F.5 Both slice-definition defects are unrepaired — and both are conservative

**Defect 1 — suspect-root contamination (Phase 02).** 248 of 614 hit-slice rows
(40.4%) match only a suspect root; they are overwhelmingly non-offensive (175
NOT / 73 OFF), so they diluted the hit slice toward the free slice. Removing
them **widens** the recall gap +0.3301 → +0.3662 (shift +0.0361).

**Defect 2 — the `MIN_ROOT_LEN` blind spot (Phase 08).** 28 of 565 gold-OFF
`lexicon_free` rows (4.96%) carry a lexicon entry shorter than 3 characters and
can never be matched. Removing them raises the bound on the gap +0.3301 →
+0.3529.

**Both known slice-definition defects move the headline in the same conservative
direction: the reported +0.3301 understates the gap under either correction.**

**But the direction is not uniform across metrics.** The same repair that widens
the recall gap **shrinks the AUC gap** to +0.006164, below the pre-registered
smallness floor. Per C9-10 that qualifies the verdict and **may not overturn
it**. This is recorded as a strong qualification in the narrowing direction.

**Neither is fixed.** The lexicon and `MIN_ROOT_LEN` stay frozen; both are
reported as limitations.
SRC `RL:17`, `RL:38`, `RL:41` · `slice_sensitivity.json`, `token_stats.json#posthoc_exploratory.min_root_len_blind_spot`, `stage1_auc.json#sensitivities` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

### F.6 Phase 12's thresholds are dev-only and unvalidatable

Every Phase 12 and C12-16 figure is measured on the dev split, thresholds fitted
on CAL and scored on EVAL. **The CI understates real uncertainty by design:**
C12-6 fixed thresholds from CAL and excluded refitting variance; C12-9 shows
that variance is large (`t_hit` IQR 0.123716, p5/p95 0.129509–0.494651). The
verdict survives a wider interval, but **+0.0411 may not be written up as
"slice-conditional is worse."**

**Three limits on the S1a headline, recorded together:**

1. It is **descriptive with no interval** as C12-8 pre-registered it; the C12-16
   intervals are post-hoc estimation, and a significance claim requires new
   pre-registration.
2. C12-3's internal control **diverged materially at every r**, with the fitted
   threshold always above the analytic one — consistent with Run A's global
   over-scoring (`SG_global` −0.0117) and, per C12-3's own terms, **weakening**
   the Elkan argument rather than confirming it.
3. **S1a does not dominate** — S1b is cheaper at r = 1, 2 and 10.

**The defensible claim is that a cost-derived threshold beats 0.5, not that the
analytic one is optimal.**

**And on the C12-16 intervals:** three of the four were **structurally determined
in sign** and must not be read as evidence of an effect — nesting guarantees
`d_recall` and `d_recall_free` positive and `d_precision` negative. Their value
is the **precision of the magnitude, not a sign test**. `d_gap` is the exception
and the one earned sign claim. The pre-registered wording is "recovers 13.0pp of
recall [10.0, 16.1] at 14.2pp of precision [11.3, 17.2]", **never**
"significantly recovers recall". No verdict was computed and no branch rule
exists for any C12-16 quantity.

**`r` is a policy input this project cannot derive**; the report presents the
frontier and lets the reader select.
SRC `RL:49`, `RL:50` · `#primary`, `#threshold_stability_C12_9`, `c12_16_intervals.json#scope, #not_run_in_this_stage` · SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`, `[POST-HOC]`

### F.7 EOL / digest portability — **FOUND AND CLOSED**

Stated as found and closed, on the `RL:45` precedent ("LIMITATION CLOSED — the
Drive mirror is now byte-verified"). **It is not outstanding.**

**What was found:** Git's end-of-line conversion made the recorded sha256 digests
unverifiable against committed blobs on any platform other than the one that
wrote them. Before the fix (at `355d6b1`): 121 tracked files, 18 of them
mismatching, `cal_eval_split.json` blob `eb0e6aee…c140` against the recorded
`6d1e3ed7…af899`, and no `.gitattributes` anywhere in the tree.

**The fix, cited: `3bc0d2e` (2026-08-19 12:10:08 +0300).** It created
`.gitattributes` containing `* -text` and renormalised 19 files
(+79,013 / −79,008), making committed blobs byte-identical to working copies so
that **every recorded digest verifies on every platform and no recorded value
changed.** (The alternative — normalising to LF — would have moved
`6d1e3ed7…af899`, which appears in nine tracked files including two committed
pre-registrations, and was rejected on that ground.)

**Verified state at HEAD `9d3c8c6`:** 122 tracked files, 18 still containing CRLF
on disk, **0 working-tree/blob mismatches**, all recorded digests verifying.
`core.autocrlf` is still `true` at system level (unset local and global), but
`* -text` overrides it.

**Both commits are cited:** `3bc0d2e` for the fix, `RL:52` for the correction to
the record. `RL:51` is `[SUPERSEDED]` wherever it is transcribed.
SRC `RL:52`, `RL:45` (precedent) · `git show --stat 3bc0d2e`; tracked-file scan at HEAD · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### F.8 The repository alone cannot re-run the analysis

**This survives the EOL fix unchanged.** The two largest frozen inputs are
**untracked** and restored from the Drive mirror:
`results/01_baseline_berturk/dev_predictions.csv` (`.gitignore:41`,
`results/**/*predictions*.csv`) and `data/lexicon/karaliste.txt`
(`.gitignore:12`, `data/**`). What the EOL fix restored is the **portability of
the part that was verifiable**.
SRC `RL:51`, `RL:52` · `.gitignore:12`, `.gitignore:41` · SCOPE `[DEV-ONLY]` · STATUS `[CORRECTED]`

### F.9 The evidential ceiling on the deixis finding

**Co-occurrence shows the signal was AVAILABLE in the training data, not that the
model USED it.** Attribution or ablation would be required and **neither was
run**. The grouping of tokens into deictic and political sets is additionally
**post-hoc**; the pre-registered quantity is the 19-token group as a whole.
C8-11 forbids turning any of it into a feature, and none is proposed.
SRC `RL:36`, `RL:40` · SCOPE `[DEV-ONLY]` · STATUS `[POST-HOC]`

### F.10 The annotation convention is adopted as given

Çöltekin's convention is adopted and **nothing is relabelled**. The stated
limitation is that ~13 of 40 of the unbiased `lexicon_free` FN sample is
criticism of politicians or institutions whose offensiveness is
convention-dependent, and those rows stay counted in every reported number. If
criticism of a party is annotated OFF, a party name predicting OFF is the
convention showing through the data, **and this project cannot separate that
from a model defect**.
SRC `RL:17`, `RL:36` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

### F.11 Measurement-only ceilings recorded in the artifacts

`results/11_prior_correction/metrics.json#ceilings_C11_14` lists, verbatim:
dev-only; one seed; one checkpoint (`best.pt` = epoch 1); same-corpus; the two
known slice-definition defects unrepaired, both pushing the headline in the
conservative direction; measurement only — no intervention proposed, no model
retrained, no forward pass, lexicon and `MIN_ROOT_LEN` frozen, official test set
spent and unread; and **"Phase 11's answer does not license Phase 12; it changes
what Phase 12 would be testing, and that is all."**

C12-13's prohibition on deriving an operating point **is lifted in Phase 12 and
only there**, and remains in force for every earlier phase.
SCOPE `[DEV-ONLY]` · STATUS `[PRE-REGISTERED]`

### F.12 What Phase 11 forbids the report to say

**Every sentence implying the `lexicon_free` scores are *wrong*,
*under-confident*, or *in need of repair* is unsupported and is to be audited
out.** The claim that survives is narrower and operational: at the deployed
threshold nearly half of profanity-free offensive content goes unflagged, **and
the probabilities behind that outcome are accurate.**
SRC `RL:47` · SCOPE `[DEV-ONLY]` · STATUS `[VERDICT]`

---

# G. ARTIFACT REGISTRY

State at HEAD `9d3c8c6`: **122 tracked files, 0 working-tree/blob mismatches, all
recorded digests verifying.** Bytes and digests below are the working-tree
values, which are byte-identical to the committed blobs for every tracked file.

## G.1 Frozen inputs — UNTRACKED (restored from the Drive mirror)

| path | bytes | sha256 | tracked |
|---|---|---|---|
| `data/coltekin/offenseval-tr-training-v1.tsv` | 4,101,728 | `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa` | **no** (`.gitignore:12`, `data/**`) |
| `data/coltekin/offenseval-tr-testset-v1.tsv` | 449,553 | `9052784e13248e58658e34a4f86a3463ef8b2594d2feb289e4b29bba2866b437` | **no** — **SPENT** |
| `data/coltekin/offenseval-tr-labela-v1.tsv` | 35,280 | `ae9b0837e948c3d9c3a147d2a415989a4940a7756d5821b3289276574941c9e3` | **no** — **SPENT** |
| `data/lexicon/karaliste.txt` | 5,988 | `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` | **no** (`.gitignore:12`) — **FROZEN, 695 entries** |
| `results/01_baseline_berturk/dev_predictions.csv` | 736,591 | `a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346` | **no** (`.gitignore:41`, `results/**/*predictions*.csv`) — **FROZEN** |

Also on the Drive mirror only, not in the repository:
`results/03_defense/run_raw/dev_predictions.csv` — sha256 **identical** to the
Phase-01 dump (`a2f5bddf…a6346`, byte-verified 2026-08-17); and
`results/03_defense/run_1a1b_d/dev_predictions.csv` — sha256
`e525eaabeaf30f55469bf9a16e13ed9363b1a72b04f9adbada01b59ade6bbd4a`.
SRC `RL:45`, `stage1b_defense_auc.json#inputs`

## G.2 Frozen artifacts — TRACKED

| path | bytes | sha256 | blob matches |
|---|---|---|---|
| `.gitattributes` | 284 | `69a20d784f4889887fb7667cec4c8c5d0d4279cb4ca37b851b206c10255f38f4` | yes |
| `data/splits/split_seed42.json` | 815,066 | `73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2` | yes |
| `data/deixis/address_tokens.json` | 3,443 | `90c880c1e9c58bea6af74d6a098c4e790fb978fe00d8d9ac210e440b9d45af91` | yes |
| `results/01_baseline_berturk/metrics.json` | 5,524 | `3dc26a179b48e9fce6e1839bab495d66bb600f33177a715f49b51582f7286042` | yes |
| `results/01_baseline_berturk/run_config.json` | 2,330 | `d54d27161e9e3f8a625dc807831a18e4139ecdeffeb93e5e2e0111fad2ac66d4` | yes |
| `results/02_failure_analysis/slice_sensitivity.json` | 2,406 | `a37b48b92c9da5ec5deb60976364e23805a05f7a324c1828285a699a3d874eed` | yes |
| `results/03_defense/comparison.json` | 4,543 | `c9d84de844ba6375f315b652b735ba8b9f1d2201bb34960ae5d7552d91656fb2` | yes |
| `results/04_calibration/cal_eval_split.json` | 69,676 | `6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899` | yes |
| `results/04_calibration/calibration.json` | 46,790 | `21aa6c8e62604a97f2f0c9a0c315249a3042eae61e0b6c3b94bae48f984247f9` | yes |
| `results/05_final_test/metrics.json` | 20,114 | `e4b5b35d07542344abe1a469b9cc598500e3dc16490080d8dcb5a9fc73b3fc94` | yes |
| `results/05_final_test/paired_deltas.json` | 1,189 | `7b0945b033b3d35ec9890ff466ceeae7ee5b6e8c352152a25b93dc23a90d5eec` | yes |
| `results/05_final_test/TEST_SET_OPENED.json` | 176 | `4dbe8b151eabf114b6ffbb8308da0ceaf6259f1ce9145d60c0bc6529798824b8` | yes |
| `results/05_final_test/TEST_SET_SPENT.json` | 901 | `87eb2e58139497ea3a43958be7d1f6e411bcacdc12aebfc57ed45ccb2d441ff7` | yes |
| `results/08_lexical_analysis/token_stats.json` | 89,324 | `750798f077856af4f9649f05722ed135d26675d4b5556aff856b70fe5ec81dc6` | yes |
| `results/09_deeper_analysis/stage_1/stage1_auc.json` | 6,159 | `5914c7c9e92bad7d7f2d0f0abd8254c666e4b5af1499eb948e3522d9486a9eaa` | yes |
| `results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json` | 4,203 | `3471a7fc3368ed8650010fd36b787d14b36a38023a9fe6f1c1117309fcf35fce` | yes |
| `results/11_prior_correction/metrics.json` | 33,578 | `59be3fd06a78b35397adfd38371e88086c4b193d85285f87b454cf34a12887e9` | yes |
| `results/12_threshold_policy/metrics.json` | 52,195 | `c60bd4a3c4f9040129202c66e7d84cb68fb1cfe539881f68eaf21669cf3b3815` | yes |
| `results/12_threshold_policy/c12_16_intervals.json` | 11,663 | `caf52a6cb7f10bb83b22a0f2b481aedf798148f0cff61c91ad318cce36c1ccf1` | yes |
| `results/15_deixis/cell_counts.json` | 44,256 | `facd3544c2ad28f63297219ca2a050e5c9626a323c304ad18e49d65757ee210a` | yes |
| `results/day1_report.json` | 671 | `32a9d585d6e0628cc9cf368da287c5f0ad9069125156cf82d0fb8c1f34840c3b` | yes |

**Two digests were orphaned until 2026-08-19.** `59be3fd0…87e9`
(`11_prior_correction/metrics.json`) and `caf52a6c…ccf1` (`c12_16_intervals.json`)
appeared **nowhere** in any tracked or untracked file and existed only in
controller-held notes; `RL:51` bound both files to their digests inside the
repository for the first time. `cal_eval_split.json`'s digest, by contrast, is
recorded in **nine** tracked files.
SRC `RL:51` · SCOPE `[DEV-ONLY]` · STATUS `[SUPERSEDED]` for the surrounding EOL claims of `RL:51`; the orphaned-digest fact itself is not superseded

**Other recorded digests** (not files in this registry): dev fingerprint
`034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4`;
`cal_eval_split.json` git blob `108599c280162ab3ad17a283d0e59a464e665031`.

SRC for G.1 and G.2: direct `sha256` of the working tree plus
`git cat-file blob HEAD:<path>` at commit `9d3c8c6`; `git ls-files` for tracked
status; `.gitignore` lines 12 and 41. SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

---

# H. LITERATURE

Every citation used anywhere in the repository, outside
`docs/PROJECT_HISTORY.md`. Found by exhaustive search of all tracked `.md`,
`.py` and `.json` files for arXiv identifiers, DOIs and author names.

**There are three literature citations in the entire repository, and one of them
is the corpus.**

| # | citation | identifier | peer-reviewed or preprint | where it is used |
|---|---|---|---|---|
| 1 | Elkan, *The Foundations of Cost-Sensitive Learning*, **IJCAI 2001** | **no DOI or arXiv ID appears anywhere in the repository** | conference paper — **peer-reviewed** (IJCAI is a refereed conference) | `phases/12_threshold_policy.md` C12-1 @ `ec2fd3a7`; the basis for `t* = 1/(1+r)` and therefore for system S1a |
| 2 | Saerens, Latinne & Decaestecker, *Neural Computation* **14(1):21–41, 2002** | DOI **`10.1162/089976602753284446`** | journal article — **peer-reviewed** | `phases/11_prior_correction.md` C11-10 @ `d589dbad` (the EM prior-correction treatment, **specified and not run**); repeated at `RL:48` |
| 3 | Surana | **`arXiv:2605.14074`**, May 2026 | **preprint, single-author, NOT peer-reviewed** — described as such in the pre-registration itself | `phases/11_prior_correction.md` C11-1 preamble @ `d589dbad`; `results/11_prior_correction/metrics.json#calibration_fairness_gap.comparable_to`; `src/phase11_prior_correction.py:612`; `RL:47` |
| 4 | Çöltekin — Turkish Offensive Tweet Corpus / **OffensEval-2020 TR** | **no bibliographic citation exists in the repository.** Referenced by filename, by SHA-256, by project site `https://coltekin.github.io/offensive-turkish/` and by HuggingFace id `coltekin/offenseval2020_tr` | the corpus paper is **LREC 2020** per `docs/phase_briefing.md:179`, which also records "BERTurk on OffensEval-TR macro-F1 ≈ 0.786" as an unverified orientation figure | the data source for every measurement in the project |

**Verification status, stated rather than assumed.**

- Identifier **2** (`10.1162/089976602753284446`) and identifier **3**
  (`arXiv:2605.14074`) are the only two machine-checkable identifiers in the
  repository. Both appear verbatim in a committed pre-registration.
- Identifier **1** (Elkan) carries **no** DOI or arXiv ID anywhere in the tree.
  Its peer-review status is inferred from the venue named in the citation
  (IJCAI 2001), not from a stored identifier.
- Identifier **4** (Çöltekin) has **no bibliographic entry** anywhere. This is
  recorded as a known gap, not discovered here.

**The repository has no bibliography and no in-text `[n]` citations.**
`phases/10_sablon_mapping.md` records both facts as `NONE` verdicts against the
KYS template: *"There is **no bibliography in the repository**"* (line 225) and
*"There is not one `[n]` citation in `report/`, and no numbered list for one to
point at"* (line 227). It also records that the Çöltekin corpus is *"Named by
filename and SHA-256 only"* with *"**no bibliographic citation** of Çöltekin or
of any other academic source anywhere in `report/`"* (line 102), and that
`report/` has **no section-3 file at all**.

**`phases/07_report.md` records the reason the section was left unwritten:**
*"No citation in that list has been verified"* (line 169), and lists
*"Verify the §3 citations from primary sources (G4) — blocking for §3"* as an
open task (line 193). `report/` contains files 01, 02, 04 and 05 only.

**Polarity note attached to citation 3, pre-registered so it is not conflated
later:** Surana's subgroups are **over**-confident (false positives on
identity-mentioning content); this project's hypothesis concerns **under**-scoring
(false negatives on profanity-free content). *"The shapes of evidence are
analogous; the directions are opposite. Any sentence that treats them as the
same finding is wrong."* The comparable numbers are our **+0.0084
[−0.0002, +0.0529]** against his **+0.029…+0.134 with every subgroup CI excluding
zero** — see C §C.8.
SRC `phases/11_prior_correction.md:48-59, :287, :306-307`; `phases/12_threshold_policy.md:51`; `phases/10_sablon_mapping.md:102, :225, :227`; `phases/07_report.md:169, :193`; `docs/phase_briefing.md:78-86, :179`; `RL:47`, `RL:48` · SCOPE `[DEV-ONLY]` · STATUS `[DESCRIPTIVE, NO CI]`

---

*End of extract. Built from `docs/RESULTS_LOG.md` (53 lines), the committed
artifacts under `results/`, the pre-registrations and addenda under `phases/`,
and `git log --oneline --all`, at commit `9d3c8c6`.*
