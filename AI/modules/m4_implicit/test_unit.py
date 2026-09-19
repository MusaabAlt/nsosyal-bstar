"""Unit tests for m4_implicit: the contract, and the stage-1 signals m4 publishes from what m3
publishes (spec.md §4-§5). C1-C5 behaviour tests arrive with m3's C head (ADR-006)."""
from __future__ import annotations

import copy
import unittest
from types import MappingProxyType

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m4_implicit.module import NOTE_C_FAMILY, STAGE1_DERIVED_FOR, ImplicitModule


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


def with_m3(**published: object) -> Context:
    """A context carrying what m3_encoder publishes (m4 spec.md §5), frozen like the pipeline's."""
    return Context(text="Bu bir test cumlesi", signals=MappingProxyType({"m3_encoder": MappingProxyType(published)}))


SIGNAL_KEYS = {"stage", "stage1_input", "stage1_input_present", "m3_artifact", "stage1_derived_for",
               "stage1_protocol", "stage1_artifact_match", "norm_minus_raw"}


class ImplicitModuleRoleTest(unittest.TestCase):
    def test_not_a_stub_and_never_scores_content(self) -> None:
        # ADR-006: C1-C5 come from m3's C head; m4 emits no content, guard or target of its own.
        module = ImplicitModule()
        self.assertFalse(getattr(module, "stub", False))
        for ctx in (Context(text="Bu bir test cumlesi"), with_m3(raw_score=1.0, norm_score=1.0, artifact=STAGE1_DERIVED_FOR)):
            out = module.process(ctx)
            self.assertTrue(out.ok, out.notes)
            self.assertEqual((out.content, out.guards, out.target, out.form), ([], [], None, None))
            self.assertEqual(out.notes[0], NOTE_C_FAMILY)
        self.assertEqual(NOTE_C_FAMILY, "C1–C5 not implemented yet")


class ImplicitModuleStageOneTest(unittest.TestCase):
    """What stage 1 runs on, read from m3's published signals (spec.md §4-§5, ADR-006 amendment 2026-09-19)."""

    def setUp(self) -> None:
        self.module = ImplicitModule()

    def test_publishes_stage_one_from_m3_signals(self) -> None:
        out = self.module.process(with_m3(raw_score=0.25, norm_score=0.75, artifact=STAGE1_DERIVED_FOR))
        self.assertEqual(set(out.signals), SIGNAL_KEYS)
        self.assertEqual(out.signals["stage"], 1)
        self.assertEqual(out.signals["stage1_input"], "m3_encoder.raw_score")
        self.assertIs(out.signals["stage1_input_present"], True)
        self.assertEqual(out.signals["m3_artifact"], STAGE1_DERIVED_FOR)
        self.assertEqual(out.signals["stage1_derived_for"], "m3-berturk-multihead-a-rule-v4-20260918-163728")
        self.assertEqual(out.signals["stage1_protocol"],
                         "protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md")
        self.assertIs(out.signals["stage1_artifact_match"], True)
        self.assertEqual(out.signals["norm_minus_raw"], 0.5)
        self.assertEqual(out.notes, [NOTE_C_FAMILY])

    def test_channel_gap_is_signed(self) -> None:
        # Negative: the original text scores higher than its de-obfuscated channel.
        out = self.module.process(with_m3(raw_score=0.75, norm_score=0.25, artifact=STAGE1_DERIVED_FOR))
        self.assertEqual(out.signals["norm_minus_raw"], -0.5)

    def test_no_m3_signals_means_no_stage_one_input(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertEqual(set(out.signals), SIGNAL_KEYS)
        self.assertIs(out.signals["stage1_input_present"], False)
        self.assertIsNone(out.signals["m3_artifact"])
        self.assertIsNone(out.signals["stage1_artifact_match"])
        self.assertIsNone(out.signals["norm_minus_raw"])
        self.assertEqual(out.notes, [NOTE_C_FAMILY, "stage 1 had no input: m3_encoder published no raw_score"])

    def test_raw_only_has_no_channel_gap(self) -> None:
        out = self.module.process(with_m3(raw_score=0.5, artifact=STAGE1_DERIVED_FOR))
        self.assertIs(out.signals["stage1_input_present"], True)
        self.assertIsNone(out.signals["norm_minus_raw"])
        self.assertEqual(out.notes, [NOTE_C_FAMILY])

    def test_unusable_scores_count_as_absent(self) -> None:
        for bad in (float("nan"), float("inf"), True, "0.9", None):
            with self.subTest(bad=bad):
                out = self.module.process(with_m3(raw_score=bad, norm_score=0.5, artifact=STAGE1_DERIVED_FOR))
                self.assertIs(out.signals["stage1_input_present"], False)
                self.assertIsNone(out.signals["norm_minus_raw"])
                self.assertIn("stage 1 had no input: m3_encoder published no raw_score", out.notes)

    def test_other_artifact_is_flagged_not_hidden(self) -> None:
        # e.g. the binary baseline selected explicitly through NSOSYAL_M3_ARTIFACT: the stage-1 threshold
        # in force was derived for rule-v4 only (decision/thresholds.yaml binary_offensive comment).
        other = "m3-berturk-pytorch-fp32-epoch1"
        out = self.module.process(with_m3(raw_score=0.5, norm_score=0.5, artifact=other))
        self.assertEqual(out.signals["m3_artifact"], other)
        self.assertIs(out.signals["stage1_artifact_match"], False)
        self.assertEqual(out.notes, [NOTE_C_FAMILY,
                                     f"stage 1: binary_offensive was derived for {STAGE1_DERIVED_FOR}; this score "
                                     f"comes from {other}, for which no binary_offensive threshold was derived"])
        self.assertEqual(out.content, [])

    def test_score_magnitude_never_changes_what_m4_emits(self) -> None:
        # Rule 4: m4 thresholds nothing, so only the published numbers move with the score.
        low = self.module.process(with_m3(raw_score=0.0, norm_score=0.0, artifact=STAGE1_DERIVED_FOR))
        high = self.module.process(with_m3(raw_score=1.0, norm_score=1.0, artifact=STAGE1_DERIVED_FOR))
        self.assertEqual((low.content, low.notes, low.signals), (high.content, high.notes, high.signals))

    def test_deterministic(self) -> None:
        ctx = with_m3(raw_score=0.125, norm_score=0.875, artifact=STAGE1_DERIVED_FOR)
        first, second = self.module.process(ctx), self.module.process(ctx)
        self.assertEqual((first.signals, first.notes), (second.signals, second.notes))


if __name__ == "__main__":
    unittest.main()
