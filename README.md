# NSosyal B* — measuring lexicon dependence in Turkish offensive-language detection

Most Turkish offensive content carries no profanity word. Keyword and lexicon
filters — the first layer of automated moderation — never see it. This project
**measures** how much of a fine-tuned classifier's performance rests on profanity
vocabulary, and repairs the resulting failure at the **decision threshold**,
without retraining the model.

The deliverable is not a better classifier. It is a measurement with confidence
intervals, replicated on a held-out test set, plus a triage layer that routes the
uncertain fraction to a human reviewer.

Full spec: [`docs/phase_briefing.md`](docs/phase_briefing.md) (what is being
built) and [`docs/claude_master_brief.md`](docs/claude_master_brief.md) (how the
work is run). Both are binding.

**Repo stays private until submission** — `src/obfuscation.py` generates
functional evasion text.

## Headline findings

Every figure below is read from the results file named. Confidence intervals are
95% bootstrap percentile, seed 42.

**The gap.** In the OffensEval-2020 TR training split (31,756 posts, Çöltekin
corpus; 19.3% offensive), **3,892 of 6,131 offensive posts — 63.5% — match no
root** in a frozen 695-entry profanity lexicon.
→ `results/day1_report.json`

**The classifier does not close it.** Fine-tuned BERTurk OFF-recall on dev:
**0.8930** on the lexicon-matched slice, **0.5628** on the lexicon-free slice.
Gap **+0.3301** [+0.2771, +0.3827].
→ `results/03_defense/comparison.json`

**Replicated once on the official test set** (opened exactly once, then locked):
gap **+0.3970** [+0.3418, +0.4542].
→ `results/05_final_test/metrics.json`

**The loss is at the decision, not the ranking.** Dev ROC-AUC is **0.9306**
lexicon-matched vs **0.8962** lexicon-free. The model separates profanity-free
offensive content; it fails to push it over the threshold.
→ `results/09_deeper_analysis/stage_1/stage1_auc.json`

**Retraining was tried and failed.** Counterfactual data augmentation (`1a1b_d`)
moved dev macro-F1 by **−0.0069** [−0.0185, +0.0052] — interval includes zero.
It bought **+0.0336** [+0.0052, +0.0662] lexicon-free OFF-recall at a cost of
**−0.0423** [−0.0778, −0.0109] on the lexicon-matched slice. This is reported as
a failure, and it is why the repair moved to the threshold layer.
→ `results/03_defense/comparison.json`

**The threshold repair.** On the EVAL half of dev (n = 2,382), a cost-derived
threshold raises lexicon-free OFF-recall by **+0.1727** [+0.1295, +0.2194] and
narrows the slice gap by **−0.1067** [−0.1630, −0.0484], at a precision cost of
**−0.1418** [−0.1723, −0.1131]. The four point estimates were pre-registered;
the intervals were added afterwards and are labelled as not pre-registered.
→ `results/12_threshold_policy/c12_16_intervals.json`

## What this project does not claim

Stated here because these are the claims the numbers do **not** support:

- **Not** that the interface or the threshold improves model accuracy. Ranking is
  unchanged; only the operating point moves, and it is a recall/precision trade.
- **Not** that human review effort disappears. The triage layer routes work; it
  does not remove it.
- **Not** WCAG *conformance*. Contrast and attribute checks are measurements, not
  a conformance process, and no conformance testing was run.
- **Not** cross-corpus generalisation, and not fine-grained target classification.
  Both are out of scope; see [`report/final/`](report/final/).
- **No live-test numbers.** The official test set is spent. Everything produced
  after that single pass is dev-set evidence and is labelled as such.

## Status

| Phase | Protocol | State |
|---|---|---|
| Day 1 — data load, lexicon freeze, go/no-go gate | — | done → `results/day1_report.json` |
| 01 — baseline diagnosis | [`phases/01_baseline_diagnosis.md`](phases/01_baseline_diagnosis.md) | done → `results/01_baseline_berturk/` |
| 02 — failure analysis | — | done → `results/02_failure_analysis/` |
| 03 — defense design (counterfactual augmentation) | [`phases/03_defense_design.md`](phases/03_defense_design.md) | done, **negative result** → `results/03_defense/` |
| 04 — calibration + risk–coverage | [`phases/04_calibration.md`](phases/04_calibration.md) | done → `results/04_calibration/` |
| 05 — official test run (once) | — | done, **test set spent** → `results/05_final_test/TEST_SET_SPENT.json` |
| 07 — report | [`phases/07_report.md`](phases/07_report.md) | in progress → `report/` |
| 08 — lexical analysis | [`phases/08_lexical_analysis.md`](phases/08_lexical_analysis.md) | done → `results/08_lexical_analysis/` |
| 09 — deeper analysis (AUC decomposition) | [`phases/09_deeper_analysis.md`](phases/09_deeper_analysis.md) | done → `results/09_deeper_analysis/` |
| 10 — template mapping | [`phases/10_sablon_mapping.md`](phases/10_sablon_mapping.md) | done |
| 11 — prior correction | [`phases/11_prior_correction.md`](phases/11_prior_correction.md) | done → `results/11_prior_correction/` |
| 12 — threshold policy | [`phases/12_threshold_policy.md`](phases/12_threshold_policy.md) | done → `results/12_threshold_policy/` |
| 15 — deixis / address flag | — | done → `results/15_deixis/` |
| Offline demo | — | runs; verified end-to-end 2026-08-23 |

Seven phase protocols fix decision rules and produce numbers (01, 03, 04, 08, 09,
11, 12). Each was committed to version control **before** the first number of its
phase existed; `git log --follow` confirms the ordering for all seven, phase 08
included once its rename from `phases/06_lexical_analysis.md` is followed.

## Layout

