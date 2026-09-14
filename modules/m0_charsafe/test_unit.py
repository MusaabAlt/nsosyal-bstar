"""Unit tests for m0_charsafe (reference module)."""
from __future__ import annotations

import copy
import unittest
from types import MappingProxyType

from contracts.codes import FormCode, ModuleName
from contracts.module_api import Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m0_charsafe.module import CharSafeModule

ZWSP = "\u200b"
ZWJ = "\u200d"
SOFT_HYPHEN = "\u00ad"
BOM = "\ufeff"
CYRILLIC_A = "\u0430"
CYRILLIC_O = "\u043e"
COMBINING_DOT = "\u0307"
MAN, WOMAN = "\U0001F468", "\U0001F469"


class CharSafeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = CharSafeModule()

    def run_m0(self, text: str):
        out = self.module.process(Context(text=text))
        self.assertTrue(out.ok, out.notes)
        return out

    def codes(self, out) -> list[FormCode]:
        return [p.code for p in out.form.patterns]

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

    # -- contract -------------------------------------------------------------
    def test_contract(self) -> None:
        out = self.run_m0("Bu bir test cumlesi")
        self.assertEqual(out.module, ModuleName.M0_CHARSAFE.value)
        self.assertEqual(out.charsafe_text, "bu bir test cumlesi")
        self.assertEqual(out.form.patterns, [])
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))
        self.assertEqual(out.content, [])

    def test_original_text_untouched_and_offsets_align(self) -> None:
        text = "Ap" + ZWSP + "tal " + CYRILLIC_A + "b SIKINTI"
        ctx = Context(text=text)
        out = self.module.process(ctx)
        self.assertEqual(ctx.text, text)
        offsets = out.signals["offsets"]
        self.assertEqual(len(offsets), len(out.charsafe_text))
        self.assertEqual(sorted(offsets), offsets)
        self.assertNotIn(2, offsets)  # the ZWSP position has no output char

    # -- edge inputs ------------------------------------------------------------
    def test_empty_string(self) -> None:
        out = self.run_m0("")
        self.assertEqual(out.charsafe_text, "")
        self.assertEqual(out.form.patterns, [])
        self.assertEqual(out.signals["offsets"], [])

    def test_whitespace_only(self) -> None:
        out = self.run_m0(" \t\n ")
        self.assertEqual(out.charsafe_text, " \t\n ")
        self.assertEqual(out.form.patterns, [])

    def test_5000_characters(self) -> None:
        text = ("Bu bir test cumlesi " * 250)[:5000]
        out = self.run_m0(text)
        self.assertEqual(len(text), 5000)
        self.assertEqual(out.charsafe_text, text.lower())
        self.assertEqual(len(out.signals["offsets"]), 5000)
        self.assertEqual(out.form.patterns, [])

    def test_sikinti_never_yields_profane_root(self) -> None:
        # Criterion (spec.md): every uppercase I maps to ı. Inputs typed with a
        # lowercase dotted i are out of scope; m0 does not guess.
        for text in ("SIKINTI", "Sıkıntı", "SıKıNTı", "sIkIntI", "SIKıNTI", "SIKINTI YOK",
                     "BÜYÜK SIKINTI", "sıkıntı", "SIKINTILAR", "SIKINTIDAN"):
            with self.subTest(text=text):
                out = self.run_m0(text)
                self.assertNotIn("sik", out.charsafe_text)
                self.assertIn("sık", out.charsafe_text)

    # -- invisible characters ---------------------------------------------------
    def test_zero_width_inside_word_is_stripped_with_high_confidence(self) -> None:
        out = self.run_m0("ap" + ZWSP + ZWSP + "tal")
        self.assertEqual(out.charsafe_text, "aptal")
        [pattern] = out.form.patterns
        self.assertIs(pattern.code, FormCode.ZERO_WIDTH)
        self.assertEqual(pattern.span, (2, 4))
        self.assertIn("inside word", pattern.evidence)
        self.assertIn("U+200B", pattern.evidence)
        self.assertGreater(pattern.confidence, 0.9)

    def test_soft_hyphen_is_cf_and_stripped(self) -> None:
        out = self.run_m0("ap" + SOFT_HYPHEN + "tal")
        self.assertEqual(out.charsafe_text, "aptal")
        self.assertEqual(self.codes(out), [FormCode.ZERO_WIDTH])

    def test_leading_bom_is_low_confidence(self) -> None:
        out = self.run_m0(BOM + "Merhaba")
        self.assertEqual(out.charsafe_text, "merhaba")
        self.assertLess(out.form.patterns[0].confidence, 0.1)

    def test_layout_controls_are_preserved(self) -> None:
        out = self.run_m0("kerpic\nsikke\tamca")
        self.assertEqual(out.charsafe_text, "kerpic\nsikke\tamca")
        self.assertEqual(out.form.patterns, [])

    def test_other_control_bytes_are_stripped(self) -> None:
        out = self.run_m0("ap\x00tal")
        self.assertEqual(out.charsafe_text, "aptal")
        self.assertEqual(self.codes(out), [FormCode.ZERO_WIDTH])

    def test_emoji_zwj_sequence_is_kept_and_not_reported(self) -> None:
        text = MAN + ZWJ + WOMAN
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, text)
        self.assertEqual(out.form.patterns, [])

    # -- homoglyphs -------------------------------------------------------------
    def test_mixed_script_token_is_mapped(self) -> None:
        out = self.run_m0(CYRILLIC_A + "ptal")
        self.assertEqual(out.charsafe_text, "aptal")
        [pattern] = out.form.patterns
        self.assertIs(pattern.code, FormCode.HOMOGLYPH)
        self.assertEqual(pattern.span, (0, 5))
        self.assertEqual(out.signals["homoglyphs_mapped"], 1)

    def test_genuine_foreign_word_is_not_mapped(self) -> None:
        out = self.run_m0("мир")  # "мир": no Latin twin for м, и
        self.assertEqual(out.charsafe_text, "мир")
        self.assertEqual(out.form.patterns, [])

    def test_token_made_only_of_lookalikes_is_mapped(self) -> None:
        out = self.run_m0(CYRILLIC_O + CYRILLIC_A)
        self.assertEqual(out.charsafe_text, "oa")
        self.assertIs(out.form.patterns[0].code, FormCode.HOMOGLYPH)

    def test_turkish_letters_are_never_confusables(self) -> None:
        text = "çğıöşü " + CYRILLIC_A
        out = self.run_m0(text)
        self.assertTrue(out.charsafe_text.startswith("çğıöşü"))

    # -- Turkish casing ---------------------------------------------------------
    def test_sikinti_casing_trap(self) -> None:
        out = self.run_m0("SIKINTI")
        self.assertEqual(out.charsafe_text, "sıkıntı")
        [pattern] = out.form.patterns
        self.assertIs(pattern.code, FormCode.DOTLESS_I)
        self.assertLess(pattern.confidence, 0.5)

    def test_dotted_capital_i(self) -> None:
        self.assertEqual(self.run_m0("İSTANBUL").charsafe_text, "istanbul")

    def test_decomposed_dotted_i(self) -> None:
        out = self.run_m0("I" + COMBINING_DOT + "yi")
        self.assertEqual(out.charsafe_text, "iyi")
        self.assertEqual(out.signals["offsets"], [0, 2, 3])

    def test_inner_capital_i_is_high_confidence(self) -> None:
        out = self.run_m0("sIkIntI")
        self.assertEqual(out.charsafe_text, "sıkıntı")
        self.assertGreater(out.form.patterns[0].confidence, 0.5)

    def test_ascii_i_is_not_guessed_as_dotted(self) -> None:
        # DEASCII is m2's interpretation, not m0's.
        self.assertEqual(self.run_m0("Istanbul").charsafe_text, "ıstanbul")


if __name__ == "__main__":
    unittest.main()
