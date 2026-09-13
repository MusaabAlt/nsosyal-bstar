"""Unit tests for m2_deobf. Contract tests run now; behaviour tests are
skipped until the module is implemented (see spec.md)."""
from __future__ import annotations

import unittest

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from modules.m2_deobf.module import DeobfModule


class DeobfModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = DeobfModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m2_deobf"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m2_deobf")

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


class DeobfModuleBehaviourTest(unittest.TestCase):
    @unittest.skip("TODO: m2_deobf detection not implemented")
    def test_raw_channel_never_replaced(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m2_deobf detection not implemented")
    def test_legit_double_letters_survive(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m2_deobf detection not implemented")
    def test_ambiguous_deasciification_keeps_alternatives(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
