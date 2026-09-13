# Artifact manifest

Every file a module or the decision layer loads at runtime is listed here with
its sha256. Binaries are not committed (see `.gitignore`); this manifest is.
A module's `_load` must verify the hash and fail loudly on mismatch.

Compute a hash: `python -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <file>`

| id | path | sha256 | owner | source / license | derived on | status |
|---|---|---|---|---|---|---|
| thresholds-v0.0.0-placeholder | `decision/thresholds.yaml` | computed at runtime into `AnalysisResult.artifact_hash` | decision | in-repo | not derived | PLACEHOLDER |
| lexicon | `artifacts/m1_lexicon/lexicon.jsonl` | TBD | m1_lexicon | TBD | - | not created |
| suffix-automaton | `artifacts/m1_lexicon/suffixes.json` | TBD | m1_lexicon | TBD | - | not created |
| deobf-tables | `artifacts/m2_deobf/` (leet, unigram freq, deasciifier patterns) | TBD | m2_deobf | TBD | - | not created |
| berturk-3head-int8 | `artifacts/m3_encoder/model.onnx` + tokenizer | TBD | m3_encoder | dbmdz/bert-base-turkish-cased (license: verify on model card), fine-tuned | - | not created |
| implicit-head + calibrators | `artifacts/m4_implicit/` | TBD | m4_implicit | TBD | - | not created |
| sarcasm-head (stage 2) | `artifacts/m5_sarcasm/` | TBD | m5_sarcasm | sarcasm corpus: TBD (record license) | - | not created |
| gazetteers | `artifacts/m6_target/` | TBD | m6_target | TBD | - | not created |

## Change log

| date | id | change | by |
|---|---|---|---|
| | | | |
