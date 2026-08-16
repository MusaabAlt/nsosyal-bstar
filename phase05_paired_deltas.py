#!/usr/bin/env python3
"""NSosyal B* -- Phase 05 addendum: paired deltas on the test predictions.

Reads `results/05_final_test/test_predictions.csv` ONLY. It does not open the
official test set -- that resource is spent, and `load_coltekin_test` now
refuses. Every number here is a derived statistic of the single pass that
already happened, in the same way the write-up's tables are.

Why this exists: the headline table reports raw 0.8095 and +1a+1b+D 0.8093 side
by side, and two point estimates that close together are not an answer to "is
there a difference". The two systems were scored on identical rows, so the CI of
their difference must come from resampling rows once and scoring BOTH systems on
that resample.

Usage:
    python phase05_paired_deltas.py --mirror_dir <drive>/results/05_final_test
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
from src import evaluate

RUN_ID = "05_final_test"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default=None)
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--mirror_dir", default=None)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=config.SEED)
    args = ap.parse_args()

    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    path = Path(args.pred or out_dir / "test_predictions.csv")
    if not path.exists():
        sys.exit(f"ABORT: {path} not found. Run phase05_final_test.py first.")

    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    gold = [r["gold"] for r in rows]
    slices = [r["slice"] for r in rows]
    raw = [r["pred_raw"] for r in rows]
    dfs = [r["pred_1a1b_d"] for r in rows]
    hit = [i for i, s in enumerate(slices) if s == "lexicon_hit"]
    free = [i for i, s in enumerate(slices) if s == "lexicon_free"]

    def paired(idx, metric):
        g = [gold[i] for i in idx] if idx is not None else gold
        a = [dfs[i] for i in idx] if idx is not None else dfs
        b = [raw[i] for i in idx] if idx is not None else raw
        d = evaluate.bootstrap_delta_ci(g, a, b, metric, args.n_boot, args.seed)
        return {k: d[k] for k in ("delta", "ci_low", "ci_high", "excludes_zero")}

    rep = {
        "run_id": RUN_ID,
        "note": ("Paired deltas (+1a+1b+D minus BERTurk raw) on the official test "
                 "set, computed from the saved predictions of the single pass. "
                 "The test set itself was not reopened."),
        "n_rows": len(rows),
        "n_boot": args.n_boot,
        "seed": args.seed,
        "paired": True,
        "deltas_defense_minus_raw": {
            "macro_f1": paired(None, "macro_f1"),
            "off_recall": paired(None, "off_recall"),
            "off_precision": paired(None, "off_precision"),
            "lexicon_hit_off_recall": paired(hit, "off_recall"),
            "lexicon_free_off_recall": paired(free, "off_recall"),
        },
    }

    print("\n" + "=" * 88)
    print("PHASE 05 ADDENDUM -- PAIRED DELTAS, +1a+1b+D minus BERTurk raw, on TEST")
    print("(same rows for both systems; CI excluding 0 = a real difference)")
    print("=" * 88)
    for k, d in rep["deltas_defense_minus_raw"].items():
        star = "   <-- CI excludes 0" if d["excludes_zero"] else ""
        print(f"  {k:<26} {d['delta']:+.4f}  95% CI "
              f"[{d['ci_low']:+.4f}, {d['ci_high']:+.4f}]{star}")

    dest = out_dir / "paired_deltas.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"\nwritten -> {dest}")

    if args.mirror_dir:
        import shutil
        m = Path(args.mirror_dir)
        m.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, m / dest.name)
        print(f"mirrored -> {m / dest.name}")


if __name__ == "__main__":
    main()
