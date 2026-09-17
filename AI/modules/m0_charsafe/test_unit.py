"""Unit tests for m0_charsafe (reference module)."""
from __future__ import annotations

import copy
import unittest
from types import MappingProxyType

from contracts.codes import FormCode, ModuleName
from contracts.module_api import Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m0_charsafe.module import (CONF_CASING_INNER, CONF_CASING_ORDINARY, CONF_COMBINING_STUFFING,
                                        CONF_STYLED_LATIN, CONF_HOMOGLYPH_ALL_LOOKALIKE,
                                        CONF_HOMOGLYPH_MIXED_SCRIPT, CONF_INVISIBLE_BOUNDARY,
                                        CONF_INVISIBLE_INSIDE_WORD, CONF_INVISIBLE_LEADING_BOM,
                                        CharSafeModule)

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
        offsets = out.signals["_offsets"]
        self.assertEqual(len(offsets), len(out.charsafe_text))
        self.assertEqual(sorted(offsets), offsets)
        self.assertNotIn(2, offsets)  # the ZWSP position has no output char

    # -- edge inputs ------------------------------------------------------------
    def test_empty_string(self) -> None:
        out = self.run_m0("")
        self.assertEqual(out.charsafe_text, "")
        self.assertEqual(out.form.patterns, [])
        self.assertEqual(out.signals["_offsets"], [])

    def test_whitespace_only(self) -> None:
        out = self.run_m0(" \t\n ")
        self.assertEqual(out.charsafe_text, " \t\n ")
        self.assertEqual(out.form.patterns, [])

    def test_5000_characters(self) -> None:
        text = ("Bu bir test cumlesi " * 250)[:5000]
        out = self.run_m0(text)
        self.assertEqual(len(text), 5000)
        self.assertEqual(out.charsafe_text, text.lower())
        self.assertEqual(len(out.signals["_offsets"]), 5000)
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
        self.assertEqual(pattern.confidence, CONF_INVISIBLE_INSIDE_WORD)

    def test_soft_hyphen_is_cf_and_stripped(self) -> None:
        out = self.run_m0("ap" + SOFT_HYPHEN + "tal")
        self.assertEqual(out.charsafe_text, "aptal")
        self.assertEqual(self.codes(out), [FormCode.ZERO_WIDTH])

    def test_leading_bom_is_low_confidence(self) -> None:
        out = self.run_m0(BOM + "Merhaba")
        self.assertEqual(out.charsafe_text, "merhaba")
        self.assertEqual(out.form.patterns[0].confidence, CONF_INVISIBLE_LEADING_BOM)

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
        self.assertEqual(pattern.confidence, CONF_CASING_ORDINARY)

    def test_dotted_capital_i(self) -> None:
        self.assertEqual(self.run_m0("İSTANBUL").charsafe_text, "istanbul")

    def test_spec_casing_words_in_mixed_casing(self) -> None:
        # spec §7: SIKINTI, IŞIK, İSTANBUL in mixed casing; ASCII "I" is always dotless, never guessed.
        for text, expected in (("IŞIK", "ışık"), ("Işık", "ışık"), ("ışık", "ışık"), ("İSTANBUL", "istanbul"),
                               ("İstanbul", "istanbul"), ("istanbul", "istanbul"), ("Istanbul", "ıstanbul"),
                               ("SIKINTI", "sıkıntı"), ("Sıkıntı", "sıkıntı")):
            with self.subTest(text=text):
                self.assertEqual(self.run_m0(text).charsafe_text, expected)

    def test_decomposed_dotted_i(self) -> None:
        out = self.run_m0("I" + COMBINING_DOT + "yi")
        self.assertEqual(out.charsafe_text, "iyi")
        self.assertEqual(out.signals["_offsets"], [0, 2, 3])

    def test_inner_capital_i_is_high_confidence(self) -> None:
        out = self.run_m0("sIkIntI")
        self.assertEqual(out.charsafe_text, "sıkıntı")
        self.assertEqual(out.form.patterns[0].confidence, CONF_CASING_INNER)

    def test_evidence_strength_ordering(self) -> None:
        # Relative strength is the module's claim; where the cut-off sits is
        # decided in decision/thresholds.yaml, not here.
        self.assertLess(CONF_INVISIBLE_LEADING_BOM, CONF_INVISIBLE_BOUNDARY)
        self.assertLess(CONF_INVISIBLE_BOUNDARY, CONF_INVISIBLE_INSIDE_WORD)
        self.assertLess(CONF_HOMOGLYPH_ALL_LOOKALIKE, CONF_HOMOGLYPH_MIXED_SCRIPT)
        self.assertLess(CONF_CASING_ORDINARY, CONF_CASING_INNER)

    # -- gaps: fullwidth, combining marks, invisible fillers ----------------------
    def test_fullwidth_letters_are_mapped(self) -> None:
        text = "".join(chr(0xFF41 + ord(c) - ord("a")) for c in "aptal")
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, "aptal")
        [pattern] = out.form.patterns
        self.assertIs(pattern.code, FormCode.HOMOGLYPH)
        self.assertEqual(pattern.confidence, CONF_STYLED_LATIN)
        self.assertEqual(pattern.span, (0, 5))

    def test_fullwidth_capital_i_follows_turkish_casing(self) -> None:
        out = self.run_m0(chr(0xFF33) + chr(0xFF29) + "KINTI")
        self.assertEqual(out.charsafe_text, "sıkıntı")
        self.assertIn(FormCode.DOTLESS_I, self.codes(out))

    def test_mathematical_circled_and_small_capital_letters_are_mapped(self) -> None:
        cases = {
            "mathematical bold": "".join(chr(0x1D41A + ord(c) - ord("a")) for c in "aptal"),
            "mathematical italic capital": "".join(chr(0x1D434 + ord(c) - ord("A")) for c in "APTAL"),
            "circled": "".join(chr(0x24D0 + ord(c) - ord("a")) for c in "aptal"),
            "small capitals": "".join(chr(cp) for cp in (0x1D00, 0x1D18, 0x1D1B, 0x1D00, 0x029F)),
        }
        for style, text in cases.items():
            with self.subTest(style=style):
                out = self.run_m0(text)
                self.assertEqual(out.charsafe_text, "aptal")
                self.assertEqual(self.codes(out), [FormCode.HOMOGLYPH])
                self.assertEqual(out.form.patterns[0].confidence, CONF_STYLED_LATIN)

    def test_small_capital_i_follows_turkish_casing(self) -> None:
        out = self.run_m0("s" + chr(0x026A) + "k" + chr(0x026A) + "nt" + chr(0x026A))
        self.assertEqual(out.charsafe_text, "sıkıntı")

    # -- styled Latin: enclosed, superscript, regional indicators --------------------
    @staticmethod
    def shifted(word: str, first_code_point: int, first_letter: str = "A") -> str:
        return "".join(chr(first_code_point + ord(c) - ord(first_letter)) for c in word)

    def test_enclosed_and_superscript_letters_are_mapped(self) -> None:
        cases = {
            "negative circled": self.shifted("APTAL", 0x1F150),
            "negative squared": self.shifted("APTAL", 0x1F170),
            "squared": self.shifted("APTAL", 0x1F130),
            "parenthesized small": self.shifted("aptal", 0x249C, "a"),
            "parenthesized capital": self.shifted("APTAL", 0x1F110),
            "superscript": "".join(chr(cp) for cp in (0x1D43, 0x1D56, 0x1D57, 0x1D43, 0x02E1)),
            "regional indicator": self.shifted("APTAL", 0x1F1E6),
        }
        for style, text in cases.items():
            with self.subTest(style=style):
                out = self.run_m0(text)
                self.assertEqual(out.charsafe_text, "aptal")
                self.assertEqual(self.codes(out), [FormCode.HOMOGLYPH])
                self.assertEqual(out.form.patterns[0].confidence, CONF_STYLED_LATIN)
                self.assertEqual(out.form.patterns[0].span, (0, len(text)))
                self.assertEqual(out.signals["homoglyphs_mapped"], 5)

    def test_enclosed_capital_i_follows_turkish_casing(self) -> None:
        for first in (0x1F150, 0x1F170, 0x1F110, 0x1F1E6):
            with self.subTest(block=hex(first)):
                out = self.run_m0(self.shifted("SIKINTI", first))
                self.assertEqual(out.charsafe_text, "sıkıntı")
                self.assertIn(FormCode.DOTLESS_I, self.codes(out))

    def test_superscript_digits_are_left_alone(self) -> None:
        # Folding "m²" is normalization, not safety (docstring "does NOT").
        text = "Oda 12 m\u00b2, hacim 10\u00b3 litre"
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, text.lower())
        self.assertEqual(out.form.patterns, [])

    def test_flags_are_not_mapped(self) -> None:
        for text in (self.shifted("TR", 0x1F1E6),
                     "T\u00fcrkiye" + self.shifted("TR", 0x1F1E6) + "!",
                     self.shifted("TRTRTR", 0x1F1E6),
                     "Ma\u00e7 " + self.shifted("TR", 0x1F1E6) + self.shifted("DE", 0x1F1E6)):
            with self.subTest(text=text):
                out = self.run_m0(text)
                self.assertEqual(out.charsafe_text, text.lower())
                self.assertNotIn(FormCode.HOMOGLYPH, self.codes(out))

    def test_regional_indicators_that_are_not_flags_are_mapped(self) -> None:
        flag = self.shifted("TR", 0x1F1E6)
        out = self.run_m0(flag + " " + self.shifted("SIK", 0x1F1E6))  # odd run: never a row of flags
        self.assertEqual(out.charsafe_text, flag + " s\u0131k")
        [homoglyph] = [p for p in out.form.patterns if p.code is FormCode.HOMOGLYPH]
        self.assertEqual(homoglyph.span, (3, 6))
        # Even length but not valid region pairs ("AP" is not a region).
        self.assertEqual(self.run_m0(self.shifted("APTA", 0x1F1E6)).charsafe_text, "apta")

    def test_word_spelled_only_from_valid_flag_pairs_passes(self) -> None:
        # Known, documented gap: indistinguishable from a row of flags.
        text = self.shifted("SIKE", 0x1F1E6)  # SI + KE are both regions
        self.assertEqual(self.run_m0(text).charsafe_text, text)

    def test_mathematical_greek_is_not_mapped_to_latin(self) -> None:
        text = chr(0x1D6C2)  # MATHEMATICAL BOLD SMALL ALPHA
        self.assertEqual(self.run_m0(text).charsafe_text, text)

    def test_accents_are_not_normalised_by_m0(self) -> None:
        # Accent normalisation belongs to m2 (spec.md §2).
        self.assertEqual(self.run_m0("\u00e1ptal").charsafe_text, "\u00e1ptal")

    def test_offsets_are_internal_and_summarised(self) -> None:
        out = self.run_m0("ap\u200btal")
        self.assertEqual(out.signals["_offsets"], [0, 1, 3, 4, 5])
        self.assertFalse(out.signals["offsets_identity"])
        self.assertTrue(self.run_m0("bu bir test").signals["offsets_identity"])

    def test_fullwidth_punctuation_is_left_alone(self) -> None:
        text = "\u4f60\u597d\uff01"
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, text)
        self.assertEqual(out.form.patterns, [])

    def test_combining_mark_stuffing_is_stripped(self) -> None:
        text = "".join(c + "\u0336" for c in "aptal")
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, "aptal")
        [pattern] = out.form.patterns
        self.assertIs(pattern.code, FormCode.ZERO_WIDTH)
        self.assertEqual(pattern.confidence, CONF_COMBINING_STUFFING)
        self.assertEqual(out.signals["_offsets"], [0, 2, 4, 6, 8])

    def test_decomposed_turkish_letter_is_composed_not_stripped(self) -> None:
        out = self.run_m0("s\u0327ahane")
        self.assertEqual(out.charsafe_text, "şahane")
        self.assertLess(out.form.patterns[0].confidence, CONF_COMBINING_STUFFING)

    def test_combining_marks_of_other_scripts_are_kept(self) -> None:
        text = "\u0645\u064e\u0631\u062d\u064e\u0628\u064b\u0627"
        out = self.run_m0(text)
        self.assertEqual(out.charsafe_text, text)
        self.assertEqual(out.form.patterns, [])

    def test_emoji_presentation_marks_are_kept(self) -> None:
        for text in ("\u2764\ufe0f", "1\ufe0f\u20e3"):
            with self.subTest(text=text):
                out = self.run_m0(text)
                self.assertEqual(out.charsafe_text, text)
                self.assertEqual(out.form.patterns, [])

    def test_invisible_filler_letters_are_stripped(self) -> None:
        for filler in ("\u3164", "\u115f", "\u1160", "\uffa0", "\u2800"):
            with self.subTest(filler=hex(ord(filler))):
                out = self.run_m0("ap" + filler + "tal")
                self.assertEqual(out.charsafe_text, "aptal")
                self.assertEqual(self.codes(out), [FormCode.ZERO_WIDTH])
                self.assertEqual(out.form.patterns[0].confidence, CONF_INVISIBLE_INSIDE_WORD)

    def test_charsafe_changed_signal(self) -> None:
        self.assertFalse(self.run_m0("bu bir test").signals["charsafe_changed"])
        self.assertTrue(self.run_m0("ap\u200btal").signals["charsafe_changed"])

    def test_ascii_i_is_not_guessed_as_dotted(self) -> None:
        # DEASCII is m2's interpretation, not m0's.
        self.assertEqual(self.run_m0("Istanbul").charsafe_text, "ıstanbul")


if __name__ == "__main__":
    unittest.main()
