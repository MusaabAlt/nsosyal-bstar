"""terlik (m1, balanced) versus the historical karaliste on the frozen dev split -
runs protocols/m1_terlik_vs_karaliste_protocol.md, nothing else.

    python -m eval.m1_terlik_vs_karaliste --out eval/results/m1_terlik_vs_karaliste.json [--n-boot 2000 --seed 42]

Inputs are hashed and must match the protocol; the official test set is never read. Output holds
counts, recall / FPR / precision of each lexicon as a predictor of OFF with bootstrap CIs, the
paired differences, the 2x2 disagreement tables and 20 examples per direction (matched surfaces
only, no corpus text).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
PROTOCOL = "protocols/m1_terlik_vs_karaliste_protocol.md"
FROZEN_SLICE = AI_ROOT / "eval/frozen/study_slice_dev.json"
DERIVED = AI_ROOT / "eval/derived/m1_lexicon_dev_seed42.json"
PREDICTIONS = REPO_ROOT / "diagnosis/results/01_baseline_berturk/dev_predictions.csv"
EXPECTED_SHA256 = {
    "frozen_slice": "94754632fb66d543b7c1e84bc4e396b65585f8adba90a4f2fc87aca8f2acbed8",   # eval/m4_stage1b.py INPUTS
    "predictions": "a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346",
}


class ProtocolStop(Exception):
    """An integrity check failed: stop, write nothing."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def load_inputs() -> tuple[dict[str, bool], dict[str, dict[str, Any]], dict[str, bool], dict[str, str]]:
    hashes = {}
    for name, path in (("frozen_slice", FROZEN_SLICE), ("predictions", PREDICTIONS)):
        if not path.exists():
            raise ProtocolStop(f"missing input {path}")
        hashes[name] = sha256(path)
        if hashes[name] != EXPECTED_SHA256[name]:
            raise ProtocolStop(f"{name} sha256 {hashes[name]} != protocol {EXPECTED_SHA256[name]}")
    if not DERIVED.exists():
        raise ProtocolStop(f"missing derived labels {DERIVED}")
    derived = json.loads(DERIVED.read_text(encoding="utf-8"))
    hashes["derived"] = sha256(DERIVED)
    if not derived["protocol"].get("committed_and_unchanged"):
        raise ProtocolStop("derived labels were generated against an uncommitted or changed protocol")
    frozen = json.loads(FROZEN_SLICE.read_text(encoding="utf-8"))
    karaliste = {str(rid): (slice_ == "lexicon_hit") for rid, slice_ in frozen["rows"]}
    terlik = {str(r["row_id"]): {"hit": bool(r["lexicon_hit_raw"]), "hit_any": bool(r["lexicon_hit"]),
                                 "hit_norm": bool(r.get("lexicon_hit_norm")), "roots": r.get("roots", []),
                                 "surfaces": [m.get("surface", "") for m in r.get("matches", [])],
                                 "collision": bool(r.get("collisions"))} for r in derived["rows"]}
    gold: dict[str, bool] = {}
    with open(PREDICTIONS, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            gold[str(row["row_id"])] = row["gold"].strip().upper() == "OFF"
    ids = list(karaliste)
    expected_n = frozen["counts"]["n"]                  # the frozen file states its own row count
    if not (set(ids) == set(terlik) == set(gold)) or len(ids) != expected_n:
        raise ProtocolStop(f"id sets differ: frozen {len(karaliste)} (declares {expected_n}) terlik {len(terlik)} "
                           f"gold {len(gold)}")
    hashes["derived_header"] = {k: derived.get(k) for k in ("generator", "engine", "channels")}
    return karaliste, terlik, gold, hashes


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered), max(1, round(q / 100 * len(ordered)))) - 1]


def rates(hit: list[bool], off: list[bool], idx: list[int]) -> dict[str, float | None]:
    tp = sum(1 for i in idx if hit[i] and off[i]); fp = sum(1 for i in idx if hit[i] and not off[i])
    fn = sum(1 for i in idx if not hit[i] and off[i]); tn = sum(1 for i in idx if not hit[i] and not off[i])
    return {"recall": tp / (tp + fn) if tp + fn else None, "fpr": fp / (fp + tn) if fp + tn else None,
            "precision": tp / (tp + fp) if tp + fp else None}


