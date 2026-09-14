"""Axis 4 repetition counter (pipeline/thread_counter.py, ADR-004).

The counter counts OFFENSIVE, non-self-directed posts per (sender_id, target_id)
inside a server-time window; the decision layer says whether a post is offensive
and alone compares the count with thread.min_repeats.
"""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from contracts.codes import Action, ContentCode, ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore, ThreadSignal
from decision import fusion
from pipeline import run
from pipeline.run import Pipeline
from pipeline.thread_counter import SOURCE, ThreadBlock, ThreadCounter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class ThreadCounterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.window = 60.0
        self.counter = ThreadCounter({"window_seconds": self.window}, clock=self.clock)
        self.block = ThreadBlock("u1", "u2", "t1")

    def observe(self, offensive: bool = True, block: ThreadBlock | None = None) -> int:
        return self.counter.observe(block or self.block, self.counter.now(), offensive).repeat_count

    def test_counts_offensive_posts_inside_the_window_including_this_one(self) -> None:
        self.assertEqual([self.observe() for _ in range(3)], [1, 2, 3])

    def test_non_offensive_posts_are_not_counted(self) -> None:
        # Two friends who talk a lot must not look like repeated abuse.
        self.assertEqual([self.observe(offensive=False) for _ in range(5)], [0] * 5)
        self.assertEqual(self.observe(), 1)
        # A clean post reports the offensive history in the window without adding to it.
        self.assertEqual(self.observe(offensive=False), 1)
        self.assertEqual(self.observe(), 2)

    def test_self_directed_posts_are_never_counted(self) -> None:
        me = ThreadBlock("u1", "u1")
        self.assertTrue(me.self_directed)
        self.assertEqual([self.observe(block=me) for _ in range(5)], [0] * 5)
        self.assertEqual(len(self.counter), 0)

    def test_signal_shape(self) -> None:
        signal = self.counter.observe(self.block, self.counter.now(), True)
        self.assertEqual((signal.thread_id, signal.same_target, signal.source), ("t1", True, SOURCE))
        # The counter never fills decision-owned fields, nor the retired post-count window.
        self.assertEqual((signal.threshold, signal.fired, signal.window_posts), (None, None, 0))

    def test_events_older_than_the_window_expire(self) -> None:
        self.observe()
        self.clock.now += self.window / 2
        self.assertEqual(self.observe(), 2)
        self.clock.now += self.window  # the first two are now out of the window
        self.assertEqual(self.observe(), 1)

    def test_counts_by_receive_time_not_by_completion_order(self) -> None:
        early = self.counter.now()
        self.clock.now += 5
        self.assertEqual(self.observe(), 1)  # a later post finishes first
        # The earlier post does not count the later one as its history.
        self.assertEqual(self.counter.observe(self.block, early, True).repeat_count, 1)
        self.assertEqual(self.observe(), 3)

    def test_keyed_by_sender_and_target(self) -> None:
        self.observe()
        self.assertEqual(self.observe(block=ThreadBlock("u1", "u3")), 1)
        self.assertEqual(self.observe(block=ThreadBlock("u9", "u2")), 1)
        # Across threads: the key is sender and target, not the thread.
        self.assertEqual(self.observe(block=ThreadBlock("u1", "u2", "other-thread")), 2)

    def test_quiet_keys_are_swept(self) -> None:
        self.observe(block=ThreadBlock("quiet", "u2"))
        self.clock.now += self.window
        self.observe()
        self.assertEqual(len(self.counter), 1)

    def test_state_is_per_instance_so_a_restart_starts_empty(self) -> None:
        self.observe()
        fresh = ThreadCounter({"window_seconds": self.window}, clock=self.clock)
        self.assertEqual(fresh.observe(self.block, fresh.now(), True).repeat_count, 1)

    def test_caller_supplied_time_is_refused(self) -> None:
        # ADR-004: a timestamp from the caller is forgeable (backdating stays under the count).
        with self.assertRaises(ValueError):
            ThreadBlock.from_dict({"sender_id": "u1", "target_id": "u2", "timestamp": 0})

    def test_thread_block_validation(self) -> None:
        for bad in ([], {"sender_id": "u1"}, {"sender_id": "", "target_id": "u2"},
                    {"sender_id": "u1", "target_id": 7}, {"sender_id": "u1", "target_id": "u2", "thread_id": 1}):
            with self.subTest(block=bad), self.assertRaises(ValueError):
                ThreadBlock.from_dict(bad)
        self.assertEqual(ThreadBlock.from_dict({"sender_id": "u1", "target_id": "u2"}), ThreadBlock("u1", "u2"))


