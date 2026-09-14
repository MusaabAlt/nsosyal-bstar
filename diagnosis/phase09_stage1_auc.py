#!/usr/bin/env python
"""Phase 09 Stage 1 -- threshold-free comparison of the two lexicon slices.

Pre-registration: phases/09_deeper_analysis.md, C9-1 .. C9-11, committed at
12afa74 BEFORE any number in this file existed.

The objection this answers: `lexicon_hit` is 57.8% OFF and `lexicon_free` is
13.6% OFF. A calibrated model assigns lower probabilities in the rarer slice, so
a fixed 0.5 threshold costs recall there automatically. How much of the 33pp
recall gap is where the threshold sits rather than how well the model ranks?

ROC-AUC does not care where the threshold sits. If the AUC gap is small, the
headline narrows -- and C9-6 already says, in git, exactly how it narrows.

Read-only: no training, no forward pass, dev split only, official test set
untouched. Measurement only; no intervention is proposed (C9-11).

Usage:
    python phase09_stage1_auc.py \
        --pred results/01_baseline_berturk/dev_predictions.csv
"""

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config                                    # noqa: E402
from src import lexicon                          # noqa: E402

# --- C9-1 --------------------------------------------------------------------
PRED_SHA256 = "a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346"
PRED_BYTES = 736591

# Every one of these is already in docs/RESULTS_LOG.md. The stage aborts unless
# the dump reproduces all of them -- provenance by content, not by filename.
RECORDED = {
    "n_rows": 4764,
    "gold_off": 920, "gold_not": 3844,
    "pred_off": 848,
    "off_recall": (635, 920),
    "hit_recall": (317, 355),
    "free_recall": (318, 565),
    "n_fn": 285, "n_fp": 213,
    "fp_rate_hit": (47, 259),
    "fp_rate_free": (166, 3585),
    "off_precision": 0.7488,
}

FROZEN_THRESHOLD = 0.5

# --- C9-3 --------------------------------------------------------------------
N_BOOT = 10000
BOOT_SEED = 42
ALPHA = 0.05

# --- C9-4: fixed at 12afa74, from a design calculation, never from the data ---
LARGE = 0.05
SMALL = 0.02

# --- C9-10 -------------------------------------------------------------------
SUSPECT_ROOTS = {"allah", "ana", "cim", "emi", "göt", "mal", "sie"}
# hard checks on the S2 reimplementation, from slice_sensitivity.json
S2_EXPECT = {"excluded": 248, "retained": 366, "excluded_not": 175, "excluded_off": 73}
S1_EXPECT = {"leak_rows": 28}   # phase 08, token_stats.json


# ==============================================================================
# the statistic
# ==============================================================================

def auc_ties(pos, neg):
    """Mann-Whitney U with half credit for ties (C9-2).

    P(random positive scores above random negative) + 0.5 P(equal). Written out
    rather than imported so the tie convention is visible in the code that the
    pre-registration names; it is cross-checked against sklearn in the tests.
    """
    pos = np.asarray(pos, dtype=np.float64)
    neg = np.asarray(neg, dtype=np.float64)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(neg, kind="mergesort")
    ns = neg[order]
    below = np.searchsorted(ns, pos, side="left")     # strictly less
    upto = np.searchsorted(ns, pos, side="right")     # less or equal
    wins = below.sum() + 0.5 * (upto - below).sum()
    return float(wins / (len(pos) * len(neg)))


def average_precision(pos, neg):
    """AP with step interpolation, sum_n (R_n - R_{n-1}) * P_n (C9-9).

    Base-rate sensitive by construction, so C9-9 forbids using it to argue
    either side of the C9-5 verdict. Reported for completeness only.
    """
    scores = np.concatenate([np.asarray(pos, float), np.asarray(neg, float)])
    labels = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    order = np.argsort(-scores, kind="mergesort")
    s, y = scores[order], labels[order]
    # collapse tied scores: a threshold cannot separate rows with equal scores
    boundary = np.r_[np.diff(s) != 0, True]
    tp = np.cumsum(y)[boundary]
    fp = np.cumsum(1 - y)[boundary]
    prec = tp / (tp + fp)
    rec = tp / len(pos)
    return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


