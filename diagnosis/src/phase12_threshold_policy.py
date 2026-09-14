#!/usr/bin/env python3
"""Phase 12 -- threshold policy: slice-conditional vs a single cost-optimal threshold.

Pre-registration: `phases/12_threshold_policy.md`, C12-1..C12-15, committed at
ec2fd3a7 BEFORE any number in this file existed, with Addendum 1 at 584292c and
Addendum 2 at 2b4391bf. The pre-registration is authoritative; this module
implements it and does not extend it.

**Naming, per Addendum 1 item 1.** The four SYSTEMS are S0 / S1a / S1b / S2.
The three SENSITIVITIES are SENS-1 (cost frontier), SENS-2 (`MIN_ROOT_LEN`
leak), SENS-3 (suspect-root contamination). `S1`/`S2` never denote a
sensitivity anywhere in this file or in its output.

Every number this module produces is **dev-only** and is labelled dev-only in
both the stdout report and `metrics.json`. Read-only: no training, no forward
pass, no model loaded, the lexicon and MIN_ROOT_LEN frozen, and
`load_coltekin_test` is never called -- the official test set is spent and stays
spent.

Two things this file must not be misread as doing:

  * It never compares one slice against the other. Every endpoint is TWO
    SYSTEMS ON THE SAME ROWS (C12-5). Per-slice figures under C12-8 describe one
    system and are never used to match operating points across slices -- that
    was the SPEC DEFECT recorded against C9-8 on 2026-08-17.
  * It reports no per-slice macro-F1 and no per-slice accuracy (C12-2, the
    phase-01 constraint). Raw confusion counts, OFF-recall and OFF-precision
    only.

Usage:
    python -m src.phase12_threshold_policy
"""

import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config                                                       # noqa: E402
from src import data_io, lexicon                                    # noqa: E402
from src import phase11_prior_correction as p11                     # noqa: E402

RUN_ID = "12_threshold_policy"
STAGE = "primary (r=3), stability, descriptive frontier, SENS-1/2/3"
PREREG = "phases/12_threshold_policy.md @ ec2fd3a7 (+584292c, +2b4391bf)"

OUT_DIR = ROOT / "results/12_threshold_policy"
SPLIT_SHA256 = "6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899"

# --- C12-2: frozen fitting and scoring denominators ---------------------------
CAL_CELLS = [("lexicon_hit", "OFF", 173), ("lexicon_hit", "NOT", 132),
             ("lexicon_free", "OFF", 287), ("lexicon_free", "NOT", 1790)]
EVAL_CELLS = [("lexicon_hit", "OFF", 182), ("lexicon_hit", "NOT", 127),
              ("lexicon_free", "OFF", 278), ("lexicon_free", "NOT", 1795)]
SLICES = ("lexicon_hit", "lexicon_free")

# --- C12-4: the cost grid -----------------------------------------------------
R_GRID = (1, 2, 3, 5, 10)
R_PRIMARY = 3
FROZEN_THRESHOLD = 0.5          # S0, and the historical reference

# --- C12-6: interval estimation ----------------------------------------------
N_BOOT = 10000
BOOT_SEED = 42
ALPHA = 0.05

# --- C12-7: the verdict bands -------------------------------------------------
D_FLOOR = 40
SMALL = 0.04
LARGE = 0.10

# --- C12-9: the pre-registered instability rule -------------------------------
IQR_T_HIT_LIMIT = 0.20

# --- C12-11 / Addendum 1 item 1: the sensitivities, under their new names -----
SENS2_TOKENS = {"ag", "am", "aq", "oc", "oç"}
SENS3_ROOTS = {"allah", "ana", "cim", "emi", "göt", "mal", "sie"}
SENS2_EXPECTED_FULL_DEV = 28    # phases/12_threshold_policy.md C12-11, phase 08

# Matched-flag-count search (C12-8). Declared here rather than after the fact.
RPRIME_GRID = (0.001, 20.000, 0.001)    # start, stop inclusive, step


# ==============================================================================
# C12-4 -- the cost model
# ==============================================================================

def cost(fp, fn, n, r):
    """Expected cost per row: `(FP + r*FN) / N`, with `c_FP = 1`, `c_FN = r`."""
    if n <= 0:
        raise ValueError(f"cost() needs a positive denominator, got N={n}")
    return (float(fp) + float(r) * float(fn)) / float(n)


def elkan_threshold(r):
    """C12-1: `t* = c_FP/(c_FP + c_FN) = 1/(1+r)`. Base-rate independent.

    At `r = 1` this is exactly 0.5 in binary floating point, which is what makes
    the C12-4 correctness check (S1a reproduces S0 bit for bit) meaningful
    rather than approximate.
    """
    return 1.0 / (1.0 + float(r))


# ==============================================================================
# C12-3 -- the fitting protocol
# ==============================================================================

def _gold01(gold):
    """Accept `OFF`/`NOT` strings or 0/1, return a float array of 1.0 for OFF."""
    out = np.empty(len(gold), dtype=np.float64)
    for i, g in enumerate(gold):
        if isinstance(g, str):
            if g not in ("OFF", "NOT"):
                raise ValueError(f"gold label must be OFF or NOT, got {g!r}")
            out[i] = 1.0 if g == "OFF" else 0.0
        else:
            v = float(g)
            if v not in (0.0, 1.0):
                raise ValueError(f"numeric gold must be 0 or 1, got {g!r}")
            out[i] = v
    return out


