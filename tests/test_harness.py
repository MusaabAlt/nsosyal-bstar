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


class TrapFormatTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fixture = self.dir / "fixture.jsonl"
        self.fixture.write_text(json.dumps({"id": "1", "text": "x", "expected": []}) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def traps(self, module: BaseModule, items: list[dict]) -> dict:
        path = self.dir / "traps.jsonl"
        path.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")
        return ModuleEvaluator(module, self.fixture, traps_path=path, results_dir=self.dir, n_boot=10).check_traps()

    def test_form_must_and_must_not_are_checked_for_listed_modules(self) -> None:
        items = [
            {"id": "t1", "text": "a zw b", "form": {"modules": ["m0_charsafe"], "must": ["ZERO_WIDTH"]}},
            {"id": "t2", "text": "a b", "form": {"modules": ["m0_charsafe"], "must": ["ZERO_WIDTH"]}},
            {"id": "t3", "text": "zw", "form": {"modules": ["m0_charsafe"], "must_not": ["*"]}},
            {"id": "t4", "text": "zw", "form": {"modules": ["m2_deobf"], "must_not": ["*"]}},
        ]
        report = self.traps(_Rewriter(), items)
        self.assertEqual([f["id"] for f in report["failures"]], ["t2", "t3"])

    def test_stub_must_is_pending_but_must_not_still_applies(self) -> None:
        class StubLexicon(_Lexicon):
            stub = True

        items = [
            {"id": "t1", "text": "amca", "guards": {"modules": ["m1_lexicon"], "must": ["SUBSTRING_COLLISION"]}},
            {"id": "t2", "text": "kotu", "must_not_fire": ["*"]},
        ]
        report = self.traps(StubLexicon(), items)
        self.assertEqual([p["id"] for p in report["pending"]], ["t1"])
        self.assertEqual([f["id"] for f in report["failures"]], ["t2"])

    def test_implemented_module_missing_a_must_is_a_regression(self) -> None:
        items = [{"id": "t1", "text": "amca", "guards": {"modules": ["m1_lexicon"], "must": ["SUBSTRING_COLLISION"]}}]
        report = self.traps(_Lexicon(), items)
        self.assertEqual(report["regressions"], 1)
        self.assertEqual(report["pending"], [])


class PipelineBudgetTest(unittest.TestCase):
    def test_flip_rate_counts_traps_only_the_normalized_channel_fires_on(self) -> None:
        from contracts.codes import ContentCode, ModuleName
        from eval.harness import pipeline_budget_report

        class Deobf(BaseModule):
            name = ModuleName.M2_DEOBF
            provides = frozenset({"normalized_text"})
            emits_spans = False

            def _run(self, ctx: Context) -> ModuleOutput:
                return ModuleOutput(normalized_text=ctx.text.replace("4", "a"))

        class Lexicon(BaseModule):
            name = ModuleName.M1_LEXICON
            provides = frozenset({"content"})
            emits_spans = False

            def _run(self, ctx: Context) -> ModuleOutput:
                hit = ctx.normalized_text is not None and "amca" in ctx.normalized_text
                return ModuleOutput(content=[ContentScore(ContentCode.A1, 0.99, "m1_lexicon@normalized")] if hit else [])

        with tempfile.TemporaryDirectory() as tmp:
            traps = Path(tmp) / "traps.jsonl"
            traps.write_text("".join(json.dumps(t) + chr(10) for t in (
                {"id": "t1", "text": "amc4"}, {"id": "t2", "text": "iyi"})), encoding="utf-8")
            report = pipeline_budget_report(traps_path=traps, modules=[Deobf(), Lexicon()], texts=["iyi"], runs=1)
        flip = report["clean_to_dirty_flip_rate"]
        self.assertEqual((flip["flipped_trap_ids"], flip["value"], flip["n_traps"]), (["t1"], 0.5, 2))
        self.assertFalse(flip["within_budget"])
        self.assertEqual(report["pipeline_latency"]["n"], 1)


class LatencyBudgetTest(unittest.TestCase):
    def test_per_length_bands(self) -> None:
        from eval.harness import latency_budget

        report = latency_budget([0.1, 0.2, 3.0, 30.0], [10, 50, 900, 6000], {64: 0.25, 1000: 4})
        self.assertEqual([(b["max_chars"], b["n"], b["within_budget"]) for b in report["budget_bands"]],
                         [(64, 2, True), (1000, 1, True)])
        self.assertEqual(report["unbudgeted_n"], 1)
        self.assertTrue(report["within_budget"])
        self.assertFalse(latency_budget([5.0], [900], {1000: 4})["within_budget"])
        self.assertEqual(latency_budget([0.5], [10], 1), {"budget_p95_ms": 1, "within_budget": True})

    def test_invalid_band_key_fails_config_validation(self) -> None:
        import copy
        from decision import fusion

        cfg = copy.deepcopy(fusion.load_config())
        cfg["budgets"]["module_latency_p95_ms"]["m0_charsafe"] = {"long": 4}
        with self.assertRaises(ValueError):
            fusion.validate_config(cfg)


if __name__ == "__main__":
    unittest.main()
