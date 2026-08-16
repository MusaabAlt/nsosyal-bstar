#!/usr/bin/env python3
"""Dry-run the phase 05 scoring and report path on synthetic predictions.

Phase 05 runs ONCE against the official test set. A KeyError in the report path
discovered after the forward pass would mean either losing the run or touching
the resource twice, so the whole non-model half is exercised here first.

This never calls load_coltekin_test and never writes a spend record.

Usage:  python tests/_dryrun_phase05.py
"""

import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase05_final_test as drv
from src import calibration as cal

N = 3000


def main():
    rng = random.Random(5)
    gold, slices, preds, probs = [], [], {"keyword": [], "raw": [], "1a1b_d": []}, \
        {"keyword": None, "raw": [], "1a1b_d": []}

    for i in range(N):
        tag = "lexicon_hit" if rng.random() < 0.13 else "lexicon_free"
        slices.append(tag)
        # OFF is likelier inside lexicon_hit, mirroring the real base rates.
        g = "OFF" if rng.random() < (0.58 if tag == "lexicon_hit" else 0.14) else "NOT"
        gold.append(g)
        preds["keyword"].append("OFF" if tag == "lexicon_hit" else "NOT")
        for name, skill in (("raw", 2.2), ("1a1b_d", 1.9)):
            z = rng.gauss(skill if g == "OFF" else -skill, 2.0)
            p = cal.sigmoid(z)
            probs[name].append(round(p, 6))
            preds[name].append("OFF" if p >= 0.5 else "NOT")

    thresholds = {"raw": {"high_automation": 0.6632, "high_precision": 0.8009},
                  "1a1b_d": {"high_automation": 0.8656, "high_precision": 0.9877}}

    systems = drv.evaluate_all(gold, slices, preds, probs, thresholds,
                               n_boot=120, seed=42)

    dev = {n: {"macro_f1": 0.8, "off_recall": 0.69, "off_precision": 0.74,
               "lexicon_hit_off_recall": 0.89, "lexicon_free_off_recall": 0.56,
               "recall_gap": {"delta": 0.3301}} for n in drv.SYSTEMS}

    report = {
        "run_id": "DRYRUN", "n_test": N, "systems": systems,
        "thresholds": {"points": {
            s: {p: {"threshold": thresholds[s][p], "selected_on": "CAL",
                    "rule": "dry run", "dev_coverage": 0.91,
                    "dev_macro_f1": 0.85, "dev_error_rate": 0.079}
                for p in drv.OPERATING_POINTS} for s in ("raw", "1a1b_d")}},
    }
    drv.print_report(report, dev)

    # --- assertions on the shape the write-up depends on -------------------
    for name in drv.SYSTEMS:
        b = systems[name]
        assert b["lexicon_hit"]["n"] + b["lexicon_free"]["n"] == N
        assert b["recall_gap"]["delta"] is not None
        assert b["lexicon_hit"]["macro_f1"] is None, "per-slice macro-F1 must stay omitted"
        assert b["overall_ci"]["macro_f1"]["ci_low"] <= b["overall"]["macro_f1"]
    assert "selective" not in systems["keyword"], "keyword filter has no confidences"
    for name in ("raw", "1a1b_d"):
        for p in drv.OPERATING_POINTS:
            blk = systems[name]["selective"][p]
            assert blk["threshold"] == thresholds[name][p], "threshold was altered"
            for k in ("coverage", "macro_f1", "error_rate", "capture_lift"):
                assert blk[k] is not None, f"{name}/{p}/{k}"
            assert set(blk["by_slice"]) == {"lexicon_hit", "lexicon_free"}

    tmp = Path(tempfile.mkdtemp(prefix="p05_dryrun_"))
    (tmp / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("DRY RUN OK -- scoring, report and serialise paths all execute.")
    print("Numbers above are SYNTHETIC and are not results.")
    print("No test set was opened; no spend record was written.")


if __name__ == "__main__":
    main()
