"""Gate 1: the harness observes what it used to hide (TEST_SYSTEM_AUDIT.md §2.5-§2.7).

Three blind spots, each with a test that failed (or could not exist) before:
  * a stub or failed module was never degraded inside the harness, so its result
    file was healthy and its verdict could be clean;
  * the binary offensive score was invisible to traps, per-code metrics and the
    flip-rate budget;
  * a result file carried no provenance, so it could not be tied to a commit.

All modules here are doubles (DOUBLE); nothing loads a model.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from contracts.codes import Action, ContentCode, GuardCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from decision import actions, fusion
from eval import harness
from eval.harness import ModuleEvaluator, degradation_record, implementation_status, pipeline_budget_report, summarize
from pipeline.run import Pipeline


class _Binary(BaseModule):
    """m3 double: publishes a raw_score, no content."""

    name = ModuleName.M3_ENCODER
    provides = frozenset({"content"})
    emits_spans = False

    def __init__(self, score: float, only_with_channel: bool = False) -> None:
        super().__init__()
        self.score = score
        self.only_with_channel = only_with_channel

    def _run(self, ctx: Context) -> ModuleOutput:
        if self.only_with_channel and ctx.normalized_text is None:
            return ModuleOutput(signals={"raw_score": 0.0, "artifact": "double"})
        return ModuleOutput(signals={"raw_score": self.score, "artifact": "double"})


class _Channel(BaseModule):
    """m2 double that always publishes a normalized channel."""

    name = ModuleName.M2_DEOBF
    provides = frozenset({"normalized_text", "form"})
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(normalized_text=ctx.text)


class _Stub(BaseModule):
    name = ModuleName.M2_DEOBF
    provides = frozenset({"normalized_text", "form"})
    emits_spans = False
    stub = True

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(notes=["stub: detection not implemented"])


class _Failing(BaseModule):
    name = ModuleName.M5_SARCASM
    provides = frozenset({"content"})
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        raise ValueError("boom")


class _Invalid(BaseModule):
    """Declares spans and emits a score without one: dropped by _merge."""

    name = ModuleName.M6_TARGET
    provides = frozenset({"target", "content"})
    emits_spans = True

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(content=[ContentScore(ContentCode.B4, 0.9, "m6_target@raw")])


class _Lexicon(BaseModule):
    """m1 double: A1 with a span on 'kotu'; a collision guard on 'amca'."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content", "guards"})
    emits_spans = True

    def _run(self, ctx: Context) -> ModuleOutput:
        content = [ContentScore(ContentCode.A1, 1.0, "m1_lexicon@raw", span=(0, 4))] if "kotu" in ctx.text else []
        guards = ([GuardResult(GuardCode.SUBSTRING_COLLISION, 1.0, "m1_lexicon", "amca", span=(0, 4))]
                  if "amca" in ctx.text else [])
        return ModuleOutput(content=content, guards=guards)


