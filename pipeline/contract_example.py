"""Deterministic regeneration of the contract examples in contracts/fixtures/.

  * analysis_result.example.json - a full pipeline run on EXAMPLE_TEXT
  * module_output.example.json   - one real module run (m0_charsafe, the reference
                                   module) on MODULE_EXAMPLE_TEXT

The example is produced by a real run of the current code (ADR-002/ADR-003
amendments), never edited by hand. Values that change on every run - total and
per-module latency - are frozen to LATENCY_SENTINEL_MS, so regenerating an
unchanged system gives a byte-identical file and the `contracts/` gate in
scripts/check.sh only trips on a real change. `artifact_hash` stays REAL on
purpose: a genuine change to the decision config or to a module version must
still change the example and trip the gate.

contracts/ is frozen: writing requires --write and an explicit owner
instruction. Without it the example is printed; --check compares it with the
committed file and exits 1 when they differ.

    python -m pipeline.contract_example            # print
    python -m pipeline.contract_example --check    # 0 when the committed example is current
    python -m pipeline.contract_example --write    # only on explicit instruction
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from contracts.module_api import Context
from contracts.schema import to_jsonable
from modules import registry
from pipeline.run import Pipeline

FIXTURES = Path(__file__).resolve().parent.parent / "contracts" / "fixtures"
EXAMPLE_PATH = FIXTURES / "analysis_result.example.json"
MODULE_EXAMPLE_PATH = FIXTURES / "module_output.example.json"
EXAMPLE_TEXT = "Bu bir test cumlesi"
MODULE_EXAMPLE_MODULE = "m0_charsafe"
MODULE_EXAMPLE_TEXT = "SIKINTI"
EXAMPLE_TRACE_ID = "example-trace-id"
# Not a measurement: a fixed stand-in so the example does not change between runs.
LATENCY_SENTINEL_MS = 0.0


def build_example(pipeline: Pipeline | None = None) -> dict[str, Any]:
    example = (pipeline or Pipeline()).analyze(EXAMPLE_TEXT, trace_id=EXAMPLE_TRACE_ID).to_dict()
    example["latency_ms"] = LATENCY_SENTINEL_MS
    example["per_module_ms"] = {name: LATENCY_SENTINEL_MS for name in example["per_module_ms"]}
    return example


def build_module_example() -> dict[str, Any]:
    module = registry.build(MODULE_EXAMPLE_MODULE)
    module.load()
    example = to_jsonable(module.process(Context(text=MODULE_EXAMPLE_TEXT)))
    example["latency_ms"] = LATENCY_SENTINEL_MS
    return example


def examples() -> dict[Path, str]:
    return {EXAMPLE_PATH: render(build_example()), MODULE_EXAMPLE_PATH: render(build_module_example())}


def render(example: dict[str, Any]) -> str:
    return json.dumps(example, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.contract_example", description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 when the committed example is not current")
    mode.add_argument("--write", action="store_true", help="overwrite the frozen example (explicit instruction only)")
    args = parser.parse_args(argv)
    generated = examples()
    if args.check:
        stale = [path.name for path, text in generated.items()
                 if (path.read_text(encoding="utf-8") if path.exists() else "") != text]
        for name in stale:
            print(f"{name} is not current", file=sys.stderr)
        return 1 if stale else 0
    if args.write:
        for path, text in generated.items():
            path.write_text(text, encoding="utf-8", newline="\n")
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write("".join(generated.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
