# training/ — model training code (outside the modules)

`docs/team/abdullah/RESOURCES.md` open item 4 left undecided where m3's training code lives and
how it receives corpus paths: a module folder may import only the standard library, `contracts`,
its own package and what its `requirements.txt` declares, and the corpus reader lives in
`diagnosis/src/data_io.py`. This directory is the answer, **RATIFIED by the owner on 2026-09-18**
(decision 3: `AI/training/` is the official location for project training code):

- **Training code lives in `AI/training/<module>/`**, one package per model-owning module. It is
  not a module (never in `PIPELINE_ORDER`, never imported by a module), so rule 2 and the
  architecture scanners do not apply to it; it is not core either, so it may import the heavy
  libraries its own `requirements.txt` declares and reach the study's reader by putting the
  repository's `diagnosis/` on `sys.path` (the way the study's own scripts and the Colab smoke test
  already do).
- **Paths come from the environment or the command line, never from constants**: the corpus root
  through `NSOSYAL_DATA` (the variable `diagnosis/config.py` already honours) or `--corpus`, the
  frozen split through its committed path, the output directory through `--out`.
- **Guards are inherited, not re-implemented**: the frozen split is loaded with
  `data_io.get_split` (which verifies the corpus hash and refuses to create a split), the official
  test set stays behind `data_io.load_coltekin_test`'s lock, and banned dataset names are refused
  before any file is opened.
- **Artifacts leave through `export`**: a versioned directory under `AI/artifacts/<module>/`
  (git-ignored) with weights, head layout, tokenizer files, a `sha256.txt`, and the row text for
  `artifacts/MANIFEST.md`. The module's `_load` verifies every digest before use.
- **The GPU step is the only step not run here.** Each package has a CPU smoke test on a handful
  of rows; the real run is the Colab handoff in `docs/training/`.

| package | consumer | handoff |
|---|---|---|
| `training/m3_encoder/` | `modules/m3_encoder` | `docs/training/m3_encoder.md` |
| `training/m5_sarcasm/` | `modules/m5_sarcasm` | `docs/training/m5_sarcasm.md` |

Nothing under `training/` runs at inference time.
