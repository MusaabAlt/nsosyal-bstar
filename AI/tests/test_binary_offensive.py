"""binary_offensive against the REAL thresholds.yaml (Gate 1, task 1).

Every other decision-layer test pins its own numbers so it tests logic, not
placeholders. This file does the opposite on purpose: it loads the shipped
configuration unchanged and proves what the ONE derived threshold does at its
boundary, because nothing else in the suite observes it (TEST_SYSTEM_AUDIT.md §3).

Labels used in test names / docstrings:
  NO-MODEL   the decision layer alone on a hand-built AnalysisResult; m3 is not run
  DOUBLE     a pipeline with a test double standing in for m3

Nothing here changes the threshold; the tests read it and fail if it drifts from
the derivation record. Q1-Q6 (frozen policy questions) are not touched: every
expected verdict below follows from a single fired signal and the shipped
action for it, with no guard, no target and no degradation in play.
"""
from __future__ import annotations

import copy
import math
import re
import unittest
from pathlib import Path

from contracts.codes import Action, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import AnalysisResult
from decision import actions, fusion
from eval import m4_stage1b
from pipeline.run import Pipeline
from pipeline.thread_counter import ThreadBlock

ROOT = Path(__file__).resolve().parent.parent
# The threshold in force was derived for the deployed m3 artifact (rule-v4, 2026-09-19); the baseline's
# derivation (0.320188, 2026-09-15) stays the historical record that stage 1b was measured against.
DERIVATION_PROTOCOL = ROOT / "protocols" / "threshold_derivation_binary_offensive_stage1_rule_v4.md"
BASELINE_PROTOCOL = ROOT / "protocols" / "threshold_derivation_binary_offensive_stage1.md"
# Each derivation file records its tie row at full precision. Quoted verbatim from those files;
# if a file changes, the test that reads it tells us.
TIE_ROW_PATTERN = re.compile(r"scores exactly\s+\*\*([0-9.]+)\*\*")
BASELINE_TIE_ROW_PATTERN = re.compile(r"\*\*(0\.32018762826919556)\*\*")
EVAL_T_PATTERN = re.compile(r"EVAL confusion at t = ([0-9.]+)")


def binary_signals(score: object) -> dict:
    """Signals as m3 publishes them, keyed exactly as thresholds.yaml reads them."""
    cfg = fusion.load_config()
    module, key = cfg["binary_offensive"]["channels"]["raw"].split(".", 1)
    return {module: {key: score}}


