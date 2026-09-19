# m3_encoder — truncation policy

**Status: PROPOSED by Abdullah 2026-09-16, awaiting Musaab.** Nothing here is implemented.
`module.py` still uses `MAX_LEN = 128`, and spec §5 still describes the study's policy.
Spec §5 requires this declared **before training**, which is why it is written now.

---

## 1. The policy in force today

| | |
|---|---|
| Maximum sequence length | **128 tokens**, including `[CLS]` and `[SEP]` |
| What happens to longer input | the **first** 128 tokens are scored, the remainder is dropped |
| Note emitted | yes — `truncated: N tokens, scored the first 128` |
| Where it comes from | the frozen baseline's training config (`hyperparams.max_len` = 128). The deployed `binary_offensive` threshold was fitted on scores produced under it. |
| Both channels at the same point? | **not applicable yet** — m3 scores the raw channel only, because m2 is a stub. The spec's cross-channel question cannot be measured until m2 produces `normalized_text`. |

---

## 2. What it costs, measured

**Token lengths on the frozen dev split (4,764 rows):** min 7, median 23, p95 64, p99 82,
max 152.

| Window | Dev rows exceeding it |
|---|---|
| 64 | 215 (4.51%) |
| **128 (current)** | **2 (0.04%)** |
| 256 | 0 |
| 512 | 0 |

So on the evaluation data the policy is nearly free. **The risk is not in the dev
distribution — it is in what a judge will paste.**

**The failure it creates, demonstrated.** Fixture `m3-trunc-002` is a long, entirely
ordinary Turkish text with an insult as its last sentence — 212 tokens:

| Window | Score | Latency |
|---|---|---|
| 128 (current) | **0.0048** — far below the 0.320188 threshold, verdict clean | 114 ms |
| 256 | **0.8905** — fires | 189 ms |
| 512 | 0.8905 | 201 ms |

The note fires in every case, but a note is not a decision: the post is judged clean by a
system that never read the abusive part of it. Anyone who knows the limit can hide an
insult behind 128 tokens of filler.

**Raising the window changes nothing for normal posts.** Scoring 300 dev rows at
`max_length` 256 instead of 128 produced **0 differing scores**, to full precision. There is
no padding for a single post, so a longer window is inert unless the input actually exceeds
the old one. Cost is latency on long input only: p95 rises from ~115 ms to ~190 ms on a
212-token post.

---

## 3. Options, with what each costs

**Option A — keep 128 tokens, first tokens kept.** No change, no re-derivation, stays
byte-identical to the frozen baseline. Accepts the tail-insult hole knowingly and documents
it as a known limitation.

**Option B — raise to 256 tokens (recommended).** Covers 100% of the dev split and every
realistic post. Measured to change **no** score for input under 128 tokens, so the frozen
reproduction in `RESULTS_DEV.md` §1 and the fitted threshold both survive: the only scores
that move are the 2 dev rows that were being truncated. Costs ~75 ms extra on long input.
Caveat to state plainly: the checkpoint was fine-tuned at 128, so positions 129–256 are
in-range for BERT (512 limit) but unseen during fine-tuning. That is a distribution
question, not a crash, and the tail-insult result suggests it works — but it has been tested
on one constructed example, not on a labelled long-post slice, because none exists.

**Option C — score the head and the tail, report both.** Two passes: first 128 tokens and
last 128 tokens, both published. Catches the hidden tail without touching the window the
model was trained at. Doubles latency on long input, and needs a contract decision about
which score the decision layer reads — which makes it a bigger change than it looks.

**Option D — truncate both channels at the same character offset.** Spec §5 raises this for
when raw and normalized token counts diverge. **Not decidable now:** m2 is a stub, so there
is no second channel to diverge. To be revisited when m2 lands; the measurement the spec
asks for (how often the two channels truncate at different points) should be run then.

---

## 4. What we propose

**Option B**, plus keeping the note. Rationale: it closes a hole a judge can trigger by
pasting one long post, it is measurably free on every input the system currently sees, and
it leaves the frozen numbers intact. If Musaab prefers A, the limitation belongs in the
report as a stated boundary rather than left to be discovered.

**Either way, two things follow:**
- The chosen policy is written into `spec.md` §5 — a spec change, so Musaab's call.
- If B is adopted, `RESULTS_DEV.md` §1 is re-run to confirm the confusion matrix and the
  macro-F1 are unchanged, and the 2 affected dev rows are named.
