# Artifact manifest

Every file a module or the decision layer loads at runtime is listed here with
its sha256. Binaries are not committed (see `.gitignore`); this manifest is.
A module's `_load` must verify the hash and fail loudly on mismatch.

Compute a hash: `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <file>`

Columns (m3_encoder spec.md §8): `artifact_id | format | sha256 | thresholds_file | derived_on | date`,
plus `owner` and `licence`. Every deployable artifact has its own thresholds file, derived on that
artifact; `TBD` means the artifact does not exist yet.

| artifact_id | format | sha256 | thresholds_file | derived_on | date | owner | licence |
|---|---|---|---|---|---|---|---|
| thresholds-v0.1.0 | yaml (`decision/thresholds.yaml`) | per result: `AnalysisResult.artifact_hash` (config in use + module versions) | self | `binary_offensive` only: frozen dev `034415af…` CAL half, on `m3-berturk-pytorch-fp32-epoch1` (`protocols/threshold_derivation_binary_offensive_stage1.md`); every other row placeholder | 2026-09-15 | decision | in-repo |
| m1-lexicon | TBD (terlik lists + sacred-concept extension) | TBD | TBD | TBD | TBD | m1_lexicon | TBD — record per list (m1 spec.md §8) |
| m2-deobf-tables | TBD | TBD | TBD | TBD | TBD | m2_deobf | TBD |
| m3-berturk-pytorch-fp32-epoch1 | PyTorch FP32 state dict, `artifacts/m3_encoder/berturk_epoch1.pt` (`NSOSYAL_M3_CHECKPOINT`); the phase-01 study baseline `best.pt`, epoch 1 | `43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca` | `decision/thresholds.yaml` (`binary_offensive` only) | frozen dev split `034415af…`, CAL half (phase 12) | 2026-09-15 | m3_encoder | base model `dbmdz/bert-base-turkish-cased` (licence not verified in this session); fine-tuned on the Çöltekin OffensEval-TR training split only |
| m3-berturk-tokenizer | tokenizer + model config, `artifacts/m3_encoder/tokenizer/` (`NSOSYAL_M3_TOKENIZER`): `config.json` / `tokenizer.json` / `tokenizer_config.json` | `980b01dd…8f48` / `d424e0bc…61e5` / `d50873ed…0a04` (full digests in `modules/m3_encoder/module.py`) | n/a | n/a | 2026-09-15 | m3_encoder | same base model; copied from the study's demo bundle (`demo_assets/tokenizer`) |
| m4-implicit | TBD | TBD | TBD | TBD | TBD | m4_implicit | TBD |
| m5-sarcasm | TBD (own model, ADR-003; gated: m5 spec.md §2) | TBD | TBD | TBD | TBD | m5_sarcasm | TBD — record dataset name, version, size |
| m6-gazetteer-groups | text gazetteer, `modules/m6_target/gazetteers/groups_tr.txt` (committed) | `008078f9507ee450e27a5415cba1f2ab4eb822c0d9d62a0ad919a5222f5697e7` | n/a (stems, not scores) | n/a | 2026-09-17 | m6_target | project (in-repo, authored from the spec's categories; protocols/m6_target_guideline.md) |
| m6-gazetteer-non | text gazetteer, `modules/m6_target/gazetteers/non_human_tr.txt` (committed) | `73d75121179a40177d080e10384f29e12493207f1f0d58080a4319ee5555b050` | n/a (stems, not scores) | n/a | 2026-09-17 | m6_target | project (in-repo, authored from the spec's categories; protocols/m6_target_guideline.md) |

## Change log

| date | artifact_id | change | by |
|---|---|---|---|
| 2026-09-15 | m3-berturk-pytorch-fp32-epoch1, m3-berturk-tokenizer | added: study baseline wrapped as m3 inference; dev reproduction exact (0 label flips) | Musaab |
| 2026-09-17 | m6-gazetteer-groups, m6-gazetteer-non | added: m6_target v1 gazetteers (stems with suffix-aware matching), guideline protocols/m6_target_guideline.md | Musaab (assistant) |
| 2026-09-15 | thresholds-v0.0.0-placeholder -> thresholds-v0.1.0 | `binary_offensive` 0.50 -> 0.320188 (stage 1, r = 3), raw channel only | Musaab |
