# GPU handoff index

Every GPU-dependent task the project still needs executed. Each row points at a self-contained
handoff document that can be followed on Colab Pro+ without guessing. A task leaves this list only
when its artifact has been returned to the repository, registered in `artifacts/MANIFEST.md` with a
real sha256, and verified by the commands in its handoff.

State vocabulary: `WAITING_FOR_GPU_ARTIFACT` (code and handoff complete, GPU run pending),
`BLOCKED_BY_DATA` (the handoff cannot be executed until named data exists),
`BLOCKED_BY_POLICY` (an owner decision precedes the run), `RETURNED_UNVERIFIED`, `VERIFIED`.

| task | consumer | handoff | state | blocked on |
|---|---|---|---|---|
| m3 three-head fine-tune (A / B / C on BERTurk) | `modules/m3_encoder` | `m3_encoder.md` | BLOCKED_BY_DATA (B, C) · BLOCKED_BY_POLICY (A label source) · code: pending | `docs/blockers/m3_head_labels.md` |
| m4 stage 2 influence-function hardening (retrains m3's encoder) | `modules/m4_implicit`, `decision/thresholds.yaml` C rows | `m4_stage2.md` | BLOCKED_BY_POLICY (pre-registered precision budget, Q23) · BLOCKED_BY_DATA (labelled C slice) | m4 spec §7, §10 |
| m5 sarcasm sequential transfer (own small model) | `modules/m5_sarcasm` | `m5_sarcasm.md` | BLOCKED_BY_DATA (entry gate, Q27) | `docs/blockers/m5_sarcasm_corpus_gate.md` |

Rules that apply to every handoff:

- The official Çöltekin test set is SPENT and locked (`diagnosis/src/data_io.py`); no handoff reads it.
- Training uses the frozen split `diagnosis/data/splits/split_seed42.json` (fingerprint `034415af…`);
  a handoff never creates a split.
- Banned datasets (`Toygar/turkish-offensive-language-detection`, `Overfit-GM/turkish-toxic-language`)
  are refused by name in the training code and listed in `modules/m3_encoder/DATASETS.md`.
- Every returned artifact gets a `MANIFEST.md` row (`artifact_id | format | sha256 | thresholds_file
  | derived_on | date | owner | licence`) and its **own** thresholds derivation on dev before any
  verdict uses it (m3 spec §8; `protocols/templates/threshold_derivation.md`).
- Returned artifacts are placed under `AI/artifacts/<module>/` (git-ignored) and referenced through
  the module's environment overrides where they exist.
