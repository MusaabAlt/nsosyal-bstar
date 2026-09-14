"""Evaluate every registered module on its own dev fixture.

python -m eval.run_all [--n-boot N]

Exit code 1 if any module has a trap regression.
"""
from __future__ import annotations

import argparse
import sys

from eval.harness import ModuleEvaluator, default_fixture, summarize
from modules import registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.run_all")
    parser.add_argument("--n-boot", type=int, default=1000)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    regressions = 0
    for entry in registry.PIPELINE_ORDER:
        fixture = default_fixture(entry.name.value)
        evaluator = ModuleEvaluator(registry.load_class(entry)(), fixture, n_boot=args.n_boot)
        report = evaluator.evaluate()
        evaluator.write(report)
        regressions += report["traps"]["regressions"]
        print(summarize(report))
    return 1 if regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
