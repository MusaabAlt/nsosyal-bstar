from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout

from contracts.codes import Action, ContentCode, GuardCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import AnalysisResult, ContentScore, GuardResult
from decision import fusion
from pipeline import run
from pipeline.run import Pipeline


class _Scorer(BaseModule):
    """Test double: emits a fixed score."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content"})

    def __init__(self, value: float, **decision_fields) -> None:
        super().__init__()
        self.value = value
        self.decision_fields = decision_fields

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(content=[ContentScore(ContentCode.A3, self.value, "m1_lexicon@raw",
                                                  **self.decision_fields)])


class _Charsafe(BaseModule):
    name = ModuleName.M0_CHARSAFE
    provides = frozenset({"charsafe_text"})

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(charsafe_text=ctx.text.lower())


class _Spy(BaseModule):
    name = ModuleName.M3_ENCODER
    provides = frozenset({"guards"})

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[Context] = []

    def _run(self, ctx: Context) -> ModuleOutput:
        self.seen.append(ctx)
        # Also returns an undeclared field, which must be dropped.
        return ModuleOutput(guards=[GuardResult(GuardCode.NEGATION, 0.1, "m3")], normalized_text="sneaky")


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())
        self.cfg["categories"]["A3"].update(threshold=0.5, action="block")
        self.cfg["guards"]["NEGATION"]["threshold"] = 0.5
        self.cfg["fast_path"].update(enabled=True, margin=0.3, requires=["m0_charsafe", "m1_lexicon"])

    def test_default_pipeline_on_clean_sentence(self) -> None:
        text = "Bu bir test cumlesi"
        result = Pipeline().analyze(text)
        self.assertEqual(result.text, text)
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertEqual(len(result.per_module_ms), 7)
        self.assertEqual(result.signals["channels"]["charsafe_text"], "bu bir test cumlesi")
        self.assertEqual(len(result.artifact_hash), 64)
        data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(set(data), set(AnalysisResult(text="").to_dict()))

    def test_downstream_module_sees_charsafe_text_and_signals(self) -> None:
        spy = _Spy()
        Pipeline(modules=[_Charsafe(), spy], config=self.cfg).analyze("ABC")
        ctx = spy.seen[0]
        self.assertEqual(ctx.text, "ABC")
        self.assertEqual(ctx.charsafe_text, "abc")
        self.assertIn("m0_charsafe", ctx.signals)

    def test_stub_modules_are_named_and_clean_is_not_confident(self) -> None:
        result = Pipeline().analyze("Bu bir test cumlesi")
        stubs = ["m2_deobf", "m1_lexicon", "m6_target", "m3_encoder", "m4_implicit", "m5_sarcasm"]
        self.assertEqual(result.signals["pipeline"]["stub_modules"], stubs)
        self.assertTrue(result.notes[0].startswith("[pipeline] STUB modules"))
        for name in stubs:
            self.assertIn(name, result.notes[0])
            self.assertIn(name, result.explanation)
        self.assertTrue(result.explanation.startswith("Kesin sonuç değil"))

    def test_no_stub_caveat_without_stubs(self) -> None:
        result = Pipeline(modules=[_Charsafe()], config=self.cfg).analyze("x")
        self.assertEqual(result.signals["pipeline"]["stub_modules"], [])
        self.assertFalse(any("STUB" in n for n in result.notes))
        self.assertFalse(result.explanation.startswith("Kesin sonuç değil"))

    def test_undeclared_fields_are_dropped(self) -> None:
        result = Pipeline(modules=[_Spy()], config=self.cfg).analyze("x")
        self.assertIsNone(result.signals["channels"]["normalized_text"])
        self.assertTrue(any("undeclared" in n for n in result.notes))

    def test_module_decision_fields_are_cleared(self) -> None:
        cheater = _Scorer(0.1, threshold=0.0, fired=True)
        result = Pipeline(modules=[cheater], config=self.cfg).analyze("x")
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertTrue(any("decision-owned" in n for n in result.notes))

    def test_fast_path_skips_remaining_modules(self) -> None:
        spy = _Spy()
        result = Pipeline(modules=[_Charsafe(), _Scorer(0.95), spy], config=self.cfg).analyze("x")
        self.assertTrue(result.fast_path)
        self.assertEqual(spy.seen, [])
        self.assertIs(result.verdict, Action.BLOCK)

    def test_no_fast_path_below_margin(self) -> None:
        spy = _Spy()
        result = Pipeline(modules=[_Charsafe(), _Scorer(0.6), spy], config=self.cfg).analyze("x")
        self.assertFalse(result.fast_path)
        self.assertEqual(len(spy.seen), 1)
        self.assertIs(result.verdict, Action.BLOCK)

    def test_failing_module_degrades_not_aborts(self) -> None:
        class Broken(_Scorer):
            def _run(self, ctx: Context) -> ModuleOutput:
                raise ValueError("bad input")

        result = Pipeline(modules=[_Charsafe(), Broken(0.0)], config=self.cfg).analyze("x")
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertTrue(any("degraded" in n for n in result.notes))

    def test_cli_prints_contract_json(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(run.main(["Bu bir test cumlesi", "--compact"]), 0)
        data = json.loads(buffer.getvalue())
        self.assertEqual(data["verdict"], "clean")


if __name__ == "__main__":
    unittest.main()