class ThreadConfigTest(unittest.TestCase):
    def test_window_is_configured_and_validated(self) -> None:
        cfg = fusion.load_config()
        self.assertIn("window_seconds", cfg["thread"])
        for bad in (None, 0, -5, "600", True, float("inf")):
            broken = copy.deepcopy(cfg)
            broken["thread"]["window_seconds"] = bad
            with self.subTest(window=bad), self.assertRaises(ValueError):
                fusion.validate_config(broken)


class _TextScorer(BaseModule):
    """Test double: scores A3 high when the text starts with "!", low otherwise."""

    name = ModuleName.M1_LEXICON
    provides = frozenset({"content"})
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        value = 0.9 if ctx.text.startswith("!") else 0.1
        return ModuleOutput(content=[ContentScore(ContentCode.A3, value, "m1_lexicon@raw")])


class ThreadPipelineTest(unittest.TestCase):
    """The pipeline asks the decision layer whether a post is offensive, then counts."""

    def setUp(self) -> None:
        self.cfg = copy.deepcopy(fusion.load_config())
        self.cfg["categories"]["A3"].update(threshold=0.5, action="nudge")
        self.cfg["thread"].update(enabled=True, min_repeats=3, action="escalate")
        self.pipeline = Pipeline(modules=[_TextScorer()], config=self.cfg)
        self.block = ThreadBlock("u1", "u2")

    def analyze(self, text: str, block: ThreadBlock | None = None):
        return self.pipeline.analyze(text, thread_block=block or self.block)

    def test_offensive_repeats_fire_the_thread_rule(self) -> None:
        results = [self.analyze("!saldırı") for _ in range(3)]
        self.assertEqual([r.thread.repeat_count for r in results], [1, 2, 3])
        self.assertEqual([r.thread.fired for r in results], [False, False, True])
        self.assertTrue(all(r.signals["decision"]["post_offensive"] for r in results))
        self.assertIs(results[-1].verdict, Action.ESCALATE)
        self.assertIn("aynı hedefe yönelik 3 saldırgan mesajı", results[-1].explanation)
        self.assertNotIn("başlık", results[-1].explanation)

    def test_clean_post_after_abuse_is_not_escalated(self) -> None:
        for _ in range(3):
            self.analyze("!saldırı")
        after = self.analyze("özür dilerim")
        # The history is reported as a fact, but it never escalates a clean post.
        self.assertEqual(after.thread.repeat_count, 3)
        self.assertFalse(after.thread.fired)
        self.assertIs(after.verdict, Action.CLEAN)

    def test_frequent_friendly_posts_never_escalate(self) -> None:
        results = [self.analyze("merhaba") for _ in range(10)]
        self.assertEqual({r.thread.repeat_count for r in results}, {0})
        self.assertEqual({r.verdict for r in results}, {Action.CLEAN})
        self.assertFalse(results[-1].signals["decision"]["post_offensive"])

    def test_self_directed_offensive_posts_never_escalate(self) -> None:
        me = ThreadBlock("u1", "u1")
        results = [self.analyze("!saldırı", me) for _ in range(5)]
        self.assertEqual({r.thread.repeat_count for r in results}, {0})
        self.assertNotIn(Action.ESCALATE, {r.verdict for r in results})
        self.assertTrue(any("not counted" in n for n in results[-1].notes))

    def test_thread_signal_and_block_are_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            self.pipeline.analyze("x", thread=ThreadSignal(), thread_block=self.block)


class ThreadCliTest(unittest.TestCase):
    """The thread path is reachable from the CLI before the API exists."""

    def run_cli(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = run.main(argv)
        return code, buffer.getvalue()

    def test_thread_block_reaches_the_counter(self) -> None:
        code, out = self.run_cli(["mesaj 1", "mesaj 2", "--compact", "--thread",
                                  '{"sender_id": "u1", "target_id": "u2", "thread_id": "t1"}'])
        self.assertEqual(code, 0)
        results = json.loads(out)
        self.assertEqual([r["thread"]["source"] for r in results], [SOURCE, SOURCE])
        self.assertEqual([r["thread"]["thread_id"] for r in results], ["t1", "t1"])
        # Detection modules are stubs today: no post is offensive, so nothing is counted.
        self.assertEqual([r["thread"]["repeat_count"] for r in results], [0, 0])
        self.assertEqual([r["signals"]["decision"]["post_offensive"] for r in results], [False, False])

    def test_single_text_without_thread_is_unchanged(self) -> None:
        code, out = self.run_cli(["Bu bir test", "--compact"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["thread"])

    def test_bad_thread_block_is_a_usage_error(self) -> None:
        for bad in ("not json", '{"sender_id": "u1", "target_id": "u2", "timestamp": 1}'):
            with self.subTest(block=bad), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                run.main(["x", "--thread", bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