def cost_curve(scores, gold01):
    """Candidate thresholds ascending, with FP and FN at each.

    The candidate set is C12-3's: the distinct observed scores among the rows
    being fitted, PLUS one value strictly below their minimum so that "flag
    everything" is reachable under the frozen `flag iff score > t` rule. That
    extra candidate is `nextafter(min, -inf)` -- the largest representable float
    strictly below the minimum, so it is provably below every observed score
    without inventing a gap of arbitrary size.

    Returns `(cand, fp, fn, n_flagged)`, all aligned and length `len(unique)+1`.
    """
    s = np.asarray(scores, dtype=np.float64)
    g = np.asarray(gold01, dtype=np.float64)
    if s.size == 0:
        raise ValueError("cannot fit a threshold on zero rows")
    order = np.argsort(s, kind="mergesort")
    s = s[order]
    g = g[order]

    uniq = np.unique(s)
    cand = np.concatenate(([np.nextafter(uniq[0], -np.inf)], uniq))

    # le[k] = number of rows with score <= cand[k]  (these are NOT flagged)
    le = np.searchsorted(s, cand, side="right")
    cum_off = np.concatenate(([0.0], np.cumsum(g)))
    n_off = cum_off[-1]
    n_not = float(s.size) - n_off

    fn = cum_off[le]                       # gold OFF, score <= t  -> missed
    not_le = le.astype(np.float64) - cum_off[le]
    fp = n_not - not_le                    # gold NOT, score >  t  -> false flag
    n_flagged = float(s.size) - le.astype(np.float64)
    return cand, fp, fn, n_flagged


def fit_threshold(scores, gold, r):
    """C12-3: the `t` minimising empirical cost on these rows, ties to the LOWER.

    `np.argmin` returns the first minimum and `cand` is ascending, so the tie
    rule is the array order rather than a separate comparison. C12-3 declares
    the tie direction in advance because it maximises recall at equal cost and
    is therefore the choice least favourable to the null C12-10 predicts.
    """
    if len(scores) != len(gold):
        raise ValueError(f"{len(scores)} scores against {len(gold)} labels")
    if len(scores) == 0:
        raise ValueError("cannot fit a threshold on zero rows")
    if float(r) <= 0:
        raise ValueError(f"cost ratio must be positive, got {r}")
    cand, fp, fn, _ = cost_curve(scores, _gold01(gold))
    c = (fp + float(r) * fn) / float(len(scores))
    return float(cand[int(np.argmin(c))])


def _fit_from_curve(cand, fp, fn, n, r):
    """Same selection, on a curve computed once. Used inside bootstrap loops and
    the r' grid search so the curve is not rebuilt for every candidate `r`."""
    c = (fp + float(r) * fn) / float(n)
    j = int(np.argmin(c))
    return float(cand[j]), j


# ==============================================================================
# C12-7 -- the verdict rule
# ==============================================================================

def verdict_branch(dcost_rel, ci_low, ci_high, d):
    """C12-7, evaluated in order. Returns `(branch_number, verdict_string)`.

    Branch 0 is first and unconditional on the interval: `d` is not knowable
    until the thresholds are fitted, and C12-7 forbids reframing a
    coincidentally small `dCost_rel` on few discordant rows as a null.

    The magnitude bands are on `|dCost_rel|` exactly as C12-7 writes them. Under
    `ci_high < 0` a positive point estimate is contradictory input; the rule is
    not silently sign-filtered to hide that.
    """
    if ci_low > ci_high:
        raise ValueError(f"inverted interval: ci_low={ci_low} > ci_high={ci_high}")
    if d < 0:
        raise ValueError(f"discordant count cannot be negative, got {d}")

    if d < D_FLOOR:
        return 0, "INSUFFICIENT"
    if ci_low > 0:
        return 1, "SLICE-CONDITIONAL WORSE"
    if ci_low <= 0 <= ci_high:
        return 2, "SINGLE-THRESHOLD-SUFFICIENT"
    # ci_high < 0 from here: ci_low <= ci_high < 0 and ci_low is not > 0.
    mag = abs(dcost_rel)
    if mag < SMALL:
        return 3, "SINGLE-THRESHOLD-SUFFICIENT"
    if mag < LARGE:
        return 4, "INTERMEDIATE"
    return 5, "SLICE-CONDITIONAL BETTER"


def verdict(dcost_rel, ci_low, ci_high, d):
    return verdict_branch(dcost_rel, ci_low, ci_high, d)[1]


# ==============================================================================
# systems, scoring, confusion
# ==============================================================================

def system_thresholds(name, r, fitted):
    """The per-slice threshold map for one system at one `r` (C12-3)."""
    if name == "S0":
        return {sl: FROZEN_THRESHOLD for sl in SLICES}
    if name == "S1a":
        return {sl: elkan_threshold(r) for sl in SLICES}
    if name == "S1b":
        return {sl: fitted["S1b"][r] for sl in SLICES}
    if name == "S2":
        return {sl: fitted["S2"][r][sl] for sl in SLICES}
    raise ValueError(f"unknown system {name!r}")


def flags_for(rows, thr):
    """`flag iff score > t`, with `t` chosen by the row's own slice."""
    return np.array([r["p_off"] > thr[r["slice"]] for r in rows], dtype=bool)


def confusion(rows, flag):
    off = np.array([r["gold"] == "OFF" for r in rows], dtype=bool)
    tp = int((off & flag).sum())
    fp = int((~off & flag).sum())
    fn = int((off & ~flag).sum())
    tn = int((~off & ~flag).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "n": len(rows), "n_flagged": int(flag.sum()), "n_gold_off": int(off.sum())}


def _rate(num, den):
    return float(num) / float(den) if den else None


def describe_system(rows, thr, r, name):
    """C12-8: everything reported for one system at one `r`, on EVAL.

    NOT reported, per C12-2 and the phase-01 constraint: per-slice macro-F1 and
    per-slice accuracy. The slices' base rates differ by a factor of four and
    those two statistics are not comparable across them. Raw confusion counts,
    OFF-recall and OFF-precision are.
    """
    flag = flags_for(rows, thr)
    cf = confusion(rows, flag)
    out = {"system": name, "r": r,
           "thresholds": {sl: float(thr[sl]) for sl in SLICES},
           "cost": cost(cf["fp"], cf["fn"], cf["n"], r),
           "confusion": cf,
           "off_recall": _rate(cf["tp"], cf["n_gold_off"]),
           "off_precision": _rate(cf["tp"], cf["n_flagged"]),
           "per_slice": {}}
    for sl in SLICES:
        idx = [i for i, x in enumerate(rows) if x["slice"] == sl]
        sub = [rows[i] for i in idx]
        sf = flag[idx]
        c = confusion(sub, sf)
        out["per_slice"][sl] = {
            "confusion": c,
            "off_recall": _rate(c["tp"], c["n_gold_off"]),
            "off_precision": _rate(c["tp"], c["n_flagged"]),
        }
    rh = out["per_slice"]["lexicon_hit"]["off_recall"]
    rf = out["per_slice"]["lexicon_free"]["off_recall"]
    out["recall_gap_hit_minus_free"] = (rh - rf) if (rh is not None and rf is not None) else None
    return out


