"""Gate 1, task 4: producer -> consumer signal interfaces that the system relies
on today, pinned so a renamed key, a missing signal, a wrong type or a changed
assumption on either side fails here instead of silently downstream.

Interfaces covered (MODULE_MAP.md §3), with their oracle:
  m0 -> m1          `_offsets` (ADR-001 Consequences; m1/module.py _raw_offsets)
  m1 -> decision    `lexicon_hit`, `lexicon_hit_raw`, `lexicon_hit_norm` (m1 spec §3, §8;
                    protocols/m4_stage1b_protocol.md §3)
  m3 -> decision    `raw_score`, `artifact`; `norm_score` absent today (thresholds.yaml
                    binary_offensive.channels; m3/module.py docstring)
  m3 -> m4          `raw_score`, `norm_score`, `artifact` (m4 spec §5); m4's stage-1 constants
                    against the config (ADR-006 amendment 2026-09-19)
  m1 -> m5          `lexicon_hit` for the D1 precedence rule (m5 spec §3, protocol M5-S1 §5), and
                    m5's D1 through the configured D1 row to the verdict
  pipeline -> decision  `signals.pipeline.degraded`, `signals.pipeline.emits_spans`
                    (HANDOVER #15, ADR-001 amendment; actions.degraded_modules, fusion.guard_applies)

NOT covered on purpose: the m2 normalized-channel offset map (OPEN_QUESTIONS Q5 -
no contract exists to test against) and m6's target routes (Q6).

Preconditions (terlik, the m3 artifact) FAIL with a named reason; they never skip,
because a skipped interface test is exactly the kind of green this gate removes.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from contracts.codes import Action, ContentCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import AnalysisResult, ContentScore
from decision import actions, fusion
from modules.m0_charsafe.module import CharSafeModule
from modules.m1_lexicon.module import LexiconModule
from modules.m2_deobf.module import DeobfModule
from modules.m3_encoder import module as m3
from modules.m4_implicit import module as m4
from modules.m5_sarcasm.module import SarcasmModule
from modules.m6_target.module import TargetModule
from modules.m3_encoder.test_unit import artifact_available
from pipeline.run import Pipeline, public_signals, span_declarations

ROOT = Path(__file__).resolve().parent.parent
M0_SIGNAL_KEYS = {"_offsets", "offsets_identity", "invisible_removed", "homoglyphs_mapped", "charsafe_changed"}
M1_SIGNAL_KEYS = {"lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "matched_roots", "engine"}
M3_SIGNAL_KEYS = {"raw_score", "artifact", "truncated_differently", "_truncation"}       # + norm_score with a channel
PIPELINE_SIGNAL_KEYS = {"degraded", "emits_spans"}
DEGRADATION_KINDS = {"stub", "failed", "invalid_output"}
SAMPLE_TEXTS = ("", "Bu bir test cumlesi", "SIKINTI YOK", "ap​tal herif", "аptal", "İstanbul'da",
                "şehir", "\U0001F468‍\U0001F469", "a" * 300)


def require_terlik(test: unittest.TestCase) -> None:
    # find_spec, not an import: tests/ is core (stdlib + pyyaml only, rule 6); m1 owns terlik.
    if importlib.util.find_spec("terlik") is None:
        test.fail("PRECONDITION: terlik is not importable; m1_lexicon cannot be constructed on this machine")


def require_m3_artifact(test: unittest.TestCase) -> None:
    if not artifact_available():
        test.fail("PRECONDITION: m3 artifact files or torch/transformers missing on this machine "
                  "(eval/implementation_status.json m3_encoder.preconditions); not skipped on purpose")


class _Spy(BaseModule):
    """Records the Context it receives; stands in any slot."""

    provides = frozenset({"content"})
    emits_spans = False

    def __init__(self, name: ModuleName) -> None:
        super().__init__()
        self.name = name  # type: ignore[misc]
        self.seen: list[Context] = []

    def _run(self, ctx: Context) -> ModuleOutput:
        self.seen.append(ctx)
        return ModuleOutput()


class M0ToM1OffsetsTest(unittest.TestCase):
    """m1 maps every span back to the ORIGINAL text through m0's `_offsets`."""

    def setUp(self) -> None:
        self.m0 = CharSafeModule()
        self.m0.load()

    def test_m0_publishes_exactly_the_keys_downstream_relies_on(self) -> None:
        for text in SAMPLE_TEXTS:
            out = self.m0.process(Context(text=text))
            with self.subTest(text=text[:12], stage="INTERFACE_CONTRACT"):
                self.assertTrue(out.ok, out.notes)
                self.assertEqual(set(out.signals), M0_SIGNAL_KEYS)
                self.assertIsInstance(out.signals["offsets_identity"], bool)
                self.assertIsInstance(out.signals["charsafe_changed"], bool)
                self.assertIsInstance(out.signals["invisible_removed"], int)
                self.assertIsInstance(out.signals["homoglyphs_mapped"], int)
                self.assertIsInstance(out.charsafe_text, str)

    def test_offsets_invariants_m1_assumes(self) -> None:
        """One original index per charsafe character, in range, non-decreasing;
        identity flag true iff every character kept its index."""
        for text in SAMPLE_TEXTS:
            out = self.m0.process(Context(text=text))
            offsets = out.signals["_offsets"]
            with self.subTest(text=text[:12], stage="INTERFACE_CONTRACT"):
                self.assertIsInstance(offsets, list)
                self.assertEqual(len(offsets), len(out.charsafe_text))
                self.assertTrue(all(isinstance(o, int) and not isinstance(o, bool) for o in offsets))
                self.assertTrue(all(0 <= o < len(text) for o in offsets))
                self.assertEqual(offsets, sorted(offsets))
                self.assertEqual(out.signals["offsets_identity"], all(o == i for i, o in enumerate(offsets)))

    def test_offsets_reach_m1_frozen_and_stay_out_of_the_response(self) -> None:
        spy = _Spy(ModuleName.M1_LEXICON)
        text = "ap​tal herif"
        result = Pipeline(modules=[self.m0, spy], config=fusion.load_config()).analyze(text)
        ctx = spy.seen[0]
        with self.subTest(stage="INTERFACE_CONTRACT/context"):
            m0_signals = ctx.signals[ModuleName.M0_CHARSAFE.value]
            self.assertIn("_offsets", m0_signals)
            self.assertIsInstance(m0_signals["_offsets"], tuple)        # deep_freeze: sequences become tuples
            self.assertEqual(len(m0_signals["_offsets"]), len(ctx.charsafe_text))
            # m1's reader accepts that frozen form and yields the same list m0 produced.
            self.assertEqual(LexiconModule._raw_offsets(ctx, ctx.best_text()), list(m0_signals["_offsets"]))
        with self.subTest(stage="INTERFACE_CONTRACT/response"):
            self.assertNotIn("_offsets", result.signals[ModuleName.M0_CHARSAFE.value])
            self.assertEqual(set(result.signals[ModuleName.M0_CHARSAFE.value]), M0_SIGNAL_KEYS - {"_offsets"})
            self.assertEqual(public_signals({"_a": 1, "b": 2}), {"b": 2})

    def test_m1_span_lands_on_the_original_text_through_real_m0_output(self) -> None:
        require_terlik(self)
        text = "ap​tal herif"
        m0_out = self.m0.process(Context(text=text))
        m1 = LexiconModule()
        m1.load()
        out = m1.process(Context(text=text, charsafe_text=m0_out.charsafe_text,
                                 signals={ModuleName.M0_CHARSAFE.value: m0_out.signals}))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual([s.code.value for s in out.content], ["B1"])         # "aptal": B1 under M1-ROUTE-1
        start, end = out.content[0].span
        self.assertEqual(text[start:end], "ap​tal")     # the ORIGINAL substring, invisible char included


