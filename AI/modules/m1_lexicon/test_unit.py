"""Unit tests for m1_lexicon: contract tests and behaviour tests (spec.md §3, §7, §8)."""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import ContentCode, GuardCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m1_lexicon import module as M1
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
        # M1-ROUTE-1 §5 is scoped to EXCLUDED roots. POSITIVE-root matching has its own rules
        # (M1-PREC-1, PositiveRootPrecisionTest below); a complete spaced spelling stays a match.
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


PRECISION_PROTOCOL = Path(__file__).resolve().parents[2] / "protocols" / "m1_positive_matching_precision_protocol.md"


def protocol_line(name: str) -> tuple[str, int | None]:
    """A machine-checked line of the M1-PREC-1 protocol: its body and its declared count, if any."""
    found = re.search(rf"^{re.escape(name)}(?: \((\d+)\))?: (.*)$", PRECISION_PROTOCOL.read_text(encoding="utf-8"), re.M)
    if found is None:
        raise AssertionError(f"{name} line missing from {PRECISION_PROTOCOL.name}")
    return found.group(2), (int(found.group(1)) if found.group(1) else None)


def accept_list(name: str) -> list[str]:
    body, count = protocol_line(name)
    items = body.split(" | ")
    if len(items) != count:
        raise AssertionError(f"{name}: {len(items)} entries, the protocol declares {count}")
    return items


