#!/usr/bin/env python3
"""NSosyal B* -- Phase 05: the official Çöltekin test set, touched exactly once.

This is the single-use measurement that produces the reported result. Three
systems are evaluated in ONE pass: the frozen keyword filter, BERTurk raw, and
the +1a+1b+D defense variant.

ABSOLUTE CONSTRAINT
-------------------
The selective-prediction thresholds are NOT derived here. They are read from
`results/04_calibration/calibration.json`, where they were selected on the dev
calibration half in phase 04, and applied to test unchanged. Nothing in this
file computes a threshold, a quantile, or a target coverage from test data. The
coverage that results is whatever it is, and it is reported as achieved rather
than as targeted.

Accounting
----------
`src.data_io.load_coltekin_test` writes an append-only OPEN log before reading
the bytes, and refuses entirely once the SPEND record exists. This script writes
the SPEND record last, only after a complete run. A crash therefore leaves the
open log as evidence and permits one honest retry; a success closes the door.

Usage:
    python phase05_final_test.py --run_final_test 1 \
        --raw_ckpt     <drive>/checkpoints/01_baseline_berturk/best.pt \
        --defense_ckpt <drive>/checkpoints/03_defense/1a1b_d/best.pt \
        --mirror_dir   <drive>/results/05_final_test
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
from src import data_io, evaluate, lexicon

RUN_ID = "05_final_test"
SYSTEMS = ["keyword", "raw", "1a1b_d"]
LABEL = {"keyword": "keyword filter", "raw": "BERTurk raw", "1a1b_d": "+1a+1b+D"}
OPERATING_POINTS = ["high_automation", "high_precision"]


class Tee:
    """Duplicate stdout to a file so the raw run output is preserved verbatim.

    The write-up quotes numbers; this keeps the unedited console output next to
    them, which is what makes the quoting checkable.
    """

    def __init__(self, stream, path):
        self.stream = stream
        self.file = open(path, "w", encoding="utf-8")

    def write(self, s):
        self.stream.write(s)
        self.file.write(s)
        return len(s)

    def flush(self):
        self.stream.flush()
        self.file.flush()

    def close(self):
        self.file.close()


# --------------------------------------------------------------------------
# frozen inputs
# --------------------------------------------------------------------------

def load_frozen_thresholds(path):
    """Read the phase-04 operating points. Never recompute them.

    Returns {system: {point: threshold}} and the provenance block that goes into
    the result file, so a reader can verify the numbers came from dev.
    """
    path = Path(path)
    if not path.exists():
        sys.exit(f"ABORT: {path} not found. The operating-point thresholds are declared "
                 "in phase 04 and cannot be re-derived on test.")
    blob = json.loads(path.read_text(encoding="utf-8"))
    thr, prov = {}, {}
    for sysname in ("raw", "1a1b_d"):
        v = blob["variants"][sysname]["operating_points"]
        thr[sysname] = {p: v[p]["threshold"] for p in OPERATING_POINTS}
        prov[sysname] = {
            p: {"threshold": v[p]["threshold"],
                "selected_on": v[p]["threshold_selected_on"],
                "rule": v[p]["rule"],
                "dev_coverage": v[p]["coverage"],
                "dev_macro_f1": v[p]["macro_f1"],
                "dev_error_rate": v[p]["error_rate"]}
            for p in OPERATING_POINTS}
    return thr, {"source": str(path), "dev_fingerprint": blob["dev_fingerprint"],
                 "points": prov}


def load_dev_reference():
    """Dev numbers for the replication comparison, read from committed records."""
    ref = {}
    p1 = config.RESULTS_DIR / "01_baseline_berturk" / "metrics.json"
    if p1.exists():
        m = json.loads(p1.read_text(encoding="utf-8"))
        b = m.get("berturk", {})
        ref["raw"] = {
            "macro_f1": b.get("overall", {}).get("macro_f1"),
            "off_recall": b.get("overall", {}).get("off_recall"),
            "off_precision": b.get("overall", {}).get("off_precision"),
            "lexicon_hit_off_recall": b.get("lexicon_hit", {}).get("off_recall"),
            "lexicon_free_off_recall": b.get("lexicon_free", {}).get("off_recall"),
            "recall_gap": b.get("recall_gap"),
        }
        ref["keyword"] = m.get("keyword_filter")
    p3 = config.RESULTS_DIR / "03_defense" / "comparison.json"
    if p3.exists():
        c = json.loads(p3.read_text(encoding="utf-8"))
        r = c.get("runs", {}).get("1a1b_d", {})
        ref["1a1b_d"] = {
            "macro_f1": r.get("macro_f1"), "off_recall": r.get("off_recall"),
            "off_precision": r.get("off_precision"),
            "lexicon_hit_off_recall": r.get("lexicon_hit_off_recall"),
            "lexicon_free_off_recall": r.get("lexicon_free_off_recall"),
            "recall_gap": r.get("recall_gap"),
        }
    return ref


# --------------------------------------------------------------------------
# scoring (no model here -- testable without a GPU)
# --------------------------------------------------------------------------

def evaluate_all(gold, slices, preds, probs, thresholds, n_boot, seed):
    """Every phase-05 number, given predictions that are already made."""
    hit = [i for i, s in enumerate(slices) if s == "lexicon_hit"]
    free = [i for i, s in enumerate(slices) if s == "lexicon_free"]
    out = {}

    for name in SYSTEMS:
        p = preds[name]
        s = evaluate.score(gold, p, n_boot=n_boot, seed=seed)
        gap = evaluate.bootstrap_gap_ci(
            [gold[i] for i in hit], [p[i] for i in hit],
            [gold[i] for i in free], [p[i] for i in free],
            metric="off_recall", n_boot=n_boot, seed=seed)

        def slice_block(idx):
            g = [gold[i] for i in idx]
            q = [p[i] for i in idx]
            b = evaluate.score(g, q, with_ci=False)
            return {
                "n": len(idx),
                "support_off": sum(1 for x in g if x == "OFF"),
                "support_not": sum(1 for x in g if x == "NOT"),
                "base_rate_off": sum(1 for x in g if x == "OFF") / len(idx),
                "off_recall": b["off_recall"],
                "off_recall_ci": evaluate.bootstrap_ci(g, q, "off_recall", n_boot, seed),
                "confusion": b["confusion"],
                # Pre-registered phase-01 constraint, still binding: macro-F1 is
                # not comparable ACROSS slices (base rates differ), so it is not
                # reported per slice. Recompute from `confusion` if ever needed
                # strictly within one slice.
                "macro_f1": None,
                "macro_f1_note": "omitted by the phase-01 pre-registered constraint",
            }

        block = {
            "overall": {k: s[k] for k in ("macro_f1", "off_precision", "off_recall",
                                          "n", "support_off", "confusion")},
            "overall_ci": s["ci"],
            "lexicon_hit": slice_block(hit),
            "lexicon_free": slice_block(free),
            "recall_gap": {k: gap[k] for k in
                           ("delta", "ci_low", "ci_high", "excludes_zero")},
        }

        # Selective prediction, only where confidences exist. The keyword filter
        # has no notion of confidence, so it has no risk-coverage curve -- that
        # is a property of the system, not a gap in the measurement.
        if probs.get(name) is not None:
            block["selective"] = {}
            for point in OPERATING_POINTS:
                t = thresholds[name][point]
                b = cal.apply_threshold(gold, p, probs[name], t, slices=slices)
                b["ci"] = cal.bootstrap_operating_point(gold, p, probs[name], t,
                                                        n_boot=n_boot, seed=seed)
                b["threshold_provenance"] = "phase 04, selected on the dev CAL half"
                block["selective"][point] = b
        out[name] = block
    return out


def sentence(b):
    return (f"At {b['coverage']:.1%} automatic coverage the system holds "
            f"{b['macro_f1']:.4f} macro-F1 / {b['error_rate']:.2%} error, "
            f"deferring {1 - b['coverage']:.1%} to human review.")


def print_report(rep, dev):
    r = rep["systems"]
    print("\n" + "=" * 100)
    print(f"PHASE 05 -- OFFICIAL ÇÖLTEKIN TEST SET, {rep['n_test']:,} rows, "
          "single pass")
    print("=" * 100)

    print(f"\n{'system':<18}{'macro-F1':>10}{'95% CI':>22}"
          f"{'OFF-recall':>12}{'OFF-prec':>10}")
    print("-" * 100)
    for name in SYSTEMS:
        o, ci = r[name]["overall"], r[name]["overall_ci"]
        c = ci["macro_f1"]
        span = "[{:.4f}, {:.4f}]".format(c["ci_low"], c["ci_high"])
        print(f"{LABEL[name]:<18}{o['macro_f1']:>10.4f}{span:>22}"
              f"{o['off_recall']:>12.4f}{o['off_precision']:>10.4f}")

    print("\n\nSLICES AND THE RECALL GAP (the phase-01 headline, on held-out data)")
    print("-" * 100)
    print(f"{'system':<18}{'hit n':>8}{'hit OFF-R':>11}{'free n':>8}"
          f"{'free OFF-R':>12}{'gap':>9}{'95% CI':>22}{'excl 0':>8}")
    for name in SYSTEMS:
        b = r[name]
        h, fr, g = b["lexicon_hit"], b["lexicon_free"], b["recall_gap"]
        span = "[{:+.4f}, {:+.4f}]".format(g["ci_low"], g["ci_high"])
        print(f"{LABEL[name]:<18}{h['n']:>8}{h['off_recall']:>11.4f}{fr['n']:>8}"
              f"{fr['off_recall']:>12.4f}{g['delta']:>+9.4f}{span:>22}"
              f"{str(g['excludes_zero']):>8}")

    print("\n\nDEV -> TEST (does the headline replicate?)")
    print("-" * 100)
    print(f"{'system / metric':<34}{'dev':>10}{'test':>10}{'delta':>10}")
    for name in SYSTEMS:
        d = dev.get(name) or {}
        b = r[name]
        rows = [("macro-F1", d.get("macro_f1"), b["overall"]["macro_f1"]),
                ("OFF-recall", d.get("off_recall"), b["overall"]["off_recall"]),
                ("lexicon_hit OFF-recall", d.get("lexicon_hit_off_recall"),
                 b["lexicon_hit"]["off_recall"]),
                ("lexicon_free OFF-recall", d.get("lexicon_free_off_recall"),
                 b["lexicon_free"]["off_recall"])]
        gapd = (d.get("recall_gap") or {}).get("delta")
        rows.append(("RECALL GAP", gapd, b["recall_gap"]["delta"]))
        for label, dv, tv in rows:
            if dv is None:
                print(f"  {LABEL[name] + ' / ' + label:<32}{'-':>10}{tv:>10.4f}{'-':>10}")
            else:
                print(f"  {LABEL[name] + ' / ' + label:<32}{dv:>10.4f}{tv:>10.4f}"
                      f"{tv - dv:>+10.4f}")

    print("\n\nSELECTIVE PREDICTION AT THE FROZEN DEV THRESHOLDS")
    print("(thresholds selected on the dev CAL half in phase 04 and applied "
          "unchanged; coverage is ACHIEVED, not targeted)")
    print("-" * 100)
    for name in ("raw", "1a1b_d"):
        if "selective" not in r[name]:
            continue
        for point in OPERATING_POINTS:
            b = r[name]["selective"][point]
            dp = rep["thresholds"]["points"][name][point]
            print(f"\n  [{LABEL[name]} / {point}]  threshold {b['threshold']:.4f} "
                  f"(dev coverage was {dp['dev_coverage']:.1%})")
            print(f"    {sentence(b)}")
            ci = b["ci"]
            print(f"    coverage   {b['coverage']:.4f} "
                  f"[{ci['coverage']['ci_low']:.4f}, {ci['coverage']['ci_high']:.4f}]")
            print(f"    macro-F1   {b['macro_f1']:.4f} "
                  f"[{ci['macro_f1']['ci_low']:.4f}, {ci['macro_f1']['ci_high']:.4f}]"
                  f"   (dev {dp['dev_macro_f1']:.4f})")
            print(f"    error rate {b['error_rate']:.4f} "
                  f"[{ci['error_rate']['ci_low']:.4f}, {ci['error_rate']['ci_high']:.4f}]"
                  f"   (dev {dp['dev_error_rate']:.4f})")
            print(f"    deferred error rate {b['deferred_error_rate']:.4f}   "
                  f"capture lift {b['capture_lift']:.2f}x   "
                  f"({b['error_capture_share']:.1%} of all errors in "
                  f"{1 - b['coverage']:.1%} of rows)")
            print(f"    {'slice':<14}{'rows':>7}{'defer':>7}{'defer%':>9}"
                  f"{'%of defs':>10}{'auto err':>10}{'def err':>9}")
            for tag, s in sorted(b["by_slice"].items()):
                print(f"    {tag:<14}{s['n_rows']:>7}{s['n_deferred']:>7}"
                      f"{s['deferral_rate']:>9.1%}{s['share_of_deferrals']:>10.1%}"
                      f"{(s['auto_error_rate'] or 0):>10.2%}"
                      f"{(s['deferred_error_rate'] or 0):>9.2%}")


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_final_test", type=int, default=0,
                    help="must be 1; the guard exists so this cannot happen by accident")
    ap.add_argument("--raw_ckpt", required=True)
    ap.add_argument("--defense_ckpt", required=True)
    ap.add_argument("--calibration", default=None)
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--mirror_dir", default=None)
    ap.add_argument("--model", default=config.MODEL_NAME if hasattr(config, "MODEL_NAME")
                    else "dbmdz/bert-base-turkish-cased")
    ap.add_argument("--batch_size", type=int, default=64)
    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n_boot", type=int, default=1000)
    args = ap.parse_args()

    if args.run_final_test != 1:
        sys.exit("Refusing to run: pass --run_final_test 1 explicitly.\n"
                 "The official test set is touched exactly once (briefing S7.2).")
    if config.TEST_SPEND_RECORD.exists():
        sys.exit(f"Refusing to run: the test set is already SPENT "
                 f"({config.TEST_SPEND_RECORD}).")

    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    out_dir.mkdir(parents=True, exist_ok=True)
    tee = Tee(sys.stdout, out_dir / "raw_output.txt")
    sys.stdout = tee

    started = datetime.now()
    from phase01_baseline import assert_trainable_runtime, git_sha

    # --- frozen inputs, read BEFORE the test set ---------------------------
    thresholds, prov = load_frozen_thresholds(
        args.calibration or config.RESULTS_DIR / "04_calibration" / "calibration.json")
    dev_ref = load_dev_reference()
    print("Frozen thresholds loaded from phase 04 (NOT re-derived here):")
    for s in ("raw", "1a1b_d"):
        for p in OPERATING_POINTS:
            d = prov["points"][s][p]
            print(f"  {LABEL[s]:<14} {p:<16} threshold {d['threshold']:.4f}  "
                  f"[{d['selected_on']}]  dev coverage {d['dev_coverage']:.1%}")

    lex = lexicon.load_lexicon()
    assert_trainable_runtime(allow_cpu=False)

    # --- the single read ---------------------------------------------------
    print("\nOpening the official test set (this is the one permitted read)...")
    test_rows = data_io.load_coltekin_test(run_final_test=True)
    hashes = {"test_sha256": data_io.sha256(config.COLTEKIN_TEST),
              "gold_sha256": data_io.sha256(config.COLTEKIN_GOLD),
              "lexicon_sha256": data_io.sha256(config.LEXICON_PATH)}
    gold = [r["label"] for r in test_rows]
    slices = evaluate.tag_slices(test_rows, lex)
    print(f"  {len(test_rows):,} rows  "
          f"{{'NOT': {sum(1 for g in gold if g == 'NOT')}, "
          f"'OFF': {sum(1 for g in gold if g == 'OFF')}}}")
    print(f"  slices: lexicon_hit {slices.count('lexicon_hit'):,} / "
          f"lexicon_free {slices.count('lexicon_free'):,}")
    print(f"  sha256: test {hashes['test_sha256'][:16]}  "
          f"gold {hashes['gold_sha256'][:16]}")

    # --- predictions -------------------------------------------------------
    import torch
    from src import models

    preds = {"keyword": ["OFF" if t == "lexicon_hit" else "NOT" for t in slices]}
    probs = {"keyword": None}
    for name, ckpt in (("raw", args.raw_ckpt), ("1a1b_d", args.defense_ckpt)):
        print(f"\nloading {name} <- {ckpt}")
        tokenizer, model = models.load_model(args.model)
        state = torch.load(ckpt, map_location="cuda", weights_only=False)
        model.load_state_dict(state["model"])
        model.to("cuda")
        print(f"  checkpoint epoch {state.get('epoch')}, "
              f"dev macro-F1 {state.get('dev_macro_f1')}")
        p, po = models.predict(model, tokenizer, test_rows,
                               batch_size=args.batch_size, max_len=args.max_len)
        preds[name], probs[name] = p, po
        del model
        torch.cuda.empty_cache()

    # --- score -------------------------------------------------------------
    systems = evaluate_all(gold, slices, preds, probs, thresholds,
                           args.n_boot, args.seed)
    report = {
        "run_id": RUN_ID,
        "git_sha": git_sha(),
        "started_at": started.isoformat(timespec="seconds"),
        "n_test": len(test_rows),
        "hashes": hashes,
        "official_test_set_touched": True,
        "single_pass": True,
        "thresholds": prov,
        "thresholds_re_derived_on_test": False,
        "dev_reference": dev_ref,
        "systems": systems,
        "environment": models.environment_info(),
        "seed": args.seed,
        "n_boot": args.n_boot,
    }
    print_report(report, dev_ref)

    # --- outputs -----------------------------------------------------------
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(out_dir / "test_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "text", "gold", "slice",
                    "pred_keyword", "pred_raw", "p_off_raw",
                    "pred_1a1b_d", "p_off_1a1b_d"])
        for i, r in enumerate(test_rows):
            w.writerow([r["id"], r["text"], gold[i], slices[i],
                        preds["keyword"][i], preds["raw"][i], f"{probs['raw'][i]:.6f}",
                        preds["1a1b_d"][i], f"{probs['1a1b_d'][i]:.6f}"])
    print(f"\nwritten -> {out_dir / 'metrics.json'}")
    print(f"written -> {out_dir / 'test_predictions.csv'}")
    print(f"written -> {out_dir / 'raw_output.txt'} (verbatim console output)")

    if args.mirror_dir:
        from phase01_baseline import mirror_outputs
        mirror_outputs(out_dir, Path(args.mirror_dir),
                       required=("metrics.json", "test_predictions.csv", "raw_output.txt"),
                       marker="metrics.json")

    # --- spend the resource, LAST ------------------------------------------
    spend = {
        "spent_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": RUN_ID,
        "git_sha": report["git_sha"],
        "results_dir": str(out_dir),
        "n_test": len(test_rows),
        "hashes": hashes,
        "systems_evaluated": SYSTEMS,
        "thresholds_source": prov["source"],
        "note": ("The official Çöltekin test set has been used for its single "
                 "permitted measurement. src.data_io.load_coltekin_test refuses "
                 "while this file exists. Deleting it is a project-lead decision "
                 "and must be recorded in docs/RESULTS_LOG.md."),
    }
    config.TEST_SPEND_RECORD.parent.mkdir(parents=True, exist_ok=True)
    config.TEST_SPEND_RECORD.write_text(json.dumps(spend, indent=2), encoding="utf-8")
    print("\n" + "=" * 100)
    print(f"TEST SET MARKED SPENT -> {config.TEST_SPEND_RECORD}")
    print("Further calls to load_coltekin_test() will refuse, on this machine and "
          "on any clone of this commit.")
    print("=" * 100)
    sys.stdout = tee.stream
    tee.close()


if __name__ == "__main__":
    main()
