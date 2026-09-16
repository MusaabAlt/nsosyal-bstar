from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout

from contracts.codes import Action, ContentCode, GuardCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import AnalysisResult, ContentScore, GuardResult
from decision import fusion
from pipeline import run
from pipeline.run import Pipeline


class _Scorer(BaseModule):
    """Test double: emits a fixed, whole-post score (no span)."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content"})
    emits_spans = False

    def __init__(self, value: float, **decision_fields) -> None:
        super().__init__()
        self.value = value
        self.decision_fields = decision_fields

    def _run(self, ctx: Context) -> ModuleOutput:
        # A1 is the family-A carrier (ADR-005); with no target it is decided as A1.
        return ModuleOutput(content=[ContentScore(ContentCode.A1, self.value, "m1_lexicon@raw",
                                                  **self.decision_fields)])


class _Charsafe(BaseModule):
    name = ModuleName.M0_CHARSAFE
    provides = frozenset({"charsafe_text"})

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(charsafe_text=ctx.text.lower())


class _Spy(BaseModule):
    name = ModuleName.M3_ENCODER
    provides = frozenset({"guards"})

    def __init__(self) -> None:
        super().__init__()
        self.seen: list[Context] = []

    def _run(self, ctx: Context) -> ModuleOutput:
        self.seen.append(ctx)
        # Also returns an undeclared field, which must be dropped.
        return ModuleOutput(guards=[GuardResult(GuardCode.HOMONYM, 0.1, "m3_encoder")], normalized_text="sneaky")


class PipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())
        self.cfg["categories"]["A1"].update(threshold=0.5, action="block")
        self.cfg["guards"]["HOMONYM"]["threshold"] = 0.5
        self.cfg["fast_path"].update(enabled=True, margin=0.3, requires=["m0_charsafe", "m1_lexicon"])

    def test_default_pipeline_on_clean_sentence(self) -> None:
        text = "Bu bir test cumlesi"
        result = Pipeline().analyze(text)
        self.assertEqual(result.text, text)
        # Five stub modules: the judgement is incomplete, so never clean (Phase 9).
        self.assertIs(result.verdict, Action.REVIEW)
        self.assertEqual(len(result.per_module_ms), 7)
        self.assertNotIn("channels", result.signals)  # bounded response (decision 17)
        self.assertEqual(len(result.artifact_hash), 64)
        data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(set(data), set(AnalysisResult(text="").to_dict()))

    def test_downstream_module_sees_charsafe_text_and_signals(self) -> None:
        spy = _Spy()
        Pipeline(modules=[_Charsafe(), spy], config=self.cfg).analyze("ABC")
        ctx = spy.seen[0]
        self.assertEqual(ctx.text, "ABC")
        self.assertEqual(ctx.charsafe_text, "abc")
        self.assertIn("m0_charsafe", ctx.signals)

    def test_stub_modules_are_degraded_and_named(self) -> None:
        result = Pipeline().analyze("Bu bir test cumlesi")
        stubs = ["m2_deobf", "m6_target", "m5_sarcasm"]  # registry order; m1, m3 and m4 are not stubs
        # m3 degrades with another kind when its git-ignored artifact is absent on this machine.
        degraded = [d for d in result.signals["pipeline"]["degraded"] if d["module"] != "m3_encoder"]
        self.assertEqual([d["module"] for d in degraded], stubs)
        self.assertTrue(all(d["kinds"] == ["stub"] for d in degraded))
        self.assertTrue(result.notes[0].startswith("[pipeline] DEGRADED"))
        for name in stubs:
            self.assertIn(name, result.explanation)
        self.assertTrue(result.explanation.startswith("Karar verilemedi"))

    def test_clean_is_reachable_only_without_degradation(self) -> None:
        result = Pipeline(modules=[_Charsafe()], config=self.cfg).analyze("x")
        self.assertEqual(result.signals["pipeline"]["degraded"], [])
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertFalse(any("DEGRADED" in n for n in result.notes))

    def test_undeclared_fields_are_dropped(self) -> None:
        downstream = _Spy()
        result = Pipeline(modules=[_Spy(), downstream], config=self.cfg).analyze("x")
        self.assertIsNone(downstream.seen[0].normalized_text)
        self.assertTrue(any("undeclared" in n for n in result.notes))

    def test_module_decision_fields_are_cleared(self) -> None:
        cheater = _Scorer(0.1, threshold=0.0, fired=True)
        result = Pipeline(modules=[cheater], config=self.cfg).analyze("x")
        self.assertIs(result.verdict, Action.CLEAN)
        self.assertTrue(any("decision-owned" in n for n in result.notes))

    def test_fast_path_skips_remaining_modules(self) -> None:
        spy = _Spy()
        result = Pipeline(modules=[_Charsafe(), _Scorer(0.95), spy], config=self.cfg).analyze("x")
        self.assertTrue(result.fast_path)
        self.assertEqual(spy.seen, [])
        self.assertIs(result.verdict, Action.BLOCK)

    def test_no_fast_path_below_margin(self) -> None:
        spy = _Spy()
        result = Pipeline(modules=[_Charsafe(), _Scorer(0.6), spy], config=self.cfg).analyze("x")
        self.assertFalse(result.fast_path)
        self.assertEqual(len(spy.seen), 1)
        self.assertIs(result.verdict, Action.BLOCK)

    def test_failing_module_degrades_not_aborts(self) -> None:
        class Broken(_Scorer):
            def _run(self, ctx: Context) -> ModuleOutput:
                raise ValueError("bad input")

        result = Pipeline(modules=[_Charsafe(), Broken(0.0)], config=self.cfg).analyze("x")
        self.assertIs(result.verdict, Action.REVIEW)
        self.assertTrue(any("degraded" in n for n in result.notes))

    def test_cli_prints_contract_json(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(run.main(["Bu bir test cumlesi", "--compact"]), 0)
        data = json.loads(buffer.getvalue())
        self.assertEqual(data["verdict"], "review")  # stubs: judgement incomplete


class _InitBoom(BaseModule):
    name = ModuleName.M5_SARCASM
    provides = frozenset({"content"})

    def __init__(self) -> None:
        raise RuntimeError("init crash")


class _Emit(BaseModule):
    """Returns whatever ModuleOutput it was given."""

    name = ModuleName.M3_ENCODER
    provides = frozenset({"content", "guards"})
    emits_spans = False

    def __init__(self, out: ModuleOutput) -> None:
        super().__init__()
        self.out = out

    def _run(self, ctx: Context) -> ModuleOutput:
        return self.out


class RobustnessTest(unittest.TestCase):
    """W1/W2/W4: nothing a module does crashes a request."""

    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())

    def test_protocol_module_that_raises_does_not_crash(self) -> None:
        class RawModule:
            name = ModuleName.M6_TARGET
            version = "0"
            provides = frozenset({"target"})

            def load(self) -> None:
                return None

            def process(self, ctx: Context) -> ModuleOutput:
                raise RuntimeError("raw crash")

        result = Pipeline(modules=[_Charsafe(), RawModule()], config=self.cfg).analyze("x")
        self.assertIn("m6_target", result.per_module_ms)
        self.assertTrue(any("process raised RuntimeError: raw crash" in n for n in result.notes))
        self.assertTrue(any("degraded" in n for n in result.notes))

    def test_module_load_that_raises_does_not_crash(self) -> None:
        class BadLoad(_Charsafe):
            def load(self) -> None:
                raise OSError("missing artifact")

        result = Pipeline(modules=[BadLoad()], config=self.cfg).analyze("x")
        self.assertTrue(any("load failed: OSError: missing artifact" in n for n in result.notes))

    def test_module_construction_failure_does_not_crash(self) -> None:
        entries = (run.registry.RegistryEntry(ModuleName.M0_CHARSAFE, "modules.m0_charsafe.module:CharSafeModule"),
                   run.registry.RegistryEntry(ModuleName.M5_SARCASM, "tests.test_pipeline:_InitBoom"))
        modules = run.build_modules_safely(entries)
        result = Pipeline(modules=modules, config=self.cfg).analyze("Bu bir test")
        self.assertIn("m0_charsafe", result.per_module_ms)
        self.assertTrue(result.signals["m0_charsafe"]["offsets_identity"])
        self.assertTrue(any("construction failed: RuntimeError: init crash" in n for n in result.notes))

    def test_malformed_code_is_dropped_not_crashing(self) -> None:
        result = Pipeline(modules=[_Emit(ModuleOutput(content=[ContentScore("A2", 0.9, "m3_encoder@raw")]))],
                          config=self.cfg).analyze("x")
        self.assertEqual(result.content, [])
        self.assertTrue(any("not a ContentScore with a ContentCode" in n for n in result.notes))

    def test_nan_score_is_an_error_not_clean(self) -> None:
        nan = float("nan")
        result = Pipeline(modules=[_Emit(ModuleOutput(content=[ContentScore(ContentCode.A3, nan, "m3_encoder@raw")]))],
                          config=self.cfg).analyze("x")
        self.assertEqual(result.content, [])
        self.assertTrue(any("not a finite number (treated as degradation, not as clean)" in n for n in result.notes))
        self.assertTrue(any("degraded" in n for n in result.notes))

    def test_source_naming_another_module_is_dropped(self) -> None:
        out = ModuleOutput(guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon")])
        result = Pipeline(modules=[_Emit(out)], config=self.cfg).analyze("x")
        self.assertEqual(result.guards, [])
        self.assertTrue(any("names a different module" in n for n in result.notes))

    def test_span_outside_text_is_dropped(self) -> None:
        out = ModuleOutput(content=[ContentScore(ContentCode.A2, 0.9, "m3_encoder@raw", span=(0, 99))])
        result = Pipeline(modules=[_Emit(out)], config=self.cfg).analyze("kisa")
        self.assertEqual(result.content, [])

    def test_decision_failure_does_not_crash(self) -> None:
        broken = copy.deepcopy(self.cfg)
        del broken["form"]  # apply_form always reads it
        result = Pipeline(modules=[_Charsafe()], config=broken).analyze("x")
        self.assertIsNone(result.verdict)
        self.assertTrue(result.explanation.startswith("Karar verilemedi"))
        self.assertTrue(any("decision layer failed" in n for n in result.notes))

    def test_module_cannot_mutate_another_modules_signals(self) -> None:
        from modules.m0_charsafe.module import CharSafeModule

        class Vandal(BaseModule):
            name = ModuleName.M2_DEOBF
            provides = frozenset({"normalized_text"})

            def _run(self, ctx: Context) -> ModuleOutput:
                ctx.signals["m0_charsafe"]["_offsets"].clear()
                return ModuleOutput()

        class Reader(BaseModule):
            name = ModuleName.M1_LEXICON
            provides = frozenset({"content"})
            emits_spans = False
            seen: list = []

            def _run(self, ctx: Context) -> ModuleOutput:
                Reader.seen.append(list(ctx.signals["m0_charsafe"]["_offsets"]))
                return ModuleOutput()

        result = Pipeline(modules=[CharSafeModule(), Vandal(), Reader()], config=self.cfg).analyze("merhaba")
        self.assertEqual(Reader.seen, [[0, 1, 2, 3, 4, 5, 6]])
        self.assertTrue(any("[m2_deobf] AttributeError" in n for n in result.notes))

    def test_internal_signals_stay_out_of_the_response(self) -> None:
        from modules.m0_charsafe.module import CharSafeModule

        long_post = "Bu bir test cumlesi " * 250
        result = Pipeline(modules=[CharSafeModule()], config=self.cfg).analyze(long_post)
        self.assertNotIn("_offsets", result.signals["m0_charsafe"])
        self.assertTrue(result.signals["m0_charsafe"]["offsets_identity"])
        short = Pipeline(modules=[CharSafeModule()], config=self.cfg).analyze("Bu bir test cumlesi")
        size = lambda r: len(json.dumps(r.to_dict()["signals"]["m0_charsafe"]))
        self.assertEqual(size(result), size(short))

    def test_response_signals_do_not_grow_with_post_length(self) -> None:
        # Decision 17: no copy of the post in signals; only `text` itself scales.
        size = lambda text: len(json.dumps(Pipeline(config=self.cfg).analyze(text).to_dict()["signals"]))
        self.assertEqual(size("Bu bir test cumlesi"), size("Bu bir test cumlesi " * 250))

    def test_nested_signal_payload_is_read_only(self) -> None:
        frozen = run.deep_freeze({"a": {"b": [1, {"c": 2}]}})
        with self.assertRaises(TypeError):
            frozen["a"]["x"] = 1  # type: ignore[index]
        with self.assertRaises(TypeError):
            frozen["a"]["b"][1]["c"] = 3  # type: ignore[index]

    def test_artifact_hash_covers_in_memory_config(self) -> None:
        modules = [_Charsafe()]
        changed = copy.deepcopy(self.cfg)
        changed["categories"]["A1"]["threshold"] = 0.99
        self.assertNotEqual(Pipeline(modules=modules, config=changed).artifact_hash,
                            Pipeline(modules=modules, config=self.cfg).artifact_hash)
        self.assertEqual(run.artifact_hash(self.cfg, modules), Pipeline(modules=modules, config=self.cfg).artifact_hash)


class DegradationTest(unittest.TestCase):
    """Phase 9 policy: an unavailable module means the system cannot judge."""

    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())

    def assertDegradedReview(self, result: AnalysisResult, module: str, kind: str) -> None:
        self.assertIs(result.verdict, Action.REVIEW)
        entry = next((d for d in result.signals["pipeline"]["degraded"] if d["module"] == module), None)
        self.assertIsNotNone(entry, result.signals["pipeline"])
        self.assertIn(kind, entry["kinds"])
        self.assertTrue(entry["reasons"])
        self.assertIn(module, result.explanation)
        self.assertTrue(result.explanation.startswith("Karar verilemedi"))
        self.assertNotIn("temiz kabul edildi", result.explanation)
        self.assertNotIn("bulunmadı.", result.explanation)

    def test_stub(self) -> None:
        class Stub(_Charsafe):
            stub = True

        self.assertDegradedReview(Pipeline(modules=[Stub()], config=self.cfg).analyze("x"), "m0_charsafe", "stub")

    def test_run_raises(self) -> None:
        class Broken(_Scorer):
            def _run(self, ctx: Context) -> ModuleOutput:
                raise ValueError("bad input")

        self.assertDegradedReview(Pipeline(modules=[Broken(0.0)], config=self.cfg).analyze("x"),
                                  "m1_lexicon", "failed")

    def test_protocol_module_raises(self) -> None:
        class RawModule:
            name = ModuleName.M6_TARGET
            version = "0"
            provides = frozenset({"target"})

            def load(self) -> None:
                return None

            def process(self, ctx: Context) -> ModuleOutput:
                raise RuntimeError("raw crash")

        self.assertDegradedReview(Pipeline(modules=[RawModule()], config=self.cfg).analyze("x"), "m6_target", "failed")

    def test_construction_failure(self) -> None:
        entries = (run.registry.RegistryEntry(ModuleName.M5_SARCASM, "tests.test_pipeline:_InitBoom"),)
        result = Pipeline(modules=run.build_modules_safely(entries), config=self.cfg).analyze("x")
        self.assertDegradedReview(result, "m5_sarcasm", "failed")

    def test_load_failure(self) -> None:
        class BadLoad(_Charsafe):
            def load(self) -> None:
                raise OSError("missing artifact")

        self.assertDegradedReview(Pipeline(modules=[BadLoad()], config=self.cfg).analyze("x"), "m0_charsafe", "failed")

    def test_invalid_output_items(self) -> None:
        for label, score in (("nan", float("nan")), ("none", None), ("above one", 1.5), ("below zero", -0.2)):
            with self.subTest(score=label):
                out = ModuleOutput(content=[ContentScore(ContentCode.A3, score, "m3_encoder@raw")])
                result = Pipeline(modules=[_Emit(out)], config=self.cfg).analyze("x")
                self.assertDegradedReview(result, "m3_encoder", "invalid_output")
                self.assertEqual(result.content, [])
        malformed = ModuleOutput(content=[ContentScore("A2", 0.9, "m3_encoder@raw")])
        self.assertDegradedReview(Pipeline(modules=[_Emit(malformed)], config=self.cfg).analyze("x"),
                                  "m3_encoder", "invalid_output")

    def test_severe_verdict_stands_but_says_incomplete(self) -> None:
        self.cfg["categories"]["A1"].update(threshold=0.5, action="block")

        class Stub(_Charsafe):
            stub = True

        result = Pipeline(modules=[Stub(), _Scorer(0.9)], config=self.cfg).analyze("x")
        self.assertIs(result.verdict, Action.BLOCK)
        self.assertIn("ancak değerlendirme eksik", result.explanation)
        self.assertIn("m0_charsafe", result.explanation)


class _SpanLexicon(BaseModule):
    """m1-like double that declares spans and raises a collision guard."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content", "guards"})
    emits_spans = True

    def __init__(self, score_span, guard_span) -> None:
        super().__init__()
        self.score_span, self.guard_span = score_span, guard_span

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(
            content=[ContentScore(ContentCode.A1, 0.99, "m1_lexicon@raw", span=self.score_span)],
            guards=[GuardResult(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon", evidence="'am' inside 'amcam'",
                                span=self.guard_span)])