class PositiveRootPrecisionTest(unittest.TestCase):
    """M1-PREC-1 (pseudo-label rule v4, protocols/m1_positive_matching_precision_protocol.md): a match
    of a family-A root is a hit only when it is a real word of that root. m1 alone here (raw channel,
    and the same text as a normalized channel); tests/test_m1_lexicon_labels.py runs the protocol's
    lists through the full m0 -> m2 -> m6 -> m1 path as well."""

    def setUp(self) -> None:
        self.module = LexiconModule()

    def run_m1(self, text: str, **kwargs) -> ModuleOutput:
        out = self.module.process(Context(text=text, **kwargs))
        self.assertTrue(out.ok, out.notes)
        return out

    def family_a(self, text: str, **kwargs) -> list[tuple[str, str]]:
        """(root, matched original text) of every family-A match m1 keeps, raw channel first."""
        out = self.run_m1(text, **kwargs)
        return [(m["root"], text[m["span"][0]:m["span"][1]]) for m in out.signals["_matches"] if m["route"] == "A"]

    def rejection(self, text: str) -> list[str]:
        return [g.evidence for g in self.run_m1(text).guards
                if g.code is GuardCode.SUBSTRING_COLLISION and "rule-v4" in g.evidence]

    # -- the data is the protocol ----------------------------------------------------------------
    def test_character_classes_stems_forms_are_the_protocol(self) -> None:
        for name in ("PREC_EDGE_KEPT", "PREC_EDGE_KEPT_LEADING", "PREC_IN_WORD", "PREC_IN_WORD_BETWEEN_LETTERS",
                     "PREC_APOSTROPHES", "PREC_MASKS", "PREC_CROSS_WORD"):
            with self.subTest(name=name):
                self.assertEqual(frozenset(protocol_line(name)[0].split()), getattr(M1, name))
        body, count = protocol_line("PREC_TURKISH_STEMS")
        stems = {root.strip(): tuple(s.strip() for s in spellings.split(","))
                 for root, spellings in (entry.split("=") for entry in body.split(";"))}
        self.assertEqual((stems, len(stems)), (M1.PREC_TURKISH_STEMS, count))
        self.assertEqual(frozenset(v.strip() for v in protocol_line("PREC_HARMONY_BREAK_VOWELS")[0].split(",")),
                         M1.PREC_HARMONY_BREAK_VOWELS)
        self.assertEqual(tuple(protocol_line("PREC_INVARIANT_SUFFIXES")[0].split(", ")), M1.PREC_INVARIANT_SUFFIXES)
        self.assertEqual(protocol_line("PREC_AM_FORMS")[0], M1.PREC_AM_FORMS.pattern)
        body, count = protocol_line("PREC_CLEAN_FORMS")
        forms = [tuple(x.strip() for x in entry.split("=")) for entry in body.split(";")]
        self.assertEqual((forms, len(forms)), ([(root, form) for root, form, _, _ in M1.PREC_CLEAN_FORMS], count))
        self.assertLessEqual({root for root, _ in forms} | set(M1.PREC_TURKISH_STEMS), ROUTE_A)

    def test_family_a_roots_are_still_the_seventeen_rule_v3_roots(self) -> None:
        self.assertEqual(ROUTE_A, frozenset({"am", "amcı", "amk", "bok", "gavat", "göt", "hassiktir", "orospu", "oç",
                                             "pezevenk", "piç", "sakso", "sg", "sik", "sktrgt", "taşak", "yarrak"}))
        self.assertFalse(ROUTE_A & EXCLUDED_ROOTS)

    # -- the protocol's acceptance lists ---------------------------------------------------------
    def test_acceptance_lists(self) -> None:
        for channels in ({}, "normalized"):
            for text in accept_list("ACCEPT_CLEAN"):
                with self.subTest(clean=text, channels=channels):
                    kwargs = {"normalized_text": text} if channels else {}
                    self.assertEqual(self.family_a(text, **kwargs), [])
            for name in ("ACCEPT_GENUINE", "ACCEPT_RESIDUE", "ACCEPT_MASKED"):
                for entry in accept_list(name):
                    text, root = entry.rsplit(" => ", 1)
                    with self.subTest(list=name, text=text, channels=channels):
                        kwargs = {"normalized_text": text} if channels else {}
                        self.assertIn(root, {r for r, _ in self.family_a(text, **kwargs)})

    # -- one rule at a time: the rejection names its rule; a kept hit spans its word -------------
    def test_r1_no_letter_and_r2_edge_digits(self) -> None:
        for text in ("59", "6-7", "566"):
            with self.subTest(text=text):
                self.assertTrue(any("rule-v4 R1" in e for e in self.rejection(text)), self.rejection(text))
        for text in ("4k", "GOT7", "got7", "4.5g"):
            with self.subTest(text=text):
                self.assertTrue(any("rule-v4 R2" in e for e in self.rejection(text)), self.rejection(text))
        for text, root in (("s1k", "sik"), ("g0t", "göt"), ("s1kt1r", "sik")):
            with self.subTest(kept=text):
                self.assertEqual(self.family_a(text), [(root, text)])

    def test_r3_edge_punctuation_hashtag_and_glued_words(self) -> None:
        for text, kept in (("#sikiş", ("sik", "sikiş")), ("'pezevenk'", ("pezevenk", "pezevenk")),
                           ("#YaRRaĞıMıYe", ("yarrak", "YaRRaĞıMıYe")), ("[piç(3) nalan(5)]", ("piç", "piç")),
                           ("bozuntusu:'Amına", ("amk", "Amına")),
                           # terlik reads the quote as a separator and -ce -ken as suffixes: one whole word
                           ('"Hassiktir"çeken', ("hassiktir", 'Hassiktir"çeken')),
                           ("amk😂 çok güzel", ("amk", "amk")), ("a.q.", ("amk", "a.q"))):
            with self.subTest(text=text):
                self.assertIn(kept, self.family_a(text))
                self.assertTrue(all(len(surface) <= len(text) and surface.strip("#'\"[(") == surface
                                    for _, surface in self.family_a(text)))
        for text, reason in (("(Amin) inşallah güzel olur", "clean word amin"), ("#AMİN çok güzel", "clean word amin"),
                             ("‘amca geldi’ dedi şöyle", "clean word amca"), ("sıkı. çok güzel", "whitelist"),
                             ("ama! öyle değil", "whitelist")):
            with self.subTest(clean=text):
                self.assertEqual(self.family_a(text), [])
                self.assertTrue(any("rule-v4 R3" in e and reason in e for e in self.rejection(text)),
                                self.rejection(text))

    def test_a_rejected_glued_segment_never_suppresses_the_word_inside_it(self) -> None:
        # Guards suppress by span overlap (ADR-001): a collision over "[piç(3)" would silence "piç".
        for text in ("[piç(3) nalan(5)]", "bozuntusu:'Amına", '"Hassiktir"çeken'):
            with self.subTest(text=text):
                out = self.run_m1(text)
                a1 = [s.span for s in out.content if s.code is ContentCode.A1]
                self.assertTrue(a1)
                collisions = [g.span for g in out.guards if g.code is GuardCode.SUBSTRING_COLLISION]
                self.assertFalse([c for c in collisions for s in a1 if c[0] < s[1] and s[0] < c[1]], (a1, collisions))

    def test_r4_apostrophes_and_masks_inside_a_word(self) -> None:
        for text in ("Bel'am", "En'âm", "istanbul'a mı", "ta+ak"):
            with self.subTest(text=text):
                self.assertEqual(self.family_a(text), [])
                self.assertTrue(self.rejection(text))
        self.assertTrue(any("rule-v4 R4" in e for e in self.rejection("Bel'am")))
        self.assertEqual(self.family_a("taşAK'larını"), [("taşak", "taşAK'larını")])

    def test_r5_cross_word(self) -> None:
        for text in ("A mı", "ama en", "ama cam", "YA A. SİZE NE A. MALLARI", "A&M", "T A M A M",
                     "S I K I L D I K", "B A Ş A R A M A Y A C A K"):
            with self.subTest(text=text):
                self.assertEqual(self.family_a(text), [])
        self.assertTrue(any("rule-v4 R5" in e for e in self.rejection("A mı")))
        self.assertEqual(self.family_a("B O K"), [("bok", "B O K")])
        self.assertEqual(self.family_a("L Ü T F E N  B O K"), [("bok", "B O K")])     # two spaces end a run
        self.assertEqual(self.family_a("L Ü T F E N B O K"), [])                       # one run: "lütfenbok"
        self.assertEqual(self.family_a("sik, sin"), [("sik", "sik")])                  # punctuation cut
        self.assertEqual(self.family_a("göt, e"), [("göt", "göt")])

    def test_r6_turkish_letter_precision(self) -> None:
        for text in ("sıkıldım", "canım sıkıldı", "sık sık", "sıkıyor", "sıklıkla", "sıkarken", "sıkıyim", "şık",
                     "şike", "ŞİKE", "öç almak", "Öc", "sıkım", "sıkımı", "sıktır git", "SIKTIR GIT"):
            with self.subTest(clean=text):
                self.assertEqual(self.family_a(text), [])
                self.assertTrue(any("rule-v4 R6" in e for e in self.rejection(text)), self.rejection(text))
        for text in ("sıkecek", "sıkmek", "sıkıcıler", "SIKERIM", "sik", "sikildim", "siktir", "s!k", "PIÇ",
                     "HASSIKTIR"):
            with self.subTest(kept=text):
                self.assertTrue(self.family_a(text))

    def test_r7_am_morphology(self) -> None:
        for text in ("amacı", "amaca", "amma", "amirim", "amirlik", "amade", "amme", "amenna", "ammar", "aamca", "amık",
                     "I am here", "i am here"):
            with self.subTest(clean=text):
                self.assertEqual(self.family_a(text), [])
                self.assertTrue(any("rule-v4 R7" in e for e in self.rejection(text)), self.rejection(text))
        for text in ("am", "amı", "ami", "amini", "aminin", "amindan", "amdan", "amcık", "senin amın"):
            with self.subTest(kept=text):
                self.assertEqual([r for r, _ in self.family_a(text)], ["am"])
        for text in ("amin", "AMİN", "âmin", "amîn", "Amiiin!"):
            with self.subTest(prayer=text):
                self.assertEqual(self.family_a(text), [])

    def test_r8_stable_clean_forms(self) -> None:
        for text, form in (("AK Parti", "ak"), ("ak renk", "ak"), ("akk", "ak"), ("A.K. Parti", "ak"), ("GT", "gt"),
                           ("gta", "gta"), ("GOT", "GOT"), ("#GOT çok iyi", "GOT"), ("pc", "pc"), ("book", "book"),
                           ("ananı", "ananı"), ("ananıda", "ananı"), ("anani", "ananı")):
            with self.subTest(clean=text):
                self.assertEqual(self.family_a(text), [])
                self.assertTrue(any(f"rule-v4 R8: clean form {form}" in e for e in self.rejection(text)),
                                self.rejection(text))
        for text, root in (("got yalamayı", "göt"), ("gotunu", "göt"), ("g.t", "göt"), ("g*t", "göt"), ("pic", "piç"),
                           ("ananısikeyim", "amk"), ("a.q", "amk"), ("@Q", "amk"), ("M.K. Atatürk", "amk"),
                           ("she's got the look", "göt")):
            with self.subTest(kept=text):
                self.assertIn(root, {r for r, _ in self.family_a(text)})

    def test_r9_masked_root_alignment(self) -> None:
        self.assertEqual(self.family_a("ta*ak geçtim"), [("taşak", "ta*ak")])
        self.assertEqual(self.family_a("ta+ak"), [])                  # "+" and "." are not masks for R9
        self.assertEqual(self.family_a("g*t"), [("göt", "g*t")])      # terlik's own reading, not doubled

    def test_original_evidence_decides_r1_r2_and_cased_forms(self) -> None:
        # m0 lowercases and m2 repairs leet: R1, R2 and the cased GOT form read the ORIGINAL text.
        for text, normalized in (("got7", "gott"), ("59", "sg"), ("GOT", "got")):
            with self.subTest(text=text):
                out = self.run_m1(text, charsafe_text=text.lower(), normalized_text=normalized)
                self.assertEqual([m for m in out.signals["_matches"] if m["route"] == "A"], [])

    def test_excluded_roots_and_routes_are_untouched(self) -> None:
        for text, code in (("s a l a k", ContentCode.B1), ("salak mısın", ContentCode.B1), ("geri zekalısın", ContentCode.B1),
                           ("öldürücem seni", ContentCode.B2), ("geber", ContentCode.B3)):
            with self.subTest(text=text):
                self.assertEqual([s.code for s in self.run_m1(text).content], [code])
        self.assertTrue(any("split across words, not the bare root" in g.evidence for g in self.run_m1("Ali Kınık").guards))


if __name__ == "__main__":
    unittest.main()
