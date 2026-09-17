"""Gate 1, tasks 5-6: end-to-end verification of the CURRENT implemented behaviour
through the REAL pipeline - real m0, real m1 (terlik), real m3 (BERTurk artifact),
the documented stubs, the shipped thresholds.yaml.

This is not a golden set. It proves that module outputs -> merge -> decision ->
verdict are connected, by asserting intermediate state at every stage, on posts
whose expected behaviour is already unambiguous in the repository.

Stages (task 6): every assertion runs in a subTest named after the stage where a
failure would originate, so one failing case reads as e.g.
"[stage=GUARD_APPLICATION]" rather than "verdict was wrong":
  MODULE_OUTPUT       what a module published (signals, notes)
  INTERFACE_CONTRACT  keys and types crossing a module boundary
  PIPELINE_MERGE      what _merge kept: content, guards, spans, per_module_ms
  DEGRADATION         signals.pipeline.degraded
  DECISION_THRESHOLD  family_a, channel_scores.fired, binary_offensive, post_offensive
  GUARD_APPLICATION   guard.active / suppressed after fusion.apply_guards
  FINAL_ACTION        verdict, driver (actions.resolve), explanation
A failure message carries the diagnostic dump of the result (diagnose()).

Oracles and labels:
  * expected verdicts are computed from the loaded config with actions.severity,
    never written as literals, so a placeholder change moves the expectation
    deliberately and visibly;
  * m3's probability on a given sentence is a property of artifact
    m3-berturk-pytorch-fp32-epoch1, not of any spec. Assertions on it are labelled
    CURRENT_ARTIFACT_OBSERVATION: they pin the artifact the threshold was derived
    on (the contract example already pins one such value);
  * BLOCKED_BY_POLICY - cases deliberately NOT asserted here:
      Q1  an A-family hit that m3 scores below threshold while m6 is a stub
          (nudge vs review under degradation);
      Q2  a non-human target guard together with a binary fire;
      Q3  the verdict on obfuscated input (m3 scores the raw text): the ZWSP case
          below asserts m0 -> m1 only and records the binary state without judging it;
      Q5  any normalized-channel span; Q6 any m6 target route (m6 is a stub).

Preconditions FAIL with a named reason (never skip): the m3 artifact and terlik.
"""
from __future__ import annotations

import importlib.util
import json
import unittest

from contracts.codes import Action, ContentCode, FormCode, GuardCode, ModuleName
from contracts.schema import AnalysisResult
from decision import actions, fusion
from modules.m3_encoder import module as m3
from modules.m3_encoder.test_unit import artifact_available
from pipeline.run import Pipeline
from pipeline.thread_counter import ThreadBlock

STUBS = ["m6_target", "m5_sarcasm"]      # registry order; m0, m2, m1, m3, m4 are not stubs


def most_severe(*candidates: Action) -> Action:
    return min(candidates, key=actions.severity)