class M1ToDecisionSignalsTest(unittest.TestCase):
    def setUp(self) -> None:
        require_terlik(self)
        self.m1 = LexiconModule()
        self.m1.load()

    def test_hit_signals_are_present_and_boolean_on_every_input(self) -> None:
        for text in SAMPLE_TEXTS:
            out = self.m1.process(Context(text=text))
            with self.subTest(text=text[:12], stage="INTERFACE_CONTRACT"):
                self.assertTrue(out.ok, out.notes)
                self.assertGreaterEqual(set(out.signals), M1_SIGNAL_KEYS)
                for key in ("lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm"):
                    self.assertIsInstance(out.signals[key], bool, key)
                self.assertEqual(out.signals["lexicon_hit"],
                                 out.signals["lexicon_hit_raw"] or out.signals["lexicon_hit_norm"])
                self.assertFalse(out.signals["lexicon_hit_norm"])       # no normalized channel was given
                self.assertIsInstance(out.signals["matched_roots"], list)
                self.assertIsInstance(out.signals["engine"], str)

    def test_stage_1b_consumer_reads_a_key_m1_publishes(self) -> None:
        """protocols/m4_stage1b_protocol.md conditions on lexicon_hit_raw; the script
        must read the key by the name m1 publishes, and the decision layer's signal
        lookup must resolve it to a bool."""
        source = (ROOT / "eval" / "m4_stage1b.py").read_text(encoding="utf-8")
        self.assertIn('"lexicon_hit_raw"', source)
        out = self.m1.process(Context(text="Onlar aptallar"))
        signals = {ModuleName.M1_LEXICON.value: out.signals}
        self.assertIs(fusion.lookup_signal(signals, "m1_lexicon.lexicon_hit_raw"), True)
        self.assertIs(fusion.lookup_signal(signals, "m1_lexicon.lexicon_hit"), True)
        self.assertIs(fusion.lookup_signal(signals, "m1_lexicon.lexicon_hit_norm"), False)

    def test_hit_and_emitted_matches_agree_on_the_raw_channel(self) -> None:
        """The raw flag and the evidence agree: lexicon_hit_raw is true iff m1's private `_matches`
        holds a raw match. Since M1-ROUTE-1 a match emits content only when its root routes to a
        code: topic vocabulary ("meme") is a hit with no content score."""
        for text, hit, content in (("Onlar aptallar", True, True), ("meme kanseri", True, False),
                                   ("Bu bir test cumlesi", False, False), ("SIKINTI YOK", False, False)):
            out = self.m1.process(Context(text=text))
            with self.subTest(text=text):
                self.assertIs(out.signals["lexicon_hit_raw"], hit)
                self.assertIs(any(m["channel"] == "raw" for m in out.signals["_matches"]), hit)
                self.assertEqual(bool(out.content), content)