class Slice:
    """Score codes for one slice, so a bootstrap replicate costs O(K), not O(n log n)."""

    def __init__(self, name, pos_scores, neg_scores):
        self.name = name
        self.pos = np.asarray(pos_scores, dtype=np.float64)
        self.neg = np.asarray(neg_scores, dtype=np.float64)
        allv = np.concatenate([self.pos, self.neg])
        self.grid = np.unique(allv)                      # ascending distinct scores
        self.K = len(self.grid)
        self.pos_code = np.searchsorted(self.grid, self.pos)
        self.neg_code = np.searchsorted(self.grid, self.neg)
        self.n_pos, self.n_neg = len(self.pos), len(self.neg)

    def counts(self, pos_idx=None, neg_idx=None):
        pc = self.pos_code if pos_idx is None else self.pos_code[pos_idx]
        nc = self.neg_code if neg_idx is None else self.neg_code[neg_idx]
        return (np.bincount(pc, minlength=self.K).astype(np.float64),
                np.bincount(nc, minlength=self.K).astype(np.float64))

    def auc_from_counts(self, cp, cn):
        below = np.cumsum(cn) - cn
        wins = float(np.dot(cp, below + 0.5 * cn))
        return wins / (cp.sum() * cn.sum())

    def sweep(self, cp, cn):
        """Per candidate threshold, the counts flagged. Candidate j means score > grid[j].

        Index 0 is the 'flag everything' threshold (t below the minimum score);
        index j+1 is t = grid[j]. Returns (tp, flagged, thresholds).
        """
        suf_p = np.r_[cp.sum(), cp.sum() - np.cumsum(cp)]
        suf_n = np.r_[cn.sum(), cn.sum() - np.cumsum(cn)]
        thr = np.r_[-np.inf, self.grid]
        return suf_p, suf_p + suf_n, thr


# ==============================================================================
# C9-5: the verdict. Ordered, exhaustive, mutually exclusive.
# ==============================================================================

def verdict(g, ci_low, ci_high):
    """Fixed at 12afa74. Branch order is part of the rule, not an implementation detail."""
    if ci_high < 0:
        return "REVERSES"
    if ci_low <= 0 <= ci_high:
        return "NARROWS"
    if g < SMALL:
        return "NARROWS"
    if g < LARGE:
        return "INTERMEDIATE"
    return "CONFIRMS"


def pct(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=np.float64), q))


def ci_of(vals):
    return {"ci_low": round(pct(vals, 100 * ALPHA / 2), 6),
            "ci_high": round(pct(vals, 100 * (1 - ALPHA / 2)), 6)}


# ==============================================================================
# C9-8: matched operating points
# ==============================================================================

def match_precision(moved, cp, cn, target):
    """Lowest threshold whose precision >= target (C9-8: lowest maximises recall)."""
    tp, flagged, thr = moved.sweep(cp, cn)
    with np.errstate(invalid="ignore", divide="ignore"):
        prec = np.where(flagged > 0, tp / np.maximum(flagged, 1), np.nan)
    ok = np.where((flagged > 0) & (prec >= target))[0]
    if len(ok) == 0:
        j = int(np.nanargmax(prec))
        return {"failed": True, "threshold": float(thr[j]),
                "precision": float(prec[j]), "recall": float(tp[j] / cp.sum()),
                "best_attainable_precision": float(prec[j])}
    j = int(ok[0])
    return {"failed": False, "threshold": float(thr[j]),
            "precision": float(prec[j]), "recall": float(tp[j] / cp.sum())}


def match_flag_rate(moved, cp, cn, target):
    """Threshold whose flagging rate is closest to target; ties -> lower t."""
    tp, flagged, thr = moved.sweep(cp, cn)
    rate = flagged / (cp.sum() + cn.sum())
    j = int(np.argmin(np.abs(rate - target)))          # argmin takes the first = lowest t
    with np.errstate(invalid="ignore", divide="ignore"):
        prec = float(tp[j] / flagged[j]) if flagged[j] > 0 else float("nan")
    return {"failed": False, "threshold": float(thr[j]), "flag_rate": float(rate[j]),
            "precision": prec, "recall": float(tp[j] / cp.sum())}


