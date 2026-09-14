# ADR-004 — The repetition counter stamps events with server receive time

- **Status:** accepted
- **Date:** 2026-09-14
- **Decided by:** project owner (policy decision; options prepared in the session handover, open question on decision #19)
- **Scope:** `pipeline/thread_counter.py`, `pipeline/run.py` (CLI), `decision/thresholds.yaml` (`thread.window_seconds`), `decision/fusion.py` (config validation)

## Context

Axis 4 was never judged at runtime: the decision layer had a thread rule, but
neither the CLI nor the API ever built a `ThreadSignal`. The owner decided that
repetition is time-windowed, not bounded by a post count (decision #19), which
left two things undefined: the window length, and where the time comes from.
`ThreadSignal` in the frozen contract has no time field. Two options were
presented:

- **Server receive time:** the counter stamps each event itself when the post
  arrives. No contract change.
- **Caller-supplied timestamp:** the request carries the event time, which
  needs a new contract field and therefore an ADR opening `contracts/`.

## Decision

**Server receive time.** An in-memory counter keyed by `(sender_id, target_id)`
stamps every observed post with the server's own clock, keeps the events inside
`thread.window_seconds` (from `decision/thresholds.yaml`, a PLACEHOLDER to be
derived later) and passes `repeat_count` down in a `ThreadSignal`. The decision
layer compares that count with `thread.min_repeats` and picks the action. The
contract does not change.

## Reasons

1. **The contract is not opened for this.** `contracts/` has already been opened
   twice (ADR-001 for spans and guard scoping, ADR-002 for label keys, the
   second also carrying the regenerated example). A demo-scope repetition
   counter does not justify a third opening.
2. **A caller-supplied timestamp is forgeable.** Anyone could backdate events so
   that they fall outside the window and stay under the escalation count. A
   counter the sender can steer is worthless as a signal. The thread block
   therefore has no time field at all, and a block carrying one is rejected.

## Consequences

- `pipeline/thread_counter.py` counts; it reads `window_seconds` and never reads
  `min_repeats`, so the escalation comparison stays in `decision/fusion.py`.
- The clock is monotonic. The caller reads it (`ThreadCounter.now()`) as soon as a
  post arrives, before analysis, and hands that server-side value to `observe()`;
  it never comes from the request.
- **Demo scope, not production:** state is in memory, per process, and resets
  on restart. No sharing across workers. Sender and target ids are taken as the
  caller sends them, unverified.
- `ThreadSignal.window_posts` (frozen) stays `0`; `same_target` is always `True`
  because the key includes the target.
- The CLI takes `--thread '{"sender_id": ..., "target_id": ..., "thread_id": ...}'`
  and several texts, observed in order, so the path is testable before the API
  exists. The API side waits for `docs/frontend/02_BACKEND_SPEC.md` to be
  committed.
- `thread.window_seconds` is a placeholder with no claimed justification; it is
  derived with `protocols/templates/threshold_derivation.md` like every other
  number in the file.

## Amendment — what counts as a repeat (2026-09-14)

- **Decided by:** project owner (policy question raised at the end of session 2)

**Decision.** Only OFFENSIVE posts count as repeats, and a self-directed post
(`sender_id == target_id`) is never counted.

**Reason.** The bullying literature defines repetition as one of three elements,
alongside intent and power imbalance. Counting every post measures conversation
frequency, not repeated abuse: two friends who talk a lot would escalate.
Self-directed posts are excluded explicitly - there is no second party to abuse.

**How it is applied.**

- The counter still only counts. Whether a post is offensive is decided by the
  decision layer: `decision/fusion.py` now runs in two stages, `decide_post`
  (reset, thresholds, binary score, guards, fusion, form) and `conclude` (thread
  rule, verdict, explanation); `decide` runs both. Between them the pipeline asks
  `fusion.post_is_offensive(result)` and passes the answer to `observe()`.
  Fusion learns nothing about the pipeline: it exposes its stages, the pipeline
  keeps the order.
- `post_is_offensive` (recorded as `signals.decision.post_offensive`): a content
  code that fired and survived the guards, or the binary offensive score fired.
  Form patterns never count (obfuscation is not content), and neither does
  degradation - an incomplete judgement is not a finding of abuse. This reading
  of "offensive" is the assistant's implementation; the owner confirms it.
- `repeat_count` is the number of counted posts received in the window ending at
  this post's receive time, this post included when it was counted. Posts
  received later (a concurrent request that finished first) are not its history.
- A self-directed post returns `repeat_count = 0`, is never recorded, and the
  pipeline adds a note.
- The Turkish explanation no longer says "aynı başlıkta" (in the same thread),
  because counting is per sender and target across threads: "Aynı gönderenin
  aynı hedefe yönelik N saldırgan mesajı nedeniyle içerik ...".

**Consequences.**

- While m1-m6 are stubs no post is offensive, so the CLI thread path runs but
  never counts; tests exercise counting with a scoring test double.
- A non-offensive post still carries the offensive history of its window in
  `repeat_count`, as a fact. It never fires the thread rule (next amendment).

## Amendment — the thread rule fires on offensive posts only (2026-09-14)

- **Decided by:** project owner

**Decisions.**

1. The reading of "offensive" above is confirmed as implemented: a content code
   fired after guards, or the binary offensive score fired. A `review` caused only
   by stubs or other degradation does not count - otherwise the counter measures
   how unfinished the system is, not repeated abuse. The fixed-score test module
   stays.
2. The thread rule fires only when THIS post is offensive. A clean message is not
   escalated on the strength of history.

**Reason.** Escalation is an action taken on this post. Penalising a benign
message because of earlier ones means the system acts on the person rather than
the content, and that is a line a moderation system does not cross. Repetition
raises the severity of an offensive post; it never creates severity where the
post itself has none.

**How.** `decision/fusion.py::apply_thread` takes the post-level answer from
`post_is_offensive` and requires it, alongside `min_repeats` and the same-target
rule. `repeat_count` on a clean post still reports the window's offensive history.
Pinned by `tests/test_decision.py::test_thread_rule_never_fires_on_a_clean_post`
and `tests/test_thread_counter.py::test_clean_post_after_abuse_is_not_escalated`.
