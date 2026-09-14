"""Every code written in gold data must exist in the contracts code books.

A typo in a gold label ("A22", "ZERO-WIDTH", "posts") silently becomes a code
nothing can ever predict, so recall on it reads as a real failure. Covers the
end-to-end testsuite (all four axes plus guards), module fixtures and traps.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from contracts.codes import ContentCode, FormCode, GuardCode, Level, ModuleName, TargetType

ROOT = Path(__file__).resolve().parent.parent
PREDICTED_TARGET_PREFIX = "target:"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def known_prediction_codes() -> set[str]:
    return ({c.value for c in ContentCode} | {c.value for c in FormCode} | {c.value for c in GuardCode}
            | {PREDICTED_TARGET_PREFIX + t.value for t in TargetType})


class GoldDataTest(unittest.TestCase):
    def test_testsuite_items_use_contract_codes_on_every_axis(self) -> None:
        for path in sorted((ROOT / "eval" / "testsuite").glob("*.jsonl")):
            for item in load_jsonl(path):
                with self.subTest(file=path.name, id=item.get("id")):
                    ContentCode(item["content"])                      # Axis 1: one label
                    for code in item["form"]:                         # Axis 2: multi-valued
                        FormCode(code)
                    TargetType(item["target"])                        # Axis 3
                    Level(item["level"])                              # Axis 4: post vs thread
                    for code in item["guards"]:
                        GuardCode(code)

    def test_module_fixtures_use_contract_codes(self) -> None:
        known = known_prediction_codes()
        for path in sorted((ROOT / "modules").glob("m*/fixtures/*.jsonl")):
            for item in load_jsonl(path):
                gold = item.get("expected", item.get("expect_patterns", []))
                with self.subTest(file=str(path.relative_to(ROOT)), id=item.get("id")):
                    self.assertLessEqual(set(gold), known)

    def test_traps_use_contract_codes_and_module_names(self) -> None:
        for item in load_jsonl(ROOT / "eval" / "traps" / "traps.jsonl"):
            with self.subTest(id=item.get("id")):
                for code in item.get("must_not_fire", []):
                    self.assertTrue(code == "*" or ContentCode(code))
                for field_name, enum in (("form", FormCode), ("guards", GuardCode)):
                    rule = item.get(field_name)
                    if not rule:
                        continue
                    for name in rule["modules"]:
                        ModuleName(name)
                    for code in rule.get("must", []) + rule.get("must_not", []):
                        self.assertTrue(code == "*" or enum(code))


if __name__ == "__main__":
    unittest.main()
