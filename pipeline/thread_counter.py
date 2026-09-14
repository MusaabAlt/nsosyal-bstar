"""Axis 4 repetition counter: how many OFFENSIVE posts one sender addressed to
one target inside the configured time window.

It COUNTS; it never decides. Two things arrive from outside:
  * whether the post is offensive - decided by the decision layer
    (decision/fusion.py post_is_offensive) and passed in by the pipeline;
  * `thread.window_seconds` from decision/thresholds.yaml.
It returns a ThreadSignal whose `repeat_count` the decision layer compares with
`thread.min_repeats` (fusion.apply_thread). The counter deliberately does not
read `min_repeats`: that would move the escalation comparison out of the
decision layer.

What counts as a repeat (owner decision, ADR-004 amendment): offensive posts
only, never self-directed ones. Repetition is one element of bullying alongside
intent and power imbalance; counting every post would measure how often two
people talk, not repeated abuse.

Time source: SERVER RECEIVE TIME (ADR-004). The caller takes `now()` as soon as
the post arrives and hands that value back to `observe()`. A caller-supplied
timestamp is never accepted from a request: it is forgeable, and backdated
events would stay under the escalation count.

DEMO SCOPE, not production:
  * state is in memory only and RESETS ON RESTART - every process starts with
    zero history, so one CLI invocation only counts the posts passed to it;
  * one process, one counter: no sharing across workers or machines;
  * keys are `(sender_id, target_id)`; the ids are whatever the caller sends,
    unverified.

Deliberately does NOT:
  * look at the text, or decide whether a post is offensive;
  * decide whether the count is enough to escalate (decision layer);
  * fill `ThreadSignal.window_posts`: repetition is time-windowed, not bounded
    by a post count (owner decision #19), so the frozen field stays 0.
"""
from __future__ import annotations

import bisect
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from contracts.schema import ThreadSignal

SOURCE = "pipeline.thread_counter"


@dataclass(frozen=True)
class ThreadBlock:
    """What a caller may say about a post's thread. No timestamp, by design."""

    sender_id: str
    target_id: str
    thread_id: str | None = None

    @property
    def self_directed(self) -> bool:
        return self.sender_id == self.target_id

    @classmethod
    def from_dict(cls, raw: Any) -> "ThreadBlock":
        """Validate a JSON thread block; raises ValueError with the reason."""
        if not isinstance(raw, dict):
            raise ValueError(f"thread block must be a JSON object, got {type(raw).__name__}")
        unknown = set(raw) - {"sender_id", "target_id", "thread_id"}
        if unknown:
            # A "timestamp" key lands here: caller-supplied time is refused (ADR-004).
            raise ValueError(f"thread block has unknown keys: {sorted(unknown)}")
        for key in ("sender_id", "target_id"):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValueError(f"thread block needs a non-empty string {key}")
        thread_id = raw.get("thread_id")
        if thread_id is not None and not isinstance(thread_id, str):
            raise ValueError("thread block thread_id must be a string when given")
        return cls(raw["sender_id"], raw["target_id"], thread_id)


class ThreadCounter:
    """In-memory sliding-window counter of offensive posts per (sender_id, target_id)."""

    def __init__(self, thread_cfg: Mapping[str, Any], clock: Callable[[], float] = time.monotonic) -> None:
        self.window_seconds = float(thread_cfg["window_seconds"])
        self._clock = clock
        # Receive times, kept sorted: concurrent requests can finish out of arrival order.
        self._events: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()  # the HTTP server handles requests on several threads
        self._last_sweep = clock()

    def now(self) -> float:
        """Server receive time. Take it when the post arrives, before analysis."""
        return self._clock()

    def observe(self, block: ThreadBlock, received_at: float, offensive: bool) -> ThreadSignal:
        """Record the post if it is offensive and not self-directed, and return
        the number of counted posts received in the window ending at
        `received_at` - this post included when it was counted."""
        signal = ThreadSignal(thread_id=block.thread_id, same_target=True, source=SOURCE)
        if block.self_directed:
            return signal  # never counted, never recorded: repeat_count stays 0
        with self._lock:
            key = (block.sender_id, block.target_id)
            events = self._events.setdefault(key, [])
            if offensive:
                bisect.insort(events, received_at)
            # Posts received after this one (a concurrent request) are not its history.
            upper = bisect.bisect_right(events, received_at)
            lower = bisect.bisect_right(events, received_at - self.window_seconds)
            signal.repeat_count = upper - lower
            now = self._clock()
            if now - self._last_sweep >= self.window_seconds:
                self._sweep(now)
            elif not events:
                del self._events[key]
        return signal

    def _sweep(self, now: float) -> None:
        # Drop events that can no longer fall inside any future window, and
        # the keys of senders who went quiet.
        for key in list(self._events):
            events = self._events[key]
            del events[:bisect.bisect_right(events, now - self.window_seconds)]
            if not events:
                del self._events[key]
        self._last_sweep = now

    def __len__(self) -> int:
        """Number of (sender, target) keys held in memory."""
        return len(self._events)
