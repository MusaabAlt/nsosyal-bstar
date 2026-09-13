from __future__ import annotations

import copy
import unittest

from contracts.codes import Action, ContentCode, FormCode, GuardCode
from contracts.schema import AnalysisResult, ContentScore, FormPattern, GuardResult, ThreadSignal
from decision import fusion


def score(code: str, value: float, source: str = "m@raw") -> ContentScore:
    return ContentScore(ContentCode(code), value, source)


class DecisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_cfg = fusion.load_config()

    def setUp(self) -> None:
        # Tests pin their own numbers so they do not depend on placeholder values.
        self.cfg = copy.deepcopy(self.base_cfg)
        for entry in self.cfg["categories"].values():
            entry["threshold"] = 0.5
        for entry in self.cfg["guards"].values():
            entry["threshold"] = 0.5
        self.cfg["form"]["min_confidence"] = 0.5
        self.cfg["categories"]["A2"]["action"] = "review"
        self.cfg["categories"]["B2"]["action"] = "escalate"
        self.cfg["categories"]["A3"]["action"] = "block"

    def test_config_loads_and_validates(self) -> None:
        self.assertEqual(self.base_cfg["fusion"]["strategy"], "max")
        self.assertEqual(set(self.base_cfg["categories"]),
                         {c.value for c in ContentCode if c is not ContentCode.CLEAN})

    def test_invalid_config_fails_loudly(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["categories"]["A1"]["action"] = "delete"
        with self.assertRaises(ValueError):
            fusion.validate_config(bad)

    def test_clean_when_nothing_scores(self) -> None:
        result = fusion.decide(AnalysisResult(text="x"), self.cfg)
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertTrue(result.explanation.endswith("."))

    def test_max_fusion_across_channels_keeps_winning_source(self) -> None:
        result = AnalysisResult(text="x", content=[score("A2", 0.3, "m1@raw"), score("A2", 0.8, "m1@normalized")])
        fusion.decide(result, self.cfg)
        [fused] = result.content
        self.assertEqual(fused.source, "m1@normalized")
        self.assertTrue(fused.fired)
        self.assertEqual(fused.threshold, 0.5)
        self.assertEqual(len(result.signals["decision"]["channel_scores"]), 2)

    def test_most_severe_action_wins(self) -> None:
        result = AnalysisResult(text="x", content=[score("A2", 0.9), score("B2", 0.6)])
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.ESCALATE)
        self.assertIn("B2", result.explanation)

    def test_guard_suppresses_family(self) -> None:
        result = AnalysisResult(
            text="x",
            content=[score("A3", 0.9), score("B2", 0.9)],
            guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.95, "m1_lexicon")],
        )
        fusion.decide(result, self.cfg)
        fired = {s.code.value for s in result.fired()}
        self.assertEqual(fired, {"B2"})
        self.assertEqual(result.guards[0].suppressed, [ContentCode.A3])
        self.assertIs(result.verdict, Action.ESCALATE)

    def test_inactive_guard_suppresses_nothing(self) -> None:
        result = AnalysisResult(text="x", content=[score("A3", 0.9)],
                                guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.1, "m1_lexicon")])
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.BLOCK)
        self.assertFalse(result.guards[0].active)

    def test_clean_explanation_names_suppressing_guard(self) -> None:
        result = AnalysisResult(text="x", content=[score("A1", 0.9)],
                                guards=[GuardResult(GuardCode.QUOTE_COUNTERSPEECH, 0.9, "m3")])
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertIn("bastırıldı", result.explanation)

    def test_form_active_codes(self) -> None:
        result = AnalysisResult(text="x")
        result.form.patterns = [FormPattern(FormCode.DOTLESS_I, 0.1, "casing"),
                                FormPattern(FormCode.ZERO_WIDTH, 0.95, "zw")]
        fusion.decide(result, self.cfg)
        self.assertEqual(result.form.active, [FormCode.ZERO_WIDTH])

    def test_thread_rule(self) -> None:
        result = AnalysisResult(text="x", thread=ThreadSignal(repeat_count=5, same_target=True))
        fusion.decide(result, self.cfg)
        self.assertTrue(result.thread.fired)
        self.assertIs(result.verdict, Action(self.cfg["thread"]["action"]))

    def test_thread_rule_requires_same_target(self) -> None:
        result = AnalysisResult(text="x", thread=ThreadSignal(repeat_count=5, same_target=False))
        fusion.decide(result, self.cfg)
        self.assertFalse(result.thread.fired)

    def test_fast_path_hit(self) -> None:
        self.cfg["fast_path"]["margin"] = 0.3
        self.assertTrue(fusion.fast_path_hit([score("A3", 0.85)], [], self.cfg))
        self.assertFalse(fusion.fast_path_hit([score("A3", 0.7)], [], self.cfg))
        guard = GuardResult(GuardCode.HOMONYM, 0.9, "m1")
        self.assertFalse(fusion.fast_path_hit([score("A3", 0.85)], [guard], self.cfg))


if __name__ == "__main__":
    unittest.main()
