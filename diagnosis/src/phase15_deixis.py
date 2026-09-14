#!/usr/bin/env python3
"""Phase 15 step 1 -- freeze the address flag, then count. COUNTS ONLY.

The flag itself is frozen in `data/deixis/address_tokens.json` and is committed
before any Phase 15 count exists. Its primary set is transcribed from
`phases/09_deeper_analysis.md` Stage 4, which required exactly that: enumerate
the set and commit it before running.

**This module computes no calibration quantity.** No signed gap, no ECE, no AUC,
no recall, no mean `p_OFF`, no per-cell OFF rate expressed as a calibration
figure, no verdict. Integers, shares of integers, and hashes. The point of the
stage is that the cell sizes -- including the sensitivity denominators and the
CAL-half fitting cells -- are known *before* any band or statistic is fixed, so
that a later choice of band cannot be made after seeing what it would buy.

Dev split only, fingerprint 034415af3a23b388. Read-only: no training, no forward
pass, no model loaded, lexicon and MIN_ROOT_LEN frozen, `load_coltekin_test`
never called. The official test set is spent and stays spent.

The provenance gate is `phase11_prior_correction.load_and_gate`, imported and
called unmodified rather than reimplemented, so this stage and Phase 11 Run A
stand or fall on the identical checks.

Usage:
    python -m src.phase15_deixis
"""

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import lexicon                                    # noqa: E402
from src.phase11_prior_correction import (                 # noqa: E402
    FROZEN_THRESHOLD, SPLIT_PATH, load_and_gate, sha256_of)

RUN_ID = "15_deixis"
STAGE = "step 1 -- freeze the address flag, then count (COUNTS ONLY)"
TOKENS_PATH = ROOT / "data/deixis/address_tokens.json"

SLICES = ("lexicon_free", "lexicon_hit")
GOLDS = ("OFF", "NOT")
ADDRESS = ("address", "no_address")


# ==============================================================================
# the flag
# ==============================================================================

def address_flag(text, token_set):
    """True iff `text` contains a token that IS in `token_set`, by equality.

    Tokenisation is `src.lexicon.tokens` -- the frozen project tokeniser, which
    Turkish-lowercases first (`I` -> `ı`, `İ` -> `i`) and then splits on `\\w+`.
    It is imported, never reimplemented.

    Equality, NOT prefix matching. `sen` must not take `sene` / `senaryo` /
    `senato` / `sendika`, and `siz` must not take `sizofren`. Prefix matching is
    what `hit_root` does for the profanity lexicon, and the contamination it
    causes there is already on the record (phase 02: 248 of 614 hit-slice rows
    matched only via a suspect root). That failure mode is not repeated here.
    """
    return any(t in token_set for t in lexicon.tokens(text))