def diagnose(result: AnalysisResult) -> str:
    """Everything a reader needs to place a failure, as one JSON blob."""
    decision = result.signals.get("decision", {})
    return json.dumps({
        "text": result.text,
        "degraded": result.signals.get("pipeline", {}).get("degraded"),
        "m0": result.signals.get("m0_charsafe"),
        "m1": result.signals.get("m1_lexicon"),
        "m3": result.signals.get("m3_encoder"),
        "content": [{"code": s.code.value, "score": s.score, "source": s.source, "span": s.span,
                     "threshold": s.threshold, "fired": s.fired} for s in result.content],
        "guards": [{"code": g.code.value, "score": g.score, "span": g.span, "active": g.active,
                    "suppressed": [c.value for c in g.suppressed]} for g in result.guards],
        "form": {"patterns": [(p.code.value, p.confidence, p.span) for p in result.form.patterns],
                 "active": [c.value for c in result.form.active]},
        "family_a": decision.get("family_a"),
        "channel_scores": decision.get("channel_scores"),
        "binary_offensive": decision.get("binary_offensive"),
        "post_offensive": decision.get("post_offensive"),
        "thread": None if result.thread is None else vars(result.thread),
        "verdict": None if result.verdict is None else result.verdict.value,
        "explanation": result.explanation,
        "notes": result.notes,
    }, ensure_ascii=False, indent=1, default=str)


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = fusion.load_config()
        cls.t = float(cls.cfg["binary_offensive"]["threshold"])
        cls.binary_action = Action(cls.cfg["binary_offensive"]["action"])
        cls.a1_action = Action(cls.cfg["categories"]["A1"]["action"])
        cls.pipeline = Pipeline()      # the real registry, the real config

    def setUp(self) -> None:
        if not artifact_available():
            self.fail("PRECONDITION: m3 artifact files or torch/transformers missing; the real pipeline cannot "
                      "be verified on this machine (eval/implementation_status.json m3_encoder.preconditions)")
        # find_spec, not an import: tests/ is core (stdlib + pyyaml only, rule 6); m1 owns terlik.
        if importlib.util.find_spec("terlik") is None:
            self.fail("PRECONDITION: terlik is not importable; m1_lexicon cannot run on this machine")

    # -- shared stage checks ------------------------------------------------------------
    def check_preconditions_held(self, result: AnalysisResult) -> None:
        """m1 and m3 must have RUN. If they are degraded, the failure is a precondition
        or a MODULE_OUTPUT failure, never a decision-layer one."""
        degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
        with self.subTest(stage="DEGRADATION/preconditions"):
            for name in ("m1_lexicon", "m3_encoder", "m0_charsafe", "m4_implicit"):
                self.assertNotIn(name, degraded, f"{name} degraded: {degraded.get(name)}\n{diagnose(result)}")
            self.assertEqual([d["module"] for d in result.signals["pipeline"]["degraded"]], STUBS, diagnose(result))
            self.assertTrue(all(d["kinds"] == ["stub"] for d in degraded.values()), diagnose(result))

    def check_interfaces(self, result: AnalysisResult) -> None:
        with self.subTest(stage="INTERFACE_CONTRACT"):
            self.assertEqual(set(result.signals["m1_lexicon"]),
                             {"lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "matched_roots", "engine"})
            self.assertEqual(set(result.signals["m3_encoder"]), {"raw_score", "artifact"})
            self.assertEqual(result.signals["m3_encoder"]["artifact"], m3.ARTIFACT_ID)
            self.assertNotIn("_offsets", result.signals["m0_charsafe"])
            self.assertNotIn("channels", result.signals)
            self.assertEqual(len(result.per_module_ms), 7)
        with self.subTest(stage="DECISION_THRESHOLD/binary consistency"):
            binary = result.signals["decision"]["binary_offensive"]
            score = result.signals["m3_encoder"]["raw_score"]
            self.assertEqual(binary["channels"]["raw"]["score"], score)
            self.assertIs(binary["fired"], score >= self.t)
            self.assertEqual(binary["threshold"], self.t)

    def check_binary(self, result: AnalysisResult, fired: bool) -> None:
        """CURRENT_ARTIFACT_OBSERVATION: pins what artifact m3-berturk-pytorch-fp32-epoch1
        does on this sentence. A different artifact must re-derive the threshold and
        re-pin these (MANIFEST.md: one thresholds file per artifact)."""
        with self.subTest(stage="DECISION_THRESHOLD/binary", label="CURRENT_ARTIFACT_OBSERVATION"):
            self.assertIs(result.signals["decision"]["binary_offensive"]["fired"], fired,
                          f"artifact {m3.ARTIFACT_ID}\n{diagnose(result)}")

    def check_verdict(self, result: AnalysisResult, expected: Action, driver: object) -> None:
        with self.subTest(stage="FINAL_ACTION"):
            got_verdict, got_driver = actions.resolve(result, self.cfg)
            self.assertIs(result.verdict, expected, diagnose(result))
            self.assertIs(got_verdict, expected, diagnose(result))
            if isinstance(driver, ContentCode):
                self.assertEqual(getattr(got_driver, "code", None), driver, diagnose(result))
            else:
                self.assertEqual(got_driver, driver, diagnose(result))
            # Every verdict today is under degradation (three stubs): the explanation says so.
            self.assertIn("değerlendirme eksik", result.explanation, diagnose(result))

    def expected_offensive_verdict(self, *extra: Action) -> tuple[Action, object]:
        """A1 fired plus the binary fired: the more severe configured action wins; on
        equal severity actions.resolve keeps the content driver (it is visited first)."""
        candidates = [(self.a1_action, ContentCode.A1), (self.binary_action, "binary_offensive")]
        candidates += [(a, "thread") for a in extra]
        best = candidates[0]
        for action, driver in candidates[1:]:
            if actions.severity(action) < actions.severity(best[0]):
                best = (action, driver)
        return best

    # -- cases --------------------------------------------------------------------------
    def test_clean_sentence_is_reviewed_only_because_of_the_stubs(self) -> None:
        text = "Bu bir test cumlesi"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertFalse(result.signals["m0_charsafe"]["charsafe_changed"], diagnose(result))
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
            self.assertEqual(result.signals["m1_lexicon"]["matched_roots"], [], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual(result.content, [], diagnose(result))
            self.assertEqual(result.guards, [], diagnose(result))
            self.assertIsNone(result.target)
            # "cumlesi" is ASCII-flattened Turkish: m2 restores "cümlesi" on the parallel channel (DEASCII,
            # spec §4) and reports it with the original span; nothing else in the sentence changes.
            self.assertEqual([(p.code, p.source, text[p.span[0]:p.span[1]]) for p in result.form.patterns],
                             [(FormCode.DEASCII, "m2_deobf", "cumlesi")], diagnose(result))
            self.assertEqual(result.signals["m2_deobf"]["codes"], ["DEASCII"], diagnose(result))
            self.assertNotIn("_repairs", result.signals["m2_deobf"])                  # internal, stripped
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit_norm"], diagnose(result))
        self.check_binary(result, fired=False)      # the frozen contract example pins raw_score 0.021 here
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertIsNone(result.signals["decision"]["family_a"])
            self.assertFalse(result.signals["decision"]["post_offensive"])
        self.check_verdict(result, actions.DEGRADED_ACTION, "degraded")
        with self.subTest(stage="FINAL_ACTION/explanation"):
            self.assertTrue(result.explanation.startswith("Karar verilemedi"), result.explanation)
            for name in STUBS:
                self.assertIn(name, result.explanation)

    def test_explicit_insult_fires_lexicon_and_binary(self) -> None:
        text = "Onlar aptallar"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit_raw"], diagnose(result))
            self.assertTrue(result.signals["m1_lexicon"]["matched_roots"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual([(s.code, s.source, s.span) for s in result.content],
                             [(ContentCode.A1, "m1_lexicon@raw", (6, 14))], diagnose(result))
            self.assertEqual(text[6:14], "aptallar")
            self.assertEqual(result.guards, [], diagnose(result))
        with self.subTest(stage="DECISION_THRESHOLD"):
            family_a = result.signals["decision"]["family_a"]
            self.assertEqual(family_a["resolved_as"], "none", diagnose(result))          # m6 is a stub: no target
            self.assertEqual(family_a["code"], self.cfg["family_a"]["by_target"]["none"], diagnose(result))
            score = result.content[0]
            self.assertEqual(score.threshold, float(self.cfg["categories"]["A1"]["threshold"]), diagnose(result))
            self.assertGreaterEqual(score.score, score.threshold, diagnose(result))
            # m1 scans both channels (raw and m2's normalized), so two A1 scores reach the decision layer.
            self.assertEqual(sorted((b["code"], b["source"]) for b in result.signals["decision"]["threshold_branches"]),
                             [("A1", "m1_lexicon@normalized"), ("A1", "m1_lexicon@raw")], diagnose(result))
        self.check_binary(result, fired=True)
        with self.subTest(stage="GUARD_APPLICATION"):
            # channel_scores are recorded AFTER guards ran: `fired` here means "not suppressed".
            self.assertEqual(result.guards, [])
            channel = result.signals["decision"]["channel_scores"]
            self.assertEqual(sorted((c["code"], c["source"], c["fired"]) for c in channel),
                             [("A1", "m1_lexicon@normalized", True), ("A1", "m1_lexicon@raw", True)], diagnose(result))
            self.assertTrue(result.content[0].fired, diagnose(result))
        with self.subTest(stage="FINAL_ACTION/post_offensive"):
            self.assertTrue(result.signals["decision"]["post_offensive"], diagnose(result))
        verdict, driver = self.expected_offensive_verdict()
        self.check_verdict(result, verdict, driver)

    def test_collision_word_raises_a_guard_and_no_content(self) -> None:
        text = "SIKINTI YOK"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertIn(FormCode.DOTLESS_I, result.form.codes(), diagnose(result))
            self.assertTrue(result.signals["m0_charsafe"]["charsafe_changed"], diagnose(result))
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual(result.content, [], diagnose(result))
            self.assertEqual([(g.code, g.span) for g in result.guards],
                             [(GuardCode.SUBSTRING_COLLISION, (0, 7))], diagnose(result))
            self.assertEqual(text[0:7], "SIKINTI")
        with self.subTest(stage="GUARD_APPLICATION"):
            guard = result.guards[0]
            threshold = float(self.cfg["guards"][guard.code.value]["threshold"])
            self.assertEqual(guard.threshold, threshold)
            self.assertIs(guard.active, guard.score >= threshold, diagnose(result))
            self.assertEqual(guard.suppressed, [])                       # nothing to suppress
        with self.subTest(stage="DECISION_THRESHOLD/form"):
            min_confidence = float(self.cfg["form"]["min_confidence"])
            expected_active = [c for c in result.form.codes()
                               if max(p.confidence for p in result.form.patterns if p.code is c) >= min_confidence]
            self.assertEqual(result.form.active, expected_active, diagnose(result))
        self.check_binary(result, fired=False)
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertFalse(result.signals["decision"]["post_offensive"], diagnose(result))
        self.check_verdict(result, actions.DEGRADED_ACTION, "degraded")

    def test_non_overlapping_collision_guard_suppresses_nothing(self) -> None:
        text = "Sen bir gerizekalısın, amcam da öyle"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual([(s.code, s.span) for s in result.content], [(ContentCode.A1, (8, 21))],
                             diagnose(result))
            self.assertEqual(text[8:21], "gerizekalısın")
            self.assertEqual([(g.code, g.span) for g in result.guards],
                             [(GuardCode.SUBSTRING_COLLISION, (23, 28))], diagnose(result))
            self.assertEqual(text[23:28], "amcam")
        with self.subTest(stage="DECISION_THRESHOLD"):
            score = result.content[0]
            self.assertEqual(score.threshold, float(self.cfg["categories"]["A1"]["threshold"]), diagnose(result))
            self.assertGreaterEqual(score.score, score.threshold, diagnose(result))
        with self.subTest(stage="GUARD_APPLICATION"):
            guard = result.guards[0]
            self.assertTrue(guard.active, diagnose(result))
            self.assertEqual(guard.suppressed, [], diagnose(result))          # ADR-001: spans do not overlap
            self.assertTrue(result.content[0].fired, diagnose(result))
        self.check_binary(result, fired=True)
        verdict, driver = self.expected_offensive_verdict()
        self.check_verdict(result, verdict, driver)

    def test_zero_width_inside_a_word_maps_the_span_through_m0(self) -> None:
        """m0 -> m1 through the pipeline. The verdict and the binary state are
        BLOCKED_BY_POLICY (Q3: m3 sees the raw text) and are NOT asserted; the
        binary block is only checked for internal consistency (check_interfaces)."""
        text = "ap​tal herif"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertEqual([(p.code, p.span) for p in result.form.patterns], [(FormCode.ZERO_WIDTH, (2, 3))],
                             diagnose(result))
            self.assertFalse(result.signals["m0_charsafe"]["offsets_identity"], diagnose(result))
            self.assertEqual(result.signals["m0_charsafe"]["invisible_removed"], 1, diagnose(result))
            self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit_raw"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual([(s.code, s.span) for s in result.content], [(ContentCode.A1, (0, 6))],
                             diagnose(result))
            self.assertEqual(text[0:6], "ap​tal")                     # ORIGINAL span, invisible char inside
        with self.subTest(stage="DECISION_THRESHOLD/form"):
            self.assertIn(FormCode.ZERO_WIDTH, result.form.active, diagnose(result))
        with self.subTest(stage="GUARD_APPLICATION"):
            self.assertTrue(result.content[0].fired, diagnose(result))          # no guard on this post
        # Recorded, not judged (Q3): what m3 did with the raw text on this run.
        binary = result.signals["decision"]["binary_offensive"]
        self.assertIn(binary["fired"], (True, False), diagnose(result))

    def test_third_offensive_post_from_the_same_sender_escalates(self) -> None:
        pipeline = Pipeline()          # its own counter: history must not leak between tests
        block = ThreadBlock("u1", "u2", "t1")
        min_repeats = int(self.cfg["thread"]["min_repeats"])
        results = [pipeline.analyze("Onlar aptallar", thread_block=block) for _ in range(min_repeats)]
        for result in results:
            self.check_preconditions_held(result)
        with self.subTest(stage="PIPELINE_MERGE/thread"):
            self.assertEqual([r.thread.repeat_count for r in results], list(range(1, min_repeats + 1)))
            self.assertTrue(all(r.thread.same_target for r in results))
            self.assertEqual([r.thread.fired for r in results], [False] * (min_repeats - 1) + [True],
                             diagnose(results[-1]))
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertTrue(all(r.signals["decision"]["post_offensive"] for r in results))
        first_verdict, first_driver = self.expected_offensive_verdict()
        self.check_verdict(results[0], first_verdict, first_driver)
        last_verdict, last_driver = self.expected_offensive_verdict(Action(self.cfg["thread"]["action"]))
        self.check_verdict(results[-1], last_verdict, last_driver)
        after = pipeline.analyze("Bu bir test cumlesi", thread_block=block)
        with self.subTest(stage="FINAL_ACTION/clean post after abuse"):
            self.assertEqual(after.thread.repeat_count, min_repeats, diagnose(after))   # history is a fact ...
            self.assertFalse(after.thread.fired, diagnose(after))                      # ... never an escalation
            self.assertIs(after.verdict, actions.DEGRADED_ACTION, diagnose(after))

    def test_response_is_bounded_and_serialisable(self) -> None:
        result = self.pipeline.analyze("ap​tal herif " * 20)
        data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(set(data), set(AnalysisResult(text="").to_dict()))
        self.assertNotIn("_offsets", json.dumps(data))
        self.assertNotIn("channels", data["signals"])


if __name__ == "__main__":
    unittest.main()
