#!/usr/bin/env python3
"""Build the offline demo asset bundle. Run ONCE, with network. Then never again.

The demo must run with networking disabled, which means every byte it needs has
to be on local disk first: the tokenizer vocabulary and the model config come
from the HF Hub, and `from_pretrained` will silently reach for them at runtime
unless they are already saved locally. This script is the only place that fetch
is allowed to happen.

It writes a self-describing bundle with a manifest of sha256s, so `demo/app.py`
can verify it has the assets it expects instead of discovering a missing file
after a user has already disabled their network.

Usage (on the machine that has network + the checkpoints):
    python demo/build_assets.py \
        --raw_ckpt     <drive>/checkpoints/01_baseline_berturk/best.pt \
        --defense_ckpt <drive>/checkpoints/03_defense/1a1b_d/best.pt \
        --out demo_assets
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config

MODEL_NAME = "dbmdz/bert-base-turkish-cased"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw_ckpt", required=True)
    ap.add_argument("--defense_ckpt", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--calibration", default=None)
    args = ap.parse_args()

    out = Path(args.out or Path(__file__).resolve().parents[1] / "demo_assets")
    (out / "tokenizer").mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
    (out / "lexicon").mkdir(parents=True, exist_ok=True)

    # --- tokenizer + config: THE network step -----------------------------
    print(f"fetching tokenizer + config for {MODEL_NAME} (this needs network) ...")
    from transformers import AutoConfig, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    tok.save_pretrained(out / "tokenizer")
    cfg = AutoConfig.from_pretrained(MODEL_NAME, num_labels=2,
                                     id2label={0: "NOT", 1: "OFF"},
                                     label2id={"NOT": 0, "OFF": 1})
    cfg.save_pretrained(out / "tokenizer")   # config lives beside the vocab
    print(f"  -> {out / 'tokenizer'}")

    # --- checkpoints -------------------------------------------------------
    # Copied, not symlinked: the point of the bundle is that it is complete on
    # one disk. These are the two big files and they dominate the bundle size.
    for name, src in (("raw", args.raw_ckpt), ("1a1b_d", args.defense_ckpt)):
        dst = out / "checkpoints" / f"{name}.pt"
        print(f"copying {name} checkpoint ({Path(src).stat().st_size / 1e6:.1f} MB) ...")
        shutil.copy2(src, dst)

    # --- lexicon -----------------------------------------------------------
    shutil.copy2(config.LEXICON_PATH, out / "lexicon" / "karaliste.txt")

    # --- the frozen operating point ---------------------------------------
    calp = Path(args.calibration or config.RESULTS_DIR / "04_calibration" / "calibration.json")
    blob = json.loads(calp.read_text(encoding="utf-8"))
    op = blob["variants"]["raw"]["operating_points"]["high_automation"]
    operating = {
        "name": "high_automation",
        "threshold": op["threshold"],
        "source": "phase 04, selected on the dev CAL half; never re-derived",
        "dev_coverage": op["coverage"],
        "test_coverage": 0.9016,
        "test_macro_f1": 0.8485,
        "test_error_rate": 0.0852,
        "test_capture_lift": 3.59,
    }
    (out / "operating_point.json").write_text(
        json.dumps(operating, indent=2), encoding="utf-8")

    # --- manifest ----------------------------------------------------------
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "model_name": MODEL_NAME,
        "note": ("Everything demo/app.py needs. Built once with network; the demo "
                 "itself sets HF_HUB_OFFLINE=1 and never fetches."),
        "total_bytes": sum(p.stat().st_size for p in files),
        "files": {str(p.relative_to(out)).replace("\\", "/"):
                  {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in files},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"BUNDLE -> {out}")
    print("=" * 72)
    for rel, meta in manifest["files"].items():
        print(f"  {rel:<44} {meta['bytes'] / 1e6:>9.1f} MB")
    print(f"  {'TOTAL':<44} {manifest['total_bytes'] / 1e6:>9.1f} MB")
    print("\nCopy this whole directory to the demo machine, then:")
    print("  python demo/app.py --assets <path to demo_assets>")


if __name__ == "__main__":
    main()
