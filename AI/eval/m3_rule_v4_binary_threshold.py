"""binary_offensive (stage 1) for m3-berturk-multihead-a-rule-v4-20260918-163728 - runs
protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md: the methodology of
protocols/threshold_derivation_binary_offensive_stage1.md, unchanged, applied to the new artifact.

    python -m eval.m3_rule_v4_binary_threshold --r 3 --n-boot 10000 --seed 42 \\
        --out eval/results/m3_rule_v4_binary_threshold.json

Steps, each a stop condition when it fails (no number is produced):
  1. integrity: input sha256s; 4,764 dev rows; CAL / EVAL halves of 2,382, disjoint and covering;
     EVAL 460 OFF / 1,922 NOT
  2. methodology check: the same fit on the study's own baseline scores (dev_predictions.csv) must
     reproduce t = 0.320188 and EVAL tp 343 / fp 184 / fn 117 / tn 1,738
  3. scores: every dev row through the DEPLOYED m3 (`EncoderModule()`, raw channel = the CSV text,
     exactly as the 2026-09-15 equivalence check did); the loaded artifact must be rule-v4 with the
     pinned weights sha256
  4. fit on CAL only: candidates = the distinct CAL scores, flag iff score > t, minimise
     (FP + r * FN) / N_CAL, ties toward the lower t
  5. EVAL, once: confusion, precision, recall, F1, macro-F1, FPR, cost, flagged; rows exactly at t
  6. stability: bootstrap of the CAL fit (C12-9)

Deliberately does NOT: open the official test set (the split file is hashed, never read), read the
500-row A reference or any annotation file, choose anything on EVAL, or write thresholds.yaml.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contracts.module_api import Context
from modules.m3_encoder import module as m3

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
PROTOCOL = "protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md"
BASE_PROTOCOL = "protocols/threshold_derivation_binary_offensive_stage1.md"

INPUTS = {
    "predictions": (REPO_ROOT / "diagnosis/results/01_baseline_berturk/dev_predictions.csv",
                    "a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346"),
    "cal_eval_split": (REPO_ROOT / "diagnosis/results/04_calibration/cal_eval_split.json",
                       "6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899"),
    # Hashed only, never read: it also indexes the test split.
    "dev_split": (REPO_ROOT / "diagnosis/data/splits/split_seed42.json",
                  "73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2"),
}
EXPECTED: dict[str, Any] = {
    "n_dev": 4764, "n_half": 2382, "eval_off": 460, "eval_not": 1922,
    "baseline_t": 0.320188, "baseline_eval_confusion": {"tp": 343, "fp": 184, "fn": 117, "tn": 1738},
}


class ProtocolStop(Exception):
    """An integrity check failed: the protocol says stop, produce no number."""


@dataclass(frozen=True)
class Row:
    row_id: str
    score: float
    off: bool


@dataclass(frozen=True)
class Option:
    t: float
    tp: int
    fp: int


def require(ok: bool, what: str) -> None:
    if not ok:
        raise ProtocolStop(what)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# -- fit (CAL) and evaluate (EVAL), protocol §3-§4 ------------------------------------------------
def sweep(rows: list[Row]) -> list[Option]:
    """Every distinct score as candidate t; flag iff score > t."""
    ordered = sorted(rows, key=lambda r: r.score, reverse=True)
    options, tp, fp, i = [], 0, 0, 0
    while i < len(ordered):
        t = ordered[i].score
        options.append(Option(t, tp, fp))   # rows strictly above t are already counted
        while i < len(ordered) and ordered[i].score == t:
            tp, fp = tp + ordered[i].off, fp + (not ordered[i].off)
            i += 1
    return options


def fit(cal: list[Row], r: float) -> Option:
    positives = sum(row.off for row in cal)
    return min(sweep(cal), key=lambda o: (o.fp + r * (positives - o.tp), o.t))   # ties toward the lower t


def ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def f1(p: float | None, rec: float | None) -> float | None:
    return None if p is None or rec is None or not p + rec else 2 * p * rec / (p + rec)


def evaluate(rows: list[Row], t: float, r: float) -> dict[str, Any]:
    c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for row in rows:
        flagged = row.score > t
        c[("tp" if flagged else "fn") if row.off else ("fp" if flagged else "tn")] += 1
    precision, recall = ratio(c["tp"], c["tp"] + c["fp"]), ratio(c["tp"], c["tp"] + c["fn"])
    not_precision, not_recall = ratio(c["tn"], c["tn"] + c["fn"]), ratio(c["tn"], c["tn"] + c["fp"])
    f1_off, f1_not = f1(precision, recall), f1(not_precision, not_recall)
    return {
        "n": len(rows), "confusion": c, "flagged": c["tp"] + c["fp"],
        "precision": precision, "recall": recall, "f1": f1_off,
        "macro_f1": None if f1_off is None or f1_not is None else (f1_off + f1_not) / 2,
        "fpr": ratio(c["fp"], c["fp"] + c["tn"]), "cost": (c["fp"] + r * c["fn"]) / len(rows),
        "rows_scoring_exactly_t": sum(row.score == t for row in rows),
    }


def percentile_ci(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    b = len(ordered)
    return ordered[math.floor(0.025 * b)], ordered[math.ceil(0.975 * b) - 1]


def bootstrap_t(cal: list[Row], r: float, n_boot: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    fitted = [fit([cal[rng.randrange(len(cal))] for _ in cal], r).t for _ in range(n_boot)]
    low, high = percentile_ci(fitted)
    return {"n_boot": n_boot, "seed": seed, "t_ci95": [low, high], "t_median": sorted(fitted)[len(fitted) // 2]}


# -- data ----------------------------------------------------------------------------------------
def load_inputs() -> tuple[list[dict[str, str]], set[str], set[str], dict[str, Any]]:
    hashes = {}
    for key, (path, want) in INPUTS.items():
        got = sha256(path)
        require(got == want, f"sha256 mismatch for {path}: {got}")
        hashes[key] = {"file": path.relative_to(REPO_ROOT).as_posix(), "sha256": got}
    with open(INPUTS["predictions"][0], encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    ids = [row["row_id"] for row in csv_rows]
    require(len(ids) == EXPECTED["n_dev"] and len(set(ids)) == len(ids), "CSV row count / unique row_ids")
    split = json.loads(INPUTS["cal_eval_split"][0].read_text(encoding="utf-8"))
    cal, eval_ = set(split["cal_row_ids"]), set(split["eval_row_ids"])
    require(len(cal) == EXPECTED["n_half"] and len(eval_) == EXPECTED["n_half"], "CAL / EVAL sizes")
    require(not cal & eval_ and cal | eval_ == set(ids), "CAL / EVAL disjoint and covering the CSV")
    gold = {row["row_id"]: row["gold"] for row in csv_rows}
    require(set(gold.values()) == {"OFF", "NOT"}, "gold labels are OFF / NOT")
    require(sum(gold[i] == "OFF" for i in eval_) == EXPECTED["eval_off"]
            and sum(gold[i] == "NOT" for i in eval_) == EXPECTED["eval_not"], "EVAL class counts")
    return csv_rows, cal, eval_, hashes


def rows_from(csv_rows: list[dict[str, str]], scores: dict[str, float], ids: set[str]) -> list[Row]:
    return [Row(row["row_id"], scores[row["row_id"]], row["gold"] == "OFF") for row in csv_rows if row["row_id"] in ids]


def score_with_deployed_m3(csv_rows: list[dict[str, str]], cache: Path | None) -> tuple[dict[str, float], dict[str, Any]]:
    module = m3.EncoderModule()
    module.load()
    artifact = getattr(module, "_artifact_id", None)
    require(artifact == m3.DEPLOYED_ID, f"deployed m3 loaded {artifact!r}, not {m3.DEPLOYED_ID}")
    provenance = {"artifact_id": artifact, "weights_sha256": m3.DEPLOYED_WEIGHTS_SHA256,
                  "module_version": m3.EncoderModule.version, "channel": "raw (ctx.text = CSV text)"}
    if cache is not None and cache.is_file():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("provenance") == provenance and len(cached.get("scores", {})) == len(csv_rows):
            return {k: float(v) for k, v in cached["scores"].items()}, {**provenance, "scores_from_cache": str(cache)}
    scores, failures, started = {}, [], time.time()
    for n, row in enumerate(csv_rows, 1):
        out = module.process(Context(text=row["text"]))
        value = out.signals.get("raw_score")
        if not out.ok or isinstance(value, bool) or not isinstance(value, float):
            failures.append(row["row_id"])
            continue
        scores[row["row_id"]] = value
        if not n % 500:
            print(f"  scored {n}/{len(csv_rows)} in {time.time() - started:.0f} s", file=sys.stderr, flush=True)
    require(not failures, f"m3 failed on {len(failures)} dev rows, e.g. {failures[:5]}")
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"provenance": provenance, "scores": scores}), encoding="utf-8")
    return scores, {**provenance, "scoring_seconds": round(time.time() - started, 1)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.m3_rule_v4_binary_threshold")
    parser.add_argument("--r", type=float, required=True, help="cost ratio: a false negative costs r false positives")
    parser.add_argument("--n-boot", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scores-cache", type=Path, default=None,
                        help="row_id -> score cache, reused only when its provenance matches the loaded artifact")
    args = parser.parse_args(argv)
    try:
        csv_rows, cal_ids, eval_ids, hashes = load_inputs()
        # 2. methodology check on the study's own scores (the baseline derivation, reproduced)
        baseline = {row["row_id"]: float(row["confidence"]) for row in csv_rows}
        base_fit = fit(rows_from(csv_rows, baseline, cal_ids), args.r)
        base_eval = evaluate(rows_from(csv_rows, baseline, eval_ids), base_fit.t, args.r)
        require(base_fit.t == EXPECTED["baseline_t"], f"methodology check: baseline refit gave t = {base_fit.t}")
        require(base_eval["confusion"] == EXPECTED["baseline_eval_confusion"],
                f"methodology check: baseline EVAL confusion {base_eval['confusion']}")
        # 3-6. the deployed artifact
        scores, provenance = score_with_deployed_m3(csv_rows, args.scores_cache)
        cal, eval_ = rows_from(csv_rows, scores, cal_ids), rows_from(csv_rows, scores, eval_ids)
        chosen = fit(cal, args.r)
        result = {
            "protocol": PROTOCOL, "base_protocol": BASE_PROTOCOL, "inputs": hashes, "m3": provenance,
            "rule": {"r": args.r, "flag": "score > t", "candidates": "distinct CAL scores", "ties": "lower t",
                     "fitted_on": "CAL half only"},
            "methodology_check": {"baseline_t": base_fit.t, "baseline_eval_confusion": base_eval["confusion"],
                                  "reproduces_protocol": True},
            "threshold": chosen.t,
            "cal": evaluate(cal, chosen.t, args.r),
            "eval": evaluate(eval_, chosen.t, args.r),
            "eval_at_the_old_baseline_threshold_descriptive_only": evaluate(eval_, EXPECTED["baseline_t"], args.r),
            "stability": bootstrap_t(cal, args.r, args.n_boot, args.seed),
            "not_read": ["official test set (split file hashed only)", "500-row A reference", "annotation files"],
        }
    except ProtocolStop as stop:
        print(f"PROTOCOL STOP: {stop}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("threshold", "eval", "stability")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
