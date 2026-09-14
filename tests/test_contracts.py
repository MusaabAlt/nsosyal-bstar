from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from contracts.codes import (ACTION_PRECEDENCE, FAMILY, TR_LABELS, Action, ContentCode, Family, FormCode,
                             GuardCode, ModuleName, TargetType, codes_in_family)
from contracts.module_api import BaseModule, Context, Module, ModuleOutput
from contracts.schema import AnalysisResult, ContentScore, FormPattern

FIXTURES = Path(__file__).resolve().parent.parent / "contracts" / "fixtures"


class CodesTest(unittest.TestCase):
    def test_code_books_are_complete(self) -> None:
        self.assertEqual([c.value for c in ContentCode],
                         ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "B5",
                          "C1", "C2", "C3", "C4", "C5", "D1", "CLEAN"])
        self.assertEqual(len(FormCode), 16)
        self.assertEqual(len(GuardCode), 9)
        self.assertEqual({t.value for t in TargetType}, {"individual", "group", "non_human", "none"})
        self.assertEqual(len(ModuleName), 7)

    def test_every_member_has_a_turkish_label(self) -> None:
        for enum in (ContentCode, Family, FormCode, GuardCode, TargetType, Action):
            for member in enum:
                self.assertIn(member, TR_LABELS, member)

    def test_family_map(self) -> None:
        self.assertIs(FAMILY[ContentCode.B4], Family.B)
        self.assertIs(FAMILY[ContentCode.CLEAN], Family.CLEAN)
        self.assertEqual(len(codes_in_family(Family.C)), 5)

    def test_action_precedence(self) -> None:
        self.assertEqual(ACTION_PRECEDENCE[0], Action.BLOCK)
        self.assertEqual(ACTION_PRECEDENCE[-1], Action.CLEAN)
        self.assertEqual(set(ACTION_PRECEDENCE), set(Action))


class SchemaTest(unittest.TestCase):
    def make(self) -> AnalysisResult:
        return AnalysisResult(
            text="x",
            content=[ContentScore(ContentCode.A1, 0.2, "m@raw", threshold=0.5, fired=False),
                     ContentScore(ContentCode.B2, 0.9, "m@raw", threshold=0.5, fired=True),
                     ContentScore(ContentCode.A2, 0.7, "m@raw", threshold=0.5, fired=True)],
        )

    def test_fired_and_top(self) -> None:
        result = self.make()
        self.assertEqual([s.code for s in result.fired()], [ContentCode.B2, ContentCode.A2])
        self.assertIs(result.top().code, ContentCode.B2)
        self.assertIsNone(AnalysisResult(text="x").top())

    def test_to_dict_is_json_serializable(self) -> None:
        result = self.make()
        result.form.patterns.append(FormPattern(FormCode.LEET, 0.8, "4 -> a", (1, 2)))
        data = json.loads(json.dumps(result.to_dict()))
        self.assertEqual(data["content"][1]["code"], "B2")
        self.assertEqual(data["form"]["patterns"][0]["span"], [1, 2])

    def test_example_fixture_matches_contract_shape(self) -> None:
        example = json.loads((FIXTURES / "analysis_result.example.json").read_text(encoding="utf-8"))
        self.assertEqual(set(example), set(AnalysisResult(text="").to_dict()))
        module_example = json.loads((FIXTURES / "module_output.example.json").read_text(encoding="utf-8"))
        self.assertEqual(set(module_example), set(vars(ModuleOutput())))


class _Boom(BaseModule):
    name = ModuleName.M1_LEXICON
    provides = frozenset({"content"})

    def _run(self, ctx: Context) -> ModuleOutput:
        raise RuntimeError("kaboom")


class _BadLoad(BaseModule):
    name = ModuleName.M3_ENCODER
    provides = frozenset({"content"})

    def _load(self) -> None:
        raise FileNotFoundError("model.onnx")

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput()


class ModuleApiTest(unittest.TestCase):
    def test_context_is_read_only(self) -> None:
        ctx = Context(text="orijinal")
        with self.assertRaises(FrozenInstanceError):
            ctx.text = "değişti"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            ctx.signals["x"] = 1  # type: ignore[index]

    def test_best_text_defaults_to_raw_channel(self) -> None:
        ctx = Context(text="Orijinal", charsafe_text="orijinal", normalized_text="normal")
        self.assertEqual(ctx.best_text(), "orijinal")
        self.assertEqual(ctx.best_text("normalized"), "normal")
        self.assertEqual(Context(text="T").best_text("normalized"), "T")
        with self.assertRaises(ValueError):
            ctx.best_text("other")

    def test_base_module_catches_run_exceptions(self) -> None:
        out = _Boom().process(Context(text="x"))
        self.assertFalse(out.ok)
        self.assertIn("RuntimeError: kaboom", out.notes[0])
        self.assertEqual(out.module, "m1_lexicon")
        self.assertGreaterEqual(out.latency_ms, 0)

    def test_base_module_reports_load_failure(self) -> None:
        out = _BadLoad().process(Context(text="x"))
        self.assertFalse(out.ok)
        self.assertIn("load failed", out.notes[0])

    def test_base_module_satisfies_protocol(self) -> None:
        self.assertIsInstance(_Boom(), Module)

    def test_populated_fields(self) -> None:
        out = ModuleOutput(charsafe_text="a", content=[ContentScore(ContentCode.A1, 0.1, "m@raw")])
        self.assertEqual(out.populated_fields(), {"charsafe_text", "content"})


if __name__ == "__main__":
    unittest.main()
