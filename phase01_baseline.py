#!/usr/bin/env python3
"""NSosyal B* -- Phase 01: baseline diagnosis (BERTurk vs the lexicon-free slice).

Implements phases/01_baseline_diagnosis.md end to end.

The one question this run answers
---------------------------------
Day 1 proved 3,892 / 6,131 OFF tweets (63%) evade the frozen keyword filter under
root matching. That is a fact about the FILTER. This run establishes whether it
is also a fact about a TRANSFORMER: is BERTurk's OFF-recall on the lexicon-free
slice of dev materially below its OFF-recall on the lexicon-hit slice, with a
bootstrap CI on the difference that excludes zero?

Two stages, run in this order:

    python phase01_baseline.py --stage preflight
        Preconditions + split + slice tagging + the 3,892/6,131 sanity gate +
        the keyword-filter matrix row. No torch, no GPU, seconds. This is a
        gate: if the sanity check fails, the tagger in use is not the one that
        produced the frozen record and NO training should be started.

    python phase01_baseline.py --stage train
        Everything above (cheap, re-verified) + fine-tune BERTurk + evaluate +
        write the four output-contract files.

Gate: this script NEVER touches the official Çöltekin test set. It calls
`load_coltekin_train()` only; `load_coltekin_test()`'s PermissionError guard
stays armed and unused (briefing S7.2).

Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH
Outputs : <RESULTS_DIR>/01_baseline_berturk/{metrics.json,
          classification_report.txt, dev_predictions.csv, run_config.json}
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import data_io, evaluate, lexicon

RUN_ID = "01_baseline_berturk"

# --- frozen expectations (results/day1_report.json). These are not tuning
# --- targets; they are what the sanity gate asserts against.
EXPECTED_TRAIN_SHA = "8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa"
EXPECTED_LEXICON_SHA = "0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b"
EXPECTED_LEXICON_FREE_OFF = 3892
EXPECTED_TOTAL_OFF = 6131


def git_sha():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True, text=True, timeout=10,
        )
        sha = out.stdout.strip()
        if out.returncode != 0 or not sha:
            return None
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


def check_preconditions(train_path, lex_path, strict=True):
    """Phase 01 preconditions 1, 2 and 4. Returns the check block; aborts on
    failure unless --allow_hash_mismatch was passed."""
    checks = {}

    train_sha = data_io.sha256(train_path)
    lex_sha = data_io.sha256(lex_path)
    checks["train_sha256"] = {"got": train_sha, "expected": EXPECTED_TRAIN_SHA,
                              "passed": train_sha == EXPECTED_TRAIN_SHA}
    checks["lexicon_sha256"] = {"got": lex_sha, "expected": EXPECTED_LEXICON_SHA,
                                "passed": lex_sha == EXPECTED_LEXICON_SHA}

    # Precondition 1: the Day 1 reproduction check needs a rerun record to
    # compare against; report its state rather than silently claiming it passed.
    rerun = config.RESULTS_DIR / "day1_report_rerun.json"
    checks["day1_reproduction_record"] = {
        "path": str(rerun),
        "present": rerun.exists(),
        "note": None if rerun.exists() else (
            "absent -- run `python day1_gate_en.py --out results/day1_report_rerun.json` "
            "then `python tests/_verify_day1_reproduction.py` before trusting this run"
        ),
    }

    # Precondition 4, asserted rather than assumed.
    checks["official_test_set_touched"] = False

    print("Preconditions")
    for name in ("train_sha256", "lexicon_sha256"):
        c = checks[name]
        print(f"  {name:<16}: {'OK' if c['passed'] else 'MISMATCH'}  {c['got'][:16]}...")
    r = checks["day1_reproduction_record"]
    print(f"  day1 rerun record: {'present' if r['present'] else 'ABSENT'}")
    if r["note"]:
        print(f"      -> {r['note']}")

    failed = [n for n in ("train_sha256", "lexicon_sha256") if not checks[n]["passed"]]
    if failed and strict:
        sys.exit(
            f"ABORT: {', '.join(failed)} does not match the frozen Day 1 record.\n"
            "The corpus or the lexicon changed under the project. Every number from "
            "Day 1 onwards would be measured on different bytes than it claims.\n"
            "Pass --allow_hash_mismatch only if you know exactly why it changed."
        )
    return checks, train_sha, lex_sha


def sanity_gate(all_rows, lex_list):
    """Phase 01 S2: the tagger must reproduce 3,892 lexicon-free OFF of 6,131 on
    the FULL training corpus. This is what proves the slice definition used here
    is the same one that produced the frozen record."""
    off_rows = [r for r in all_rows if r["label"] == "OFF"]
    tags = evaluate.tag_slices(off_rows, lex_list)
    free = sum(1 for t in tags if t == "lexicon_free")
    passed = (free == EXPECTED_LEXICON_FREE_OFF and len(off_rows) == EXPECTED_TOTAL_OFF)
    block = {
        "lexicon_free_off": free,
        "total_off": len(off_rows),
        "expected_lexicon_free_off": EXPECTED_LEXICON_FREE_OFF,
        "expected_total_off": EXPECTED_TOTAL_OFF,
        "passed": passed,
    }
    print("\nSanity gate (full training corpus, frozen tagger)")
    print(f"  lexicon-free OFF : {free:,}  (expected {EXPECTED_LEXICON_FREE_OFF:,})")
    print(f"  total OFF        : {len(off_rows):,}  (expected {EXPECTED_TOTAL_OFF:,})")
    if not passed:
        print(json.dumps(block, indent=2))
        sys.exit(
            "ABORT: the tagger does not reproduce the frozen Day 1 slice.\n"
            "src/lexicon.py has drifted from the code that produced "
            "results/day1_report.json. Report this -- do not proceed with the "
            "adjusted number (phase 01 S2)."
        )
    print("  [PASS] tagger matches the frozen record")
    return block


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["preflight", "train"], default="preflight",
                    help="preflight = no GPU, gates only; train = full run")
    ap.add_argument("--model", default=config.MODEL_BASELINE)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--no_fp16", action="store_true")
    ap.add_argument("--resume", action="store_true", help="continue from checkpoints/<run>/latest.pt")
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--ckpt_dir", default=None)
    ap.add_argument("--force", action="store_true", help="allow overwriting existing result files")
    ap.add_argument("--allow_hash_mismatch", action="store_true")
    args = ap.parse_args()

    started = datetime.now()
    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID)
    train_path = Path(config.COLTEKIN_TRAIN)
    lex_path = Path(config.LEXICON_PATH)

    print(f"NSosyal B* -- phase 01 ({args.stage})")
    print(f"env={config.ENV}  root={config.ROOT}")
    print(f"data={config.DATA_DIR}\nout={out_dir}\nckpt={ckpt_dir}\n")

    if not train_path.exists():
        sys.exit(f"Training file not found: {train_path}\n"
                 "Raw data is gitignored -- mount/copy it, or set NSOSYAL_DATA.")

    metrics_path = out_dir / "metrics.json"
    if args.stage == "train" and metrics_path.exists() and not args.force:
        sys.exit(f"Refusing to overwrite an existing result: {metrics_path}\n"
                 "Use --out_dir for a new run, or --force if you really mean to replace it.")

    # --- preconditions -----------------------------------------------------
    checks, train_sha, lex_sha = check_preconditions(
        train_path, lex_path, strict=not args.allow_hash_mismatch
    )

    # --- corpus + lexicon --------------------------------------------------
    all_rows = data_io.load_coltekin_train(train_path)
    lex_list = lexicon.load_lexicon(lex_path)
    print(f"\nCorpus: {len(all_rows):,} rows   lexicon: {len(lex_list):,} entries")

    gate = sanity_gate(all_rows, lex_list)

    # --- S1: deterministic split, written once and reused thereafter --------
    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
    train_rows, dev_rows, split_meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION
    )
    print(f"\nSplit ({'loaded from' if split_meta['reused_existing_file'] else 'created'} {split_path})")
    print(f"  train : {len(train_rows):,}  {split_meta['counts']['train']}")
    print(f"  dev   : {len(dev_rows):,}  {split_meta['counts']['dev']}")
    print(f"  dev fingerprint : {split_meta['dev_fingerprint'][:16]}...")
    if not split_meta["matches_regeneration"]:
        print("  [warn] the saved split is NOT what a fresh seed-42 split would produce.")
        print("         The file wins (it is the identity of the dev set), but say so in")
        print("         the results log -- something changed the split algorithm.")

    # --- S2: slice tags on dev --------------------------------------------
    dev_gold = [r["label"] for r in dev_rows]
    dev_slices = evaluate.tag_slices(dev_rows, lex_list)
    n_hit = sum(1 for t in dev_slices if t == "lexicon_hit")
    off_hit = sum(1 for t, g in zip(dev_slices, dev_gold) if t == "lexicon_hit" and g == "OFF")
    off_free = sum(1 for t, g in zip(dev_slices, dev_gold) if t == "lexicon_free" and g == "OFF")
    print("\nDev slices")
    print(f"  lexicon_hit  : {n_hit:,} rows  ({off_hit:,} OFF)")
    print(f"  lexicon_free : {len(dev_rows) - n_hit:,} rows  ({off_free:,} OFF)")

    # --- S3: keyword-filter baseline, same split, same scoring code ---------
    kw_pred = ["OFF" if t == "lexicon_hit" else "NOT" for t in dev_slices]
    kw = evaluate.score(dev_gold, kw_pred, n_boot=args.n_boot, seed=args.seed)
    print("\nKeyword filter (frozen lexicon, root matching) on dev -- matrix row 1")
    print(f"  macro-F1   : {kw['macro_f1']:.4f}  "
          f"[{kw['ci']['macro_f1']['ci_low']:.4f}, {kw['ci']['macro_f1']['ci_high']:.4f}]")
    print(f"  OFF-recall : {kw['off_recall']:.4f}  "
          f"[{kw['ci']['off_recall']['ci_low']:.4f}, {kw['ci']['off_recall']['ci_high']:.4f}]")
    print(f"  OFF-prec.  : {kw['off_precision']:.4f}")
    print("  (Per-slice keyword numbers are omitted on purpose: the filter predicts OFF on")
    print("   lexicon_hit and NOT on lexicon_free BY DEFINITION, so its slice recalls are")
    print("   1.0 and 0.0 tautologically. Only the model's slice recalls carry information.)")

    if args.stage == "preflight":
        print("\nPreflight complete. Gates passed, split fixed, matrix row 1 measured.")
        print("Nothing was written except the split file. Next: --stage train on the GPU box.")
        return

    # --- S4: fine-tune BERTurk ---------------------------------------------
    from src import models  # imported here so preflight needs no torch

    print("\n" + "=" * 68)
    print("TRAINING")
    print("=" * 68)
    env = models.environment_info()
    print(f"  torch={env['torch']}  transformers={env['transformers']}  "
          f"sklearn={env['scikit_learn']}  device={env['device_name']}")

    model, tokenizer, history = models.train(
        train_rows, dev_rows, args.model, ckpt_dir,
        epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
        max_len=args.max_len, seed=args.seed, fp16=not args.no_fp16, resume=args.resume,
    )

    # --- S5: evaluate -------------------------------------------------------
    dev_pred, p_off = models.predict(model, tokenizer, dev_rows, max_len=args.max_len)

    overall = evaluate.score(dev_gold, dev_pred, n_boot=args.n_boot, seed=args.seed)
    by_slice = evaluate.score_by_slice(dev_gold, dev_pred, dev_slices,
                                       n_boot=args.n_boot, seed=args.seed)

    hit_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_hit"]
    free_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_free"]
    gap = evaluate.bootstrap_gap_ci(
        [dev_gold[i] for i in hit_idx], [dev_pred[i] for i in hit_idx],
        [dev_gold[i] for i in free_idx], [dev_pred[i] for i in free_idx],
        metric="off_recall", n_boot=args.n_boot, seed=args.seed,
    )

    print("\n" + "=" * 68)
    print("RESULTS (dev split -- the official test set was NOT touched)")
    print("=" * 68)
    print(f"BERTurk overall : macro-F1 {overall['macro_f1']:.4f}  "
          f"OFF-P {overall['off_precision']:.4f}  OFF-R {overall['off_recall']:.4f}")
    for tag in ("lexicon_hit", "lexicon_free"):
        s = by_slice[tag]
        ci = s["ci"]["off_recall"]
        print(f"  {tag:<13}: n={s['n']:>5}  OFF n={s['support_off']:>4}  "
              f"base rate {s['support_off'] / s['n']:.3f}  "
              f"OFF-recall {s['off_recall']:.4f} [{ci['ci_low']:.4f}, {ci['ci_high']:.4f}]")
    print("  (OFF-recall only, by pre-registered constraint: the slices' base rates differ")
    print("   sharply, so a per-slice macro-F1 difference would be driven by class balance.)")
    print(f"\nRECALL GAP (hit - free) : {gap['delta']:+.4f}   "
          f"95% CI [{gap['ci_low']:+.4f}, {gap['ci_high']:+.4f}]   "
          f"excludes zero: {gap['excludes_zero']}")
    print("This is the pivotal number. Apply the pre-registered decision rule in")
    print("phases/01_baseline_diagnosis.md to it -- out loud, before anything else is built.")

    # --- output contract ----------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        "NOTE (pre-registered constraint, phases/01_baseline_diagnosis.md):\n"
        "The per-slice sections below are diagnostic, useful WITHIN a slice. Their F1 and\n"
        "accuracy columns are NOT comparable ACROSS slices -- base rates are 57.8% OFF in\n"
        "lexicon_hit vs 13.6% in lexicon_free, so a difference there reflects class balance,\n"
        "not model behaviour. The only cross-slice comparison this project makes is\n"
        "OFF-recall, which conditions on gold=OFF and is immune to base rate.\n"
        + "=" * 78,
        evaluate.sklearn_report(dev_gold, dev_pred, title="BERTurk -- dev, overall", strict=False),
    ]
    for tag in ("lexicon_hit", "lexicon_free"):
        idx = hit_idx if tag == "lexicon_hit" else free_idx
        report_lines.append(evaluate.sklearn_report(
            [dev_gold[i] for i in idx], [dev_pred[i] for i in idx],
            title=f"BERTurk -- dev, slice={tag} (n={len(idx)})", strict=False))
    report_lines.append(evaluate.sklearn_report(
        dev_gold, kw_pred, title="Keyword filter (frozen lexicon) -- dev, overall", strict=False))
    (out_dir / "classification_report.txt").write_text(
        "\n\n".join(report_lines), encoding="utf-8")

    with open(out_dir / "dev_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
        for r, g, p, c, s in zip(dev_rows, dev_gold, dev_pred, p_off, dev_slices):
            # confidence = softmax P(OFF); the failure analysis and the
            # risk-coverage curve both read this column.
            w.writerow([r["id"], r["text"], g, p, f"{c:.6f}", s])

    metrics = {
        "run_id": RUN_ID,
        "git_sha": git_sha(),
        "sanity_gate": gate,
        "keyword_filter": {
            "macro_f1": kw["macro_f1"],
            "off_recall": kw["off_recall"],
            "off_precision": kw["off_precision"],
            "ci": kw["ci"],
            "note": "slice recalls are tautological (1.0 / 0.0) and deliberately not reported",
        },
        "berturk": {
            "overall": {
                "macro_f1": overall["macro_f1"],
                "off_precision": overall["off_precision"],
                "off_recall": overall["off_recall"],
                "n": overall["n"],
                "support_off": overall["support_off"],
                "confusion": overall["confusion"],
                "ci": overall["ci"],
            },
            # Pre-registered constraint (phases/01_baseline_diagnosis.md): the
            # per-slice comparison is OFF-recall ONLY. Base rates are 57.8% OFF
            # in lexicon_hit vs 13.6% in lexicon_free, so a per-slice macro-F1
            # difference would report class balance as if it were model
            # behaviour. macro_f1 is therefore deliberately absent here.
            "lexicon_hit": {
                "n": by_slice["lexicon_hit"]["n"],
                "support_off": by_slice["lexicon_hit"]["support_off"],
                "base_rate_off": by_slice["lexicon_hit"]["support_off"] / by_slice["lexicon_hit"]["n"],
                "off_recall": by_slice["lexicon_hit"]["off_recall"],
                "off_recall_ci": by_slice["lexicon_hit"]["ci"]["off_recall"],
                "macro_f1": None,
                "macro_f1_note": "omitted by pre-registered constraint -- not comparable across slices",
            },
            "lexicon_free": {
                "n": by_slice["lexicon_free"]["n"],
                "support_off": by_slice["lexicon_free"]["support_off"],
                "base_rate_off": by_slice["lexicon_free"]["support_off"] / by_slice["lexicon_free"]["n"],
                "off_recall": by_slice["lexicon_free"]["off_recall"],
                "off_recall_ci": by_slice["lexicon_free"]["ci"]["off_recall"],
                "macro_f1": None,
                "macro_f1_note": "omitted by pre-registered constraint -- not comparable across slices",
            },
            "recall_gap": {
                "delta": gap["delta"],
                "ci_low": gap["ci_low"],
                "ci_high": gap["ci_high"],
                "excludes_zero": gap["excludes_zero"],
                "method": gap["resampling"],
                "n_boot": gap["n_boot"],
            },
        },
        "training_history": history,
        "decision_rule_applied": None,  # filled by a human, from the log entry
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    run_config = {
        "run_id": RUN_ID,
        "git_sha": metrics["git_sha"],
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "env": config.ENV,
        "paths": {"root": str(config.ROOT), "data": str(config.DATA_DIR),
                  "results": str(out_dir), "checkpoints": str(ckpt_dir),
                  "split_file": str(split_path)},
        "hashes": {"train_sha256": train_sha, "lexicon_sha256": lex_sha,
                   "dev_fingerprint": split_meta["dev_fingerprint"]},
        "preconditions": checks,
        "split": {k: split_meta[k] for k in
                  ("seed", "dev_fraction", "counts", "reused_existing_file", "matches_regeneration")},
        "model": args.model,
        "hyperparams": {"epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
                        "max_len": args.max_len, "seed": args.seed, "warmup_ratio": 0.1,
                        "weight_decay": 0.01, "fp16": not args.no_fp16,
                        "class_weighting": None, "threshold": 0.5},
        "bootstrap": {"n_boot": args.n_boot, "alpha": 0.05, "seed": args.seed},
        "environment": env,
        "official_test_set_touched": False,
    }
    with open(out_dir / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)

    print(f"\nWritten -> {out_dir}")
    for name in ("metrics.json", "classification_report.txt", "dev_predictions.csv", "run_config.json"):
        print(f"  {name}")
    print("\nNext: paste this output back. The decision rule is applied before phase 2 opens.")


if __name__ == "__main__":
    main()
