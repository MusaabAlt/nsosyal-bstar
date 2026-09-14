"""Tests for phase09_stage1_auc.py, written before the real scores were loaded.

Two of these carry the whole stage:

  * `test_auc_is_invariant_to_the_base_rate` -- AUC not moving when the negative
    class is duplicated IS the reason this stage answers the reviewer's
    objection. If it moved, the analysis would be measuring the thing it was
    built to control for.
  * `test_average_precision_does_move_with_the_base_rate` -- the same
    manipulation on AP, which is why C9-9 forbids AP from arguing the verdict.
    The ban is a property of the metric, and it is demonstrated, not asserted.

The verdict rule is tested on both sides of every boundary because C9-5's whole
purpose is that no result can be argued into a branch after the fact.
"""

import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase09_stage1_auc as s1
from src import lexicon


# --------------------------------------------------------------------------
# the statistic
# --------------------------------------------------------------------------

def test_auc_of_perfect_separation_and_of_its_reverse():
    assert s1.auc_ties([0.9, 0.8, 0.7], [0.1, 0.2]) == 1.0
    assert s1.auc_ties([0.1, 0.2], [0.9, 0.8, 0.7]) == 0.0


def test_all_ties_give_exactly_one_half():
    """C9-2: half credit. A model that scores everything identically ranks nothing."""
    assert s1.auc_ties([0.5] * 7, [0.5] * 4) == 0.5


def test_ties_get_half_credit_not_zero_and_not_one():
    # one positive tied with the single negative, one clearly above it
    assert s1.auc_ties([0.5, 0.9], [0.5]) == pytest.approx(0.75)


def test_auc_matches_sklearn_on_random_scores():
    """An independent implementation, including its tie handling."""
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(7)
    for _ in range(20):
        pos = np.round(rng.random(60), 2)     # rounding manufactures ties on purpose
        neg = np.round(rng.random(90), 2)
        y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        assert s1.auc_ties(pos, neg) == pytest.approx(
            roc_auc_score(y, np.r_[pos, neg]), abs=1e-12)


def test_average_precision_matches_sklearn():
    from sklearn.metrics import average_precision_score
    rng = np.random.default_rng(11)
    for _ in range(20):
        pos = np.round(rng.random(40), 2)
        neg = np.round(rng.random(120), 2)
        y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
        assert s1.average_precision(pos, neg) == pytest.approx(
            average_precision_score(y, np.r_[pos, neg]), abs=1e-12)


def test_auc_is_invariant_to_the_base_rate():
    """The property the entire stage rests on.

    Duplicating every negative changes the slice's base rate and changes nothing
    about ranking. AUC must not move. This is why an AUC comparison answers
    "is the recall gap just where the threshold sits?" and a recall comparison
    cannot.
    """
    rng = np.random.default_rng(3)
    pos, neg = rng.random(50), rng.random(70)
    base = s1.auc_ties(pos, neg)
    for k in (2, 5, 20):
        assert s1.auc_ties(pos, np.tile(neg, k)) == pytest.approx(base, abs=1e-12)


def test_average_precision_does_move_with_the_base_rate():
    """C9-9's ban, demonstrated rather than asserted."""
    rng = np.random.default_rng(3)
    pos, neg = rng.random(50), rng.random(70)
    assert s1.average_precision(pos, np.tile(neg, 10)) < s1.average_precision(pos, neg) - 0.1


def test_auc_is_invariant_to_any_monotone_rescaling_of_scores():
    """Threshold-free means calibration-free: squashing the scores changes the
    probabilities and every fixed-threshold metric, and must not change AUC."""
    rng = np.random.default_rng(5)
    pos, neg = rng.random(40), rng.random(60)
    squashed = lambda v: 1.0 / (1.0 + np.exp(-8 * (v - 0.5)))
    assert s1.auc_ties(squashed(pos), squashed(neg)) == pytest.approx(
        s1.auc_ties(pos, neg), abs=1e-12)


def test_slice_count_path_agrees_with_the_direct_computation():
    """The bootstrap uses the O(K) count path; it must equal the pairwise form."""
    rng = np.random.default_rng(13)
    pos = np.round(rng.random(80), 2)
    neg = np.round(rng.random(200), 2)
    sl = s1.Slice("t", pos, neg)
    cp, cn = sl.counts()
    assert sl.auc_from_counts(cp, cn) == pytest.approx(s1.auc_ties(pos, neg), abs=1e-12)


# --------------------------------------------------------------------------
# C9-5: the verdict rule, on both sides of every boundary
# --------------------------------------------------------------------------

def test_verdict_confirms_only_above_the_large_threshold_with_a_positive_interval():
    assert s1.verdict(0.05, 0.01, 0.09) == "CONFIRMS"      # exactly at LARGE
    assert s1.verdict(0.30, 0.25, 0.35) == "CONFIRMS"


def test_verdict_intermediate_band_is_declared_not_spun():
    assert s1.verdict(0.02, 0.005, 0.04) == "INTERMEDIATE"  # exactly at SMALL
    assert s1.verdict(0.0499, 0.01, 0.09) == "INTERMEDIATE"  # just under LARGE


def test_verdict_narrows_below_the_floor_even_with_a_tight_interval():
    assert s1.verdict(0.0199, 0.018, 0.022) == "NARROWS"


def test_verdict_narrows_whenever_the_interval_touches_zero():
    assert s1.verdict(0.30, -0.01, 0.60) == "NARROWS"       # big point estimate, no support
    assert s1.verdict(0.30, 0.0, 0.60) == "NARROWS"         # touching counts as including
    assert s1.verdict(0.001, -0.05, 0.05) == "NARROWS"


