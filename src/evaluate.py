"""Unified metric computation across every system in the comparison matrix.

Fulfils phase 01 S5 (macro-F1 / OFF-precision / OFF-recall, per slice, plus a
bootstrap CI on the recall GAP) and briefing S8.

This module exists so that the keyword filter, BERTurk, the defense and the
calibrated system are all scored by literally the same code path. A metric
computed slightly differently per system makes the Section 8 table meaningless.

Two deliberate choices
----------------------
1. **Pure stdlib.** No numpy/sklearn/torch import at module level, so this runs
   in the local Python 3.14 venv (pytest only) as well as on Colab. Metrics can
   therefore be unit-tested locally, before any GPU time is spent.
2. **Cross-checked against sklearn, not replaced by it.** `sklearn_report()`
   produces the human-readable report file and, in the same call, asserts that
   sklearn's macro-F1 agrees with the number computed here to 1e-9. If the two
   ever disagree, the run stops instead of publishing a metric nobody rechecked.

Predictions come in as label lists, never as models -- this module cannot
accidentally trigger a test-set load (briefing S7.2).
"""

import math
import random

LABELS = ("NOT", "OFF")
POSITIVE = "OFF"


# --------------------------------------------------------------------------
# counting
# --------------------------------------------------------------------------


def _check(y_true, y_pred):
    if len(y_true) != len(y_pred):
        raise ValueError(f"length mismatch: {len(y_true)} gold vs {len(y_pred)} predicted")
    bad = (set(y_true) | set(y_pred)) - set(LABELS)
    if bad:
        raise ValueError(f"labels outside {LABELS}: {sorted(bad)}")


def _codes(y_true, y_pred, positive=POSITIVE):
    """Per-row outcome code w.r.t. the positive class: 3=tp 2=fn 1=fp 0=tn.

    Bootstrapping resamples these small ints instead of re-comparing strings,
    which is what makes 1,000 resamples cheap in pure Python.
    """
    return [
        (2 if t == positive else 0) + (1 if p == positive else 0)
        for t, p in zip(y_true, y_pred)
    ]


def _tally(codes):
    tn = fp = fn = tp = 0
    for c in codes:
        if c == 3:
            tp += 1
        elif c == 2:
            fn += 1
        elif c == 1:
            fp += 1
        else:
            tn += 1
    return tn, fp, fn, tp


def _f1(tp, fp, fn):
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else 0.0