def reference_point(ref, cp, cn, t=FROZEN_THRESHOLD):
    tp, flagged, thr = ref.sweep(cp, cn)
    j = int(np.searchsorted(thr, t, side="right") - 1)   # largest candidate <= t
    return {"threshold": t,
            "precision": float(tp[j] / flagged[j]) if flagged[j] else float("nan"),
            "recall": float(tp[j] / cp.sum()),
            "flag_rate": float(flagged[j] / (cp.sum() + cn.sum()))}


# ==============================================================================
# loading + provenance (C9-1)
# ==============================================================================

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_predictions(path):
    path = Path(path)
    got_sha, got_bytes = sha256_of(path), path.stat().st_size
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["p_off"] = float(r["confidence"])
    return rows, got_sha, got_bytes


def check_provenance(rows, got_sha, got_bytes):
    """C9-1. Eight recorded figures. A mismatch on any one aborts the stage."""
    fails = []

    def need(name, got, want):
        ok = (got == want)
        print(f"  {'OK  ' if ok else 'FAIL'} {name:<34} {got}")
        if not ok:
            fails.append(f"{name}: got {got}, recorded {want}")

    need("sha256", got_sha, PRED_SHA256)
    need("bytes", got_bytes, PRED_BYTES)
    need("n rows", len(rows), RECORDED["n_rows"])

    gold_off = [r for r in rows if r["gold"] == "OFF"]
    need("gold OFF", len(gold_off), RECORDED["gold_off"])
    need("gold NOT", len(rows) - len(gold_off), RECORDED["gold_not"])
    need("pred OFF", sum(r["pred"] == "OFF" for r in rows), RECORDED["pred_off"])

    conv = all((r["p_off"] > FROZEN_THRESHOLD) == (r["pred"] == "OFF") for r in rows)
    need("pred == OFF iff p_off > 0.5", conv, True)

    def recall(sl=None):
        o = [r for r in gold_off if sl is None or r["slice"] == sl]
        return (sum(r["pred"] == "OFF" for r in o), len(o))

    need("OFF-recall", recall(), RECORDED["off_recall"])
    need("lexicon_hit OFF-recall", recall("lexicon_hit"), RECORDED["hit_recall"])
    need("lexicon_free OFF-recall", recall("lexicon_free"), RECORDED["free_recall"])
    need("false negatives", sum(r["gold"] == "OFF" and r["pred"] == "NOT" for r in rows),
         RECORDED["n_fn"])
    need("false positives", sum(r["gold"] == "NOT" and r["pred"] == "OFF" for r in rows),
         RECORDED["n_fp"])

    for sl, key in (("lexicon_hit", "fp_rate_hit"), ("lexicon_free", "fp_rate_free")):
        n = [r for r in rows if r["slice"] == sl and r["gold"] == "NOT"]
        need(f"FP rate {sl}", (sum(r["pred"] == "OFF" for r in n), len(n)), RECORDED[key])

    tp = sum(r["gold"] == "OFF" and r["pred"] == "OFF" for r in rows)
    pp = sum(r["pred"] == "OFF" for r in rows)
    need("OFF-precision", round(tp / pp, 4), RECORDED["off_precision"])

    if fails:
        sys.exit("ABORT (C9-1): the dump does not reproduce the record:\n  " +
                 "\n  ".join(fails))
    print("  -> provenance established by content, not by filename\n")


# ==============================================================================
# the run
# ==============================================================================

def build_slices(rows):
    out = {}
    for name in ("lexicon_hit", "lexicon_free"):
        sl = [r for r in rows if r["slice"] == name]
        out[name] = Slice(name,
                          [r["p_off"] for r in sl if r["gold"] == "OFF"],
                          [r["p_off"] for r in sl if r["gold"] == "NOT"])
    return out


