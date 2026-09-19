# M3 — Shared Encoder, Three Heads

**Type:** detection
**Owner:** Abdullah
**Note:** this is the heaviest module. Its heavy dependencies live in `modules/m3_encoder/requirements.txt`. D1 is not produced here: m5 is its own model (ADR-003).

---

## 1. Objective

One Turkish BERT encoder, three classification heads on top (families A, B and C), so CPU latency and memory stay at single-model cost while each family keeps its own head and its own threshold. C1–C5 are a head here rather than a fourth standalone model, because a fourth model means a fourth encoder pass on CPU; M4 owns their thresholds and the slice repair, not a model (ADR-006). Degrading sarcasm (D1) is not a head of this encoder: it is m5's own model with its own artifact and thresholds, so sarcasm experiments never produce a new m3 artifact (ADR-003).

```
                          ┌─ head_explicit    → profanity present (one score, A1 carrier)
ctx.text            ──┐   │
                      ├─ BERTurk ─┼─ head_nonlexical → B1..B5  (MULTI-label)
ctx.normalized_text ──┘   │
                          └─ head_implicit    → C1..C5
```

The encoder runs **twice per request**: once on the raw text, once on the normalized text from M2. Both score sets are reported. Fusion happens in the decision layer, not here.

---

## 2. Why multi-label for the B head

One post can be a threat and an exclusion at the same time. The reference taxonomy this project uses explicitly states its categories are not mutually exclusive and that more than one may apply to a single input. Forcing single-label on family B will destroy your agreement numbers.

Family A is a single "profanity present" score: its codes differ only by target, and the decision layer assigns A1, A2 or A3 from M6's target (ADR-005).

---

## 3. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| Family A: one "profanity present" score, emitted on the `A1` carrier | `A4` sacred profanity → M1 (concept-based, not target-based) |
| `C1`–`C5` implicit abuse, third head (thresholds and slice repair → M4, ADR-006) | |
| `B1`–`B5` abuse with no profane root, multi-label | `D1` degrading sarcasm → M5, its own model (ADR-003) |
| A binary offensive probability per channel | who the abuse targets → M6 |
| The same text read twice: raw and de-obfuscated | which obfuscation was used → M0 / M2 |

**The target dependency, stated plainly.** Family A codes differ only by
target: `A1` untargeted, `A2` individual, `A3` group. M3 emits one "profanity
present" score, on code `A1`, which carries it until the decision layer assigns
the final code from M6's target: no target → `A1`, individual → `A2`, group →
`A3` (ADR-005). Do not build a head that guesses the target, and never emit
`A2` or `A3`. `A4` is not produced here — it is distinguished by the concept
used, not by the target, and M1's sacred-concept extension carries it.

**Also out of scope:**

- **Calibration.** M3 emits the model's raw probabilities. Turning a
  probability into a decision — and any recalibration — belongs to the decision
  layer. A module that calibrates its own output makes the threshold meaningless.
- **Fusion.** The raw and normalized channels are reported separately, always.
  Combining them inside the module destroys the measurement the whole
  obfuscation story depends on.
- **Thread-level repetition.** Counted by the pipeline, judged by the decision
  layer. M3 sees one post.
- **Doxing patterns.** `B4` is a pattern task and belongs to M6, even though it
  sits in family B. The B head does not attempt it.

---

## 4. Contract

**Reads:** `ctx.text`, `ctx.normalized_text`

