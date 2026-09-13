"""Unit tests for m5_sarcasm. Contract tests run now; behaviour tests are
skipped until the module is implemented (see spec.md)."""
from __future__ import annotations

import unittest

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from modules.m5_sarcasm.module import SarcasmModule


class SarcasmModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = SarcasmModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m5_sarcasm"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m5_sarcasm")

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


class SarcasmModuleBehaviourTest(unittest.TestCase):
    @unittest.skip("TODO: m5_sarcasm detection not implemented")
    def test_missing_m3_signal_is_noted_not_clean(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m5_sarcasm detection not implemented")
    def test_friendly_irony_is_not_d1(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
