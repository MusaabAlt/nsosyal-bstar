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
| m3 multi-head fine-tune (binary + A / B / C on BERTurk) | `modules/m3_encoder` (loader for the artifact format exists: `NSOSYAL_M3_ARTIFACT`) | `m3_encoder.md` | **RULE-V3 RUN DONE, reviewed, not promoted** (`m3-berturk-multihead-a-rule-v3-20260918-074806`, weights `41d98d7f…`, `runs/m3-berturk-multihead-a-rule-v3-20260918-074806.md`; A operating point fixed at 0.50 by A-OP-1; next: its `binary_offensive` threshold, §34; no further GPU run needed). Earlier state: READY_FOR_COLAB for the binary + A-head RETRAINING under pseudo-label rule v3 (the frozen explicit taxonomy; rule v2 was an intermediate experiment; new run id and artifact id; the first run `m3-berturk-multihead-2026-09-18` is frozen as TECHNICALLY_VALID_BUT_A_SEMANTICALLY_MISALIGNED, `runs/m3-berturk-multihead-2026-09-18.md`). Earlier state: READY_FOR_COLAB for the binary + A-head run (owner decisions 2026-09-18: HYBRID A-head strategy; pseudo-labels `eval/derived/m1_lexicon_train_seed42.json` committed; code smoke-tested on CPU, `training/tests/test_training_m3.py`). The A head is evaluated only against the 500-row AI-assisted, human-adjudicated dev reference (evaluation only, not a human oracle); no A threshold is derived (A-OP-1 fixes the rule-v3 candidate's at 0.50); the run itself was not blocked on it. B and C BLOCKED_BY_DATA | `docs/blockers/m3_head_labels.md` |
| m4 stage 2 influence-function hardening (retrains m3's encoder) | `modules/m4_implicit`, `decision/thresholds.yaml` C rows | `m4_stage2.md` | BLOCKED_BY_POLICY (pre-registered precision budget, Q23) · BLOCKED_BY_DATA (labelled C slice); procedure written, mining script not yet written | m4 spec §7, §10 |
| m5 sarcasm sequential transfer (own small model) | `modules/m5_sarcasm` (still a stub; the artifact format is defined by `training/m5_sarcasm/train.py`) | `m5_sarcasm.md` | BLOCKED_BY_DATA (entry gate, Q27) — code complete (`training/m5_sarcasm`), no smoke test yet (needs a D1 jsonl) | `docs/blockers/m5_sarcasm_corpus_gate.md` |

Last updated 2026-09-18 (fourth pass: rule-v3 candidate trained and reviewed; A-OP-1; metadata correction prepared).

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
