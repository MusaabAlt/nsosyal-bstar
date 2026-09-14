#!/usr/bin/env python3
"""NSosyal B* -- Phase 03 step 3: train and evaluate one defense variant.

Fulfils phases/03_defense_design.md. Four runs, one variant each, so effects are
attributable rather than inferred:

    raw     BERTurk raw                       (phase 01, already have it)
    1a      + masked-profanity OFF rows       -> recall changes attribute here
    1a1b    + profanity-in-NOT insertion      -> FP changes attribute here
    1a1b_d  + D-family obfuscation            -> held-out robustness attributes here

Every variant is evaluated on the SAME frozen dev split (fingerprint
034415af3a23b388), never on augmented dev, and additionally on an H-perturbed
copy of dev for the held-out-obfuscation column. `assert_disjoint` is called at
both sites -- training augmentation and robustness evaluation -- so a run that
reused D for testing aborts.

Gates: the official Çöltekin test set is never loaded. Dev is never augmented.

Usage:
    python phase03_train_defense.py --variant 1a     --mirror_dir <drive>
    python phase03_train_defense.py --variant raw --no_train \
        --load_checkpoint <drive>/checkpoints/01_baseline_berturk/best.pt
"""

import argparse
import csv
import json
import random
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from phase01_baseline import assert_trainable_runtime, git_sha
from src import augment, data_io, evaluate, lexicon, obfuscation

RUN_ID = "03_defense"
VARIANTS = ("raw", "1a", "1a1b", "1a1b_d")


def build_training_set(train_rows, lex, variant, args, log=print):
    """Assemble the augmented training split. Dev is never touched."""
    rows = list(train_rows)
    stats = {"base": len(train_rows), "1a": 0, "1a_upsample": 0, "1b": 0, "obf_D": 0}
    if variant == "raw":
        return rows, stats

    off_rows = [r for r in train_rows if r["label"] == "OFF"]
    not_rows = [r for r in train_rows if r["label"] == "NOT"]

    aug_1a, reasons = augment.build_1a(off_rows, lex)
    stats["1a"] = len(aug_1a)
    stats["1a_skip_reasons"] = {k: v for k, v in reasons.items() if k != "ok"}
    for _ in range(args.upsample_1a):
        rows.extend(aug_1a)
    stats["1a_upsample"] = len(aug_1a) * args.upsample_1a
    log(f"  1a: {len(aug_1a)} clean rows x{args.upsample_1a} = {stats['1a_upsample']}")

    if variant in ("1a1b", "1a1b_d"):
        aug_1b, pool = augment.build_1b(not_rows, args.n_1b, seed=args.seed)
        rows.extend(aug_1b)
        stats["1b"] = len(aug_1b)
        log(f"  1b: {len(aug_1b)} rows from a pool of {pool} short NOT rows")

    if variant == "1a1b_d":
        # ANTI-CIRCULARITY (briefing S7.3): training uses D, evaluation uses H.
        obfuscation.assert_disjoint(train_families=["D"], eval_families=["H"])
        rng = random.Random(args.seed)
        pool = [r for r in off_rows if lexicon.hit_root(r["text"], lex)]
        rng.shuffle(pool)
        made = 0
        for r in pool:
            if made >= args.n_obf:
                break
            text, ops = obfuscation.apply_family(r["text"], "D", lex, rng)
            if not ops:
                continue
            rows.append({"id": f"{r['id']}_D", "text": text, "label": "OFF",
                         "source_id": r["id"], "op": f"D_{'+'.join(ops)}"})
            made += 1
        stats["obf_D"] = made
        log(f"  D : {made} obfuscated OFF rows (family D, training only)")

    return rows, stats


