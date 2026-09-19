"""Unit tests for m5_sarcasm Stage 1 (protocols/m5_stage1_deterministic_protocol.md, M5-S1): the
contract, every rule family, every exclusion, and the spec §11 fixture classes. Evidence, not a
benchmark: nothing here measures precision or recall."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import MappingProxyType

from contracts.codes import ContentCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m5_sarcasm.module import RULES_VERSION, SarcasmModule, fold

FIXTURES = Path(__file__).with_name("fixtures") / "cases.jsonl"
SIGNAL_KEYS = {"stage", "detector", "rules_version", "matched_rules", "excluded", "precedence_checked"}


def ctx(text: str, lexicon_hit: object = False, **channels: str) -> Context:
    """A context carrying m1's published lexicon_hit, frozen like the pipeline's (None: m1 absent)."""
    signals = {} if lexicon_hit is None else {"m1_lexicon": MappingProxyType({"lexicon_hit": lexicon_hit})}
    return Context(text=text, signals=MappingProxyType(signals), **channels)


class SarcasmModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = SarcasmModule()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m5_sarcasm"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m5_sarcasm")

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


class SarcasmModuleBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = SarcasmModule()

    def d1(self, context: Context) -> list[ContentScore]:
        out = self.module.process(context)
        self.assertTrue(out.ok, out.notes)
        return [s for s in out.content if s.code is ContentCode.D1]

    def assert_d1(self, text: str, rule: str) -> ModuleOutput:
        out = self.module.process(ctx(text))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual([(s.code, s.score, s.source) for s in out.content],
                         [(ContentCode.D1, 1.0, "m5_sarcasm@raw")], text)
        self.assertIn(rule, out.signals["matched_rules"], text)
        return out

    def assert_no_d1(self, text: str, reason: str | None = None, **kwargs: object) -> None:
        out = self.module.process(ctx(text, **kwargs))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.content, [], text)
        self.assertEqual(out.signals["matched_rules"], [], text)
        if reason is not None:
            self.assertIn(reason, [e["reason"] for e in out.signals["excluded"]], text)

    def test_stage_is_declared_honestly(self) -> None:
        self.assertFalse(getattr(self.module, "stub", False))
        out = self.module.process(ctx("Bu bir test cumlesi"))
        self.assertEqual(set(out.signals), SIGNAL_KEYS)
        self.assertEqual((out.signals["stage"], out.signals["detector"], out.signals["rules_version"]),
                         (1, "deterministic", RULES_VERSION))

    # 1-2. every rule family, each on its own
    def test_r1_scare_quoted_praise_at_the_addressee(self) -> None:
        text = "Bu kadar 'derin' bir yorum yapman etkileyici."   # spec §1, second example
        out = self.assert_d1(text, "R1_SCARE_QUOTE")
        start, end = out.content[0].span
        self.assertEqual(text[start:end], "'derin'")

    def test_r2_clause_final_tabii(self) -> None:
        self.assert_d1("Çok zekisin tabii.", "R2_CLAUSE_FINAL_TABII")
        self.assert_d1("Sen çok akıllısın tabi ki...", "R2_CLAUSE_FINAL_TABII")

    def test_r3_congratulated_failure(self) -> None:
        for text in ("Aferin sana, yine her şeyi berbat ettin.", "Yine geç kaldın, bravo.", "Bravo! Yine geç kaldın.",
                     "Helal olsun size, yine her şeyi berbat ettiniz."):
            with self.subTest(text=text):
                self.assert_d1(text, "R3_CONGRATULATED_FAILURE")

    def test_r4_irony_mark(self) -> None:
        self.assert_d1("Çok akıllısın (!)", "R4_IRONY_MARK")

    # 3. sincere praise, same vocabulary (spec §3, §11)
    def test_sincere_praise_is_not_d1(self) -> None:
        for text in ("Zekânı hayranlıkla izliyorum.", "Zekânı hayranlıkla izliyorum, gerçekten.",
                     "Aferin sana, sınavı geçtin.", "Tebrikler, 5 kilo kaybettin!", "Harika, rekor kırdın!",
                     "Aferin, hiç unutmadın.", "Tabii ki çok zekisin.", "Sen çok zekisin, tebrik ederim."):
            with self.subTest(text=text):
                self.assert_no_d1(text)

    # 4. benign sarcasm aimed at things (spec §8 control set); historical skipped test, now real
    def test_friendly_irony_is_not_d1(self) -> None:
        for text in ("Harika, otobüs yine gelmedi.", "Harika, yine yağmur yağıyor", "Muhteşem, takımımız yine kaybetti."):
            with self.subTest(text=text):
                self.assert_no_d1(text)
        for text in ("Bu program mükemmel çalışıyor tabii.", "Bu program mükemmel (!) çalışıyor.", "Ahmet çok zeki tabii."):
            with self.subTest(text=text):   # the construction is recognised, and declined: no person anchor
                self.assert_no_d1(text, "X_NO_PERSON")

    # 5. direct insult, no sarcastic structure
    def test_direct_insult_is_not_d1(self) -> None:
        for text in ("Sen tam bir aptalsın.", "Onlardan başka ne beklenir", "Zeki değilsin tabii."):
            with self.subTest(text=text):
                self.assert_no_d1(text)
        self.assert_no_d1("Zeki değilsin tabii.", "X_NEGATED")

    def test_explicit_content_takes_precedence(self) -> None:
        text = "Aferin sana aptal, yine her şeyi berbat ettin."
        out = self.module.process(ctx(text, lexicon_hit=True))
        self.assertEqual(out.content, [])
        self.assertEqual([e["reason"] for e in out.signals["excluded"]], ["X_EXPLICIT_CONTENT"])
        self.assertIn("D1 withheld: m1_lexicon found explicit content, which takes precedence (spec §3)", out.notes)

    def test_without_m1_the_precedence_rule_is_reported_unchecked(self) -> None:
        out = self.module.process(ctx("Çok zekisin tabii.", lexicon_hit=None))
        self.assertEqual([s.code for s in out.content], [ContentCode.D1])
        self.assertIs(out.signals["precedence_checked"], False)
        self.assertIn("precedence not checked: m1_lexicon published no lexicon_hit (spec §3)", out.notes)

    # 6. quoted or reported sarcasm (spec §11)
    def test_reported_sarcasm_is_not_d1(self) -> None:
        for text in ("'Aferin sana, yine her şeyi berbat ettin.' dedi hocam.",
                     "Aferin sana, yine her şeyi berbat ettin dedi.", "Bana 'harika' dedi."):
            with self.subTest(text=text):
                self.assert_no_d1(text, "X_REPORTED")
        self.assert_no_d1("Hoca bana 'çok zekisin tabii' dedi.")
        self.assert_no_d1("'Zeki' kelimesi nereden gelir?", "X_MENTION")
        self.assert_no_d1("Çok zekisin tabii?", "X_QUESTION")

    # 7. clean sentences
    def test_clean_sentences_are_not_d1(self) -> None:
        for text in ("Bugün hava çok güzel.", "Yarın saat 10'da toplantımız var.", "Süpermarkete gittin tabii.",
                     "Harika bir gün!"):
            with self.subTest(text=text):
                self.assert_no_d1(text)

    # raw-text sensitivity (spec §11): m5 reads ctx.text, never the normalized or charsafe channel
    def test_reads_the_raw_text_only(self) -> None:
        marked, plain = "Bu kadar 'derin' bir yorum yapman etkileyici.", "Bu kadar derin bir yorum yapman etkileyici."
        self.assertEqual(self.d1(ctx(plain, normalized_text=marked, charsafe_text=marked.lower())), [])
        self.assertEqual(len(self.d1(ctx(marked, normalized_text=plain, charsafe_text=plain.lower()))), 1)

    # Unicode interaction: Turkish casing and circumflex are folded character for character
    def test_turkish_casing_and_offsets(self) -> None:
        text = "ÇOK ZEKİSİN TABİİ."
        self.assertEqual(len(fold(text)), len(text))
        self.assertEqual(fold("ZEKÂNI İstanbul IŞIK"), "zekanı istanbul ışık")
        out = self.assert_d1(text, "R2_CLAUSE_FINAL_TABII")
        start, end = out.content[0].span
        self.assertEqual(text[start:end], "ÇOK ZEKİSİN TABİİ")

    # 8. deterministic repetition
    def test_deterministic(self) -> None:
        texts = ("Bu kadar 'derin' bir yorum yapman etkileyici.", "Bu program mükemmel çalışıyor tabii.",
                 "Aferin sana, yine her şeyi berbat ettin dedi.")
        for text in texts:
            first, second = self.module.process(ctx(text)), self.module.process(ctx(text))
            self.assertEqual((first.content, first.signals, first.notes), (second.content, second.signals, second.notes))

    # 9. invalid and edge inputs
    def test_edge_inputs(self) -> None:
        for text in ("", " ", "\t\n ", "🙂", "a" * 5000, "\x00\x1b", "''", "' '", "(!)", "tabii", "\"\"\"", "'derin"):
            with self.subTest(text=text[:20]):
                self.assert_no_d1(text)

    def test_signals_carry_no_copy_of_the_post(self) -> None:
        # decision 17: spans and rule ids only
        out = self.module.process(ctx("Bu program mükemmel çalışıyor tabii."))
        self.assertNotIn("program", json.dumps(out.signals, ensure_ascii=False))

    # spec §11 fixture check: every D1 positive names its literally positive element
    def test_fixture_positives_carry_an_inversion_span_the_module_covers(self) -> None:
        rows = [json.loads(line) for line in FIXTURES.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(any(r["expected"] == ["D1"] for r in rows))
        for row in rows:
            with self.subTest(id=row["id"]):
                signals = {k: MappingProxyType(v) for k, v in row["context"]["signals"].items()}
                out = self.module.process(Context(text=row["text"], signals=MappingProxyType(signals)))
                self.assertEqual([s.code.value for s in out.content], row["expected"])
                if row["expected"] == ["D1"]:
                    start, end = row["inversion_span"]
                    self.assertTrue(row["text"][start:end].strip())
                    span = out.content[0].span
                    self.assertTrue(span[0] <= start and end <= span[1], (span, row["inversion_span"]))
                else:
                    self.assertIsNone(row["inversion_span"])


if __name__ == "__main__":
    unittest.main()
