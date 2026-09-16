"""m4 stage 1b vs stage 1 - runs protocols/m4_stage1b_protocol.md, nothing else.

Stage 1 is the global cost-derived threshold on m3's raw binary offensive score.
Stage 1b conditions it on m1_lexicon.lexicon_hit_raw (t_hit / t_free), fitted on
the CAL half at stage 1's CAL flag count and compared on the EVAL half.

Deliberately does NOT:
  * run m3. Scores come from the study's dev_predictions.csv, sha256-checked: they
    are the scores stage 1 was fitted on (protocol §2)
  * open the official test set. Every input is dev; the split file is hashed, not read
  * choose the rule constants. r, the precision budget, the resample count and the
    seed are required arguments, so the protocol's command line is their only source
  * write thresholds.yaml. The decision is recorded; applying it is a reviewed change

    python -m eval.m4_stage1b --r 3 --precision-drop-budget 0.02 --n-boot 2000 --seed 42 \\
        --out eval/results/m4_stage1b.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from modules import registry
from pipeline.run import Pipeline

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
PROTOCOL = "protocols/m4_stage1b_protocol.md"

INPUTS = {
    "predictions": (REPO_ROOT / "diagnosis/results/01_baseline_berturk/dev_predictions.csv",
                    "a2f5bddf12dcfbc4f4ffa1f0bbfd9d37adcffaec0518d3aa627864a0538a6346"),
    "cal_eval_split": (REPO_ROOT / "diagnosis/results/04_calibration/cal_eval_split.json",
                       "6d1e3ed7f7285eb871ef9cf7876fc629c7dabc8546245c39151290e0a72af899"),
    "frozen_slice": (AI_ROOT / "eval/frozen/study_slice_dev.json",
                     "94754632fb66d543b7c1e84bc4e396b65585f8adba90a4f2fc87aca8f2acbed8"),
    # Hashed only, never read: it also indexes the test split.
    "dev_split": (REPO_ROOT / "diagnosis/data/splits/split_seed42.json",
                  "73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2"),
}

# Integrity checks, protocol §2. Values from the stage-1 derivation file and
# cal_eval_split.json's own reproduction checks.
EXPECTED: dict[str, Any] = {
    "n_dev": 4764, "n_half": 2382,
    "dev_fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4",
    "eval_off": 460, "eval_not": 1922, "eval_frozen_free": 2073, "eval_frozen_hit": 309,
    "stage1_t": 0.320188, "stage1_eval_confusion": {"tp": 343, "fp": 184, "fn": 117, "tn": 1738},
}

LEXICON_MODULES = ("m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon")


class ProtocolStop(Exception):
    """An integrity check failed: the protocol says stop, produce no number."""


@dataclass(frozen=True)
class Row:
    row_id: str
    score: float
    off: bool
    frozen_free: bool   # PRIMARY slice (decides)
    terlik_free: bool   # SECONDARY slice, and the stage-1b condition (lexicon_hit_raw false)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(ok: bool, what: str) -> None:
    if not ok:
        raise ProtocolStop(what)


def protocol_commit() -> str:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(AI_ROOT), *args], capture_output=True, text=True)
    commit = git("log", "-1", "--format=%H", "--", PROTOCOL).stdout.strip()
    require(bool(commit), f"{PROTOCOL} is not committed - the protocol must exist before any number")
    require(git("diff", "--quiet", "HEAD", "--", PROTOCOL).returncode == 0,
            f"{PROTOCOL} has uncommitted changes")
    return commit


# -- data -------------------------------------------------------------------
def load_rows() -> tuple[list[dict[str, str]], set[str], set[str], dict[str, str], dict[str, Any]]:
    hashes = {}
    for key, (path, want) in INPUTS.items():
        got = sha256(path)
        require(got == want, f"sha256 mismatch for {path}: {got}")
        hashes[key] = {"file": str(path.relative_to(REPO_ROOT).as_posix()), "sha256": got}

    with open(INPUTS["predictions"][0], encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    ids = [r["row_id"] for r in csv_rows]
    require(len(ids) == EXPECTED["n_dev"] and len(set(ids)) == len(ids), "CSV row count / unique row_ids")

    split = json.loads(INPUTS["cal_eval_split"][0].read_text(encoding="utf-8"))
    cal, eval_ = set(split["cal_row_ids"]), set(split["eval_row_ids"])
    require(len(cal) == EXPECTED["n_half"] and len(eval_) == EXPECTED["n_half"], "CAL/EVAL sizes")
    require(not cal & eval_ and cal | eval_ == set(ids), "CAL/EVAL disjoint and covering the CSV")

    frozen = json.loads(INPUTS["frozen_slice"][0].read_text(encoding="utf-8"))
    require(frozen["split"]["dev_fingerprint"] == EXPECTED["dev_fingerprint"], "frozen slice dev fingerprint")
    require(frozen["verified_against"]["sha256"] == INPUTS["predictions"][1], "frozen slice verified_against")
    slice_by_id = dict(frozen["rows"])
    require(set(slice_by_id) == set(ids), "frozen slice covers exactly the CSV row_ids")
    return csv_rows, cal, eval_, slice_by_id, hashes


def terlik_hits(texts: list[str]) -> tuple[list[bool], dict[str, str]]:
    """lexicon_hit_raw exactly as the runtime pipeline publishes it (protocol §3)."""
    names = [e.name.value for e in registry.PIPELINE_ORDER if e.name.value in LEXICON_MODULES]
    modules = [registry.build(n) for n in names]
    pipeline = Pipeline(modules=modules)
    versions = {m.name.value: m.version for m in pipeline.modules}
    hits = []
    for text in texts:
        result = pipeline.analyze(text)
        degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
        require("m1_lexicon" not in degraded, f"m1_lexicon degraded: {degraded.get('m1_lexicon')}")
        value = result.signals.get("m1_lexicon", {}).get("lexicon_hit_raw")
        require(isinstance(value, bool), f"lexicon_hit_raw not a bool: {value!r}")
        hits.append(value)
    return hits, versions


# -- fit (CAL) ----------------------------------------------------------------
@dataclass(frozen=True)
class Option:
    t: float
    tp: int
    fp: int

    @property
    def flagged(self) -> int:
        return self.tp + self.fp


def sweep(rows: list[Row]) -> list[Option]:
    """Every distinct score as candidate t, flag iff score > t (protocol §4)."""
    ordered = sorted(rows, key=lambda r: r.score, reverse=True)
    options, tp, fp, i = [], 0, 0, 0
    while i < len(ordered):
        t = ordered[i].score
        options.append(Option(t, tp, fp))   # rows strictly above t are already counted
        while i < len(ordered) and ordered[i].score == t:
            tp, fp = tp + ordered[i].off, fp + (not ordered[i].off)
            i += 1
    return options


def cost_numerator(fp: int, fn: int, r: float) -> float:
    return fp + r * fn


def fit_stage1(cal: list[Row], r: float) -> Option:
    positives = sum(row.off for row in cal)
    # min cost, ties toward the lower t
    return min(sweep(cal), key=lambda o: (cost_numerator(o.fp, positives - o.tp, r), o.t))


def fit_stage1b(cal: list[Row], r: float, k: int) -> tuple[Option, Option, int]:
    hit_rows = [row for row in cal if not row.terlik_free]
    free_rows = [row for row in cal if row.terlik_free]
    positives = sum(row.off for row in cal)
    best_key, best = None, None
    free_options = sweep(free_rows)
    for oh in sweep(hit_rows):
        for of in free_options:
            count = oh.flagged + of.flagged
            if count > k:
                continue
            key = (-count, cost_numerator(oh.fp + of.fp, positives - oh.tp - of.tp, r), oh.t, of.t)
            if best_key is None or key < best_key:
                best_key, best = key, (oh, of)
    require(best is not None, "no stage-1b pair at or below stage 1's CAL flag count")
    return best[0], best[1], -best_key[0]


# -- evaluate (EVAL) -----------------------------------------------------------
def flags_stage1(t: float):
    return lambda row: row.score > t


def flags_stage1b(t_hit: float, t_free: float):
    return lambda row: row.score > (t_free if row.terlik_free else t_hit)


def confusion(rows: list[Row], flag) -> dict[str, int]:
    c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for row in rows:
        c[("tp" if flag(row) else "fn") if row.off else ("fp" if flag(row) else "tn")] += 1
    return c


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def metrics(rows: list[Row], flag, r: float) -> dict[str, Any]:
    overall = confusion(rows, flag)
    out: dict[str, Any] = {
        "confusion": overall,
        "flagged": overall["tp"] + overall["fp"],
        "flag_rate": ratio(overall["tp"] + overall["fp"], len(rows)),
        "precision": ratio(overall["tp"], overall["tp"] + overall["fp"]),
        "recall": ratio(overall["tp"], overall["tp"] + overall["fn"]),
        "fpr": ratio(overall["fp"], overall["fp"] + overall["tn"]),
        "cost": cost_numerator(overall["fp"], overall["fn"], r) / len(rows),
    }
    for name, attr in (("primary_frozen", "frozen_free"), ("secondary_terlik", "terlik_free")):
        free = confusion([row for row in rows if getattr(row, attr)], flag)
        hit = confusion([row for row in rows if not getattr(row, attr)], flag)
        free_recall = ratio(free["tp"], free["tp"] + free["fn"])
        hit_recall = ratio(hit["tp"], hit["tp"] + hit["fn"])
        out[name] = {
            "lexicon_free_recall": free_recall, "lexicon_hit_recall": hit_recall,
            "slice_gap": None if free_recall is None or hit_recall is None else hit_recall - free_recall,
            "lexicon_free": free, "lexicon_hit": hit,
        }
    return out


def percentile_ci(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    b = len(ordered)
    return ordered[math.floor(0.025 * b)], ordered[math.ceil(0.975 * b) - 1]


def paired_bootstrap(rows: list[Row], flag_1, flag_1b, n_boot: int, seed: int) -> dict[str, Any]:
    """Protocol §5: same resample for both stages; one choices call of k = n per resample."""
    n = len(rows)
    per_row = [(row.off, row.frozen_free, row.terlik_free, flag_1(row), flag_1b(row)) for row in rows]
    rng = random.Random(seed)
    deltas: dict[str, list[float]] = {"primary": [], "secondary": [], "precision": []}
    dropped = {"primary": 0, "secondary": 0, "precision": 0}
    for _ in range(n_boot):
        sample = rng.choices(range(n), k=n)
        acc = {"primary": [0, 0, 0], "secondary": [0, 0, 0]}   # [free OFF, tp stage 1, tp stage 1b]
        prec = [0, 0, 0, 0]                                     # tp1, flagged1, tp1b, flagged1b
        for i in sample:
            off, frozen_free, terlik_free, f1, f1b = per_row[i]
            for key, free in (("primary", frozen_free), ("secondary", terlik_free)):
                if free and off:
                    acc[key][0] += 1
                    acc[key][1] += f1
                    acc[key][2] += f1b
            prec[0] += off and f1
            prec[1] += f1
            prec[2] += off and f1b
            prec[3] += f1b
        for key, (pos, tp1, tp1b) in acc.items():
            if pos:
                deltas[key].append((tp1b - tp1) / pos)
            else:
                dropped[key] += 1
        if prec[1] and prec[3]:
            deltas["precision"].append(prec[2] / prec[3] - prec[0] / prec[1])
        else:
            dropped["precision"] += 1
    return {
        "n_boot": n_boot, "seed": seed,
        "primary_free_recall_delta_ci95": percentile_ci(deltas["primary"]),
        "secondary_free_recall_delta_ci95": percentile_ci(deltas["secondary"]),
        "precision_delta_ci95": percentile_ci(deltas["precision"]),
        "dropped_resamples": dropped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.m4_stage1b")
    parser.add_argument("--r", type=float, required=True)
    parser.add_argument("--precision-drop-budget", type=float, required=True)
    parser.add_argument("--n-boot", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    started = time.time()

    try:
        commit = protocol_commit()
        csv_rows, cal_ids, eval_ids, slice_by_id, hashes = load_rows()
        hits, versions = terlik_hits([r["text"] for r in csv_rows])
        rows = [Row(row_id=r["row_id"], score=float(r["confidence"]), off=r["gold"] == "OFF",
                    frozen_free=slice_by_id[r["row_id"]] == "lexicon_free", terlik_free=not hit)
                for r, hit in zip(csv_rows, hits)]
        cal = [row for row in rows if row.row_id in cal_ids]
        ev = [row for row in rows if row.row_id in eval_ids]

        require(sum(row.off for row in ev) == EXPECTED["eval_off"]
                and sum(not row.off for row in ev) == EXPECTED["eval_not"], "EVAL class counts")
        require(sum(row.frozen_free for row in ev) == EXPECTED["eval_frozen_free"]
                and sum(not row.frozen_free for row in ev) == EXPECTED["eval_frozen_hit"], "EVAL frozen slice counts")

        s1 = fit_stage1(cal, args.r)
        require(s1.t == EXPECTED["stage1_t"], f"stage-1 refit gave t = {s1.t}")
        require(confusion(ev, flags_stage1(s1.t)) == EXPECTED["stage1_eval_confusion"], "stage-1 EVAL confusion")
    except ProtocolStop as stop:
        print(f"PROTOCOL STOP - no number produced: {stop}", file=sys.stderr)
        return 2

    k = s1.flagged
    oh, of, k_star = fit_stage1b(cal, args.r, k)
    flag_1, flag_1b = flags_stage1(s1.t), flags_stage1b(oh.t, of.t)
    eval_1, eval_1b = metrics(ev, flag_1, args.r), metrics(ev, flag_1b, args.r)
    boot = paired_bootstrap(ev, flag_1, flag_1b, args.n_boot, args.seed)

    delta = eval_1b["primary_frozen"]["lexicon_free_recall"] - eval_1["primary_frozen"]["lexicon_free_recall"]
    precision_drop = eval_1["precision"] - eval_1b["precision"]
    ci_excludes_zero = boot["primary_free_recall_delta_ci95"][0] > 0
    within_budget = precision_drop <= args.precision_drop_budget
    adopt = ci_excludes_zero and within_budget

    result = {
        "protocol": PROTOCOL, "protocol_commit": commit,
        "command": "python -m eval.m4_stage1b " + " ".join(sys.argv[1:] if argv is None else argv),
        "inputs": hashes, "module_versions": versions,
        "fit_cal": {
            "n": len(cal), "r": args.r,
            "stage1": {"t": s1.t, "flagged": k, "cost": cost_numerator(s1.fp, sum(x.off for x in cal) - s1.tp, args.r) / len(cal)},
            "stage1b": {"t_hit": oh.t, "t_free": of.t, "flagged": k_star, "flag_count_gap": k - k_star,
                        "flagged_hit": oh.flagged, "flagged_free": of.flagged,
                        "cost": cost_numerator(oh.fp + of.fp, sum(x.off for x in cal) - oh.tp - of.tp, args.r) / len(cal)},
        },
        "eval": {"n": len(ev), "stage1": eval_1, "stage1b": eval_1b},
        "slice_agreement_eval": {
            f"frozen_{'free' if ff else 'hit'}__terlik_{'free' if tf else 'hit'}":
                sum(1 for row in ev if row.frozen_free == ff and row.terlik_free == tf)
            for ff in (True, False) for tf in (True, False)
        },
        "ties_at_runtime_rule_eval": {
            "stage1_rows_equal_t": sum(1 for row in ev if row.score == s1.t),
            "stage1b_hit_rows_equal_t_hit": sum(1 for row in ev if not row.terlik_free and row.score == oh.t),
            "stage1b_free_rows_equal_t_free": sum(1 for row in ev if row.terlik_free and row.score == of.t),
        },
        "bootstrap": boot,
        "decision": {
            "primary_free_recall_delta": delta,
            "primary_ci95_lower_gt_0": ci_excludes_zero,
            "precision_drop": precision_drop,
            "precision_drop_budget": args.precision_drop_budget,
            "precision_within_budget": within_budget,
            "adopt_stage1b": adopt,
            "verdict": "ADOPT stage 1b" if adopt else "KEEP stage 1",
        },
        "note": "EVAL half was already used in the study to evaluate S1b; this CI is conditional on that reuse.",
        "runtime_s": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["fit_cal"], indent=2))
    print(json.dumps(result["decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