def evaluate_variant(model, tokenizer, dev_rows, dev_gold, dev_slices, lex, args, log=print):
    """All four required metrics plus the no-profanity FP count, on clean dev."""
    from src import models

    pred, p_off = models.predict(model, tokenizer, dev_rows, max_len=args.max_len)
    overall = evaluate.score(dev_gold, pred, n_boot=args.n_boot, seed=args.seed)
    by_slice = evaluate.score_by_slice(dev_gold, pred, dev_slices, n_boot=args.n_boot, seed=args.seed)

    hit_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_hit"]
    free_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_free"]
    gap = evaluate.bootstrap_gap_ci(
        [dev_gold[i] for i in hit_idx], [pred[i] for i in hit_idx],
        [dev_gold[i] for i in free_idx], [pred[i] for i in free_idx],
        metric="off_recall", n_boot=args.n_boot, seed=args.seed)

    hit = by_slice["lexicon_hit"]["confusion"]
    fp_rate_hit = hit["fp"] / max(1, hit["fp"] + hit["tn"])

    # No-profanity false positives. Automated proxy for the manually tagged 118:
    # a false positive containing no lexicon token once the demonstrated
    # false-match roots are excluded. If 1a teaches "[MASK] in an insult frame =
    # OFF", the model may transfer that to any unknown token and this rises.
    fps = [(r, pr) for r, g, pr in zip(dev_rows, dev_gold, pred) if g == "NOT" and pr == "OFF"]
    no_prof_fp = sum(1 for r, _ in fps if not augment._profane_tokens(r["text"], lex))

    return {
        "predictions": pred, "p_off": p_off,
        "macro_f1": overall["macro_f1"], "macro_f1_ci": overall["ci"]["macro_f1"],
        "off_recall": overall["off_recall"], "off_recall_ci": overall["ci"]["off_recall"],
        "off_precision": overall["off_precision"], "confusion": overall["confusion"],
        "lexicon_free_off_recall": by_slice["lexicon_free"]["off_recall"],
        "lexicon_free_off_recall_ci": by_slice["lexicon_free"]["ci"]["off_recall"],
        "lexicon_hit_off_recall": by_slice["lexicon_hit"]["off_recall"],
        "lexicon_hit_off_recall_ci": by_slice["lexicon_hit"]["ci"]["off_recall"],
        "lexicon_hit_fp_rate": fp_rate_hit,
        "lexicon_hit_confusion": hit,
        "lexicon_free_confusion": by_slice["lexicon_free"]["confusion"],
        "recall_gap": {k: gap[k] for k in ("delta", "ci_low", "ci_high", "excludes_zero")},
        "false_positives_total": len(fps),
        "false_positives_no_profanity": no_prof_fp,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, required=True)
    ap.add_argument("--upsample_1a", type=int, default=3)
    ap.add_argument("--n_1b", type=int, default=2000)
    ap.add_argument("--n_obf", type=int, default=2000)
    ap.add_argument("--model", default=config.MODEL_BASELINE)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--no_fp16", action="store_true")
    ap.add_argument("--allow_cpu", action="store_true")
    ap.add_argument("--no_train", action="store_true", help="evaluate an existing checkpoint")
    ap.add_argument("--load_checkpoint", default=None)
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--ckpt_dir", default=None)
    ap.add_argument("--mirror_dir", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    started = datetime.now()
    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID / f"run_{args.variant}")
    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID / args.variant)
    metrics_path = out_dir / "metrics.json"
    if metrics_path.exists() and not args.force:
        sys.exit(f"Refusing to overwrite {metrics_path}. Use --force to replace.")

    print(f"NSosyal B* -- phase 03 defense, variant '{args.variant}'")
    print(f"env={config.ENV}  out={out_dir}\n")

    all_rows = data_io.load_coltekin_train()
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
    train_rows, dev_rows, split_meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION)
    lex = lexicon.load_lexicon()
    if not split_meta["dev_fingerprint"].startswith("034415af3a23b388"):
        sys.exit(f"ABORT: dev fingerprint is {split_meta['dev_fingerprint'][:16]}, "
                 "not the frozen 034415af3a23b388. Every comparison would be invalid.")
    print(f"dev fingerprint {split_meta['dev_fingerprint'][:16]}...  [matches the frozen split]")

    dev_gold = [r["label"] for r in dev_rows]
    dev_slices = evaluate.tag_slices(dev_rows, lex)

    print("\nTraining set:")
    aug_rows, stats = build_training_set(train_rows, lex, args.variant, args)
    print(f"  total: {len(aug_rows):,} rows ({len(train_rows):,} base + "
          f"{len(aug_rows) - len(train_rows):,} augmented)")

    from src import models
    env = models.environment_info()
    assert_trainable_runtime(allow_cpu=args.allow_cpu)

    if args.no_train:
        import torch
        tokenizer, model = models.load_model(args.model)
        state = torch.load(args.load_checkpoint, map_location="cuda", weights_only=False)
        model.load_state_dict(state["model"])
        model.to("cuda")
        history = [{"note": f"loaded {args.load_checkpoint}, no training"}]
        print(f"\nloaded checkpoint {args.load_checkpoint} (no training)")
    else:
        print(f"\n=== training variant {args.variant} ===")
        model, tokenizer, history = models.train(
            aug_rows, dev_rows, args.model, ckpt_dir,
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            max_len=args.max_len, seed=args.seed, fp16=not args.no_fp16)

    # --- clean dev ---------------------------------------------------------
    res = evaluate_variant(model, tokenizer, dev_rows, dev_gold, dev_slices, lex, args)

    # --- H-perturbed dev: held-out obfuscation, NEVER trained on -----------
    obfuscation.assert_disjoint(train_families=["D"], eval_families=["H"])
    rng = random.Random(args.seed)
    h_rows, n_perturbed = [], 0
    for r in dev_rows:
        text, ops = obfuscation.apply_family(r["text"], "H", lex, rng)
        n_perturbed += bool(ops)
        h_rows.append({**r, "text": text})
    h_pred, _ = models.predict(model, tokenizer, h_rows, max_len=args.max_len)
    h_score = evaluate.score(dev_gold, h_pred, n_boot=args.n_boot, seed=args.seed)

    print("\n" + "=" * 70)
    print(f"VARIANT {args.variant} on dev (official test set untouched)")
    print("=" * 70)
    print(f"  macro-F1            {res['macro_f1']:.4f} "
          f"[{res['macro_f1_ci']['ci_low']:.4f}, {res['macro_f1_ci']['ci_high']:.4f}]")
    print(f"  lexicon_free OFF-R  {res['lexicon_free_off_recall']:.4f} "
          f"[{res['lexicon_free_off_recall_ci']['ci_low']:.4f}, {res['lexicon_free_off_recall_ci']['ci_high']:.4f}]")
    print(f"  lexicon_hit OFF-R   {res['lexicon_hit_off_recall']:.4f}")
    print(f"  lexicon_hit FP rate {res['lexicon_hit_fp_rate']:.4f}  "
          f"({res['lexicon_hit_confusion']['fp']}/{res['lexicon_hit_confusion']['fp'] + res['lexicon_hit_confusion']['tn']})")
    print(f"  recall gap          {res['recall_gap']['delta']:+.4f} "
          f"[{res['recall_gap']['ci_low']:+.4f}, {res['recall_gap']['ci_high']:+.4f}]")
    print(f"  false positives     {res['false_positives_total']}  "
          f"of which NO profanity token: {res['false_positives_no_profanity']}")
    print(f"  H-perturbed dev     macro-F1 {h_score['macro_f1']:.4f}  "
          f"OFF-recall {h_score['off_recall']:.4f}  ({n_perturbed} rows perturbed)")

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": f"{RUN_ID}_{args.variant}",
        "variant": args.variant,
        "git_sha": git_sha(),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "dev_fingerprint": split_meta["dev_fingerprint"],
        "official_test_set_touched": False,
        "dev_augmented": False,
        "attack_families": {"train": ["D"], "eval": ["H"], "disjoint_asserted": True},
        "augmentation": stats,
        "hyperparams": {"epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
                        "max_len": args.max_len, "seed": args.seed,
                        "upsample_1a": args.upsample_1a, "n_1b": args.n_1b, "n_obf": args.n_obf},
        "clean_dev": {k: v for k, v in res.items() if k not in ("predictions", "p_off")},
        "heldout_obfuscation_H_dev": {
            "macro_f1": h_score["macro_f1"], "off_recall": h_score["off_recall"],
            "off_precision": h_score["off_precision"], "confusion": h_score["confusion"],
            "rows_perturbed": n_perturbed,
            "note": "family H was never trained on; D/H disjointness asserted at both sites",
        },
        "training_history": history,
        "environment": env,
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(out_dir / "dev_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
        for r, g, p, c, s in zip(dev_rows, dev_gold, res["predictions"], res["p_off"], dev_slices):
            w.writerow([r["id"], r["text"], g, p, f"{c:.6f}", s])

    print(f"\nWritten -> {out_dir}")
    if args.mirror_dir:
        import shutil
        md = Path(args.mirror_dir) / f"run_{args.variant}"
        md.mkdir(parents=True, exist_ok=True)
        for p in sorted(out_dir.iterdir()):
            if p.is_file():
                shutil.copy2(p, md / p.name)
        print(f"mirrored -> {md}")


if __name__ == "__main__":
    main()
