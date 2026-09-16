# Start here — Abdullah

Specs in `AI/modules/*/spec.md` are the source of truth; if this page disagrees, the spec wins and you tell Musaab.

## Where m3 stands
- **m3 inference is done** (commit `0bb9d25`): it wraps the frozen epoch-1 BERTurk baseline and publishes `raw_score` + `artifact`. Dev reproduction was exact (0 label flips).
- **The A, B and C heads are deferred.** No labelled data exists for any of them. Do not build a head.

## Setup (from `AI/`)
```bash
python -m pip install -r requirements.txt -r modules/m1_lexicon/requirements.txt
python -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r modules/m3_encoder/requirements.txt
```
- Get `demo_assets/` from Musaab via Drive. It is **not in git**. You need `checkpoints/best.pt` (sha256 `43a20d55…`, full digest in `AI/artifacts/MANIFEST.md`) and `tokenizer/`.
- Point m3 at them: `export NSOSYAL_M3_CHECKPOINT=<path>/demo_assets/checkpoints/best.pt` and `export NSOSYAL_M3_TOKENIZER=<path>/demo_assets/tokenizer`. m3 checks every sha256 and fails closed on a mismatch.
- Then `python -m unittest discover -p "test_*.py"` must pass.
- **Every team member** needs `demo_assets/` from Musaab via Drive and the m1 + m3 requirements installed; otherwise the contract-example check in `check.sh` fails.

## Task 1 today: the m5 sarcasm corpus
- m5 spec §2 describes the main Turkish sarcasm corpus but does not name it (recent, distributed on request, 1,515 samples, accuracy 0.73 / 0.76 with title context). Identify it: exact name, authors, version, size, contact.
- Request access from the authors.
- Record the corpus name and the request (date, who, how) in `AI/modules/m5_sarcasm/spec.md` §2. No m5 code until the gate resolves.

## Task 2 while waiting: m6_target v1
- Build `m6_target` to `AI/modules/m6_target/spec.md`: gazetteer plus morphology, **no transformer** (ADR-007).

Before every commit, from `AI/`: the unit tests, `python -m eval.run_all`, and `BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh`. Never commit data, checkpoints or corpus text; never touch the official test set.
