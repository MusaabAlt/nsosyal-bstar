# BLOCKER — m5 entry gate: the Turkish sarcasm corpus must be identified and requested

- **Component:** `m5_sarcasm` (`D1`), spec §2 (entry gate), §11 (gate record), §12
- **State:** BLOCKED_BY_DATA (external access, human request)
- **Written:** 2026-09-17

## What the spec requires before any m5 code

Spec §2: identify the main Turkish sarcasm corpus (described as recent, distributed on request,
1,515 samples, accuracy 0.73 without / 0.76 with title context), **contact the authors**, and
record one of three outcomes:

| outcome | consequence |
|---|---|
| granted | full plan: sequential transfer (pre-train on sarcasm, fine-tune on the offensive task), own small/distilled model, own artifact and thresholds (ADR-003) |
| refused | the smaller public Turkish irony dataset; every result labelled exploratory |
| neither | the `D1` claim is dropped from the project, in writing |

Spec §11 requires a committed **gate record**: exact dataset name, version, size, and the date
access was granted or refused. `docs/team/abdullah/START_HERE.md` task 1 assigns this to the m5
owner and requires the corpus name to be reported to Musaab before any access request.

## Why engineering cannot resolve it

The corpus is distributed on request by its authors; obtaining it is a human action with a
licence agreement. Substituting an arbitrary dataset is forbidden by the spec ("record the exact
name, version and size of whatever you use") and by the project's data rules. No sarcasm or irony
data exists on this machine (`diagnosis/data/` holds only the Çöltekin corpus, the lexicon, the
deixis definition and the frozen split).

## Exactly what is needed

1. The owner (or the m5 owner) names the corpus — exact title, authors, year, version, size — and
   sends the access request; the request is recorded in `modules/m5_sarcasm/spec.md` §2 as
   START_HERE asks.
2. On reply, the gate record file `modules/m5_sarcasm/GATE_RECORD.md` with the outcome and date.
3. If granted: the files, their sha256s and licence, placed under `diagnosis/data/sarcasm/` (never
   committed), listed in `artifacts/MANIFEST.md` once an artifact exists.
4. The benign-sarcasm control set (spec §8, §11: sarcasm at objects, weather, software, traffic,
   a match result) and the sincere-praise negatives — these must be **annotated by humans** under
   the polarity-inversion rule of spec §5; a template guideline is in
   `protocols/templates/annotation_guideline.md`.

## What engineering will prepare regardless

- Training and inference scaffolding for a small Turkish classifier with sequential transfer,
  as a Colab handoff (`docs/training/m5_sarcasm.md`), parameterised by the dataset paths and the
  gate outcome, so that the only missing step is the data and the GPU run.
- The fixture schema (`inversion_span`) and the unit-test skeletons that assert it.

Until the gate resolves, `m5_sarcasm` stays a documented stub (`stub = True`), every result is
degraded by it, and its report says `NOT VERIFIED`.
