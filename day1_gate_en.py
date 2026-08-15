#!/usr/bin/env python3
"""NSosyal B* -- Day 1: correct data loading + go/no-go gate.

Fulfils briefing S3 (row 1: does a keyword filter really miss a large share of
Turkish offensive content?) and S7.1 (freeze the lexicon before measuring).

Does exactly three things:
  1. Reads OffensEval-TR correctly (src.data_io -- no quoting, manual tab-split)
  2. Freezes the profanity lexicon and records its fingerprint
  3. Measures the size of the "lexicon-free" slice  <-- this number decides
     the shape of the whole project

This is now a thin driver: all parsing lives in src/data_io.py and all matching
in src/lexicon.py. The logic is unchanged from the verified original, so a
rerun must reproduce results/day1_report.json field for field (except the
timestamp).

Gate: this script NEVER touches the official test set. It reads the training
file only.

Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH (override with flags)
Outputs : a JSON freeze record + a human-readable summary on stdout

Usage:
    python day1_gate_en.py --out results/day1_report_rerun.json
"""

import argparse
import json
import os
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout so Windows consoles on a legacy codepage don't choke
# on Turkish characters or symbols. Safe no-op on systems that don't need it.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import data_io, lexicon


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=None, help="OffensEval-TR training TSV (default: config)")
    ap.add_argument("--lexicon", default=None, help="Frozen lexicon file (default: config)")
    ap.add_argument("--out", default=None, help="Freeze record path (default: results/day1_report.json)")
    ap.add_argument("--force", action="store_true", help="Allow overwriting an existing freeze record")
    args = ap.parse_args()

    train_path = Path(args.train or config.COLTEKIN_TRAIN)
    lex_path = Path(args.lexicon or config.LEXICON_PATH)
    out_path = Path(args.out or config.RESULTS_DIR / "day1_report.json")

    if not train_path.exists():
        sys.exit(f"Training file not found: {train_path}\n"
                 "Raw data is gitignored -- copy it into data/coltekin/ first.")
    if out_path.exists() and not args.force:
        sys.exit(f"Refusing to overwrite an existing freeze record: {out_path}\n"
                 "Pass a different --out, or --force if you really mean to re-freeze.")

    print(f"Training file : {train_path}")
    train_hash = data_io.sha256(train_path)
    print(f"SHA256        : {train_hash}\n")

    header, rows = data_io.read_offenseval_tsv(train_path, has_labels=True)
    print(f"Header        : {header}")
    print(f"Row count     : {len(rows):,}")

    # raises if any label is outside {OFF, NOT}, which would mean a broken read
    dist = data_io.assert_binary_labels(rows)
    print(f"Label dist.   : {dist}")
    off_total = dist.get("OFF", 0)
    print(f"OFF rate      : {off_total / len(rows) * 100:.1f}%")

    # --- freeze the lexicon ---
    lex_list = lexicon.load_lexicon(lex_path)
    lex_set = set(lex_list)
    lex_hash = data_io.sha256(lex_path)
    print(f"\nLexicon       : {lex_path}")
    print(f"Entry count   : {len(lex_list):,}")
    print(f"SHA256        : {lex_hash}")

    # --- gate: lexicon-free slice size ---
    off_rows = [r for r in rows if r["label"] == "OFF"]
    lit_hits = sum(lexicon.hit_literal(r["text"], lex_set) for r in off_rows)
    root_hits = sum(lexicon.hit_root(r["text"], lex_list) for r in off_rows)

    lex_free_literal = len(off_rows) - lit_hits
    lex_free_root = len(off_rows) - root_hits

    print("\n" + "=" * 60)
    print("DAY 1 GATE -- lexicon-free slice (measured on OFF examples)")
    print("=" * 60)
    print(f"Total OFF                          : {len(off_rows):,}")
    print(f"Hit by literal (exact-word) match   : {lit_hits:,}")
    print(f"Hit by root (agglutination) match   : {root_hits:,}")
    print(f"Agglutination delta (root - literal): {root_hits - lit_hits:,}  <-- Turkish-specific number, worth reporting")
    print(f"\nLexicon-free (literal matching)     : {lex_free_literal:,}")
    print(f"Lexicon-free (root matching) ADOPTED: {lex_free_root:,}")

    print("\nVerdict:")
    if lex_free_root >= 800:
        print(f"  [PASS] {lex_free_root:,} >= 800 -- slice is sufficient.")
        print("         Proceed with the full B* design (both evasion axes).")
    elif lex_free_root >= 400:
        print(f"  [WARN] {lex_free_root:,} is borderline.")
        print("         Add the Mayda dataset today before continuing.")
        print("         Do NOT enlarge the lexicon after seeing this number -- that is post-hoc tuning.")
    else:
        print(f"  [FAIL] {lex_free_root:,} < 400 -- not sufficient.")
        print("         Restructure today around the obfuscation axis alone. Do not defer this decision.")

    # --- refine the slice: surface-form evasion is NOT implicit toxicity ---
    off_free = [r for r in off_rows if not lexicon.hit_root(r["text"], lex_list)]
    censored = [r for r in off_free if lexicon.is_censored(r["text"])]
    clean_free = [r for r in off_free if not lexicon.is_censored(r["text"])]

    print("\nSlice refinement:")
    print(f"  Lexicon-free (raw)                       : {len(off_free):,}")
    print(f"  of which: self-censored profanity (o***) : {len(censored):,}")
    print("            -- harvest as REAL-WORLD obfuscation evidence, do NOT count as implicit toxicity")
    print(f"  Clean implicit slice (actually adopted)  : {len(clean_free):,}")

    abbrev_hits = [r for r in clean_free if lexicon.is_abbrev_profanity(r["text"])]
    truly_clean = [r for r in clean_free if not lexicon.is_abbrev_profanity(r["text"])]
    demo_safe = [r for r in truly_clean if not lexicon.is_sensitive(r["text"])]

    print(f"  of which: abbreviated profanity (aq/mk/..)  : {len(abbrev_hits):,}  <-- surface evasion, not implicit")
    print(f"  truly clean implicit slice                  : {len(truly_clean):,}")
    print(f"  of which: non-political & non-religious      : {len(demo_safe):,}  <-- demo/report-safe")
    print("  (The FULL slice stays in the aggregate statistics -- this filter is only")
    print("   for curated demo/report examples. Dropping data from the statistical")
    print("   evaluation itself would introduce selection bias.)")

    print("\n15 demo/report-safe examples (random sample, not first-N):")
    rng = random.Random(config.SEED)  # fixed seed -> reproducible sample
    sample_pool = demo_safe.copy()
    rng.shuffle(sample_pool)
    for i, r in enumerate(sample_pool[:15], 1):
        print(f"  {i:2}. {r['text'][:110]}")

    print("\nAll self-censored examples (qualitative report evidence only -- too few")
    print("  (n={}) to serve as a standalone statistical attack family):".format(len(censored)))
    for i, r in enumerate(censored, 1):
        print(f"  {i:2}. {r['text'][:110]}")

    # --- freeze record ---
    report = {
        "frozen_at": datetime.now().isoformat(timespec="seconds"),
        "seed": config.SEED,
        "train_file": os.path.basename(train_path),
        "train_sha256": train_hash,
        "n_rows": len(rows),
        "label_dist": dist,
        "lexicon_file": os.path.basename(lex_path),
        "lexicon_sha256": lex_hash,
        "lexicon_size": len(lex_list),
        "off_total": len(off_rows),
        "lexicon_hit_literal": lit_hits,
        "lexicon_hit_root": root_hits,
        "lexicon_free_root": lex_free_root,
        "agglutination_delta": root_hits - lit_hits,
        "censored_selfmasked": len(censored),
        "abbrev_profanity": len(abbrev_hits),
        "truly_clean_implicit": len(truly_clean),
        "demo_safe_final": len(demo_safe),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nFreeze record written -> {out_path}")
    print("Commit this file to your repo now. It is your evidence to the jury that")
    print("the lexicon was frozen before any test result was inspected.")


if __name__ == "__main__":
    main()
