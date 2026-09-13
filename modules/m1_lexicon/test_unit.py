"""Unit tests for m1_lexicon. Contract tests run now; behaviour tests are
skipped until the module is implemented (see spec.md)."""
from __future__ import annotations

import unittest

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from modules.m1_lexicon.module import LexiconModule


class LexiconModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = LexiconModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m1_lexicon"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m1_lexicon")

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


class LexiconModuleBehaviourTest(unittest.TestCase):
    @unittest.skip("TODO: m1_lexicon detection not implemented")
    def test_collision_traps_never_fire(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m1_lexicon detection not implemented")
    def test_inflected_root_matches_on_morpheme_boundary(self) -> None:
        raise NotImplementedError


    @unittest.skip("TODO: m1_lexicon detection not implemented")
    def test_scores_tagged_with_channel(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