def test_verdict_reverses_only_when_the_whole_interval_is_below_zero():
    assert s1.verdict(-0.10, -0.20, -0.02) == "REVERSES"
    assert s1.verdict(-0.10, -0.20, 0.0) == "NARROWS"       # touches zero -> not a reversal


def test_verdict_branches_are_exhaustive():
    """No (G, CI) can fall through. A rule with a hole is a rule with a choice."""
    rng = random.Random(1)
    for _ in range(3000):
        lo = rng.uniform(-0.4, 0.4)
        hi = lo + rng.uniform(0.0, 0.5)
        g = rng.uniform(lo, hi)
        assert s1.verdict(g, lo, hi) in {"CONFIRMS", "INTERMEDIATE", "NARROWS", "REVERSES"}


# --------------------------------------------------------------------------
# C9-8: matched operating points
# --------------------------------------------------------------------------

def _toy():
    # positives high, negatives low, with overlap
    pos = np.array([0.9, 0.8, 0.7, 0.6, 0.4])
    neg = np.array([0.5, 0.3, 0.2, 0.1])
    return s1.Slice("toy", pos, neg)


def test_match_precision_takes_the_lowest_threshold_that_attains_the_target():
    """C9-8 declares 'lowest' in advance because it maximises recall at the
    matched precision -- the choice most favourable to the model."""
    sl = _toy()
    cp, cn = sl.counts()
    m = s1.match_precision(sl, cp, cn, 0.8)
    assert not m["failed"]
    assert m["precision"] >= 0.8
    # a lower threshold would have to miss the target
    tp, flagged, thr = sl.sweep(cp, cn)
    lower = [j for j, t in enumerate(thr) if t < m["threshold"]]
    assert all(flagged[j] == 0 or tp[j] / flagged[j] < 0.8 for j in lower)


def test_match_precision_reports_failure_instead_of_substituting_a_target():
    sl = _toy()
    cp, cn = sl.counts()
    m = s1.match_precision(sl, cp, cn, 1.01)      # unattainable by construction
    assert m["failed"] is True
    assert "best_attainable_precision" in m


def test_match_flag_rate_breaks_ties_toward_the_lower_threshold():
    sl = _toy()
    cp, cn = sl.counts()
    m = s1.match_flag_rate(sl, cp, cn, 1.0)       # flag everything
    assert m["threshold"] == -np.inf
    assert m["recall"] == 1.0


def test_reference_point_uses_the_frozen_half_threshold():
    sl = _toy()
    cp, cn = sl.counts()
    r = s1.reference_point(sl, cp, cn)
    # score > 0.5 flags four positives and no negative
    assert r["recall"] == pytest.approx(4 / 5)
    assert r["precision"] == pytest.approx(1.0)
    assert r["flag_rate"] == pytest.approx(4 / 9)


# --------------------------------------------------------------------------
# C9-3: the bootstrap
# --------------------------------------------------------------------------

def test_bootstrap_is_deterministic_under_the_fixed_seed():
    rng = np.random.default_rng(21)
    hit = s1.Slice("hit", rng.random(60), rng.random(50))
    free = s1.Slice("free", rng.random(80), rng.random(400))
    a = s1.bootstrap_pair(hit, free, n_boot=200, seed=42)
    b = s1.bootstrap_pair(hit, free, n_boot=200, seed=42)
    assert s1.ci_of(a[2]) == s1.ci_of(b[2])


def test_bootstrap_preserves_every_cell_size():
    """C9-3: each of the four cells is resampled to its OWN size, so the
    denominators 355/259/565/3585 survive into every replicate."""
    rng = np.random.default_rng(22)
    hit = s1.Slice("hit", rng.random(31), rng.random(17))
    free = s1.Slice("free", rng.random(43), rng.random(97))
    a_hit, a_free, a_diff, _ = s1.bootstrap_pair(hit, free, n_boot=50, matched=False)
    assert len(a_hit) == len(a_free) == len(a_diff) == 50
    assert all(0.0 <= v <= 1.0 for v in a_hit + a_free)


def test_ci_brackets_the_point_estimate():
    rng = np.random.default_rng(23)
    pos = rng.random(120) * 0.6 + 0.4
    neg = rng.random(600) * 0.6
    hit = s1.Slice("hit", pos, neg)
    free = s1.Slice("free", rng.random(100), rng.random(500))
    b_hit, _, _, _ = s1.bootstrap_pair(hit, free, n_boot=400, matched=False)
    ci = s1.ci_of(b_hit)
    assert ci["ci_low"] <= s1.auc_ties(pos, neg) <= ci["ci_high"]


# --------------------------------------------------------------------------
# C9-10: the sensitivity reimplements hit_root's inner rule -- it must match
# --------------------------------------------------------------------------

def test_matching_roots_agrees_with_hit_root_on_every_text():
    """S2 needs WHICH root fired, which hit_root does not report. The helper
    that recovers it must not drift from the frozen matcher."""
    lex = ["aptal", "mal", "allah", "sik"]
    texts = ["Aptalsın sen", "malatya güzel", "hiçbir şey yok", "ALLAH razı olsun",
             "sikayet ettim", "@USER url", "mal mülk", ""]
    for t in texts:
        assert bool(s1.matching_roots(t, lex)) == lexicon.hit_root(t, lex)


def test_matching_roots_respects_min_root_len():
    """Entries shorter than MIN_ROOT_LEN can never fire -- that blind spot is
    the phase 08 finding, and S1 depends on it still being true here."""
    assert s1.matching_roots("aq lan", ["aq"]) == set()
    assert lexicon.MIN_ROOT_LEN == 3
