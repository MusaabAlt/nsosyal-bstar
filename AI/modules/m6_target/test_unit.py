"""Unit tests for m6_target. Rules under test are the ones declared in
protocols/m6_target_guideline.md; the PENDING ones are asserted as declared behaviour so a
change is deliberate. Fixed-value assertions only (rule 4's scan)."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import ContentCode, ModuleName, TargetType
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m6_target.module import TargetModule, iban_valid, tckn_valid

FIXTURES = Path(__file__).with_name("fixtures") / "cases.jsonl"
SHARED: dict[str, TargetModule] = {}


def module() -> TargetModule:
    if "m" not in SHARED:
        SHARED["m"] = TargetModule()
        SHARED["m"].load()
    return SHARED["m"]


class TargetModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = module()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m6_target"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m6_target")

    def test_output_stays_within_provides(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))

    def test_never_sets_decision_fields(self) -> None:
        out = self.module.process(Context(text="Sen aptalsın, 05321234567"))
        for score in out.content:
            self.assertIsNone(score.threshold)
            self.assertIsNone(score.fired)
        for guard in out.guards:
            self.assertIsNone(guard.active)

    HOSTILE_INPUTS = ("", " ", "\t\n ", "a" * 5000, "Bu bir test cumlesi", "SIKINTI", "ap​tal", "аptal",
                      "\U0001F468‍\U0001F469", "\x00\x1b", "@", "#", "TR", "0", "1" * 40, "Merhaba مرحبا")

    def test_contract_shape(self) -> None:
        out = self.module.process(Context(text="Sen aptalsın"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertEqual(out.module, self.module.name.value)
        self.assertEqual(out.version, self.module.version)
        self.assertIsInstance(out.latency_ms, float)
        self.assertIsInstance(out.signals, dict)
        self.assertIsInstance(out.notes, list)
        for score in out.content:
            self.assertIsInstance(score, ContentScore)
            self.assertIsNotNone(score.span)
        for guard in out.guards:
            self.assertIsInstance(guard, GuardResult)

    def test_input_not_mutated(self) -> None:
        upstream = {"m0_charsafe": {"offsets": [0, 1, 2]}}
        snapshot = copy.deepcopy(upstream)
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                ctx = Context(text=text, charsafe_text=text.lower(), normalized_text=text, signals=MappingProxyType(upstream))
                self.module.process(ctx)
                self.assertEqual(ctx.text, text)
        self.assertEqual(upstream, snapshot)

    def test_never_raises(self) -> None:
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                out = self.module.process(Context(text=text))
                self.assertIsInstance(out, ModuleOutput)
                self.assertTrue(out.ok, out.notes)


class TargetModuleBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = module()

    def target(self, text: str) -> tuple[ModuleOutput, TargetType]:
        out = self.module.process(Context(text=text))
        self.assertTrue(out.ok, out.notes)
        return out, (out.target.type if out.target is not None else TargetType.NONE)

    # -- taxonomy (spec §3) and the published signals (spec §6) -------------------------------
    def test_non_human_object_resolves_non_human_target(self) -> None:
        for text in ("Bu program berbat", "Otobüs yine gelmedi, rezalet", "Maç sonucu tam bir fiyasko",
                     "Bu film çok sıkıcıydı", "Hava berbat bugün"):
            with self.subTest(text=text):
                out, t = self.target(text)
                self.assertIs(t, TargetType.NON_HUMAN)
                self.assertEqual(out.signals["target_type"], "non_human")
                self.assertEqual(out.signals["target_confidence"], out.target.confidence)
                self.assertEqual(text[out.target.span[0]:out.target.span[1]], out.target.evidence)

    def test_mention_and_second_person_resolve_individual(self) -> None:
        for text, evidence in (("@ahmet sen tam bir aptalsın", "@ahmet"), ("Sen çok aptalsın", "Sen"),
                               ("Sana diyorum aptal", "Sana"), ("Sizler de aynısınız", "Sizler")):
            with self.subTest(text=text):
                out, t = self.target(text)
                self.assertIs(t, TargetType.INDIVIDUAL)
                self.assertEqual(out.target.evidence, evidence)

    def test_second_person_is_an_exact_token_never_a_prefix(self) -> None:
        for text in ("Bu sene çok kötü geçti", "Senaryo berbat", "Sizofren bir program"):
            with self.subTest(text=text):
                out, t = self.target(text)
                self.assertIsNot(t, TargetType.INDIVIDUAL)

    def test_turkish_casing_in_second_person(self) -> None:
        # SİZİN -> sizin flags; SIZIN -> sızın does not (deixis file casing note)
        self.assertIs(self.target("SİZİN suçunuz")[1], TargetType.INDIVIDUAL)
        self.assertIs(self.target("SIZIN suçunuz")[1], TargetType.NONE)

    def test_vocative_and_copula_endings(self) -> None:
        self.assertIs(self.target("Ne yapıyorsun lan")[1], TargetType.INDIVIDUAL)
        out, t = self.target("Gerizekalısın resmen")
        self.assertIs(t, TargetType.INDIVIDUAL)
        self.assertEqual(out.target.evidence, "Gerizekalısın")

    def test_group_stems_with_suffixes(self) -> None:
        for text, stem in (("Türkler hep böyle", "Türkler"), ("Bu kadınlara güvenilmez", "kadınlara"),
                           ("Mültecilerin hepsi", "Mültecilerin"), ("Suriyeliler gitsin", "Suriyeliler")):
            with self.subTest(text=text):
                out, t = self.target(text)
                self.assertIs(t, TargetType.GROUP)
                self.assertEqual(out.target.evidence, stem)

    def test_group_stem_does_not_take_arbitrary_tails(self) -> None:
        self.assertIsNot(self.target("Türkiye güzel ülke")[1], TargetType.GROUP)     # 'iye' is not a suffix

    def test_precedence_individual_over_group_over_non_human(self) -> None:
        self.assertIs(self.target("Sen bu programı beğenmedin mi")[1], TargetType.INDIVIDUAL)
        self.assertIs(self.target("Türkler bu programı sevmez")[1], TargetType.GROUP)

    def test_none_when_nothing_matches(self) -> None:
        out, t = self.target("Bugün pazara gittik")
        self.assertIs(t, TargetType.NONE)
        self.assertIsNone(out.target)
        self.assertEqual(out.signals["target_type"], "none")

    # -- PENDING rules, asserted as declared (guideline §2) -----------------------------------
    def test_declared_pending_rules(self) -> None:
        self.assertIs(self.target("Siz de bilmiyorsunuz")[1], TargetType.INDIVIDUAL)           # siz -> individual
        self.assertIs(self.target("Belediye rezil çalışıyor")[1], TargetType.NON_HUMAN)       # institution noun
        self.assertIs(self.target("Belediyedekiler rezil insanlar")[1], TargetType.NONE)        # members (-deki): unresolved
        self.assertIs(self.target("Müslümanlar hep böyle")[1], TargetType.GROUP)               # followers
        self.assertIs(self.target("İslam saçma")[1], TargetType.NONE)                          # religion itself: unresolved
        self.assertIs(self.target("Fenerliler rezil")[1], TargetType.NONE)                     # supporters: unresolved

    # -- doxing (spec §5, guideline §3) ------------------------------------------------------
    def test_validators(self) -> None:
        self.assertTrue(tckn_valid("10000000146"))
        self.assertFalse(tckn_valid("12345678901"))
        self.assertFalse(tckn_valid("01234567890"))
        self.assertTrue(iban_valid("TR33 0006 1005 1978 6457 8413 26"))
        self.assertFalse(iban_valid("TR33 0006 1005 1978 6457 8413 27"))

    def test_doxing_patterns_fire_with_exact_spans(self) -> None:
        cases = (("Numarası 0532 123 45 67 arayın", "0532 123 45 67"),
                 ("Numarası +90 532 123 45 67", "+90 532 123 45 67"),
                 ("Kimlik no 10000000146 bu adamın", "10000000146"),
                 ("IBAN TR33 0006 1005 1978 6457 8413 26 hesabı", "TR33 0006 1005 1978 6457 8413 26"),
                 ("Profili https://instagram.com/ayse.k burada", "https://instagram.com/ayse.k"),
                 ("Maili ayse@example.com", "ayse@example.com"),
                 ("Plakası 34 ABC 123 olan", "34 ABC 123"))
        for text, surface in cases:
            with self.subTest(text=text):
                out = self.module.process(Context(text=text))
                spans = [text[s.span[0]:s.span[1]] for s in out.content]
                self.assertIn(surface, spans)
                self.assertTrue(all(s.code is ContentCode.B4 for s in out.content))
                self.assertTrue(all(s.source == "m6_target@raw" for s in out.content))

    def test_address_needs_a_personal_cue_and_no_public_cue(self) -> None:
        private = "Ayşe'nin evi Çamlık Mah. Gül Sok. No: 12 Daire 3, oraya gidin"
        out = self.module.process(Context(text=private))
        self.assertEqual([s.code for s in out.content], [ContentCode.B4])
        public = "Mağazamız Çamlık Mah. Gül Sok. No: 12 adresinde açıldı"
        self.assertEqual(self.module.process(Context(text=public)).content, [])
        event = "Konser Çamlık Mah. Gül Sok. No: 12 adresinde yapılacak"
        self.assertEqual(self.module.process(Context(text=event)).content, [])

    def test_near_misses_do_not_fire(self) -> None:
        for text in ("Sipariş numaram 12345678901", "IBAN TR33 0006 1005 1978 6457 8413 27 yanlış",
                     "Saat 05 32 12 34 gibi", "Kargo takip 1234567890123"):
            with self.subTest(text=text):
                self.assertEqual(self.module.process(Context(text=text)).content, [])

    def test_fixtures_have_spans_on_every_b4(self) -> None:
        for item in [json.loads(l) for l in FIXTURES.read_text(encoding="utf-8").splitlines() if l.strip()]:
            if item.get("placeholder"):
                continue
            out = self.module.process(Context(text=item["text"]))
            with self.subTest(id=item["id"]):
                self.assertTrue(out.ok, out.notes)
                for s in out.content:
                    self.assertIsNotNone(s.span)
                    self.assertTrue(item["text"][s.span[0]:s.span[1]])

    def test_deterministic(self) -> None:
        text = "@ahmet sen 0532 123 45 67 numaralı aptalsın"
        a, b = self.module.process(Context(text=text)), self.module.process(Context(text=text))
        self.assertEqual(a.target, b.target)
        self.assertEqual(a.content, b.content)


if __name__ == "__main__":
    unittest.main()
