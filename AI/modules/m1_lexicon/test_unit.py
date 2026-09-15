"""Unit tests for m1_lexicon: contract tests and behaviour tests (spec.md §3, §7, §8)."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import ContentCode, GuardCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m1_lexicon.module import LexiconModule


class LexiconModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = LexiconModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m1_lexicon"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m1_lexicon")

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


TRAPS = Path(__file__).resolve().parents[2] / "eval" / "traps" / "traps.jsonl"


def fake_m6_target(target_type: str, target_confidence: float) -> MappingProxyType:
    """Stands in for m6_target with fixed values. modules.m6_target is never imported."""
    return MappingProxyType({"m6_target": MappingProxyType(
        {"target_type": target_type, "target_confidence": target_confidence})})


class LexiconModuleBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = LexiconModule()

    def run_m1(self, text: str, **kwargs) -> ModuleOutput:
        out = self.module.process(Context(text=text, **kwargs))
        self.assertTrue(out.ok, out.notes)
        return out

    def test_collision_traps_never_fire(self) -> None:
        traps = [json.loads(line) for line in TRAPS.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(traps)
        for trap in traps:
            with self.subTest(trap=trap["id"]):
                out = self.run_m1(trap["text"])
                self.assertEqual(out.content, [])
                self.assertFalse(out.signals["lexicon_hit"])
                self.assertIn(GuardCode.SUBSTRING_COLLISION, {g.code for g in out.guards})

    def test_inflected_root_matches_on_morpheme_boundary(self) -> None:
        for text, word in (("Onlar aptallar", "aptallar"), ("Sen bir gerizekalısın", "gerizekalısın"),
                           ("siktiler", "siktiler")):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual([s.code for s in out.content], [ContentCode.A1])
                start, end = out.content[0].span
                self.assertEqual(text[start:end], word)
                self.assertTrue(out.signals["lexicon_hit"])

    def test_root_inside_clean_word_is_a_collision_not_a_match(self) -> None:
        for text, word in (("amca", "amca"), ("psikoloji", "psikoloji"), ("götürdüler", "götürdüler")):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual(out.content, [])
                self.assertEqual([(g.code, text[g.span[0]:g.span[1]]) for g in out.guards],
                                 [(GuardCode.SUBSTRING_COLLISION, word)])

    def test_turkish_capital_i_is_dotless(self) -> None:
        # SIKINTI is sıkıntı: default lower() would read it as a profane root.
        self.assertEqual(self.run_m1("SIKINTI").content, [])
        self.assertEqual([s.code for s in self.run_m1("APTALLAR").content], [ContentCode.A1])

    def test_scores_tagged_with_channel(self) -> None:
        out = self.run_m1("a.p.t.a.l", charsafe_text="a.p.t.a.l", normalized_text="aptal....")
        self.assertEqual({s.source for s in out.content}, {"m1_lexicon@raw", "m1_lexicon@normalized"})
        out = self.run_m1("xptal herif", normalized_text="aptal herif")
        self.assertEqual([s.source for s in out.content], ["m1_lexicon@normalized"])
        self.assertEqual((out.signals["lexicon_hit_raw"], out.signals["lexicon_hit_norm"]), (False, True))

    def test_normalized_channel_without_offset_map_reports_flag_only(self) -> None:
        out = self.run_m1("xptal", normalized_text="aptal herif")
        self.assertEqual(out.content, [])
        self.assertTrue(out.signals["lexicon_hit_norm"])
        self.assertTrue(out.notes)

    def test_spans_map_through_m0_offsets(self) -> None:
        text = "ap​tal herif"
        signals = MappingProxyType({"m0_charsafe": MappingProxyType({"_offsets": [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11]})})
        out = self.run_m1(text, charsafe_text="aptal herif", signals=signals)
        self.assertEqual([s.span for s in out.content], [(0, 6)])

    def test_signals_present_and_boolean_on_every_input(self) -> None:
        for text in LexiconModuleContractTest.HOSTILE_INPUTS + ("Onlar aptallar",):
            with self.subTest(text=text[:20]):
                out = self.run_m1(text)
                for key in ("lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm"):
                    self.assertIs(type(out.signals[key]), bool)

    def test_every_item_carries_a_span_of_the_triggering_text(self) -> None:
        text = "Amcam aptallar psikoloji"
        out = self.run_m1(text, signals=fake_m6_target("non_human", 0.9))
        self.assertTrue(out.content and out.guards)
        for item in [*out.content, *out.guards]:
            self.assertIsNotNone(item.span)
        self.assertEqual({text[s.span[0]:s.span[1]] for s in out.content}, {"aptallar"})
        self.assertEqual({text[g.span[0]:g.span[1]] for g in out.guards
                          if g.code is GuardCode.SUBSTRING_COLLISION}, {"Amcam", "psikoloji"})
        self.assertEqual({g.source for g in out.guards}, {"m1_lexicon"})

    def test_non_human_target_raises_guard_on_family_a_matches(self) -> None:
        text = "aptal film"
        out = self.run_m1(text, signals=fake_m6_target("non_human", 0.9))
        guards = [g for g in out.guards if g.code is GuardCode.NON_HUMAN_TARGET]
        self.assertEqual([text[g.span[0]:g.span[1]] for g in guards], ["aptal"])
        self.assertEqual({g.score for g in guards}, {0.9})   # score = m6's target_confidence (spec §3)
        self.assertEqual([g for g in self.run_m1(text, signals=fake_m6_target("individual", 0.9)).guards
                          if g.code is GuardCode.NON_HUMAN_TARGET], [])
        self.assertEqual([g for g in self.run_m1("film", signals=fake_m6_target("non_human", 0.9)).guards
                          if g.code is GuardCode.NON_HUMAN_TARGET], [])

    def test_deterministic(self) -> None:
        text = "Amcam aptallar psikoloji"
        self.assertEqual(self.run_m1(text).content, self.run_m1(text).content)


if __name__ == "__main__":
    unittest.main()
