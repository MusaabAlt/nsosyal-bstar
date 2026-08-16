"""NSosyal B* -- calibration and selective prediction.

Pure stdlib, like src/evaluate.py: no numpy, no sklearn at module level, so it
runs on the local Python 3.14 venv as well as on Colab.

Two independent things live here and it is worth keeping them apart:

  * CALIBRATION changes the probability attached to a decision. It does not
    change the decision (temperature scaling is monotonic, so argmax is fixed)
    and it does not change the ORDER of rows by confidence.
  * SELECTIVE PREDICTION uses that order to defer the least confident rows to a
    human. It depends only on the order, never on the probability values.

The consequence -- registered in phases/04_calibration.md as C4-3 -- is that
temperature scaling cannot move the risk-coverage curve at all. Anything that
appears to show otherwise is a bug, and `verify_rc_invariance` exists to catch
it rather than to argue about it.
"""

import math

from . import evaluate

# Half the 6-decimal rounding grid the prediction dumps are written on. A dump
# value of 0.000000 means "somewhere in [0, 5e-7)", and 5e-7 is the midpoint we
# can defend. See C4-5: this compresses the extreme logit tail.
EPS = 5e-7


# --------------------------------------------------------------------------
# probability <-> logit
# --------------------------------------------------------------------------

def clip(p, eps=EPS):
    return min(1.0 - eps, max(eps, p))


def logit(p, eps=EPS):
    """Inverse sigmoid. For a two-class softmax, log(p/(1-p)) is exactly the
    difference of the two logits, which is the quantity temperature divides."""
    p = clip(p, eps)
    return math.log(p / (1.0 - p))


def sigmoid(z):
    # Branch to avoid overflow in exp for large |z|.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def apply_temperature(p_off, T):
    """Rescale P(OFF) by temperature T. T > 1 softens, T < 1 sharpens."""
    if T <= 0:
        raise ValueError(f"temperature must be positive, got {T}")
    return sigmoid(logit(p_off) / T)


def saturated_count(p_list, eps=EPS):
    """How many dumped probabilities hit the rounding floor/ceiling.

    Reported, not silently absorbed: these are precisely the rows whose true
    confidence is unrecoverable from the dump (C4-5).
    """
    return sum(1 for p in p_list if p <= eps or p >= 1.0 - eps)


# --------------------------------------------------------------------------
# calibration error
# --------------------------------------------------------------------------

def decision_confidence(p_off):
    """Confidence in the decision actually made, i.e. max(p, 1-p) in [0.5, 1]."""
    return max(p_off, 1.0 - p_off)


def reliability_bins(y_true, p_off, n_bins=15):
    """Reliability-diagram data: the table IS the diagram.

    Bins are equal-width over the confidence range [0.5, 1.0]. Empty bins are
    returned with n=0 rather than dropped, so the table always has n_bins rows
    and two runs are directly comparable line by line.
    """
    if len(y_true) != len(p_off):
        raise ValueError(f"length mismatch: {len(y_true)} labels vs {len(p_off)} probabilities")
    bad = set(y_true) - set(evaluate.LABELS)
    if bad:
        raise ValueError(f"labels outside {evaluate.LABELS}: {sorted(bad)}")

    lo, hi = 0.5, 1.0
    width = (hi - lo) / n_bins
    bins = [{"lo": lo + i * width, "hi": lo + (i + 1) * width,
             "n": 0, "correct": 0, "conf_sum": 0.0} for i in range(n_bins)]

    for gold, p in zip(y_true, p_off):
        conf = decision_confidence(p)
        pred = "OFF" if p >= 0.5 else "NOT"
        idx = int((conf - lo) / width)
        if idx >= n_bins:          # conf == 1.0 lands one past the last bin
            idx = n_bins - 1
        if idx < 0:
            idx = 0
        b = bins[idx]
        b["n"] += 1
        b["correct"] += 1 if pred == gold else 0
        b["conf_sum"] += conf

    for b in bins:
        b["accuracy"] = (b["correct"] / b["n"]) if b["n"] else None
        b["mean_confidence"] = (b["conf_sum"] / b["n"]) if b["n"] else None
        b["gap"] = ((b["accuracy"] - b["mean_confidence"])
                    if b["n"] else None)
        del b["conf_sum"]
    return bins


def ece(y_true, p_off, n_bins=15):
    """Expected and maximum calibration error, plus the signed mean gap.

    `signed_gap` = mean(accuracy - confidence) weighted by bin size. Its SIGN is
    the answer to "over- or under-confident": negative means confidence exceeds
    accuracy, i.e. overconfident. ECE alone is unsigned and cannot say which.
    """
    bins = reliability_bins(y_true, p_off, n_bins)
    n = sum(b["n"] for b in bins)
    if n == 0:
        return {"ece": None, "mce": None, "signed_gap": None, "n": 0, "n_bins": n_bins}
    e = sum((b["n"] / n) * abs(b["gap"]) for b in bins if b["n"])
    m = max((abs(b["gap"]) for b in bins if b["n"]), default=0.0)
    s = sum((b["n"] / n) * b["gap"] for b in bins if b["n"])
    return {"ece": e, "mce": m, "signed_gap": s, "n": n, "n_bins": n_bins}


