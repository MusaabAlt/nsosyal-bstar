# Handoff — paste this at the start of a new chat

> **Partly superseded (15 Aug 2026).** The "Next step" section below is now
> specified in full by [`phases/01_baseline_diagnosis.md`](../phases/01_baseline_diagnosis.md),
> and the compute target is decided: **Colab Pro+**, not Kaggle. Everything else
> here still holds. Phase 01 preflight is done; BERTurk has not been trained.

Continuing the **NSosyal B\*** project (Turkish adversarial toxicity detection +
review triage). The scaffold phase is finished; the modeling phase has not
started.

## Read first — both are binding

Before anything else, read these two files in the repo:

- `docs/claude_master_brief.md` — **how** you must work (professional execution
  mode, one verified step at a time, never fabricate results, gate discipline)
- `docs/phase_briefing.md` — **what** we are building (method, data role
  separation, anti-circularity rules, the final comparison matrix)

Treat both as specification, not suggestion. If a request of mine conflicts with
a rule in them, flag the conflict instead of silently complying.

## Environment

- Repo: `C:\Projects\NSosyal` (Windows, PowerShell). Git repo, branch `master`,
  one commit: `c33d1bd "Project scaffold + ported Day 1 lexicon logic"`.
- Local venv `.venv` runs **Python 3.14** — currently only `pytest` is
  installed. `pip install -r requirements.txt` may fail locally on 3.14 (torch
  wheels lag). This doesn't block anything: training is a GPU job that runs on
  Kaggle/Colab, and PyCharm is only for writing and reviewing code.
- The repo is **local-only** — no GitHub remote yet. It must be created
  **private**; `src/obfuscation.py` will generate functional evasion text.
- Compute target is unresolved in the source docs: the setup prompt says Colab
  Pro+, the phase briefing says Kaggle. `config.py` handles both, so this is
  decided when the first training run happens, not before.

## What already exists and is verified

**Day 1 gate is complete and frozen.** `results/day1_report.json`:

- 31,756 training rows, 6,131 OFF (19.3%)
- Lexicon frozen: 695 entries, `karaliste.txt`, sha256 recorded
- **3,892 / 6,131 OFF tweets (63%) evade the lexicon** under agglutination-aware
  root matching — this is the empirical premise of the whole project
- Agglutination delta (root − literal) = 452
- Slice refinement: 5 self-censored (`o***`), 208 abbreviated profanity
  (`aq`/`mk`), 3,679 truly clean implicit, 2,755 demo/report-safe

That logic was ported from the original script into `src/` and re-verified:
all 16 reported fields reproduce the frozen record exactly. Re-check any time
with `python tests/_verify_day1_reproduction.py`.

## Repo layout and current state

```
config.py        env-driven paths (NSOSYAL_ENV=local|kaggle|colab,
                 NSOSYAL_DATA, NSOSYAL_ROOT). SEED=42, MAX_LEN=128,
                 DEV_FRACTION=0.15. No script hardcodes a path.
src/
  data_io.py     DONE  — readers + format-trap guards + LABEL_MAP_3TO2
  lexicon.py     DONE  — Turkish casing, literal/root matching, slice filters
  obfuscation.py PARTIAL — assert_disjoint() implemented; generators are stubs
  models.py      STUB
  calibration.py STUB
  evaluate.py    STUB
day1_gate_en.py  thin driver over src/ (does not touch the test set)
tests/           17 passing tests for the confirmed format traps + guards
docs/            briefings, RESULTS_LOG.md (header row only, empty by design)
results/         day1_report.json (committed evidence)
data/            gitignored; raw corpora present locally
demo/app.py      STUB
legacy/          superseded scripts, do not run
```

Stubs raise `NotImplementedError` deliberately. **Do not fill them in with
invented code.** They get written when the corresponding step is specified, so
`src/` and the execution-phase scripts stay in sync — a plausible-looking
placeholder would become a second, unverified source of truth.

## Guards that are already code, not tribal knowledge

- `data_io.load_coltekin_test()` raises `PermissionError` unless the caller
  passes `run_final_test=True` — the official test set is touched exactly once,
  at the end.
- `obfuscation.assert_disjoint(train_families, eval_families)` raises if a
  robustness number would be measured on an attack family the model trained on.
- `data_io.assert_binary_labels()` raises on any label outside `{OFF, NOT}` —
  a broken TSV read announces itself instead of quietly dropping rows.
- `data_io.map_3way_to_binary()` raises on unmapped Mayda/Beyhan labels rather
  than guessing.
- `day1_gate_en.py` refuses to overwrite an existing freeze record without
  `--force`.

## Data on disk

```
data/coltekin/offenseval-tr-training-v1.tsv    31,756 rows, train + dev
data/coltekin/offenseval-tr-testset-v1.tsv     official test, DO NOT TOUCH YET
data/coltekin/offenseval-tr-labela-v1.tsv      gold, comma-separated
data/lexicon/karaliste.txt                     frozen, 695 entries
data/mayda/     EMPTY — cross-corpus source not downloaded yet
data/beyhan/    EMPTY — cross-corpus source not downloaded yet
```

## One known quirk, deliberately preserved

`lexicon.tokens()` splits on `\w+`, which strips the `@`, so `"@USER"` yields the
token `user` and the `"@user"` entry in `SKIP` never fires. Verified harmless —
no lexicon entry equals or prefixes `user`, and it isn't in `ABBREV_PROFANITY`,
so no Day 1 number changes. Left as-is because the frozen record was produced
with this behaviour; a characterisation test pins it so changing it becomes a
deliberate re-freeze rather than silent drift.

## Next step

Day 2: fine-tune BERTurk (`dbmdz/bert-base-turkish-cased`) on the 85/15
stratified split of the Çöltekin training set, then compare OFF-recall on the
lexicon-hit vs lexicon-free slices of the **dev** set. Per the master brief:
propose that one script, tell me what it will show and why, then stop and wait
for me to run it and paste back real output. Do not write the diagnosis script
in advance of seeing the training output.

The failure analysis drives the defense design — do not commit to an
obfuscation defense (or any fix) before the failures prove that is the real
failure mode.

## Deadlines

Application 20 Aug 2026; technical report **24 Aug 2026, 17:00 TSİ**.