class _Harness(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.cfg = fusion.load_config()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def jsonl(self, name: str, items: list[dict]) -> Path:
        path = self.dir / name
        path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
        return path

    def evaluator(self, module: BaseModule, traps: list[dict] | None = None,
                  fixture: list[dict] | None = None) -> ModuleEvaluator:
        fixture_path = self.jsonl("fixture.jsonl", fixture or [{"id": "f1", "text": "temiz", "expected": []}])
        traps_path = self.jsonl("traps.jsonl", traps or [{"id": "t1", "text": "goturmek", "must_not_fire": ["*"]}])
        return ModuleEvaluator(module, fixture_path, traps_path=traps_path, results_dir=self.dir, n_boot=10,
                               latency_repeats=1)


class DegradationInHarnessTest(_Harness):
    def test_harness_degrades_exactly_as_the_pipeline_does(self) -> None:
        """The harness's degraded entry is byte-for-byte the pipeline's for the same output."""
        for module in (_Stub(), _Failing(), _Invalid(), _Binary(0.1)):
            with self.subTest(module=type(module).__name__, stage="DEGRADATION"):
                in_pipeline = Pipeline(modules=[module], config=self.cfg).analyze("temiz")
                _, in_harness, _ = self.evaluator(module).run_item({"id": "x", "text": "temiz"})
                self.assertEqual(in_harness.signals["pipeline"]["degraded"],
                                 in_pipeline.signals["pipeline"]["degraded"])

    def test_degradation_record_kinds(self) -> None:
        for module, kinds in ((_Stub(), ["stub"]), (_Failing(), ["failed"]), (_Invalid(), ["invalid_output"]),
                              (_Binary(0.1), None)):
            module.load()
            out = module.process(Context(text="x"))
            problems = list(Pipeline._merge(harness.AnalysisResult(text="x"), out, module))
            record = degradation_record(module, out, problems)
            with self.subTest(module=type(module).__name__):
                self.assertEqual(None if kinds is None else record["kinds"], kinds)

    def test_stub_fixture_item_is_degraded_and_its_verdict_is_never_clean(self) -> None:
        evaluator = self.evaluator(_Stub())
        _, result, predicted = evaluator.run_item({"id": "f1", "text": "temiz", "expected": []})
        with self.subTest(stage="DEGRADATION"):
            self.assertEqual([d["module"] for d in result.signals["pipeline"]["degraded"]], ["m2_deobf"])
        with self.subTest(stage="FINAL_ACTION"):
            self.assertIs(result.verdict, actions.DEGRADED_ACTION)
            self.assertEqual(predicted, set())        # scoring is unchanged: degradation is not a prediction
        report = evaluator.evaluate()
        with self.subTest(stage="REPORT"):
            self.assertEqual(report["degraded_items"]["n"], 1)
            self.assertTrue(report["implementation"]["stub"])
            self.assertFalse(report["implementation"]["behaviour_measurable"])
            self.assertIn("NOT VERIFIED", report["implementation"]["scope"])
            text = summarize(report)
            self.assertIn("[STUB]", text)
            self.assertIn("NOT VERIFIED", text)
            self.assertIn("degraded_items=1", text)

    def test_implementation_status_disagreeing_with_the_stub_flag_is_reported(self) -> None:
        declared = {"modules": {"m2_deobf": {"status": "IMPLEMENTED", "not_built": []}}}
        path = self.dir / "status.json"
        path.write_text(json.dumps(declared), encoding="utf-8")
        with mock.patch.object(harness, "IMPLEMENTATION_STATUS_PATH", path):
            status = implementation_status(_Stub())
        self.assertFalse(status["consistent"])
        self.assertFalse(status["behaviour_measurable"])
        self.assertIn("INCONSISTENT", status["scope"])

    def test_undeclared_module_is_not_measurable(self) -> None:
        path = self.dir / "status.json"
        path.write_text(json.dumps({"modules": {}}), encoding="utf-8")
        with mock.patch.object(harness, "IMPLEMENTATION_STATUS_PATH", path):
            status = implementation_status(_Lexicon())
        self.assertEqual(status["declared_status"], "UNDECLARED")
        self.assertFalse(status["behaviour_measurable"])


class TrapBinaryTest(_Harness):
    def test_binary_fire_is_observed_even_without_a_rule(self) -> None:
        report = self.evaluator(_Binary(0.99)).check_traps()
        with self.subTest(stage="CONTENT_FIRED"):
            self.assertEqual(report["regressions"], 0)               # content rule: nothing fired
            self.assertEqual(report["observations"][0]["content_fired"], [])
        with self.subTest(stage="BINARY_FIRED"):
            self.assertEqual(report["binary_fired"], ["t1"])
            self.assertTrue(report["binary_observable"])
            binary = report["observations"][0]["binary"]
            self.assertTrue(binary["fired"])
            self.assertEqual(binary["threshold"], float(self.cfg["binary_offensive"]["threshold"]))
        with self.subTest(stage="FINAL_VERDICT"):
            self.assertEqual(report["observations"][0]["verdict"], self.cfg["binary_offensive"]["action"])
            self.assertEqual(report["observations"][0]["driver"], "binary_offensive")
            self.assertTrue(report["observations"][0]["post_offensive"])

    def test_binary_below_threshold_is_observed_as_not_fired(self) -> None:
        report = self.evaluator(_Binary(0.0)).check_traps()
        self.assertEqual(report["binary_fired"], [])
        self.assertTrue(report["binary_observable"])
        self.assertFalse(report["observations"][0]["binary"]["fired"])
        self.assertEqual(report["observations"][0]["verdict"], Action.CLEAN.value)

    def test_binary_rule_turns_the_fire_into_a_regression(self) -> None:
        trap = {"id": "t1", "text": "goturmek", "must_not_fire": ["*"],
                "binary": {"modules": ["m3_encoder"], "must_not_fire": True}}
        report = self.evaluator(_Binary(0.99), traps=[trap]).check_traps()
        self.assertEqual(report["regressions"], 1)
        self.assertTrue(report["failures"][0]["problems"][0].startswith("binary: fired"))
        clean = self.evaluator(_Binary(0.0), traps=[trap]).check_traps()
        self.assertEqual(clean["regressions"], 0)

    def test_binary_rule_on_a_listed_module_without_a_score_is_a_failure(self) -> None:
        trap = {"id": "t1", "text": "goturmek", "binary": {"modules": ["m1_lexicon"], "must_not_fire": True}}
        report = self.evaluator(_Lexicon(), traps=[trap]).check_traps()
        self.assertEqual(report["regressions"], 1)
        self.assertIn("no numeric score", report["failures"][0]["problems"][0])
        self.assertFalse(report["binary_observable"])

    def test_binary_rule_is_scoped_to_the_listed_modules(self) -> None:
        trap = {"id": "t1", "text": "goturmek", "binary": {"modules": ["m3_encoder"], "must_not_fire": True}}
        report = self.evaluator(_Lexicon(), traps=[trap]).check_traps()
        self.assertEqual(report["regressions"], 0)

    def test_observation_keeps_the_four_facts_separate(self) -> None:
        traps = [{"id": "hit", "text": "kotu", "must_not_fire": []},
                 {"id": "guard", "text": "amca", "must_not_fire": ["*"]}]
        report = self.evaluator(_Lexicon(), traps=traps).check_traps()
        hit, guard = report["observations"]
        with self.subTest(stage="CONTENT_FIRED"):
            self.assertEqual(hit["content_fired"], ["A1"])
            self.assertEqual(hit["content_scored"], ["A1<-m1_lexicon@raw"])
            self.assertEqual(guard["content_fired"], [])
        with self.subTest(stage="BINARY_FIRED"):
            self.assertIsNotNone(hit["binary"])                      # the block exists ...
            self.assertIsNone(hit["binary"]["fired"])               # ... but no score was published
        with self.subTest(stage="FORM/GUARD EFFECT"):
            self.assertEqual(guard["guards_active"], ["SUBSTRING_COLLISION"])
            self.assertEqual(guard["guards_suppressed"], {})
            self.assertEqual(hit["guards_active"], [])
        with self.subTest(stage="FINAL_VERDICT"):
            self.assertEqual(hit["verdict"], self.cfg["categories"]["A1"]["action"])
            self.assertEqual(hit["driver"], "content:A1")
            self.assertEqual(guard["verdict"], Action.CLEAN.value)
            self.assertIsNone(guard["driver"])
        self.assertEqual(report["regressions"], 0)


class PipelineBudgetBinaryTest(_Harness):
    def test_binary_fire_on_traps_is_reported_next_to_the_flip_rate(self) -> None:
        traps = self.jsonl("traps.jsonl", [{"id": "t1", "text": "goturmek", "must_not_fire": ["*"]}])
        report = pipeline_budget_report(modules=[_Binary(0.99)], traps_path=traps, texts=["x"], runs=1)
        with self.subTest(stage="CONTENT flip rate"):
            self.assertEqual(report["clean_to_dirty_flip_rate"]["value"], 0.0)
        with self.subTest(stage="BINARY_FIRED"):
            self.assertEqual(report["binary_offensive_on_traps"]["fired_with_channel_trap_ids"], ["t1"])
            self.assertEqual(report["binary_offensive_on_traps"]["flipped_by_channel_trap_ids"], [])
            self.assertFalse(report["binary_offensive_on_traps"]["budgeted"])
            self.assertEqual(report["trap_observations"][0]["driver"], "binary_offensive")
        with self.subTest(stage="PROVENANCE"):
            self.assertIn("git_head", report["provenance"])
            self.assertEqual(report["provenance"]["inputs"]["traps"]["sha256"],
                             hashlib.sha256(traps.read_bytes()).hexdigest())
            self.assertEqual(report["provenance"]["traps_n"], 1)

    def test_a_binary_flip_caused_by_the_channel_is_visible_but_not_budgeted(self) -> None:
        traps = self.jsonl("traps.jsonl", [{"id": "t1", "text": "goturmek", "must_not_fire": ["*"]}])
        report = pipeline_budget_report(modules=[_Channel(), _Binary(0.99, only_with_channel=True)],
                                        traps_path=traps, texts=["x"], runs=1)
        self.assertEqual(report["clean_to_dirty_flip_rate"]["flipped_trap_ids"], [])
        self.assertTrue(report["clean_to_dirty_flip_rate"]["within_budget"])
        self.assertEqual(report["binary_offensive_on_traps"]["flipped_by_channel_trap_ids"], ["t1"])

    def test_degraded_modules_are_listed_for_the_full_pipeline_run(self) -> None:
        traps = self.jsonl("traps.jsonl", [{"id": "t1", "text": "x", "must_not_fire": ["*"]}])
        report = pipeline_budget_report(modules=[_Stub(), _Binary(0.0)], traps_path=traps, texts=["x"], runs=1)
        self.assertEqual(report["degraded_modules"], ["m2_deobf"])
        self.assertEqual(report["trap_observations"][0]["degraded"], ["m2_deobf"])
        self.assertEqual(report["trap_observations"][0]["verdict"], actions.DEGRADED_ACTION.value)


class ProvenanceTest(_Harness):
    def test_provenance_ties_a_report_to_bytes_and_a_commit(self) -> None:
        traps = self.jsonl("traps.jsonl", [{"id": "t1", "text": "x"}])
        report = self.evaluator(_Lexicon()).evaluate()
        prov = report["provenance"]
        self.assertEqual(set(prov) >= {"git_head", "git_dirty", "inputs", "python", "traps_n", "latency_repeats"}, True)
        self.assertEqual(prov["inputs"]["traps"]["sha256"], hashlib.sha256(traps.read_bytes()).hexdigest())
        self.assertEqual(prov["inputs"]["thresholds"]["sha256"],
                         hashlib.sha256(fusion.DEFAULT_CONFIG_PATH.read_bytes()).hexdigest())
        self.assertEqual(prov["traps_n"], 1)
        self.assertEqual(prov["latency_repeats"], 1)
        if prov["git_head"] is not None:
            self.assertRegex(prov["git_head"], r"^[0-9a-f]{40}$")
            self.assertIsInstance(prov["git_dirty"], bool)


if __name__ == "__main__":
    unittest.main()
