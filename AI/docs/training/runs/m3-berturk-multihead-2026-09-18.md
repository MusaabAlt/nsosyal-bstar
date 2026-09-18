# Historical experiment — `m3-berturk-multihead-2026-09-18` (first GPU run, binary + A head)

**Verdict: `TECHNICALLY_VALID_BUT_A_SEMANTICALLY_MISALIGNED`.** Frozen on 2026-09-18. This record
is history: its numbers are never edited, the run is never overwritten, no A threshold is derived
from it, and it is not promoted. A new run uses a new run id.

## Identity

| | |
|---|---|
| artifact id | `m3-berturk-multihead-2026-09-18` |
| run directory (Drive, preserved) | `/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/2026-09-18/` |
| weights sha256 | `995ba52514f57c33595b585d501866738df89f8791b51b9ca6f8439098e7123b` |
| trained commit | `206f7e913152f5477c8a2ddb3ffd29036ae804fd` (`audit/m1-m6`, clean) |
| hardware / stack | NVIDIA L4 23 GB, torch 2.11.0+cu128, transformers 5.15.0, Python 3.13.15 |
| configuration | handoff §18 unchanged: 3 epochs, batch 32, lr 2e-5, max_len 128, warmup 0.1, weight decay 0.01, seed 42, fp16 |
| duration | 5 min 53 s; no OOM, no NaN / Inf, no retry |
| A supervision | pseudo-label **rule v1** (any terlik match): train file sha256 `1f6f6cc21c553f68…` (26,992 rows, 2,578 positives), dev file `03c9895541cc6d86…` (agreement only); both preserved in git at `d7925de` |
| heads | binary trained, A trained, B untrained, C untrained |

## Binary head — acceptable

Dev, 4,764 rows, reporting point 0.5, 1,000 bootstrap resamples.

| metric | value | 95 % CI |
|---|---|---|
| macro-F1 | 0.8267 | [0.8122, 0.8400] |
| OFF recall | 0.6859 | [0.6563, 0.7152] |
| OFF precision | 0.7521 | [0.7237, 0.7818] |
| FPR | 0.0541 | [0.0463, 0.0618] |

Confusion tp 631 / fp 208 / fn 289 / tn 3,636. Frozen baseline: 0.8271 [0.8139, 0.8405]; the drop
of 0.0004 is far inside the handoff §28 allowance (0.0266). Epochs: F1 0.8187 / 0.8131 / 0.8267,
train loss 0.5751 / 0.3451 / 0.2491; best = epoch 3.

## A head — what was measured

**Pseudo-label agreement (rule v1, 4,764 dev rows; agreement, not accuracy):** precision 0.8956,
recall 0.8410, F1 0.8674, FPR 0.0105 (tp 386 / fp 45 / fn 73 / tn 4,260).

**AI-assisted, human-adjudicated reference metrics** (500-row uniform dev sample, seed 42,
guideline v1.1; two AI annotators — Claude/Fable and Gemini — 497/500 agreement, Cohen's κ 0.958,
the 3 disagreements decided by the human project owner; 39 positives / 461 negatives). This is
**not** a human oracle and these are **not** human-ground-truth numbers.

| metric | value | 95 % CI |
|---|---|---|
| precision | 0.6364 | [0.5088, 0.7593] |
| recall | 0.8974 | [0.8000, 0.9773] |
| F1 | 0.7447 | [0.6374, 0.8333] |
| FPR | 0.0434 | [0.0259, 0.0607] |

tp 35 / fp 20 / fn 4 / tn 441, reporting point 0.5. No threshold curve was inspected.

## Why it is misaligned

On the same 500 rows the rule-v1 pseudo-labels themselves score precision 0.6034 / recall 0.8974
against the reference — the same recall as the head and nearly the same precision. 17 of the
head's 20 false positives are rows rule v1 also labels positive. The head reproduced its
supervision, and its supervision encodes a broader concept than the A head's:

- terlik's Turkish dictionary has 147 roots: 18 `sexual`, 104 `insult`, 3 `slur`, 22 `general`;
- rule v1 labelled a post positive on **any** match, so ordinary insults became "profanity present";
- guideline v1.1 (owner decision 2026-09-18) defines the A head as explicit profanity — an obscene
  or profane root — and scores ordinary insults `0`.

A threshold moves an operating point along one concept; it cannot turn "insult" into "obscene
root". The supervision changes instead: pseudo-label **rule v2**
(`protocols/m1_lexicon_train_labels_protocol.md`, amendment 2026-09-18).

## Standing rules for this record

- The 500-row reference is an **evaluation set only**: never a training label, never a source of
  rule edits, never used to tune on individual dev errors.
- The run directory on Drive and the private evaluation files
  (`eval/annotation/private/a_head_eval_ai_assisted_reference.json`) are kept as they are.
- The binary head of this artifact is sound, but the artifact is one unit: it is not promoted.
