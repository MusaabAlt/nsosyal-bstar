#!/usr/bin/env python3
"""NSosyal B* -- Phase 04: calibration and risk-coverage (selective prediction).

Reads prediction dumps only. No model is loaded, nothing is trained, and no
forward pass happens -- so this runs on a CPU in seconds and cannot touch the
official test set even by accident.

Protocol is pre-registered in phases/04_calibration.md:
  C4-1  dev halved stratified (seed 42) into CAL / EVAL; T fit on CAL, reported on EVAL
  C4-2  ECE over 15 equal-width bins on max(p, 1-p), with 10/20-bin sensitivity
  C4-3  risk-coverage must be invariant to temperature -- verified, not assumed
  C4-4  operating-point thresholds selected on CAL, metrics and CIs from EVAL
  C4-5  6dp dumps: saturated rows are clipped and counted
  C4-6  deferral broken down by slice, reported regardless of sign
  C4-8  the two operating points are fixed by rule, not read off the curve

Usage:
    python phase04_calibration.py \
        --raw_pred     <...>/run_raw/dev_predictions.csv \
        --defense_pred <...>/run_1a1b_d/dev_predictions.csv \
        --mirror_dir   <drive>/results/04_calibration
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import calibration as cal
from src import data_io, evaluate

RUN_ID = "04_calibration"
DEV_FINGERPRINT = "034415af3a23b388"
COVERAGES = [1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50]

# C4-8, fixed before the curve was seen.
HIGH_AUTOMATION_COVERAGE = 0.90
HIGH_PRECISION_ERROR_TARGET = 0.05


def load_predictions(path):
    """Load a dump and verify it describes the frozen dev split.

    The fingerprint is recomputed from the row ids in the file itself, so this
    check needs neither the corpus nor the split file -- a dump that came from a
    different dev set is rejected here rather than silently averaged in.
    """
    path = Path(path)
    if not path.exists():
        sys.exit(f"ABORT: missing prediction dump {path}")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows:
        sys.exit(f"ABORT: {path} is empty")

    fp = data_io.dev_fingerprint([{"id": r["row_id"]} for r in rows])
    if not fp.startswith(DEV_FINGERPRINT):
        sys.exit(f"ABORT: {path} has dev fingerprint {fp[:16]}, expected {DEV_FINGERPRINT}.\n"
                 "Every phase 01-03 number was measured on the frozen split; a different "
                 "dev set makes this analysis incomparable to all of them.")

    out = {
        "path": str(path),
        "row_id": [r["row_id"] for r in rows],
        "gold": [r["gold"] for r in rows],
        "pred": [r["pred"] for r in rows],
        "p_off": [float(r["confidence"]) for r in rows],
        "slice": [r["slice"] for r in rows],
        "n": len(rows),
        "dev_fingerprint": fp,
    }
    # The dumped `pred` must be argmax of the dumped probability. If it is not,
    # the two columns came from different places and everything below is void.
    mismatch = sum(1 for p, q in zip(out["p_off"], out["pred"])
                   if ("OFF" if p >= 0.5 else "NOT") != q)
    if mismatch:
        sys.exit(f"ABORT: {path} has {mismatch} rows where pred != argmax(confidence). "
                 "The probability and the decision disagree; neither can be trusted.")
    return out


def cal_eval_split(data, seed):
    """C4-1: stratified 50/50 halving of dev, reusing the project splitter.

    Reused rather than reimplemented so the sort-by-id-then-shuffle discipline
    is identical to every other split in this project.
    """
    rows = [{"id": rid, "label": g} for rid, g in zip(data["row_id"], data["gold"])]
    cal_rows, eval_rows = data_io.stratified_split(rows, dev_fraction=0.5, seed=seed)
    pos = {rid: i for i, rid in enumerate(data["row_id"])}
    return ([pos[r["id"]] for r in cal_rows], [pos[r["id"]] for r in eval_rows])


def subset(data, idx):
    return {k: [data[k][i] for i in idx] for k in ("gold", "pred", "p_off", "slice")}


def analyse(data, variant, seed, n_boot):
    """The whole phase-04 block for one variant."""
    cal_idx, eval_idx = cal_eval_split(data, seed)
    C, E = subset(data, cal_idx), subset(data, eval_idx)
    rep = {"variant": variant, "source": data["path"], "n_dev": data["n"],
           "dev_fingerprint": data["dev_fingerprint"],
           "n_cal": len(cal_idx), "n_eval": len(eval_idx)}

    # --- C4-5 rounding exposure -------------------------------------------
    rep["saturated_rows"] = {
        "dev": cal.saturated_count(data["p_off"]),
        "cal": cal.saturated_count(C["p_off"]),
        "eval": cal.saturated_count(E["p_off"]),
        "note": "P(OFF) dumped at 6dp; 0.000000/1.000000 clipped to 5e-7 and counted.",
    }

    # --- 1. calibration ----------------------------------------------------
    fit = cal.fit_temperature(C["gold"], C["p_off"])
    T = fit["temperature"]
    E_scaled = [cal.apply_temperature(p, T) for p in E["p_off"]]

    rep["temperature_fit"] = fit
    rep["ece"] = {
        "before": {str(nb): cal.ece(E["gold"], E["p_off"], nb) for nb in (10, 15, 20)},
        "after": {str(nb): cal.ece(E["gold"], E_scaled, nb) for nb in (10, 15, 20)},
    }
    rep["reliability"] = {
        "before": cal.reliability_bins(E["gold"], E["p_off"], 15),
        "after": cal.reliability_bins(E["gold"], E_scaled, 15),
    }
    gap = rep["ece"]["before"]["15"]["signed_gap"]
    rep["direction"] = ("overconfident" if gap < 0 else
                        "underconfident" if gap > 0 else "neither")

    # --- 2. risk-coverage on full dev (no parameter is fit for this) --------
    rep["risk_coverage"] = cal.risk_coverage(data["gold"], data["pred"],
                                             data["p_off"], COVERAGES)

    ok, worst = cal.verify_rc_invariance(data["gold"], data["pred"], data["p_off"],
                                         T, COVERAGES)
    rep["rc_invariance_check"] = {"holds": ok, "max_abs_diff": worst,
                                  "temperature": T}
    if not ok:
        sys.exit(f"ABORT: risk-coverage moved by {worst} under temperature scaling. "
                 "C4-3 says it cannot; one of the two implementations is wrong.")

    # --- 3. operating points, thresholds from CAL (C4-4, C4-8) -------------
    cal_rc = cal.risk_coverage(C["gold"], C["pred"], C["p_off"], COVERAGES)
    reachable = [r for r in cal_rc if r["error_rate"] <= HIGH_PRECISION_ERROR_TARGET]
    if reachable:
        hp_cov = max(r["target_coverage"] for r in reachable)
        hp_note = f"largest grid coverage whose CAL error rate <= {HIGH_PRECISION_ERROR_TARGET:.1%}"
    else:
        hp_cov = min(COVERAGES)
        best = min(r["error_rate"] for r in cal_rc)
        hp_note = (f"TARGET UNREACHABLE: no coverage on the grid reaches "
                   f"{HIGH_PRECISION_ERROR_TARGET:.1%} CAL error (best {best:.4f} at "
                   f"{min(COVERAGES):.0%}); reporting the {min(COVERAGES):.0%} point instead")

    rep["operating_points"] = {}
    for name, cov, note in (
        ("high_automation", HIGH_AUTOMATION_COVERAGE, "fixed at 90% coverage, declared in advance"),
        ("high_precision", hp_cov, hp_note),
    ):
        thr = cal.threshold_for_coverage(C["p_off"], cov)
        block = cal.apply_threshold(E["gold"], E["pred"], E["p_off"], thr, slices=E["slice"])
        block["ci"] = cal.bootstrap_operating_point(E["gold"], E["pred"], E["p_off"],
                                                    thr, n_boot=n_boot, seed=seed)
        block["target_coverage"] = cov
        block["threshold_selected_on"] = "CAL"
        block["metrics_measured_on"] = "EVAL"
        block["rule"] = note
        rep["operating_points"][name] = block

    # --- 4. deferral by slice, at both points, on full dev too -------------
    rep["deferral_full_dev"] = {}
    for name in ("high_automation", "high_precision"):
        thr = rep["operating_points"][name]["threshold"]
        rep["deferral_full_dev"][name] = cal.apply_threshold(
            data["gold"], data["pred"], data["p_off"], thr, slices=data["slice"])
    return rep


def sentence(name, block):
    """Deliverable 3: the operating point as a complete sentence."""
    return (f"At {block['coverage']:.1%} automatic coverage the system holds "
            f"{block['macro_f1']:.4f} macro-F1 / {block['error_rate']:.2%} error, "
            f"deferring {1 - block['coverage']:.1%} to human review.")


def print_report(rep):
    v = rep["variant"]
    print("\n" + "=" * 96)
    print(f"PHASE 04 -- {v}   (dev {rep['dev_fingerprint'][:16]}, "
          f"CAL {rep['n_cal']} / EVAL {rep['n_eval']})")
    print("=" * 96)

    f = rep["temperature_fit"]
    print(f"\nTemperature fit on CAL: T = {f['temperature']:.4f}   "
          f"NLL {f['nll_before']:.4f} -> {f['nll_after']:.4f}")
    if f.get("at_boundary"):
        print(f"  [WARN] T sits on the search bound [{f['search_lo']}, {f['search_hi']}]. "
              "The NLL is still falling at the edge, so this is a failed bracket, not a\n"
              "         fitted temperature -- it means the scores carry little information "
              "about the labels. Do NOT report it as a calibration temperature.")
    print(f"Model is {rep['direction'].upper()} "
          f"(signed gap accuracy-confidence = {rep['ece']['before']['15']['signed_gap']:+.4f})")
    print(f"Saturated (6dp) rows: dev {rep['saturated_rows']['dev']} / {rep['n_dev']}")

    print(f"\n{'ECE':<10}{'10 bins':>12}{'15 bins':>12}{'20 bins':>12}")
    for when in ("before", "after"):
        print(f"  {when:<8}" + "".join(f"{rep['ece'][when][str(nb)]['ece']:>12.4f}"
                                       for nb in (10, 15, 20)))
    print(f"  {'MCE(15)':<8}{rep['ece']['before']['15']['mce']:>12.4f}"
          f"{rep['ece']['after']['15']['mce']:>24.4f}")

    print("\nReliability (EVAL, 15 bins, before -> after temperature)")
    print(f"  {'bin':<14}{'n':>6}{'acc':>9}{'conf':>9}{'gap':>9}   |"
          f"{'n':>6}{'acc':>9}{'conf':>9}{'gap':>9}")
    for b0, b1 in zip(rep["reliability"]["before"], rep["reliability"]["after"]):
        rng = f"[{b0['lo']:.3f},{b0['hi']:.3f})"
        if b0["n"] == 0 and b1["n"] == 0:
            continue
        def fmt(b):
            if b["n"] == 0:
                return f"{0:>6}{'-':>9}{'-':>9}{'-':>9}"
            return (f"{b['n']:>6}{b['accuracy']:>9.4f}"
                    f"{b['mean_confidence']:>9.4f}{b['gap']:>+9.4f}")
        print(f"  {rng:<14}{fmt(b0)}   |{fmt(b1)}")

    print("\nRisk-coverage (full dev; invariant to temperature, verified "
          f"max diff {rep['rc_invariance_check']['max_abs_diff']:.2e})")
    print(f"  {'coverage':>9}{'n_auto':>8}{'deferred':>10}{'macro-F1':>10}"
          f"{'error':>9}{'OFF-R':>9}{'thresh':>9}")
    for r in rep["risk_coverage"]:
        print(f"  {r['coverage']:>9.1%}{r['n_auto']:>8}{r['n_deferred']:>10}"
              f"{r['macro_f1']:>10.4f}{r['error_rate']:>9.2%}"
              f"{r['off_recall']:>9.4f}{r['threshold']:>9.4f}")

    print("\nOperating points (threshold from CAL, metrics from EVAL, "
          "1,000-resample bootstrap)")
    for name, b in rep["operating_points"].items():
        print(f"\n  [{name}]  target {b['target_coverage']:.0%}  "
              f"threshold {b['threshold']:.4f}")
        print(f"    rule: {b['rule']}")
        print(f"    {sentence(name, b)}")
        ci = b["ci"]
        print(f"    coverage   {b['coverage']:.4f} [{ci['coverage']['ci_low']:.4f}, "
              f"{ci['coverage']['ci_high']:.4f}]")
        print(f"    macro-F1   {b['macro_f1']:.4f} [{ci['macro_f1']['ci_low']:.4f}, "
              f"{ci['macro_f1']['ci_high']:.4f}]")
        print(f"    error rate {b['error_rate']:.4f} [{ci['error_rate']['ci_low']:.4f}, "
              f"{ci['error_rate']['ci_high']:.4f}]")
        print(f"    deferred error rate {b['deferred_error_rate']:.4f}  "
              f"capture lift {b['capture_lift']:.2f}x  "
              f"({b['error_capture_share']:.1%} of all errors in "
              f"{1 - b['coverage']:.1%} of rows)")

    print("\nDeferral by slice (full dev)")
    for name, blk in rep["deferral_full_dev"].items():
        print(f"\n  [{name}]  {blk['n_deferred']} deferred of {rep['n_dev']}")
        print(f"    {'slice':<14}{'rows':>7}{'defer':>7}{'defer%':>9}"
              f"{'%of defs':>10}{'auto err':>10}{'def err':>9}{'err capt':>10}")
        for tag, s in sorted(blk["by_slice"].items()):
            print(f"    {tag:<14}{s['n_rows']:>7}{s['n_deferred']:>7}"
                  f"{s['deferral_rate']:>9.1%}{s['share_of_deferrals']:>10.1%}"
                  f"{s['auto_error_rate']:>10.2%}"
                  f"{(s['deferred_error_rate'] or 0):>9.2%}"
                  f"{s['error_capture_share']:>10.1%}")


def main():
    ap = argparse.ArgumentParser()
    d = config.RESULTS_DIR / "03_defense"
    ap.add_argument("--raw_pred", default=str(d / "run_raw" / "dev_predictions.csv"))
    ap.add_argument("--defense_pred", default=str(d / "run_1a1b_d" / "dev_predictions.csv"))
    ap.add_argument("--baseline_pred", default=None,
                    help="optional phase-01 dump; asserted identical to --raw_pred")
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--mirror_dir", default=None)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n_boot", type=int, default=1000)
    args = ap.parse_args()

    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = load_predictions(args.raw_pred)
    dfs = load_predictions(args.defense_pred)
    if raw["row_id"] != dfs["row_id"]:
        sys.exit("ABORT: the two dumps are not in the same row order; every paired "
                 "statement below would be meaningless.")

    identical_note = None
    if args.baseline_pred:
        base = load_predictions(args.baseline_pred)
        same = (base["pred"] == raw["pred"] and base["p_off"] == raw["p_off"]
                and base["row_id"] == raw["row_id"])
        identical_note = ("phase-01 dump is identical to run_raw" if same else
                          "WARNING: phase-01 dump DIFFERS from run_raw")
        print(identical_note)
        if not same:
            sys.exit("ABORT: run_raw was supposed to reproduce phase 01 exactly.")

    report = {
        "run_id": RUN_ID,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "n_boot": args.n_boot,
        "dev_fingerprint": raw["dev_fingerprint"],
        "official_test_set_touched": False,
        "protocol": "phases/04_calibration.md (C4-1..C4-8)",
        "coverage_grid": COVERAGES,
        "baseline_identity_check": identical_note,
        "variants": {},
    }
    for variant, data in (("raw", raw), ("1a1b_d", dfs)):
        rep = analyse(data, variant, args.seed, args.n_boot)
        print_report(rep)
        report["variants"][variant] = rep

    # Paired statement: did the defense change calibration?
    a, b = report["variants"]["raw"], report["variants"]["1a1b_d"]
    report["defense_vs_raw"] = {
        "temperature": {"raw": a["temperature_fit"]["temperature"],
                        "1a1b_d": b["temperature_fit"]["temperature"]},
        "ece_before_15": {"raw": a["ece"]["before"]["15"]["ece"],
                          "1a1b_d": b["ece"]["before"]["15"]["ece"]},
        "ece_after_15": {"raw": a["ece"]["after"]["15"]["ece"],
                         "1a1b_d": b["ece"]["after"]["15"]["ece"]},
        "delta_ece_before_15": b["ece"]["before"]["15"]["ece"] - a["ece"]["before"]["15"]["ece"],
    }
    print("\n" + "=" * 96)
    print("DEFENSE vs RAW -- calibration only")
    print("=" * 96)
    dv = report["defense_vs_raw"]
    print(f"  temperature   raw {dv['temperature']['raw']:.4f}   "
          f"+1a+1b+D {dv['temperature']['1a1b_d']:.4f}")
    print(f"  ECE (15, uncalibrated)  raw {dv['ece_before_15']['raw']:.4f}   "
          f"+1a+1b+D {dv['ece_before_15']['1a1b_d']:.4f}   "
          f"delta {dv['delta_ece_before_15']:+.4f}")
    print(f"  ECE (15, temperature-scaled)  raw {dv['ece_after_15']['raw']:.4f}   "
          f"+1a+1b+D {dv['ece_after_15']['1a1b_d']:.4f}")

    path = out_dir / "calibration.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nwritten -> {path}")

    if args.mirror_dir:
        from phase01_baseline import mirror_outputs
        mirror_outputs(out_dir, Path(args.mirror_dir),
                       required=("calibration.json",), marker="calibration.json")


if __name__ == "__main__":
    main()
