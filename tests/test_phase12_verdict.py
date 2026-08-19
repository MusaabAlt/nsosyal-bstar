"""Tests for the Phase 12 verdict rule, cost model and threshold fitter.

Every input here is synthetic. Nothing reads the prediction dump, the split, or
the lexicon. C12-7 requires that the verdict function be "unit-tested on both
sides of every boundary before the data loads", and that is what this file is.

The verdict rule has four numeric boundaries -- `d = 40`, `ci_low = 0`,
`ci_high = 0`, and the two magnitude bands 0.04 and 0.10 -- and it is ORDERED,
so a later branch's condition can be true while an earlier branch fires. Both
facts are tested: each boundary from both sides, and each ordering precedence
with the later branch's condition deliberately satisfied.

Branch 0 is the one that most needs a test. `d` is not knowable until the
thresholds are fitted, so a small `|dCost_rel|` on a handful of discordant rows
would otherwise read as a clean null when it is really a resolution limit.
C12-7 says so explicitly: if branch 0 fires the phase "does not reframe a
coincidentally small `dCost_rel` as a null". A test that pins INSUFFICIENT
against an otherwise-null input is what stops that from happening quietly.

The expectations below are transcribed from the C12-7 branch table and from
nothing else:

    0. d < 40                                     -> INSUFFICIENT
    1. ci_low > 0                                 -> SLICE-CONDITIONAL WORSE
    2. ci_low <= 0 <= ci_high                     -> SINGLE-THRESHOLD-SUFFICIENT
    3. ci_high < 0 and |dCost_rel| <  0.04        -> SINGLE-THRESHOLD-SUFFICIENT
    4. ci_high < 0 and 0.04 <= |dCost_rel| < 0.10 -> INTERMEDIATE
    5. ci_high < 0 and |dCost_rel| >= 0.10        -> SLICE-CONDITIONAL BETTER
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.phase12_threshold_policy import cost, fit_threshold, verdict, verdict_branch

INSUFF = "INSUFFICIENT"
WORSE = "SLICE-CONDITIONAL WORSE"
SUFF = "SINGLE-THRESHOLD-SUFFICIENT"
INTER = "INTERMEDIATE"
BETTER = "SLICE-CONDITIONAL BETTER"


# ==============================================================================
# branch 0 -- the d = 40 boundary, from both sides
# ==============================================================================

@pytest.mark.parametrize("d", [0, 1, 39])
def test_below_forty_discordant_rows_is_insufficient(d):
    """Whatever the interval says. C12-7 branch 0 is evaluated first."""
    assert verdict(-0.30, -0.50, -0.10, d) == INSUFF
    assert verdict(0.00, -0.01, 0.01, d) == INSUFF
    assert verdict(0.30, 0.10, 0.50, d) == INSUFF


def test_exactly_forty_discordant_rows_is_not_insufficient():
    """`d < 40`, not `d <= 40`. At exactly 40 the rule proceeds to branch 1."""
    assert verdict(0.00, -0.01, 0.01, 40) == SUFF
    assert verdict(0.30, 0.10, 0.50, 40) == WORSE
    assert verdict(-0.30, -0.50, -0.10, 40) == BETTER


def test_branch_zero_does_not_let_a_small_effect_pass_as_a_null():
    """The specific reframing C12-7 forbids: |dCost_rel| = 0.001 with an
    interval straddling zero is branch 2's shape, but on 12 discordant rows it
    is a resolution limit and must be reported as one."""
    assert verdict_branch(0.001, -0.02, 0.02, 12) == (0, INSUFF)
    assert verdict_branch(0.001, -0.02, 0.02, 40) == (2, SUFF)


# ==============================================================================
# branch 1 -- the ci_low = 0 boundary, from both sides
# ==============================================================================

def test_strictly_positive_ci_low_is_slice_conditional_worse():
    assert verdict(0.20, 0.05, 0.40, 100) == WORSE
    assert verdict(0.20, 1e-12, 0.40, 100) == WORSE


def test_ci_low_exactly_zero_falls_through_to_branch_two():
    """`ci_low > 0`, not `>= 0`. At exactly zero branch 2 claims it."""
    assert verdict_branch(0.20, 0.0, 0.40, 100) == (2, SUFF)


def test_branch_one_wins_over_a_large_negative_point_estimate():
    """Ordering: branch 1 is tested before any magnitude band. An interval
    entirely above zero fires branch 1 even though |dCost_rel| >= 0.10 would
    satisfy branch 5's magnitude condition."""
    assert verdict_branch(-0.50, 0.01, 0.40, 100) == (1, WORSE)


