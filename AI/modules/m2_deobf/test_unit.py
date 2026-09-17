"""Unit tests for m2_deobf. Upstream (m0) is faked with fixed values: rule 2 forbids importing
another module. Fixed-value assertions only (rule 4's scan rejects numeric comparisons here)."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import FormCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m2_deobf.module import AMBIGUOUS_DEASCII, DeobfModule

FIXTURES = Path(__file__).with_name("fixtures") / "cases.jsonl"


def tr_lower(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower()


def fake_m0(text: str, charsafe_text: str | None = None, offsets: list[int] | None = None) -> Context:
    """Stands in for m0 with fixed values (docs/team/MOHAMMED.md). No other module is imported."""
    charsafe = tr_lower(text) if charsafe_text is None else charsafe_text
    signals = {}
    if offsets is not None:
        signals["m0_charsafe"] = MappingProxyType({"_offsets": tuple(offsets)})
    elif len(charsafe) == len(text):
        signals["m0_charsafe"] = MappingProxyType({"_offsets": tuple(range(len(text)))})
    return Context(text=text, charsafe_text=charsafe, signals=MappingProxyType(signals))


SHARED: dict[str, DeobfModule] = {}


def module() -> DeobfModule:
    """One loaded module for the file: tier 2's analyser takes seconds to construct."""
    if "m" not in SHARED:
        SHARED["m"] = DeobfModule()
        SHARED["m"].load()
    return SHARED["m"]


class DeobfModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = module()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m2_deobf"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m2_deobf")

    def test_output_stays_within_provides(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))

    def test_never_sets_decision_fields(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertEqual(out.form.active, [])
        self.assertEqual(out.content, [])
        self.assertEqual(out.guards, [])

    HOSTILE_INPUTS = ("", " ", "\t\n ", "a" * 5000, "Bu bir test cumlesi", "SIKINTI",
                      "ap​tal", "аptal", "\U0001F468‍\U0001F469", "\x00\x1b", "...!!!???",
                      "Merhaba مرحبا dünya", "s a l a k s a l a k " * 200)

    def test_contract_shape(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertEqual(out.module, self.module.name.value)
        self.assertEqual(out.version, self.module.version)
        self.assertIsInstance(out.latency_ms, float)
        self.assertIsInstance(out.signals, dict)
        self.assertIsInstance(out.notes, list)
        self.assertIsInstance(out.normalized_text, str)
        for score in out.content:
            self.assertIsInstance(score, ContentScore)
        for guard in out.guards:
            self.assertIsInstance(guard, GuardResult)

    def test_input_not_mutated(self) -> None:
        upstream = {"m0_charsafe": {"_offsets": [0, 1, 2], "invisible_removed": 0}}
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


class DeobfModuleBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = module()

    def run_m2(self, text: str, **kwargs) -> ModuleOutput:
        out = self.module.process(fake_m0(text, **kwargs))
        self.assertTrue(out.ok, out.notes)
        return out

    def codes(self, out: ModuleOutput) -> list[str]:
        return [p.code.value for p in out.form.patterns]

    # -- spec §11: raw text provably untouched -----------------------------------------------
    def test_raw_channel_never_replaced(self) -> None:
        text = "Sen tam bir s4l4k adamsın"
        ctx = fake_m0(text)
        out = self.module.process(ctx)
        self.assertEqual(ctx.text, text)
        self.assertEqual(out.charsafe_text, None)
        self.assertEqual(out.normalized_text, "sen tam bir salak adamsın")
        self.assertNotEqual(out.normalized_text, ctx.text)

    def test_legit_double_letters_survive(self) -> None:
        for text in ("annem elli yaşında", "hakkında bilgi", "millet sokakta"):
            with self.subTest(text=text):
                out = self.run_m2(text)
                self.assertEqual(out.normalized_text, text)
                self.assertEqual(out.form.patterns, [])

    # -- tier 1 patterns ----------------------------------------------------------------------
    def test_leet(self) -> None:
        out = self.run_m2("Bu adam tam bir 5al4k")
        self.assertEqual(out.normalized_text, "bu adam tam bir salak")
        self.assertEqual(self.codes(out), ["LEET"])
        self.assertEqual(out.form.patterns[0].evidence, "5al4k")

    def test_repeat(self) -> None:
        out = self.run_m2("saaalaaak herif")
        self.assertEqual(out.normalized_text, "salak herif")
        self.assertEqual(self.codes(out), ["REPEAT"])

    def test_spaced(self) -> None:
        text = "sen s a l a k mısın"
        out = self.run_m2(text)
        self.assertEqual(out.normalized_text, "sen salak mısın")
        self.assertEqual(self.codes(out), ["SPACED"])
        self.assertEqual(out.form.patterns[0].evidence, "s a l a k")
        self.assertEqual(text[out.form.patterns[0].span[0]:out.form.patterns[0].span[1]], "s a l a k")

    def test_punct_split_but_never_star(self) -> None:
        out = self.run_m2("s.a.l.a.k adam")
        self.assertEqual(out.normalized_text, "salak adam")
        self.assertEqual(self.codes(out), ["PUNCT_SPLIT"])
        masked = self.run_m2("s*a*l*a*k adam")
        self.assertNotIn("PUNCT_SPLIT", self.codes(masked))

    def test_accent_reported_as_homoglyph_from_m2(self) -> None:
        out = self.run_m2("sen áptal mısın")
        self.assertEqual(out.normalized_text, "sen aptal mısın")
        self.assertEqual(self.codes(out), ["HOMOGLYPH"])
        self.assertEqual(out.form.patterns[0].source, "m2_deobf")

    def test_turkish_circumflex_is_not_an_accent(self) -> None:
        out = self.run_m2("kâr ve zarar")
        self.assertEqual(out.normalized_text, "kâr ve zarar")
        self.assertEqual(out.form.patterns, [])

    def test_phonetic(self) -> None:
        out = self.run_m2("siqtir git")
        self.assertEqual(out.normalized_text, "siktir git")
        self.assertEqual(self.codes(out), ["PHONETIC"])
        out2 = self.run_m2("gerexiz yorum")
        self.assertEqual(out2.normalized_text, "gereksiz yorum")

    # -- tier 2 --------------------------------------------------------------------------------
    def test_deascii_restores_an_unambiguous_word(self) -> None:
        if not self.module.tier2_enabled:
            self.fail("PRECONDITION: tier 2 (zeyrek) unavailable; install modules/m2_deobf/requirements.txt")
        out = self.run_m2("ne kadar serefsiz bir davranış")
        self.assertEqual(out.normalized_text, "ne kadar şerefsiz bir davranış")
        self.assertEqual(self.codes(out), ["DEASCII"])

    def test_declared_ambiguities_are_never_resolved(self) -> None:
        for word in sorted(AMBIGUOUS_DEASCII):
            with self.subTest(word=word):
                out = self.run_m2(f"bu {word} bir şey")
                self.assertEqual(out.normalized_text, f"bu {word} bir şey")
                self.assertNotIn("DEASCII", self.codes(out))

    def test_masked_letter_is_reported_not_altered(self) -> None:
        out = self.run_m2("s*ktirtmişler adamı")
        self.assertEqual(out.normalized_text, "s*ktirtmişler adamı")
        self.assertEqual(self.codes(out), ["SUFFIX_ON_MASKED"])

    # -- protection pass (spec §5, §9) --------------------------------------------------------
    def test_protected_tokens_pass_through_unchanged(self) -> None:
        for text in ("3M ürünü aldım", "Turkcell'in kampanyası", "@kullanici selam", "#TeknoFest2026 başladı",
                     "https://example.com/a1b2 linki", "Ayşe'yi gördüm", "COVID-19 aşısı", "Ar-Ge birimi",
                     "0532 123 45 67 numaram", "TR33 0006 1005 1978 6457 8413 26"):
            with self.subTest(text=text):
                out = self.run_m2(text)
                self.assertEqual(out.normalized_text, tr_lower(text))
                self.assertEqual(out.form.patterns, [])

    # -- spans, offsets, idempotency (spec §9, ADR-008) --------------------------------------
    def test_every_pattern_points_at_its_evidence(self) -> None:
        for item in self.fixture_items():
            ctx = Context(text=item["text"], charsafe_text=item["context"]["charsafe_text"],
                          signals=MappingProxyType({"m0_charsafe": MappingProxyType(
                              {"_offsets": tuple(range(len(item["text"])))})}))
            out = self.module.process(ctx)
            with self.subTest(id=item["id"]):
                self.assertTrue(out.ok, out.notes)
                for p in out.form.patterns:
                    self.assertIsNotNone(p.span)
                    self.assertEqual(item["text"][p.span[0]:p.span[1]], p.evidence)

    def test_idempotent_on_every_fixture(self) -> None:
        """f(f(x)) == f(x) (spec §9). SUFFIX_ON_MASKED is an observation of unchanged text, not a
        transformation, so it may be reported again; no transforming pattern may fire twice."""
        for item in self.fixture_items():
            once = self.run_m2(item["text"], charsafe_text=item["context"]["charsafe_text"])
            twice = self.run_m2(once.normalized_text, charsafe_text=once.normalized_text)
            with self.subTest(id=item["id"]):
                self.assertEqual(twice.normalized_text, once.normalized_text)
                self.assertEqual([p.code for p in twice.form.patterns if p.code is not FormCode.SUFFIX_ON_MASKED], [])

    def test_offsets_map_every_normalized_character_to_the_original(self) -> None:
        text = "Sen s a l a k ve 5al4k ve saaalak"
        out = self.run_m2(text)
        offsets = out.signals["_offsets"]
        self.assertEqual(len(offsets), len(out.normalized_text))
        self.assertEqual(offsets, sorted(offsets))
        self.assertTrue(all(isinstance(o, int) for o in offsets))
        self.assertEqual(out.signals["offsets_identity"], False)
        # the first letter of each repaired token still points at its original position
        self.assertEqual(text[offsets[out.normalized_text.index("salak")]], "s")

    def test_spans_go_through_m0_offsets(self) -> None:
        text = "ap​tal 5al4k"           # m0 removed the zero-width space: charsafe is one shorter
        charsafe = "aptal 5al4k"
        offsets = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        out = self.run_m2(text, charsafe_text=charsafe, offsets=offsets)
        self.assertEqual(out.normalized_text, "aptal salak")
        leet = [p for p in out.form.patterns if p.code is FormCode.LEET][0]
        self.assertEqual(text[leet.span[0]:leet.span[1]], "5al4k")

    def test_no_map_means_no_span_but_still_a_channel(self) -> None:
        out = self.module.process(Context(text="XX ap​tal 5al4k", charsafe_text="aptal 5al4k"))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.normalized_text, "aptal salak")
        self.assertNotIn("_offsets", out.signals)
        self.assertTrue(all(p.span is None for p in out.form.patterns))
        self.assertTrue(any("no offset map" in n for n in out.notes))

    def test_repairs_signal_lists_before_and_after(self) -> None:
        out = self.run_m2("Bu adam tam bir 5al4k")
        self.assertEqual(out.signals["_repairs"], [{"code": "LEET", "span": [16, 21], "before": "5al4k", "after": "salak"}])
        self.assertEqual(out.signals["_repair_counts"], {"LEET": 1})
        self.assertEqual(out.signals["codes"], ["LEET"])

    def test_long_post_is_repaired_consistently_under_the_latency_guard(self) -> None:
        # The guard counts analyser calls, not tokens: a repeated surface is cached, so every copy is repaired.
        out = self.run_m2("Bu bir test cumlesi " * 50)
        self.assertEqual(out.signals["_repair_counts"], {"DEASCII": 50})
        self.assertNotIn("cumlesi", out.normalized_text)

    def test_public_signals_are_fixed_size(self) -> None:
        # decision #21: only "_"-prefixed keys may scale with the post.
        short = self.run_m2("Bu bir test cumlesi").signals
        long = self.run_m2("Bu bir test cumlesi " * 200).signals
        public = lambda s: {k: v for k, v in s.items() if not k.startswith("_")}
        self.assertEqual(public(short), public(long))

    def test_edge_inputs(self) -> None:
        for text, expected in (("", ""), (" ", " "), ("...!!!???", "...!!!???"), ("Merhaba مرحبا dünya", "merhaba مرحبا dünya")):
            with self.subTest(text=text):
                out = self.run_m2(text)
                self.assertEqual(out.normalized_text, expected)
                self.assertEqual(out.form.patterns, [])

    def test_deterministic(self) -> None:
        text = "sen s a l a k ve serefsiz ve 5al4k"
        a, b = self.run_m2(text), self.run_m2(text)
        self.assertEqual(a.normalized_text, b.normalized_text)
        self.assertEqual(a.form.patterns, b.form.patterns)

    @staticmethod
    def fixture_items() -> list[dict]:
        items = [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [i for i in items if not i.get("placeholder")]


if __name__ == "__main__":
    unittest.main()