def bootstrap_pair(hit, free, n_boot=N_BOOT, seed=BOOT_SEED, matched=True):
    """C9-3. Four cells, each resampled to its own original size, 10k, seed 42.

    Matched operating points are recomputed inside the replicate, threshold
    selection included (C9-8), so the interval carries the selection variance.
    """
    rng = np.random.default_rng(seed)
    a_hit, a_free, a_diff = [], [], []
    m = {k: [] for k in ("hit_at_free_prec", "hit_at_free_rate",
                         "free_at_hit_prec", "free_at_hit_rate")}
    for _ in range(n_boot):
        ih_p = rng.integers(0, hit.n_pos, hit.n_pos)
        ih_n = rng.integers(0, hit.n_neg, hit.n_neg)
        if_p = rng.integers(0, free.n_pos, free.n_pos)
        if_n = rng.integers(0, free.n_neg, free.n_neg)
        cph, cnh = hit.counts(ih_p, ih_n)
        cpf, cnf = free.counts(if_p, if_n)
        ah = hit.auc_from_counts(cph, cnh)
        af = free.auc_from_counts(cpf, cnf)
        a_hit.append(ah); a_free.append(af); a_diff.append(ah - af)
        if matched:
            rh = reference_point(hit, cph, cnh)
            rf = reference_point(free, cpf, cnf)
            m["free_at_hit_prec"].append(match_precision(free, cpf, cnf, rh["precision"])["recall"])
            m["free_at_hit_rate"].append(match_flag_rate(free, cpf, cnf, rh["flag_rate"])["recall"])
            m["hit_at_free_prec"].append(match_precision(hit, cph, cnh, rf["precision"])["recall"])
            m["hit_at_free_rate"].append(match_flag_rate(hit, cph, cnh, rf["flag_rate"])["recall"])
    return a_hit, a_free, a_diff, m


def describe(scores):
    s = np.asarray(scores, dtype=np.float64)
    return {"n": int(len(s)), "mean": round(float(s.mean()), 6),
            "q1": round(float(np.percentile(s, 25)), 6),
            "median": round(float(np.median(s)), 6),
            "q3": round(float(np.percentile(s, 75)), 6),
            "share_below_0.5": round(float((s <= 0.5).mean()), 6)}


def matching_roots(text, lex_list):
    """Every lexicon root that hit_root would match on this text.

    Mirrors lexicon.hit_root's inner rule exactly (same MIN_ROOT_LEN, same
    prefix test, same tokeniser) but returns the roots instead of a boolean --
    S2 needs to know WHICH root fired, which hit_root does not report.
    """
    out = set()
    for t in lexicon.tokens(text):
        for root in lex_list:
            if len(root) >= lexicon.MIN_ROOT_LEN and t.startswith(root):
                out.add(root)
    return out


