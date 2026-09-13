"""ModuleEvaluator: measure ONE module alone (CLAUDE.md rule 7).

Fixture format (jsonl, one item per line):
  {"id": "...", "text": "...",
   "expected": ["A2", "ZERO_WIDTH", "NEGATION", "target:individual"],
   "context": {"charsafe_text": "...", "normalized_text": "...", "signals": {}},  # optional
   "expect": {"charsafe_text": "..."},                                            # optional
   "placeholder": false}                                                           # optional

`context` lets a downstream module be measured without running upstream
modules. Items with "placeholder": true are counted but not scored.

Predicted codes come from the decision layer applied to the module's output
alone, so the thresholds measured are exactly the ones in thresholds.yaml.
Metrics are micro-averaged over (item x code) cells for the codes present in
gold or predictions; CIs are percentile bootstrap over items.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from contracts.codes import TargetType
from contracts.module_api import Context, ModuleOutput
from contracts.schema import AnalysisResult
from decision import fusion
from modules import registry
from pipeline.run import Pipeline, artifact_hash

ROOT = Path(__file__).resolve().parent.parent
TRAPS_PATH = ROOT / "eval" / "traps" / "traps.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid json: {exc}") from exc
    return items


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile, q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(q / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


@dataclass
class Cells:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def add(self, other: "Cells") -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        self.tn += other.tn

    def metrics(self) -> dict[str, float | None]:
        return {
            "recall": _ratio(self.tp, self.tp + self.fn),
            "precision": _ratio(self.tp, self.tp + self.fp),
            "fpr": _ratio(self.fp, self.fp + self.tn),
        }


class ModuleEvaluator:
    def __init__(self, module: Any, fixture_path: Path, traps_path: Path = TRAPS_PATH,
                 config: dict[str, Any] | None = None, results_dir: Path = RESULTS_DIR,
                 n_boot: int = 1000, ci: float = 0.95, seed: int = 20240901) -> None:
        self.module = module
        self.fixture_path = Path(fixture_path)
        self.traps_path = Path(traps_path)
        self.config = config if config is not None else fusion.load_config()
        self.results_dir = Path(results_dir)
        self.n_boot = n_boot
        self.ci = ci
        self.seed = seed
        self.latencies: list[float] = []
        self.module.load()

    # -- running ----------------------------------------------------------------
    def run_item(self, item: dict[str, Any]) -> tuple[ModuleOutput, AnalysisResult, set[str]]:
        extra = item.get("context", {})
        ctx = Context(
            text=item["text"],
            charsafe_text=extra.get("charsafe_text"),
            normalized_text=extra.get("normalized_text"),
            signals=MappingProxyType(dict(extra.get("signals", {}))),
            trace_id=str(item.get("id", "")),
        )
        out = self.module.process(ctx)
        self.latencies.append(out.latency_ms)
        result = AnalysisResult(text=item["text"])
        Pipeline._merge(result, out, self.module)
        fusion.decide(result, self.config)
        predicted = {s.code.value for s in result.fired()}
        predicted |= {c.value for c in result.form.active}
        predicted |= {g.code.value for g in result.guards if g.active}
        if result.target is not None and result.target.type is not TargetType.NONE:
            predicted.add(f"target:{result.target.type.value}")
        return out, result, predicted

    @staticmethod
    def _expect_failures(item: dict[str, Any], out: ModuleOutput) -> list[str]:
        failures = []
        for field_name, wanted in item.get("expect", {}).items():
            got = getattr(out, field_name, None)
            if got is not None and got != wanted:
                failures.append(f"{field_name}: expected {wanted!r}, got {got!r}")
        return failures

    # -- metrics ------------------------------------------------------------------
    def _bootstrap(self, per_item: list[Cells]) -> dict[str, dict[str, float | None]]:
        total = Cells()
        for cells in per_item:
            total.add(cells)
        point = total.metrics()
        samples: dict[str, list[float]] = {k: [] for k in point}
        rng = random.Random(self.seed)
        n = len(per_item)
        for _ in range(self.n_boot if n else 0):
            agg = Cells()
            for _ in range(n):
                agg.add(per_item[rng.randrange(n)])
            for key, value in agg.metrics().items():
                if value is not None:
                    samples[key].append(value)
        tail = (1 - self.ci) / 2 * 100
        return {
            key: {
                "value": point[key],
                "ci_low": percentile(samples[key], tail),
                "ci_high": percentile(samples[key], 100 - tail),
                "n_boot_defined": len(samples[key]),
            }
            for key in point
        }

    def evaluate(self) -> dict[str, Any]:
        items = load_jsonl(self.fixture_path)
        scored = [it for it in items if not it.get("placeholder")]
        rows: list[tuple[set[str], set[str]]] = []
        expect_total, expect_failures = 0, []
        module_errors = []
        for item in scored:
            out, _, predicted = self.run_item(item)
            if not out.ok:
                module_errors.append({"id": item.get("id"), "notes": out.notes})
            rows.append((set(item.get("expected", [])), predicted))
            if item.get("expect"):
                expect_total += 1
                failures = self._expect_failures(item, out)
                if failures:
                    expect_failures.append({"id": item.get("id"), "failures": failures})

        universe = sorted(set().union(*(gold | pred for gold, pred in rows))) if rows else []
        per_item: list[Cells] = []
        per_code: dict[str, Cells] = {code: Cells() for code in universe}
        for gold, pred in rows:
            cells = Cells()
            for code in universe:
                c = Cells(tp=int(code in gold and code in pred), fp=int(code not in gold and code in pred),
                          fn=int(code in gold and code not in pred), tn=int(code not in gold and code not in pred))
                cells.add(c)
                per_code[code].add(c)
            per_item.append(cells)

        traps = self.check_traps()
        budget = self.config["budgets"]["module_latency_p95_ms"].get(self.module.name.value)
        p95 = percentile(self.latencies, 95)
        report = {
            "module": self.module.name.value,
            "version": self.module.version,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "fixture": str(self.fixture_path.relative_to(ROOT)) if self.fixture_path.is_relative_to(ROOT) else str(self.fixture_path),
            "thresholds_artifact": self.config["artifact"]["id"],
            "thresholds_status": self.config["artifact"]["status"],
            "artifact_hash": artifact_hash(fusion.DEFAULT_CONFIG_PATH, [self.module]),
            "n_items": len(items),
            "n_scored": len(scored),
            "n_placeholder": len(items) - len(scored),
            "codes": universe,
            "metrics": self._bootstrap(per_item),
            "bootstrap": {"n_boot": self.n_boot, "ci": self.ci, "seed": self.seed, "unit": "item"},
            "per_code": {code: {**vars(c), **c.metrics()} for code, c in per_code.items()},
            "expect": {"n": expect_total, "exact_match": _ratio(expect_total - len(expect_failures), expect_total),
                       "failures": expect_failures},
            "traps": traps,
            "latency": {"p50_ms": percentile(self.latencies, 50), "p95_ms": p95, "budget_p95_ms": budget,
                        "within_budget": None if budget is None or p95 is None else p95 <= budget},
            "module_errors": module_errors,
        }
        return report

    def check_traps(self) -> dict[str, Any]:
        """Collision traps must never fire. `must_not_fire: ["*"]` means no
        content code at all; `expect` fields are checked when the module
        produces them."""
        if not self.traps_path.exists():
            return {"n": 0, "regressions": 0, "failures": [], "note": "traps file missing"}
        traps = load_jsonl(self.traps_path)
        failures = []
        for trap in traps:
            out, result, _ = self.run_item(trap)
            banned = set(trap.get("must_not_fire", ["*"]))
            fired = {s.code.value for s in result.fired()}
            hit = fired if "*" in banned else fired & banned
            problems = [f"fired {sorted(hit)}"] if hit else []
            problems += self._expect_failures(trap, out)
            if problems:
                failures.append({"id": trap.get("id"), "text": trap["text"], "problems": problems})
        return {"n": len(traps), "regressions": len(failures), "failures": failures}

    def write(self, report: dict[str, Any]) -> Path:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        path = self.results_dir / f"{report['module']}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path


def summarize(report: dict[str, Any]) -> str:
    def fmt(m: dict[str, Any]) -> str:
        if m["value"] is None:
            return "n/a"
        if m["ci_low"] is None:
            return f"{m['value']:.3f}"
        return f"{m['value']:.3f} [{m['ci_low']:.3f}, {m['ci_high']:.3f}]"

    metrics, lat = report["metrics"], report["latency"]
    p95 = "n/a" if lat["p95_ms"] is None else f"{lat['p95_ms']:.3f}ms"
    return (f"{report['module']:<12} scored={report['n_scored']:<3} placeholder={report['n_placeholder']:<3} "
            f"recall={fmt(metrics['recall'])} precision={fmt(metrics['precision'])} fpr={fmt(metrics['fpr'])} "
            f"traps={report['traps']['regressions']}/{report['traps']['n']} p95={p95} "
            f"within_budget={lat['within_budget']}")


def main_for(module_name: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"python -m modules.{module_name}.eval")
    parser.add_argument("--fixture", default=str(ROOT / "modules" / module_name / "fixtures" / "dev.jsonl"))
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    evaluator = ModuleEvaluator(registry.build(module_name), Path(args.fixture), n_boot=args.n_boot)
    report = evaluator.evaluate()
    print(summarize(report))
    if not args.no_write:
        print(f"wrote {evaluator.write(report).relative_to(ROOT)}")
    return 1 if report["traps"]["regressions"] else 0
