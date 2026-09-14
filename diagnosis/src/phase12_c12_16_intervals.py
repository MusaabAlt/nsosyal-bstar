#!/usr/bin/env python3
"""C12-16 -- intervals on the S1a-vs-S0 headline. Phase 12, Addendum 3.

Pre-registration: `phases/12_threshold_policy.md` Addendum 3 / C12-16, committed
at b0f2b0b5 BEFORE this file computed anything. Addendum 3 states its own
ordering plainly and this module does not soften it: the four QUANTITIES were
fixed in advance by C12-8 and C12-4, but their UNCERTAINTY is being computed
late, after the point estimates were seen and published in the `RESULTS_LOG`
row at d74acd93. That is estimation after the fact, not pre-registration.

Scope, and nothing outside it: S1a (t = 0.25) versus S0 (t = 0.5), on EVAL, at
r = 3 only. No verdict is computed and no branch rule exists for these
quantities (C12-16). No other `r`, no other system pair, no pooling to full dev.

Every number is dev-only. The official test set is spent; `load_coltekin_test`
is never called.

Usage:
    python -m src.phase12_c12_16_intervals
"""

import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import phase11_prior_correction as p11                     # noqa: E402
from src import phase12_threshold_policy as p12                     # noqa: E402

RUN_ID = "12_threshold_policy"
STAGE = "C12-16 -- intervals on the S1a-vs-S0 headline (Addendum 3)"
PREREG = "phases/12_threshold_policy.md Addendum 3 / C12-16 @ b0f2b0b5"

OUT = ROOT / "results/12_threshold_policy/c12_16_intervals.json"
METRICS_SHA256 = "c60bd4a3c4f9040129202c66e7d84cb68fb1cfe539881f68eaf21669cf3b3815"

R = 3
T_S0 = 0.5                      # frozen historical
T_S1A = p12.elkan_threshold(R)  # analytic Elkan, 1/(1+3) = 0.25
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
TOL = 5e-7                      # "to six decimal places"

# C12-16's recorded point estimates. These came from the committed run and must
# reproduce; a disagreement beyond six decimals is a defect and aborts.
RECORDED = {
    "d_recall": 0.130435,
    "d_recall_free": 0.172662,
    "d_gap": -0.106728,
    "d_precision": -0.141816,
}


def quantities(scores, gold_off, is_hit, t):
    """The four ingredients, for one arm, on one (possibly resampled) row set.

    OFF-recall, `lexicon_free` OFF-recall, the hit-free recall gap, and
    OFF-precision. No macro-F1 and no accuracy: the phase-01 constraint holds
    here as everywhere else in Phase 12.
    """
    flag = scores > t
    off = gold_off
    free = ~is_hit
    n_off = off.sum()
    n_flag = flag.sum()
    tp = (off & flag).sum()

    off_free = off & free
    tp_free = off_free & flag
    off_hit = off & is_hit
    tp_hit = off_hit & flag

    rec = tp / n_off if n_off else np.nan
    rec_free = tp_free.sum() / off_free.sum() if off_free.sum() else np.nan
    rec_hit = tp_hit.sum() / off_hit.sum() if off_hit.sum() else np.nan
    prec = tp / n_flag if n_flag else np.nan
    return {"off_recall": float(rec), "off_recall_free": float(rec_free),
            "gap": float(rec_hit - rec_free), "off_precision": float(prec)}


def deltas(scores, gold_off, is_hit):
    """S1a minus S0 on the same rows -- the paired difference."""
    a = quantities(scores, gold_off, is_hit, T_S1A)
    b = quantities(scores, gold_off, is_hit, T_S0)
    return {"d_recall": a["off_recall"] - b["off_recall"],
            "d_recall_free": a["off_recall_free"] - b["off_recall_free"],
            "d_gap": a["gap"] - b["gap"],
            "d_precision": a["off_precision"] - b["off_precision"]}, a, b


