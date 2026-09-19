"""Evaluate every registered module on its own fixture, then the pipeline budgets.

python -m eval.run_all [--n-boot N] [--latency-repeats N] [--results-dir DIR]

Exit code 1 if any module has a trap regression, or the pipeline exceeds
budgets.clean_to_dirty_flip_rate or budgets.latency_p95_ms.

Gate 1: every report carries `implementation` (STUB / PARTIAL / IMPLEMENTED,
from eval/implementation_status.json), `degraded_items`, per-trap
`observations` with the binary offensive state, and `provenance` (commit,
dirty flag, input digests). The closing lines name the modules whose numbers
verify nothing (stubs) and the traps on which the binary score fired in the
full pipeline. `--results-dir` writes elsewhere than eval/results/, so a
current run never overwrites a historical one.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.harness import (DEFAULT_LATENCY_REPEATS, RESULTS_DIR, ModuleEvaluator, default_fixture,
                          pipeline_budget_report, summarize)
from modules import registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.run_all")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--latency-repeats", type=int, default=DEFAULT_LATENCY_REPEATS,
                        help="timings per item / per pipeline text for latency p50/p95")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR),
                        help="where to write <module>.json and pipeline.json (default eval/results/)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    results_dir = Path(args.results_dir)

    regressions = 0
    not_verified: list[str] = []
    for entry in registry.PIPELINE_ORDER:
        fixture = default_fixture(entry.name.value)
        evaluator = ModuleEvaluator(registry.load_class(entry)(), fixture, n_boot=args.n_boot,
                                    latency_repeats=args.latency_repeats, results_dir=results_dir)
        report = evaluator.evaluate()
        evaluator.write(report)
        regressions += report["traps"]["regressions"]
        if not report["implementation"]["behaviour_measurable"]:
            not_verified.append(f"{report['module']} ({report['implementation']['declared_status']})")
        print(summarize(report))

    budgets = pipeline_budget_report(runs=args.latency_repeats)
    flip, lat = budgets["clean_to_dirty_flip_rate"], budgets["pipeline_latency"]
    binary = budgets["binary_offensive_on_traps"]
    prov = budgets["provenance"]
    print(f"pipeline: clean_to_dirty_flip_rate={flip['value']} (budget {flip['budget']}, within={flip['within_budget']}) "
          f"p95={lat['p95_ms']:.2f}ms over {lat['n']} runs ({lat['n_texts']} texts x{lat['repeats']}) "
          f"(budget {lat['budget_p95_ms']}ms, "
          f"within={lat['within_budget']})")
    print(f"pipeline: binary_offensive fired on {len(binary['fired_with_channel_trap_ids'])}/{binary['n_traps']} traps "
          f"{binary['fired_with_channel_trap_ids']} (reported, not budgeted); flipped by the channel: "
          f"{binary['flipped_by_channel_trap_ids']}; degraded modules: {budgets['degraded_modules']}")
    print(f"NOT VERIFIED (numbers describe an empty module): {', '.join(not_verified) or 'none'}")
    print(f"provenance: head={prov['git_head']} dirty={prov['git_dirty']} traps_n={prov['traps_n']} "
          f"repeats={prov['latency_repeats']} -> {'CURRENT_REPRODUCIBLE_RESULT' if prov['git_dirty'] is False else 'NOT REPRODUCIBLE (dirty tree or no git)'}")
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "pipeline.json").write_text(json.dumps(budgets, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    over_budget = flip["within_budget"] is False or lat["within_budget"] is False
    return 1 if regressions or over_budget else 0


if __name__ == "__main__":
    raise SystemExit(main())
