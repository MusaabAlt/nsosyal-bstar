"""Exercise the phase 01 post-training path with MOCK predictions, no GPU.

Not part of the pytest suite -- it needs the real corpus, which is gitignored.

Why this exists
---------------
`--stage train`'s evaluation and file-writing code otherwise runs for the first
time only after a completed Colab training run. That is the wrong place to
discover a KeyError: the GPU time is already spent and the session may drop
before a fix can be re-run. This harness calls the SAME `prepare()` and
`evaluate_and_write()` the real driver calls, with the model swapped for a fake,
so a structural bug in scoring, the gap CI, metrics assembly or any of the five
output files surfaces locally in seconds.

It exercises the code, NOT the numbers. Every artifact it writes is stamped
MOCK_RUN, it writes to a disposable temp directory, and it refuses to write into
the canonical run directory or to touch docs/RESULTS_LOG.md.

    python tests/_dryrun_phase01_outputs.py                 # both modes
    python tests/_dryrun_phase01_outputs.py --mode all_not  # one mode
    python tests/_dryrun_phase01_outputs.py --keep          # don't delete the temp dir

Mock modes, chosen because they hit different structural branches:
  all_not  -- every prediction NOT. OFF-recall is 0.0 in both slices, the gap is
              exactly 0.0, and OFF-precision is undefined (no predicted OFF).
              This is the None-handling path: a metric that does not exist must
              print as "undefined", not crash and not silently become 0.0.
  random   -- seeded coin flips. Non-degenerate confusion matrices, a non-zero
              gap, and bootstrap CIs that actually have spread.
"""

import argparse
import json
import random
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
import phase01_baseline as drv  # noqa: E402


def mock_predictions(dev_rows, mode, seed=42):
    """Fabricated dev predictions. The ONLY fabricated thing in this project --
    which is why it lives in tests/ and is stamped into every file it touches."""
    if mode == "all_not":
        return ["NOT"] * len(dev_rows), [0.0] * len(dev_rows)
    rng = random.Random(seed)
    probs = [rng.random() for _ in dev_rows]
    return ["OFF" if p >= 0.5 else "NOT" for p in probs], probs


def run_mode(mode, out_root, n_boot):
    out_dir = Path(out_root) / mode
    args = drv.build_parser().parse_args([
        "--stage", "train",
        "--n_boot", str(n_boot),
        "--out_dir", str(out_dir),
    ])

    print("=" * 70)
    print(f"DRY RUN -- mock mode: {mode}   out_dir: {out_dir}")
    print("=" * 70)

    ctx = drv.prepare(args)
    dev_pred, p_off = mock_predictions(ctx["dev_rows"], mode)

    fake_history = [
        {"epoch": 1, "train_loss": 0.4212, "dev_macro_f1": 0.7411, "seconds": 61.0},
        {"epoch": 2, "train_loss": 0.2871, "dev_macro_f1": 0.7620, "seconds": 60.4},
        {"epoch": 3, "train_loss": 0.1954, "dev_macro_f1": 0.7588, "seconds": 60.9},
    ]
    fake_env = {"torch": "MOCK", "cuda_available": False, "device_name": None,
                "transformers": "MOCK", "scikit_learn": None}

    metrics = drv.evaluate_and_write(
        dev_rows=ctx["dev_rows"], dev_gold=ctx["dev_gold"], dev_slices=ctx["dev_slices"],
        dev_pred=dev_pred, p_off=p_off, kw=ctx["kw"], kw_pred=ctx["kw_pred"],
        history=fake_history, env=fake_env, gate=ctx["gate"], checks=ctx["checks"],
        split_meta=ctx["split_meta"], split_path=ctx["split_path"],
        train_sha=ctx["train_sha"], lex_sha=ctx["lex_sha"],
        out_dir=out_dir, ckpt_dir=Path(out_root) / "ckpt",
        args=args, started=datetime.now(),
        mock_note=f"predictions fabricated by tests/_dryrun_phase01_outputs.py (mode={mode})",
    )

    # --- structural assertions on what was produced ------------------------
    expected_files = ["metrics.json", "classification_report.txt", "dev_predictions.csv",
                      "run_config.json", "results_log_row.md"]
    for name in expected_files:
        p = out_dir / name
        assert p.exists() and p.stat().st_size > 0, f"{name} missing or empty"

    m = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    assert m["MOCK_RUN"], "mock stamp missing from metrics.json"
    assert m["sanity_gate"]["passed"] is True
    for tag in ("lexicon_hit", "lexicon_free"):
        b = m["berturk"][tag]
        assert b["macro_f1"] is None, f"{tag}: macro_f1 must stay null (pre-registered)"
        assert b["macro_f1_note"], f"{tag}: the null needs its note"
        c = b["confusion"]
        assert set(c) == {"tn", "fp", "fn", "tp"}, f"{tag}: raw counts missing"
        assert c["tp"] + c["fn"] == b["support_off"], f"{tag}: counts disagree with support"
        assert c["tn"] + c["fp"] == b["support_not"], f"{tag}: counts disagree with support"
        assert sum(c.values()) == b["n"], f"{tag}: counts do not sum to n"
    hit, free = m["berturk"]["lexicon_hit"], m["berturk"]["lexicon_free"]
    assert hit["n"] + free["n"] == m["berturk"]["overall"]["n"], "slices do not partition dev"
    assert hit["support_off"] + free["support_off"] == m["berturk"]["overall"]["support_off"]
    assert "recall_gap" in m["berturk"] and "ci_low" in m["berturk"]["recall_gap"]
    assert m["decision_rule_applied"] is None, "the verdict is a human's to write"

    rows = (out_dir / "dev_predictions.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == "row_id,text,gold,pred,confidence,slice"
    assert len(rows) - 1 == len(ctx["dev_rows"]), "csv row count != dev size"

    log_row = (out_dir / "results_log_row.md").read_text(encoding="utf-8")
    assert "DO NOT PASTE" in log_row, "mock log row is not marked"

    print(f"\n[OK] {mode}: all {len(expected_files)} files written, structure verified")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all_not", "random", "both"], default="both")
    ap.add_argument("--n_boot", type=int, default=200,
                    help="lower than production (1000) -- this is a code path check, not a result")
    ap.add_argument("--keep", action="store_true", help="keep the temp directory")
    a = ap.parse_args()

    out_root = Path(tempfile.mkdtemp(prefix="nsosyal_dryrun_"))
    canonical = Path(config.RESULTS_DIR / drv.RUN_ID).resolve()
    assert canonical not in out_root.resolve().parents and out_root.resolve() != canonical, \
        "the dry run must not write anywhere near the canonical run directory"

    try:
        modes = ["all_not", "random"] if a.mode == "both" else [a.mode]
        for mode in modes:
            run_mode(mode, out_root, a.n_boot)
        print("\n" + "=" * 70)
        print(f"DRY RUN COMPLETE -- {len(modes)} mode(s) clean. No result file and no")
        print("RESULTS_LOG entry was touched; the numbers above are fabricated.")
        print("=" * 70)
    finally:
        if a.keep:
            print(f"temp dir kept: {out_root}")
        else:
            shutil.rmtree(out_root, ignore_errors=True)


if __name__ == "__main__":
    main()