```
config.py        every path + constant; no script hardcodes a location
src/             source of truth — scripts import from here, never re-implement
  data_io.py     corpus readers, format traps guarded in code, test-set lock
  lexicon.py     Turkish-aware casing + literal/root lexicon matching
  obfuscation.py attack families D (train) / H (eval) + disjointness guard
  augment.py     counterfactual augmentation (phase 03)
  models.py      BERTurk wrappers + training loop
  calibration.py temperature scaling, ECE, risk–coverage, selective prediction
  evaluate.py    one metric path shared by every system
  phase11_*.py   prior correction
  phase12_*.py   threshold policy + C12-16 intervals
  phase15_*.py   deixis / address flag
phase*.py        one runner per phase, at the repo root
phases/          pre-registration protocols — committed before their numbers
data/            gitignored — raw corpora live here locally only
results/         experiment JSON (committed); prediction dumps ignored
docs/            briefings + RESULTS_LOG.md (append-only evidence log)
report/          Turkish report drafts + build_docx.py
report/final/    approved report text (KYS 1.1 / 1.2 / 2.1 / 2.2) + bibliography
demo/            offline side-by-side demo (app.py, build_assets.py)
demo_assets/     gitignored — 885.9 MB bundle, rebuilt by demo/build_assets.py
tests/           regression tests for the confirmed format traps
```

Nothing in `src/` is a stub any more. Every module listed above is implemented.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
pytest tests/ -q
```

Raw data is gitignored. On a fresh checkout, place it as:

```
data/coltekin/offenseval-tr-training-v1.tsv
data/coltekin/offenseval-tr-testset-v1.tsv
data/coltekin/offenseval-tr-labela-v1.tsv     # comma-separated despite .tsv
data/lexicon/karaliste.txt                     # frozen, 695 entries
```

Reproduce the Day 1 gate:

```bash
python day1_gate_en.py --out results/day1_report_rerun.json
python tests/_verify_day1_reproduction.py      # diffs it against the frozen record
```

## Offline demo

Three systems side by side — keyword filter, raw BERTurk, augmented variant —
with the review layer gating the raw model at the frozen phase-04 threshold
(0.663171). Build the asset bundle once (this is the only step that needs
network), then run:

```bash
python demo/build_assets.py \
    --raw_ckpt     <path>/01_baseline_berturk/best.pt \
    --defense_ckpt <path>/03_defense/1a1b_d/best.pt \
    --out demo_assets
python demo/app.py --host 127.0.0.1 --port 8000
```

At runtime it makes **no network calls**: `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` are set before `transformers` is imported, there are no
CDN script tags, and the served page carries no external references. CPU only, no
GPU required. Startup takes roughly 40 s to load 885.9 MB of fp32 weights.

On a deferred case the raw model's decision and probability are withheld from the
page; the confidence that remains visible is `max(p, 1-p)`, which is
label-neutral. The other two systems are not gated — the demo is a research
comparison tool, and that is deliberate.

## Ground rules

Enforced in code where possible, not left as tribal knowledge:

- **Seed 42** everywhere data is split, shuffled or a model is initialised, and
  stated in every result file.
- **Every experiment writes a step-named JSON** into `results/`. Nothing is
  silently overwritten — `day1_gate_en.py` refuses to clobber without `--force`.
- **The official Çöltekin test set was touched exactly once.**
  `results/05_final_test/TEST_SET_SPENT.json` now exists, and
  `data_io.load_coltekin_test()` refuses while it does. Deleting it is a
  project-lead decision and must be recorded in `docs/RESULTS_LOG.md`.
- **Pre-registration.** Each phase protocol in `phases/` fixes its decision rules,
  numeric thresholds and failure conditions before any number of that phase
  exists. Ordering is auditable with `git log --follow`.
- **Training obfuscation ≠ evaluation obfuscation.** `obfuscation.assert_disjoint()`
  raises if a robustness number would be measured on an attack family the model
  was trained on. That circularity killed an earlier version of this idea.
- **The lexicon is frozen** (695 entries, sha256 `0f5a05f5…ce20b` in
  `results/day1_report.json`). Adding words after seeing a result is post-hoc
  tuning and invalidates the lexicon-free measurement the whole project rests on.
- **`docs/RESULTS_LOG.md` is append-only** — one row per completed experiment:
  date, what ran, headline numbers, interpretation, decision. Contradictions are
  recorded as new correction rows; earlier rows are never edited. The log
  currently carries six correction rows and one spec-defect row.
- **Byte stability.** `.gitattributes` sets `* -text` so Git performs no
  end-of-line conversion — the repo records sha256 digests, and conversion would
  make them unverifiable on any platform other than the one that wrote them.
- **Every difference is reported with a confidence interval, whatever its sign.**
  Negative results are published as results.

## Data sources

| Role | Source | Note |
|---|---|---|
| Train + diagnose | Çöltekin OffensEval-2020 TR | 31,756 rows, 85/15 train/dev |
| Final test | Çöltekin official test + gold | 3,528 rows; touched once, now locked |
| Cross-corpus | [Mayda](https://github.com/imayda/turkish-hate-speech-dataset-1), [Beyhan](https://github.com/verimsu/Turkish-HS-Dataset) | never trained on; 3-way labels → `LABEL_MAP_3TO2` |
| Lexicon | [turkce-kufur-karaliste](https://github.com/ooguz/turkce-kufur-karaliste) | CC BY-SA 4.0; frozen Day 1 |
| Base model | [`dbmdz/bert-base-turkish-cased`](https://huggingface.co/dbmdz/bert-base-turkish-cased) | 110,618,882 params |

Rejected: `Overfit-GM/turkish-toxic-language` — merged (likely contains
Çöltekin → contamination) and partly pseudo-labeled.
