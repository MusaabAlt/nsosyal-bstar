#!/usr/bin/env python3
"""NSosyal B* -- Phase 03 step 4: compare the four defense variants.

Reads the per-run dev predictions and reports every required metric for all four
runs together, with PAIRED bootstrap CIs on each delta against BERTurk raw.

Paired matters: the four systems are scored on identical dev rows, so the CI of a
difference must come from resampling rows once and scoring both systems on that
resample. Comparing two independently-computed CIs would overstate the
uncertainty of the difference.

Reports deltas regardless of sign. Reads predictions only -- it cannot trigger a
model load or a test-set read.

Usage:
    python phase03_compare.py --runs_dir <results>/03_defense
"""

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import augment, evaluate, lexicon

VARIANTS = ["raw", "1a", "1a1b", "1a1b_d"]
LABEL = {"raw": "BERTurk raw", "1a": "+1a", "1a1b": "+1a+1b", "1a1b_d": "+1a+1b+D"}


def load_run(runs_dir, variant):
    path = Path(runs_dir) / f"run_{variant}" / "dev_predictions.csv"
    if not path.exists():
        sys.exit(f"missing {path} -- run phase03_train_defense.py --variant {variant} first")
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs_dir", default=None)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir or config.RESULTS_DIR / "03_defense")
    lex = lexicon.load_lexicon()

    data = {v: load_run(runs_dir, v) for v in VARIANTS}
    base = data["raw"]
    gold = [r["gold"] for r in base]
    slices = [r["slice"] for r in base]
    hit_idx = [i for i, s in enumerate(slices) if s == "lexicon_hit"]
    free_idx = [i for i, s in enumerate(slices) if s == "lexicon_free"]

    for v in VARIANTS:                       # identical row order is a precondition
        if [r["row_id"] for r in data[v]] != [r["row_id"] for r in base]:
            sys.exit(f"ABORT: run_{v} rows are not in the same order as run_raw; "
                     "a paired comparison would be meaningless.")

    preds = {v: [r["pred"] for r in data[v]] for v in VARIANTS}
    rep = {"runs": {}, "deltas_vs_raw": {}, "n_boot": args.n_boot, "seed": args.seed,
           "paired": True, "dev_rows": len(base)}

    def slice_recall(v, idx):
        return evaluate.score([gold[i] for i in idx], [preds[v][i] for i in idx],
                              with_ci=False)["off_recall"]

    def hit_fp_rate(v):
        c = evaluate.score([gold[i] for i in hit_idx], [preds[v][i] for i in hit_idx],
                           with_ci=False)["confusion"]
        return c["fp"] / max(1, c["fp"] + c["tn"]), c

    def no_prof_fp(v):
        return sum(1 for r, p in zip(base, preds[v])
                   if r["gold"] == "NOT" and p == "OFF"
                   and not augment._profane_tokens(r["text"], lex))

    for v in VARIANTS:
        s = evaluate.score(gold, preds[v], with_ci=False)
        fpr, hc = hit_fp_rate(v)
        gap = evaluate.bootstrap_gap_ci(
            [gold[i] for i in hit_idx], [preds[v][i] for i in hit_idx],
            [gold[i] for i in free_idx], [preds[v][i] for i in free_idx],
            metric="off_recall", n_boot=args.n_boot, seed=args.seed)
        rep["runs"][v] = {
            "macro_f1": s["macro_f1"], "off_recall": s["off_recall"],
            "off_precision": s["off_precision"],
            "lexicon_free_off_recall": slice_recall(v, free_idx),
            "lexicon_hit_off_recall": slice_recall(v, hit_idx),
            "lexicon_hit_fp_rate": fpr, "lexicon_hit_confusion": hc,
            "recall_gap": {k: gap[k] for k in ("delta", "ci_low", "ci_high", "excludes_zero")},
            "false_positives_total": sum(1 for g, p in zip(gold, preds[v]) if g == "NOT" and p == "OFF"),
            "false_positives_no_profanity": no_prof_fp(v),
        }

    for v in VARIANTS[1:]:
        d = {}
        d["macro_f1"] = evaluate.bootstrap_delta_ci(gold, preds[v], preds["raw"], "macro_f1",
                                                    args.n_boot, args.seed)
        d["lexicon_free_off_recall"] = evaluate.bootstrap_delta_ci(
            [gold[i] for i in free_idx], [preds[v][i] for i in free_idx],
            [preds["raw"][i] for i in free_idx], "off_recall", args.n_boot, args.seed)
        d["lexicon_hit_off_recall"] = evaluate.bootstrap_delta_ci(
            [gold[i] for i in hit_idx], [preds[v][i] for i in hit_idx],
            [preds["raw"][i] for i in hit_idx], "off_recall", args.n_boot, args.seed)
        rep["deltas_vs_raw"][v] = {k: {kk: vv[kk] for kk in
                                       ("delta", "ci_low", "ci_high", "excludes_zero")}
                                   for k, vv in d.items()}

    # ---- print ------------------------------------------------------------
    w = 22
    print("\n" + "=" * 104)
    print("PHASE 03 -- FOUR VARIANTS ON THE FROZEN DEV SPLIT (official test set untouched)")
    print("=" * 104)
    print(f"{'metric':<28}" + "".join(f"{LABEL[v]:>{w}}" for v in VARIANTS))
    print("-" * 104)
    rows_to_print = [
        ("overall macro-F1", lambda v: f"{rep['runs'][v]['macro_f1']:.4f}"),
        ("lexicon_free OFF-recall", lambda v: f"{rep['runs'][v]['lexicon_free_off_recall']:.4f}"),
        ("lexicon_hit OFF-recall", lambda v: f"{rep['runs'][v]['lexicon_hit_off_recall']:.4f}"),
        ("lexicon_hit FP rate", lambda v: f"{rep['runs'][v]['lexicon_hit_fp_rate']:.4f}"),
        ("recall gap", lambda v: f"{rep['runs'][v]['recall_gap']['delta']:+.4f}"),
        ("false positives (total)", lambda v: str(rep["runs"][v]["false_positives_total"])),
        ("  of which no profanity", lambda v: str(rep["runs"][v]["false_positives_no_profanity"])),
    ]
    for name, fn in rows_to_print:
        print(f"{name:<28}" + "".join(f"{fn(v):>{w}}" for v in VARIANTS))

    print("\n" + "=" * 104)
    print("PAIRED DELTAS vs BERTurk raw  (same rows for both systems; CI excluding 0 = real change)")
    print("=" * 104)
    for v in VARIANTS[1:]:
        print(f"\n{LABEL[v]}")
        for metric, dd in rep["deltas_vs_raw"][v].items():
            star = "  <-- CI excludes 0" if dd["excludes_zero"] else ""
            print(f"  {metric:<26} {dd['delta']:+.4f}  95% CI "
                  f"[{dd['ci_low']:+.4f}, {dd['ci_high']:+.4f}]{star}")

    out = Path(args.out or runs_dir / "comparison.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"\nwritten -> {out}")


if __name__ == "__main__":
    main()
