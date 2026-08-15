# NSosyal B* — Results Log

One entry per **completed, verified** experiment. Written like an engineering
log, not a chat message: what ran, the headline numbers, the interpretation,
and the decision it led to. The technical report's methodology and results
sections get drafted directly from this file.

Entries are appended, never rewritten. If a later result contradicts an earlier
one, add a new entry saying so — do not edit the old entry.

| Date | Step | What ran | Headline numbers | Interpretation | Decision |
|---|---|---|---|---|---|
| 2026-08-15 | Day 1 reproduction check | `day1_gate_en.py --out results/day1_report_rerun.json`, then `tests/_verify_day1_reproduction.py` (local, Python 3.14) | 16/16 frozen fields reproduce exactly. Corpus sha256 `8509c01c…`, lexicon sha256 `0f5a05f5…` both match the frozen record. | The port into `src/` has not drifted; the Day 1 premise (3,892/6,131) still stands on the same bytes. | Phase 01 precondition 1 and 2 cleared. |
| 2026-08-15 | Phase 01 preflight (no GPU) | `phase01_baseline.py --stage preflight` (local) | Sanity gate PASS: tagger reproduces 3,892 lexicon-free OFF of 6,131 on the full corpus. Split seed 42: train 26,992 (5,211 OFF) / dev 4,764 (920 OFF), dev fingerprint `034415af3a23b388…`. Dev slices: lexicon_hit 614 rows (355 OFF), lexicon_free 4,150 rows (565 OFF). Keyword filter on dev — macro-F1 **0.6799** [0.6621, 0.6969], OFF-recall **0.3859** [0.3539, 0.4187], OFF-precision 0.5782. | The frozen matcher used for slicing is provably the Day 1 one. Dev OFF-recall of the filter (0.386) sits close to the corpus-wide 2,239/6,131 = 0.365, as a correct stratified split should. 61% of dev OFF examples carry no lexicon cue at all. | Split written to `data/splits/split_seed42.json` and committed — it is now the authoritative dev set for every row of the Section 8 matrix. Matrix row 1 (keyword filter) is measured and closed. Proceed to `--stage train` on Colab. No BERTurk number exists yet. |
