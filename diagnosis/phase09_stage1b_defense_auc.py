#!/usr/bin/env python
"""Phase 09 Stage 1b -- did +1a+1b+D improve ranking, or move scores?

Pre-registration: phases/09_deeper_analysis.md, C9-12 .. C9-17, committed at
910d21e BEFORE any number in this file existed.

The intervention raised `lexicon_free` OFF-recall by +0.0336 [+0.0052, +0.0662]
on dev. Stage 1 has just shown that a recall change at a fixed threshold can come
from ordering or from placement. This stage asks which, by comparing ROC-AUC --
which is invariant to both threshold and base rate -- between the two systems on
the same rows.

Read-only: no training, no forward pass, dev split only, official test set
untouched. Measurement only; no intervention is proposed (C9-17).

Usage:
    python phase09_stage1b_defense_auc.py \
        --control   <dir>/run_raw/dev_predictions.csv \
        --treatment <dir>/run_1a1b_d/dev_predictions.csv

Both dumps survive only on the Drive mirror. C9-12 forbids substituting the
phase-01 baseline dump for `run_raw`: the +0.0336 was computed against run_raw,
and quietly swapping the control would change the quantity being explained.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase09_stage1_auc as s1                  # noqa: E402

FROZEN_THRESHOLD = s1.FROZEN_THRESHOLD
N_BOOT = 10000
BOOT_SEED = 42

# --- C9-15: fixed at 910d21e, from AUC's own scale, never from the data -------
SMALL_DELTA = 0.01

COMPARISON = "results/03_defense/comparison.json"
CONTROL_RUN, TREATMENT_RUN = "raw", "1a1b_d"


# ==============================================================================
# C9-15 -- the interpretation rule. Ordered, exhaustive, mutually exclusive.
# ==============================================================================

def verdict_1b(delta, ci_low, ci_high):
    """Branch order is part of the rule, not an implementation detail."""
    if ci_high < 0:
        return "ORDERING WORSENED"
    if ci_low <= 0 <= ci_high:
        return "FLAT"
    if delta < SMALL_DELTA:
        return "MARGINAL"
    return "DISCRIMINATION IMPROVED"


# ==============================================================================
# C9-12 -- provenance, by content
# ==============================================================================

def recorded_figures(run_key, comparison_path=COMPARISON):
    c = json.loads(Path(comparison_path).read_text(encoding="utf-8"))["runs"][run_key]
    return {
        "macro_f1": round(c["macro_f1"], 4),
        "off_recall": round(c["off_recall"], 4),
        "lexicon_free_off_recall": round(c["lexicon_free_off_recall"], 4),
        "lexicon_hit_off_recall": round(c["lexicon_hit_off_recall"], 4),
        "lexicon_hit_fp_rate": round(c["lexicon_hit_fp_rate"], 4),
        "false_positives_total": c["false_positives_total"],
    }


def observed_figures(rows):
    """Recomputed from the dump, in the same shapes comparison.json records."""
    from collections import Counter

    def f1(pos):
        tp = sum(r["gold"] == pos and r["pred"] == pos for r in rows)
        fp = sum(r["gold"] != pos and r["pred"] == pos for r in rows)
        fn = sum(r["gold"] == pos and r["pred"] != pos for r in rows)
        return 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)

    def recall(sl=None):
        o = [r for r in rows if r["gold"] == "OFF" and (sl is None or r["slice"] == sl)]
        return sum(r["pred"] == "OFF" for r in o) / len(o)

    hit_not = [r for r in rows if r["slice"] == "lexicon_hit" and r["gold"] == "NOT"]
    return {
        "macro_f1": round((f1("OFF") + f1("NOT")) / 2, 4),
        "off_recall": round(recall(), 4),
        "lexicon_free_off_recall": round(recall("lexicon_free"), 4),
        "lexicon_hit_off_recall": round(recall("lexicon_hit"), 4),
        "lexicon_hit_fp_rate": round(sum(r["pred"] == "OFF" for r in hit_not) / len(hit_not), 4),
        "false_positives_total": sum(r["gold"] == "NOT" and r["pred"] == "OFF" for r in rows),
    }


def check_run(label, rows, run_key, comparison_path=COMPARISON):
    want, got = recorded_figures(run_key, comparison_path), observed_figures(rows)
    print(f"  [{label}] against comparison.json runs.{run_key}")
    bad = []
    for k in want:
        ok = got[k] == want[k]
        print(f"    {'OK  ' if ok else 'FAIL'} {k:<26} {got[k]}")
        if not ok:
            bad.append(f"{k}: got {got[k]}, recorded {want[k]}")
    if bad:
        sys.exit(f"ABORT (C9-12): {label} does not reproduce its record:\n  " + "\n  ".join(bad))


def load_aligned(control_path, treatment_path):
    """Load both dumps and align them row-for-row.

    A paired comparison that is silently unpaired would look like a tighter
    result, not a broken one, so the alignment is asserted rather than assumed.
    """
    for p in (control_path, treatment_path):
        if not Path(p).is_file():
            sys.exit(f"ABORT (C9-12): {p} not found. Stage 1b is BLOCKED, not run "
                     f"with a substitute -- the dumps live only on the Drive mirror.")
    a, _, _ = s1.load_predictions(control_path)
    b, _, _ = s1.load_predictions(treatment_path)
    a.sort(key=lambda r: int(r["row_id"]))
    b.sort(key=lambda r: int(r["row_id"]))
    if len(a) != len(b):
        sys.exit(f"ABORT: row counts differ, {len(a)} vs {len(b)}")
    for x, y in zip(a, b):
        if x["row_id"] != y["row_id"] or x["gold"] != y["gold"] or x["slice"] != y["slice"]:
            sys.exit(f"ABORT: dumps disagree on row {x['row_id']} "
                     f"(gold/slice must be model-independent)")
    return a, b


# ==============================================================================
# C9-13 -- the paired comparison
# ==============================================================================

def paired_slices(a_rows, b_rows, slice_name):
    """Two Slice objects over the SAME rows in the SAME order."""
    idx = [i for i, r in enumerate(a_rows) if r["slice"] == slice_name]
    pos = [i for i in idx if a_rows[i]["gold"] == "OFF"]
    neg = [i for i in idx if a_rows[i]["gold"] == "NOT"]
    sa = s1.Slice(slice_name, [a_rows[i]["p_off"] for i in pos], [a_rows[i]["p_off"] for i in neg])
    sb = s1.Slice(slice_name, [b_rows[i]["p_off"] for i in pos], [b_rows[i]["p_off"] for i in neg])
    return sa, sb


def paired_delta(sa, sb, n_boot=N_BOOT, seed=BOOT_SEED):
    """C9-13: resample rows ONCE per replicate, score BOTH systems on them.

    Using independent resamples for the two systems would discard the pairing
    and widen the interval for no reason; using different indices for the two
    would be worse than that -- it would not estimate the paired difference at
    all. The same index arrays therefore drive both.
    """
    rng = np.random.default_rng(seed)
    da, db, dd = [], [], []
    for _ in range(n_boot):
        pi = rng.integers(0, sa.n_pos, sa.n_pos)
        ni = rng.integers(0, sa.n_neg, sa.n_neg)
        cpa, cna = sa.counts(pi, ni)
        cpb, cnb = sb.counts(pi, ni)          # SAME rows
        aa = sa.auc_from_counts(cpa, cna)
        bb = sb.auc_from_counts(cpb, cnb)
        da.append(aa); db.append(bb); dd.append(bb - aa)
    return da, db, dd


def crossings(a_rows, b_rows, slice_name, gold):
    """C9-14: rows that changed side of the frozen threshold, each direction."""
    up = dn = 0
    for x, y in zip(a_rows, b_rows):
        if x["slice"] != slice_name or x["gold"] != gold:
            continue
        was = x["p_off"] > FROZEN_THRESHOLD
        now = y["p_off"] > FROZEN_THRESHOLD
        if now and not was:
            up += 1
        elif was and not now:
            dn += 1
    return {"NOT_to_OFF": up, "OFF_to_NOT": dn, "net": up - dn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True,
                    help="run_raw/dev_predictions.csv -- C9-12 forbids substituting "
                         "the phase-01 dump here")
    ap.add_argument("--treatment", required=True, help="run_1a1b_d/dev_predictions.csv")
    ap.add_argument("--out_dir", default="results/09_deeper_analysis/stage_1b")
    ap.add_argument("--n_boot", type=int, default=N_BOOT)
    args = ap.parse_args()

    print("=" * 88)
    print("PHASE 09 STAGE 1b -- ranking or placement?")
    print("pre-registration: phases/09_deeper_analysis.md C9-12..C9-17 (commit 910d21e)")
    print("=" * 88)

    print("\n[C9-12] provenance")
    a_rows, b_rows = load_aligned(args.control, args.treatment)
    sha_a, sha_b = s1.sha256_of(args.control), s1.sha256_of(args.treatment)
    print(f"  control   sha256 {sha_a}")
    print(f"  treatment sha256 {sha_b}")
    print(f"  control is byte-identical to the phase-01 baseline dump: "
          f"{sha_a == s1.PRED_SHA256}")
    check_run("control", a_rows, CONTROL_RUN)
    check_run("treatment", b_rows, TREATMENT_RUN)
    print(f"  aligned row-for-row on {len(a_rows):,} rows\n")

    payload_slices, verdicts = {}, {}
    for name in ("lexicon_free", "lexicon_hit"):
        sa, sb = paired_slices(a_rows, b_rows, name)
        auc_a = s1.auc_ties(sa.pos, sa.neg)
        auc_b = s1.auc_ties(sb.pos, sb.neg)
        ba, bb, bd = paired_delta(sa, sb, n_boot=args.n_boot)
        ci_a, ci_b, ci_d = s1.ci_of(ba), s1.ci_of(bb), s1.ci_of(bd)
        v = verdict_1b(auc_b - auc_a, ci_d["ci_low"], ci_d["ci_high"])
        verdicts[name] = v
        role = "PRIMARY (C9-15)" if name == "lexicon_free" else "CONTROL (C9-16)"
        print(f"[C9-13] {name}  -- {role}")
        print(f"  AUC control   {auc_a:.6f}  [{ci_a['ci_low']:+.6f}, {ci_a['ci_high']:+.6f}]")
        print(f"  AUC treatment {auc_b:.6f}  [{ci_b['ci_low']:+.6f}, {ci_b['ci_high']:+.6f}]")
        print(f"  paired dAUC   {auc_b - auc_a:+.6f}  "
              f"[{ci_d['ci_low']:+.6f}, {ci_d['ci_high']:+.6f}]   -> {v}")
        payload_slices[name] = {
            "role": role,
            "auc_control": round(auc_a, 6), "auc_control_ci": ci_a,
            "auc_treatment": round(auc_b, 6), "auc_treatment_ci": ci_b,
            "delta_auc": round(auc_b - auc_a, 6), "delta_auc_ci": ci_d,
            "verdict": v,
            "n": {"off": sa.n_pos, "not": sa.n_neg},
            "crossings_gold_OFF": crossings(a_rows, b_rows, name, "OFF"),
            "crossings_gold_NOT": crossings(a_rows, b_rows, name, "NOT"),
            "score_distribution_control": s1.describe(sa.pos),
            "score_distribution_treatment": s1.describe(sb.pos),
        }

    print("\n[C9-14] score movement, gold-OFF rows")
    for name in ("lexicon_free", "lexicon_hit"):
        d = payload_slices[name]
        c = d["crossings_gold_OFF"]
        print(f"  {name:<13} median {d['score_distribution_control']['median']:.4f} -> "
              f"{d['score_distribution_treatment']['median']:.4f}   "
              f"crossings +{c['NOT_to_OFF']} / -{c['OFF_to_NOT']} (net {c['net']:+d})")

    gap_c = payload_slices["lexicon_hit"]["auc_control"] - payload_slices["lexicon_free"]["auc_control"]
    gap_t = payload_slices["lexicon_hit"]["auc_treatment"] - payload_slices["lexicon_free"]["auc_treatment"]
    print(f"\n  slice AUC gap: control {gap_c:+.6f}  treatment {gap_t:+.6f}  "
          f"delta {gap_t - gap_c:+.6f}")

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = "?"

    payload = {
        "run_id": "09_deeper_analysis/stage_1b",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "git_sha": sha,
        "preregistration": "phases/09_deeper_analysis.md C9-12..C9-17, commit 910d21e",
        "scope": "measurement only; no training, no forward pass, no intervention (C9-17)",
        "inputs": {
            "control": {"path": args.control, "run": CONTROL_RUN, "sha256": sha_a,
                        "byte_identical_to_phase01_dump": sha_a == s1.PRED_SHA256},
            "treatment": {"path": args.treatment, "run": TREATMENT_RUN, "sha256": sha_b},
            "provenance_check": "both reproduce results/03_defense/comparison.json (C9-12)",
            "dev_fingerprint": "034415af3a23b388",
            "test_set_touched": False,
        },
        "threshold_fixed_in_advance": {
            "SMALL_DELTA": SMALL_DELTA,
            "justification": "AUC is the fraction of correctly ordered OFF/NOT pairs; "
                             "0.01 of the 565 x 3585 = 2,025,525 pairs in lexicon_free",
        },
        "bootstrap": {"n_boot": args.n_boot, "seed": BOOT_SEED,
                      "method": "paired: rows resampled once per replicate, both "
                                "systems scored on the same rows"},
        "slices": payload_slices,
        "slice_auc_gap": {"control": round(gap_c, 6), "treatment": round(gap_t, 6),
                          "delta": round(gap_t - gap_c, 6)},
        "primary_verdict": verdicts["lexicon_free"],
        "control_verdict": verdicts["lexicon_hit"],
        "recall_deltas_being_explained": {
            "lexicon_free": {"delta": 0.03362831858407078,
                             "ci": [0.005233136699419122, 0.06617711108833776]},
            "lexicon_hit": {"delta": -0.04225352112676062,
                            "ci": [-0.07777857829010572, -0.010924554909219123]},
            "source": "results/03_defense/comparison.json deltas_vs_raw.1a1b_d",
        },
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "stage1b_defense_auc.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwritten -> {out}  ({out.stat().st_size:,} bytes)")
    print("=" * 88)


if __name__ == "__main__":
    main()