class M3ToDecisionSignalsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = fusion.load_config()

    def test_yaml_channel_path_names_m3_and_a_key_m3_publishes(self) -> None:
        """No model needed: the path in thresholds.yaml must split into m3's module
        name and the signal key m3 is documented to publish."""
        channels = self.cfg["binary_offensive"]["channels"]
        self.assertEqual(set(channels), {"raw"})                      # no norm_score row exists today
        module, key = fusion._split_signal_path(channels["raw"])
        self.assertEqual(module, ModuleName.M3_ENCODER.value)
        self.assertEqual(key, "raw_score")
        self.assertIn(key, M3_SIGNAL_KEYS)

    def test_artifact_id_is_the_one_the_threshold_was_derived_on(self) -> None:
        """The yaml states the artifact its threshold is valid for; the MANIFEST lists
        it; m3 publishes it. All three must name the same id."""
        yaml_text = fusion.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
        manifest = (ROOT / "artifacts" / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn(m3.ARTIFACT_ID, yaml_text)
        self.assertIn(f"| {m3.ARTIFACT_ID} |", manifest)

    def test_m3_publishes_exactly_what_the_decision_layer_reads(self) -> None:
        require_m3_artifact(self)
        module = m3.EncoderModule()
        module.load()
        out = module.process(Context(text="Bu bir test cumlesi", charsafe_text="bu bir test cumlesi",
                                     normalized_text="bu bir test cumlesi"))
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertTrue(out.ok, out.notes)
            self.assertEqual(set(out.signals), M3_SIGNAL_KEYS | {"norm_score"})   # a normalized channel was given
            # rule-v4: the trained A head on the A1 carrier, one score per channel; B and C are not trained.
            self.assertEqual(sorted((s.code.value, s.source) for s in out.content),
                             [("A1", "m3_encoder@normalized"), ("A1", "m3_encoder@raw")])
            self.assertEqual(out.signals["artifact"], m3.ARTIFACT_ID)
        signals = {ModuleName.M3_ENCODER.value: out.signals}
        with self.subTest(stage="INTERFACE_CONTRACT"):
            value = fusion.lookup_signal(signals, self.cfg["binary_offensive"]["channels"]["raw"])
            self.assertIsInstance(value, float)
            self.assertTrue(0.0 <= value <= 1.0)
            # norm_score is published (spec §4) but no yaml row reads it: the decision layer stays raw-only.
            self.assertIsInstance(fusion.lookup_signal(signals, "m3_encoder.norm_score"), float)
        result = fusion.decide(AnalysisResult(text="x", signals=signals), self.cfg)
        binary = result.signals["decision"]["binary_offensive"]
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertEqual(set(binary["channels"]), {"raw"})
            self.assertEqual(binary["channels"]["raw"]["score"], out.signals["raw_score"])
            self.assertIsInstance(binary["fired"], bool)
            self.assertEqual(binary["fired"], out.signals["raw_score"] > binary["threshold"])


class M3ToM4SignalsTest(unittest.TestCase):
    """m4 reads what m3 publishes (m4 spec §5) and names what the stage-1 row thresholds
    (ADR-006 amendment 2026-09-19). Its constants must say what the config says."""

    def setUp(self) -> None:
        self.cfg = fusion.load_config()

    def test_stage1_constants_are_the_configured_ones(self) -> None:
        self.assertEqual(m4.STAGE1_INPUT, self.cfg["binary_offensive"]["channels"]["raw"])
        self.assertIn(m4.STAGE1_DERIVED_FOR, self.cfg["artifact"]["derived_on"])
        self.assertEqual(m4.STAGE1_DERIVED_FOR, m3.ARTIFACT_ID)
        manifest = (ROOT / "artifacts" / "MANIFEST.md").read_text(encoding="utf-8")
        self.assertIn(f"| {m4.STAGE1_DERIVED_FOR} |", manifest)

    def test_m4_reports_the_score_the_decision_layer_thresholds(self) -> None:
        require_m3_artifact(self)
        modules = [CharSafeModule(), DeobfModule(), m3.EncoderModule(), m4.ImplicitModule()]
        pipeline = Pipeline(modules=modules, config=self.cfg)
        for text in ("Bu bir test cumlesi", "s1kt1r git"):
            with self.subTest(text=text):
                result = pipeline.analyze(text)
                published, stage1 = result.signals["m3_encoder"], result.signals["m4_implicit"]
                self.assertEqual(result.signals["pipeline"]["degraded"], [])
                self.assertIs(stage1["stage1_input_present"], True)
                self.assertEqual(stage1["m3_artifact"], published["artifact"])
                self.assertIs(stage1["stage1_artifact_match"], True)
                binary = result.signals["decision"]["binary_offensive"]
                self.assertEqual(fusion.lookup_signal(result.signals, stage1["stage1_input"]),
                                 binary["channels"]["raw"]["score"])
                if "norm_score" in published:
                    self.assertEqual(stage1["norm_minus_raw"], published["norm_score"] - published["raw_score"])
                else:
                    self.assertIsNone(stage1["norm_minus_raw"])
                self.assertEqual([n for n in result.notes if n.startswith("[m4_implicit]")],
                                 [f"[m4_implicit] {m4.NOTE_C_FAMILY}"])


class M1ToM5SignalsTest(unittest.TestCase):
    """m5 Stage 1 in the real pipeline (protocols/m5_stage1_deterministic_protocol.md): it reads m1's
    published lexicon_hit for the spec §3 precedence rule, and its D1 reaches the verdict through the
    configured D1 row. m3 is left out on purpose: none of this depends on the encoder."""

    def setUp(self) -> None:
        require_terlik(self)
        self.cfg = fusion.load_config()
        self.pipeline = Pipeline(modules=[CharSafeModule(), DeobfModule(), TargetModule(), LexiconModule(),
                                          SarcasmModule()], config=self.cfg)

    def test_d1_reaches_the_verdict_through_its_configured_row(self) -> None:
        result = self.pipeline.analyze("Bu kadar 'derin' bir yorum yapman etkileyici.")
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertEqual(result.signals["m5_sarcasm"]["matched_rules"], ["R1_SCARE_QUOTE"])
            self.assertIs(result.signals["m5_sarcasm"]["precedence_checked"], True)
            self.assertEqual(result.signals["pipeline"]["degraded"], [])
        with self.subTest(stage="DECISION_THRESHOLD"):
            [d1] = [s for s in result.content if s.code is ContentCode.D1]
            self.assertEqual((d1.score, d1.source), (1.0, "m5_sarcasm@raw"))
            self.assertEqual(d1.threshold, float(self.cfg["categories"]["D1"]["threshold"]))
            self.assertTrue(d1.fired)
        with self.subTest(stage="FINAL_ACTION"):
            verdict, driver = actions.resolve(result, self.cfg)
            self.assertIs(verdict, Action(self.cfg["categories"]["D1"]["action"]))
            self.assertIs(result.verdict, verdict)
            self.assertEqual(getattr(driver, "code", None), ContentCode.D1)
            self.assertIn("(D1)", result.explanation)

    def test_explicit_content_wins_over_d1(self) -> None:
        # spec §3 precedence: m1's B1 is the post's code; m5 withholds D1 and says why.
        result = self.pipeline.analyze("Aferin sana aptal, yine her şeyi berbat ettin.")
        self.assertIs(result.signals["m1_lexicon"]["lexicon_hit"], True)
        self.assertEqual(result.signals["m5_sarcasm"]["matched_rules"], [])
        self.assertEqual([e["reason"] for e in result.signals["m5_sarcasm"]["excluded"]], ["X_EXPLICIT_CONTENT"])
        self.assertEqual(sorted(s.code.value for s in result.fired()), ["B1"])
        self.assertIn("[m5_sarcasm] D1 withheld: m1_lexicon found explicit content, which takes precedence (spec §3)",
                      result.notes)

    def test_benign_sarcasm_and_sincere_praise_leave_the_post_clean(self) -> None:
        for text in ("Harika, otobüs yine gelmedi.", "Aferin sana, sınavı geçtin."):
            with self.subTest(text=text):
                result = self.pipeline.analyze(text)
                self.assertEqual(result.fired(), [])
                self.assertEqual(result.signals["pipeline"]["degraded"], [])
                self.assertIs(result.verdict, Action.CLEAN)


class _Stub(BaseModule):
    name = ModuleName.M2_DEOBF
    provides = frozenset({"normalized_text", "form"})
    emits_spans = False
    stub = True

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput()


class _Failing(BaseModule):
    name = ModuleName.M5_SARCASM
    provides = frozenset({"content"})
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        raise RuntimeError("boom")


class _Invalid(BaseModule):
    name = ModuleName.M6_TARGET
    provides = frozenset({"target", "content"})
    emits_spans = True

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(content=[ContentScore("B4", 0.9, "m6_target@raw", span=(0, 1))])


class PipelineToDecisionSignalsTest(unittest.TestCase):
    def test_pipeline_block_has_the_shape_the_decision_layer_reads(self) -> None:
        modules = [_Stub(), _Failing(), _Invalid(), _Spy(ModuleName.M4_IMPLICIT)]
        result = Pipeline(modules=modules, config=fusion.load_config()).analyze("x")
        block = result.signals["pipeline"]
        with self.subTest(stage="INTERFACE_CONTRACT/keys"):
            self.assertEqual(set(block), PIPELINE_SIGNAL_KEYS)
        with self.subTest(stage="INTERFACE_CONTRACT/degraded"):
            self.assertEqual([d["module"] for d in block["degraded"]], ["m2_deobf", "m5_sarcasm", "m6_target"])
            for entry in block["degraded"]:
                self.assertEqual(set(entry), {"module", "kinds", "reasons"})
                self.assertTrue(set(entry["kinds"]) <= DEGRADATION_KINDS, entry["kinds"])
                self.assertTrue(entry["reasons"])
            self.assertEqual(actions.degraded_modules(result), block["degraded"])   # the consumer's reader
        with self.subTest(stage="INTERFACE_CONTRACT/emits_spans"):
            self.assertEqual(block["emits_spans"], span_declarations(modules))
            self.assertEqual(set(block["emits_spans"]), {m.name.value for m in modules})
            self.assertTrue(all(isinstance(v, bool) for v in block["emits_spans"].values()))

    def test_m2_offsets_reach_m1_and_map_every_normalized_character(self) -> None:
        """ADR-008: m2's `_offsets` has one ORIGINAL index per normalized character, non-decreasing,
        in range; it composes m0's map; m1 maps a normalized-channel hit through it to the original
        surface. Real m0, m2 and m1."""
        require_terlik(self)
        from modules.m2_deobf.module import DeobfModule
        text = "Sen s a l a k ve 5al4k mısın"
        spy = _Spy(ModuleName.M3_ENCODER)
        pipeline = Pipeline(modules=[CharSafeModule(), DeobfModule(), LexiconModule(), spy], config=fusion.load_config())
        result = pipeline.analyze(text)
        ctx = spy.seen[0]
        offsets = ctx.signals[ModuleName.M2_DEOBF.value]["_offsets"]
        with self.subTest(stage="INTERFACE_CONTRACT/m2 offsets"):
            self.assertEqual(len(offsets), len(ctx.normalized_text))
            self.assertTrue(all(isinstance(o, int) and 0 <= o < len(text) for o in offsets))
            self.assertEqual(list(offsets), sorted(offsets))
            self.assertEqual(ctx.normalized_text, "sen salak ve salak mısın")
        with self.subTest(stage="PIPELINE_MERGE/m1 spans on the normalized channel"):
            normalized = [s for s in result.signals["decision"]["channel_scores"] if s["source"].endswith("@normalized")]
            self.assertEqual([text[s["span"][0]:s["span"][1]] for s in normalized], ["s a l a k", "5al4k"])
            self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit_norm"])
        with self.subTest(stage="INTERFACE_CONTRACT/response"):
            self.assertNotIn("_offsets", result.signals["m2_deobf"])
            self.assertNotIn("_repairs", result.signals["m2_deobf"])

    def test_decision_block_has_the_keys_the_response_and_counter_read(self) -> None:
        result = Pipeline(modules=[_Spy(ModuleName.M0_CHARSAFE)], config=fusion.load_config()).analyze("x")
        decision = result.signals["decision"]
        self.assertGreaterEqual(set(decision), {"family_a", "threshold_branches", "binary_offensive",
                                                "channel_scores", "post_offensive"})
        self.assertIsInstance(decision["post_offensive"], bool)
        self.assertEqual(set(decision["binary_offensive"]) >= {"threshold", "channels", "fired", "action"}, True)


if __name__ == "__main__":
    unittest.main()
