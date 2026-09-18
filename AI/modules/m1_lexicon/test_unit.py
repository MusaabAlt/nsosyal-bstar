"""Unit tests for m1_lexicon: contract tests and behaviour tests (spec.md §3, §7, §8)."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import ContentCode, GuardCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m1_lexicon.module import (COMPOUND_ROOTS, EXCLUDED_ROOTS, ROUTE_A, ROUTE_B1, ROUTE_B2, ROUTE_B3,
                                        ROUTE_CLASSES, ROUTE_NONE, ROUTE_OF, LexiconModule)


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
        # M1-ROUTE-1: an ordinary insult routes to B1, an explicit profane root to the A1 carrier.
        for text, word, code in (("Onlar aptallar", "aptallar", ContentCode.B1),
                                 ("Sen bir gerizekalısın", "gerizekalısın", ContentCode.B1),
                                 ("siktiler", "siktiler", ContentCode.A1)):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual([s.code for s in out.content], [code])
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
        self.assertEqual([s.code for s in self.run_m1("APTALLAR").content], [ContentCode.B1])

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

    def test_normalized_channel_spans_map_through_m2_offsets(self) -> None:
        # ADR-008: m2 publishes the original index of every normalized character (fixed values here;
        # modules.m2_deobf is never imported). The raw surface "xxxxx" (5 chars at 4..9) stands for a
        # repaired token; the normalized channel reads "salak" and the span lands on the original.
        text = "sen xxxxx mısın"
        normalized = "sen salak mısın"
        signals = MappingProxyType({"m2_deobf": MappingProxyType({"_offsets": tuple(range(len(text)))})})
        out = self.run_m1(text, charsafe_text=text, normalized_text=normalized, signals=signals)
        self.assertEqual([(s.source, s.span) for s in out.content], [("m1_lexicon@normalized", (4, 9))])
        self.assertEqual(text[4:9], "xxxxx")
        self.assertEqual((out.signals["lexicon_hit_raw"], out.signals["lexicon_hit_norm"]), (False, True))
        self.assertEqual(out.notes, [])                                   # no flag-only fallback needed
        # a length-changing repair: "s a l a k" (9 chars) became "salak" (5 chars)
        text2 = "sen s a l a k mısın"
        m2_offsets = [0, 1, 2, 3, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18]
        signals2 = MappingProxyType({"m2_deobf": MappingProxyType({"_offsets": tuple(m2_offsets)})})
        out2 = self.run_m1(text2, charsafe_text=text2, normalized_text=normalized, signals=signals2)
        normalized_hits = [s.span for s in out2.content if s.source == "m1_lexicon@normalized"]
        self.assertEqual(normalized_hits, [(4, 13)])
        self.assertEqual(text2[4:13], "s a l a k")

    def test_match_span_is_the_matched_word_not_the_next_one(self) -> None:
        # terlik reads "salak mısın" as one match (root + separator + a suffix-shaped word); spec §8
        # wants the matched word, so the span stops at "salak".
        out = self.run_m1("salak mısın")
        self.assertEqual([("salak"[:0] + "salak mısın"[s.span[0]:s.span[1]]) for s in out.content], ["salak"])
        spaced = self.run_m1("s a l a k")
        self.assertEqual([("s a l a k"[s.span[0]:s.span[1]]) for s in spaced.content], ["s a l a k"])   # no nested "a k"

    def test_dual_register_words_never_auto_fire(self) -> None:
        # spec §7: moruk, lan, oğlum are a documented annotation-inconsistency source; the lexicon must not fire.
        for text in ("moruk ne haber", "lan gel buraya", "oğlum bak şuraya"):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual(out.content, [])
                self.assertFalse(out.signals["lexicon_hit"])

    def test_collision_evidence_does_not_depend_on_the_hash_seed(self) -> None:
        """Roots found inside one collision word are listed longest first, then alphabetically. They
        used to follow set iteration order, i.e. PYTHONHASHSEED: under seeds 2 and 3 "hocam" read
        "oc/am", under seed 0 "am/oc", so the derived label files differed byte-wise between runs.
        Each seed runs in its own interpreter, because the seed is fixed at interpreter start."""
        text = "Tamamdır hocam"
        expected = ["raw: am in tamamdır", "raw: am/oc in hocam"]
        self.assertEqual([g.evidence for g in self.run_m1(text).guards], expected)
        script = ("import json, sys; from contracts.module_api import Context; "
                  "from modules.m1_lexicon.module import LexiconModule; "
                  "out = LexiconModule().process(Context(text=sys.argv[1])); "
                  "sys.stdout.buffer.write(json.dumps([g.evidence for g in out.guards]).encode())")
        root = Path(__file__).resolve().parents[2]
        for seed in ("0", "2", "3"):
            with self.subTest(PYTHONHASHSEED=seed):
                run = subprocess.run([sys.executable, "-c", script, text], cwd=root, capture_output=True,
                                     env={**os.environ, "PYTHONHASHSEED": seed}, timeout=300)
                self.assertEqual(run.returncode, 0, run.stderr.decode("utf-8", "replace")[-2000:])
                self.assertEqual(json.loads(run.stdout.decode("utf-8")), expected)

    def test_amen_is_a_clean_word_not_the_obscene_root(self) -> None:
        """terlik reads "amin" (amen) as am + in; its whitelist holds only the English "amen". Prayer
        language must not carry the obscene root (spec §4.1: a root inside a clean word is a collision).
        The neighbours that ARE obscene - the dotless genitive "amın", "amına koyim", the ASCII
        "aminakoyim" - must keep matching: the clean entry is a whole-word rule, never a prefix."""
        for text in ("Allah kabul etsin, amin", "Allah akıl fikir versin AMİN", "Rabbim korusun, âmin.",
                     "amin amin", "Amiiin!"):
            with self.subTest(clean=text):
                out = self.run_m1(text)
                self.assertEqual(out.content, [], text)
                self.assertFalse(out.signals["lexicon_hit"])
                self.assertTrue(any(g.code is GuardCode.SUBSTRING_COLLISION and "clean word amin" in g.evidence
                                    for g in out.guards), [g.evidence for g in out.guards])
        for text in ("amına koyim", "aminakoyim", "senin amın", "am"):
            with self.subTest(still_matches=text):
                out = self.run_m1(text)
                self.assertTrue(out.signals["lexicon_hit"], text)
                self.assertTrue(out.content, text)

    def test_homonym_guard_on_am_as_a_time_abbreviation(self) -> None:
        # spec §7: "am" used as an abbreviation. terlik matches the standalone root; the HOMONYM
        # guard carries the same span so the decision layer suppresses exactly that match (ADR-001).
        for text in ("saat 10 am gibi gel", "toplantı 10:30 am", "am/pm formatı"):
            with self.subTest(text=text):
                out = self.run_m1(text)
                a1 = [s for s in out.content if s.code is ContentCode.A1]
                homonym = [g for g in out.guards if g.code is GuardCode.HOMONYM]
                self.assertEqual(len(a1), 1)
                self.assertEqual([g.span for g in homonym], [a1[0].span])
                self.assertEqual(text[a1[0].span[0]:a1[0].span[1]].lower(), "am")
        plain = self.run_m1("am biti")
        self.assertEqual([g.code for g in plain.guards if g.code is GuardCode.HOMONYM], [])

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

    def test_non_human_target_raises_guard_on_its_content_scores(self) -> None:
        # The guard is raised on each content span; thresholds.yaml decides which codes it may
        # suppress (A1-A3 and B1 since M1-ROUTE-1).
        text = "aptal film"
        out = self.run_m1(text, signals=fake_m6_target("non_human", 0.9))
        guards = [g for g in out.guards if g.code is GuardCode.NON_HUMAN_TARGET]
        self.assertEqual([text[g.span[0]:g.span[1]] for g in guards], ["aptal"])
        self.assertEqual({g.score for g in guards}, {0.9})   # score = m6's target_confidence (spec §3)
        self.assertEqual([g for g in self.run_m1(text, signals=fake_m6_target("individual", 0.9)).guards
                          if g.code is GuardCode.NON_HUMAN_TARGET], [])
        self.assertEqual([g for g in self.run_m1("film", signals=fake_m6_target("non_human", 0.9)).guards
                          if g.code is GuardCode.NON_HUMAN_TARGET], [])

    # -- M1-ROUTE-1 (protocols/m1_runtime_routing_protocol.md) ---------------------------------
    def test_routing_table_partitions_the_dictionary_and_keeps_family_a_narrow(self) -> None:
        self.module.process(Context(text="warmup"))                     # loads terlik
        dictionary = set(self.module._engine.get_patterns())
        classes = [roots for roots, _ in ROUTE_CLASSES.values()]
        self.assertEqual(set().union(*classes), dictionary)
        self.assertEqual(sum(map(len, classes)), len(dictionary))       # disjoint
        self.assertEqual((len(ROUTE_A), len(ROUTE_B1), len(ROUTE_B2), len(ROUTE_B3), len(ROUTE_NONE)),
                         (17, 100, 7, 9, 14))
        self.assertEqual(EXCLUDED_ROOTS, dictionary - ROUTE_A)
        self.assertEqual({code for _, code in ROUTE_CLASSES.values()},
                         {ContentCode.A1, ContentCode.B1, ContentCode.B2, ContentCode.B3, None})

    def test_each_route_emits_its_code_and_every_match_stays_a_match(self) -> None:
        for text, root, code in (("orospu", "orospu", ContentCode.A1), ("aptal", "aptal", ContentCode.B1),
                                 ("öldürücem seni", "öldürücem", ContentCode.B2), ("geber", "geber", ContentCode.B3),
                                 ("meme kanseri", "meme", None), ("kaşar peyniri", "kaşar", None)):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertTrue(out.signals["lexicon_hit"])
                self.assertEqual(out.signals["matched_roots"], [root])
                self.assertEqual([s.code for s in out.content], [] if code is None else [code])
                self.assertEqual([(m["root"], m["channel"], m["route"]) for m in out.signals["_matches"]],
                                 [(root, "raw", ROUTE_OF[root])])
                self.assertEqual(text[slice(*out.signals["_matches"][0]["span"])].lower()[:len(root) - 1],
                                 root[:len(root) - 1])

    def test_private_matches_mirror_every_spanned_match_on_both_channels(self) -> None:
        out = self.run_m1("sen salak mısın", normalized_text="sen salak mısın")
        self.assertEqual(sorted((m["channel"], tuple(m["span"])) for m in out.signals["_matches"]),
                         [("normalized", (4, 9)), ("raw", (4, 9))])
        self.assertEqual(sorted((s.source, s.span) for s in out.content),
                         [("m1_lexicon@normalized", (4, 9)), ("m1_lexicon@raw", (4, 9))])

    def test_homonym_guard_on_property_and_food_compounds_only(self) -> None:
        for text, surface in (("mal varlığı açıklandı", "mal"), ("MAL VARLIĞI", "MAL"), ("mal sahibi geldi", "mal"),
                              ("mal mülk", "mal"), ("mal ve hizmet", "mal"), ("domuz eti", "domuz"),
                              ("domuz et", "domuz"), ("domuz gribi", "domuz")):
            with self.subTest(protected=text):
                out = self.run_m1(text)
                b1 = [s for s in out.content if s.code is ContentCode.B1]
                self.assertEqual([text[s.span[0]:s.span[1]] for s in b1], [surface])
                self.assertEqual([g.span for g in out.guards if g.code is GuardCode.HOMONYM], [b1[0].span])
        for text in ("mal", "mal mısın", "mal gibi", "domuz", "domuz herif", "domuz etinden"):
            with self.subTest(still_fires=text):
                out = self.run_m1(text)
                self.assertEqual([s.code for s in out.content], [ContentCode.B1])
                self.assertEqual([g for g in out.guards if g.code is GuardCode.HOMONYM], [])

    def test_excluded_root_boundary_and_clean_word(self) -> None:
        for text in ("alık", "sen alıksın", "a l ı k", "sal ak", "salak mısın"):
            with self.subTest(hit=text):
                out = self.run_m1(text)
                self.assertTrue(out.signals["lexicon_hit"])
                self.assertEqual([s.code for s in out.content], [ContentCode.B1])
        for text, evidence in (("Ali Kınık", "split across words"), ("ali, kimi", "split across words"),
                               ("Ali kim", "split across words"), ("allık", "clean word allık")):
            with self.subTest(collision=text):
                out = self.run_m1(text)
                self.assertFalse(out.signals["lexicon_hit"])
                self.assertEqual(out.content, [])
                self.assertEqual(out.signals["_matches"], [])
                self.assertTrue(any(g.code is GuardCode.SUBSTRING_COLLISION and evidence in g.evidence
                                    for g in out.guards), [g.evidence for g in out.guards])
        for text in ("Ali", "Ali'nin"):
            with self.subTest(clean=text):
                out = self.run_m1(text)
                self.assertFalse(out.signals["lexicon_hit"])
                self.assertEqual(out.guards, [])

    def test_compound_roots_keep_their_standard_two_word_spelling(self) -> None:
        # M1-ROUTE-1.1 §1: the split on the compound's own word boundary, suffix on the last component.
        for text, root in (("geri zekalı", "gerizekalı"), ("geri zekalısın", "gerizekalı"),
                           ("geri zekalılar", "gerizekalı"), ("Geri zekâlıyım", "gerizekalı"),
                           ("kötü niyetli", "kötüniyetli"), ("kötü niyetliler", "kötüniyetli"),
                           ("üç kâğıtçı", "üçkağıtçı"), ("üç kâğıtçılıkları", "üçkağıtçı"),
                           ("kalın kafalılar", "kalınkafalı"), ("yarım akıllılar", "yarımakıllı"),
                           ("kıt akıllısın", "kıtakıllı"), ("yüz karasısın", "yüzkarası"),
                           ("ağzı bozuklar", "ağzıbozuk"), ("baldırı çıplaklar", "baldırıçıplak"),
                           ("beyin amipler", "beyinamip"), ("eş oğlu eşekler", "eşoğlueşek")):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual(out.signals["matched_roots"], [root])
                self.assertEqual([(s.code, text[s.span[0]:s.span[1]]) for s in out.content], [(ContentCode.B1, text)])
        # Root-specific, boundary-specific: a split elsewhere on a compound root is still rejected.
        out = self.run_m1("gerize kalısın")
        self.assertFalse(out.signals["lexicon_hit"])
        self.assertTrue(any("split across words" in g.evidence for g in out.guards))
        self.assertEqual({r for r, parts in COMPOUND_ROOTS.items() if "".join(parts) != r}, set())
        self.assertLessEqual(set(COMPOUND_ROOTS), ROUTE_B1)

    def test_false_cross_word_matches_stay_rejected(self) -> None:
        # The compound rule and the punctuation cut must not re-admit any of these (M1-ROUTE-1.1).
        for text in ("Ali Kınık", "ali, kimi", "Ali kim", "kan çıkar", "den yolladım", "al ikinci",
                     "Ali, Kınık", "kan, çıkar"):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertFalse(out.signals["lexicon_hit"])
                self.assertEqual((out.content, out.signals["_matches"]), ([], []))
                self.assertTrue(any("split across words" in g.evidence for g in out.guards), [g.evidence for g in out.guards])

    def test_punctuation_after_a_complete_root_word_is_cut_not_matched_across(self) -> None:
        # M1-ROUTE-1.1 §2: terlik read ", at'ı" as a suffix of "eşşek"; the hit is kept on the word only.
        for text, word in (("EŞŞEK,  AT'I", "EŞŞEK"), ("eşşek, at'ı", "eşşek")):
            with self.subTest(text=text):
                out = self.run_m1(text)
                self.assertEqual([(s.code, text[s.span[0]:s.span[1]]) for s in out.content], [(ContentCode.B1, word)])
                self.assertEqual([m["root"] for m in out.signals["_matches"]], ["eşek"])

    def test_excluded_root_fixes_never_touch_a_positive_root(self) -> None:
        # M1-ROUTE-1 §5 is scoped to EXCLUDED roots: POSITIVE-root matching is unchanged in this
        # version (its own precision work is a separate task), split matches included.
        self.module.process(Context(text="warmup"))
        for root in sorted(ROUTE_A):
            self.assertIsNone(self.module._excluded_rejection(root, f"{root[0]} {root[1:]}x"), root)
            self.assertNotIn(root, COMPOUND_ROOTS)
        for text in ("s i k", "o r o s p u"):
            with self.subTest(text=text):
                self.assertEqual([s.code for s in self.run_m1(text).content], [ContentCode.A1])

    def test_deterministic(self) -> None:
        text = "Amcam aptallar psikoloji"
        self.assertEqual(self.run_m1(text).content, self.run_m1(text).content)


if __name__ == "__main__":
    unittest.main()