class RealConfigTest(unittest.TestCase):
    """The shipped binary_offensive entry, as loaded - no override anywhere."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = fusion.load_config()
        cls.entry = cls.cfg["binary_offensive"]
        cls.t = float(cls.entry["threshold"])

    def test_entry_is_stage_1_raw_channel_only(self) -> None:
        with self.subTest(stage="INTERFACE_CONTRACT"):
            self.assertEqual(self.entry["channels"], {"raw": "m3_encoder.raw_score"})
            self.assertNotIn("threshold_when", self.entry)          # ADR-006: stage 1, not 1b
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertEqual(self.cfg["artifact"]["status"], "derived")
            self.assertTrue(0 < self.t < 1)

    def test_threshold_equals_the_derivation_record(self) -> None:
        """The number in the yaml is the number the rule-v4 protocol derived; the stage-1b script
        carries the BASELINE constant it was measured against, which stays equal to its own record."""
        recorded = EVAL_T_PATTERN.search(DERIVATION_PROTOCOL.read_text(encoding="utf-8"))
        self.assertIsNotNone(recorded, f"{DERIVATION_PROTOCOL.name} no longer states the EVAL threshold")
        with self.subTest(source="derivation protocol"):
            self.assertEqual(float(recorded.group(1)), self.t)
        baseline = EVAL_T_PATTERN.search(BASELINE_PROTOCOL.read_text(encoding="utf-8"))
        with self.subTest(source="eval.m4_stage1b EXPECTED = the baseline record"):
            self.assertEqual(float(m4_stage1b.EXPECTED["stage1_t"]), float(baseline.group(1)))
            self.assertNotEqual(float(baseline.group(1)), self.t)   # the baseline value is not in force


class BoundaryTest(unittest.TestCase):
    """NO-MODEL. fired == (score > threshold) at and around the real threshold: the derivation rule
    (protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md §3), used by fusion since 2026-09-19."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = fusion.load_config()
        cls.t = float(cls.cfg["binary_offensive"]["threshold"])
        cls.binary_action = Action(cls.cfg["binary_offensive"]["action"])

    def decide(self, score: object) -> tuple[AnalysisResult, dict]:
        result = fusion.decide(AnalysisResult(text="x", signals=binary_signals(score)), self.cfg)
        return result, result.signals["decision"]["binary_offensive"]

    def assertBinary(self, score: float, fired: bool) -> None:
        result, binary = self.decide(score)
        with self.subTest(stage="DECISION_THRESHOLD", score=repr(score)):
            self.assertEqual(binary["threshold"], self.t)
            self.assertEqual(binary["branch"], "scalar")
            self.assertEqual(binary["channels"]["raw"]["score"], score)
            self.assertIs(binary["channels"]["raw"]["fired"], fired)
            self.assertIs(binary["fired"], fired)
            self.assertEqual(binary["action"], self.binary_action.value)
        with self.subTest(stage="DECISION_THRESHOLD/post_offensive", score=repr(score)):
            self.assertIs(result.signals["decision"]["post_offensive"], fired)
            self.assertIs(fusion.post_is_offensive(result), fired)
        verdict, driver = actions.resolve(result, self.cfg)
        with self.subTest(stage="FINAL_ACTION", score=repr(score)):
            if fired:
                # Only signal present, nothing degraded: the binary action is the verdict.
                self.assertIs(result.verdict, self.binary_action)
                self.assertIs(verdict, self.binary_action)
                self.assertEqual(driver, "binary_offensive")
                self.assertIn("genel saldırganlık skoru", result.explanation)
            else:
                self.assertIs(result.verdict, Action.CLEAN)
                self.assertIsNone(driver)

    def test_score_absent_is_not_a_fire(self) -> None:
        result = fusion.decide(AnalysisResult(text="x"), self.cfg)
        binary = result.signals["decision"]["binary_offensive"]
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertIsNotNone(binary, "binary_offensive block must exist even without a score")
            self.assertEqual(binary["channels"]["raw"], {"score": None, "fired": None})
            self.assertIsNone(binary["fired"])
        with self.subTest(stage="FINAL_ACTION"):
            self.assertFalse(result.signals["decision"]["post_offensive"])
            self.assertIs(result.verdict, Action.CLEAN)

    def test_non_numeric_score_is_not_a_fire(self) -> None:
        for bad in (True, "0.9", None, [0.9]):
            with self.subTest(stage="INTERFACE_CONTRACT", value=repr(bad)):
                _, binary = self.decide(bad)
                self.assertEqual(binary["channels"]["raw"], {"score": None, "fired": None})
                self.assertIsNone(binary["fired"])

    def test_just_below_threshold_does_not_fire(self) -> None:
        self.assertBinary(math.nextafter(self.t, 0.0), fired=False)

    def test_exactly_threshold_does_not_fire(self) -> None:
        # fusion flags at >, the rule the threshold was derived with; a score equal to t is not flagged.
        self.assertBinary(self.t, fired=False)

    def test_just_above_threshold_fires(self) -> None:
        self.assertBinary(math.nextafter(self.t, 1.0), fired=True)

    def test_tie_row_is_not_flagged_at_runtime(self) -> None:
        """Dev row 46164 scores exactly the rule-v4 threshold (it is the CAL score the fit chose). The
        derivation rule `score > t` does not flag it, and neither does fusion (protocol, 'Tie row')."""
        found = TIE_ROW_PATTERN.search(DERIVATION_PROTOCOL.read_text(encoding="utf-8"))
        self.assertIsNotNone(found, "the derivation protocol no longer records the tie row value")
        tie = float(found.group(1))
        self.assertEqual(tie, self.t)
        self.assertBinary(tie, fired=False)

    def test_baseline_tie_row_record_is_unchanged(self) -> None:
        """Historical record: the baseline's tie row (dev row 29308, 0.32018762826919556) sat below its
        6-decimal threshold 0.320188."""
        text = BASELINE_PROTOCOL.read_text(encoding="utf-8")
        tie = float(BASELINE_TIE_ROW_PATTERN.search(text).group(1))
        self.assertLess(tie, float(EVAL_T_PATTERN.search(text).group(1)))

    def test_fired_is_score_gt_threshold_across_the_range(self) -> None:
        for score in (0.0, self.t / 2, math.nextafter(self.t, 0.0), self.t, math.nextafter(self.t, 1.0),
                      (self.t + 1.0) / 2, 1.0):
            self.assertBinary(score, fired=score > self.t)

    def test_deciding_twice_keeps_the_same_binary_state(self) -> None:
        result, first = self.decide(self.t)
        fusion.decide(result, self.cfg)
        self.assertEqual(result.signals["decision"]["binary_offensive"], first)