# ==============================================================================
# C12-6 -- the paired, stratified bootstrap on EVAL
# ==============================================================================

def paired_bootstrap(cells, thr_a, thr_b, r, n, n_boot=N_BOOT, seed=BOOT_SEED,
                     alpha=ALPHA):
    """C12-6. `cells` is an ordered list of `(slice, gold, scores)`.

    Both arms score the IDENTICAL resampled rows -- one index draw per cell,
    used by both -- which is what makes the interval paired and removes the
    between-system variance. Thresholds are fixed by CAL and are NOT refitted
    inside the replicate: that is what "fitted on CAL, applied to EVAL" means,
    so this interval carries EVAL sampling variance and not threshold-selection
    variance. C12-9 measures the latter separately and directly.

    Each cell is resampled to its own original size, so the frozen denominators
    are preserved in every replicate. Cells are drawn in the order C12-2 lists
    them; the draw order is part of what `seed=42` reproduces.
    """
    rng = np.random.default_rng(seed)
    pre = []
    for sl, gold, scores in cells:
        s = np.asarray(scores, dtype=np.float64)
        fa = (s > thr_a[sl])
        fb = (s > thr_b[sl])
        if gold == "OFF":
            # a missed OFF row costs r; a flagged one costs nothing
            pre.append(((~fa).astype(np.float64) * r, (~fb).astype(np.float64) * r))
        else:
            # a flagged NOT row costs 1; a passed one costs nothing
            pre.append((fa.astype(np.float64), fb.astype(np.float64)))

    ratios = np.empty(n_boot, dtype=np.float64)
    diffs = np.empty(n_boot, dtype=np.float64)
    cost_a = np.empty(n_boot, dtype=np.float64)
    cost_b = np.empty(n_boot, dtype=np.float64)
    undefined = 0
    for b in range(n_boot):
        ta = 0.0
        tb = 0.0
        for ca, cb in pre:
            i = rng.integers(0, ca.size, ca.size)
            ta += float(ca[i].sum())
            tb += float(cb[i].sum())
        ca_, cb_ = ta / n, tb / n
        cost_a[b], cost_b[b] = ca_, cb_
        diffs[b] = cb_ - ca_
        if ca_ == 0.0:
            undefined += 1
            ratios[b] = np.nan
        else:
            ratios[b] = (cb_ - ca_) / ca_

    good = ratios[~np.isnan(ratios)]
    return {
        "ci_low": float(np.percentile(good, 100 * alpha / 2)),
        "ci_high": float(np.percentile(good, 100 * (1 - alpha / 2))),
        "boot_mean": float(good.mean()),
        "boot_median": float(np.median(good)),
        "abs_diff_ci_low": float(np.percentile(diffs, 100 * alpha / 2)),
        "abs_diff_ci_high": float(np.percentile(diffs, 100 * (1 - alpha / 2))),
        "cost_baseline_boot_mean": float(cost_a.mean()),
        "cost_arm_boot_mean": float(cost_b.mean()),
        "n_boot": n_boot, "n_boot_used": int(good.size), "n_boot_undefined": undefined,
        "alpha": alpha, "seed": seed,
        "paired": True, "thresholds_refitted_inside_replicate": False,
        "strata": [{"slice": sl, "gold": g, "n": len(s)} for sl, g, s in cells],
    }


# ==============================================================================
# C12-9 -- threshold stability, measured rather than assumed
# ==============================================================================

def cal_refit_bootstrap(cal_cells, r, n_boot=N_BOOT, seed=BOOT_SEED):
    """C12-9: refit `t_hit` and `t_free` INSIDE 10,000 bootstrap replicates of
    CAL, stratified over the four CAL cells, and report each distribution.

    This is a separate computation from C12-6 and answers a different question:
    C12-6 asks how much the EVAL score would move on a different evaluation
    sample; this asks how much the fitted threshold itself would move on a
    different fitting sample. The `lexicon_hit` CAL cell is 305 rows (173 gold
    OFF), so its empirical cost curve is flat near the minimum and the argmin is
    weakly determined. C12-9 declines to call that INSUFFICIENT by construction
    and measures it instead.
    """
    rng = np.random.default_rng(seed)
    by_slice = {}
    for sl in SLICES:
        s = np.concatenate([np.asarray(sc, dtype=np.float64)
                            for x, g, sc in cal_cells if x == sl])
        g01 = np.concatenate([np.full(len(sc), 1.0 if g == "OFF" else 0.0)
                              for x, g, sc in cal_cells if x == sl])
        by_slice[sl] = (s, g01)

    order = [(sl, g) for sl, g, _ in cal_cells]
    draw = {(sl, g): np.asarray(sc, dtype=np.float64)
            for sl, g, sc in cal_cells}
    fitted = {sl: np.empty(n_boot, dtype=np.float64) for sl in SLICES}

    for b in range(n_boot):
        rep = {}
        for key in order:
            arr = draw[key]
            i = rng.integers(0, arr.size, arr.size)
            rep[key] = arr[i]
        for sl in SLICES:
            s = np.concatenate([rep[(sl, "OFF")], rep[(sl, "NOT")]])
            g01 = np.concatenate([np.ones(rep[(sl, "OFF")].size),
                                  np.zeros(rep[(sl, "NOT")].size)])
            cand, fp, fn, _ = cost_curve(s, g01)
            t, _j = _fit_from_curve(cand, fp, fn, s.size, r)
            fitted[sl][b] = t

    out = {}
    for sl in SLICES:
        a = fitted[sl]
        q25, q50, q75 = (float(np.percentile(a, q)) for q in (25, 50, 75))
        out[sl] = {"median": q50, "q25": q25, "q75": q75, "iqr": q75 - q25,
                   "p5": float(np.percentile(a, 5)), "p95": float(np.percentile(a, 95)),
                   "boot_min": float(a.min()), "boot_max": float(a.max()),
                   "n_boot": n_boot, "seed": seed, "r": r}
    out["_unstable_rule"] = {
        "clause": "C12-9",
        "statistic": "IQR of the bootstrap distribution of t_hit",
        "limit": IQR_T_HIT_LIMIT,
        "observed": out["lexicon_hit"]["iqr"],
        "S2_arm_unstable": bool(out["lexicon_hit"]["iqr"] > IQR_T_HIT_LIMIT),
        "note": "may qualify the verdict; may not overturn it",
    }
    return out


