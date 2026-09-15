# Start here — your first hour on m3

## 1. Read the spec first

**`AI/modules/m3_encoder/spec.md` is the source of truth.** Read all of it
before opening any code. If this page, `docs/team/ABDULLAH.md` or anything else
disagrees with the spec, the spec wins, and you tell Musaab about the
disagreement.

Then read, in order:
1. [RESOURCES.md](RESOURCES.md): data, frozen split, frozen baseline, hyperparameters, the test-set rule, and what is still open.
2. [COLAB_SETUP.md](COLAB_SETUP.md): get a session to `SMOKE PASS` before any training.
3. `AI/CLAUDE.md`: the seven non-negotiable rules.

## 2. Two decisions from Musaab

**The C head (C1–C5) is DEFERRED.**
- No Turkish corpus is labelled with those categories, so there is nothing to
  train or measure it on.
- Build the **A head** and the **B head** now.
- Musaab is labelling a C slice in parallel.
- The spec's three-head design stands. Only the third head waits. Don't design
  the encoder in a way that makes adding the C head later harder.

**For m5, the sarcasm corpus is not yet named.**
- Your first research task on m5: find the exact **name, authors and contact**
  of the Turkish sarcasm corpus meant by m5 spec §2.
- Also record version and size. The spec warns that similar datasets get
  confused.
- **Report it to Musaab before you request access.** Don't contact the authors
  until he has seen it.
- The gate still applies. **No m5 code until the gate in m5 spec §2 resolves.**
  m5 stays a stub until then.

## 3. Your first deliverable: the A head

The A head's per-code metrics, **with confidence intervals, on the frozen
split** (`diagnosis/data/splits/split_seed42.json`, dev = 4,764 rows),
**compared against the frozen baseline** (phase 01 BERTurk, epoch 1, decision
threshold 0.5).

It must meet the spec:
- one "profanity present" score, on the `A1` carrier only, never `A2` or `A3`
  (spec §3)
- both channels reported separately: `m3_encoder@raw` and `m3_encoder@normalized`
  (spec §4, §7)
- `raw_score`, `norm_score` and `artifact` published; `threshold` and `fired`
  left as `None` (spec §4)
- truncation policy declared and the written banned-dataset check done
  **before** training (spec §5, §9)
- results from `python -m modules.m3_encoder.eval`

Two things you need for this are still open and waiting on Musaab
(RESOURCES.md, *Open* items 4 and 5):
- **Where the training code lives.** m3 module code cannot import
  `diagnosis/config.py`; the architecture test fails.
- **What gold label the A head is measured against.** The Çöltekin corpus is
  OFF/NOT only, with no "profanity present" label.

Don't guess either one. Ask.

## 4. Before every commit

Run from `AI/`. All three must pass. They passed on `master` on 2026-09-15.

```bash
cd AI
python -m unittest discover -p "test_*.py"
python -m modules.m3_encoder.eval
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```

Once m5 has code, also run `python -m modules.m5_sarcasm.eval`.

Never commit corpus text, prediction dumps or checkpoints. Never touch the
official test set.