# ==============================================================================
# branch 2 -- the straddle, and the ci_high = 0 boundary
# ==============================================================================

@pytest.mark.parametrize("lo,hi", [(-0.10, 0.10), (0.0, 0.0), (-0.30, 0.0), (0.0, 0.30)])
def test_an_interval_containing_zero_is_single_threshold_sufficient(lo, hi):
    assert verdict(-0.02, lo, hi, 100) == SUFF


def test_ci_high_exactly_zero_is_branch_two_not_branch_five():
    """`ci_high < 0`, not `<= 0`. A large negative point estimate with an
    interval touching zero is still the null."""
    assert verdict_branch(-0.50, -0.90, 0.0, 100) == (2, SUFF)


def test_ci_high_just_below_zero_leaves_branch_two():
    assert verdict_branch(-0.50, -0.90, -1e-12, 100) == (5, BETTER)


# ==============================================================================
# branches 3 / 4 / 5 -- the 0.04 and 0.10 magnitude boundaries
# ==============================================================================

@pytest.mark.parametrize("dc", [0.0, -0.01, -0.0399])
def test_below_small_is_single_threshold_sufficient(dc):
    assert verdict_branch(dc, -0.05, -0.001, 100) == (3, SUFF)


def test_exactly_small_is_intermediate_not_sufficient():
    """`|dCost_rel| < 0.04` for branch 3; at exactly 0.04 branch 4 takes it."""
    assert verdict_branch(-0.04, -0.09, -0.001, 100) == (4, INTER)


def test_just_below_small_is_still_sufficient():
    assert verdict_branch(-0.039999, -0.09, -0.001, 100) == (3, SUFF)


@pytest.mark.parametrize("dc", [-0.04, -0.07, -0.0999])
def test_between_the_bands_is_intermediate(dc):
    assert verdict_branch(dc, -0.20, -0.001, 100) == (4, INTER)


def test_exactly_large_is_slice_conditional_better():
    """`|dCost_rel| >= 0.10` for branch 5; the boundary belongs to LARGE."""
    assert verdict_branch(-0.10, -0.20, -0.001, 100) == (5, BETTER)


def test_just_below_large_is_intermediate():
    assert verdict_branch(-0.099999, -0.20, -0.001, 100) == (4, INTER)


@pytest.mark.parametrize("dc", [-0.10, -0.25, -1.0])
def test_beyond_large_is_slice_conditional_better(dc):
    assert verdict_branch(dc, -0.40, -0.001, 100) == (5, BETTER)


def test_the_magnitude_bands_are_on_the_absolute_value():
    """C12-7 writes `|dCost_rel|`. Under `ci_high < 0` a positive point estimate
    is contradictory input, but the rule as written is on the magnitude and the
    implementation must not silently sign-filter it."""
    assert verdict_branch(0.20, -0.40, -0.001, 100) == (5, BETTER)
    assert verdict_branch(0.01, -0.40, -0.001, 100) == (3, SUFF)


# ==============================================================================
# the rule as a whole: exhaustive over any valid interval
# ==============================================================================

@pytest.mark.parametrize("d", [40, 41, 1000])
@pytest.mark.parametrize("lo,hi", [(-0.9, -0.5), (-0.9, 0.0), (-0.9, 0.9),
                                   (0.0, 0.9), (0.5, 0.9), (0.0, 0.0)])
@pytest.mark.parametrize("dc", [-1.0, -0.10, -0.04, 0.0, 0.04, 0.10, 1.0])
def test_every_valid_input_yields_exactly_one_known_verdict(d, lo, hi, dc):
    b, v = verdict_branch(dc, lo, hi, d)
    assert b in (1, 2, 3, 4, 5)
    assert v in (WORSE, SUFF, INTER, BETTER)
    assert verdict(dc, lo, hi, d) == v


def test_an_inverted_interval_is_rejected_rather_than_scored():
    """ci_low > ci_high cannot come out of a percentile bootstrap. If it ever
    does, that is a bug upstream and the verdict must not paper over it."""
    with pytest.raises(ValueError):
        verdict(-0.05, 0.10, -0.10, 100)