def with_ci(hit: list[bool], off: list[bool], n_boot: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(hit)
    point = rates(hit, off, list(range(n)))
    samples: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        for k, v in rates(hit, off, idx).items():
            if v is not None:
                samples[k].append(v)
    return {k: {"value": v, "ci_low": _pct(samples[k], 2.5), "ci_high": _pct(samples[k], 97.5)} for k, v in point.items()}


def paired_delta(hit_a: list[bool], hit_b: list[bool], off: list[bool], n_boot: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(off)
    full = list(range(n))
    point = {k: rates(hit_b, off, full)[k] - rates(hit_a, off, full)[k] for k in ("recall", "fpr")}
    samples: dict[str, list[float]] = {"recall": [], "fpr": []}
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        a, b = rates(hit_a, off, idx), rates(hit_b, off, idx)
        for k in samples:
            if a[k] is not None and b[k] is not None:
                samples[k].append(b[k] - a[k])
    return {k: {"value": v, "ci_low": _pct(samples[k], 2.5), "ci_high": _pct(samples[k], 97.5)} for k, v in point.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.m1_terlik_vs_karaliste")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        karaliste, terlik, gold, hashes = load_inputs()
    except ProtocolStop as exc:
        print(f"PROTOCOL STOP: {exc}", file=sys.stderr)
        return 2

    ids = list(karaliste)
    k_hit = [karaliste[i] for i in ids]
    t_hit = [terlik[i]["hit"] for i in ids]
    t_any = [terlik[i]["hit_any"] for i in ids]
    off = [gold[i] for i in ids]
    both = sum(1 for k, t in zip(k_hit, t_hit) if k and t)
    only_k = [i for i, k, t in zip(ids, k_hit, t_hit) if k and not t]
    only_t = [i for i, k, t in zip(ids, k_hit, t_hit) if t and not k]
    neither = sum(1 for k, t in zip(k_hit, t_hit) if not k and not t)
    off_idx = [n for n, o in enumerate(off) if o]
    table_off = {"both": sum(1 for n in off_idx if k_hit[n] and t_hit[n]),
                 "karaliste_only": sum(1 for n in off_idx if k_hit[n] and not t_hit[n]),
                 "terlik_only": sum(1 for n in off_idx if t_hit[n] and not k_hit[n]),
                 "neither": sum(1 for n in off_idx if not k_hit[n] and not t_hit[n])}
    terlik_free_with_collision = sum(1 for i in ids if not terlik[i]["hit"] and terlik[i]["collision"])
    n_terlik_free = sum(1 for i in ids if not terlik[i]["hit"])

    report = {
        "protocol": {"file": PROTOCOL, "sha256": sha256(AI_ROOT / PROTOCOL),
                     "commit": git("log", "-1", "--format=%H", "--", f"AI/{PROTOCOL}") or None},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_head": git("rev-parse", "HEAD") or None,
        "inputs": {"frozen_slice": {"path": str(FROZEN_SLICE.relative_to(AI_ROOT)), "sha256": hashes["frozen_slice"]},
                   "derived_labels": {"path": str(DERIVED.relative_to(AI_ROOT)), "sha256": hashes["derived"]},
                   "predictions": {"path": "diagnosis/results/01_baseline_berturk/dev_predictions.csv", "sha256": hashes["predictions"]}},
        "bootstrap": {"n_boot": args.n_boot, "seed": args.seed, "unit": "row", "ci": 0.95},
        "n_rows": len(ids), "n_off": len(off_idx), "n_not": len(ids) - len(off_idx),
        "counts": {"karaliste_hits": sum(k_hit), "terlik_hits": sum(t_hit)},
        "derived_labels_generator": {"version": (hashes["derived_header"].get("generator") or {}).get("version"),
                                     "module_versions": (hashes["derived_header"].get("engine") or {}).get("module_versions"),
                                     "normalized_channel_available": ((hashes["derived_header"].get("channels") or {})
                                                                      .get("normalized") or {}).get("available")},
        "karaliste": with_ci(k_hit, off, args.n_boot, args.seed),
        "terlik": with_ci(t_hit, off, args.n_boot, args.seed),
        "terlik_minus_karaliste": paired_delta(k_hit, t_hit, off, args.n_boot, args.seed),
        # Amendment 2026-09-18: ADDED next to the pre-registered raw-channel headline, never in its place.
        # terlik with lexicon_hit (raw OR normalized) - the predicate the A-head pseudo-label uses.
        "terlik_any_channel": {
            "predictor": "lexicon_hit (raw OR normalized), the A-head pseudo-label predicate",
            "hits": sum(t_any), "normalized_only_rows": sum(1 for a, r in zip(t_any, t_hit) if a and not r),
            "raw_only_rows": sum(1 for i in ids if terlik[i]["hit"] and not terlik[i]["hit_norm"]),
            **with_ci(t_any, off, args.n_boot, args.seed),
            "minus_karaliste": paired_delta(k_hit, t_any, off, args.n_boot, args.seed),
        },
        "disagreement": {
            "all_rows": {"both": both, "karaliste_only": len(only_k), "terlik_only": len(only_t), "neither": neither},
            "gold_off_rows": table_off,
            "terlik_free_rows_with_substring_collision": {"n": terlik_free_with_collision, "of": n_terlik_free,
                                                          "share": terlik_free_with_collision / n_terlik_free if n_terlik_free else None},
            "examples_karaliste_only": [{"row_id": i, "gold": "OFF" if gold[i] else "NOT",
                                         "terlik_collision": terlik[i]["collision"]} for i in only_k[:20]],
            "examples_terlik_only": [{"row_id": i, "gold": "OFF" if gold[i] else "NOT",
                                      "roots": terlik[i]["roots"], "surfaces": terlik[i]["surfaces"]} for i in only_t[:20]],
        },
        "decision_rule": "none (protocol §3): comparison only; the frozen slice stays karaliste's",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    k, t, d = report["karaliste"], report["terlik"], report["terlik_minus_karaliste"]
    print(f"rows={len(ids)} off={len(off_idx)}  karaliste hits={sum(k_hit)} recall={k['recall']['value']:.4f} "
          f"fpr={k['fpr']['value']:.4f} | terlik hits={sum(t_hit)} recall={t['recall']['value']:.4f} fpr={t['fpr']['value']:.4f} | "
          f"delta recall={d['recall']['value']:+.4f} [{d['recall']['ci_low']:+.4f}, {d['recall']['ci_high']:+.4f}] "
          f"fpr={d['fpr']['value']:+.4f} [{d['fpr']['ci_low']:+.4f}, {d['fpr']['ci_high']:+.4f}]")
    print(f"disagreement all rows: {report['disagreement']['all_rows']}  gold-OFF: {table_off}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
