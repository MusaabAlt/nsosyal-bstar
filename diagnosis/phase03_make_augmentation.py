#!/usr/bin/env python3
"""NSosyal B* -- Phase 03 step 2: build the counterfactual augmentation, for REVIEW.

Fulfils the review gate in phases/03_defense_design.md: augmentation samples are read
and approved before any training run is launched. Bad augmentation is cheaper to catch
by reading than by training on.

Runs on CPU in seconds -- no GPU, no torch. It only reads the corpus and the frozen
lexicon, applies src/augment.py, prints samples (accepted AND rejected, so the filter
boundary can be judged, not just its output), and writes a JSON summary.

Gates: training split only. Dev rows are never augmented and never read here beyond the
split bookkeeping. The official test set is not touched.

Usage:
    python phase03_make_augmentation.py --samples 20
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import augment, data_io, lexicon

RUN_ID = "03_defense"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--ratio_1b", type=float, default=1.0,
                    help="1b rows generated as a multiple of the number of 1a rows")
    ap.add_argument("--out_dir", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = data_io.load_coltekin_train()
    train_sha = data_io.sha256(config.COLTEKIN_TRAIN)
    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
    train_rows, dev_rows, meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION)
    lex = lexicon.load_lexicon()

    print(f"split      : {split_path}")
    print(f"  dev fingerprint {meta['dev_fingerprint'][:16]}...  (dev is NOT augmented)")
    print(f"  train rows {len(train_rows):,}   lexicon {len(lex):,} entries\n")

    off_rows = [r for r in train_rows if r["label"] == "OFF"]
    not_rows = [r for r in train_rows if r["label"] == "NOT"]

    # --- 1a ---------------------------------------------------------------
    aug_1a, reasons = augment.build_1a(off_rows, lex)
    print("=" * 100)
    print("1a  MASK THE PROFANITY IN GOLD-OFF ROWS, KEEP THE LABEL OFF")
    print("=" * 100)
    print(f"  gold-OFF training rows           : {len(off_rows):,}")
    print(f"  QUALIFIED (augmented)            : {len(aug_1a):,}")
    skipped = len(off_rows) - len(aug_1a)
    print(f"  SKIPPED                          : {skipped:,}")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        if why != "ok":
            print(f"      {why:<32} {n:,}")
    print("  (constraint C2: fewer clean augmented rows beat more noisy ones)")

    rng = random.Random(args.seed)
    show = rng.sample(aug_1a, min(args.samples, len(aug_1a)))
    by_id = {r["id"]: r for r in off_rows}
    print(f"\n  --- {len(show)} ACCEPTED 1a rows (random, seed {args.seed}) ---")
    for i, a in enumerate(show, 1):
        print(f"\n  {i:>2}. before: {by_id[a['source_id']]['text'][:150]}")
        print(f"      after : {a['text'][:150]}")

    rejected = [r for r in off_rows
                if not augment.qualifies_for_masking(r["text"], lex)[0]
                and augment._profane_tokens(r["text"], lex)]
    rej_show = rng.sample(rejected, min(10, len(rejected)))
    print(f"\n  --- 10 REJECTED rows, so the filter boundary can be judged ---")
    for i, r in enumerate(rej_show, 1):
        why = augment.qualifies_for_masking(r["text"], lex)[1]
        print(f"  {i:>2}. [{why}] {r['text'][:130]}")

    # --- 1b ---------------------------------------------------------------
    n_1b = int(round(len(aug_1a) * args.ratio_1b))
    aug_1b, pool_size = augment.build_1b(not_rows, n_1b, seed=args.seed)
    print("\n" + "=" * 100)
    print("1b  INSERT PROFANITY INTO GOLD-NOT ROWS IN A NON-OFFENSIVE FUNCTION, KEEP NOT")
    print("=" * 100)
    print(f"  gold-NOT training rows available : {len(not_rows):,}")
    print(f"  short enough to be a source      : {pool_size:,}  "
          f"(<= {augment.MAX_SOURCE_WORDS} words, so the insertion survives max_len truncation)")
    print(f"  generated                        : {len(aug_1b):,}")
    print(f"  by pattern: {dict(Counter(a['op'] for a in aug_1b))}")
    print("  every pattern derived from TRAINING-SPLIT out-of-fold errors (constraint C1);")
    print("  ADVERBIAL and NON_PERSON_TARGET appear only in the training-derived sample.")

    src_by_id = {r["id"]: r for r in not_rows}
    show_b = rng.sample(aug_1b, min(args.samples, len(aug_1b)))
    print(f"\n  --- {len(show_b)} 1b rows (random, seed {args.seed}) ---")
    for i, a in enumerate(show_b, 1):
        print(f"\n  {i:>2}. [{a['op']}]")
        print(f"      before: {src_by_id[a['source_id']]['text'][:150]}")
        print(f"      after : {a['text'][:150]}")

    summary = {
        "run_id": f"{RUN_ID}_augmentation_review",
        "seed": args.seed,
        "dev_fingerprint": meta["dev_fingerprint"],
        "dev_augmented": False,
        "official_test_set_touched": False,
        "train_rows": len(train_rows),
        "1a": {"gold_off_rows": len(off_rows), "qualified": len(aug_1a),
               "skipped": skipped, "skip_reasons": {k: v for k, v in reasons.items() if k != "ok"}},
        "1b": {"generated": len(aug_1b), "by_pattern": dict(Counter(a["op"] for a in aug_1b)),
               "pattern_provenance": "training-split out-of-fold errors only (C1)"},
        "totals": {"augmented_rows": len(aug_1a) + len(aug_1b),
                   "training_rows_after_augmentation": len(train_rows) + len(aug_1a) + len(aug_1b)},
    }
    with open(out_dir / "augmentation_review.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n\nsummary -> {out_dir / 'augmentation_review.json'}")
    print("NO TRAINING LAUNCHED. Samples above go to review first.")


if __name__ == "__main__":
    main()