def test_a_negative_discordant_count_is_rejected():
    with pytest.raises(ValueError):
        verdict(-0.05, -0.10, -0.01, -1)


# ==============================================================================
# C12-4 -- the cost model
# ==============================================================================

def test_cost_is_fp_plus_r_times_fn_over_n():
    assert cost(0, 0, 100, 3) == 0.0
    assert cost(10, 0, 100, 3) == pytest.approx(0.10)
    assert cost(0, 10, 100, 3) == pytest.approx(0.30)
    assert cost(213, 285, 4764, 3) == pytest.approx((213 + 3 * 285) / 4764)


def test_at_r_equals_one_cost_is_the_plain_error_rate():
    assert cost(30, 70, 1000, 1) == pytest.approx(0.10)


def test_cost_rejects_a_zero_denominator():
    with pytest.raises(ValueError):
        cost(1, 1, 0, 3)


# ==============================================================================
# C12-3 -- the fitting protocol
# ==============================================================================

def test_fit_threshold_flags_everything_when_false_negatives_dominate():
    """`flag iff score > t`, so "flag everything" needs a candidate strictly
    below the minimum observed score. At a large r it must be reachable."""
    scores = [0.10, 0.20, 0.30, 0.40]
    gold = [1, 1, 1, 0]
    t = fit_threshold(scores, gold, 100)
    assert t < min(scores)
    assert all(s > t for s in scores)


def test_fit_threshold_flags_nothing_when_false_positives_dominate():
    """The single OFF row sits at the BOTTOM of the score range, so no threshold
    can catch it without taking every negative with it. At r = 1 the cheapest
    rule is to flag nothing, which needs the top observed score as a candidate."""
    scores = [0.10, 0.20, 0.30, 0.40]
    gold = [1, 0, 0, 0]
    t = fit_threshold(scores, gold, 1)
    assert t >= max(scores)
    assert not any(s > t for s in scores)


def test_fit_threshold_finds_the_separating_point():
    scores = [0.10, 0.20, 0.70, 0.80]
    gold = [0, 0, 1, 1]
    t = fit_threshold(scores, gold, 3)
    assert 0.20 <= t < 0.70


def test_ties_break_toward_the_lower_threshold():
    """C12-3 declares this in advance: at equal cost take the lower `t`, which
    maximises recall. With one OFF and one NOT at r = 1, flagging both and
    flagging neither cost the same; the lower t must win."""
    t = fit_threshold([0.30, 0.60], [1, 0], 1)
    assert t < 0.30


def test_the_candidate_set_is_drawn_from_the_fitted_rows_only():
    """Candidates are the distinct observed scores plus one below the minimum.
    A fitted threshold can therefore never sit above the maximum observed
    score, nor strictly between two observed scores that are adjacent."""
    scores = [0.10, 0.10, 0.55, 0.90]
    for r in (1, 2, 3, 5, 10):
        t = fit_threshold(scores, [0, 1, 1, 1], r)
        assert t <= max(scores)
        assert t in (pytest.approx(0.10), pytest.approx(0.55), pytest.approx(0.90)) \
            or t < min(scores)


def test_fit_threshold_is_deterministic():
    scores = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75]
    gold = [0, 0, 1, 0, 1, 1, 0, 1]
    assert fit_threshold(scores, gold, 3) == fit_threshold(scores, gold, 3)


def test_fit_threshold_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        fit_threshold([0.1, 0.2], [1], 3)


def test_fit_threshold_rejects_an_empty_set():
    with pytest.raises(ValueError):
        fit_threshold([], [], 3)


# ==============================================================================
# C12-4 -- the r = 1 correctness check, in miniature
# ==============================================================================

def test_the_elkan_threshold_at_r_equals_one_is_exactly_one_half():
    """Not approximately. S1a at r = 1 must reproduce S0 bit for bit, which it
    can only do if 1/(1+1) is exactly the frozen 0.5."""
    assert 1.0 / (1.0 + 1) == 0.5


@pytest.mark.parametrize("r,want", [(1, 0.5), (2, 1 / 3), (3, 0.25), (5, 1 / 6), (10, 1 / 11)])
def test_the_elkan_grid_matches_the_c12_4_table(r, want):
    assert 1.0 / (1.0 + r) == pytest.approx(want)
