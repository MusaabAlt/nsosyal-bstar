"""Unit tests for m4_implicit. Contract tests run now; behaviour tests are
skipped until the module is implemented (see spec.md)."""
from __future__ import annotations

import copy
import unittest
from types import MappingProxyType

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m4_implicit.module import NOTE_C_FAMILY, ImplicitModule


class ImplicitModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = ImplicitModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m4_implicit"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m4_implicit")

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

    # -- baseline: contract shape / input not mutated / never raises --------------
    HOSTILE_INPUTS = ("", " ", "\t\n ", "a" * 5000, "Bu bir test cumlesi", "SIKINTI",
                      "ap\u200btal", "\u0430ptal", "\U0001F468\u200d\U0001F469", "\x00\x1b")

    def test_contract_shape(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertEqual(out.module, self.module.name.value)
        self.assertEqual(out.version, self.module.version)
        self.assertIsInstance(out.latency_ms, float)
        self.assertIsInstance(out.signals, dict)
        self.assertIsInstance(out.notes, list)
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))
        for score in out.content:
            self.assertIsInstance(score, ContentScore)
            self.assertIsNone(score.threshold)
            self.assertIsNone(score.fired)
        for guard in out.guards:
            self.assertIsInstance(guard, GuardResult)
            self.assertIsNone(guard.threshold)
            self.assertIsNone(guard.active)
            self.assertEqual(guard.suppressed, [])

    def test_input_not_mutated(self) -> None:
        upstream = {"m0_charsafe": {"offsets": [0, 1, 2], "invisible_removed": 0}}
        snapshot = copy.deepcopy(upstream)
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                ctx = Context(text=text, charsafe_text=text.lower(), normalized_text=text,
                              signals=MappingProxyType(upstream))
                self.module.process(ctx)
                self.assertEqual(ctx.text, text)
                self.assertEqual(ctx.charsafe_text, text.lower())
                self.assertEqual(ctx.normalized_text, text)
        self.assertEqual(upstream, snapshot)

    def test_never_raises(self) -> None:
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                out = self.module.process(Context(text=text))
                self.assertIsInstance(out, ModuleOutput)
                self.assertTrue(out.ok, out.notes)


class ImplicitModuleRoleTest(unittest.TestCase):
    def test_not_a_stub_and_emits_only_its_note(self) -> None:
        # ADR-006 amendment: C1-C5 come from m3; no scores plus one plain note is m4's real answer today.
        module = ImplicitModule()
        self.assertFalse(getattr(module, "stub", False))
        out = module.process(Context(text="Bu bir test cumlesi"))
        self.assertTrue(out.ok)
        self.assertEqual((out.content, out.guards, out.target, out.notes), ([], [], None, [NOTE_C_FAMILY]))
        self.assertEqual(NOTE_C_FAMILY, "C1–C5 not implemented yet")


# Behaviour tests are added with the implementation, from spec.md §10 Acceptance criteria.


if __name__ == "__main__":
    unittest.main()
