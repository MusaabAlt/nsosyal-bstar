from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from contracts.codes import ContentCode, FormCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore, FormPattern, FormResult
from eval.harness import ModuleEvaluator, code_space, summarize


class _Lexicon(BaseModule):
    """Fires A2 whenever the text contains 'kotu'."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content"})

    def _run(self, ctx: Context) -> ModuleOutput:
        if "kotu" in ctx.text:
            return ModuleOutput(content=[ContentScore(ContentCode.A2, 0.99, "m1_lexicon@raw", span=(0, 4))])
        return ModuleOutput()


class _Rewriter(BaseModule):
    """Representation double: uppercases the first word and reports ZERO_WIDTH on 'zw'."""

    name = ModuleName.M0_CHARSAFE
    provides = frozenset({"charsafe_text", "form"})

    def _run(self, ctx: Context) -> ModuleOutput:
        patterns = [FormPattern(FormCode.ZERO_WIDTH, 0.99, "zw")] if "zw" in ctx.text else []
        text = ctx.text.replace("bozuk", "BOZUK_DEGIL")
        return ModuleOutput(charsafe_text=text, form=FormResult(patterns=patterns))


class HarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.traps = self.dir / "traps.jsonl"
        self.traps.write_text(json.dumps({"id": "t1", "text": "amca", "must_not_fire": ["*"]}) + "\n",
                              encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def fixture(self, items: list[dict]) -> Path:
        path = self.dir / "fixture.jsonl"
        path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
        return path

    def evaluate(self, module: BaseModule, items: list[dict]) -> dict:
        evaluator = ModuleEvaluator(module, self.fixture(items), traps_path=self.traps,
                                    results_dir=self.dir, n_boot=200)
        return evaluator.evaluate()

    def test_metrics_are_per_code_never_pooled(self) -> None:
        report = self.evaluate(_Lexicon(), [
            {"id": "1", "text": "kotu adam", "expected": ["A2"]},
            {"id": "2", "text": "iyi adam", "expected": []},
            {"id": "3", "text": "kotu", "expected": ["A3"]},
        ])
        self.assertNotIn("metrics", report)
        a2, a3 = report["per_code"]["A2"], report["per_code"]["A3"]
        self.assertEqual((a2["tp"], a2["fp"], a2["fn"], a2["tn"]), (1, 1, 0, 1))
        self.assertEqual((a3["tp"], a3["fp"], a3["fn"], a3["tn"]), (0, 0, 1, 2))
        for key in ("recall", "precision", "f1", "fpr"):
            self.assertIn("ci_low", a2[key])
        self.assertIn("A2", summarize(report))

    def test_code_list_is_fixed_so_fpr_denominator_does_not_move(self) -> None:
        items = [{"id": str(i), "text": "iyi", "expected": []} for i in range(4)]
        quiet = self.evaluate(_Lexicon(), items)
        noisy = self.evaluate(_Lexicon(), items + [{"id": "x", "text": "kotu", "expected": []}])
        self.assertEqual(quiet["codes"], code_space(_Lexicon()))
        self.assertEqual(quiet["codes"], noisy["codes"])
        self.assertEqual(quiet["per_code"]["B5"]["negatives"], 4)
        self.assertEqual(noisy["per_code"]["B5"]["negatives"], 5)

    def test_representation_metrics(self) -> None:
        report = self.evaluate(_Rewriter(), [
            {"id": "1", "text": "a zw b", "expected": ["ZERO_WIDTH"]},
            {"id": "2", "text": "a b", "expected": ["ZERO_WIDTH"]},
            {"id": "3", "text": "SIKINTI yok", "expected": [], "expect_clean": True},
            {"id": "4", "text": "bozuk saat", "expected": [], "expect_clean": True},
        ])
        rep = report["representation"]
        self.assertEqual(rep["field"], "charsafe_text")
        capture = rep["capture_rate_per_pattern"]["ZERO_WIDTH"]
        self.assertEqual((capture["support"], capture["value"]), (2, 0.5))
        damage = rep["damage_rate_on_clean"]
        # "SIKINTI" is unchanged under Turkish folding; "bozuk" -> "BOZUK_DEGIL" is damage.
        self.assertEqual((damage["value"], damage["n_clean"], damage["damaged_ids"]), (0.5, 2, ["4"]))

    def test_trap_latency_is_separate_from_fixture_latency(self) -> None:
        report = self.evaluate(_Lexicon(), [{"id": "1", "text": "iyi", "expected": []},
                                            {"id": "2", "text": "iyi", "expected": []}])
        self.assertEqual(report["latency"]["fixture"]["n"], 2)
        self.assertEqual(report["latency"]["traps"]["n"], 1)
        self.assertEqual(report["traps"]["regressions"], 0)


if __name__ == "__main__":
    unittest.main()
