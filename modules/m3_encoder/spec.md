# M3 — Shared Encoder, Three Heads

**Type:** detection
**Owner:** _assign_
**Note:** this is the heaviest module. It owns the only non-stdlib dependencies in the project.

---

## 1. Objective

One Turkish BERT encoder, three classification heads on top, so CPU latency and memory stay at single-model cost while each family keeps its own head and its own threshold.

```
                    ┌─ head_explicit    → A1..A4  (single-label)
ctx.text      ──┐   │
                ├─ BERTurk ─┼─ head_nonlexical → B1..B5  (MULTI-label)
ctx.normalized ─┘   │
                    └─ head_sarcasm     → D1
```

The encoder runs **twice per request**: once on the raw text, once on the normalized text from M2. Both score sets are reported. Fusion happens in the decision layer, not here.

---

## 2. Why multi-label for the B head

One post can be a threat and an exclusion at the same time. The reference taxonomy this project uses explicitly states its categories are not mutually exclusive and that more than one may apply to a single input. Forcing single-label on family B will destroy your agreement numbers.

Family A stays single-label because its codes differ by target, and target is resolved by M6.

---

## 3. Contract

**Reads:** `ctx.text`, `ctx.normalized_text`

**Writes:**
- `out.signals["raw_score"]`, `out.signals["norm_score"]` — the binary offensive probability per channel
- `out.content_scores` — one `ContentScore` per code, `source = "m3_encoder"`
- `out.signals["artifact"]` — the artifact id that produced these scores

**Never** sets `threshold` or `fired`. **Never** fuses the two channels.

---

## 4. Base model and data

**Encoder:** `dbmdz/bert-base-turkish-cased` (BERTurk), fine-tuned on a frozen split.

**Training data — allowed:**
- Toraman v2 — large, but distributed as tweet IDs. **Measure and report the hydration loss** when you download it, together with the resulting class distribution. Licence is non-commercial share-alike; record it.
- TDDİ-2023 — available, but see the warning below about its label set.
- ATC — Turkish Instagram comments, roughly 10.5k offensive / 19.8k non-offensive.
- The Çöltekin OffensEval-TR corpus — 36,232 tweets, about 19% offensive, top-level annotator agreement κ ≈ 0.76.

**Training data — banned outright:**

| Dataset | Reason |
|---|---|
| `Toygar/turkish-offensive-language-detection` | Merges `offenseval2020_tr`, which means direct leakage of the official closed test set. Using it invalidates every number you report. |
| `Overfit-GM/turkish-toxic-language` | Labels are pseudo-labels produced by models plus machine-translated Jigsaw data. Evaluating on it measures agreement with other models, not with humans. |

---

## 5. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Writing `fired` or `threshold` | Those belong to the decision layer. This separation is what lets the decision layer be re-tuned without retraining. |
| Fusing raw and normalized inside the module | Same reason. Report both, fuse downstream. |
| Swapping the encoder without full threshold re-derivation | A published comparison shows a modest consistent gain from a different Turkish encoder, but one of those checkpoints shows an anomaly on an independent Turkish benchmark. Verify the checkpoint before trusting it, and re-derive every threshold on dev if you switch. |
| Shipping a quantized or exported artifact with the old thresholds | Decision flip near the boundary is documented and large; far from the boundary it is negligible. Every artifact is a separate model with its own thresholds and its own hash. |
| Copying the TDDİ-2023 five-label scheme as your taxonomy | A TEKNOFEST-ecosystem judge will recognise it instantly. Use the data, not the label scheme. |
| Claiming an LLM baseline beats you | Published Turkish comparison: fine-tuned BERT ≈ 82% vs ChatGPT few-shot ≈ 66%. Cite it; it is in your favour. |

---

## 6. Metrics this module must produce

- **Per-code precision, recall, F1 with CIs.** Decomposed, never a single macro number.
- **Both channels reported separately.**
- **Comparison against a frozen baseline**: the current BERTurk with its current threshold. Every later improvement is measured against this fixed point.
- **Latency p50/p95 on the demo machine**, measured not estimated, reported as a distribution.
- **Decision-flip rate per export artifact** (PyTorch FP32, ONNX FP32, INT8 if attempted), as a function of distance from the threshold. Gate: flip far from the threshold must stay under 1%. An artifact that breaks the gate is excluded from the demo and documented — that is a maturity point, not a defect.

Note: published evidence shows the same model exported by the same toolchain giving two different scores in two reports. That is exactly why you measure **your** artifact rather than citing someone else's.

---

## 7. Artifact discipline

Every deployable artifact gets a row in `artifacts/MANIFEST.md`:

```
| artifact_id | format | sha256 | thresholds file | derived on | date |
```

The demo threshold is derived from the demo artifact itself. No exceptions.

---

## 8. Acceptance criteria

- [ ] Per-code metrics with CIs, both channels, committed as `eval/results/m3_encoder.json`.
- [ ] Frozen-baseline comparison present.
- [ ] Latency p50/p95 measured on the demo machine.
- [ ] Decision-flip table per artifact, with the gate result stated.
- [ ] `artifacts/MANIFEST.md` row exists with a real sha256.
- [ ] Hydration loss and final class distribution documented for any tweet-ID dataset.
- [ ] Proof that no banned dataset appears anywhere in the training or evaluation path — a written check, not an assumption.
- [ ] Heavy dependencies confined to `modules/m3_encoder/requirements.txt`.

---

## 9. Research pointers

- OffensEval-TR 2020 results — best reported macro-F1 is around 0.826. Anything far above that on the same task should make you look for leakage before you celebrate.
- Turkish encoder comparisons (BERTurk variants, ConvBERTurk, 128k-vocab variants) — read for the gain estimate and for the checkpoint anomaly warning.
- Quantization and ONNX export effects on classification thresholds.

---

## 10. Definition of done

Three heads train and score, both channels are reported, the artifact is hashed with its own thresholds, latency is measured on the real machine, and the banned-dataset check is written down.
