"""Unit tests for m6_target. Contract tests run now; behaviour tests are
skipped until the module is implemented (see spec.md)."""
from __future__ import annotations

import unittest

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from modules.m6_target.module import TargetModule


class TargetModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = TargetModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m6_target"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m6_target")

    def test_output_stays_within_provides(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))

    def test_never_sets_decision_fields(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        for score in out.content:
            self.assertIsNone(score.threshold)
            self.assertIsNone(score.fired)
        for guard in out.guards:
            self.assertIsNone(guard.active)


class TargetModuleBehaviourTest(unittest.TestCase):
    @unittest.skip("TODO: m6_target detection not implemented")
    def test_invalid_tc_checksum_is_not_doxing(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m6_target detection not implemented")
    def test_pii_is_masked_in_evidence(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m6_target detection not implemented")
    def test_non_human_object_emits_guard(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