**Writes:**
- `out.signals["raw_score"]`, `out.signals["norm_score"]` — the binary offensive probability per channel
- `out.content` — one `ContentScore` per code and channel, `source = "m3_encoder@raw"` or `"m3_encoder@normalized"`: the family-A score on `A1` (ADR-005), `B1`–`B3` and `B5` from the B head (`B4` is M6's), `C1`–`C5` from the C head (ADR-006)
- `out.signals["artifact"]` — the artifact id that produced these scores

**Never** sets `threshold` or `fired`. **Never** fuses the two channels.

**Never** publishes embeddings or hidden states. No other module reads m3's representations; m5 (D1) runs its own model (ADR-003).

---

## 5. Base model and data

**Encoder:** `dbmdz/bert-base-turkish-cased` (BERTurk), fine-tuned on a frozen split.

**Training data — allowed:**
- Toraman v2 — large, but distributed as tweet IDs. **Measure and report the hydration loss** when you download it, together with the resulting class distribution. Licence is non-commercial share-alike; record it.
- TDDİ-2023 — available, but see the warning below about its label set.
- ATC — Turkish Instagram comments, roughly 10.5k offensive / 19.8k non-offensive.
- The Çöltekin OffensEval-TR corpus — 35,284 tweets as distributed (31,756 training + 3,528 test, verified file counts; the paper's 36,232 headline figure is not what the files hold, `docs/team/abdullah/RESOURCES.md` item 3), about 19% offensive, top-level annotator agreement κ ≈ 0.76. The test half is SPENT and locked; only the training half is used (`modules/m3_encoder/DATASETS.md`).

**Training data — banned outright:**

| Dataset | Reason |
|---|---|
| `Toygar/turkish-offensive-language-detection` | Merges `offenseval2020_tr`, which means direct leakage of the official closed test set. Using it invalidates every number you report. |
| `Overfit-GM/turkish-toxic-language` | Labels are pseudo-labels produced by models plus machine-translated Jigsaw data. Evaluating on it measures agreement with other models, not with humans. |

**Sequence length and truncation.** Declare the policy before training:
maximum sequence length, what happens to longer input, and whether the raw and
normalized channels truncate at the same point. They will not truncate
identically if de-obfuscation changes token count, which means the two channels
can end up judging different amounts of text. Measure how often that happens on
your own data and record it; if it is common, truncate both channels at the
same character offset rather than the same token count.

*Declared policy (implemented, `module.py`, `DATASETS.md`):* maximum sequence length **128
tokens** (the study's `max_len`, the value the frozen threshold was fitted with), the first tokens
kept and the rest dropped, on each channel independently; a note `truncated (<channel>): N tokens,
scored the first 128` whenever it happens, and `signals["truncated_differently"]` set when only one
channel was truncated (token counts stay internal). How often the channels truncate differently on
dev is measured once the normalized channel is scored on the corpus (the training package's
evaluation records both token counts); until then the same-token-count rule stands.


---

## 6. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Writing `fired` or `threshold` | Those belong to the decision layer. This separation is what lets the decision layer be re-tuned without retraining. |
| Fusing raw and normalized inside the module | Same reason. Report both, fuse downstream. |
| Swapping the encoder without full threshold re-derivation | A published comparison shows a modest consistent gain from a different Turkish encoder, but one of those checkpoints shows an anomaly on an independent Turkish benchmark. Verify the checkpoint before trusting it, and re-derive every threshold on dev if you switch. |
| Shipping a quantized or exported artifact with the old thresholds | Decision flip near the boundary is documented and large; far from the boundary it is negligible. Every artifact is a separate model with its own thresholds and its own hash. |
| Copying the TDDİ-2023 five-label scheme as your taxonomy | A TEKNOFEST-ecosystem judge will recognise it instantly. Use the data, not the label scheme. |
| Claiming an LLM baseline beats you | Published Turkish comparison: fine-tuned BERT ≈ 82% vs ChatGPT few-shot ≈ 66%. Cite it; it is in your favour. |

---

## 7. Metrics this module must produce

- **Per-code precision, recall, F1 with CIs.** Decomposed, never a single macro number.
- **Both channels reported separately.**
- **Comparison against a frozen baseline**: the current BERTurk with its current threshold. Every later improvement is measured against this fixed point.
- **Latency p50/p95 on the demo machine**, measured not estimated, reported as a distribution.
- **Decision-flip rate per export artifact** (PyTorch FP32, ONNX FP32, INT8 if attempted), as a function of distance from the threshold. Gate: flip far from the threshold must stay under 1%. An artifact that breaks the gate is excluded from the demo and documented — that is a maturity point, not a defect.

Note: published evidence shows the same model exported by the same toolchain giving two different scores in two reports. That is exactly why you measure **your** artifact rather than citing someone else's.

---

## 8. Artifact discipline

Every deployable artifact gets a row in `artifacts/MANIFEST.md`:

```
| artifact_id | format | sha256 | thresholds file | derived on | date |
```

The demo threshold is derived from the demo artifact itself. No exceptions.

---

## 9. Required fixtures

`fixtures/cases.jsonl` — `{"id": ..., "text": ..., "context": {"charsafe_text": ..., "normalized_text": ...}, "expected": [...], "expect": {...}}` (keys as read by `eval/harness.py`)

**Per code.** At least 20 positives per code in families A and B, and a matched
set of negatives. Codes with fewer than 20 report "insufficient sample" instead
of a metric — an F1 on eight examples is not a result.

**Multi-label proof.** At least five cases that are simultaneously two B codes
(a threat that is also an exclusion, defamation that is also degradation).
Assert both scores are present and neither suppresses the other. If the head
can only ever return one, it was built single-label by accident.

**Both channels.** For every obfuscated fixture, assert two entries exist with
sources `m3_encoder@raw` and `m3_encoder@normalized`, and that their scores are
reported independently. A fixture where the two channels disagree strongly is
the most valuable one in the file — keep several deliberately.

**Contract compliance.** On every fixture, assert every emitted `ContentScore`
has `threshold is None` and `fired is None`. This is the one rule most likely
to be broken accidentally when someone debugs a head locally.

**Determinism.** The same input twice produces the same score to full
precision. Model in eval mode, dropout off, seeds fixed. A non-deterministic
module makes every downstream number unrepeatable.

**Truncation.** BERTurk's maximum sequence length is 512 tokens; a 5000-character
Turkish post exceeds it. The truncation policy must be declared in §5 Base model and data
and tested: what is kept, what is dropped, and that a note is emitted
whenever truncation occurred. Silent truncation means the system judged a post
it never fully read, and a judge who pastes a long text will hit it.

**Artifact identity.** Assert `signals["artifact"]` is present, non-empty, and
matches a row in `artifacts/MANIFEST.md`. A score with no traceable artifact
cannot be reproduced.

**Leakage check.** A committed file listing every dataset in the training and
evaluation path, with an explicit line confirming neither banned dataset
appears. A written check, dated, not an assumption.

**Edge inputs.** Empty string, whitespace only, a single emoji, 5000
characters, and text mixing Turkish with another script.

---

## 10. Acceptance criteria

- [ ] Per-code metrics with CIs, both channels, committed as `eval/results/m3_encoder.json`.
- [ ] Frozen-baseline comparison present.
- [ ] Latency p50/p95 measured on the demo machine.
- [ ] Decision-flip table per artifact, with the gate result stated.
- [ ] `artifacts/MANIFEST.md` row exists with a real sha256.
- [ ] Hydration loss and final class distribution documented for any tweet-ID dataset.
- [ ] Proof that no banned dataset appears anywhere in the training or evaluation path — a written check, not an assumption.
- [ ] Heavy dependencies confined to `modules/m3_encoder/requirements.txt`.

---

## 11. Research pointers

- OffensEval-TR 2020 results — best reported macro-F1 is around 0.826. Anything far above that on the same task should make you look for leakage before you celebrate.
- Turkish encoder comparisons (BERTurk variants, ConvBERTurk, 128k-vocab variants) — read for the gain estimate and for the checkpoint anomaly warning.
- Quantization and ONNX export effects on classification thresholds.

---

## 12. Definition of done

All three heads train and score, both channels are reported, the artifact is hashed with its own thresholds, latency is measured on the real machine, and the banned-dataset check is written down.
