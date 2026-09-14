"""Evaluate every registered module on its own fixture, then the pipeline budgets.

python -m eval.run_all [--n-boot N] [--latency-repeats N]

Exit code 1 if any module has a trap regression, or the pipeline exceeds
budgets.clean_to_dirty_flip_rate or budgets.latency_p95_ms.
"""
from __future__ import annotations

import argparse
import sys

import json

from eval.harness import (DEFAULT_LATENCY_REPEATS, RESULTS_DIR, ModuleEvaluator, default_fixture,
                          pipeline_budget_report, summarize)
from modules import registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.run_all")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--latency-repeats", type=int, default=DEFAULT_LATENCY_REPEATS,
                        help="timings per item / per pipeline text for latency p50/p95")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    regressions = 0
    for entry in registry.PIPELINE_ORDER:
        fixture = default_fixture(entry.name.value)
        evaluator = ModuleEvaluator(registry.load_class(entry)(), fixture, n_boot=args.n_boot,
                                    latency_repeats=args.latency_repeats)
        report = evaluator.evaluate()
        evaluator.write(report)
        regressions += report["traps"]["regressions"]
        print(summarize(report))

    budgets = pipeline_budget_report(runs=args.latency_repeats)
    flip, lat = budgets["clean_to_dirty_flip_rate"], budgets["pipeline_latency"]
    print(f"pipeline: clean_to_dirty_flip_rate={flip['value']} (budget {flip['budget']}, within={flip['within_budget']}) "
          f"p95={lat['p95_ms']:.2f}ms over {lat['n']} runs ({lat['n_texts']} texts x{lat['repeats']}) "
          f"(budget {lat['budget_p95_ms']}ms, "
          f"within={lat['within_budget']})")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "pipeline.json").write_text(json.dumps(budgets, indent=2) + "\n", encoding="utf-8")
    over_budget = flip["within_budget"] is False or lat["within_budget"] is False
    return 1 if regressions or over_budget else 0


if __name__ == "__main__":
    raise SystemExit(main())
