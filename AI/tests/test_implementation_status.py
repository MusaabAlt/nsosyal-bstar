"""Gate 1, task 3: a stub can never look like a verified module, and a skipped
behaviour test can never look like a passing one.

`unittest` exits 0 on skips and `scripts/check.sh` counts nothing, so before
this file a module whose every behaviour test was skipped was green. Now the
exact set of allowed skips per module is declared in
eval/implementation_status.json and any other skip - or a missing
precondition that would turn a real test into a skip - fails here with a
named reason.
"""
from __future__ import annotations

import json
import unittest

from eval.harness import IMPLEMENTATION_STATUS_PATH, IMPLEMENTATION_STATUSES, implementation_status
from modules import registry
from modules.m3_encoder.test_unit import artifact_available

DECLARED = json.loads(IMPLEMENTATION_STATUS_PATH.read_text(encoding="utf-8"))
GENERIC = set(DECLARED["generic_contract_tests"])


def module_tests(module_name: str) -> dict[str, bool]:
    """'Class.method' -> skipped? for every test in modules/<name>/test_unit.py."""
    found: dict[str, bool] = {}

    def walk(suite: unittest.TestSuite) -> None:
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                walk(test)
                continue
            method = getattr(test, test.id().rsplit(".", 1)[-1], None)
            skipped = bool(getattr(method, "__unittest_skip__", False)) or bool(
                getattr(type(test), "__unittest_skip__", False))
            found[".".join(test.id().rsplit(".", 2)[-2:])] = skipped

    walk(unittest.defaultTestLoader.loadTestsFromName(f"modules.{module_name}.test_unit"))
    return found


class ImplementationStatusTest(unittest.TestCase):
    def test_declaration_covers_exactly_the_registered_modules(self) -> None:
        registered = {entry.name.value for entry in registry.PIPELINE_ORDER}
        self.assertEqual(set(DECLARED["modules"]), registered)

    def test_declared_status_agrees_with_the_stub_flag(self) -> None:
        for entry in registry.PIPELINE_ORDER:
            cls = registry.load_class(entry)
            declared = DECLARED["modules"][entry.name.value]
            with self.subTest(module=entry.name.value):
                self.assertIn(declared["status"], IMPLEMENTATION_STATUSES)
                self.assertEqual(declared["status"] == "STUB", bool(getattr(cls, "stub", False)),
                                 "eval/implementation_status.json disagrees with module.stub")
                if declared["status"] == "PARTIAL":
                    self.assertTrue(declared["not_built"], "a PARTIAL module must list what is not built")
                if declared["status"] == "IMPLEMENTED":
                    self.assertEqual(declared["not_built"], [])

    def test_skipped_behaviour_tests_are_exactly_the_declared_ones(self) -> None:
        for entry in registry.PIPELINE_ORDER:
            name = entry.name.value
            declared = DECLARED["modules"][name]
            with self.subTest(module=name):
                if name == "m3_encoder" and not artifact_available():
                    self.fail("PRECONDITION: m3 artifact files or torch/transformers missing on this machine "
                              f"({declared['preconditions']}); its behaviour tests would skip and this suite "
                              "would be green for the wrong reason")
                tests = module_tests(name)
                self.assertTrue(tests, f"no tests loaded from modules/{name}/test_unit.py")
                skipped = sorted(t for t, s in tests.items() if s)
                self.assertEqual(skipped, sorted(declared["expected_skipped_tests"]),
                                 "skipped tests differ from eval/implementation_status.json")

    def test_stub_has_no_runnable_behaviour_test_and_others_have_some(self) -> None:
        for entry in registry.PIPELINE_ORDER:
            name = entry.name.value
            tests = module_tests(name)
            behaviour = {t: s for t, s in tests.items() if t.rsplit(".", 1)[-1] not in GENERIC}
            runnable = [t for t, s in behaviour.items() if not s]
            with self.subTest(module=name, status=DECLARED["modules"][name]["status"]):
                if DECLARED["modules"][name]["status"] == "STUB":
                    self.assertEqual(runnable, [], "a stub with a runnable behaviour test is not a stub")
                else:
                    self.assertTrue(runnable, "an implemented or partial module must run at least one behaviour test")

    def test_harness_marks_stubs_not_verified_and_others_measurable(self) -> None:
        for entry in registry.PIPELINE_ORDER:
            cls = registry.load_class(entry)
            # Class attributes suffice: implementation_status reads `stub` and the name only.
            status = implementation_status(cls)
            with self.subTest(module=entry.name.value):
                self.assertTrue(status["consistent"], status["scope"])
                if status["stub"]:
                    self.assertFalse(status["behaviour_measurable"])
                    self.assertIn("NOT VERIFIED", status["scope"])
                else:
                    self.assertTrue(status["behaviour_measurable"])
                    self.assertIn("MEASURED", status["scope"])


if __name__ == "__main__":
    unittest.main()
