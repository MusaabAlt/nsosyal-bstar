"""Tests for src/calibration.py.

The important ones are not the arithmetic checks -- they are the two properties
the phase 04 conclusions rest on:

  * a temperature fit on perfectly calibrated data must come back ~1.0, and on
    deliberately overconfident data must come back > 1;
  * temperature must NOT move the risk-coverage curve (C4-3).

If either breaks, the phase 04 write-up is wrong in a way no aggregate number
would reveal.
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import calibration as cal


def _synthetic(n=4000, seed=7, sharpen=1.0):
    """Rows whose labels are drawn from a known probability.

    With sharpen=1 the dumped probability is the true one, so the data is
    perfectly calibrated by construction. sharpen>1 pushes probabilities toward
    0/1 without changing the labels -- i.e. overconfidence.
    """
    rng = random.Random(seed)
    y, p = [], []
    for _ in range(n):
        z = rng.gauss(0.0, 2.0)
        true_p = cal.sigmoid(z)
        y.append("OFF" if rng.random() < true_p else "NOT")
        p.append(cal.sigmoid(z * sharpen))
    return y, p


def test_logit_sigmoid_roundtrip():
    for p in (0.001, 0.1, 0.5, 0.9, 0.999):
        assert abs(cal.sigmoid(cal.logit(p)) - p) < 1e-12


def test_temperature_identity_at_one():
    for p in (0.02, 0.37, 0.5, 0.88):
        assert abs(cal.apply_temperature(p, 1.0) - p) < 1e-12


def test_temperature_is_monotonic_and_order_preserving():
    ps = [0.01, 0.2, 0.45, 0.5, 0.55, 0.8, 0.99]
    for T in (0.5, 1.0, 2.0, 5.0):
        scaled = [cal.apply_temperature(p, T) for p in ps]
        assert scaled == sorted(scaled), f"T={T} broke monotonicity"


def test_temperature_does_not_change_decisions():
    """argmax is fixed under temperature scaling: p>0.5 stays p>0.5."""
    for p in (0.001, 0.2, 0.499, 0.501, 0.8, 0.999):
        for T in (0.3, 1.0, 4.0):
            assert (cal.apply_temperature(p, T) >= 0.5) == (p >= 0.5)


def test_clipping_handles_saturated_dumps():
    assert math.isfinite(cal.logit(0.0))
    assert math.isfinite(cal.logit(1.0))
    assert cal.saturated_count([0.0, 1.0, 0.5, 0.3]) == 2


def test_fit_returns_one_on_calibrated_data():
    y, p = _synthetic(sharpen=1.0)
    fit = cal.fit_temperature(y, p)
    assert 0.85 < fit["temperature"] < 1.18, fit


def test_fit_exceeds_one_on_overconfident_data():
    """Probabilities sharpened by 2x should need T ~ 2 to undo."""
    y, p = _synthetic(sharpen=2.0)
    fit = cal.fit_temperature(y, p)
    assert fit["temperature"] > 1.4, fit
    assert fit["nll_after"] <= fit["nll_before"] + 1e-12


def test_fit_below_one_on_underconfident_data():
    y, p = _synthetic(sharpen=0.5)
    fit = cal.fit_temperature(y, p)
    assert fit["temperature"] < 0.8, fit


def test_ece_near_zero_when_calibrated():
    y, p = _synthetic(sharpen=1.0)
    assert cal.ece(y, p)["ece"] < 0.03


def test_ece_signed_gap_negative_when_overconfident():
    """Overconfident => confidence exceeds accuracy => accuracy-confidence < 0."""
    y, p = _synthetic(sharpen=2.5)
    e = cal.ece(y, p)
    assert e["signed_gap"] < 0, e
    assert e["ece"] > 0.03


def test_reliability_bins_shape_and_totals():
    y, p = _synthetic(n=500)
    for nb in (10, 15, 20):
        bins = cal.reliability_bins(y, p, n_bins=nb)
        assert len(bins) == nb
        assert sum(b["n"] for b in bins) == 500
        assert all(b["accuracy"] is None for b in bins if b["n"] == 0)


def test_risk_coverage_is_invariant_to_temperature():
    """C4-3 -- the property the phase 04 wording depends on."""
    y, p = _synthetic(sharpen=2.0)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    covs = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    for T in (0.4, 1.0, 1.7, 3.3):
        ok, worst = cal.verify_rc_invariance(y, pred, p, T, covs)
        assert ok, f"T={T} moved the risk-coverage curve by {worst}"


def test_error_rate_falls_as_coverage_falls():
    """Deferring the least confident rows should not make the kept set worse."""
    y, p = _synthetic(n=3000)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    rc = cal.risk_coverage(y, pred, p, [1.0, 0.9, 0.8, 0.7, 0.6, 0.5])
    assert rc[0]["error_rate"] >= rc[-1]["error_rate"]
    assert rc[0]["n_deferred"] == 0


def test_coverage_full_matches_plain_score():
    from src import evaluate
    y, p = _synthetic(n=800)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    rc = cal.risk_coverage(y, pred, p, [1.0])[0]
    assert abs(rc["macro_f1"] - evaluate.score(y, pred, with_ci=False)["macro_f1"]) < 1e-12


def test_threshold_selected_on_one_set_applies_to_another():
    y, p = _synthetic(n=2000, seed=11)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    t = cal.threshold_for_coverage(p[:1000], 0.8)
    block = cal.apply_threshold(y[1000:], pred[1000:], p[1000:], t)
    # Realised coverage on held-out rows is close to, but need not equal, 0.8.
    assert 0.70 < block["coverage"] < 0.90, block["coverage"]


def test_capture_lift_and_slice_breakdown():
    y, p = _synthetic(n=1200, seed=5)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    slices = ["lexicon_hit" if i % 4 == 0 else "lexicon_free" for i in range(len(y))]
    t = cal.threshold_for_coverage(p, 0.8)
    b = cal.apply_threshold(y, pred, p, t, slices=slices)
    assert b["capture_lift"] > 1.0, "deferral should beat random at catching errors"
    assert set(b["by_slice"]) == {"lexicon_hit", "lexicon_free"}
    tot = sum(v["n_rows"] for v in b["by_slice"].values())
    assert tot == len(y)
    assert sum(v["n_deferred"] for v in b["by_slice"].values()) == b["n_deferred"]
    for v in b["by_slice"].values():
        assert v["errors_deferred"] + v["errors_auto"] == v["errors_total"]


def test_bootstrap_ci_brackets_the_point_estimate():
    y, p = _synthetic(n=1500, seed=3)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    t = cal.threshold_for_coverage(p, 0.85)
    pt = cal.apply_threshold(y, pred, p, t)
    ci = cal.bootstrap_operating_point(y, pred, p, t, n_boot=200, seed=42)
    assert ci["macro_f1"]["ci_low"] <= pt["macro_f1"] <= ci["macro_f1"]["ci_high"]
    assert ci["error_rate"]["ci_low"] <= pt["error_rate"] <= ci["error_rate"]["ci_high"]


def test_bootstrap_is_deterministic_under_seed():
    y, p = _synthetic(n=600, seed=9)
    pred = ["OFF" if q >= 0.5 else "NOT" for q in p]
    t = cal.threshold_for_coverage(p, 0.8)
    a = cal.bootstrap_operating_point(y, pred, p, t, n_boot=100, seed=42)
    b = cal.bootstrap_operating_point(y, pred, p, t, n_boot=100, seed=42)
    assert a == b


def test_boundary_fit_is_flagged_not_reported_silently():
    """Labels independent of scores => optimal T runs to infinity => bound hit."""
    rng = random.Random(1)
    y = ["OFF" if rng.random() < 0.5 else "NOT" for _ in range(1500)]
    p = [cal.sigmoid(rng.gauss(0.0, 4.0)) for _ in range(1500)]
    fit = cal.fit_temperature(y, p, lo=0.05, hi=20.0)
    assert fit["at_boundary"] is True, fit


def test_normal_fit_is_not_flagged():
    y, p = _synthetic(sharpen=2.0)
    assert cal.fit_temperature(y, p)["at_boundary"] is False


def test_fit_rejects_empty_and_bad_temperature():
    import pytest
    with pytest.raises(ValueError):
        cal.fit_temperature([], [])
    with pytest.raises(ValueError):
        cal.apply_temperature(0.5, 0.0)
    with pytest.raises(ValueError):
        cal.ece(["OFF", "MAYBE"], [0.5, 0.5])
