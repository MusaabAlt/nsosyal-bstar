# Phase 1 — Baseline diagnosis

Execute against the standards in `nsosyal_pycharm_setup_prompt.md` and
`docs/claude_master_brief.md`.

**Entry gate:** Phase 0 complete — private GitHub remote exists, Colab clones
the repo, `NSOSYAL_ENV=colab` resolves all paths.

**Exit gate:** the recall gap and its CI are recorded in `metrics.json`, and the
pre-registered decision rule below has been applied out loud. Phase 2 does not
open until that verdict is stated.

---

## The one question this run answers

Does the lexicon-free gap survive a real trained model, or does BERTurk learn
the phenomenon on its own — unlike the naive keyword filter?

Day 1 proved that 3,892 / 6,131 OFF tweets (63%) evade a keyword filter under
root matching. That is a fact about the **filter**, not about any model. This
run establishes whether it is also a fact about a **transformer**. Everything
downstream — the defense design, the report's central claim, the demo — depends
on the answer, so nothing else should be built until it lands.

---

## Preconditions (abort if any fails)

1. `tests/_verify_day1_reproduction.py` passes. If the 16 frozen fields no
   longer reproduce, stop — the refactor has drifted and no number below is
   trustworthy.
2. `data/coltekin/offenseval-tr-training-v1.tsv` matches SHA256
   `8509c01c...bcd4baa`; `karaliste.txt` matches `0f5a05f5...eace20b`.
3. `NSOSYAL_ENV=colab`. **Colab Pro+ is the decided runtime** — the Kaggle
   reference in the phase briefing is superseded; correct that doc so one
   source of truth remains.
4. The official test set is NOT touched. `load_coltekin_test()` must not be
   called anywhere in this task. Its `PermissionError` guard stays armed.

---

## Steps

### 1. Deterministic split
85/15, stratified on label, `seed=42`. Write the resulting row indices to
`data/splits/split_seed42.json` and load from that file on every subsequent
run. The dev set must be byte-identical across all four rows of the Section 8
comparison matrix — regenerating it per run is how a matrix quietly stops
comparing like with like.

### 2. Slice tagging
Tag every dev row `lexicon_hit` / `lexicon_free` using `src/lexicon.py` as-is.
Do not reimplement the matching rule; import it.

**Sanity gate:** apply the same tagger to the full training corpus and assert
it reproduces 3,892 lexicon-free OFF out of 6,131. If it does not, the tagger
in use differs from the one that produced the frozen record — abort and report,
do not proceed with an adjusted number.

### 3. Keyword-filter baseline
Score the frozen lexicon as a classifier on the same dev split. Cheap, and it
is row 1 of the comparison matrix. Compute it here so it never gets produced
under slightly different conditions later.

### 4. Train BERTurk
`dbmdz/bert-base-turkish-cased`, `max_len=128`, `seed=42`, fp16, checkpoint per
epoch. lr `2e-5`, batch 32, 3 epochs, linear warmup 10%. Single configuration —
no hyperparameter search. A sweep costs a day and earns nothing on a rubric that
rewards the diagnosis, not the third decimal place.

### 5. Evaluate
On dev, overall and per slice:
- macro-F1, OFF-precision, OFF-recall, full classification report
- **OFF-recall on `lexicon_hit` vs `lexicon_free`, with a 1,000-resample
  bootstrap CI on the difference** — this is the pivotal number
- per-row prediction, gold label, slice tag, and softmax confidence

Confidences are required output even though calibration is a later task; the
risk–coverage curve and the failure analysis both read from this same file, and
re-running training to recover them would waste a day.

---

## Output contract

Write to `<DRIVE>/nsosyal-bstar/results/01_baseline_berturk/`:

| File | Contents |
|---|---|
| `metrics.json` | all scalars below |
| `classification_report.txt` | sklearn report, overall + per slice |
| `dev_predictions.csv` | `row_id, text, gold, pred, confidence, slice` |
| `run_config.json` | seeds, hashes, model string, hyperparams, git SHA, timestamp |

`metrics.json` schema:

```json
{
  "run_id": "01_baseline_berturk",
  "git_sha": "...",
  "sanity_gate": {"lexicon_free_off": 3892, "total_off": 6131, "passed": true},
  "keyword_filter": {"macro_f1": null, "off_recall": null},
  "berturk": {
    "overall": {"macro_f1": null, "off_precision": null, "off_recall": null},
    "lexicon_hit":  {"n": null, "off_recall": null},
    "lexicon_free": {"n": null, "off_recall": null},
    "recall_gap": {"delta": null, "ci_low": null, "ci_high": null}
  }
}
```

Nulls are placeholders for real values, never for estimates. A field that could
not be computed stays null with a note — it does not get filled by inference.

Append the run to `docs/RESULTS_LOG.md`.

---

## Pre-registered decision rule

**Pre-registered 15 Aug 2026, committed to git before any BERTurk number
existed. Not to be revised after seeing results.** Fixed in advance so the
interpretation cannot be fitted to whatever comes back.

Three outcomes, on the bootstrap CI of the OFF-recall gap (lexicon_hit −
lexicon_free):

1. **CI excludes zero → gap survives.** The project's central claim holds.
   Phase 2 opens: failure analysis on the confidently-wrong false negatives.