# ==============================================================================
# SENS-3 -- which lexicon roots actually matched
# ==============================================================================

def matching_roots(text, lex_list):
    """Every frozen root that prefix-matches some token of `text`.

    `src.lexicon.hit_root` answers only yes/no, and SENS-3 needs the set. This
    mirrors that function's inner loop exactly -- same `tokens()`, same
    `MIN_ROOT_LEN`, same `startswith` -- and `main()` asserts on all 4,764 dev
    rows that `bool(matching_roots(...)) == hit_root(...)`, so the mirror is
    verified against the frozen definition rather than trusted.
    """
    hits = set()
    for t in lexicon.tokens(text):
        for root in lex_list:
            if len(root) >= lexicon.MIN_ROOT_LEN and t.startswith(root):
                hits.add(root)
    return hits


# ==============================================================================
# the run
# ==============================================================================

def _cells(rows, spec):
    out = []
    for sl, gold, _want in spec:
        out.append((sl, gold, [r["p_off"] for r in rows
                               if r["slice"] == sl and r["gold"] == gold]))
    return out


def fit_all(cal_rows, r_values=R_GRID):
    """C12-3: every fitted threshold, all of them on CAL, none on EVAL."""
    fitted = {"S1b": {}, "S2": {}}
    curves = {}
    all_scores = [r["p_off"] for r in cal_rows]
    all_gold = [r["gold"] for r in cal_rows]
    curves["_all"] = cost_curve(all_scores, _gold01(all_gold))
    for sl in SLICES:
        sub = [r for r in cal_rows if r["slice"] == sl]
        curves[sl] = cost_curve([r["p_off"] for r in sub],
                                _gold01([r["gold"] for r in sub]))
        curves[sl + "_n"] = len(sub)
    curves["_all_n"] = len(cal_rows)

    for r in r_values:
        cand, fp, fn, _ = curves["_all"]
        fitted["S1b"][r] = _fit_from_curve(cand, fp, fn, curves["_all_n"], r)[0]
        fitted["S2"][r] = {}
        for sl in SLICES:
            cand, fp, fn, _ = curves[sl]
            fitted["S2"][r][sl] = _fit_from_curve(cand, fp, fn, curves[sl + "_n"], r)[0]
    return fitted, curves


def primary_block(cal_rows, eval_rows, r=R_PRIMARY, n_boot=N_BOOT, tag="primary"):
    """C12-5 / C12-6 / C12-7, plus the Addendum 1 item 3 resolution report."""
    fitted, _curves = fit_all(cal_rows, r_values=(r,))
    thr_s1b = {sl: fitted["S1b"][r] for sl in SLICES}
    thr_s2 = dict(fitted["S2"][r])

    f1b = flags_for(eval_rows, thr_s1b)
    f2 = flags_for(eval_rows, thr_s2)
    c1b = confusion(eval_rows, f1b)
    c2 = confusion(eval_rows, f2)
    n = len(eval_rows)
    cost_1b = cost(c1b["fp"], c1b["fn"], n, r)
    cost_2 = cost(c2["fp"], c2["fn"], n, r)
    dcost_rel = (cost_2 - cost_1b) / cost_1b
    d = int((f1b != f2).sum())

    spec = [(sl, g, 0) for sl, g, _ in EVAL_CELLS]
    boot = paired_bootstrap(_cells(eval_rows, spec), thr_s1b, thr_s2, r, n,
                            n_boot=n_boot)
    branch, v = verdict_branch(dcost_rel, boot["ci_low"], boot["ci_high"], d)

    half = (boot["ci_high"] - boot["ci_low"]) / 2.0
    resolution = {
        "clause": "Addendum 1 item 3 -- mandatory beside the verdict, whatever the verdict",
        "realized_d": d,
        "realized_relative_half_width": half,
        "LARGE_band": LARGE,
        "branch_5_reachable_at_this_resolution": bool(half < LARGE),
        "statement": (
            f"Realized d = {d}; realized relative half-width = {half:.4f}. "
            + (f"That half-width is >= the LARGE band ({LARGE:.2f}), so branch 5 "
               f"(SLICE-CONDITIONAL BETTER) was NOT reachable at the realized "
               f"resolution: no observed effect could have cleared it with an "
               f"interval entirely below zero."
               if half >= LARGE else
               f"That half-width is below the LARGE band ({LARGE:.2f}), so branch 5 "
               f"was reachable at the realized resolution.")),
    }

    return {
        "tag": tag, "dev_only": True, "r": r,
        "thresholds_fitted_on_CAL": {"S1b": thr_s1b["lexicon_hit"],
                                     "S2_t_hit": thr_s2["lexicon_hit"],
                                     "S2_t_free": thr_s2["lexicon_free"]},
        "n_eval": n,
        "S1b": {"cost": cost_1b, "confusion": c1b},
        "S2": {"cost": cost_2, "confusion": c2},
        "discordant_rows_d": d,
        "dcost_rel": dcost_rel,
        "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
        "bootstrap": boot,
        "verdict": v, "branch": branch,
        "resolution_C12_7_addendum1_item3": resolution,
    }