def _metrics_from_tally(tn, fp, fn, tp):
    """macro-F1 treats NOT as the positive class of the other binary problem:
    its tp is tn, its fp is fn, its fn is fp."""
    f1_off = _f1(tp, fp, fn)
    f1_not = _f1(tn, fn, fp)
    n = tn + fp + fn + tp
    return {
        "macro_f1": (f1_off + f1_not) / 2,
        "off_precision": (tp / (tp + fp)) if (tp + fp) else None,
        "off_recall": (tp / (tp + fn)) if (tp + fn) else None,
        "off_f1": f1_off,
        "not_f1": f1_not,
        "accuracy": ((tp + tn) / n) if n else None,
        "n": n,
        "support_off": tp + fn,
        "support_not": tn + fp,
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def macro_f1(y_true, y_pred):
    _check(y_true, y_pred)
    return _metrics_from_tally(*_tally(_codes(y_true, y_pred)))["macro_f1"]


def off_recall(y_true, y_pred):
    _check(y_true, y_pred)
    return _metrics_from_tally(*_tally(_codes(y_true, y_pred)))["off_recall"]


# --------------------------------------------------------------------------
# bootstrap
# --------------------------------------------------------------------------


def _percentile(sorted_vals, q):
    """Linear-interpolated percentile, q in [0, 1]."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_vals[int(pos)]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _resample_tallies(codes, n_boot, rng):
    """Yield (tn, fp, fn, tp) for each nonparametric bootstrap resample."""
    n = len(codes)
    if n == 0:
        return
    population = range(n)
    for _ in range(n_boot):
        yield _tally([codes[i] for i in rng.choices(population, k=n)])


def bootstrap_ci(y_true, y_pred, metric="macro_f1", n_boot=1000, seed=42, alpha=0.05):
    """Percentile CI for one metric on one set of predictions.

    Nonparametric bootstrap over rows: resample the evaluation set with
    replacement n_boot times, recompute, take the alpha/2 and 1-alpha/2
    percentiles. Resamples in which the metric is undefined (e.g. OFF-recall
    with zero OFF examples drawn) are dropped and counted, not treated as 0.
    """
    _check(y_true, y_pred)
    codes = _codes(y_true, y_pred)
    rng = random.Random(seed)
    vals = []
    dropped = 0
    for tally in _resample_tallies(codes, n_boot, rng):
        v = _metrics_from_tally(*tally)[metric]
        if v is None:
            dropped += 1
        else:
            vals.append(v)
    vals.sort()
    return {
        "metric": metric,
        "ci_low": _percentile(vals, alpha / 2),
        "ci_high": _percentile(vals, 1 - alpha / 2),
        "n_boot": n_boot,
        "n_boot_used": len(vals),
        "n_boot_undefined": dropped,
        "alpha": alpha,
        "seed": seed,
    }


def bootstrap_gap_ci(
    y_true_a, y_pred_a, y_true_b, y_pred_b, metric="off_recall", n_boot=1000, seed=42, alpha=0.05
):
    """CI for (metric on slice A) - (metric on slice B).

    THE pivotal number of phase 01: A = lexicon_hit, B = lexicon_free.

    The two slices are disjoint sets of rows, so they are resampled
    independently -- an unpaired difference of two proportions. Pairing would be
    wrong here: no row appears in both slices, so there is nothing to pair on.
    The same rng drives both, so the whole procedure is reproducible from `seed`.

    Returns delta (the point estimate on the real data) plus the percentile CI
    of the resampled deltas. A CI excluding zero is what the pre-registered
    decision rule calls "gap survives".
    """
    _check(y_true_a, y_pred_a)
    _check(y_true_b, y_pred_b)
    codes_a = _codes(y_true_a, y_pred_a)
    codes_b = _codes(y_true_b, y_pred_b)

    point_a = _metrics_from_tally(*_tally(codes_a))[metric]
    point_b = _metrics_from_tally(*_tally(codes_b))[metric]
    delta = None if (point_a is None or point_b is None) else point_a - point_b

    rng = random.Random(seed)
    deltas = []
    dropped = 0
    gen_a = _resample_tallies(codes_a, n_boot, rng)
    gen_b = _resample_tallies(codes_b, n_boot, rng)
    for ta, tb in zip(gen_a, gen_b):
        va = _metrics_from_tally(*ta)[metric]
        vb = _metrics_from_tally(*tb)[metric]
        if va is None or vb is None:
            dropped += 1
        else:
            deltas.append(va - vb)
    deltas.sort()

    ci_low = _percentile(deltas, alpha / 2)
    ci_high = _percentile(deltas, 1 - alpha / 2)
    return {
        "metric": metric,
        "value_a": point_a,
        "value_b": point_b,
        "delta": delta,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "excludes_zero": None if (ci_low is None or ci_high is None) else (ci_low > 0 or ci_high < 0),
        "n_boot": n_boot,
        "n_boot_used": len(deltas),
        "n_boot_undefined": dropped,
        "alpha": alpha,
        "seed": seed,
        "resampling": "independent (disjoint slices), percentile CI",
    }


# --------------------------------------------------------------------------
# the public scoring call
# --------------------------------------------------------------------------


def score(y_true, y_pred, n_boot=1000, seed=42, alpha=0.05, with_ci=True):
    """Full metric block for one system on one evaluation set."""
    _check(y_true, y_pred)
    out = _metrics_from_tally(*_tally(_codes(y_true, y_pred)))
    if with_ci and n_boot:
        out["ci"] = {
            "macro_f1": bootstrap_ci(y_true, y_pred, "macro_f1", n_boot, seed, alpha),
            "off_recall": bootstrap_ci(y_true, y_pred, "off_recall", n_boot, seed, alpha),
        }
    return out


# --------------------------------------------------------------------------
# slices (phase 01 S2 -- tagging uses src.lexicon as-is, never a reimplementation)
# --------------------------------------------------------------------------


def tag_slices(rows, lex_list):
    """Tag each row 'lexicon_hit' / 'lexicon_free' with the FROZEN matcher.

    `lexicon.hit_root` is the Day 1 adopted definition of "the lexicon caught
    it". It is imported, never reimplemented -- a second copy of the rule would
    be free to drift away from the frozen record.
    """
    from src import lexicon

    return ["lexicon_hit" if lexicon.hit_root(r["text"], lex_list) else "lexicon_free" for r in rows]


def score_by_slice(y_true, y_pred, slice_tags, n_boot=1000, seed=42, alpha=0.05):
    """Per-slice metric blocks, keyed by tag.

    PRE-REGISTERED CONSTRAINT (phases/01_baseline_diagnosis.md, binding on every
    later phase): the cross-slice comparison is **OFF-recall only**. The full
    block is returned here because the numbers are meaningful *within* a slice,
    but macro-F1 and accuracy must not be compared *between* slices -- dev base
    rates are 57.8% OFF in lexicon_hit vs 13.6% in lexicon_free, so a difference
    on those metrics reports class balance as if it were model behaviour.
    OFF-recall conditions on gold=OFF and is immune to that.
    """
    if not (len(y_true) == len(y_pred) == len(slice_tags)):
        raise ValueError("y_true, y_pred and slice_tags must be the same length")
    out = {}
    for tag in sorted(set(slice_tags)):
        idx = [i for i, t in enumerate(slice_tags) if t == tag]
        out[tag] = score(
            [y_true[i] for i in idx],
            [y_pred[i] for i in idx],
            n_boot=n_boot,
            seed=seed,
            alpha=alpha,
        )
    return out


# --------------------------------------------------------------------------
# human-readable report + the sklearn cross-check
# --------------------------------------------------------------------------


def sklearn_report(y_true, y_pred, title="", digits=4, strict=True):
    """sklearn's classification_report text, cross-checked against this module.

    Raises if sklearn's macro-F1 disagrees with ours by more than 1e-9: one of
    the two implementations would then be wrong, and we would not know which.
    Returns a plain-text fallback (clearly labelled) if sklearn is unavailable,
    unless strict=True.
    """
    ours = macro_f1(y_true, y_pred)
    try:
        from sklearn.metrics import classification_report, f1_score
    except ImportError:
        if strict:
            raise
        m = _metrics_from_tally(*_tally(_codes(y_true, y_pred)))
        return (
            f"{title}\n[sklearn unavailable -- stdlib metrics only]\n"
            f"  macro_f1={m['macro_f1']:.{digits}f}  off_precision={m['off_precision']}\n"
            f"  off_recall={m['off_recall']}  n={m['n']}  support_off={m['support_off']}\n"
        )

    theirs = f1_score(y_true, y_pred, labels=list(LABELS), average="macro", zero_division=0)
    if abs(theirs - ours) > 1e-9:
        raise AssertionError(
            f"macro-F1 mismatch: src.evaluate={ours!r} vs sklearn={theirs!r}. "
            "One of the two is wrong -- do not report either number until this is resolved."
        )
    text = classification_report(
        y_true, y_pred, labels=list(LABELS), digits=digits, zero_division=0
    )
    return f"{title}\n{text}"
