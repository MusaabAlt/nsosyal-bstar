#!/usr/bin/env python3
"""Phase 11 -- per-slice calibration and prior correction. RUN A.

Pre-registration: `phases/11_prior_correction.md`, C11-1..C11-14, committed at
d589dbad BEFORE any number in this file existed. The pre-registration is
authoritative; this module implements it and does not extend it.

Run A covers the primary endpoint (C11-4), the control (C11-9), the interval
estimation (C11-5), the verdict (C11-7) and the always-reported descriptive
calibration (C11-8). **The C11-10 treatments -- Saerens EM, per-slice Platt,
per-slice isotonic -- are NOT run here.** They are Run B.

Every number this module produces is **dev-only** and is labelled dev-only in
both the stdout report and `metrics.json`. Read-only: no training, no forward
pass, no model loaded, the lexicon and MIN_ROOT_LEN frozen, and
`load_coltekin_test` is never called -- the official test set is spent and stays
spent.

C11-3, stated once here because the confusion it guards against is the easiest
mistake in this file: `signed_gap_p_off` / `ece_p_off` bin on **P(OFF)** over 10
equal-width bins on [0, 1]. `src.calibration.ece` computes a *different*
quantity -- it bins on decision confidence `max(p, 1-p)` over both classes and
is what phase 04 reported. The two may not be compared, summed, or quoted in the
same sentence without naming both definitions. `src.calibration` is imported
here only for `saturated_count`, never for its ECE.

Usage:
    python -m src.phase11_prior_correction
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

import config                                      # noqa: E402
from src import calibration as cal                 # noqa: E402
from src import data_io, lexicon                   # noqa: E402

RUN_ID = "11_prior_correction"
STAGE = "Run A -- primary, control, descriptive calibration"

# --- C11-1: provenance, byte-verified ----------------------------------------
PRED_PATH = ROOT / "results/01_baseline_berturk/dev_predictions.csv"
PRED_SHA256 = "a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346"
PRED_BYTES = 736591
LEXICON_SHA256 = "0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b"
LEXICON_BYTES = 5988
DEV_FINGERPRINT = "034415af3a23b388"

# The eight recorded phase-01 figures in C11-1. A mismatch on any one of them
# aborts the stage -- provenance by content, not by filename.
RECORDED = {
    "dev_rows":            4764,
    "dev_gold_off":         920,
    "lexicon_hit_rows":     614,
    "lexicon_hit_gold_off": 355,
    "lexicon_free_rows":   4150,
    "lexicon_free_gold_off": 565,
    "overall_off_recall":  (635, 920),
    "lexicon_hit_recall":  (317, 355),
    "lexicon_free_recall": (318, 565),
    "false_negatives":      285,
    "false_positives":      213,
}

# --- C11-2: the frozen split --------------------------------------------------
SPLIT_PATH = ROOT / "results/04_calibration/cal_eval_split.json"
SPLIT_SHA256 = "6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899"

# C11-2 frozen denominators / C11-5 bootstrap strata, in the order C11-5 lists
# them: 182 / 127 / 278 / 1,795.
EVAL_CELLS = [("lexicon_hit", "OFF", 182), ("lexicon_hit", "NOT", 127),
              ("lexicon_free", "OFF", 278), ("lexicon_free", "NOT", 1795)]
EVAL_SLICE_ROWS = {"lexicon_hit": 309, "lexicon_free": 2073}

# --- C11-3 / C11-4 ------------------------------------------------------------
N_BINS = 10                 # primary; 15 and 20 are the C11-11 S1 sensitivity
FROZEN_THRESHOLD = 0.5      # the frozen decision rule, and the band edge
SLICES = ("lexicon_free", "lexicon_hit")

# --- C11-5 --------------------------------------------------------------------
N_BOOT = 10000
BOOT_SEED = 42
ALPHA = 0.05

# --- C11-6 / C11-7: fixed in the pre-registration, never from the data --------
N_BAND_FLOOR = 400
SMALL = 0.02
LARGE = 0.05
DESIGN = {"SG_free_low": {"n": 1831, "pi": 0.067, "se": 0.0059, "half_width": 0.0115},
          "SG_hit_low":  {"n": 126,  "pi": 0.151, "se": 0.0319, "half_width": 0.0625},
          "SG_free":     {"n": 2073, "pi": 0.134, "se": 0.0075, "half_width": 0.0148},
          "SG_hit":      {"n": 309,  "pi": 0.589, "se": 0.0280, "half_width": 0.0549}}


# ==============================================================================
# C11-3: the statistics. Binned on P(OFF), NOT on decision confidence.
# ==============================================================================

def _check(y_true, p_off):
    if len(y_true) != len(p_off):
        raise ValueError(f"length mismatch: {len(y_true)} labels vs {len(p_off)} probabilities")
    if len(p_off) == 0:
        raise ValueError("SignedGap/ECE are undefined on zero rows")
    bad = set(y_true) - {"OFF", "NOT"}
    if bad:
        raise ValueError(f"labels outside ('OFF', 'NOT'): {sorted(bad)}")


def _bin_of(p, n_bins):
    """Equal-width bins on [0, 1]. `p == 1.0` lands one past the last bin and is
    clamped into it -- dropping it would break the C11-4 identity silently.

    Uses `int(p / width)` rather than `int(p * n_bins)` to mirror
    `src.calibration.reliability_bins`, so the two tables bin the same way even
    though they bin different quantities."""
    width = 1.0 / n_bins
    idx = int(p / width)
    return min(max(idx, 0), n_bins - 1)


def reliability_table(y_true, p_off, n_bins=N_BINS):
    """The per-bin record behind ECE and SignedGap; the table IS the diagram.

    Empty bins are returned with `n = 0` rather than dropped, so the table always
    has `n_bins` rows and two slices are comparable line by line (C11-8 requires
    the full table). `off_rate` is the empirical share of gold-OFF rows in the
    bin; `mean_p` is the mean P(OFF) in the bin.

    NOTE the argument order `(y_true, p_off, n_bins)`: it matches
    `src.calibration.ece` / `reliability_bins` and the committed tests.
    """
    _check(y_true, p_off)
    width = 1.0 / n_bins
    bins = [{"bin": i, "lo": i * width, "hi": (i + 1) * width,
             "n": 0, "p_sum": 0.0, "off": 0} for i in range(n_bins)]
    for g, p in zip(y_true, p_off):
        b = bins[_bin_of(p, n_bins)]
        b["n"] += 1
        b["p_sum"] += p
        b["off"] += 1 if g == "OFF" else 0
    for b in bins:
        n = b["n"]
        b["mean_p"] = (b["p_sum"] / n) if n else None
        b["off_rate"] = (b["off"] / n) if n else None
        b["gap"] = (b["off_rate"] - b["mean_p"]) if n else None
        b["weight"] = n / len(p_off)
        del b["p_sum"]
    return bins


def signed_gap_p_off(y_true, p_off, n_bins=N_BINS):
    """C11-3: SignedGap = sum_b (n_b / N) * (off_rate_b - mean_p_b).

    Positive means the model **under**-states P(OFF) -- under-confidence in the
    OFF direction. Negative means it over-states it. Empty bins contribute 0.

    Computed through the bins, not through the C11-4 closed form, so that the
    identity check in `identity_check` is a real check rather than a tautology.
    """
    return sum(b["weight"] * b["gap"]
               for b in reliability_table(y_true, p_off, n_bins) if b["n"])


def ece_p_off(y_true, p_off, n_bins=N_BINS):
    """C11-3: ECE = sum_b (n_b / N) * | off_rate_b - mean_p_b |.

    The shape-sensitive companion to SignedGap (C11-4: a slice can be badly
    miscalibrated in shape and still return SignedGap ~ 0). Neither replaces the
    other, and C11-8 requires both in every table.
    """
    return sum(b["weight"] * abs(b["gap"])
               for b in reliability_table(y_true, p_off, n_bins) if b["n"])


def closed_form_gap(y_true, p_off):
    """C11-4: `(mean gold) - (mean p)`, the value SignedGap telescopes to."""
    n = len(p_off)
    return sum(1.0 for g in y_true if g == "OFF") / n - sum(p_off) / n


def identity_check(y_true, p_off, bin_counts=(10, 15, 20), tol=1e-12):
    """C11-4's derivation, verified on the real rows rather than asserted.

    The derivation is the reason the whole-slice figure is disqualified as the
    primary endpoint, so it is checked wherever the whole-slice figure is
    printed.
    """
    closed = closed_form_gap(y_true, p_off)
    out = {"closed_form": closed, "tolerance": tol, "by_bins": {}, "holds": True}
    for nb in bin_counts:
        binned = signed_gap_p_off(y_true, p_off, nb)
        ok = abs(binned - closed) < tol
        out["by_bins"][str(nb)] = {"binned": binned, "abs_diff": abs(binned - closed),
                                   "holds": ok}
        out["holds"] = out["holds"] and ok
    return out


# ==============================================================================
# C11-7: the verdict. Ordered, branch 0 first, mutually exclusive, exhaustive.
# ==============================================================================

def verdict(sg, ci_low, ci_high, n_band):
    """C11-7. Branch order is part of the rule, not an implementation detail.

    Branch 0 exists because the band size is data-dependent; it is evaluated
    first so an under-powered band cannot be reported as a finding however large
    `sg` is. Branch 2 precedes the magnitude branches so an interval straddling
    zero cannot be reported as a direction.
    """
    return verdict_branch(sg, ci_low, ci_high, n_band)[1]


def verdict_branch(sg, ci_low, ci_high, n_band):
    """The same rule, returning `(branch_number, verdict)` for the report."""
    if n_band < N_BAND_FLOOR:
        return 0, "INSUFFICIENT"
    if ci_high < 0:
        return 1, "OVER-SCORED"
    if ci_low <= 0 <= ci_high:
        return 2, "BASE-RATE-CORRECT"
    if sg < SMALL:
        return 3, "BASE-RATE-CORRECT"
    if sg < LARGE:
        return 4, "INTERMEDIATE"
    return 5, "UNDER-CONFIDENT"


# ==============================================================================
# C11-5: stratified nonparametric bootstrap
# ==============================================================================

def _binned_np(gold01, p, n_bins):
    """Vectorised reliability bins for one replicate. Same binning as `_bin_of`."""
    idx = np.clip((p / (1.0 / n_bins)).astype(np.int64), 0, n_bins - 1)
    cnt = np.bincount(idx, minlength=n_bins).astype(np.float64)
    sp = np.bincount(idx, weights=p, minlength=n_bins)
    sg = np.bincount(idx, weights=gold01, minlength=n_bins)
    nz = cnt > 0
    gap = np.zeros(n_bins)
    gap[nz] = sg[nz] / cnt[nz] - sp[nz] / cnt[nz]
    w = cnt / cnt.sum()
    return float((w * gap).sum()), float((w * np.abs(gap)).sum())


def bootstrap(cells, n_boot=N_BOOT, seed=BOOT_SEED, alpha=ALPHA, n_bins=N_BINS):
    """C11-5: resample each of the four (slice x gold) EVAL cells with
    replacement to its own original size, so the frozen denominators
    182/127/278/1795 are preserved in every replicate.

    Band membership (`p_OFF < 0.5`) is recomputed INSIDE each replicate, so the
    interval carries the variance of which rows fall in the band rather than
    pretending the band was fixed in advance. That is also why `n_band` varies
    across replicates and is reported.

    Cells are drawn in the order C11-5 lists them (hit-OFF, hit-NOT, free-OFF,
    free-NOT); the draw order is part of what `seed=42` reproduces.
    """
    rng = np.random.default_rng(seed)
    keys = [(s, g) for s, g, _ in EVAL_CELLS]
    stats = {k: [] for k in ("SG_free_low", "SG_hit_low", "SG_free", "SG_hit",
                             "ECE_free", "ECE_hit", "ECE_gap_hit_minus_free",
                             "n_free_low", "n_hit_low")}
    empty = {"SG_free_low": 0, "SG_hit_low": 0}

    for _ in range(n_boot):
        drawn = {}
        for k in keys:
            p, g01 = cells[k]
            i = rng.integers(0, len(p), len(p))
            drawn[k] = (p[i], g01[i])
        for slug, sl in (("free", "lexicon_free"), ("hit", "lexicon_hit")):
            p = np.concatenate([drawn[(sl, "OFF")][0], drawn[(sl, "NOT")][0]])
            g = np.concatenate([drawn[(sl, "OFF")][1], drawn[(sl, "NOT")][1]])
            sg_whole, ece_whole = _binned_np(g, p, n_bins)
            stats[f"SG_{slug}"].append(sg_whole)
            stats[f"ECE_{slug}"].append(ece_whole)
            m = p < FROZEN_THRESHOLD
            stats[f"n_{slug}_low"].append(int(m.sum()))
            if m.any():
                stats[f"SG_{slug}_low"].append(_binned_np(g[m], p[m], n_bins)[0])
            else:
                empty[f"SG_{slug}_low"] += 1
        stats["ECE_gap_hit_minus_free"].append(stats["ECE_hit"][-1] - stats["ECE_free"][-1])

    out = {}
    for k, vals in stats.items():
        a = np.asarray(vals, dtype=np.float64)
        out[k] = {"ci_low": float(np.percentile(a, 100 * alpha / 2)),
                  "ci_high": float(np.percentile(a, 100 * (1 - alpha / 2))),
                  "boot_mean": float(a.mean()),
                  "n_boot": n_boot, "n_boot_used": int(a.size),
                  "n_boot_undefined": empty.get(k, 0),
                  "alpha": alpha, "seed": seed}
        if k.startswith("n_"):
            out[k].update({"boot_min": int(a.min()), "boot_max": int(a.max())})
    return out


# ==============================================================================
# C11-1: the provenance gate. A mismatch on any check aborts the stage.
# ==============================================================================

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Gate:
    """Collects expected-vs-observed checks and aborts if any one fails."""

    def __init__(self):
        self.checks = []

    def add(self, name, expected, observed, note=None):
        ok = expected == observed
        rec = {"check": name, "expected": expected, "observed": observed, "pass": ok}
        if note:
            rec["note"] = note
        self.checks.append(rec)
        return ok

    def report(self, title):
        print(f"\n{title}")
        for c in self.checks:
            e, o = c["expected"], c["observed"]
            es = e if not isinstance(e, str) or len(e) <= 24 else e[:16] + "..."
            os_ = o if not isinstance(o, str) or len(o) <= 24 else o[:16] + "..."
            print(f"  [{'PASS' if c['pass'] else 'FAIL':4}] {c['check']:<44} "
                  f"expected {str(es):>22}   observed {str(os_):>22}")

    def enforce(self):
        bad = [c for c in self.checks if not c["pass"]]
        if bad:
            for c in bad:
                print(f"  MISMATCH {c['check']}: expected {c['expected']!r}, "
                      f"observed {c['observed']!r}", file=sys.stderr)
            sys.exit("ABORT (C11-1): the dump does not reproduce the recorded phase-01 "
                     "figures. Every number in phases 01-09 was measured on those rows; "
                     "a different dump makes this analysis incomparable to all of them.")
        return self.checks


def load_and_gate(check_lexicon_recompute=True):
    """C11-1 + C11-2. Returns (rows, split, gate_checks)."""
    g = Gate()

    # --- files, by content --------------------------------------------------
    for path, sha, nbytes, tag in ((PRED_PATH, PRED_SHA256, PRED_BYTES, "dev_predictions.csv"),
                                   (config.LEXICON_PATH, LEXICON_SHA256, LEXICON_BYTES,
                                    "karaliste.txt")):
        if not Path(path).exists():
            sys.exit(f"ABORT (C11-1): missing {path}")
        g.add(f"{tag} sha256", sha, sha256_of(path))
        g.add(f"{tag} bytes", nbytes, Path(path).stat().st_size)

    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    g.add("cal_eval_split.json sha256", SPLIT_SHA256, sha256_of(SPLIT_PATH))
    g.add("split-recorded dev_predictions sha256",
          sha256_of(PRED_PATH), split["provenance"]["dev_predictions_sha256"],
          note="the split file must name the dump that is actually on disk")

    rows = list(csv.DictReader(open(PRED_PATH, encoding="utf-8")))
    for r in rows:
        r["p_off"] = float(r["confidence"])

    # --- the frozen dev split -----------------------------------------------
    fp = data_io.dev_fingerprint([{"id": r["row_id"]} for r in rows])
    g.add("dev fingerprint", DEV_FINGERPRINT, fp[:16])
    g.add("split seed", 42, split["seed"])
    g.add("split n_cal", 2382, split["n_cal"])
    g.add("split n_eval", 2382, split["n_eval"])
    g.add("split dev fingerprint", DEV_FINGERPRINT, split["dev_fingerprint"][:16])

    # --- the frozen decision rule, asserted rather than assumed (C11-1) -----
    viol = sum(1 for r in rows if (r["p_off"] > FROZEN_THRESHOLD) != (r["pred"] == "OFF"))
    g.add("rows violating `pred == OFF iff confidence > 0.5`", 0, viol)
    g.add("rows with confidence == 0.5 exactly", 0, sum(1 for r in rows
                                                        if r["p_off"] == FROZEN_THRESHOLD),
          note="reported, not assumed away: at 0.5 exactly the rule `> 0.5` and phase-04's "
               "`>= 0.5` would disagree, and such a row would be excluded from the C11-4 "
               "band by the literal `p_OFF < 0.5` definition")

    # --- the eight recorded phase-01 figures --------------------------------
    hit = [r for r in rows if r["slice"] == "lexicon_hit"]
    free = [r for r in rows if r["slice"] == "lexicon_free"]
    off = [r for r in rows if r["gold"] == "OFF"]

    def rec(rs):
        o = [r for r in rs if r["gold"] == "OFF"]
        return sum(1 for r in o if r["pred"] == "OFF"), len(o)

    g.add("dev rows", RECORDED["dev_rows"], len(rows))
    g.add("dev gold OFF", RECORDED["dev_gold_off"], len(off))
    g.add("lexicon_hit rows", RECORDED["lexicon_hit_rows"], len(hit))
    g.add("lexicon_hit gold OFF", RECORDED["lexicon_hit_gold_off"],
          sum(1 for r in hit if r["gold"] == "OFF"))
    g.add("lexicon_free rows", RECORDED["lexicon_free_rows"], len(free))
    g.add("lexicon_free gold OFF", RECORDED["lexicon_free_gold_off"],
          sum(1 for r in free if r["gold"] == "OFF"))
    g.add("overall OFF-recall (tp, support)", RECORDED["overall_off_recall"], rec(rows))
    g.add("lexicon_hit OFF-recall (tp, support)", RECORDED["lexicon_hit_recall"], rec(hit))
    g.add("lexicon_free OFF-recall (tp, support)", RECORDED["lexicon_free_recall"], rec(free))
    g.add("false negatives", RECORDED["false_negatives"],
          sum(1 for r in rows if r["gold"] == "OFF" and r["pred"] == "NOT"))
    g.add("false positives", RECORDED["false_positives"],
          sum(1 for r in rows if r["gold"] == "NOT" and r["pred"] == "OFF"))

    # --- the slice definition itself, recomputed from the frozen lexicon ----
    # C11-1: import `src.lexicon.hit_root`, never reimplement it. The dumped
    # `slice` column is phase-01's; this proves it is still what the frozen
    # lexicon and MIN_ROOT_LEN produce, rather than trusting a column header.
    if check_lexicon_recompute:
        t0 = time.time()
        lex = lexicon.load_lexicon(config.LEXICON_PATH)
        redisagree = sum(1 for r in rows
                         if ("lexicon_hit" if lexicon.hit_root(r["text"], lex)
                             else "lexicon_free") != r["slice"])
        g.add("rows where hit_root disagrees with the dumped `slice`", 0, redisagree,
              note=f"MIN_ROOT_LEN={lexicon.MIN_ROOT_LEN}, {len(lex)} frozen roots, "
                   f"recomputed in {time.time() - t0:.1f}s")

    g.report("[C11-1/C11-2] provenance gate  (dev-only; the official test set is not read)")
    return rows, split, g.enforce()


# ==============================================================================
# the run
# ==============================================================================

def build_eval(rows, split):
    """EVAL rows only, from the frozen split, keyed into the four C11-5 cells."""
    ids = set(split["eval_row_ids"])
    ev = [r for r in rows if r["row_id"] in ids]
    if len(ev) != len(split["eval_row_ids"]):
        sys.exit(f"ABORT (C11-2): {len(split['eval_row_ids'])} frozen EVAL ids but "
                 f"{len(ev)} matched rows. The split file and the dump disagree.")
    cells = {}
    for sl, gold, _ in EVAL_CELLS:
        sub = [r for r in ev if r["slice"] == sl and r["gold"] == gold]
        cells[(sl, gold)] = (np.array([r["p_off"] for r in sub], dtype=np.float64),
                             np.array([1.0 if gold == "OFF" else 0.0] * len(sub)))
    return ev, cells


def slice_rows(ev, sl):
    return [r for r in ev if r["slice"] == sl]


def describe(rs, tag):
    """C11-8: everything reported per slice regardless of verdict. No per-slice
    macro-F1 and no per-slice accuracy -- the phase-01 constraint holds (base
    rates 57.8% vs 13.6%). Raw confusion counts are retained."""
    gold = [r["gold"] for r in rs]
    p = [r["p_off"] for r in rs]
    tp = sum(1 for r in rs if r["gold"] == "OFF" and r["pred"] == "OFF")
    fn = sum(1 for r in rs if r["gold"] == "OFF" and r["pred"] == "NOT")
    fp = sum(1 for r in rs if r["gold"] == "NOT" and r["pred"] == "OFF")
    tn = sum(1 for r in rs if r["gold"] == "NOT" and r["pred"] == "NOT")
    return {
        "slice": tag, "dev_only": True, "n": len(rs),
        "gold_off": tp + fn, "gold_not": tn + fp,
        "base_rate_off": (tp + fn) / len(rs),
        "mean_p_off": sum(p) / len(rs),
        "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "confusion_note": "raw counts only; per-slice macro-F1 and per-slice accuracy are "
                          "NOT reported (phase-01 pre-registered constraint, base rates "
                          "57.8% vs 13.6%)",
        "ece_10": ece_p_off(gold, p, 10),
        "signed_gap_10": signed_gap_p_off(gold, p, 10),
        "saturated_rows_6dp": cal.saturated_count(p),
        "reliability_10": reliability_table(gold, p, 10),
        "identity_check": identity_check(gold, p),
        "whole_slice_caveat":
            "C11-4: SignedGap telescopes to (slice OFF rate - slice mean p_OFF), and with "
            "lexicon_free at 87.1% of dev and global calibration good, "
            "0.871*SG_free + 0.129*SG_hit ~ SG_global ~ 0, so SG_free is pinned near zero "
            "by arithmetic almost regardless of what the model does. This figure is a "
            "SECONDARY. Its smallness is not a finding.",
        "sensitivity_S1_bin_count": {
            str(nb): {"ece": ece_p_off(gold, p, nb), "signed_gap": signed_gap_p_off(gold, p, nb)}
            for nb in (10, 15, 20)},
    }


def band_block(rs, tag, design_key, boot_key, boot):
    """The C11-4 band statistic for one slice, with its realized n beside it."""
    band = [r for r in rs if r["p_off"] < FROZEN_THRESHOLD]
    at_edge = [r for r in rs if r["p_off"] == FROZEN_THRESHOLD]
    gold = [r["gold"] for r in band]
    p = [r["p_off"] for r in band]
    sg = signed_gap_p_off(gold, p, N_BINS)
    b = boot[boot_key]
    br, vd = verdict_branch(sg, b["ci_low"], b["ci_high"], len(band))
    return {
        "statistic": boot_key, "slice": tag, "dev_only": True,
        "band": "p_OFF < 0.5, strictly (the frozen decision rule; C11-4)",
        "n_band_realized": len(band),
        "n_band_design": DESIGN[design_key]["n"],
        "n_slice": len(rs),
        "rows_at_p_off_exactly_0.5": len(at_edge),
        "rows_at_p_off_exactly_0.5_note":
            "excluded from the band by the literal C11-4 definition `p_OFF < 0.5`. The "
            "exclusion is reported, not decided.",
        "gold_off_in_band": sum(1 for g in gold if g == "OFF"),
        "off_rate_in_band": sum(1.0 for g in gold if g == "OFF") / len(band),
        "mean_p_in_band": sum(p) / len(band),
        "signed_gap": sg,
        "ece": ece_p_off(gold, p, N_BINS),
        "ci_low": b["ci_low"], "ci_high": b["ci_high"],
        "ci_half_width_realized": (b["ci_high"] - b["ci_low"]) / 2,
        "ci_half_width_design": DESIGN[design_key]["half_width"],
        "boot_mean": b["boot_mean"],
        "n_boot": b["n_boot"], "n_boot_used": b["n_boot_used"],
        "n_boot_undefined": b["n_boot_undefined"],
        "branch": br, "verdict": vd,
        "reliability_10": reliability_table(gold, p, N_BINS),
        "identity_check": identity_check(gold, p),
    }


def git_head():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main(n_boot=N_BOOT):
    print("=" * 96)
    print(f"PHASE 11 -- {STAGE}")
    print("pre-registration phases/11_prior_correction.md @ d589dbad (C11-1..C11-14)")
    print("EVERY NUMBER BELOW IS DEV-ONLY. No C11-10 treatment is run in this stage.")
    print("=" * 96)

    rows, split, gate_checks = load_and_gate()
    ev, cells = build_eval(rows, split)

    # C11-2 frozen denominators / C11-5 strata.
    print("\n[C11-2/C11-5] EVAL cells (slice x gold), frozen denominators")
    cell_checks = []
    for sl, gold, want in EVAL_CELLS:
        got = len(cells[(sl, gold)][0])
        cell_checks.append({"cell": f"{sl} x {gold}", "expected": want,
                            "observed": got, "pass": want == got})
        print(f"  [{'PASS' if want == got else 'FAIL'}] {sl:<13} x {gold:<3}  "
              f"expected {want:>5}   observed {got:>5}")
    if any(not c["pass"] for c in cell_checks):
        sys.exit("ABORT (C11-5): the four bootstrap strata are not the frozen "
                 "denominators. The interval would not preserve them.")

    t0 = time.time()
    print(f"\n[C11-5] bootstrap: {n_boot:,} replicates, seed {BOOT_SEED}, "
          f"percentile interval, alpha {ALPHA}; strata 182/127/278/1795, "
          f"band membership recomputed inside each replicate")
    boot = bootstrap(cells, n_boot=n_boot)
    print(f"        done in {time.time() - t0:.1f}s")

    free_rows, hit_rows = slice_rows(ev, "lexicon_free"), slice_rows(ev, "lexicon_hit")
    primary = band_block(free_rows, "lexicon_free", "SG_free_low", "SG_free_low", boot)
    control = band_block(hit_rows, "lexicon_hit", "SG_hit_low", "SG_hit_low", boot)
    primary["role"] = "PRIMARY (C11-4)"
    control["role"] = "CONTROL (C11-9)"
    control["control_note"] = (
        "C11-9: if under-scoring in the sub-threshold band were a global property of the "
        "model rather than a slice-specific one, both slices would show it at comparable "
        "magnitude. A lexicon_free effect accompanied by a lexicon_hit effect of similar "
        "size does not support a slice-specific account. Design half-width +-0.063, five "
        "times coarser than the primary: this control can refute a large effect and "
        "cannot resolve a small one.")

    desc = {"lexicon_free": describe(free_rows, "lexicon_free"),
            "lexicon_hit": describe(hit_rows, "lexicon_hit")}
    for sl in SLICES:
        desc[sl]["whole_slice_signed_gap_ci"] = {
            k: boot["SG_free" if sl == "lexicon_free" else "SG_hit"][k]
            for k in ("ci_low", "ci_high", "boot_mean")}
        desc[sl]["ece_10_ci"] = {
            k: boot["ECE_free" if sl == "lexicon_free" else "ECE_hit"][k]
            for k in ("ci_low", "ci_high", "boot_mean")}
        desc[sl]["ece_10_ci"]["caveat"] = (
            "Binned ECE is positively biased in small samples (the absolute value cannot "
            "cancel noise), so this percentile interval is not centred on `ece_10` and "
            "`boot_mean` is not the estimate. Reported as pre-registered in C11-5.")

    fair = {
        "statistic": "ECE_hit - ECE_free (10 bins, EVAL, binned on P(OFF))",
        "dev_only": True,
        "ece_lexicon_hit": desc["lexicon_hit"]["ece_10"],
        "ece_lexicon_free": desc["lexicon_free"]["ece_10"],
        "gap": desc["lexicon_hit"]["ece_10"] - desc["lexicon_free"]["ece_10"],
        "ci_low": boot["ECE_gap_hit_minus_free"]["ci_low"],
        "ci_high": boot["ECE_gap_hit_minus_free"]["ci_high"],
        "boot_mean": boot["ECE_gap_hit_minus_free"]["boot_mean"],
        "comparable_to": "Surana arXiv:2605.14074 subgroup calibration gaps, +0.029..+0.134",
        "percentile_ci_is_not_centred_on_the_point_estimate":
            "Binned ECE is a plug-in statistic with a positive small-sample bias: with few "
            "rows per bin, |off_rate_b - mean_p_b| picks up sampling noise that cannot "
            "cancel because it is inside an absolute value. Resampling therefore drifts "
            "UPWARD, and the bootstrap mean of this gap sits well above the observed gap. "
            "The percentile interval pre-registered in C11-5 is reported as pre-registered "
            "and is an interval over the bootstrap distribution -- it is NOT centred on the "
            "observed value, and the bootstrap mean is NOT the estimate. The estimate is "
            "`gap`. The same caveat applies to `ece_10_ci` on each slice, and it bites "
            "harder on lexicon_hit (n=309) than on lexicon_free (n=2073). SignedGap is not "
            "affected: it has no absolute value, so its bootstrap mean tracks the point "
            "estimate.",
        "polarity_warning":
            "C11-1 preamble: Surana's subgroups are OVER-confident (false positives on "
            "identity-mentioning content); our hypothesis concerns UNDER-scoring (false "
            "negatives on profanity-free content). The shapes of evidence are analogous; "
            "the directions are opposite. Any sentence that treats them as the same "
            "finding is wrong. Note also that this gap is an unsigned-ECE difference and "
            "carries no direction of its own -- the direction is in SignedGap.",
    }

    _print_report(primary, control, desc, fair, boot)

    out = {
        "run_id": RUN_ID, "stage": STAGE, "dev_only": True,
        "dev_only_note": "Every number in this file is measured on the frozen dev split "
                         "(fingerprint 034415af3a23b388) and is dev-only. The official "
                         "test set is spent and was not read; load_coltekin_test was not "
                         "called.",
        "preregistration": {"path": "phases/11_prior_correction.md", "commit": "d589dbad",
                            "clauses": "C11-1..C11-14"},
        "not_run_in_this_stage": {
            "C11-10": "Saerens EM prior correction, per-slice Platt scaling, per-slice "
                      "isotonic regression -- Run B, not this stage.",
            "C11-11": "S2 (MIN_ROOT_LEN leak) and S3 (suspect-root contamination) "
                      "sensitivities are not run in this stage. S1 (bin count) IS "
                      "reported, per slice, under `sensitivity_S1_bin_count`.",
        },
        "provenance": {
            "gate_checks": gate_checks,
            "dev_predictions_csv": str(PRED_PATH.relative_to(ROOT)).replace("\\", "/"),
            "dev_predictions_sha256": PRED_SHA256,
            "lexicon": str(Path(config.LEXICON_PATH).relative_to(ROOT)).replace("\\", "/"),
            "lexicon_sha256": LEXICON_SHA256,
            "split_file": str(SPLIT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "split_sha256": SPLIT_SHA256,
            "dev_fingerprint": DEV_FINGERPRINT,
            "score_column": "confidence",
            "score_meaning": "P(OFF), not max-class probability",
            "frozen_decision_rule": "pred == OFF iff confidence > 0.5 (asserted, not assumed)",
        },
        "definitions": {
            "binning": f"{N_BINS} equal-width bins on [0, 1], binned on P(OFF) (C11-3); "
                       "empty bins contribute 0 and are retained in the table with n=0",
            "signed_gap": "sum_b (n_b/N) * (off_rate_b - mean_p_b)",
            "ece": "sum_b (n_b/N) * |off_rate_b - mean_p_b|",
            "sign_convention": "SignedGap > 0 means the model UNDER-states P(OFF) -- "
                               "under-confidence in the OFF direction.",
            "not_the_phase04_statistic":
                "This is the PROBABILISTIC form, binned on P(OFF). Phase 04's statistic "
                "bins on decision confidence max(p, 1-p) over both classes and returned a "
                "global signed gap of -0.0091 with direction `overconfident` and "
                "ECE(15) = 0.0205. The two are different quantities conditioned on "
                "different things and may not be compared or summed (C11-3).",
        },
        "eval_cells": cell_checks,
        "primary": primary,
        "control": control,
        "descriptive": desc,
        "calibration_fairness_gap": fair,
        "bootstrap": {"n_boot": n_boot, "seed": BOOT_SEED, "alpha": ALPHA,
                      "method": "nonparametric, stratified over the four (slice x gold) "
                                "EVAL cells 182/127/278/1795, each resampled with "
                                "replacement to its own original size; band membership "
                                "recomputed inside each replicate; percentile interval",
                      "raw": boot},
        "prediction_C11_12": {
            "recorded_before_the_number": "SG_free_low will be positive but below 0.05 -- "
                                          "branch 4, INTERMEDIATE -- and the substantive "
                                          "content will be in the shape of the reliability "
                                          "curve rather than in the mean.",
            "observed_verdict": primary["verdict"],
            "observed_branch": primary["branch"],
            "prediction_held": primary["branch"] == 4,
        },
        "not_reported": [
            "per-slice macro-F1 (phase-01 pre-registered constraint)",
            "per-slice accuracy (phase-01 pre-registered constraint)",
            "recall at any threshold other than the frozen 0.5",
            "any threshold derived from anything measured here -- nothing here is an "
            "operating point (C11-14)",
        ],
        "ceilings_C11_14": [
            "dev-only", "one seed", "one checkpoint (best.pt = epoch 1)", "same-corpus",
            "the two known slice-definition defects unrepaired, both of which push the "
            "headline in the conservative direction",
            "measurement only: no intervention proposed, no model retrained, no forward "
            "pass, lexicon and MIN_ROOT_LEN frozen, official test set spent and unread",
            "Phase 11's answer does not license Phase 12; it changes what Phase 12 would "
            "be testing, and that is all.",
        ],
        "environment": {"python_version": platform.python_version(),
                        "numpy_version": np.__version__,
                        "git_head": git_head(),
                        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    }

    out_dir = ROOT / "results" / RUN_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "metrics.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nwritten -> {path}")
    print(f"sha256   {sha256_of(path)}")
    return out


def _print_report(primary, control, desc, fair, boot):
    def band_line(b):
        print(f"\n  {b['role']}   {b['statistic']}   (slice {b['slice']}, DEV-ONLY)")
        print(f"    n_band realized {b['n_band_realized']:>5}   "
              f"(C11-6 design projection ~{b['n_band_design']:,})   "
              f"of {b['n_slice']:,} EVAL rows in the slice")
        print(f"    rows at p_OFF == 0.5 exactly: {b['rows_at_p_off_exactly_0.5']} "
              f"(excluded from the band by the literal `p_OFF < 0.5`)")
        print(f"    gold OFF in band {b['gold_off_in_band']:>4}   "
              f"empirical OFF rate {b['off_rate_in_band']:.4f}   "
              f"mean p_OFF {b['mean_p_in_band']:.4f}")
        print(f"    SignedGap  {b['signed_gap']:+.4f}   "
              f"95% CI [{b['ci_low']:+.4f}, {b['ci_high']:+.4f}]   "
              f"half-width +-{b['ci_half_width_realized']:.4f} "
              f"(design +-{b['ci_half_width_design']:.4f})")
        print(f"    ECE(10)    {b['ece']:.4f}")
        print(f"    ---> branch {b['branch']}   VERDICT: {b['verdict']}")

    print("\n" + "=" * 96)
    print("[C11-4 / C11-7 / C11-9] THE SUB-THRESHOLD BAND      *** DEV-ONLY ***")
    print("=" * 96)
    band_line(primary)
    band_line(control)

    print("\n" + "=" * 96)
    print("[C11-8] DESCRIPTIVE, REPORTED REGARDLESS OF VERDICT      *** DEV-ONLY ***")
    print("=" * 96)
    print(f"\n  {'slice':<14}{'n':>7}{'OFF rate':>10}{'mean p':>9}"
          f"{'ECE(10)':>10}{'SignedGap':>11}{'identity':>10}")
    for sl in SLICES:
        d = desc[sl]
        print(f"  {sl:<14}{d['n']:>7}{d['base_rate_off']:>10.4f}{d['mean_p_off']:>9.4f}"
              f"{d['ece_10']:>10.4f}{d['signed_gap_10']:>+11.4f}"
              f"{'OK' if d['identity_check']['holds'] else 'FAIL':>10}")
    print("\n  whole-slice SignedGap is a SECONDARY (C11-4): it telescopes to "
          "(OFF rate - mean p),")
    print("  so it is pinned near zero by arithmetic. Its smallness is not a finding.")
    for sl in SLICES:
        ic = desc[sl]["identity_check"]
        print(f"    {sl:<14} binned(10) {ic['by_bins']['10']['binned']:+.12f}   "
              f"closed form {ic['closed_form']:+.12f}   "
              f"|diff| {ic['by_bins']['10']['abs_diff']:.2e} "
              f"(also checked at 15 and 20 bins, tol 1e-12)")

    for sl in SLICES:
        d = desc[sl]
        print(f"\n  reliability, EVAL {sl}, 10 equal-width bins on P(OFF)   *** DEV-ONLY ***")
        print(f"    {'bin':<16}{'n_b':>7}{'mean_p_b':>11}{'off_rate_b':>12}{'gap':>10}")
        for b in d["reliability_10"]:
            if b["n"] == 0:
                print(f"    {'[%.1f,%.1f)' % (b['lo'], b['hi']):<16}{0:>7}"
                      f"{'-':>11}{'-':>12}{'-':>10}")
            else:
                print(f"    {'[%.1f,%.1f)' % (b['lo'], b['hi']):<16}{b['n']:>7}"
                      f"{b['mean_p']:>11.4f}{b['off_rate']:>12.4f}{b['gap']:>+10.4f}")
        s1 = d["sensitivity_S1_bin_count"]
        print(f"    S1 bin-count sensitivity (C11-11): ECE " +
              "  ".join(f"{nb}b {s1[str(nb)]['ece']:.4f}" for nb in (10, 15, 20)) +
              "   | SignedGap " +
              "  ".join(f"{nb}b {s1[str(nb)]['signed_gap']:+.4f}" for nb in (10, 15, 20)) +
              "  (SignedGap is bin-count invariant by the C11-4 identity)")

    print("\n  calibration-fairness gap  ECE_hit - ECE_free (10 bins, EVAL, DEV-ONLY)")
    print(f"    {fair['ece_lexicon_hit']:.4f} - {fair['ece_lexicon_free']:.4f} = "
          f"{fair['gap']:+.4f}   95% CI [{fair['ci_low']:+.4f}, {fair['ci_high']:+.4f}]")
    print(f"    boot mean {fair['boot_mean']:+.4f} -- NOT the estimate. Binned ECE is "
          "positively biased in")
    print("    small samples, so the percentile interval is not centred on the observed "
          "gap.")
    print(f"    comparable to {fair['comparable_to']}")
    print("    POLARITY: Surana's subgroups are OVER-confident; our hypothesis is")
    print("    UNDER-scoring. Analogous shapes, opposite directions.")

    print("\n" + "=" * 96)
    print("[C11-12] the prediction recorded before the number existed")
    print("=" * 96)
    print("  predicted: SG_free_low positive but below 0.05 -- branch 4, INTERMEDIATE")
    print(f"  observed : branch {primary['branch']}, {primary['verdict']}, "
          f"SG {primary['signed_gap']:+.4f} "
          f"CI [{primary['ci_low']:+.4f}, {primary['ci_high']:+.4f}]")
    print(f"  --> the prediction {'HELD' if primary['branch'] == 4 else 'FAILED'}. "
          "C9-16: a prediction that cannot be wrong is not a prediction.")


if __name__ == "__main__":
    main()