class _BinaryOnly(BaseModule):
    """DOUBLE for m3: publishes the score it was given, no content, no spans."""

    name = ModuleName.M3_ENCODER
    provides = frozenset({"content"})
    emits_spans = False

    def __init__(self, score: float) -> None:
        super().__init__()
        self.score = score

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(signals={"raw_score": self.score, "artifact": "test-double"})


class BinaryThroughPipelineTest(unittest.TestCase):
    """DOUBLE. The score travels module -> merge -> decision -> counter -> verdict
    under the real config; nothing else is in the pipeline, so nothing is degraded."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = fusion.load_config()
        cls.t = float(cls.cfg["binary_offensive"]["threshold"])

    def test_binary_only_post_counts_as_offensive_for_the_thread_counter(self) -> None:
        """G0-7: post_is_offensive's binary branch feeds the repetition counter. The smallest firing
        score is the next float above t (fusion flags at score > t)."""
        cfg = copy.deepcopy(self.cfg)
        pipeline = Pipeline(modules=[_BinaryOnly(math.nextafter(self.t, 1.0))], config=cfg)
        block = ThreadBlock("u1", "u2")
        results = [pipeline.analyze("x", thread_block=block) for _ in range(int(cfg["thread"]["min_repeats"]))]
        with self.subTest(stage="DEGRADATION"):
            self.assertEqual(results[-1].signals["pipeline"]["degraded"], [])
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertTrue(all(r.signals["decision"]["binary_offensive"]["fired"] for r in results))
            self.assertEqual(results[-1].content, [])
            self.assertTrue(all(r.signals["decision"]["post_offensive"] for r in results))
        with self.subTest(stage="PIPELINE_MERGE/thread"):
            self.assertEqual([r.thread.repeat_count for r in results], list(range(1, len(results) + 1)))
            self.assertEqual([r.thread.fired for r in results], [False] * (len(results) - 1) + [True])
        with self.subTest(stage="FINAL_ACTION"):
            binary_action = Action(cfg["binary_offensive"]["action"])
            thread_action = Action(cfg["thread"]["action"])
            expected = min((binary_action, thread_action), key=actions.severity)
            self.assertIs(results[-1].verdict, expected)
            self.assertIs(results[0].verdict, binary_action)

    def test_binary_below_threshold_is_never_counted(self) -> None:
        pipeline = Pipeline(modules=[_BinaryOnly(math.nextafter(self.t, 0.0))], config=copy.deepcopy(self.cfg))
        block = ThreadBlock("u1", "u2")
        results = [pipeline.analyze("x", thread_block=block) for _ in range(5)]
        self.assertEqual({r.thread.repeat_count for r in results}, {0})
        self.assertEqual({r.verdict for r in results}, {Action.CLEAN})
        self.assertFalse(results[-1].signals["decision"]["post_offensive"])


if __name__ == "__main__":
    unittest.main()
