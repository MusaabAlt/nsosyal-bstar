"""Tests for the Phase 11 verdict rule (C11-7) and the SignedGap identity (C11-4).

Written and run BEFORE any Phase 11 datum is scored. Every input here is
synthetic; nothing in this file reads `dev_predictions.csv`, the lexicon, or the
frozen split, and nothing here produces a Phase 11 number.

Two things are being nailed down, and they are nailed down for different reasons:

  * **The verdict rule (C11-7).** C11-7 says the branches are ordered, mutually
    exclusive and exhaustive. That is a claim about code, so it is tested as one:
    both sides of every boundary (n_band 399/400, ci_high -0.001/+0.001, SG at
    0.0199 / 0.0200 / 0.0499 / 0.0500), plus the shadowing tests that would catch
    a reordering. C9-5's precedent is the reason: no result may be argued into a
    branch after the fact, and the only defence against that is that the branch
    boundaries were executable before the numbers existed.

  * **The SignedGap identity (C11-4).** C11-4 disqualifies the whole-slice signed
    gap as the primary endpoint on the grounds that it telescopes -- the binning
    cancels and it equals `(mean gold) - (mean p)` exactly. That derivation is the
    argument for the sub-threshold band being primary, so the derivation is
    verified rather than asserted, at 10, 15 and 20 bins, to 1e-12.

`signed_gap_p_off` bins on **P(OFF)**, per C11-3. It is NOT the phase-04
statistic, which bins on decision confidence `max(p, 1-p)` over both classes.
`src.calibration.ece` computes that other quantity and is deliberately not
imported here; the two may not be compared or quoted in the same sentence.

The reference implementations below are the spec as code, frozen with the
pre-registration. When `phase11_prior_correction.py` exists it must export
`verdict` and `signed_gap_p_off` with these signatures and this behaviour: the
import below then points this same file at the real implementation, and any drift
from the pre-registered rule fails here.
"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# C11-6/C11-7 constants. Fixed in the pre-registration, not tuned here.
N_BAND_FLOOR = 400
SMALL = 0.02
LARGE = 0.05

VERDICTS = {"INSUFFICIENT", "OVER-SCORED", "BASE-RATE-CORRECT",
            "INTERMEDIATE", "UNDER-CONFIDENT"}


# ==============================================================================
# the spec, as code
# ==============================================================================

def _reference_verdict(sg, ci_low, ci_high, n_band):
    """C11-7, transcribed. Branch order is part of the rule, not an implementation
    detail -- see the ordering tests below."""
    if n_band < N_BAND_FLOOR:                 # 0
        return "INSUFFICIENT"
    if ci_high < 0:                           # 1
        return "OVER-SCORED"
    if ci_low <= 0 <= ci_high:                # 2
        return "BASE-RATE-CORRECT"
    if sg < SMALL:                            # 3   (ci_low > 0 from here on)
        return "BASE-RATE-CORRECT"
    if sg < LARGE:                            # 4
        return "INTERMEDIATE"
    return "UNDER-CONFIDENT"                  # 5


def _reference_signed_gap_p_off(y_true, p_off, n_bins=10):
    """C11-3: SignedGap = sum_b (n_b / N) * (off_rate_b - mean_p_b).

    Binned on P(OFF) over `n_bins` equal-width bins on [0, 1]. `p == 1.0` belongs
    to the last bin; dropping it would break the C11-4 identity silently, so the
    clamp is deliberate and is tested.

    Positive means the model under-states P(OFF) -- under-confidence in the OFF
    direction.
    """
    n = len(p_off)
    if n == 0:
        raise ValueError("SignedGap is undefined on zero rows")
    sum_p = [0.0] * n_bins
    sum_g = [0.0] * n_bins
    cnt = [0] * n_bins
    for g, p in zip(y_true, p_off):
        b = min(int(p * n_bins), n_bins - 1)
        cnt[b] += 1
        sum_p[b] += p
        sum_g[b] += 1.0 if g == "OFF" else 0.0
    total = 0.0
    for b in range(n_bins):
        if cnt[b] == 0:
            continue
        total += (cnt[b] / n) * (sum_g[b] / cnt[b] - sum_p[b] / cnt[b])
    return total


try:  # once Phase 11 has an implementation, these tests bind to it instead
    from phase11_prior_correction import (  # type: ignore  # noqa: F401
        signed_gap_p_off, verdict)
    IMPLEMENTATION = "phase11_prior_correction"
except ImportError:
    verdict = _reference_verdict
    signed_gap_p_off = _reference_signed_gap_p_off
    IMPLEMENTATION = "reference frozen in tests/test_phase11_verdict.py"


def _gold(bits):
    return ["OFF" if b else "NOT" for b in bits]


# ==============================================================================
# C11-7: both sides of every boundary
# ==============================================================================

def test_branch_0_the_n_band_floor():
    """399 is INSUFFICIENT, 400 is not. The floor is `< 400`, not `<= 400`."""
    assert verdict(0.10, 0.05, 0.15, 399) == "INSUFFICIENT"
    assert verdict(0.10, 0.05, 0.15, 400) == "UNDER-CONFIDENT"


def test_branch_1_and_2_the_ci_high_boundary():
    """ci_high < 0 is OVER-SCORED; the moment the interval touches zero it is not."""
    assert verdict(-0.03, -0.06, -0.001, 1000) == "OVER-SCORED"
    assert verdict(-0.03, -0.06, +0.001, 1000) == "BASE-RATE-CORRECT"


def test_branch_2_includes_a_ci_bound_of_exactly_zero():
    """`ci_low <= 0 <= ci_high` is closed at both ends, so 0.0 lands in branch 2,
    not in branch 1 and not in the magnitude branches."""
    assert verdict(-0.03, -0.06, 0.0, 1000) == "BASE-RATE-CORRECT"
    assert verdict(0.03, 0.0, 0.09, 1000) == "BASE-RATE-CORRECT"


def test_branch_3_and_4_the_small_boundary():
    """SMALL = 0.02 is the floor of INTERMEDIATE, not the ceiling of
    BASE-RATE-CORRECT."""
    assert verdict(0.0199, 0.001, 0.04, 1000) == "BASE-RATE-CORRECT"
    assert verdict(0.0200, 0.001, 0.04, 1000) == "INTERMEDIATE"


def test_branch_4_and_5_the_large_boundary():
    """LARGE = 0.05 is UNDER-CONFIDENT, not INTERMEDIATE."""
    assert verdict(0.0499, 0.001, 0.09, 1000) == "INTERMEDIATE"
    assert verdict(0.0500, 0.001, 0.09, 1000) == "UNDER-CONFIDENT"


def test_the_declared_inconclusive_band_is_reachable_from_both_sides():
    """C11-6 declares [0.02, 0.05) inconclusive in advance. It is a real branch,
    reachable from just above SMALL and from just below LARGE."""
    assert verdict(0.02001, 0.001, 0.05, 1000) == "INTERMEDIATE"
    assert verdict(0.04999, 0.001, 0.09, 1000) == "INTERMEDIATE"


# ==============================================================================
# C11-7: ordered as written
# ==============================================================================

def test_branch_0_shadows_every_other_branch():
    """The floor is evaluated first, so an under-powered band cannot be reported as
    a finding however large SG is or whichever side of zero the interval sits."""
    for sg, lo, hi in [(0.10, 0.05, 0.15),      # would otherwise be UNDER-CONFIDENT
                       (0.03, 0.01, 0.06),      # would otherwise be INTERMEDIATE
                       (0.001, 0.0005, 0.02),   # would otherwise be BASE-RATE-CORRECT
                       (-0.09, -0.15, -0.02)]:  # would otherwise be OVER-SCORED
        assert verdict(sg, lo, hi, 399) == "INSUFFICIENT"
        assert verdict(sg, lo, hi, 0) == "INSUFFICIENT"


def test_branch_2_shadows_the_magnitude_branches():
    """An interval straddling zero returns BASE-RATE-CORRECT however big the point
    estimate is. If branches 3-5 ran first, a large-but-not-significant SG would be
    reported as UNDER-CONFIDENT."""
    assert verdict(0.20, -0.01, 0.41, 1000) == "BASE-RATE-CORRECT"
    assert verdict(0.03, -0.01, 0.07, 1000) == "BASE-RATE-CORRECT"


def test_the_magnitude_branches_require_a_ci_strictly_above_zero():
    """Branches 3-5 are reachable only with ci_low > 0; the same SG with ci_low at
    exactly zero falls back to branch 2."""
    assert verdict(0.10, 1e-9, 0.20, 1000) == "UNDER-CONFIDENT"
    assert verdict(0.10, 0.0, 0.20, 1000) == "BASE-RATE-CORRECT"


# ==============================================================================
# C11-7: exhaustive and mutually exclusive
# ==============================================================================

def _grid():
    """Every combination worth distinguishing, boundaries included."""
    ns = [0, 1, 399, 400, 401, 2073]
    edges = [-0.5, -0.05, -0.001, 0.0, 0.001, 0.0199, 0.02, 0.0499, 0.05, 0.5]
    for n in ns:
        for lo in edges:
            for hi in edges:
                if hi < lo:
                    continue          # a percentile interval cannot be inverted
                for sg in edges:
                    yield sg, lo, hi, n


def test_the_rule_is_exhaustive():
    """Every reachable input returns exactly one of the five declared verdicts, and
    all five are reachable. No sixth outcome, no fall-through to None."""
    seen = set()
    for sg, lo, hi, n in _grid():
        v = verdict(sg, lo, hi, n)
        assert v in VERDICTS, f"undeclared verdict {v!r} for {(sg, lo, hi, n)}"
        seen.add(v)
    assert seen == VERDICTS, f"unreachable verdicts: {sorted(VERDICTS - seen)}"


def test_the_rule_is_exhaustive_on_random_inputs():
    rng = random.Random(42)
    for _ in range(20000):
        lo = rng.uniform(-0.6, 0.6)
        hi = lo + rng.uniform(0.0, 0.6)
        assert verdict(rng.uniform(-0.6, 0.6), lo, hi,
                       rng.randrange(0, 3000)) in VERDICTS


def test_branches_1_to_5_are_mutually_exclusive_above_the_floor():
    """Above the floor exactly one of the five conditions holds, so the ordering
    resolves no ambiguity between them -- there is none to resolve. The ordering
    matters only for branch 0, which the shadowing test covers."""
    predicates = [
        lambda sg, lo, hi: hi < 0,                            # 1
        lambda sg, lo, hi: lo <= 0 <= hi,                     # 2
        lambda sg, lo, hi: lo > 0 and sg < SMALL,             # 3
        lambda sg, lo, hi: lo > 0 and SMALL <= sg < LARGE,    # 4
        lambda sg, lo, hi: lo > 0 and sg >= LARGE,            # 5
    ]
    for sg, lo, hi, n in _grid():
        if n < N_BAND_FLOOR:
            continue
        fired = [i for i, f in enumerate(predicates, start=1) if f(sg, lo, hi)]
        assert len(fired) == 1, f"{len(fired)} branches fired for {(sg, lo, hi)}: {fired}"


def test_the_transcribed_rule_and_the_running_implementation_agree():
    """If Phase 11 ships its own `verdict`, it must reproduce C11-7 exactly."""
    for sg, lo, hi, n in _grid():
        assert verdict(sg, lo, hi, n) == _reference_verdict(sg, lo, hi, n)


# ==============================================================================
# C11-4: the SignedGap identity
# ==============================================================================

BIN_COUNTS = (10, 15, 20)


def _random_case(rng, n):
    p = [rng.random() for _ in range(n)]
    gold = _gold([rng.random() < 0.5 for _ in range(n)])
    return gold, p


def _closed_form(gold, p):
    return sum(1.0 for g in gold if g == "OFF") / len(p) - sum(p) / len(p)


@pytest.mark.parametrize("n_bins", BIN_COUNTS)
@pytest.mark.parametrize("n", [1, 2, 17, 300, 2073])
def test_binned_signed_gap_equals_mean_gold_minus_mean_p(n, n_bins):
    """C11-4: the binning telescopes. This identity is the whole reason the
    whole-slice figure is disqualified as the primary endpoint, so it is checked
    rather than asserted."""
    rng = random.Random(1000 + n * 31 + n_bins)
    for _ in range(40):
        gold, p = _random_case(rng, n)
        assert abs(signed_gap_p_off(gold, p, n_bins) - _closed_form(gold, p)) < 1e-12


@pytest.mark.parametrize("n_bins", BIN_COUNTS)
def test_the_identity_survives_the_bin_edges(n_bins):
    """0.0 and 1.0 are the two values a naive `int(p * n_bins)` gets wrong: 1.0
    indexes off the end and gets dropped, and a dropped row breaks the identity
    silently rather than loudly."""
    rng = random.Random(7)
    p = [0.0, 1.0, 0.0, 1.0, 0.5]
    p += [i / n_bins for i in range(n_bins + 1)]
    gold = _gold([rng.random() < 0.5 for _ in p])
    assert abs(signed_gap_p_off(gold, p, n_bins) - _closed_form(gold, p)) < 1e-12


@pytest.mark.parametrize("n_bins", BIN_COUNTS)
def test_the_identity_survives_empty_bins(n_bins):
    """All mass in one bin: every other bin has n_b = 0 and must contribute nothing
    rather than a nan."""
    rng = random.Random(11)
    p = [rng.uniform(0.0, 1.0 / n_bins) for _ in range(50)]
    gold = _gold([rng.random() < 0.3 for _ in p])
    assert abs(signed_gap_p_off(gold, p, n_bins) - _closed_form(gold, p)) < 1e-12


@pytest.mark.parametrize("n_bins", BIN_COUNTS)
def test_the_identity_also_holds_on_a_sub_threshold_band(n_bins):
    """The primary endpoint is SignedGap restricted to `p_OFF < 0.5`. The identity
    is a property of any row set, so it holds there too -- which is why C11-4's
    argument against the whole-slice figure is about arithmetic pinning by the
    global calibration, not about the band being immune to telescoping."""
    rng = random.Random(13)
    gold, p = _random_case(rng, 800)
    band = [(g, q) for g, q in zip(gold, p) if q < 0.5]
    bg = [g for g, _ in band]
    bp = [q for _, q in band]
    assert abs(signed_gap_p_off(bg, bp, n_bins) - _closed_form(bg, bp)) < 1e-12


def test_the_sign_convention_is_the_one_c11_3_declares():
    """`SignedGap > 0` means the model under-states P(OFF). Getting this backwards
    would invert every verdict in C11-7."""
    assert signed_gap_p_off(["OFF"] * 9 + ["NOT"], [0.2] * 10, 10) > 0
    assert signed_gap_p_off(["NOT"] * 9 + ["OFF"], [0.8] * 10, 10) < 0


def test_zero_rows_is_an_error_not_a_zero():
    """An empty band must not quietly return 0.0 and be read as perfect
    calibration; C11-7 branch 0 is what handles a thin band."""
    with pytest.raises(ValueError):
        signed_gap_p_off([], [], 10)
