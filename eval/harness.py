"""ModuleEvaluator: measure ONE module alone (CLAUDE.md rule 7).

Fixture format (jsonl, one item per line):
  {"id": "...", "text": "...",
   "expected": ["A2", "ZERO_WIDTH", "NEGATION", "target:individual"],
   "context": {"charsafe_text": "...", "normalized_text": "...", "signals": {}},  # optional
   "expect": {"charsafe_text": "..."},                                            # optional
   "expect_clean": true,                                                           # optional
   "placeholder": false}                                                           # optional

`context` lets a downstream module be measured without running upstream
modules. Items with "placeholder": true are counted but not scored.

Predicted codes come from the decision layer applied to the module's output
alone, so the thresholds measured are exactly the ones in thresholds.yaml.

Reporting rules (modules/README.md):
  * per code, never pooled - an average hides the case that fails;
  * every rate carries a percentile-bootstrap CI over items;
  * the code list is FIXED by what the module provides (not gold ∪ predictions),
    so a code's FPR denominator never moves with what happened to be predicted;
  * representation modules also report capture rate per pattern and damage rate
    on clean text;
  * fixture-run and trap-run latency are reported separately.
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

from contracts.codes import ContentCode, FormCode, GuardCode, TargetType
from contracts.module_api import Context, ModuleOutput
from contracts.schema import AnalysisResult
from decision import fusion
from modules import registry
from pipeline.run import Pipeline, artifact_hash

ROOT = Path(__file__).resolve().parent.parent
TRAPS_PATH = ROOT / "eval" / "traps" / "traps.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
REPRESENTATION_FIELDS = ("charsafe_text", "normalized_text")


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


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def code_space(module: Any) -> list[str]:
    """Fixed list of codes a module can be scored on, derived from `provides`."""
    provides = set(module.provides)
    codes: list[str] = []
    if "content" in provides:
        codes += [c.value for c in ContentCode if c is not ContentCode.CLEAN]
    if "form" in provides:
        codes += [c.value for c in FormCode]
    if "guards" in provides:
        codes += [c.value for c in GuardCode]
    if "target" in provides:
        codes += [f"target:{t.value}" for t in TargetType if t is not TargetType.NONE]
    return codes


def tr_fold(text: str) -> str:
    """Turkish-aware case fold, used only to decide whether a word changed."""
    return text.replace("I", "ı").replace("İ", "i").lower()


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
        recall = _ratio(self.tp, self.tp + self.fn)
        precision = _ratio(self.tp, self.tp + self.fp)
        f1 = (None if recall is None or precision is None
              else _ratio(2 * precision * recall, precision + recall) or 0.0)
        return {"recall": recall, "precision": precision, "f1": f1, "fpr": _ratio(self.fp, self.fp + self.tn)}


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
        self.fixture_latencies: list[float] = []
        self.trap_latencies: list[float] = []
        self.module.load()

    # -- running ----------------------------------------------------------------
    def run_item(self, item: dict[str, Any], latencies: list[float] | None = None
                 ) -> tuple[ModuleOutput, AnalysisResult, set[str]]:
        extra = item.get("context", {})
        ctx = Context(
            text=item["text"],
            charsafe_text=extra.get("charsafe_text"),
            normalized_text=extra.get("normalized_text"),
            signals=MappingProxyType(dict(extra.get("signals", {}))),
            trace_id=str(item.get("id", "")),
        )
        out = self.module.process(ctx)
        (self.fixture_latencies if latencies is None else latencies).append(out.latency_ms)
        result = AnalysisResult(text=item["text"])
        Pipeline._merge(result, out, self.module)
        # Same signal view the pipeline gives the decision layer, so signal-
        # conditioned thresholds resolve identically in eval and at inference.
        result.signals.update(extra.get("signals", {}))
        result.signals[self.module.name.value] = out.signals
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

    # -- statistics -----------------------------------------------------------------
    def _resamples(self, n: int) -> list[list[int]]:
        rng = random.Random(self.seed)
        return [[rng.randrange(n) for _ in range(n)] for _ in range(self.n_boot if n else 0)]

    def _interval(self, point: float | None, samples: list[float]) -> dict[str, Any]:
        tail = (1 - self.ci) / 2 * 100
        return {"value": point, "ci_low": percentile(samples, tail), "ci_high": percentile(samples, 100 - tail),
                "n_boot_defined": len(samples)}

    def per_code_metrics(self, rows: list[tuple[set[str], set[str]]], codes: list[str]) -> dict[str, Any]:
        """One entry per code in the fixed code list; the same item resamples are
        used for every code so their CIs are comparable."""
        resamples = self._resamples(len(rows))
        report: dict[str, Any] = {}
        for code in codes:
            cells = [Cells(tp=int(code in g and code in p), fp=int(code not in g and code in p),
                           fn=int(code in g and code not in p), tn=int(code not in g and code not in p))
                     for g, p in rows]
            total = Cells()
            for c in cells:
                total.add(c)
            point = total.metrics()
            samples: dict[str, list[float]] = {k: [] for k in point}
            for idx in resamples:
                agg = Cells()
                for i in idx:
                    agg.add(cells[i])
                for key, value in agg.metrics().items():
                    if value is not None:
                        samples[key].append(value)
            report[code] = {
                "support": total.tp + total.fn, "negatives": total.fp + total.tn,
                "tp": total.tp, "fp": total.fp, "fn": total.fn, "tn": total.tn,
                **{key: self._interval(point[key], samples[key]) for key in point},
            }
        return report

    def damage_rate(self, clean_rows: list[tuple[str, str, str | None]]) -> dict[str, Any]:
        """Share of clean items whose words changed beyond Turkish-aware case folding."""
        measurable = [(item_id, text, produced) for item_id, text, produced in clean_rows if produced is not None]
        flags = [int(tr_fold(produced).split() != tr_fold(text).split()) for _, text, produced in measurable]
        samples = [sum(flags[i] for i in idx) / len(idx) for idx in self._resamples(len(flags))]
        return {
            **self._interval(_ratio(sum(flags), len(flags)), samples),
            "n_clean": len(clean_rows), "n_measurable": len(measurable),
            "damaged_ids": [row[0] for row, flag in zip(measurable, flags) if flag],
            "note": None if clean_rows else "no fixture item has expect_clean: true",
        }

    # -- evaluation -------------------------------------------------------------------
    def evaluate(self) -> dict[str, Any]:
        items = load_jsonl(self.fixture_path)
        scored = [it for it in items if not it.get("placeholder")]
        codes = code_space(self.module)
        rows: list[tuple[set[str], set[str]]] = []
        expect_total, expect_failures, module_errors, out_of_space = 0, [], [], []
        representation_field = next((f for f in REPRESENTATION_FIELDS if f in self.module.provides), None)
        clean_rows: list[tuple[str, str, str | None]] = []
        for item in scored:
            out, _, predicted = self.run_item(item)
            if not out.ok:
                module_errors.append({"id": item.get("id"), "notes": out.notes})
            gold = set(item.get("expected", []))
            unknown = sorted(gold - set(codes))
            if unknown:
                out_of_space.append({"id": item.get("id"), "codes": unknown})
            rows.append((gold, predicted))
            if item.get("expect"):
                expect_total += 1
                failures = self._expect_failures(item, out)
                if failures:
                    expect_failures.append({"id": item.get("id"), "failures": failures})
            if representation_field and item.get("expect_clean"):
                clean_rows.append((str(item.get("id")), item["text"], getattr(out, representation_field)))

        per_code = self.per_code_metrics(rows, codes)
        representation = None
        if representation_field:
            representation = {
                "field": representation_field,
                "capture_rate_per_pattern": {
                    code: {"support": per_code[code]["support"], **per_code[code]["recall"]}
                    for code in codes if code in FormCode.__members__
                },
                "damage_rate_on_clean": self.damage_rate(clean_rows),
            }

        traps = self.check_traps()
        budget = self.config["budgets"]["module_latency_p95_ms"].get(self.module.name.value)
        fixture_p95 = percentile(self.fixture_latencies, 95)
        return {
            "module": self.module.name.value,
            "version": self.module.version,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "fixture": (str(self.fixture_path.relative_to(ROOT)) if self.fixture_path.is_relative_to(ROOT)
                        else str(self.fixture_path)),
            "thresholds_artifact": self.config["artifact"]["id"],
            "thresholds_status": self.config["artifact"]["status"],
            "artifact_hash": artifact_hash(fusion.DEFAULT_CONFIG_PATH, [self.module]),
            "n_items": len(items),
            "n_scored": len(scored),
            "n_placeholder": len(items) - len(scored),
            "codes": codes,
            "gold_codes_outside_code_space": out_of_space,
            "bootstrap": {"n_boot": self.n_boot, "ci": self.ci, "seed": self.seed, "unit": "item"},
            "per_code": per_code,
            "representation": representation,
            "expect": {"n": expect_total, "exact_match": _ratio(expect_total - len(expect_failures), expect_total),
                       "failures": expect_failures},
            "traps": traps,
            "latency": {
                "fixture": {"n": len(self.fixture_latencies), "p50_ms": percentile(self.fixture_latencies, 50),
                            "p95_ms": fixture_p95},
                "traps": {"n": len(self.trap_latencies), "p50_ms": percentile(self.trap_latencies, 50),
                          "p95_ms": percentile(self.trap_latencies, 95)},
                "budget_p95_ms": budget,
                "within_budget": None if budget is None or fixture_p95 is None else fixture_p95 <= budget,
            },
            "module_errors": module_errors,
        }

    def check_traps(self) -> dict[str, Any]:
        """Collision traps must never fire. `must_not_fire: ["*"]` means no
        content code at all; `expect` fields are checked when the module
        produces them. Only content codes and expect fields are checked."""
        if not self.traps_path.exists():
            return {"n": 0, "regressions": 0, "failures": [], "note": "traps file missing"}
        traps = load_jsonl(self.traps_path)
        failures = []
        for trap in traps:
            out, result, _ = self.run_item(trap, latencies=self.trap_latencies)
            banned = set(trap.get("must_not_fire", ["*"]))
            fired = {s.code.value for s in result.fired()}
            hit = fired if "*" in banned else fired & banned
            problems = [f"fired {sorted(hit)}"] if hit else []
            problems += self._expect_failures(trap, out)
            if problems:
                failures.append({"id": trap.get("id"), "text": trap["text"], "problems": problems})
        return {"n": len(traps), "regressions": len(failures), "failures": failures,
                "checks": "content codes (must_not_fire) and expect fields"}

    def write(self, report: dict[str, Any]) -> Path:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        path = self.results_dir / f"{report['module']}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path


def _fmt(m: dict[str, Any]) -> str:
    if m["value"] is None:
        return "n/a"
    if m["ci_low"] is None:
        return f"{m['value']:.3f}"
    return f"{m['value']:.3f} [{m['ci_low']:.3f}, {m['ci_high']:.3f}]"


def summarize(report: dict[str, Any]) -> str:
    """Human summary: one line per code with support or predictions - never an average."""
    lat = report["latency"]
    p95 = "n/a" if lat["fixture"]["p95_ms"] is None else f"{lat['fixture']['p95_ms']:.3f}ms"
    lines = [f"{report['module']}: scored={report['n_scored']} placeholder={report['n_placeholder']} "
             f"traps={report['traps']['regressions']}/{report['traps']['n']} fixture_p95={p95} "
             f"within_budget={lat['within_budget']}"]
    for code, m in report["per_code"].items():
        if m["support"] or m["fp"]:
            lines.append(f"  {code:<22} support={m['support']:<3} recall={_fmt(m['recall'])} "
                         f"precision={_fmt(m['precision'])} f1={_fmt(m['f1'])} fpr={_fmt(m['fpr'])}")
    if len(lines) == 1:
        lines.append("  (no code has gold support or predictions on this fixture)")
    rep = report.get("representation")
    if rep:
        dmg = rep["damage_rate_on_clean"]
        lines.append(f"  damage_rate_on_clean({rep['field']})={_fmt(dmg)} n_clean={dmg['n_clean']}")
    return "\n".join(lines)


def default_fixture(module_name: str) -> Path:
    base = ROOT / "modules" / module_name / "fixtures"
    return base / "cases.jsonl" if (base / "cases.jsonl").exists() else base / "dev.jsonl"


def main_for(module_name: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"python -m modules.{module_name}.eval")
    parser.add_argument("--fixture", default=str(default_fixture(module_name)))
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    evaluator = ModuleEvaluator(registry.build(module_name), Path(args.fixture), n_boot=args.n_boot)
    report = evaluator.evaluate()
    print(summarize(report))
    if not args.no_write:
        print(f"wrote {evaluator.write(report).relative_to(ROOT)} (git-ignored; see eval/README.md)")
    return 1 if report["traps"]["regressions"] else 0
