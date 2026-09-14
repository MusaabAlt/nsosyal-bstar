from __future__ import annotations

import copy
import unittest

from contracts.codes import Action, ContentCode, FormCode, GuardCode
from contracts.schema import AnalysisResult, ContentScore, FormPattern, GuardResult, ThreadSignal
from decision import fusion


def score(code: str, value: float, source: str = "m@raw", span: tuple[int, int] | None = None) -> ContentScore:
    return ContentScore(ContentCode(code), value, source, span=span)


def guard(code: GuardCode, value: float, source: str, span: tuple[int, int] | None = None) -> GuardResult:
    return GuardResult(code, value, source, span=span)


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

    # -- ADR-001 guard scoping -------------------------------------------------
    def test_guard_suppresses_only_overlapping_same_module_score(self) -> None:
        # Replaces test_guard_suppresses_family: a guard is scoped to its own
        # module and its own span, never to a whole family across the post.
        result = AnalysisResult(
            text="x",
            content=[score("A3", 0.9, "m1_lexicon@raw", span=(10, 14)),   # overlaps the guard
                     score("A1", 0.9, "m1_lexicon@raw", span=(30, 35)),   # same family, elsewhere
                     score("B2", 0.9, "m1_lexicon@raw", span=(20, 25))],  # not in suppresses list
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.95, "m1_lexicon", span=(10, 15))],
        )
        fusion.decide(result, self.cfg)
        self.assertEqual({s.code.value for s in result.fired()}, {"A1", "B2"})
        self.assertEqual(result.guards[0].suppressed, [ContentCode.A3])
        self.assertIs(result.verdict, Action.ESCALATE)

    def test_insult_plus_unrelated_collision_still_blocks(self) -> None:
        # The exploit: A2=0.99 with a SUBSTRING_COLLISION raised on "amcam"
        # elsewhere in the same post must not clear the insult.
        self.cfg["categories"]["A2"]["action"] = "block"
        text = "<insult> amcam"
        result = AnalysisResult(
            text=text,
            content=[score("A2", 0.99, "m1_lexicon@raw", span=(0, 8))],
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon", span=(9, 14))],
        )
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.BLOCK)
        self.assertEqual(result.guards[0].suppressed, [])

    def test_guard_never_suppresses_across_modules(self) -> None:
        self.cfg["categories"]["A2"]["action"] = "block"
        result = AnalysisResult(
            text="x",
            content=[score("A2", 0.99, "m3_encoder@raw")],
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon")],
        )
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.BLOCK)

    def test_fallback_spanless_guard_suppresses_spanless_same_module_score(self) -> None:
        result = AnalysisResult(
            text="x",
            content=[score("A2", 0.99, "m1_lexicon@raw")],
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon")],
        )
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertEqual(result.guards[0].suppressed, [ContentCode.A2])

    def test_fallback_when_only_one_side_has_a_span(self) -> None:
        result = AnalysisResult(
            text="x",
            content=[score("A2", 0.99, "m1_lexicon@normalized")],
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon@raw", span=(9, 14))],
        )
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.CLEAN)

    def test_guard_without_source_suppresses_nothing(self) -> None:
        result = AnalysisResult(text="x", content=[score("A2", 0.99, "m1_lexicon@raw")],
                                guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.99)])
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.REVIEW)

    def test_suppressed_score_does_not_hide_other_module_score_for_same_code(self) -> None:
        result = AnalysisResult(
            text="x",
            content=[score("A2", 0.99, "m1_lexicon@raw", span=(9, 14)),
                     score("A2", 0.70, "m3_encoder@raw")],
            guards=[guard(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon", span=(9, 14))],
        )
        fusion.decide(result, self.cfg)
        [fused] = result.content
        self.assertTrue(fused.fired)
        self.assertEqual(fused.source, "m3_encoder@raw")
        self.assertIs(result.verdict, Action.REVIEW)

    def test_inactive_guard_suppresses_nothing(self) -> None:
        result = AnalysisResult(text="x", content=[score("A3", 0.9, "m1_lexicon@raw")],
                                guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.1, "m1_lexicon")])
        fusion.decide(result, self.cfg)
        self.assertIs(result.verdict, Action.BLOCK)
        self.assertFalse(result.guards[0].active)

    def test_clean_explanation_names_suppressing_guard(self) -> None:
        result = AnalysisResult(text="x", content=[score("A1", 0.9, "m3_encoder@raw")],
                                guards=[GuardResult(GuardCode.QUOTE_COUNTERSPEECH, 0.9, "m3_encoder@raw")])
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
