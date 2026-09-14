#!/usr/bin/env python3
"""NSosyal B* -- Phase 03 step 1: out-of-fold errors INSIDE the training split.

Fulfils constraint C1 in phases/03_defense_design.md.

Why this script exists
----------------------
The defense's insertion patterns (component 1b) must be derived from training-split
errors, never from the dev-set error families measured in phase 02. Dev is the set the
defense is reported on; deriving augmentation from its error structure would mean the
reported false-positive reduction partly measures the template rather than the model.
That is the same circularity that killed an earlier version of this project, in a new
form.

So this script produces out-of-fold predictions for all 26,992 training rows by 5-fold
stratified cross-validation INSIDE the training split. Out-of-fold means each prediction
is made by a model that did not see that row -- the same condition dev is evaluated
under. Predictions on held-in rows would be memorisation-contaminated and their error
structure would not be comparable.

Gates
-----
* Never touches the official test set (`load_coltekin_test` is not called).
* Never touches the dev split: folds are drawn from `train_rows` only, so no dev row is
  trained on or predicted here.
* Same split file, same fingerprint, same seed as phase 01.

Resumable: each fold's predictions are written as they complete and completed folds are
skipped on a rerun, because a free Colab session can drop inside a ~25 minute job.

Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH, the frozen split file
Outputs : <RESULTS_DIR>/03_defense/oof/fold{i}.csv  (per fold, resumable)
          <RESULTS_DIR>/03_defense/train_oof_predictions.csv  (merged)
          <RESULTS_DIR>/03_defense/train_oof_summary.json

Usage:
    python phase03_train_errors.py --stage preflight     # no GPU, shows the fold plan
    python phase03_train_errors.py --stage run --mirror_dir <drive path>
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from phase01_baseline import assert_trainable_runtime, git_sha, mirror_outputs
from src import data_io, evaluate, lexicon

RUN_ID = "03_defense"
K_FOLDS = 5


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["preflight", "run"], default="preflight")
    ap.add_argument("--k", type=int, default=K_FOLDS)
    ap.add_argument("--model", default=config.MODEL_BASELINE)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--no_fp16", action="store_true")
    ap.add_argument("--allow_cpu", action="store_true")
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--ckpt_dir", default=None)
    ap.add_argument("--mirror_dir", default=None)
    ap.add_argument("--force", action="store_true")
    return ap


def main():
    args = build_parser().parse_args()
    started = datetime.now()

    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    fold_dir = out_dir / "oof"
    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID)

    print(f"NSosyal B* -- phase 03 step 1: out-of-fold training errors ({args.stage})")
    print(f"env={config.ENV}  out={out_dir}\n")

    all_rows = data_io.load_coltekin_train()
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
    train_rows, dev_rows, split_meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION
    )
    print(f"split loaded : {split_path}")
    print(f"  dev fingerprint : {split_meta['dev_fingerprint'][:16]}...  (dev is NOT used here)")
    print(f"  train rows      : {len(train_rows):,}  {split_meta['counts']['train']}")

    folds = data_io.stratified_kfold(train_rows, k=args.k, seed=args.seed)
    dev_ids = {str(r["id"]) for r in dev_rows}
    for i, f in enumerate(folds):
        leaked = [r["id"] for r in f if str(r["id"]) in dev_ids]
        if leaked:
            sys.exit(f"ABORT: fold {i} contains dev rows ({leaked[:5]}). The dev split must "
                     "not appear anywhere in this job.")
    print(f"\n{args.k}-fold stratified partition of the TRAINING split (seed {args.seed}):")
    for i, f in enumerate(folds):
        print(f"  fold {i}: n={len(f):,}  {dict(Counter(r['label'] for r in f))}")
    print("  no dev row appears in any fold  [checked]")

    if args.stage == "preflight":
        print("\nPreflight only. Nothing trained, nothing written.")
        return

    from src import models

    env = models.environment_info()
    print(f"\ntorch={env['torch']}  transformers={env['transformers']}  device={env['device_name']}")
    assert_trainable_runtime(allow_cpu=args.allow_cpu)

    fold_dir.mkdir(parents=True, exist_ok=True)
    for i, fold in enumerate(folds):
        fold_file = fold_dir / f"fold{i}.csv"
        if fold_file.exists() and not args.force:
            print(f"\n=== fold {i}: already done ({fold_file.name}), skipping ===")
            continue
        inner_train = [r for j, f in enumerate(folds) if j != i for r in f]
        print(f"\n=== fold {i}/{args.k - 1}: train on {len(inner_train):,}, predict {len(fold):,} ===")

        model, tokenizer, _ = models.train(
            inner_train, fold, args.model, ckpt_dir / f"fold{i}",
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            max_len=args.max_len, seed=args.seed, fp16=not args.no_fp16,
        )
        preds, p_off = models.predict(model, tokenizer, fold, max_len=args.max_len)

        with open(fold_file, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["row_id", "text", "gold", "pred", "confidence", "fold"])
            for r, p, c in zip(fold, preds, p_off):
                w.writerow([r["id"], r["text"], r["label"], p, f"{c:.6f}", i])
        print(f"  wrote {fold_file}")
        del model, tokenizer

    # --- merge -------------------------------------------------------------
    merged = []
    for i in range(args.k):
        with open(fold_dir / f"fold{i}.csv", encoding="utf-8") as fh:
            merged.extend(list(csv.DictReader(fh)))
    if len(merged) != len(train_rows):
        sys.exit(f"ABORT: merged {len(merged)} out-of-fold rows but the training split has "
                 f"{len(train_rows)}. Folds do not partition the split.")

    merged_path = out_dir / "train_oof_predictions.csv"
    with open(merged_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "text", "gold", "pred", "confidence", "fold"])
        w.writeheader()
        w.writerows(merged)

    gold = [r["gold"] for r in merged]
    pred = [r["pred"] for r in merged]
    lex_list = lexicon.load_lexicon()
    slices = evaluate.tag_slices(merged, lex_list)
    overall = evaluate.score(gold, pred, with_ci=False)

    fp = [r for r, g, p in zip(merged, gold, pred) if g == "NOT" and p == "OFF"]
    fn = [r for r, g, p in zip(merged, gold, pred) if g == "OFF" and p == "NOT"]
    fp_hit = sum(1 for r, s, g, p in zip(merged, slices, gold, pred)
                 if s == "lexicon_hit" and g == "NOT" and p == "OFF")

    summary = {
        "run_id": f"{RUN_ID}_train_oof",
        "purpose": "training-split errors for deriving 1b insertion patterns (constraint C1); "
                   "dev error families are NOT used for derivation",
        "git_sha": git_sha(),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "k_folds": args.k,
        "seed": args.seed,
        "model": args.model,
        "n_train_rows": len(train_rows),
        "dev_fingerprint": split_meta["dev_fingerprint"],
        "dev_rows_used": 0,
        "official_test_set_touched": False,
        "oof_overall": {
            "macro_f1": overall["macro_f1"],
            "off_recall": overall["off_recall"],
            "off_precision": overall["off_precision"],
            "confusion": overall["confusion"],
        },
        "errors": {
            "false_positives": len(fp),
            "false_negatives": len(fn),
            "false_positives_lexicon_hit": fp_hit,
            "false_positives_lexicon_free": len(fp) - fp_hit,
        },
        "environment": env,
    }
    with open(out_dir / "train_oof_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print("\n" + "=" * 68)
    print("OUT-OF-FOLD RESULTS ON THE TRAINING SPLIT (dev untouched)")
    print("=" * 68)
    print(f"  macro-F1 {overall['macro_f1']:.4f}   OFF-recall {overall['off_recall']:.4f}   "
          f"OFF-precision {overall['off_precision']:.4f}")
    print(f"  false positives : {len(fp):,}  ({fp_hit:,} lexicon_hit / {len(fp) - fp_hit:,} lexicon_free)")
    print(f"  false negatives : {len(fn):,}")
    print(f"\nWritten -> {out_dir}")

    if args.mirror_dir:
        mirror_dir = Path(args.mirror_dir)
        mirror_dir.mkdir(parents=True, exist_ok=True)
        import shutil
        for name in ("train_oof_predictions.csv", "train_oof_summary.json"):
            shutil.copy2(out_dir / name, mirror_dir / name)
            print(f"  mirrored {name} -> {mirror_dir}")


if __name__ == "__main__":
    main()
