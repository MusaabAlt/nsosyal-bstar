# m3_encoder — dev numbers, measured on this machine

Every number here is a **dev** number on the frozen split
(`diagnosis/data/splits/split_seed42.json`, 4,764 rows, dev fingerprint `034415af…`).
The official test set is spent and stays closed.

**What is measured.** m3 as it exists today: the frozen phase-01 BERTurk checkpoint
(epoch 1, sha256 `43a20d55…`, artifact `m3-berturk-pytorch-fp32-epoch1`) wrapped as
`EncoderModule`, scoring the **raw channel only**. There is no A head yet, so no per-code
metric exists; these are the binary OFF/NOT numbers the deployed `binary_offensive`
threshold acts on.

**Protocol.** Bootstrap n = 1,000, α = 0.05, seed 42 — the frozen baseline's own protocol
(`diagnosis/results/01_baseline_berturk/run_config.json` → `bootstrap`), so the numbers are
directly comparable with it. Decision rule `flag iff score >= t`, matching
`decision/fusion.py`. This is a **descriptive replication**, not a newly pre-registered
measurement.

**Environment.** Python 3.12.10, torch 2.11.0, transformers 5.15.0, FP32 on CPU, Windows.
Measured 2026-09-16.

---

## 1. Reproduction of the frozen baseline — exact

| Check | Required | Measured |
|---|---|---|
| Confusion at 0.5 (tn / fp / fn / tp) | 3631 / 213 / 285 / 635 | **3631 / 213 / 285 / 635** |
| Label flips vs `dev_predictions.csv` | 0 | **0** |
| dev macro-F1 | 0.8270752670616224 | **0.8270752670616224** |
| Module errors | 0 | **0** |
| Rows truncated at 128 tokens | — | 2 |
| max \|Δp\| vs the recorded predictions | — | 3.60e-06 (row 36218) |

The residual Δp is CPU floating-point difference plus the CSV's rounding to 6 decimals; it
moves no label. Three scoring passes in separate processes were byte-identical.

---

## 2. Metrics with 95% CIs, decomposed by slice

Never averaged into one figure: the `lexicon_free` slice is the one that matters, because
`lexicon_hit` is largely what m1 already catches with a lexicon.

### At t = 0.5 (the baseline's decision threshold)

| Slice | n | tp / fp / fn / tn | OFF precision | OFF recall | OFF F1 | macro-F1 |
|---|---|---|---|---|---|---|
| all dev rows | 4,764 | 635 / 213 / 285 / 3631 | 0.7488 [0.7209, 0.7790] | 0.6902 [0.6606, 0.7187] | 0.7183 [0.6963, 0.7407] | **0.8271 [0.8140, 0.8409]** |
| `lexicon_hit` | 614 | 317 / 47 / 38 / 212 | 0.8709 [0.8355, 0.9037] | 0.8930 [0.8609, 0.9235] | 0.8818 [0.8567, 0.9050] | 0.8574 [0.8286, 0.8830] |
| `lexicon_free` | 4,150 | 318 / 166 / 247 / 3419 | 0.6570 [0.6145, 0.6981] | 0.5628 [0.5209, 0.6034] | 0.6063 [0.5686, 0.6391] | 0.7747 [0.7539, 0.7920] |

These match the recorded baseline: macro-F1 0.8271 [0.8139, 0.8405] and `lexicon_free`
recall 0.5628 [0.5210, 0.6010] in `metrics.json`. The small CI differences are resampling
implementation, not a different result.

### At t = 0.320188 (the deployed `binary_offensive` threshold)