class SpanEnforcementTest(unittest.TestCase):
    """Phase 10: the no-span fallback had become a bypass (ADR-001)."""

    TEXT = "<insult> amcam"

    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())
        self.cfg["categories"]["A1"]["action"] = "block"

    def analyze(self, score_span, guard_span) -> AnalysisResult:
        return Pipeline(modules=[_Charsafe(), _SpanLexicon(score_span, guard_span)], config=self.cfg).analyze(self.TEXT)

    def test_insult_plus_amcam_with_spans_blocks_because_spans_do_not_overlap(self) -> None:
        result = self.analyze((0, 8), (9, 14))
        self.assertIs(result.verdict, Action.BLOCK)
        [guard] = result.guards
        self.assertTrue(guard.active)
        self.assertEqual(guard.suppressed, [])
        self.assertEqual(result.signals["pipeline"]["degraded"], [])

    def test_insult_plus_amcam_guard_without_span_blocks_because_guard_is_dropped(self) -> None:
        result = self.analyze((0, 8), None)
        self.assertIs(result.verdict, Action.BLOCK)
        self.assertEqual(result.guards, [])
        self.assertTrue(any("dropped guard SUBSTRING_COLLISION: no span although the module emits spans" in n
                            for n in result.notes))
        [entry] = result.signals["pipeline"]["degraded"]
        self.assertEqual((entry["module"], entry["kinds"]), ("m1_lexicon", ["invalid_output"]))
        self.assertIn("ancak değerlendirme eksik", result.explanation)

    def test_fully_spanless_output_is_dropped_and_never_clean(self) -> None:
        result = self.analyze(None, None)
        self.assertEqual((result.content, result.guards), ([], []))
        self.assertIs(result.verdict, Action.REVIEW)

    def test_undeclared_module_must_emit_spans(self) -> None:
        class Undeclared(_SpanLexicon):
            emits_spans = None  # "not declared": spans are required, no fallback

        result = Pipeline(modules=[Undeclared(None, None)], config=self.cfg).analyze(self.TEXT)
        self.assertEqual(result.content, [])
        self.assertIs(result.verdict, Action.REVIEW)

    def test_decision_layer_refuses_fallback_for_span_emitting_module(self) -> None:
        score = ContentScore(ContentCode.A2, 0.99, "m1_lexicon@raw")
        guard = GuardResult(GuardCode.SUBSTRING_COLLISION, 0.99, "m1_lexicon")
        self.assertFalse(fusion.guard_applies(guard, score, self.cfg, {"m1_lexicon": True}))
        self.assertTrue(fusion.guard_applies(guard, score, self.cfg, {"m1_lexicon": False}))


if __name__ == "__main__":
    unittest.main()