def matched_flag_count_view(cal_rows, eval_rows, fitted, curves):
    """C12-8's matched-flag-count view.

    S2's CAL flag count is matched to S1b's CAL flag count at r = 3 by searching
    r' on a fine grid; the match is made on CAL and only then is S2 scored on
    EVAL. This is a BETWEEN-SYSTEMS comparison per C12-5 -- two systems on the
    same rows -- and it is NOT a cross-slice operating-point match, which C12-5
    records as a spec defect because it leaves the base-rate confound intact.

    Tie rule, declared here rather than after seeing the grid: among the r'
    achieving the smallest absolute flag-count difference, take the one closest
    to the primary r = 3, and report the whole achieving interval.
    """
    t_s1b = fitted["S1b"][R_PRIMARY]
    target = int(sum(1 for r in cal_rows if r["p_off"] > t_s1b))

    start, stop, step = RPRIME_GRID
    grid = np.round(np.arange(start, stop + step / 2, step), 6)
    counts = np.empty(grid.size, dtype=np.int64)
    thit = np.empty(grid.size, dtype=np.float64)
    tfree = np.empty(grid.size, dtype=np.float64)
    for k, rp in enumerate(grid):
        tot = 0
        for sl in SLICES:
            cand, fp, fn, nfl = curves[sl]
            _t, j = _fit_from_curve(cand, fp, fn, curves[sl + "_n"], rp)
            tot += int(nfl[j])
            if sl == "lexicon_hit":
                thit[k] = _t
            else:
                tfree[k] = _t
        counts[k] = tot

    diff = np.abs(counts - target)
    best = diff.min()
    achieving = grid[diff == best]
    rp = float(achieving[int(np.argmin(np.abs(achieving - R_PRIMARY)))])
    k = int(np.argmin(np.abs(grid - rp)))
    thr = {"lexicon_hit": float(thit[k]), "lexicon_free": float(tfree[k])}
    desc = describe_system(eval_rows, thr, rp, "S2")

    return {
        "labelled": "BETWEEN-SYSTEMS comparison per C12-5; NOT a cross-slice "
                    "operating-point match",
        "descriptive_only": True, "no_verdict": True,
        "target_S1b_CAL_flag_count_at_r3": target,
        "S1b_threshold_at_r3": float(t_s1b),
        "r_prime": rp,
        "S2_CAL_flag_count_at_r_prime": int(counts[k]),
        "flag_count_difference": int(diff[k]),
        "exact_match": bool(diff[k] == 0),
        "r_prime_achieving_interval": [float(achieving.min()), float(achieving.max())],
        "n_grid_points_achieving": int(achieving.size),
        "grid": {"start": start, "stop": stop, "step": step, "n_points": int(grid.size)},
        "S2_thresholds_at_r_prime": thr,
        "S2_on_EVAL_at_r_prime": {
            "recall_gap_hit_minus_free": desc["recall_gap_hit_minus_free"],
            "off_precision": desc["off_precision"],
            "off_recall": desc["off_recall"],
            "per_slice": desc["per_slice"],
            "confusion": desc["confusion"],
        },
    }


def sens2_drop_ids(rows):
    """SENS-2 (C12-11): gold-OFF `lexicon_free` rows whose tokens intersect
    `{ag, am, aq, oc, oç}` -- the sub-`MIN_ROOT_LEN` roots the frozen matcher
    cannot see, so these rows sit in `lexicon_free` by a definitional leak."""
    ids = set()
    for r in rows:
        if r["slice"] == "lexicon_free" and r["gold"] == "OFF":
            if SENS2_TOKENS & set(lexicon.tokens(r["text"])):
                ids.add(r["row_id"])
    return ids


def sens3_drop_ids(rows, lex_list):
    """SENS-3 (C12-11): `lexicon_hit` rows for which EVERY matching root is in
    `{allah, ana, cim, emi, göt, mal, sie}` -- the suspect roots recorded in
    phase 02/08 as prefix-matching unrelated common words."""
    ids = set()
    for r in rows:
        if r["slice"] == "lexicon_hit":
            roots = matching_roots(r["text"], lex_list)
            if roots and roots <= SENS3_ROOTS:
                ids.add(r["row_id"])
    return ids


def sha256_of(path):
    return p11.sha256_of(path)


def git_head():
    return p11.git_head()


def _no_row_text(obj, texts):
    """Belt and braces before writing: the serialized metrics must contain no
    corpus row text and no key that could carry it."""
    blob = json.dumps(obj, ensure_ascii=False)
    hits = [t for t in texts if t.strip() and t.strip() in blob]
    bad_keys = []

    def walk(o, path="$"):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in ("text", "texts", "rows", "examples"):
                    bad_keys.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for j, v in enumerate(o):
                walk(v, f"{path}[{j}]")

    walk(obj)
    return hits, bad_keys


