#!/usr/bin/env python3
"""Dry-run phase04_calibration.py end to end on synthetic dumps.

The real dumps live only on the Drive mirror, so without this the driver's
report/serialise path would execute for the first time on Colab -- which is the
wrong place to discover a KeyError or a None format. Nothing here is a result:
the numbers are synthetic and the output goes to a temp directory.

Usage:  python tests/_dryrun_phase04.py
"""

import csv
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import phase04_calibration as drv
from src import calibration as cal, data_io

N = 1200


def make_dump(path, seed, sharpen):
    """A dump with the same columns and the same 6dp rounding as the real ones,
    including saturated rows, so the clipping path is exercised."""
    rng = random.Random(seed)
    rows = []
    for i in range(N):
        # Labels must actually depend on the score, or the optimal temperature
        # runs to infinity and the dry run only ever exercises the degenerate
        # boundary path. `sharpen` then makes the dump overconfident by a known
        # factor, which is the case a real fit has to handle.
        z = rng.gauss(0.0, 3.0)
        gold = "OFF" if rng.random() < cal.sigmoid(z) else "NOT"
        p = round(cal.sigmoid(z * sharpen), 6)   # 6dp, exactly like the real dump
        rows.append({
            "row_id": str(10000 + i),
            "text": f"satir {i}",
            "gold": gold,
            "pred": "OFF" if p >= 0.5 else "NOT",
            "confidence": f"{p:.6f}",
            "slice": "lexicon_hit" if i % 8 == 0 else "lexicon_free",
        })
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row_id", "text", "gold", "pred",
                                          "confidence", "slice"])
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    tmp = Path(tempfile.mkdtemp(prefix="p04_dryrun_"))
    raw_p, def_p = tmp / "raw.csv", tmp / "def.csv"
    rows = make_dump(raw_p, seed=1, sharpen=1.6)
    make_dump(def_p, seed=1, sharpen=1.1)      # same ids/gold, different sharpness

    # The fingerprint gate is real and must stay real; point it at the synthetic
    # split for the duration of the dry run rather than weakening the check.
    fp = data_io.dev_fingerprint([{"id": r["row_id"]} for r in rows])
    drv.DEV_FINGERPRINT = fp[:16]
    print(f"dry-run fingerprint override: {fp[:16]}  (synthetic, not the real dev set)")

    out = tmp / "out"
    sys.argv = ["phase04_calibration.py",
                "--raw_pred", str(raw_p),
                "--defense_pred", str(def_p),
                "--out_dir", str(out),
                "--n_boot", "80"]
    drv.main()

    blob = json.loads((out / "calibration.json").read_text(encoding="utf-8"))
    assert set(blob["variants"]) == {"raw", "1a1b_d"}
    for v, rep in blob["variants"].items():
        assert rep["rc_invariance_check"]["holds"], v
        assert rep["temperature_fit"]["temperature"] > 0
        for name, b in rep["operating_points"].items():
            for k in ("coverage", "macro_f1", "error_rate", "capture_lift"):
                assert b[k] is not None, f"{v}/{name}/{k} is None"
            assert set(b["by_slice"]) == {"lexicon_hit", "lexicon_free"}
            assert b["ci"]["macro_f1"]["ci_low"] <= b["macro_f1"] <= b["ci"]["macro_f1"]["ci_high"]
        assert len(rep["risk_coverage"]) == len(drv.COVERAGES)

    print("\n" + "=" * 60)
    print("DRY RUN OK -- report, serialise and CI paths all execute.")
    print("Numbers above are SYNTHETIC and are not results.")
    print(f"temp dir: {tmp}")


if __name__ == "__main__":
    main()