# --------------------------------------------------------------------------
# temperature fitting
# --------------------------------------------------------------------------

def nll(y_true, p_off, T=1.0):
    """Mean negative log-likelihood of the labels under temperature T."""
    total = 0.0
    for gold, p in zip(y_true, p_off):
        q = clip(apply_temperature(p, T))
        total += -math.log(q if gold == "OFF" else 1.0 - q)
    return total / len(y_true)


def fit_temperature(y_true, p_off, lo=0.05, hi=20.0, tol=1e-6, max_iter=200):
    """Fit T by minimising NLL. Golden-section search on log T.

    Search is on log T because T is a scale parameter -- halving and doubling
    should cost the same number of steps. Golden-section needs only unimodality,
    not a derivative, which keeps this dependency-free; NLL under temperature
    scaling is unimodal in log T for a fixed set of logits.

    A coarse grid pass runs first and brackets the minimum, so a flat or
    monotone region inside [lo, hi] cannot strand the search in a corner.
    """
    if not y_true:
        raise ValueError("cannot fit a temperature on zero rows")

    grid = [lo * (hi / lo) ** (i / 40.0) for i in range(41)]
    vals = [nll(y_true, p_off, t) for t in grid]
    k = min(range(len(grid)), key=lambda i: vals[i])
    a = math.log(grid[max(0, k - 1)])
    b = math.log(grid[min(len(grid) - 1, k + 1)])

    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = b - inv_phi * (b - a), a + inv_phi * (b - a)
    fc, fd = nll(y_true, p_off, math.exp(c)), nll(y_true, p_off, math.exp(d))
    for _ in range(max_iter):
        if abs(b - a) < tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - inv_phi * (b - a)
            fc = nll(y_true, p_off, math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + inv_phi * (b - a)
            fd = nll(y_true, p_off, math.exp(d))
    T = math.exp((a + b) / 2.0)

    # A fit that lands on the search bound is not a fit -- it means the NLL is
    # still decreasing at the edge, i.e. the optimum is outside [lo, hi]. That
    # happens when scores carry little or no information about the labels, and
    # T -> infinity just flattens every probability toward 0.5. Reporting the
    # bound as "the temperature" would look like a measurement, so it is flagged
    # and callers are expected to say so out loud.
    at_boundary = (T <= lo * 1.001) or (T >= hi * 0.999)

    return {"temperature": T,
            "nll_before": nll(y_true, p_off, 1.0),
            "nll_after": nll(y_true, p_off, T),
            "n_fit": len(y_true),
            "grid_best": grid[k],
            "search_lo": lo,
            "search_hi": hi,
            "at_boundary": at_boundary}


# --------------------------------------------------------------------------
# selective prediction
# --------------------------------------------------------------------------

def _order(p_off):
    """Row indices sorted most-confident first. Ties broken by index so the
    ordering is deterministic and reproducible across runs and machines."""
    return sorted(range(len(p_off)),
                  key=lambda i: (-decision_confidence(p_off[i]), i))


def risk_coverage(y_true, y_pred, p_off, coverages):
    """Metrics on the auto-resolved portion at each coverage level.

    At coverage c the c most-confident rows are answered automatically and the
    rest are deferred to human review. Deferred rows are NOT counted as errors:
    they are counted as deferred, which is what a review queue actually does.
    """
    order = _order(p_off)
    n = len(order)
    out = []
    for c in coverages:
        k = max(1, int(round(c * n)))
        keep = order[:k]
        gt = [y_true[i] for i in keep]
        gp = [y_pred[i] for i in keep]
        s = evaluate.score(gt, gp, with_ci=False)
        errors = sum(1 for a, b in zip(gt, gp) if a != b)
        out.append({
            "target_coverage": c,
            "coverage": k / n,
            "n_auto": k,
            "n_deferred": n - k,
            "macro_f1": s["macro_f1"],
            "error_rate": errors / k,
            "errors": errors,
            "off_recall": s["off_recall"],
            "off_precision": s["off_precision"],
            "threshold": decision_confidence(p_off[order[k - 1]]),
        })
    return out


def threshold_for_coverage(p_off, coverage):
    """Confidence threshold that yields `coverage` on THESE rows.

    Selected on CAL and applied unchanged to EVAL (C4-4), so that a threshold is
    never chosen on the rows it is then scored on.
    """
    order = _order(p_off)
    k = max(1, int(round(coverage * len(order))))
    return decision_confidence(p_off[order[k - 1]])


def apply_threshold(y_true, y_pred, p_off, threshold, slices=None):
    """Split rows into auto-resolved and deferred at a FIXED threshold.

    Returns the operating-point block plus, if slice tags are supplied, the
    per-slice deferral breakdown required by C4-6.
    """
    auto, deferred = [], []
    for i, p in enumerate(p_off):
        (auto if decision_confidence(p) >= threshold else deferred).append(i)

    n = len(p_off)
    gt = [y_true[i] for i in auto]
    gp = [y_pred[i] for i in auto]
    s = evaluate.score(gt, gp, with_ci=False) if auto else {}
    auto_err = sum(1 for a, b in zip(gt, gp) if a != b)
    def_err = sum(1 for i in deferred if y_true[i] != y_pred[i])
    all_err = auto_err + def_err

    block = {
        "threshold": threshold,
        "coverage": len(auto) / n,
        "n_auto": len(auto),
        "n_deferred": len(deferred),
        "macro_f1": s.get("macro_f1"),
        "error_rate": (auto_err / len(auto)) if auto else None,
        "errors_auto": auto_err,
        "off_recall": s.get("off_recall"),
        "off_precision": s.get("off_precision"),
        "deferred_error_rate": (def_err / len(deferred)) if deferred else None,
        "errors_deferred": def_err,
        "errors_total": all_err,
        # Lift > 1 means deferral beats random at catching errors.
        "capture_lift": (((def_err / all_err) / (len(deferred) / n))
                         if all_err and deferred else None),
        "error_capture_share": (def_err / all_err) if all_err else None,
    }

    if slices is not None:
        by = {}
        for tag in sorted(set(slices)):
            idx = [i for i in range(n) if slices[i] == tag]
            d_idx = [i for i in deferred if slices[i] == tag]
            a_idx = [i for i in auto if slices[i] == tag]
            d_err = sum(1 for i in d_idx if y_true[i] != y_pred[i])
            a_err = sum(1 for i in a_idx if y_true[i] != y_pred[i])
            by[tag] = {
                "n_rows": len(idx),
                "share_of_dev": len(idx) / n,
                "n_deferred": len(d_idx),
                "deferral_rate": len(d_idx) / len(idx) if idx else None,
                "share_of_deferrals": (len(d_idx) / len(deferred)) if deferred else None,
                "errors_deferred": d_err,
                "errors_auto": a_err,
                "auto_error_rate": (a_err / len(a_idx)) if a_idx else None,
                "deferred_error_rate": (d_err / len(d_idx)) if d_idx else None,
                "errors_total": d_err + a_err,
                "error_capture_share": ((d_err / (d_err + a_err))
                                        if (d_err + a_err) else None),
            }
        block["by_slice"] = by
    return block


def bootstrap_operating_point(y_true, y_pred, p_off, threshold,
                              n_boot=1000, seed=42, alpha=0.05):
    """Percentile CIs for an operating point at a FIXED threshold.

    Rows are resampled with replacement and the same threshold reapplied, so the
    interval covers both which rows are auto-resolved and how well they score.
    The threshold is held fixed because it was selected on CAL -- re-selecting it
    inside each resample would measure a different, self-tuning procedure.
    """
    import random

    rng = random.Random(seed)
    n = len(p_off)
    conf = [decision_confidence(p) for p in p_off]
    ok = [1 if y_true[i] == y_pred[i] else 0 for i in range(n)]
    codes = evaluate._codes(y_true, y_pred)

    cov, mf1, err = [], [], []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        keep = [i for i in idx if conf[i] >= threshold]
        if not keep:
            continue
        cov.append(len(keep) / n)
        err.append(1.0 - sum(ok[i] for i in keep) / len(keep))
        tn = fp = fn = tp = 0
        for i in keep:
            c = codes[i]
            if c == 3:
                tp += 1
            elif c == 2:
                fn += 1
            elif c == 1:
                fp += 1
            else:
                tn += 1
        mf1.append(evaluate._metrics_from_tally(tn, fp, fn, tp)["macro_f1"])

    def ci(vals):
        v = sorted(vals)
        return {"ci_low": evaluate._percentile(v, alpha / 2),
                "ci_high": evaluate._percentile(v, 1 - alpha / 2)}

    return {"coverage": ci(cov), "macro_f1": ci(mf1), "error_rate": ci(err),
            "n_boot_used": len(mf1)}


def verify_rc_invariance(y_true, y_pred, p_off, T, coverages, tol=1e-12):
    """Self-check for C4-3: temperature must not move the risk-coverage curve.

    Returns (ok, max_abs_diff). Called by the driver and reported, so the claim
    is verified numerically rather than asserted from the algebra.
    """
    scaled = [apply_temperature(p, T) for p in p_off]
    a = risk_coverage(y_true, y_pred, p_off, coverages)
    b = risk_coverage(y_true, y_pred, scaled, coverages)
    worst = 0.0
    for x, y in zip(a, b):
        for k in ("macro_f1", "error_rate", "coverage"):
            worst = max(worst, abs(x[k] - y[k]))
    return worst <= tol, worst