def main(n_boot=N_BOOT):
    t_start = time.time()
    print("=" * 96)
    print(f"PHASE 12 -- {STAGE}")
    print(f"pre-registration {PREREG}")
    print("EVERY NUMBER BELOW IS DEV-ONLY. The official test set is spent and is not read.")
    print("Naming per Addendum 1 item 1: systems S0/S1a/S1b/S2; sensitivities SENS-1/2/3.")
    print("=" * 96)

    # --- 1. provenance gate (C12-2), the Phase 11 Run A gate unchanged --------
    rows, split, gate_checks = p11.load_and_gate()
    if p11.SPLIT_SHA256 != SPLIT_SHA256:
        sys.exit("ABORT (C12-2): the split sha256 this module pins does not match "
                 "the one Phase 11 pinned.")

    cal_ids = set(split["cal_row_ids"])
    eval_ids = set(split["eval_row_ids"])
    cal_rows = [r for r in rows if r["row_id"] in cal_ids]
    eval_rows = [r for r in rows if r["row_id"] in eval_ids]

    g = p11.Gate()
    g.add("CAL rows", 2382, len(cal_rows))
    g.add("EVAL rows", 2382, len(eval_rows))
    for spec, rs, tag in ((CAL_CELLS, cal_rows, "CAL"), (EVAL_CELLS, eval_rows, "EVAL")):
        for sl, gold, want in spec:
            got = sum(1 for r in rs if r["slice"] == sl and r["gold"] == gold)
            g.add(f"{tag} {sl} x {gold}", want, got)
    g.report("[C12-2] frozen fitting and scoring denominators")
    cell_checks = g.enforce()

    # the SENS-3 mirror, verified against the frozen definition rather than trusted
    lex = lexicon.load_lexicon(config.LEXICON_PATH)
    mism = sum(1 for r in rows
               if bool(matching_roots(r["text"], lex)) != lexicon.hit_root(r["text"], lex))
    if mism:
        sys.exit(f"ABORT: matching_roots disagrees with lexicon.hit_root on {mism} rows.")
    print(f"\n[SENS-3 prerequisite] matching_roots agrees with lexicon.hit_root on "
          f"all {len(rows)} dev rows (0 disagreements)")

    # --- 2. fit every threshold on CAL (C12-3) -------------------------------
    fitted, curves = fit_all(cal_rows)

    # C12-4 correctness check, asserted not assumed
    t1 = elkan_threshold(1)
    if t1 != FROZEN_THRESHOLD:
        sys.exit(f"ABORT (C12-4): 1/(1+1) = {t1!r}, not exactly 0.5.")
    d_s0 = describe_system(eval_rows, system_thresholds("S0", 1, fitted), 1, "S0")
    d_s1a = describe_system(eval_rows, system_thresholds("S1a", 1, fitted), 1, "S1a")
    if d_s0["confusion"] != d_s1a["confusion"]:
        sys.exit(f"ABORT (C12-4): at r=1 S1a does not reproduce S0's EVAL confusion "
                 f"counts. S0={d_s0['confusion']} S1a={d_s1a['confusion']}")
    print(f"[C12-4] correctness check PASS: t*(r=1) = {t1} exactly, and S1a reproduces "
          f"S0's EVAL confusion counts {d_s0['confusion']}")

    print("\n[C12-3] thresholds fitted on CAL (applied unchanged to EVAL)")
    print(f"  {'r':>4}  {'t* (S1a)':>10}  {'S1b':>10}  {'S2 t_hit':>10}  {'S2 t_free':>10}")
    for r in R_GRID:
        print(f"  {r:>4}  {elkan_threshold(r):>10.6f}  {fitted['S1b'][r]:>10.6f}  "
              f"{fitted['S2'][r]['lexicon_hit']:>10.6f}  "
              f"{fitted['S2'][r]['lexicon_free']:>10.6f}")

    # --- 3. the primary (C12-5/6/7) ------------------------------------------
    print(f"\n[C12-5/6/7] PRIMARY at r = {R_PRIMARY}, fitted on CAL, scored on EVAL "
          f"({n_boot} paired replicates, seed {BOOT_SEED})")
    primary = primary_block(cal_rows, eval_rows, R_PRIMARY, n_boot=n_boot)
    print(f"  realized d (S1b and S2 flag differently) = {primary['discordant_rows_d']}")
    print(f"  Cost_S1b = {primary['S1b']['cost']:.6f}   "
          f"FP={primary['S1b']['confusion']['fp']} FN={primary['S1b']['confusion']['fn']}")
    print(f"  Cost_S2  = {primary['S2']['cost']:.6f}   "
          f"FP={primary['S2']['confusion']['fp']} FN={primary['S2']['confusion']['fn']}")
    print(f"  dCost_rel = {primary['dcost_rel']:+.6f}  "
          f"95% CI [{primary['ci_low']:+.6f}, {primary['ci_high']:+.6f}]")
    print(f"  VERDICT: {primary['verdict']}   (branch {primary['branch']})")
    print(f"  {primary['resolution_C12_7_addendum1_item3']['statement']}")

    # --- 4. threshold stability (C12-9) --------------------------------------
    print(f"\n[C12-9] threshold stability: refitting inside {n_boot} bootstrap "
          f"replicates OF CAL, seed {BOOT_SEED}")
    stab = cal_refit_bootstrap(_cells(cal_rows, CAL_CELLS), R_PRIMARY, n_boot=n_boot)
    for sl in SLICES:
        s = stab[sl]
        print(f"  {sl:<13} median {s['median']:.6f}  IQR {s['iqr']:.6f} "
              f"[{s['q25']:.6f}, {s['q75']:.6f}]  p5/p95 {s['p5']:.6f}/{s['p95']:.6f}")
    unstable = stab["_unstable_rule"]["S2_arm_unstable"]
    print(f"  IQR(t_hit) = {stab['lexicon_hit']['iqr']:.6f} vs limit "
          f"{IQR_T_HIT_LIMIT}: S2 arm is "
          f"{'UNSTABLE' if unstable else 'not flagged unstable'}")
    primary["S2_arm_unstable_C12_9"] = unstable

    # --- 5. descriptive frontier (C12-8) = SENS-1 ----------------------------
    print("\n[C12-8] EVAL descriptive frontier, all four systems, every r "
          "(SENS-1 is the four non-primary r values)")
    frontier = {}
    for r in R_GRID:
        frontier[r] = {}
        for name in ("S0", "S1a", "S1b", "S2"):
            frontier[r][name] = describe_system(
                eval_rows, system_thresholds(name, r, fitted), r, name)
    hdr = (f"  {'r':>3} {'sys':>4} {'cost':>9} {'FP':>5} {'FN':>5} {'flags':>6} "
           f"{'recall':>7} {'prec':>7} {'rec_hit':>8} {'rec_free':>9} {'gap':>8}")
    print(hdr)
    for r in R_GRID:
        for name in ("S0", "S1a", "S1b", "S2"):
            b = frontier[r][name]
            ph = b["per_slice"]["lexicon_hit"]["off_recall"]
            pf = b["per_slice"]["lexicon_free"]["off_recall"]
            print(f"  {r:>3} {name:>4} {b['cost']:>9.6f} {b['confusion']['fp']:>5} "
                  f"{b['confusion']['fn']:>5} {b['confusion']['n_flagged']:>6} "
                  f"{b['off_recall']:>7.4f} {b['off_precision']:>7.4f} "
                  f"{ph:>8.4f} {pf:>9.4f} {b['recall_gap_hit_minus_free']:>+8.4f}")
        print()

    print("  S1a vs S1b (the C12-3 zero-parameter internal control):")
    for r in R_GRID:
        a, b = frontier[r]["S1a"], frontier[r]["S1b"]
        print(f"    r={r:>2}  t* = {a['thresholds']['lexicon_hit']:.6f} vs fitted "
              f"{b['thresholds']['lexicon_hit']:.6f}   cost {a['cost']:.6f} vs "
              f"{b['cost']:.6f}   (delta {b['cost'] - a['cost']:+.6f})")

    matched = matched_flag_count_view(cal_rows, eval_rows, fitted, curves)
    print(f"\n[C12-8] matched-flag-count view ({matched['labelled']})")
    print(f"  S1b CAL flag count at r=3: {matched['target_S1b_CAL_flag_count_at_r3']}   "
          f"S2 CAL flag count at r'={matched['r_prime']:.3f}: "
          f"{matched['S2_CAL_flag_count_at_r_prime']}   "
          f"(difference {matched['flag_count_difference']}, "
          f"{'exact' if matched['exact_match'] else 'nearest on the grid'})")
    print(f"  r' achieving interval: [{matched['r_prime_achieving_interval'][0]:.3f}, "
          f"{matched['r_prime_achieving_interval'][1]:.3f}] "
          f"({matched['n_grid_points_achieving']} grid points)")
    e = matched["S2_on_EVAL_at_r_prime"]
    print(f"  S2 on EVAL at r': recall gap (hit-free) "
          f"{e['recall_gap_hit_minus_free']:+.4f}, OFF-precision {e['off_precision']:.4f}, "
          f"OFF-recall {e['off_recall']:.4f}")

    # --- 6. SENS-2 and SENS-3 ------------------------------------------------
    print("\n[C12-11] sensitivities (may qualify a verdict, may not overturn it)")
    sens = {}

    drop2 = sens2_drop_ids(rows)
    keep2 = [r for r in rows if r["row_id"] not in drop2]
    s2_cal = [r for r in keep2 if r["row_id"] in cal_ids]
    s2_eval = [r for r in keep2 if r["row_id"] in eval_ids]
    print(f"  SENS-2 (MIN_ROOT_LEN leak, tokens {sorted(SENS2_TOKENS)}): dropped "
          f"{len(drop2)} of {len(rows)} full-dev rows "
          f"(pre-registration says {SENS2_EXPECTED_FULL_DEV}), "
          f"{2382 - len(s2_cal)} from CAL, {2382 - len(s2_eval)} from EVAL")
    p_s2 = primary_block(s2_cal, s2_eval, R_PRIMARY, n_boot=n_boot, tag="SENS-2")
    sens["SENS-2"] = {"definition": "drop from lexicon_free the gold-OFF rows whose "
                                    "tokens intersect {ag, am, aq, oc, oç}",
                      "tokens": sorted(SENS2_TOKENS),
                      "n_dropped_full_dev": len(drop2),
                      "n_dropped_expected_full_dev": SENS2_EXPECTED_FULL_DEV,
                      "matches_preregistered_count": len(drop2) == SENS2_EXPECTED_FULL_DEV,
                      "n_dropped_cal": 2382 - len(s2_cal),
                      "n_dropped_eval": 2382 - len(s2_eval),
                      "primary": p_s2}
    print(f"    dCost_rel = {p_s2['dcost_rel']:+.6f} "
          f"[{p_s2['ci_low']:+.6f}, {p_s2['ci_high']:+.6f}]  d = "
          f"{p_s2['discordant_rows_d']}  -> {p_s2['verdict']} (branch {p_s2['branch']})")

    drop3 = sens3_drop_ids(rows, lex)
    keep3 = [r for r in rows if r["row_id"] not in drop3]
    s3_cal = [r for r in keep3 if r["row_id"] in cal_ids]
    s3_eval = [r for r in keep3 if r["row_id"] in eval_ids]
    print(f"  SENS-3 (suspect roots {sorted(SENS3_ROOTS)}): dropped {len(drop3)} of "
          f"{len(rows)} full-dev rows, {2382 - len(s3_cal)} from CAL, "
          f"{2382 - len(s3_eval)} from EVAL")
    p_s3 = primary_block(s3_cal, s3_eval, R_PRIMARY, n_boot=n_boot, tag="SENS-3")
    sens["SENS-3"] = {"definition": "drop from lexicon_hit every row for which EVERY "
                                    "matching root is in {allah, ana, cim, emi, göt, "
                                    "mal, sie}",
                      "roots": sorted(SENS3_ROOTS),
                      "n_dropped_full_dev": len(drop3),
                      "n_dropped_cal": 2382 - len(s3_cal),
                      "n_dropped_eval": 2382 - len(s3_eval),
                      "primary": p_s3}
    print(f"    dCost_rel = {p_s3['dcost_rel']:+.6f} "
          f"[{p_s3['ci_low']:+.6f}, {p_s3['ci_high']:+.6f}]  d = "
          f"{p_s3['discordant_rows_d']}  -> {p_s3['verdict']} (branch {p_s3['branch']})")

    sens["SENS-1"] = {"definition": "the four non-primary r values",
                      "r_values": [r for r in R_GRID if r != R_PRIMARY],
                      "where": "reported in full under descriptive.frontier",
                      "rule": "may qualify the verdict; may not overturn it (C9-10)"}

    # --- 7. C12-10, checked against its own recorded prediction ---------------
    predicted = primary["branch"] in (2, 3)
    print(f"\n[C12-10] recorded prediction: dCost_rel falls inside SMALL, branch 2 or 3, "
          f"SINGLE-THRESHOLD-SUFFICIENT")
    print(f"          observed: branch {primary['branch']}, {primary['verdict']} "
          f"-> prediction {'HELD' if predicted else 'FAILED'}")

    # --- 8. output ------------------------------------------------------------
    metrics = {
        "run_id": RUN_ID,
        "stage": STAGE,
        "dev_only": True,
        "dev_only_note": "Every number in this file is measured on the dev split "
                         "(fingerprint 034415af3a23b388), thresholds fitted on CAL and "
                         "scored on EVAL. The official test set is spent and was not "
                         "read; load_coltekin_test is never called. C12-14: no figure "
                         "here may carry a generalisation claim.",
        "preregistration": {
            "file": "phases/12_threshold_policy.md",
            "commit": "ec2fd3a7af6ac2f4b241ef282451690ba1ee6030",
            "addendum_1": "584292c", "addendum_2": "2b4391bf",
            "clauses": "C12-1..C12-15",
            "naming": "Addendum 1 item 1: systems S0/S1a/S1b/S2; sensitivities "
                      "SENS-1 (cost frontier), SENS-2 (MIN_ROOT_LEN leak), "
                      "SENS-3 (suspect-root contamination). S1/S2 never denote a "
                      "sensitivity here.",
        },
        "not_run_in_this_stage": [
            "no retraining, no forward pass, no GPU (C12-15)",
            "no new corpus, no new labels; lexicon and MIN_ROOT_LEN frozen",
            "no test-set measurement of any kind",
            "no per-slice macro-F1 and no per-slice accuracy (C12-2, phase-01 constraint)",
            "no cross-slice operating-point match (C12-5 spec defect)",
            "no findings.md and no RESULTS_LOG row -- the controller drafts both",
        ],
        "provenance": {"gate": gate_checks, "cells": cell_checks,
                       "split_sha256": SPLIT_SHA256,
                       "matching_roots_vs_hit_root_disagreements": mism},
        "definitions": {
            "cost": "Cost(r) = (FP + r*FN)/N, c_FP=1, c_FN=r  (C12-4)",
            "decision_rule": "flag iff score > t  (frozen convention, C12-3)",
            "elkan": "t* = 1/(1+r), base-rate independent  (C12-1)",
            "dcost_rel": "[Cost_S2(EVAL,r=3) - Cost_S1b(EVAL,r=3)] / Cost_S1b(EVAL,r=3); "
                         "negative means slice-conditional is better  (C12-5)",
            "d": "count of EVAL rows where S1b and S2 flag differently  (C12-7)",
            "candidate_set": "the distinct observed scores among the CAL rows being "
                             "fitted, plus nextafter(min, -inf) so `flag everything` is "
                             "reachable; ties broken toward the LOWER t  (C12-3)",
            "verdict_bands": {"d_floor": D_FLOOR, "SMALL": SMALL, "LARGE": LARGE},
        },
        "systems": {
            "S0": "frozen historical, 0.5 everywhere, 0 fitted params, lexicon not "
                  "consulted at inference",
            "S1a": "analytic Elkan, t* = 1/(1+r) everywhere, 0 fitted params, lexicon "
                   "not consulted at inference",
            "S1b": "fitted single threshold, 1 fitted param, lexicon not consulted at "
                   "inference -- THE PRIMARY COMPARATOR",
            "S2": "slice-conditional, t_hit and t_free, 2 fitted params, lexicon IS "
                  "consulted at inference",
        },
        "fitted_thresholds_CAL": {
            str(r): {"S1a_analytic": elkan_threshold(r),
                     "S1b": fitted["S1b"][r],
                     "S2_t_hit": fitted["S2"][r]["lexicon_hit"],
                     "S2_t_free": fitted["S2"][r]["lexicon_free"]}
            for r in R_GRID},
        "correctness_check_C12_4": {
            "elkan_at_r1_is_exactly_half": t1 == FROZEN_THRESHOLD,
            "S1a_reproduces_S0_eval_confusion": d_s0["confusion"] == d_s1a["confusion"],
            "confusion": d_s0["confusion"],
        },
        "primary": primary,
        "threshold_stability_C12_9": stab,
        "descriptive": {
            "clause": "C12-8, reported regardless of verdict",
            "frontier": {str(r): frontier[r] for r in R_GRID},
            "matched_flag_count_view": matched,
        },
        "sensitivities_C12_11": sens,
        "prediction_C12_10": {
            "recorded": "dCost_rel falls inside SMALL -- branch 2 or 3, "
                        "SINGLE-THRESHOLD-SUFFICIENT",
            "observed_branch": primary["branch"],
            "observed_verdict": primary["verdict"],
            "held": predicted,
        },
        "ceilings_C12_14": [
            "The official test set is spent. Any threshold selected here can never "
            "receive an independent held-out number.",
            "A Phase 12 threshold may be wired into the offline demo; it may not carry "
            "any generalisation claim.",
            "Phase 05's dev->test transfer is about the phase-04 thresholds and is "
            "background, not validation of these.",
            "One seed, one checkpoint (best.pt = epoch 1), same-corpus, dev-only, with "
            "both known slice-definition defects unrepaired.",
            "C12-13: this phase derives an operating point. That prohibition is lifted "
            "here and only here, and remains in force for every earlier phase.",
        ],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "git_head_at_run": git_head(),
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_boot": n_boot, "seed": BOOT_SEED, "alpha": ALPHA,
            "elapsed_seconds": round(time.time() - t_start, 1),
        },
    }

    hits, bad_keys = _no_row_text(metrics, [r["text"] for r in rows])
    print(f"\n[output] no-corpus-row-text check: {len(hits)} of {len(rows)} dev texts "
          f"found as substrings, {len(bad_keys)} text-carrying keys")
    if hits or bad_keys:
        sys.exit(f"ABORT: metrics.json would carry corpus row text "
                 f"({len(hits)} texts, keys {bad_keys[:5]}).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[output] wrote {out} ({out.stat().st_size} bytes, sha256 "
          f"{sha256_of(out)[:16]}...)")
    print(f"[output] NOT written, by instruction: findings.md, RESULTS_LOG row. "
          f"Nothing committed.")
    print("=" * 96)
    return metrics


if __name__ == "__main__":
    main()