def sensitivities(rows, lex_list, primary):
    """C9-10. All three reported regardless of sign. None may overturn C9-5."""
    res = {}
    short_set = {w for w in lex_list if len(w) < lexicon.MIN_ROOT_LEN}

    # --- S1: MIN_ROOT_LEN leak, as registered: gold-OFF rows only -------------
    leak = [r for r in rows if r["slice"] == "lexicon_free" and r["gold"] == "OFF"
            and set(lexicon.tokens(r["text"])) & short_set]
    print(f"  S1 leak rows (gold-OFF, lexicon_free): {len(leak)} "
          f"(phase 08 recorded {S1_EXPECT['leak_rows']})")
    leak_ids = {r["row_id"] for r in leak}
    kept = [r for r in rows if not (r["row_id"] in leak_ids and r["gold"] == "OFF"
                                    and r["slice"] == "lexicon_free")]
    s = build_slices(kept)
    a_h, a_f = auc_ties(s["lexicon_hit"].pos, s["lexicon_hit"].neg), \
        auc_ties(s["lexicon_free"].pos, s["lexicon_free"].neg)
    res["S1_min_root_len_leak_removed"] = {
        "rule": "registered form: drop gold-OFF lexicon_free rows carrying a "
                "lexicon entry shorter than MIN_ROOT_LEN",
        "short_entries": sorted(short_set), "n_dropped": len(leak),
        "reproduces_phase08_count": len(leak) == S1_EXPECT["leak_rows"],
        "auc_hit": round(a_h, 6), "auc_free": round(a_f, 6),
        "gap": round(a_h - a_f, 6), "shift_vs_primary": round((a_h - a_f) - primary, 6)}

    # NOT pre-registered, reported for completeness: the registered rule drops
    # positives only, which is the phase 08 definition. Dropping the gold-NOT
    # rows that leak the same way is the symmetric version of the same repair.
    leak_all = [r for r in rows if r["slice"] == "lexicon_free"
                and set(lexicon.tokens(r["text"])) & short_set]
    ids_all = {r["row_id"] for r in leak_all}
    kept2 = [r for r in rows if not (r["row_id"] in ids_all and r["slice"] == "lexicon_free")]
    s2 = build_slices(kept2)
    res["S1b_symmetric_NOT_PREREGISTERED"] = {
        "warning": "NOT pre-registered. Reported because the registered S1 drops "
                   "positives only; this is its symmetric counterpart.",
        "n_dropped": len(leak_all),
        "n_dropped_gold_not": len(leak_all) - len(leak),
        "auc_hit": round(auc_ties(s2["lexicon_hit"].pos, s2["lexicon_hit"].neg), 6),
        "auc_free": round(auc_ties(s2["lexicon_free"].pos, s2["lexicon_free"].neg), 6)}
    res["S1b_symmetric_NOT_PREREGISTERED"]["gap"] = round(
        res["S1b_symmetric_NOT_PREREGISTERED"]["auc_hit"] -
        res["S1b_symmetric_NOT_PREREGISTERED"]["auc_free"], 6)

    # --- S2: suspect-root contamination --------------------------------------
    excl = []
    for r in rows:
        if r["slice"] != "lexicon_hit":
            continue
        roots = matching_roots(r["text"], lex_list)
        if roots and roots <= SUSPECT_ROOTS:
            excl.append(r)
    ex_not = sum(r["gold"] == "NOT" for r in excl)
    ok = (len(excl) == S2_EXPECT["excluded"] and ex_not == S2_EXPECT["excluded_not"])
    print(f"  S2 excluded rows: {len(excl)} (NOT {ex_not} / OFF {len(excl) - ex_not}); "
          f"slice_sensitivity.json recorded {S2_EXPECT['excluded']} "
          f"(NOT {S2_EXPECT['excluded_not']} / OFF {S2_EXPECT['excluded_off']}) "
          f"-> {'MATCH' if ok else 'MISMATCH'}")
    ex_ids = {r["row_id"] for r in excl}
    kept3 = [r for r in rows if r["row_id"] not in ex_ids]
    s3 = build_slices(kept3)
    a_h3 = auc_ties(s3["lexicon_hit"].pos, s3["lexicon_hit"].neg)
    a_f3 = auc_ties(s3["lexicon_free"].pos, s3["lexicon_free"].neg)
    res["S2_suspect_roots_excluded"] = {
        "rule": "drop a lexicon_hit row when EVERY matching lexicon root is suspect "
                "(results/02_failure_analysis/slice_sensitivity.json)",
        "suspect_roots": sorted(SUSPECT_ROOTS), "n_excluded": len(excl),
        "excluded_gold": {"NOT": ex_not, "OFF": len(excl) - ex_not},
        "reproduces_phase02_counts": ok,
        "auc_hit": round(a_h3, 6), "auc_free": round(a_f3, 6),
        "gap": round(a_h3 - a_f3, 6), "shift_vs_primary": round((a_h3 - a_f3) - primary, 6)}

    # --- S3: how much the tie convention could be worth ----------------------
    s0 = build_slices(rows)

    def auc_tie_as(pos, neg, credit):
        pos, neg = np.asarray(pos), np.sort(np.asarray(neg))
        below = np.searchsorted(neg, pos, side="left")
        upto = np.searchsorted(neg, pos, side="right")
        return float((below.sum() + credit * (upto - below).sum()) / (len(pos) * len(neg)))

    res["S3_tie_convention"] = {}
    for credit, label in ((0.0, "ties_count_zero"), (1.0, "ties_count_one")):
        h = auc_tie_as(s0["lexicon_hit"].pos, s0["lexicon_hit"].neg, credit)
        f = auc_tie_as(s0["lexicon_free"].pos, s0["lexicon_free"].neg, credit)
        res["S3_tie_convention"][label] = {
            "auc_hit": round(h, 6), "auc_free": round(f, 6), "gap": round(h - f, 6)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="results/01_baseline_berturk/dev_predictions.csv")
    ap.add_argument("--out_dir", default="results/09_deeper_analysis/stage_1")
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
    args = ap.parse_args()

    print("=" * 88)
    print("PHASE 09 STAGE 1 -- threshold-free slice comparison")
    print("pre-registration: phases/09_deeper_analysis.md C9-1..C9-11 (commit 12afa74)")
    print("=" * 88)

    print("\n[C9-1] provenance")
    rows, got_sha, got_bytes = load_predictions(args.pred)
    check_provenance(rows, got_sha, got_bytes)

    sl = build_slices(rows)
    hit, free = sl["lexicon_hit"], sl["lexicon_free"]

    print("[C9-2] slice AUC (Mann-Whitney U, ties at half credit)")
    auc_hit = auc_ties(hit.pos, hit.neg)
    auc_free = auc_ties(free.pos, free.neg)
    gap = auc_hit - auc_free
    for s, a in ((hit, auc_hit), (free, auc_free)):
        print(f"  {s.name:<13} n_OFF {s.n_pos:>4}  n_NOT {s.n_neg:>5}  "
              f"base rate {s.n_pos / (s.n_pos + s.n_neg):.4f}  AUC {a:.6f}")
    print(f"  G = AUC(hit) - AUC(free) = {gap:+.6f}")

    print(f"\n[C9-3] bootstrap: {args.n_boot:,} replicates, seed {BOOT_SEED}, "
          f"four cells resampled to their own sizes")
    b_hit, b_free, b_diff, b_match = bootstrap_pair(hit, free, n_boot=args.n_boot)
    ci_hit, ci_free, ci_gap = ci_of(b_hit), ci_of(b_free), ci_of(b_diff)
    print(f"  AUC hit   {auc_hit:.6f}  [{ci_hit['ci_low']:+.6f}, {ci_hit['ci_high']:+.6f}]")
    print(f"  AUC free  {auc_free:.6f}  [{ci_free['ci_low']:+.6f}, {ci_free['ci_high']:+.6f}]")
    print(f"  GAP       {gap:+.6f}  [{ci_gap['ci_low']:+.6f}, {ci_gap['ci_high']:+.6f}]")

    v = verdict(gap, ci_gap["ci_low"], ci_gap["ci_high"])
    print(f"\n[C9-5] VERDICT: {v}    (LARGE >= {LARGE}, SMALL < {SMALL}, "
          f"thresholds fixed at 12afa74)")

    print("\n[C9-7] score distributions")
    dist = {}
    for s in (hit, free):
        dist[s.name] = {"gold_OFF": describe(s.pos), "gold_NOT": describe(s.neg)}
        for k in ("gold_OFF", "gold_NOT"):
            d = dist[s.name][k]
            print(f"  {s.name:<13} {k}  n {d['n']:>5}  mean {d['mean']:.4f}  "
                  f"Q1 {d['q1']:.4f}  med {d['median']:.4f}  Q3 {d['q3']:.4f}  "
                  f"<=0.5 {d['share_below_0.5']:.4f}")

    print("\n[C9-8] matched operating points")
    cph, cnh = hit.counts()
    cpf, cnf = free.counts()
    ref_hit = reference_point(hit, cph, cnh)
    ref_free = reference_point(free, cpf, cnf)
    matched = {
        "reference_lexicon_hit_at_0.5": ref_hit,
        "reference_lexicon_free_at_0.5": ref_free,
        "free_matched_to_hit_precision": match_precision(free, cpf, cnf, ref_hit["precision"]),
        "free_matched_to_hit_flag_rate": match_flag_rate(free, cpf, cnf, ref_hit["flag_rate"]),
        "hit_matched_to_free_precision": match_precision(hit, cph, cnh, ref_free["precision"]),
        "hit_matched_to_free_flag_rate": match_flag_rate(hit, cph, cnh, ref_free["flag_rate"]),
    }
    boot_key = {"free_matched_to_hit_precision": "free_at_hit_prec",
                "free_matched_to_hit_flag_rate": "free_at_hit_rate",
                "hit_matched_to_free_precision": "hit_at_free_prec",
                "hit_matched_to_free_flag_rate": "hit_at_free_rate"}
    for k, bk in boot_key.items():
        matched[k]["recall_ci"] = ci_of(b_match[bk])
    print(f"  reference hit @0.5 : precision {ref_hit['precision']:.4f}  "
          f"recall {ref_hit['recall']:.4f}  flag rate {ref_hit['flag_rate']:.4f}")
    print(f"  reference free @0.5: precision {ref_free['precision']:.4f}  "
          f"recall {ref_free['recall']:.4f}  flag rate {ref_free['flag_rate']:.4f}")
    for k in boot_key:
        m = matched[k]
        print(f"  {k:<34} t {m['threshold']:.6f}  recall {m['recall']:.4f} "
              f"[{m['recall_ci']['ci_low']:.4f}, {m['recall_ci']['ci_high']:.4f}]"
              f"{'   MATCH FAILED' if m.get('failed') else ''}")

    print("\n[C9-9] average precision (base-rate sensitive; may not argue the verdict)")
    ap_hit = average_precision(hit.pos, hit.neg)
    ap_free = average_precision(free.pos, free.neg)
    print(f"  AP hit {ap_hit:.6f}   AP free {ap_free:.6f}   "
          f"(base rates {hit.n_pos / (hit.n_pos + hit.n_neg):.4f} / "
          f"{free.n_pos / (free.n_pos + free.n_neg):.4f})")

    print("\n[C9-10] sensitivities")
    lex_list = lexicon.load_lexicon(config.LEXICON_PATH)
    sens = sensitivities(rows, lex_list, gap)
    for k in ("S1_min_root_len_leak_removed", "S2_suspect_roots_excluded"):
        d = sens[k]
        print(f"  {k:<34} gap {d['gap']:+.6f}  (shift {d['shift_vs_primary']:+.6f})")
    for k, d in sens["S3_tie_convention"].items():
        print(f"  S3 {k:<31} gap {d['gap']:+.6f}")

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "?"

    payload = {
        "run_id": "09_deeper_analysis/stage_1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_sha": sha,
        "preregistration": "phases/09_deeper_analysis.md C9-1..C9-11, commit 12afa74",
        "scope": "measurement only; no training, no forward pass, no intervention (C9-11)",
        "inputs": {
            "predictions": str(args.pred),
            "sha256": got_sha, "bytes": got_bytes,
            "checkpoint": "BERTurk best.pt = epoch 1 (phase 01)",
            "dev_fingerprint": "034415af3a23b388",
            "provenance_check": "all recorded phase-01 figures reproduced (C9-1)",
            "test_set_touched": False,
        },
        "thresholds_fixed_in_advance": {"LARGE": LARGE, "SMALL": SMALL,
                                        "source": "Hanley-McNeil design calculation, "
                                                  "frozen denominators + assumed AUC"},
        "primary": {
            "auc_lexicon_hit": round(auc_hit, 6), "auc_lexicon_hit_ci": ci_hit,
            "auc_lexicon_free": round(auc_free, 6), "auc_lexicon_free_ci": ci_free,
            "gap": round(gap, 6), "gap_ci": ci_gap,
            "verdict": v,
            "n": {"hit_off": hit.n_pos, "hit_not": hit.n_neg,
                  "free_off": free.n_pos, "free_not": free.n_neg},
            "base_rate": {"lexicon_hit": round(hit.n_pos / (hit.n_pos + hit.n_neg), 6),
                          "lexicon_free": round(free.n_pos / (free.n_pos + free.n_neg), 6)},
            "bootstrap": {"n_boot": args.n_boot, "seed": BOOT_SEED, "alpha": ALPHA,
                          "method": "stratified over the four slice x gold cells, "
                                    "percentile interval"},
        },
        "score_distributions": dist,
        "matched_operating_points": matched,
        "average_precision": {"lexicon_hit": round(ap_hit, 6),
                              "lexicon_free": round(ap_free, 6),
                              "note": "C9-9: base-rate sensitive, reported for "
                                      "completeness, may not argue the verdict"},
        "sensitivities": sens,
        "recall_gap_for_reference": {
            "lexicon_hit_off_recall": 0.8929577464788733,
            "lexicon_free_off_recall": 0.5628318584070796,
            "gap": 0.33012588807179366,
            "source": "results/02_failure_analysis/slice_sensitivity.json",
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "stage1_auc.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)")
    print("=" * 88)


if __name__ == "__main__":
    main()
