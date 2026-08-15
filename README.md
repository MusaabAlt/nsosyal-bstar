# NSosyal B* — Turkish adversarial toxicity detection + review triage

Catches Turkish offensive content that slips past a keyword filter — because it
is orthographically obfuscated (`aptal` → `a.p.t.a.l`) or because it carries no
profanity word at all — and pairs every prediction with a calibrated confidence
that decides: auto-resolve, or send to a human reviewer.

The deliverable is **not** "a better toxicity model". It is a rigorous
comparison proving which defense actually works in Turkish, plus a triage layer
that connects model failures to human-review workload.

Full spec: [`docs/phase_briefing.md`](docs/phase_briefing.md) (what we are
building) and [`docs/claude_master_brief.md`](docs/claude_master_brief.md) (how
the work is run). Both are binding.

**Repo stays private until submission** — `src/obfuscation.py` generates
functional evasion text.

## Status

| Step | State |
|---|---|
| Day 1 — data loading + lexicon freeze + go/no-go gate | ✅ done, `results/day1_report.json` |
| Phase 0 — private GitHub remote + Colab clone | remote ✅ `MusaabAlt/nsosyal-bstar` (private, verified 404 unauthenticated); Colab clone not yet exercised |
| Phase 1 — [baseline diagnosis](phases/01_baseline_diagnosis.md) | preflight ✅ (split + sanity gate + keyword row); BERTurk training not yet run |
| Phase 2 — failure analysis + defense design | not started |
| Phase 3 — obfuscation families + cross-corpus (Mayda, Beyhan) | not started |
| Phase 4 — calibration + risk–coverage | not started |
| Phase 5 — official Çöltekin test run (once) + offline demo | not started |
| ConvBERTurk | cut; reinstated only if phase 4 finishes early |

Day 1 headline: **3,892 of 6,131 OFF tweets (63%) evade a 695-word lexicon**
even with agglutination-aware root matching.

## Layout

```
config.py        every path + constant; no script hardcodes a location
src/             source of truth — notebooks import from here, never re-implement
  data_io.py     corpus readers with the format traps guarded in code
  lexicon.py     Turkish-aware casing + literal/root lexicon matching
  obfuscation.py attack families D (train) / H (eval) + the disjointness guard
  models.py      BERTurk / ConvBERTurk wrappers                     [stub]
  calibration.py temperature scaling + risk–coverage                [stub]
  evaluate.py    one metric path shared by every system             [stub]
data/            gitignored — raw corpora live here locally only
results/         experiment JSON (committed); everything else ignored
docs/            briefings + RESULTS_LOG.md
tests/           regression tests for the confirmed format traps
demo/            offline side-by-side demo                          [stub]
```

Stubs raise `NotImplementedError` on purpose. They get written when the
corresponding step is specified, so `src/` and the execution-phase scripts stay
in sync — a plausible-looking placeholder implementation would become a second,
unverified source of truth.

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

## Running on Kaggle / Colab

`config.py` is environment-driven — the same `src/` code runs unmodified:

```python
import os
os.environ["NSOSYAL_ENV"] = "kaggle"        # or "colab"
os.environ["NSOSYAL_DATA"] = "/kaggle/input/nsosyal-data"   # optional override
import config
```

`NSOSYAL_ROOT` overrides the repo root outright if the clone lands somewhere
unexpected. Training is a GPU job and does not run locally; PyCharm is for
writing, reviewing and version-controlling the code.

## Ground rules

These are enforced in code where possible, not left as tribal knowledge:

- **Seed 42** everywhere data is split, shuffled or a model is initialised, and
  stated in every result file.
- **Every experiment writes a step-named JSON** into `results/`. Nothing is
  silently overwritten — `day1_gate_en.py` refuses to clobber without `--force`.
- **The official Çöltekin test set is touched exactly once, at the end.**
  `data_io.load_coltekin_test()` raises `PermissionError` unless a caller passes
  `run_final_test=True`, which in practice means an explicit `--run_final_test 1`
  flag that defaults to off.
- **Training obfuscation ≠ evaluation obfuscation.** `obfuscation.assert_disjoint()`
  raises if a robustness number would be measured on an attack family the model
  was trained on. That circularity killed an earlier version of this idea.
- **The lexicon is frozen** (695 entries, sha256 in `results/day1_report.json`).
  Adding words after seeing a result is post-hoc tuning and invalidates the
  lexicon-free measurement the whole project rests on.
- **`docs/RESULTS_LOG.md` gets one entry per completed experiment** — date, what
  ran, headline numbers, interpretation, decision.
- **Commit after every completed, verified step.** Messages state the finding,
  not the action: `"Day 2: BERTurk baseline, lexicon-free gap confirmed (delta=0.09)"`.

## Data sources

| Role | Source | Note |
|---|---|---|
| Train + diagnose | Çöltekin OffensEval-2020 TR | 31,756 rows, 85/15 train/dev |
| Final test | Çöltekin official test + gold | touch once |
| Cross-corpus | [Mayda](https://github.com/imayda/turkish-hate-speech-dataset-1), [Beyhan](https://github.com/verimsu/Turkish-HS-Dataset) | never trained on; 3-way labels → `LABEL_MAP_3TO2` |
| Lexicon | [turkce-kufur-karaliste](https://github.com/ooguz/turkce-kufur-karaliste) | frozen Day 1 |

Rejected: `Overfit-GM/turkish-toxic-language` — merged (likely contains
Çöltekin → contamination) and partly pseudo-labeled.