| Slice | n | tp / fp / fn / tn | OFF precision | OFF recall | OFF F1 | macro-F1 |
|---|---|---|---|---|---|---|
| all dev rows | 4,764 | 716 / 405 / 204 / 3439 | 0.6387 [0.6090, 0.6664] | 0.7783 [0.7508, 0.8021] | 0.7016 [0.6782, 0.7230] | 0.8101 [0.7960, 0.8230] |
| `lexicon_hit` | 614 | 332 / 70 / 23 / 189 | 0.8259 [0.7892, 0.8615] | 0.9352 [0.9080, 0.9593] | 0.8771 [0.8511, 0.9001] | 0.8398 [0.8082, 0.8690] |
| `lexicon_free` | 4,150 | 384 / 335 / 181 / 3250 | 0.5341 [0.4966, 0.5680] | 0.6796 [0.6379, 0.7161] | 0.5981 [0.5635, 0.6276] | 0.7623 [0.7433, 0.7797] |

**The cost, stated in the same sentence as the gain.** Moving from 0.5 to 0.320188 buys
**+8.8 points of OFF recall** (0.6902 → 0.7783) and pays **−11.0 points of OFF precision**
(0.7488 → 0.6387): 81 more true positives and 192 more false positives. That is the r = 3
cost policy working as adopted — a false negative is priced at three false positives — not
an improvement in the model. Macro-F1 falls (0.8271 → 0.8101), which is expected and is why
macro-F1 is not the objective the threshold was fitted on.

**Where the system is weakest:** `lexicon_free` OFF precision 0.5341 [0.4966, 0.5680] at the
deployed threshold. Roughly one in two flags on text with no lexicon hit is wrong. That
slice is 87% of dev.

---

## 3. Latency on this machine (CPU, one post per call)

| Input | p50 | p95 |
|---|---|---|
| ≤ 32 tokens (3,415 dev rows) | 31.1 ms | 42.2 ms |
| median length, 23 ±4 tokens (1,300 rows) | 32.4 ms | 41.9 ms |
| > 128 tokens, truncated (2 rows) | 98.9 ms | 118.4 ms |
| all dev rows (4,764) | 33.5 ms | 67.6 ms |
| by character length | ≤64 chars: p95 31.0 ms · ~900 chars: p95 149.3 ms · 5,000 chars: p95 145.5 ms |

Measured, not estimated: every dev row timed once, plus 20 repeats per fixture for the
band figures. **This is a dev laptop, not the demo machine** — the demo machine numbers
still have to be taken there.

**Budget note.** `budgets.module_latency_p95_ms.m3_encoder` is a single scalar (80 ms),
while m0 and m1 are banded by input length. m3 is far inside it at realistic post lengths
and outside it on a 5,000-character input, which spec §9 requires as a fixture. Proposal to
band it is with Musaab; `thresholds.yaml` is not ours to edit.

---

## 4. Batching: measured and rejected

On 1,000 dev rows, padded batches were **slower** and **changed scores**:

| Mode | ms per post | speed vs single | scores identical? | max \|Δ\| |
|---|---|---|---|---|
| one at a time (current) | 31.3 | — | — | — |
| batch 8 | 45.0 | 0.70× | no, 748/1000 rows | 9.5e-07 |
| batch 16 | 51.9 | 0.60× | no, 789/1000 | 1.0e-06 |
| batch 32 | 56.7 | 0.55× | no, 786/1000 | 9.5e-07 |

Padding changes the arithmetic, so batching would break the exact reproduction in §1 while
costing time. Not adopted. A negative result, measured.

---

## 5. What is not here, and why

- **Per-code A/B/C metrics.** No head exists yet. The A head waits on the per-row label file
  over the frozen dev split; the B head has no labelled corpus; the C head is deferred.
  Fixtures are in place (`fixtures/cases.jsonl`, 32 A1 positives), so A1 currently reads
  recall 0.000 — the honest state of an unbuilt head, not a regression.
- **Normalized-channel numbers.** m3 scores the raw channel only today: the threshold was
  derived on raw text and m2 is a stub.
- **Decision-flip table per artifact** (spec §7). One artifact exists, PyTorch FP32; ONNX
  and INT8 were not attempted (owner decision, 2026-09-15).
- **Demo-machine latency.** Measured here on a dev laptop only.
