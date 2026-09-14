# Artifact manifest

Every file a module or the decision layer loads at runtime is listed here with
its sha256. Binaries are not committed (see `.gitignore`); this manifest is.
A module's `_load` must verify the hash and fail loudly on mismatch.

Compute a hash: `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <file>`

Columns (m3_encoder spec.md §7): `artifact_id | format | sha256 | thresholds_file | derived_on | date`,
plus `owner` and `licence`. Every deployable artifact has its own thresholds file, derived on that
artifact; `TBD` means the artifact does not exist yet.

| artifact_id | format | sha256 | thresholds_file | derived_on | date | owner | licence |
|---|---|---|---|---|---|---|---|
| thresholds-v0.0.0-placeholder | yaml (`decision/thresholds.yaml`) | per result: `AnalysisResult.artifact_hash` (config in use + module versions) | self | not derived (placeholder) | 2026-09-14 | decision | in-repo |
| m1-lexicon | TBD (terlik lists + sacred-concept extension) | TBD | TBD | TBD | TBD | m1_lexicon | TBD — record per list (m1 spec.md §8) |
| m2-deobf-tables | TBD | TBD | TBD | TBD | TBD | m2_deobf | TBD |
| m3-berturk-pytorch-fp32 | TBD (PyTorch FP32) | TBD | TBD | TBD | TBD | m3_encoder | base model `dbmdz/bert-base-turkish-cased`: verify on model card; datasets per m3 spec.md §4 |
| m4-implicit | TBD | TBD | TBD | TBD | TBD | m4_implicit | TBD |
| m5-sarcasm | TBD (own model, ADR-003; gated: m5 spec.md §2) | TBD | TBD | TBD | TBD | m5_sarcasm | TBD — record dataset name, version, size |
| m6-target | TBD | TBD | TBD | TBD | TBD | m6_target | TBD |

## Change log

| date | artifact_id | change | by |
|---|---|---|---|
| | | | |
