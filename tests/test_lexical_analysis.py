"""Tests for phase08_lexical_analysis.py.

The arithmetic checks matter least. The ones that matter are the three
properties the phase 08 conclusions rest on:

  * the primary ranking must be monotone in frequency at fixed skew -- that is
    the whole justification for choosing binomial z over raw lift, and if it
    broke, "rare tokens with extreme ratios do not top the list" would be false;
  * stratum reweighting must actually remove a difference that is entirely due
    to the stratifying variable, and must not invent one where none exists --
    the +0.2066 result is a matched difference, so a broken matcher is a wrong
    finding rather than a noisy one;
  * the pre-registered verdict rule must return NO SUPPORT on a CI touching
    zero, in both directions.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase08_lexical_analysis as p8


# --------------------------------------------------------------------------
# the ranking statistic
# --------------------------------------------------------------------------

def test_norm_ppf_matches_known_quantiles():
    for p, want in ((0.975, 1.959964), (0.995, 2.575829), (0.9999, 3.719016)):
        assert abs(p8._norm_ppf(p) - want) < 1e-4


def test_preregistered_threshold_is_what_the_document_says():
    """phases/08_lexical_analysis.md C8-5 states |z| >= 3.66 for 200 tests."""
    z = p8._norm_ppf(1.0 - p8.ALPHA / (2.0 * p8.TOP_N))
    assert abs(z - 3.6623) < 1e-3


def test_z_is_monotone_in_frequency_at_fixed_skew():
    """The justification for the primary ranking (C8-4).

    Same P(OFF|t), ten times the evidence -> a strictly larger z. This is the
    property that stops a rare-but-extreme token topping the list.
    """
    p0 = 0.193
    small = p8.binomial_z(off_df=30, df=100, p0=p0)
    large = p8.binomial_z(off_df=300, df=1000, p0=p0)
    assert large > small
    assert abs(large - small * math.sqrt(10)) < 1e-9


def test_z_is_zero_at_the_base_rate_and_signed_correctly():
    p0 = 0.2
    assert abs(p8.binomial_z(200, 1000, p0)) < 1e-12
    assert p8.binomial_z(400, 1000, p0) > 0
    assert p8.binomial_z(50, 1000, p0) < 0


def test_lift_alone_would_rank_differently():
    """Documents *why* lift was not chosen: it ignores sample size entirely."""
    rare_extreme = (9, 10)      # p_hat 0.90 on 10 rows
    common_strong = (450, 1000)  # p_hat 0.45 on 1000 rows
    assert rare_extreme[0] / rare_extreme[1] > common_strong[0] / common_strong[1]
    assert p8.binomial_z(*rare_extreme, p0=0.193) < \
           p8.binomial_z(*common_strong, p0=0.193)


# --------------------------------------------------------------------------
# bucketing
# --------------------------------------------------------------------------

def test_quantile_edges_split_into_the_requested_number_of_buckets():
    vals = list(range(1, 101))
    edges = p8.quantile_edges(vals, 4)
    assert len(edges) == 3
    assert sorted(edges) == edges
    assert {p8.bucket_of(v, edges) for v in vals} == {0, 1, 2, 3}


def test_quantile_edges_are_observed_values_not_interpolated():
    vals = [1, 1, 1, 50, 100, 100]
    for e in p8.quantile_edges(vals, 3):
        assert e in vals


def test_bucket_of_is_monotone():
    edges = [10, 20, 30]
    got = [p8.bucket_of(v, edges) for v in (0, 9, 10, 19, 20, 29, 30, 99)]
    assert got == sorted(got)
    assert got == [0, 0, 1, 1, 2, 2, 3, 3]


# --------------------------------------------------------------------------
# the matched comparison -- the load-bearing machinery
# --------------------------------------------------------------------------

def _rows(spec):
    """spec: list of (x, in_lex, ntok) triples, expanded by count."""
    out = []
    for x, in_lex, ntok, n in spec:
        out.extend([(x, in_lex, ntok)] * n)
    return out


def test_matching_removes_a_difference_caused_entirely_by_the_strata():
    """A is long rows, B is mostly short rows, and X depends ONLY on length.

    Unmatched, A looks dramatically worse. Matched, the difference must vanish:
    within each stratum the two groups behave identically.
    """
    a = _rows([(1, False, 40, 80), (0, False, 5, 20)])
    b = _rows([(1, False, 40, 80), (0, False, 5, 320)])
    edges = p8.quantile_edges([n for _, _, n in a], 2)
    r = p8.matched_comparison(a, b, edges, n_boot=200, seed=1)
    assert r["diff_unmatched"] > 0.15          # the confound, unadjusted
    assert abs(r["diff_matched"]) < 1e-9       # removed exactly
    assert r["a_mass_in_unsupported_strata"] == 0.0


def test_matching_does_not_invent_a_difference():
    a = _rows([(1, False, 40, 50), (0, False, 5, 50)])
    b = _rows([(1, False, 40, 500), (0, False, 5, 500)])
    edges = p8.quantile_edges([n for _, _, n in a], 2)
    r = p8.matched_comparison(a, b, edges, n_boot=200, seed=1)
    assert abs(r["diff_matched"]) < 1e-9


def test_matching_preserves_a_real_within_stratum_difference():
    """Same length profile in both groups, but A genuinely carries more X."""
    a = _rows([(1, False, 10, 60), (0, False, 10, 40)])
    b = _rows([(1, False, 10, 200), (0, False, 10, 800)])
    edges = p8.quantile_edges([n for _, _, n in a], 2)
    r = p8.matched_comparison(a, b, edges, n_boot=200, seed=1)
    assert abs(r["diff_matched"] - (0.6 - 0.2)) < 1e-9


def test_unsupported_strata_are_reported_not_silently_dropped():
    """A has a stratum B cannot cover. The share must surface in the result."""
    a = _rows([(1, False, 5, 50), (1, True, 99, 50)])
    b = _rows([(0, False, 5, 100)])
    edges = p8.quantile_edges([n for _, _, n in a], 2)
    r = p8.matched_comparison(a, b, edges, n_boot=50, seed=1)
    assert r["a_mass_in_unsupported_strata"] == 0.5


def test_bootstrap_is_deterministic_under_a_fixed_seed():
    rng = random.Random(11)
    a = [(rng.randint(0, 1), rng.random() < 0.1, rng.randint(1, 40)) for _ in range(120)]
    b = [(rng.randint(0, 1), rng.random() < 0.1, rng.randint(1, 40)) for _ in range(900)]
    edges = p8.quantile_edges([n for _, _, n in a], 4)
    one = p8.matched_comparison(a, b, edges, n_boot=300, seed=42)
    two = p8.matched_comparison(a, b, edges, n_boot=300, seed=42)
    assert one["diff_matched_ci"] == two["diff_matched_ci"]


def test_ci_brackets_the_point_estimate():
    rng = random.Random(3)
    a = [(1 if rng.random() < 0.4 else 0, False, rng.randint(1, 30)) for _ in range(118)]
    b = [(1 if rng.random() < 0.2 else 0, False, rng.randint(1, 30)) for _ in range(1000)]
    edges = p8.quantile_edges([n for _, _, n in a], 4)
    r = p8.matched_comparison(a, b, edges, n_boot=500, seed=42)
    ci = r["diff_matched_ci"]
    assert ci["ci_low"] <= r["diff_matched"] <= ci["ci_high"]


# --------------------------------------------------------------------------
# the pre-registered verdict rule (C8-7)
# --------------------------------------------------------------------------

def test_verdict_requires_both_a_positive_difference_and_a_ci_excluding_zero():
    assert p8.verdict(0.20, {"ci_low": 0.12, "ci_high": 0.29}) == "SUPPORT"
    # CI touches zero
    assert p8.verdict(0.20, {"ci_low": -0.01, "ci_high": 0.40}) == "NO SUPPORT"
    assert p8.verdict(0.20, {"ci_low": 0.0, "ci_high": 0.40}) == "NO SUPPORT"
    # negative difference, however tight
    assert p8.verdict(-0.20, {"ci_low": -0.30, "ci_high": -0.10}) == "NO SUPPORT"


# --------------------------------------------------------------------------
# tokenisation is the frozen one, not a copy
# --------------------------------------------------------------------------

def test_module_uses_the_frozen_tokeniser():
    """C8-1/C8-6: `lexicon.tokens` and `lexicon.hit_root` are imported.

    A second tokenisation rule inside this phase would silently produce token
    statistics that do not correspond to any slice used anywhere else.
    """
    src = (Path(__file__).resolve().parents[1] / "phase08_lexical_analysis.py").read_text(
        encoding="utf-8")
    assert "from src import augment, data_io, lexicon" in src
    assert "lexicon.tokens(" in src and "lexicon.hit_root(" in src
    assert "re.findall" not in src, "phase 08 must not tokenise on its own"
