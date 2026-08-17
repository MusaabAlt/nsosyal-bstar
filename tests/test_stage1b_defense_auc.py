"""Tests for phase09_stage1b_defense_auc.py, written before the dumps arrived.

Stage 1b cannot run yet -- both prediction dumps live only on the Drive mirror
and the mount is unanswered. That makes these tests the only thing standing
between the pre-registration and a wrong number later, so they check the two
properties the stage's answer depends on:

  * the bootstrap is genuinely PAIRED -- both systems scored on the same
    resampled rows. An accidentally unpaired version would not fail loudly; it
    would return a wider interval that still looks like a result.
  * the C9-15 rule separates FLAT from MARGINAL from IMPROVED at exactly the
    declared boundaries, so "the intervention improved ranking" cannot be
    claimed from a delta too small to account for the recall gain.

Plus the refusal path: a missing dump must abort, never fall back to the
phase-01 baseline dump as a stand-in for run_raw (C9-12).
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase09_stage1_auc as s1
import phase09_stage1b_defense_auc as s1b


# --------------------------------------------------------------------------
# C9-15 -- the interpretation rule
# --------------------------------------------------------------------------

def test_verdict_improved_only_at_or_above_the_declared_floor():
    assert s1b.verdict_1b(0.01, 0.002, 0.02) == "DISCRIMINATION IMPROVED"
    assert s1b.verdict_1b(0.08, 0.05, 0.11) == "DISCRIMINATION IMPROVED"


def test_verdict_marginal_is_resolvable_but_too_small():
    """The Stage 1 trap: a CI excluding zero on a delta too small to matter."""
    assert s1b.verdict_1b(0.0099, 0.004, 0.016) == "MARGINAL"
    assert s1b.verdict_1b(0.001, 0.0005, 0.002) == "MARGINAL"


def test_verdict_flat_whenever_the_interval_touches_zero():
    assert s1b.verdict_1b(0.05, -0.001, 0.10) == "FLAT"
    assert s1b.verdict_1b(0.05, 0.0, 0.10) == "FLAT"
    assert s1b.verdict_1b(-0.02, -0.05, 0.01) == "FLAT"


def test_verdict_reports_a_worsening_rather_than_hiding_it():
    assert s1b.verdict_1b(-0.03, -0.06, -0.005) == "ORDERING WORSENED"
    assert s1b.verdict_1b(-0.03, -0.06, 0.0) == "FLAT"     # touching zero is not a worsening


def test_verdict_branches_are_exhaustive():
    import random
    rng = random.Random(2)
    for _ in range(3000):
        lo = rng.uniform(-0.2, 0.2)
        hi = lo + rng.uniform(0.0, 0.3)
        d = rng.uniform(lo, hi)
        assert s1b.verdict_1b(d, lo, hi) in {
            "DISCRIMINATION IMPROVED", "MARGINAL", "FLAT", "ORDERING WORSENED"}


def test_the_floor_is_the_preregistered_one():
    assert s1b.SMALL_DELTA == 0.01


# --------------------------------------------------------------------------
# C9-13 -- the pairing, which is the load-bearing part
# --------------------------------------------------------------------------

def _logit_shift(p, c):
    """A strictly monotone move of every probability, staying inside (0, 1).

    This is the right model of the thing being tested: a temperature or bias
    change moves scores without touching their order. Adding a constant and
    clipping at 1.0 would NOT model it -- clipping manufactures ties and
    destroys the ordering the test is about.
    """
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return 1.0 / (1.0 + np.exp(-(np.log(p / (1 - p)) + c)))


def _pair(n_pos=80, n_neg=300, seed=0, shift=0.0):
    """Treatment = control shifted monotonically: ordering identical by construction."""
    rng = np.random.default_rng(seed)
    pos, neg = rng.random(n_pos), rng.random(n_neg)
    a = s1.Slice("x", pos, neg)
    b = s1.Slice("x", _logit_shift(pos, shift), _logit_shift(neg, shift))
    return a, b


def test_a_pure_monotone_score_shift_leaves_the_paired_delta_at_zero():
    """The exact hypothesis Stage 1b tests. Moving every score monotonically
    changes recall at a fixed threshold and must not change AUC at all."""
    a, b = _pair(shift=1.0)
    # the shift is real: it moves rows across the frozen threshold
    assert (b.pos > 0.5).sum() > (a.pos > 0.5).sum()
    _, _, dd = s1b.paired_delta(a, b, n_boot=200, seed=1)
    assert s1.auc_ties(b.pos, b.neg) == pytest.approx(s1.auc_ties(a.pos, a.neg), abs=1e-12)
    ci = s1.ci_of(dd)
    assert ci["ci_low"] == 0.0 and ci["ci_high"] == 0.0
    assert s1b.verdict_1b(0.0, ci["ci_low"], ci["ci_high"]) == "FLAT"


def test_pairing_is_real_not_two_independent_resamples():
    """Both systems must be scored on the SAME resampled rows.

    Under a pure shift the paired delta is identically zero in every replicate.
    An unpaired implementation would draw two different samples and produce a
    non-degenerate spread -- a wider interval that still reads as a result.
    """
    a, b = _pair(shift=0.8, seed=7)
    _, _, dd = s1b.paired_delta(a, b, n_boot=300, seed=3)
    assert max(abs(x) for x in dd) < 1e-12

    rng = np.random.default_rng(3)
    unpaired = []
    for _ in range(300):
        cpa, cna = a.counts(rng.integers(0, a.n_pos, a.n_pos), rng.integers(0, a.n_neg, a.n_neg))
        cpb, cnb = b.counts(rng.integers(0, b.n_pos, b.n_pos), rng.integers(0, b.n_neg, b.n_neg))
        unpaired.append(b.auc_from_counts(cpb, cnb) - a.auc_from_counts(cpa, cna))
    assert max(abs(x) for x in unpaired) > 1e-6, "the contrast this test rests on is gone"


def test_paired_delta_recovers_a_real_reordering():
    """Only the positives are moved, so OFF/NOT pairs genuinely change order --
    which is what "discrimination improved" means and what a global shift is not."""
    rng = np.random.default_rng(11)
    pos, neg = rng.random(120), rng.random(400)
    a = s1.Slice("x", pos, neg)
    b = s1.Slice("x", _logit_shift(pos, 1.0), neg)
    _, _, dd = s1b.paired_delta(a, b, n_boot=300, seed=5)
    d = s1.auc_ties(b.pos, b.neg) - s1.auc_ties(a.pos, a.neg)
    assert d > 0.01
    ci = s1.ci_of(dd)
    assert ci["ci_low"] > 0
    assert s1b.verdict_1b(d, ci["ci_low"], ci["ci_high"]) == "DISCRIMINATION IMPROVED"


def test_paired_bootstrap_is_deterministic_under_a_fixed_seed():
    a, b = _pair(seed=13)
    assert s1.ci_of(s1b.paired_delta(a, b, n_boot=200, seed=42)[2]) == \
           s1.ci_of(s1b.paired_delta(a, b, n_boot=200, seed=42)[2])


# --------------------------------------------------------------------------
# C9-14 -- threshold crossings
# --------------------------------------------------------------------------

def _rows(scores, gold="OFF", slice_name="lexicon_free"):
    return [{"row_id": str(i), "gold": gold, "slice": slice_name,
             "p_off": v, "pred": "OFF" if v > 0.5 else "NOT"}
            for i, v in enumerate(scores)]


def test_crossings_count_each_direction_separately():
    a = _rows([0.4, 0.6, 0.45, 0.9])
    b = _rows([0.7, 0.3, 0.45, 0.95])
    c = s1b.crossings(a, b, "lexicon_free", "OFF")
    assert c == {"NOT_to_OFF": 1, "OFF_to_NOT": 1, "net": 0}


def test_crossings_ignore_other_slices_and_the_other_gold_class():
    a = _rows([0.4]) + _rows([0.4], gold="NOT") + _rows([0.4], slice_name="lexicon_hit")
    b = _rows([0.9]) + _rows([0.9], gold="NOT") + _rows([0.9], slice_name="lexicon_hit")
    assert s1b.crossings(a, b, "lexicon_free", "OFF")["NOT_to_OFF"] == 1


# --------------------------------------------------------------------------
# C9-12 -- provenance and the refusal path
# --------------------------------------------------------------------------

def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
        for r in rows:
            w.writerow([r["row_id"], "t", r["gold"], r["pred"], f"{r['p_off']:.6f}", r["slice"]])


def test_a_missing_dump_aborts_instead_of_substituting(tmp_path):
    """C9-12: no fallback to the phase-01 baseline dump for run_raw."""
    present = tmp_path / "a.csv"
    _write_csv(present, _rows([0.9, 0.1]))
    with pytest.raises(SystemExit, match="BLOCKED"):
        s1b.load_aligned(str(present), str(tmp_path / "missing.csv"))


def test_misaligned_dumps_abort(tmp_path):
    """A silently unpaired comparison would look tighter, not broken."""
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    _write_csv(a, _rows([0.9, 0.1]))
    rows_b = _rows([0.9, 0.1])
    rows_b[1]["gold"] = "NOT"                     # gold must be model-independent
    _write_csv(b, rows_b)
    with pytest.raises(SystemExit, match="disagree on row"):
        s1b.load_aligned(str(a), str(b))


def test_provenance_check_rejects_a_dump_that_does_not_match_the_record(tmp_path):
    comp = tmp_path / "comparison.json"
    comp.write_text(json.dumps({"runs": {"raw": {
        "macro_f1": 0.5, "off_recall": 1.0, "lexicon_free_off_recall": 1.0,
        "lexicon_hit_off_recall": 1.0, "lexicon_hit_fp_rate": 0.0,
        "false_positives_total": 999}}}), encoding="utf-8")
    rows = _rows([0.9]) + _rows([0.1], gold="NOT") + \
        _rows([0.9], slice_name="lexicon_hit") + _rows([0.1], gold="NOT", slice_name="lexicon_hit")
    with pytest.raises(SystemExit, match="C9-12"):
        s1b.check_run("control", rows, "raw", comparison_path=str(comp))


def test_recorded_figures_are_read_from_the_real_comparison_file():
    """The control's recorded lexicon_free recall is the 0.5628 the +0.0336 is measured from."""
    raw = s1b.recorded_figures("raw")
    trt = s1b.recorded_figures("1a1b_d")
    assert raw["lexicon_free_off_recall"] == 0.5628
    assert trt["lexicon_free_off_recall"] == 0.5965
    assert round(trt["lexicon_free_off_recall"] - raw["lexicon_free_off_recall"], 4) == 0.0337