def load_token_sets(path=TOKENS_PATH):
    """The frozen sets, as committed. Returns {name: frozenset} plus the raw doc."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    sets = {"primary": frozenset(doc["primary_set"]),
            "extended": frozenset(doc["extended_set"]),
            "third_person_deictic": frozenset(doc["third_person_deictic_set"])}
    for name, key in (("primary", "primary_set"), ("extended", "extended_set"),
                      ("third_person_deictic", "third_person_deictic_set")):
        listed = doc[key]
        if len(set(listed)) != len(listed):
            sys.exit(f"ABORT: {key} contains duplicates; the frozen set is ill-formed.")
        if len(sets[name]) != doc[f"{key}_size"]:
            sys.exit(f"ABORT: {key} has {len(sets[name])} distinct tokens but "
                     f"{key}_size records {doc[f'{key}_size']}.")
    if not frozenset(doc["primary_set"]) <= sets["extended"]:
        sys.exit("ABORT: extended_set does not contain the primary seven.")
    return sets, doc


# ==============================================================================
# counting
# ==============================================================================

def cell_counts(rows, token_set):
    """(slice x address x gold) -- 8 cells, plus the band restriction and the
    p_OFF == 0.5 count, plus margins. Integers only."""
    for r in rows:
        r["_addr"] = "address" if address_flag(r["text"], token_set) else "no_address"

    cells = {}
    for sl in SLICES:
        for ad in ADDRESS:
            for g in GOLDS:
                sub = [r for r in rows
                       if r["slice"] == sl and r["_addr"] == ad and r["gold"] == g]
                band = [r for r in sub if r["p_off"] < FROZEN_THRESHOLD]
                edge = [r for r in sub if r["p_off"] == FROZEN_THRESHOLD]
                cells[f"{sl}|{ad}|{g}"] = {
                    "slice": sl, "address": ad, "gold": g,
                    "n": len(sub),
                    "n_band_p_off_lt_0.5": len(band),
                    "n_at_p_off_exactly_0.5": len(edge),
                    "n_above_band": len(sub) - len(band) - len(edge),
                }

    def total(pred, key):
        return sum(v[key] for v in cells.values() if pred(v))

    margins = {"by_slice": {}, "by_address": {}, "by_gold": {},
               "by_slice_x_address": {}, "by_slice_x_gold": {}, "all": {}}
    keys = ("n", "n_band_p_off_lt_0.5", "n_at_p_off_exactly_0.5")
    for sl in SLICES:
        margins["by_slice"][sl] = {k: total(lambda v, s=sl: v["slice"] == s, k) for k in keys}
        for ad in ADDRESS:
            margins["by_slice_x_address"][f"{sl}|{ad}"] = {
                k: total(lambda v, s=sl, a=ad: v["slice"] == s and v["address"] == a, k)
                for k in keys}
        for g in GOLDS:
            margins["by_slice_x_gold"][f"{sl}|{g}"] = {
                k: total(lambda v, s=sl, gg=g: v["slice"] == s and v["gold"] == gg, k)
                for k in keys}
    for ad in ADDRESS:
        margins["by_address"][ad] = {k: total(lambda v, a=ad: v["address"] == a, k) for k in keys}
    for g in GOLDS:
        margins["by_gold"][g] = {k: total(lambda v, gg=g: v["gold"] == gg, k) for k in keys}
    margins["all"] = {k: total(lambda v: True, k) for k in keys}

    return {"cells": cells, "margins": margins}


def prevalence(counted):
    """Share of rows carrying address, per slice, full and band. A ratio of two
    integers already reported above it -- no new quantity is introduced."""
    m = counted["margins"]
    out = {}
    for sl in SLICES:
        n = m["by_slice"][sl]["n"]
        nb = m["by_slice"][sl]["n_band_p_off_lt_0.5"]
        a = m["by_slice_x_address"][f"{sl}|address"]
        out[sl] = {
            "n_rows": n, "n_address": a["n"],
            "address_share_full": (a["n"] / n) if n else None,
            "n_rows_band": nb, "n_address_band": a["n_band_p_off_lt_0.5"],
            "address_share_band": (a["n_band_p_off_lt_0.5"] / nb) if nb else None,
        }
    n, nb = m["all"]["n"], m["all"]["n_band_p_off_lt_0.5"]
    a = m["by_address"]["address"]
    out["_both_slices"] = {
        "n_rows": n, "n_address": a["n"],
        "address_share_full": (a["n"] / n) if n else None,
        "n_rows_band": nb, "n_address_band": a["n_band_p_off_lt_0.5"],
        "address_share_band": (a["n_band_p_off_lt_0.5"] / nb) if nb else None,
    }
    return out


# ==============================================================================
# the run
# ==============================================================================

def _print_block(title, counted, prev=None):
    print(f"\n  {title}")
    print(f"    {'slice':<13}{'address':<12}{'gold':<6}{'n':>7}"
          f"{'n band<0.5':>12}{'n ==0.5':>10}{'n >0.5':>9}")
    for sl in SLICES:
        for ad in ADDRESS:
            for g in GOLDS:
                c = counted["cells"][f"{sl}|{ad}|{g}"]
                print(f"    {sl:<13}{ad:<12}{g:<6}{c['n']:>7}"
                      f"{c['n_band_p_off_lt_0.5']:>12}"
                      f"{c['n_at_p_off_exactly_0.5']:>10}{c['n_above_band']:>9}")
    m = counted["margins"]
    print(f"    {'-' * 59}")
    for sl in SLICES:
        for ad in ADDRESS:
            v = m["by_slice_x_address"][f"{sl}|{ad}"]
            print(f"    {sl:<13}{ad:<12}{'all':<6}{v['n']:>7}"
                  f"{v['n_band_p_off_lt_0.5']:>12}{v['n_at_p_off_exactly_0.5']:>10}"
                  f"{v['n'] - v['n_band_p_off_lt_0.5'] - v['n_at_p_off_exactly_0.5']:>9}")
    for sl in SLICES:
        v = m["by_slice"][sl]
        print(f"    {sl:<13}{'all':<12}{'all':<6}{v['n']:>7}"
              f"{v['n_band_p_off_lt_0.5']:>12}{v['n_at_p_off_exactly_0.5']:>10}"
              f"{v['n'] - v['n_band_p_off_lt_0.5'] - v['n_at_p_off_exactly_0.5']:>9}")
    for ad in ADDRESS:
        v = m["by_address"][ad]
        print(f"    {'both':<13}{ad:<12}{'all':<6}{v['n']:>7}"
              f"{v['n_band_p_off_lt_0.5']:>12}{v['n_at_p_off_exactly_0.5']:>10}"
              f"{v['n'] - v['n_band_p_off_lt_0.5'] - v['n_at_p_off_exactly_0.5']:>9}")
    for g in GOLDS:
        v = m["by_gold"][g]
        print(f"    {'both':<13}{'all':<12}{g:<6}{v['n']:>7}"
              f"{v['n_band_p_off_lt_0.5']:>12}{v['n_at_p_off_exactly_0.5']:>10}"
              f"{v['n'] - v['n_band_p_off_lt_0.5'] - v['n_at_p_off_exactly_0.5']:>9}")
    v = m["all"]
    print(f"    {'both':<13}{'all':<12}{'all':<6}{v['n']:>7}"
          f"{v['n_band_p_off_lt_0.5']:>12}{v['n_at_p_off_exactly_0.5']:>10}"
          f"{v['n'] - v['n_band_p_off_lt_0.5'] - v['n_at_p_off_exactly_0.5']:>9}")

    if prev:
        print(f"\n    address prevalence (share of rows carrying address)")
        print(f"      {'slice':<15}{'full n':>9}{'addr':>8}{'share':>9}"
              f"{'band n':>9}{'addr':>8}{'share':>9}")
        for k in list(SLICES) + ["_both_slices"]:
            p = prev[k]
            print(f"      {k:<15}{p['n_rows']:>9}{p['n_address']:>8}"
                  f"{p['address_share_full']:>9.4f}"
                  f"{p['n_rows_band']:>9}{p['n_address_band']:>8}"
                  f"{p['address_share_band']:>9.4f}")


def git_head():
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    print("=" * 96)
    print(f"PHASE 15 -- {STAGE}")
    print("COUNTS ONLY. No calibration, no signed gap, no ECE, no AUC, no recall,")
    print("no mean p_OFF, no verdict. DEV-ONLY; the official test set is spent and unread.")
    print("=" * 96)

    tok_sha = sha256_of(TOKENS_PATH)
    sets, doc = load_token_sets()
    print(f"\n[flag] data/deixis/address_tokens.json")
    print(f"       sha256 {tok_sha}")
    print(f"       matching rule: {doc['matching_rule']}")
    for name in ("primary", "extended", "third_person_deictic"):
        print(f"       {name:<21} {len(sets[name]):>2} tokens  "
              f"{sorted(sets[name])}")

    rows, split, gate_checks = load_and_gate()

    cal_ids, eval_ids = set(split["cal_row_ids"]), set(split["eval_row_ids"])
    halves = {"EVAL": [r for r in rows if r["row_id"] in eval_ids],
              "CAL": [r for r in rows if r["row_id"] in cal_ids]}
    for name, rs in halves.items():
        want = split["n_eval"] if name == "EVAL" else split["n_cal"]
        if len(rs) != want:
            sys.exit(f"ABORT: {name} has {len(rs)} rows, frozen split says {want}.")
    print(f"\n[split] CAL {len(halves['CAL'])} / EVAL {len(halves['EVAL'])} "
          f"from the frozen {SPLIT_PATH.name}")

    out = {}
    for half in ("EVAL", "CAL"):
        print("\n" + "=" * 96)
        print(f"{half} HALF -- (slice x address x gold), 8 cells + margins   *** DEV-ONLY ***")
        print("=" * 96)
        out[half] = {}
        for name in ("primary", "extended", "third_person_deictic"):
            counted = cell_counts(halves[half], sets[name])
            prev = prevalence(counted)
            role = ("PRIMARY (Stage 4 seven-token set)" if name == "primary"
                    else "pre-registered SENSITIVITY -- denominator only, not primary")
            _print_block(f"token set `{name}` ({len(sets[name])} tokens) -- {role}",
                         counted, prev)
            out[half][name] = {"token_set_size": len(sets[name]),
                               "tokens": sorted(sets[name]),
                               "role": role, **counted, "prevalence": prev}

    doc_out = {
        "run_id": RUN_ID, "stage": STAGE, "dev_only": True,
        "counts_only": "No calibration quantity, no signed gap, no ECE, no AUC, no recall, "
                       "no mean p_OFF, no per-cell OFF rate expressed as a calibration "
                       "figure, and no verdict appears in this file. Integers, shares of "
                       "those integers, and hashes.",
        "why_before_any_band": "The sensitivity denominators and the CAL-half fitting cell "
                               "sizes are recorded here, before any band or statistic is "
                               "fixed, so that a later choice of band cannot be made after "
                               "seeing what it would buy.",
        "flag": {"path": "data/deixis/address_tokens.json", "sha256": tok_sha,
                 "matching_rule": doc["matching_rule"],
                 "provenance": doc["provenance"],
                 "primary_set": doc["primary_set"],
                 "extended_set": doc["extended_set"],
                 "third_person_deictic_set": doc["third_person_deictic_set"]},
        "band_definition": "p_OFF < 0.5, strictly -- the frozen decision rule. Rows at "
                           "p_OFF == 0.5 exactly are counted separately per cell and are "
                           "excluded from the band by the literal `<`.",
        "provenance_gate": gate_checks,
        "split": {"file": "results/04_calibration/cal_eval_split.json",
                  "sha256": sha256_of(SPLIT_PATH),
                  "n_cal": split["n_cal"], "n_eval": split["n_eval"],
                  "seed": split["seed"], "dev_fingerprint": split["dev_fingerprint"]},
        "counts": out,
        "environment": {"python_version": platform.python_version(),
                        "git_head": git_head(),
                        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    }

    out_dir = ROOT / "results" / RUN_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cell_counts.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc_out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nwritten -> {path}")
    print(f"sha256   {sha256_of(path)}")
    print(f"\naddress_tokens.json sha256   {tok_sha}")
    return doc_out


if __name__ == "__main__":
    main()