2. **CI includes zero AND the point estimate is under ~5pp → gap genuinely
   closed.** BERTurk learns implicit toxicity without lexical cues; the
   lexicon-free axis is then a finding about keyword filters only, not a model
   weakness. A real result, not a failure — it forces same-day reweighting of
   the project toward obfuscation robustness and calibration as the technical
   core, and the report's framing changes accordingly.
3. **CI includes zero BUT the point estimate is large → INCONCLUSIVE ON DEV.**
   Not "closed". Report the point estimate with its honest CI width and state
   plainly that dev lacks the statistical power to resolve it. Do **not** promote
   it to a finding. Do **not** touch the official test set to resolve it.

**Power basis (why outcome 3 exists).** The dev recall denominators are 355
gold-OFF rows in `lexicon_hit` and 565 in `lexicon_free`, which puts roughly
±6pp on the 95% CI of the *difference*. A ~20pp gap is detectable at that
resolution; a ~4pp gap is not, and is not a claim worth making. An
underpowered null is silence, not evidence of absence.

---

## Pre-registered constraint — per-slice comparison is OFF-RECALL ONLY

**Pre-registered 15 Aug 2026, committed to git before any BERTurk number
existed.** Binding on every later phase, not just this one.

The two slices have sharply different base rates, measured on the frozen dev
split: **57.8% OFF in `lexicon_hit`** (355 of 614) versus **13.6% OFF in
`lexicon_free`** (565 of 4,150).

OFF-recall conditions on gold = OFF, so it is immune to that. Per-slice macro-F1
and per-slice accuracy are not: a difference between the slices on either metric
is driven by class balance and would be reported as if it were a difference in
model behaviour. If per-slice F1 or accuracy appears in any later phase as a
slice **comparison**, it is measuring the wrong thing.

Consequences already applied in this phase:

- `metrics.json` per-slice blocks carry `off_recall` (with CI), the support
  counts, the base rate, and the **raw confusion counts** (`tp/fp/fn/tn`), and
  deliberately do **not** carry a per-slice macro-F1. The constraint is against
  pre-computing a misleading cross-slice comparison, not against retaining
  primitives: phase 4 needs false-positive behaviour *within* `lexicon_free` to
  characterise the deferral queue, and OFF-recall alone cannot give it. Raw
  counts also let any later phase recompute a within-slice metric without
  re-running training.
- The per-slice sections of `classification_report.txt` are kept — the output
  contract asks for them and they are useful *within* a slice — but the file
  carries a header saying the F1 columns are not comparable across slices.
- Overall (unsliced) macro-F1 is unaffected by any of this and remains the
  headline metric for the Section 8 matrix rows.

---

## Explicitly not in scope — and where it lives instead

| Deferred here | Owning phase |
|---|---|
| Reading the false negatives, designing the defense | Phase 2 |
| Obfuscation generators, held-out attack families, cross-corpus | Phase 3 |
| Calibration, risk–coverage, operating points | Phase 4 |
| Official test set, offline demo | Phase 5 |
| ConvBERTurk | cut — reinstated only if Phase 4 finishes early |

The brief's stubbing rationale holds: producing plausible metric code before
there is a verified number creates a second source of truth that is wrong in a
way nobody notices until the report is being written.

---

## Implementation notes (added during execution — not part of the original spec)

- The driver is `phase01_baseline.py`, run in two stages:
  `--stage preflight` (preconditions, split, sanity gate, keyword baseline; no
  torch, runs on the local Python 3.14 venv) and `--stage train` (the same
  checks re-run, then training + evaluation on Colab). Preflight exists so the
  S2 sanity gate is verified *before* GPU time is spent, not after.
- The split file is authoritative once written: `data_io.get_split()` creates it
  on first use, then loads and verifies it (corpus SHA + id membership + no
  train/dev overlap). It also records `matches_regeneration` — whether a fresh
  seed-42 split would still reproduce the file — as a drift detector that
  reports rather than silently corrects.
- Per-slice keyword-filter numbers are omitted deliberately: the filter predicts
  OFF on `lexicon_hit` and NOT on `lexicon_free` by construction, so its slice
  recalls are 1.0 and 0.0 tautologically.
- No class weighting and no threshold tuning in the baseline (see the docstring
  in `src/models.py`): both would move OFF-recall, which is the quantity being
  measured.
- `metrics.json` carries `decision_rule_applied: null` until a human writes the
  verdict into `docs/RESULTS_LOG.md`.
- **The driver does not append to `docs/RESULTS_LOG.md`.** Two of that table's
  columns are Interpretation and Decision, and a script cannot honestly fill
  them; an auto-appended row carrying placeholder text in the project's
  engineering log is worse than no row. Instead the run writes a fifth file,
  `results_log_row.md` — the numbers pre-filled, the two judgement columns left
  as explicit TODO — which a human pastes in after writing the verdict. This
  makes the log an output-contract file in practice, one more than the table
  above lists.
- The post-training path is exercised locally before it ever reaches a GPU:
  `tests/_dryrun_phase01_outputs.py` calls the same `prepare()` and
  `evaluate_and_write()` the driver calls, with mock predictions substituted for
  the model, and asserts the structure of all five output files. Two modes:
  `all_not` (degenerate — OFF-precision undefined, exercising the None-handling
  path) and `random` (non-degenerate confusion matrices and CI spread). Every
  artifact it writes is stamped `MOCK_RUN`, it writes only to a temp directory,
  and `evaluate_and_write` refuses to write mock output into the canonical run
  directory. The production CLI has no flag that reaches the mock path.
