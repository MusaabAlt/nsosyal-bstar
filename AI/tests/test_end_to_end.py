"""Gate 1, tasks 5-6: end-to-end verification of the CURRENT implemented behaviour
through the REAL pipeline - real m0, m2, m6, m1 (terlik), m3 (the deployed rule-v4
multi-head artifact: binary + A heads), m4 (stage 1), m5 (Stage-1 deterministic rules)
and the shipped thresholds.yaml. No module is a stub since 2026-09-19.

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
  * m3's probabilities on a given sentence are properties of artifact
    m3-berturk-multihead-a-rule-v4-20260918-163728, not of any spec. Assertions on them
    (the binary head against binary_offensive, the A head against the placeholder A rows)
    are labelled CURRENT_ARTIFACT_OBSERVATION: they pin the artifact the binary threshold
    was derived on, and were re-pinned on 2026-09-19 when rule-v4 replaced the baseline;
  * m3's A head publishes an A1-carrier score on EVERY post (ADR-005), so the family-A
    record always exists; "no family A" below means no family-A code FIRED, and m1's own
    content is read by its source;
  * BLOCKED_BY_POLICY - cases deliberately NOT asserted here:
      Q2  a non-human target guard together with a binary fire;
      Q3  the verdict on obfuscated input (m3 scores the raw text): the ZWSP case
          below asserts m0 -> m1 only and records the binary state without judging it;
      Q5  any normalized-channel span.

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

STUBS: list[str] = []      # no stub since m5 Stage 1 (2026-09-19): every module runs
M4_SIGNAL_KEYS = {"stage", "stage1_input", "stage1_input_present", "m3_artifact", "stage1_derived_for",
                  "stage1_protocol", "stage1_artifact_match", "norm_minus_raw"}
FAMILY_A = {ContentCode.A1, ContentCode.A2, ContentCode.A3}


def from_module(result: AnalysisResult, module: str) -> list:
    """Fused content whose winning source is `module` (m3's A-carrier score sits beside m1's)."""
    return [s for s in result.content if s.source.startswith(module)]


def channel_scores(result: AnalysisResult, module: str) -> list[dict]:
    """Per-source, per-channel scores as decided (after thresholds and guards), for one module."""
    return [c for c in result.signals["decision"]["channel_scores"] if c["source"].startswith(module)]


def family_a_fired(result: AnalysisResult) -> list:
    return [s for s in result.fired() if s.code in FAMILY_A]


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
        "m4": result.signals.get("m4_implicit"),
        "m5": result.signals.get("m5_sarcasm"),
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
        """Every module must have RUN. A degraded module here is a precondition or a
        MODULE_OUTPUT failure (m3 without its artifact, m1 without terlik), never a
        decision-layer one."""
        degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
        with self.subTest(stage="DEGRADATION/preconditions"):
            self.assertEqual(degraded, {}, f"PRECONDITION: degraded modules\n{diagnose(result)}")
            self.assertEqual([d["module"] for d in result.signals["pipeline"]["degraded"]], STUBS, diagnose(result))

    def check_interfaces(self, result: AnalysisResult) -> None:
        with self.subTest(stage="INTERFACE_CONTRACT"):
            self.assertEqual(set(result.signals["m1_lexicon"]),
                             {"lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "matched_roots", "engine"})
            # m2 always publishes a normalized channel now, so m3 reports both scores (spec §4)
            self.assertEqual(set(result.signals["m3_encoder"]), {"raw_score", "norm_score", "artifact", "truncated_differently"})
            self.assertNotIn("_truncation", result.signals["m3_encoder"])
            self.assertEqual(result.signals["m3_encoder"]["artifact"], m3.ARTIFACT_ID)
            self.assertNotIn("_offsets", result.signals["m0_charsafe"])
            self.assertNotIn("channels", result.signals)
            self.assertEqual(len(result.per_module_ms), 7)
        with self.subTest(stage="INTERFACE_CONTRACT/m3 -> m4"):
            stage1 = result.signals["m4_implicit"]
            self.assertEqual(set(stage1), M4_SIGNAL_KEYS)
            self.assertEqual(stage1["stage"], 1)
            self.assertIs(stage1["stage1_input_present"], True)
            self.assertEqual(stage1["m3_artifact"], result.signals["m3_encoder"]["artifact"])
            self.assertEqual(stage1["stage1_derived_for"], m3.ARTIFACT_ID)
            self.assertIs(stage1["stage1_artifact_match"], True)
            published = result.signals["m3_encoder"]
            self.assertEqual(stage1["norm_minus_raw"], published["norm_score"] - published["raw_score"])
        with self.subTest(stage="DECISION_THRESHOLD/binary consistency"):
            binary = result.signals["decision"]["binary_offensive"]
            score = result.signals["m3_encoder"]["raw_score"]
            self.assertEqual(binary["channels"]["raw"]["score"], score)
            self.assertIs(binary["fired"], score > self.t)
            self.assertEqual(binary["threshold"], self.t)

    def check_binary(self, result: AnalysisResult, fired: bool) -> None:
        """CURRENT_ARTIFACT_OBSERVATION: pins what the binary head of artifact
        m3-berturk-multihead-a-rule-v4-20260918-163728 does on this sentence at its derived
        threshold. A different artifact must re-derive the threshold and re-pin these
        (MANIFEST.md: one thresholds file per artifact)."""
        with self.subTest(stage="DECISION_THRESHOLD/binary", label="CURRENT_ARTIFACT_OBSERVATION"):
            self.assertIs(result.signals["decision"]["binary_offensive"]["fired"], fired,
                          f"artifact {m3.ARTIFACT_ID}\n{diagnose(result)}")

    def check_m3_a(self, result: AnalysisResult, fired: bool) -> None:
        """CURRENT_ARTIFACT_OBSERVATION: m3's A head published its A1-carrier score on both channels
        (recoded by target, ADR-005) and whether either cleared the PLACEHOLDER family-A threshold."""
        scores = channel_scores(result, "m3_encoder")
        with self.subTest(stage="DECISION_THRESHOLD/m3 A head", label="CURRENT_ARTIFACT_OBSERVATION"):
            self.assertEqual(sorted(c["source"] for c in scores), ["m3_encoder@normalized", "m3_encoder@raw"],
                             diagnose(result))
            self.assertTrue(all(ContentCode(c["code"]) in FAMILY_A for c in scores), diagnose(result))
            self.assertIs(any(c["fired"] for c in scores), fired, diagnose(result))

    def check_verdict(self, result: AnalysisResult, expected: Action, driver: object) -> None:
        with self.subTest(stage="FINAL_ACTION"):
            got_verdict, got_driver = actions.resolve(result, self.cfg)
            self.assertIs(result.verdict, expected, diagnose(result))
            self.assertIs(got_verdict, expected, diagnose(result))
            if isinstance(driver, ContentCode):
                self.assertEqual(getattr(got_driver, "code", None), driver, diagnose(result))
            else:
                self.assertEqual(got_driver, driver, diagnose(result))
            # Nothing is degraded any more, so no explanation says the judgement is incomplete.
            self.assertNotIn("değerlendirme eksik", result.explanation, diagnose(result))

    def expected_verdict(self, code: ContentCode, *extra: Action, binary: bool = True) -> tuple[Action, object]:
        """A content hit on `code`, plus the binary when it fired: the more severe configured action wins;
        on equal severity actions.resolve keeps the content driver (it is visited first)."""
        candidates = [(Action(self.cfg["categories"][code.value]["action"]), code)]
        candidates += [(self.binary_action, "binary_offensive")] if binary else []
        candidates += [(a, "thread") for a in extra]
        best = candidates[0]
        for action, driver in candidates[1:]:
            if actions.severity(action) < actions.severity(best[0]):
                best = (action, driver)
        return best

    def expected_offensive_verdict(self, target_type: str, *extra: Action) -> tuple[Action, object]:
        """A family-A hit assigned from m6's target (ADR-005: family_a.by_target[type]) plus the binary
        fired: the more severe configured action wins; on equal severity actions.resolve keeps the
        content driver (it is visited first). `target_type` is what m6's declared rules resolve for
        the post (protocols/m6_target_guideline.md), asserted separately at the DECISION stage."""
        code = ContentCode(self.cfg["family_a"]["by_target"][target_type])
        candidates = [(Action(self.cfg["categories"][code.value]["action"]), code),
                      (self.binary_action, "binary_offensive")]
        candidates += [(a, "thread") for a in extra]
        best = candidates[0]
        for action, driver in candidates[1:]:
            if actions.severity(action) < actions.severity(best[0]):
                best = (action, driver)
        return best

    # -- cases --------------------------------------------------------------------------
    def test_clean_sentence_is_clean(self) -> None:
        text = "Bu bir test cumlesi"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertFalse(result.signals["m0_charsafe"]["charsafe_changed"], diagnose(result))
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
            self.assertEqual(result.signals["m1_lexicon"]["matched_roots"], [], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual(from_module(result, "m1_lexicon"), [], diagnose(result))
            self.assertEqual(result.fired(), [], diagnose(result))
            self.assertEqual(result.guards, [], diagnose(result))
            self.assertIsNone(result.target)
            # "cumlesi" is ASCII-flattened Turkish: m2 restores "cümlesi" on the parallel channel (DEASCII,
            # spec §4) and reports it with the original span; nothing else in the sentence changes.
            self.assertEqual([(p.code, p.source, text[p.span[0]:p.span[1]]) for p in result.form.patterns],
                             [(FormCode.DEASCII, "m2_deobf", "cumlesi")], diagnose(result))
            self.assertEqual(result.signals["m2_deobf"]["codes"], ["DEASCII"], diagnose(result))
            self.assertNotIn("_repairs", result.signals["m2_deobf"])                  # internal, stripped
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit_norm"], diagnose(result))
        self.check_binary(result, fired=False)      # the contract example pins this raw_score
        self.check_m3_a(result, fired=False)
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertEqual(result.signals["decision"]["family_a"]["resolved_as"], "none")   # m3's A carrier, target none
            self.assertEqual(family_a_fired(result), [])
            self.assertFalse(result.signals["decision"]["post_offensive"])
        self.check_verdict(result, Action.CLEAN, None)
        with self.subTest(stage="FINAL_ACTION/explanation"):
            self.assertEqual(result.explanation, "İçerikte eşiği aşan saldırgan bir kategori bulunmadı.")
            self.assertEqual(result.signals["m5_sarcasm"]["matched_rules"], [])

    def test_explicit_insult_fires_lexicon_and_binary(self) -> None:
        """M1-ROUTE-1 (protocols/m1_runtime_routing_protocol.md): "aptal" is an ordinary insult, not
        profanity. m1 still matches it and routes it to B1 (degradation); nothing reaches family A."""
        text = "Onlar aptallar"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit_raw"], diagnose(result))
            self.assertTrue(result.signals["m1_lexicon"]["matched_roots"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual([(s.code, s.source, s.span) for s in from_module(result, "m1_lexicon")],
                             [(ContentCode.B1, "m1_lexicon@raw", (6, 14))], diagnose(result))
            self.assertEqual(text[6:14], "aptallar")
            self.assertEqual(result.guards, [], diagnose(result))
        self.check_m3_a(result, fired=False)
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertEqual(family_a_fired(result), [], diagnose(result))   # an ordinary insult reaches no family A
            score = from_module(result, "m1_lexicon")[0]
            self.assertEqual(score.threshold, float(self.cfg["categories"]["B1"]["threshold"]), diagnose(result))
            self.assertGreaterEqual(score.score, score.threshold, diagnose(result))
            # m1 scans both channels (raw and m2's normalized), so two B1 scores reach the decision layer.
            self.assertEqual(sorted((b["code"], b["source"]) for b in result.signals["decision"]["threshold_branches"]
                                    if b["source"].startswith("m1_lexicon")),
                             [("B1", "m1_lexicon@normalized"), ("B1", "m1_lexicon@raw")], diagnose(result))
        self.check_binary(result, fired=True)
        with self.subTest(stage="GUARD_APPLICATION"):
            # channel_scores are recorded AFTER guards ran: `fired` here means "not suppressed".
            self.assertEqual(result.guards, [])
            channel = channel_scores(result, "m1_lexicon")
            self.assertEqual(sorted((c["code"], c["source"], c["fired"]) for c in channel),
                             [("B1", "m1_lexicon@normalized", True), ("B1", "m1_lexicon@raw", True)], diagnose(result))
            self.assertTrue(from_module(result, "m1_lexicon")[0].fired, diagnose(result))
        with self.subTest(stage="FINAL_ACTION/post_offensive"):
            self.assertTrue(result.signals["decision"]["post_offensive"], diagnose(result))
        verdict, driver = self.expected_verdict(ContentCode.B1)
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
            self.assertEqual(from_module(result, "m1_lexicon"), [], diagnose(result))
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
        self.check_m3_a(result, fired=False)
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertFalse(result.signals["decision"]["post_offensive"], diagnose(result))
        self.check_verdict(result, Action.CLEAN, None)

    def test_prayer_word_with_exclamation_carries_no_obscene_root(self) -> None:
        """Review 2026-09-18: "Amiiin!" reached A1 through m2's parallel channel ("!" read as a leet "i"
        gave "amini" = am + ini). Fixed in m2 (0.1.2), not by widening m1's clean-word guard: the
        obscene neighbours below must keep their family-A hit on this same path."""
        for text in ("Amiiin!", "Allah razı olsun amin!", "AMİN!", "amin!?"):
            with self.subTest(clean=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.check_interfaces(result)
                m1 = result.signals["m1_lexicon"]
                self.assertFalse(m1["lexicon_hit_raw"] or m1["lexicon_hit_norm"], diagnose(result))
                self.assertEqual(m1["matched_roots"], [], diagnose(result))
                self.assertEqual([s for s in result.content if s.source.startswith("m1_lexicon")], [], diagnose(result))
                self.assertTrue(any(g.code is GuardCode.SUBSTRING_COLLISION for g in result.guards), diagnose(result))
        family_a = {ContentCode.A1, ContentCode.A2, ContentCode.A3}
        for text, root in (("amına koyim", "amk"), ("aminakoyim", "amk"), ("senin amın", "am"), ("am", "am"),
                           ("am!na koyim", "amk"), ("amk!", "amk")):
            with self.subTest(obscene=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
                self.assertIn(root, result.signals["m1_lexicon"]["matched_roots"], diagnose(result))
                self.assertTrue(any(s.code in family_a and s.source.startswith("m1_lexicon") for s in result.content),
                                diagnose(result))

    def test_targeted_insult_is_b1_and_the_target_stays_on_its_own_axis(self) -> None:
        """M1-ROUTE-1: m6's target recodes family A only. A targeted ordinary insult is B1, not A2;
        the individual target is still resolved and published."""
        for text, word in (("sen aptalsın", "aptalsın"), ("Sen bir gerizekalısın", "gerizekalısın")):
            with self.subTest(text=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.check_interfaces(result)
                self.assertEqual([(s.code, text[s.span[0]:s.span[1]], s.fired) for s in from_module(result, "m1_lexicon")],
                                 [(ContentCode.B1, word, True)], diagnose(result))
                self.assertEqual(result.target.type.value, "individual", diagnose(result))
                self.check_m3_a(result, fired=False)
                self.assertEqual(family_a_fired(result), [], diagnose(result))   # B1 is never target-recoded
                self.assertTrue(result.signals["decision"]["post_offensive"], diagnose(result))

    def test_non_overlapping_collision_guard_suppresses_nothing(self) -> None:
        # A family-A root, because SUBSTRING_COLLISION covers family A: the point is that the
        # guard does not suppress it because the spans do not overlap (ADR-001), not because of
        # its code list ("gerizekalı" is B1 since M1-ROUTE-1; see the targeted-insult test).
        text = "Sen bir piçsin, amcam da öyle"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        self.check_m3_a(result, fired=True)
        with self.subTest(stage="PIPELINE_MERGE"):
            # One fused family-A entry; m1's exact-word score (1.0) wins over m3's post-level A score.
            self.assertEqual([(s.span, s.source) for s in result.content], [((8, 14), "m1_lexicon@raw")],
                             diagnose(result))   # code asserted below
            self.assertEqual(text[8:14], "piçsin")
            self.assertEqual([(g.code, g.span) for g in result.guards],
                             [(GuardCode.SUBSTRING_COLLISION, (16, 21))], diagnose(result))
            self.assertEqual(text[16:21], "amcam")
        with self.subTest(stage="DECISION_THRESHOLD"):
            # "Sen" is a second-person token: m6 resolves individual, so the carrier A1 is assigned the
            # configured individual code before thresholds (ADR-005); the guard and threshold apply to it.
            family_a = result.signals["decision"]["family_a"]
            self.assertEqual(family_a["resolved_as"], "individual", diagnose(result))
            assigned = ContentCode(self.cfg["family_a"]["by_target"]["individual"])
            self.assertEqual(family_a["code"], assigned.value, diagnose(result))
            score = result.content[0]
            self.assertIs(score.code, assigned, diagnose(result))
            self.assertEqual(score.threshold, float(self.cfg["categories"][assigned.value]["threshold"]), diagnose(result))
            self.assertGreaterEqual(score.score, score.threshold, diagnose(result))
        with self.subTest(stage="GUARD_APPLICATION"):
            guard = result.guards[0]
            self.assertTrue(guard.active, diagnose(result))
            self.assertEqual(guard.suppressed, [], diagnose(result))          # ADR-001: spans do not overlap
            self.assertTrue(result.content[0].fired, diagnose(result))
        self.check_binary(result, fired=True)
        verdict, driver = self.expected_offensive_verdict("individual")
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
            self.assertEqual([(s.code, s.span) for s in from_module(result, "m1_lexicon")], [(ContentCode.B1, (0, 6))],
                             diagnose(result))
            self.assertEqual(text[0:6], "ap​tal")                     # ORIGINAL span, invisible char inside
        with self.subTest(stage="DECISION_THRESHOLD/form"):
            self.assertIn(FormCode.ZERO_WIDTH, result.form.active, diagnose(result))
        with self.subTest(stage="GUARD_APPLICATION"):
            self.assertTrue(from_module(result, "m1_lexicon")[0].fired, diagnose(result))   # no guard on this post
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
        first_verdict, first_driver = self.expected_verdict(ContentCode.B1)
        self.check_verdict(results[0], first_verdict, first_driver)
        last_verdict, last_driver = self.expected_verdict(ContentCode.B1, Action(self.cfg["thread"]["action"]))
        self.check_verdict(results[-1], last_verdict, last_driver)
        after = pipeline.analyze("Bu bir test cumlesi", thread_block=block)
        with self.subTest(stage="FINAL_ACTION/clean post after abuse"):
            self.assertEqual(after.thread.repeat_count, min_repeats, diagnose(after))   # history is a fact ...
            self.assertFalse(after.thread.fired, diagnose(after))                      # ... never an escalation
            self.assertIs(after.verdict, Action.CLEAN, diagnose(after))

    def test_non_human_target_guard_suppresses_the_lexicon_hit(self) -> None:
        """m6 -> m1 -> decision (ADR-005 mechanics, all settled): a lexicon hit aimed at a program
        resolves target non_human, m1 raises NON_HUMAN_TARGET on its own match, and the decision
        layer suppresses that match: a family-A root (recoded from the target) and, since
        M1-ROUTE-1, an ordinary insult on B1 (thresholds.yaml lists B1 for this guard). The VERDICT
        is BLOCKED_BY_POLICY (Q2: the binary score is not suppressible by guards), so it is
        recorded, not asserted. Since rule-v4 (2026-09-19) m3's A head scores "bok" as profanity too;
        m1's guard cannot suppress another module's score (ADR-001), so that A1 fires - recorded as a
        CURRENT_ARTIFACT_OBSERVATION, reported as a known consequence, not fixed here."""
        self.assertIn("B1", self.cfg["guards"]["NON_HUMAN_TARGET"]["suppresses"])
        for text, word, code in (("Bu program tam bir bok", "bok", self.cfg["family_a"]["by_target"]["non_human"]),
                                 ("Bu program tam bir aptal", "aptal", "B1")):
            with self.subTest(text=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.check_interfaces(result)
                with self.subTest(stage="MODULE_OUTPUT/m6"):
                    self.assertEqual(result.signals["m6_target"]["target_type"], "non_human", diagnose(result))
                    self.assertEqual(result.target.type.value, "non_human", diagnose(result))
                    self.assertEqual(text[result.target.span[0]:result.target.span[1]], "program", diagnose(result))
                with self.subTest(stage="INTERFACE_CONTRACT/m6 -> m1"):
                    guards = [g for g in result.guards if g.code is GuardCode.NON_HUMAN_TARGET]
                    self.assertEqual([text[g.span[0]:g.span[1]] for g in guards], [word], diagnose(result))
                    self.assertEqual(guards[0].score, result.signals["m6_target"]["target_confidence"], diagnose(result))
                with self.subTest(stage="DECISION_THRESHOLD"):
                    family_a = result.signals["decision"]["family_a"]
                    self.assertEqual(family_a["resolved_as"], "non_human", diagnose(result))
                    self.assertEqual(family_a["code"], self.cfg["family_a"]["by_target"]["non_human"], diagnose(result))
                with self.subTest(stage="GUARD_APPLICATION"):
                    guard = [g for g in result.guards if g.code is GuardCode.NON_HUMAN_TARGET][0]
                    self.assertTrue(guard.active, diagnose(result))
                    self.assertEqual([c.value for c in guard.suppressed], [code], diagnose(result))
                    self.assertFalse(any(c["fired"] for c in channel_scores(result, "m1_lexicon")),
                                     diagnose(result))   # every m1 score suppressed
                self.check_m3_a(result, fired=code != "B1")   # "bok": m3's A1 is outside m1's guard (ADR-001)
                # Q2: whether the binary score should also yield to the guard is undecided; recorded only.
                self.assertIn(result.signals["decision"]["binary_offensive"]["fired"], (True, False), diagnose(result))

    def test_family_a_needs_a_real_word_of_the_root(self) -> None:
        """M1-PREC-1 (protocols/m1_positive_matching_precision_protocol.md, pseudo-label rule v4) end to end:
        ordinary words, party names, digits, clean words behind punctuation and letters harvested across
        words reach no family-A score and no family-A decision; genuine obscene words - hashtagged, spaced,
        glued behind punctuation, masked, leet - keep theirs, on the same path."""
        from modules.m1_lexicon.module import ROUTE_A

        family_a = {ContentCode.A1, ContentCode.A2, ContentCode.A3}
        for text in ("AK Parti kazandı", "canım sıkıldı", "amacı ne", "59 dakikada gol", "(Amin) inşallah güzel olur",
                     "T A M A M", "pc aldım", "öç almak"):
            with self.subTest(clean=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.assertFalse(set(result.signals["m1_lexicon"]["matched_roots"]) & ROUTE_A, diagnose(result))
                self.assertEqual([s for s in result.content if s.code in family_a and s.source.startswith("m1_lexicon")],
                                 [], diagnose(result))
                self.assertEqual(family_a_fired(result), [], diagnose(result))   # m3's A head stays below it too
        for text, root in (("#sikiş", "sik"), ("B O K", "bok"), ("[piç(3) nalan(5)]", "piç"), ("ta*ak geçtim", "taşak"),
                           ("s1k", "sik"), ("sıkecek", "sik")):
            with self.subTest(obscene=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.assertIn(root, result.signals["m1_lexicon"]["matched_roots"], diagnose(result))
                self.assertTrue(any(s.code in family_a and s.source.startswith("m1_lexicon") for s in result.content),
                                diagnose(result))

    def test_routed_threat_curse_topic_and_homonym(self) -> None:
        """M1-ROUTE-1 end to end: a threat is B2, a curse is B3 (NON_HUMAN_TARGET does not list them),
        topic vocabulary is a match with no content code, and the property / food compounds of
        "mal" / "domuz" are suppressed by m1's span-scoped HOMONYM guard."""
        self.assertNotIn("B2", self.cfg["guards"]["NON_HUMAN_TARGET"]["suppresses"])
        self.assertNotIn("B3", self.cfg["guards"]["NON_HUMAN_TARGET"]["suppresses"])
        for text, fired in (("öldürücem seni", [ContentCode.B2]), ("geber", [ContentCode.B3]),
                            ("meme kanseri", []), ("mal varlığı açıklandı", []), ("domuz eti", []),
                            ("mal gibi adam", [ContentCode.B1])):
            with self.subTest(text=text):
                result = self.pipeline.analyze(text)
                self.check_preconditions_held(result)
                self.assertTrue(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
                self.assertEqual([s.code for s in result.content if s.fired], fired, diagnose(result))
                self.assertEqual(family_a_fired(result), [], diagnose(result))
        for text in ("mal varlığı açıklandı", "domuz eti"):
            result = self.pipeline.analyze(text)
            homonym = [g for g in result.guards if g.code is GuardCode.HOMONYM]
            self.assertTrue(homonym and all(g.active and g.suppressed == [ContentCode.B1] for g in homonym[:1]),
                            diagnose(result))

    def test_lexicon_free_attack_reaches_the_verdict_through_m4_stage_one(self) -> None:
        """m3 -> m4 -> decision (m4 spec §4, ADR-006): a group-aimed attack with no profane root is
        caught only by stage 1, the binary_offensive row m4 owns, on the raw score m4 names as its
        input. No module emits a content code; the verdict is the binary action."""
        text = "Bu Suriyeliler ülkeyi mahvetti"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
            self.assertEqual(result.signals["m6_target"]["target_type"], "group", diagnose(result))
            self.assertEqual(result.signals["m4_implicit"]["stage1_input"],
                             self.cfg["binary_offensive"]["channels"]["raw"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            self.assertEqual(from_module(result, "m1_lexicon"), [], diagnose(result))
            self.assertEqual(result.fired(), [], diagnose(result))
            self.assertEqual(result.guards, [], diagnose(result))
        self.check_binary(result, fired=True)
        self.check_m3_a(result, fired=False)
        with self.subTest(stage="DECISION_THRESHOLD"):
            binary = result.signals["decision"]["binary_offensive"]
            self.assertEqual(binary["channels"]["raw"]["score"],
                             fusion.lookup_signal(result.signals, result.signals["m4_implicit"]["stage1_input"]))
            self.assertTrue(result.signals["decision"]["post_offensive"], diagnose(result))
        self.check_verdict(result, self.binary_action, "binary_offensive")

    def test_rule_v4_a_head_reaches_the_decision(self) -> None:
        """m3 A head -> ADR-005 family A -> PLACEHOLDER A threshold -> verdict. Explicit profanity: m1 and
        m3's A head both report the A1 carrier; the decision layer assigns the code from the target and
        thresholds every source and channel separately; the fused code fires."""
        text = "Siktir git buradan"
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        code = ContentCode(self.cfg["family_a"]["by_target"]["none"])
        with self.subTest(stage="MODULE_OUTPUT"):
            self.assertEqual(result.signals["m3_encoder"]["artifact"], m3.DEPLOYED_ID, diagnose(result))
            self.assertIn("sik", result.signals["m1_lexicon"]["matched_roots"], diagnose(result))
        self.check_m3_a(result, fired=True)
        with self.subTest(stage="DECISION_THRESHOLD"):
            self.assertEqual(result.signals["decision"]["family_a"]["code"], code.value, diagnose(result))
            m3_scores = channel_scores(result, "m3_encoder")
            self.assertTrue(all(c["code"] == code.value and c["threshold"] == float(self.cfg["categories"][code.value]["threshold"])
                                for c in m3_scores), diagnose(result))
            self.assertTrue(all(c["fired"] is (c["score"] >= c["threshold"]) for c in m3_scores), diagnose(result))
            self.assertEqual([s.code for s in result.fired()], [code], diagnose(result))
        self.check_binary(result, fired=True)
        verdict, driver = self.expected_verdict(code)
        self.check_verdict(result, verdict, driver)

    def test_degrading_sarcasm_reaches_the_verdict_through_m5(self) -> None:
        """m5 Stage 1 (protocols/m5_stage1_deterministic_protocol.md) end to end: the spec's scare-quote
        example fires D1 by rule R1, the D1 row (placeholder policy) decides, nothing is degraded."""
        text = "Bu kadar 'derin' bir yorum yapman etkileyici."
        result = self.pipeline.analyze(text)
        self.check_preconditions_held(result)
        self.check_interfaces(result)
        with self.subTest(stage="MODULE_OUTPUT"):
            m5 = result.signals["m5_sarcasm"]
            self.assertEqual((m5["stage"], m5["detector"], m5["matched_rules"]), (1, "deterministic", ["R1_SCARE_QUOTE"]))
            self.assertIs(m5["precedence_checked"], True)
            self.assertFalse(result.signals["m1_lexicon"]["lexicon_hit"], diagnose(result))
        with self.subTest(stage="PIPELINE_MERGE"):
            [d1] = from_module(result, "m5_sarcasm")
            self.assertEqual((d1.code, d1.score), (ContentCode.D1, 1.0))
            self.assertEqual(text[d1.span[0]:d1.span[1]], "'derin'")
        self.check_binary(result, fired=False)
        self.check_m3_a(result, fired=False)
        verdict, driver = self.expected_verdict(ContentCode.D1, binary=False)
        self.check_verdict(result, verdict, driver)

    def test_response_is_bounded_and_serialisable(self) -> None:
        result = self.pipeline.analyze("ap​tal herif " * 20)
        data = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertEqual(set(data), set(AnalysisResult(text="").to_dict()))
        self.assertNotIn("_offsets", json.dumps(data))
        self.assertNotIn("channels", data["signals"])


if __name__ == "__main__":
    unittest.main()