def main(n_boot=N_BOOT):
    t0 = time.time()
    print("=" * 96)
    print(f"PHASE 12 -- {STAGE}")
    print(f"pre-registration {PREREG}")
    print("EVERY NUMBER BELOW IS DEV-ONLY. The official test set is spent and is not read.")
    print("No verdict is computed. r = 3 only. S1a vs S0 only. EVAL only.")
    print("=" * 96)

    # --- provenance gate: the same one the Phase 12 run used -----------------
    rows, split, gate_checks = p11.load_and_gate()
    metrics_path = ROOT / "results/12_threshold_policy/metrics.json"
    got = p12.sha256_of(metrics_path)
    if got != METRICS_SHA256:
        sys.exit(f"ABORT: metrics.json sha256 {got} != recorded {METRICS_SHA256}")
    print(f"\n[gate] metrics.json sha256 matches the committed run "
          f"({METRICS_SHA256[:16]}...)")

    eval_ids = set(split["eval_row_ids"])
    ev = [r for r in rows if r["row_id"] in eval_ids]
    g = p11.Gate()
    g.add("EVAL rows", 2382, len(ev))
    for sl, gold, want in p12.EVAL_CELLS:
        g.add(f"EVAL {sl} x {gold}", want,
              sum(1 for r in ev if r["slice"] == sl and r["gold"] == gold))
    g.report("[C12-16] EVAL strata, frozen denominators")
    cell_checks = g.enforce()

    # --- point estimates, reproduced against C12-16 --------------------------
    scores = np.array([r["p_off"] for r in ev], dtype=np.float64)
    gold_off = np.array([r["gold"] == "OFF" for r in ev], dtype=bool)
    is_hit = np.array([r["slice"] == "lexicon_hit" for r in ev], dtype=bool)

    point, q_s1a, q_s0 = deltas(scores, gold_off, is_hit)

    print(f"\n[C12-16] point estimates against the values recorded in the clause "
          f"(tolerance {TOL:g}, i.e. six decimals)")
    print(f"  {'quantity':<16} {'observed':>14} {'C12-16 recorded':>18} "
          f"{'abs diff':>12}   status")
    bad = []
    reproduction = {}
    for k, want in RECORDED.items():
        obs = point[k]
        diff = abs(obs - want)
        ok = diff <= TOL
        if not ok:
            bad.append(k)
        reproduction[k] = {"observed": obs, "recorded_in_C12_16": want,
                           "abs_diff": diff, "reproduces_to_six_decimals": bool(ok)}
        print(f"  {k:<16} {obs:>+14.6f} {want:>+18.6f} {diff:>12.2e}   "
              f"{'MATCH' if ok else '*** FLAG: DISAGREEMENT ***'}")
    if bad:
        sys.exit(f"ABORT (C12-16): {len(bad)} point estimate(s) do not reproduce to six "
                 f"decimals: {bad}. The clause says a disagreement beyond that is a "
                 f"defect and aborts.")

    # --- the realized discordant gold-OFF count ------------------------------
    f_s0 = scores > T_S0
    f_s1a = scores > T_S1A
    nests = bool((f_s0 & ~f_s1a).sum() == 0)
    disc_off = int((gold_off & (f_s0 != f_s1a)).sum())
    print(f"\n[C12-16] realized discordant gold-OFF count = {disc_off} "
          f"(design figure: exactly 60)  -> "
          f"{'MATCH' if disc_off == 60 else '*** FLAG: DISAGREEMENT ***'}")
    print(f"  S0 catches {int((gold_off & f_s0).sum())} of {int(gold_off.sum())} EVAL "
          f"gold-OFF; S1a catches {int((gold_off & f_s1a).sum())}; S1a's flagged set "
          f"{'strictly nests' if nests else 'does NOT nest'} S0's "
          f"(S0 flags {int(f_s0.sum())}, S1a flags {int(f_s1a.sum())})")

    # --- the paired bootstrap, C12-6's scheme exactly ------------------------
    # Both arms are zero-parameter, so nothing is fitted and nothing is held
    # fixed across replicates: unlike C12-6, no threshold-selection variance is
    # being excluded here, and C12-16 says the C12-6 understatement caveat does
    # not apply. Cells are drawn in the order C12-2 lists them; the draw order is
    # part of what seed 42 reproduces.
    rng = np.random.default_rng(SEED)
    idx_of = {}
    for sl, gold, _ in p12.EVAL_CELLS:
        idx_of[(sl, gold)] = np.array(
            [i for i, r in enumerate(ev) if r["slice"] == sl and r["gold"] == gold],
            dtype=np.int64)
    order = [(sl, gold) for sl, gold, _ in p12.EVAL_CELLS]

    keys = list(RECORDED)
    draws = {k: np.empty(n_boot, dtype=np.float64) for k in keys}
    undefined = {k: 0 for k in keys}
    print(f"\n[C12-16] paired bootstrap: {n_boot} replicates, seed {SEED}, stratified "
          f"over 182/127/278/1795, percentile, alpha = {ALPHA}")
    for b in range(n_boot):
        parts = []
        for key in order:
            pool = idx_of[key]
            parts.append(pool[rng.integers(0, pool.size, pool.size)])
        sel = np.concatenate(parts)
        d, _, _ = deltas(scores[sel], gold_off[sel], is_hit[sel])
        for k in keys:
            v = d[k]
            if np.isnan(v):
                undefined[k] += 1
            draws[k][b] = v

    intervals = {}
    for k in keys:
        a = draws[k]
        a = a[~np.isnan(a)]
        lo = float(np.percentile(a, 100 * ALPHA / 2))
        hi = float(np.percentile(a, 100 * (1 - ALPHA / 2)))
        intervals[k] = {
            "point_estimate": point[k],
            "ci_low": lo, "ci_high": hi,
            "half_width": (hi - lo) / 2.0,
            "boot_mean": float(a.mean()), "boot_median": float(np.median(a)),
            "boot_se": float(a.std(ddof=1)),
            "n_boot": n_boot, "n_boot_used": int(a.size),
            "n_boot_undefined": undefined[k],
            "alpha": ALPHA, "seed": SEED, "interval_type": "percentile",
            "excludes_zero": bool(lo > 0 or hi < 0),
        }

    print(f"  {'quantity':<16} {'point':>10} {'ci_low':>11} {'ci_high':>11} "
          f"{'half-width':>11} {'SE':>9}  excludes 0")
    for k in keys:
        v = intervals[k]
        print(f"  {k:<16} {v['point_estimate']:>+10.6f} {v['ci_low']:>+11.6f} "
              f"{v['ci_high']:>+11.6f} {v['half_width']:>11.6f} {v['boot_se']:>9.6f}  "
              f"{'yes' if v['excludes_zero'] else 'no'}")

    out = {
        "run_id": RUN_ID,
        "stage": STAGE,
        "clause": "C12-16",
        "dev_only": True,
        "dev_only_note": "EVAL half of the dev split (fingerprint 034415af3a23b388). "
                         "The official test set is spent and was not read. C12-14 "
                         "governs: no interval here makes any of these numbers "
                         "validatable on held-out data.",
        "ordering_disclosure": (
            "The four QUANTITIES were fixed in advance by C12-8 and C12-4's "
            "designation of r = 3 as primary. Their UNCERTAINTY was computed late, "
            "after the point estimates were seen and published in the RESULTS_LOG "
            "row at commit d74acd93. Addendum 3 (b0f2b0b5) records that ordering. "
            "This is estimation after the fact, not pre-registration."),
        "preregistration": {
            "file": "phases/12_threshold_policy.md",
            "clause": "Addendum 3 / C12-16",
            "commit": "b0f2b0b528f577de56df0efb23a3dff33f2279b0",
            "metrics_sha256_verified": METRICS_SHA256,
        },
        "scope": {
            "systems": "S1a (analytic Elkan, t = 1/(1+r)) versus S0 (frozen 0.5)",
            "t_S1a": T_S1A, "t_S0": T_S0,
            "r": R, "split": "EVAL only -- pooling to full dev declined by C12-16",
            "both_arms_zero_parameter": True,
            "c12_6_understatement_caveat_applies": False,
        },
        "not_run_in_this_stage": [
            "no verdict and no branch rule -- C12-16 defines none",
            "no other r; the rest of the frontier stays descriptive per C12-8",
            "no other system pair",
            "no pooling to full dev",
            "no multiplicity correction -- these are estimation intervals, not tests",
            "no per-slice macro-F1 and no per-slice accuracy (phase-01 constraint)",
            "no RESULTS_LOG row -- the controller drafts it",
        ],
        "provenance": {"gate": gate_checks, "strata": cell_checks},
        "point_estimate_reproduction": reproduction,
        "arms_on_EVAL": {"S1a": q_s1a, "S0": q_s0},
        "discordance": {
            "realized_discordant_gold_off": disc_off,
            "design_figure": 60,
            "matches_design": bool(disc_off == 60),
            "S0_gold_off_caught": int((gold_off & f_s0).sum()),
            "S1a_gold_off_caught": int((gold_off & f_s1a).sum()),
            "n_gold_off": int(gold_off.sum()),
            "S0_flagged": int(f_s0.sum()), "S1a_flagged": int(f_s1a.sum()),
            "S1a_strictly_nests_S0": nests,
        },
        "intervals": intervals,
        "bootstrap": {
            "n_boot": n_boot, "seed": SEED, "alpha": ALPHA,
            "interval": "percentile", "paired": True,
            "strata": [{"slice": sl, "gold": gd, "n": int(idx_of[(sl, gd)].size)}
                       for sl, gd in order],
            "scheme": "identical to C12-6: each of the four EVAL cells resampled with "
                      "replacement to its own original size; both arms score the "
                      "identical resampled rows",
        },
        "environment": {
            "python": platform.python_version(), "numpy": np.__version__,
            "platform": platform.platform(),
            "git_head_at_run": p12.git_head(),
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "elapsed_seconds": round(time.time() - t0, 1),
        },
    }

    hits, bad_keys = p12._no_row_text(out, [r["text"] for r in rows])
    print(f"\n[output] no-corpus-row-text check: {len(hits)} of {len(rows)} dev texts "
          f"found as substrings, {len(bad_keys)} text-carrying keys")
    if hits or bad_keys:
        sys.exit(f"ABORT: output would carry corpus row text ({len(hits)} texts, "
                 f"keys {bad_keys[:5]}).")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[output] wrote {OUT} ({OUT.stat().st_size} bytes, sha256 "
          f"{p12.sha256_of(OUT)[:16]}...)")
    print("[output] NOT committed, by instruction. No RESULTS_LOG row.")
    print("=" * 96)
    return out


if __name__ == "__main__":
    main()
