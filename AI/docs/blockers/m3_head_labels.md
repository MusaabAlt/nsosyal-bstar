# BLOCKER — m3's three heads need labelled data the repository does not have

- **Component:** `m3_encoder` heads A (profanity present), B (`B1`,`B2`,`B3`,`B5` multi-label),
  C (`C1`–`C5`); downstream `m4_implicit` rows `C1`–`C5` and the stage-2 slice
- **State:** A = **DECIDED 2026-09-18** (below); pseudo-label **rule v3** frozen and generated →
  WAITING_FOR_GPU_ARTIFACT for the retraining. Evaluation reference: the 500-row AI-assisted,
  human-adjudicated dev reference (evaluation only, not a human oracle). A threshold NOT DERIVED;
  B = BLOCKED_BY_DATA; C = BLOCKED_BY_DATA. Training code and the Colab handoff are engineering
  work and are provided (`docs/training/m3_encoder.md`).
- **Written:** 2026-09-17. Sources: `docs/team/abdullah/RESOURCES.md` open items 5–7, m3 spec §5, §9.

## Owner decisions, 2026-09-18 (A head)

1. **HYBRID strategy.** Training supervision: regenerated terlik-derived pseudo-labels on the
   frozen TRAIN split (`eval/derived/m1_lexicon_train_seed42.json`, field `a_label`,
   `protocols/m1_lexicon_train_labels_protocol.md`). Scientific evaluation: a separately
   human-labelled "profanity present" subset of the frozen DEV split
   (`docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md`, `python -m eval.a_head_dev_sample`). The human
   dev subset is the authoritative oracle for any reported A-head quality claim; terlik agreement is
   reported as agreement (`dev_eval.json` → `a_pseudo_label_agreement`), never as accuracy.
2. **Pseudo-label signal:** `lexicon_hit` (raw OR normalized), not `lexicon_hit_raw` alone; a
   normalized-only hit counts only when its mapping back to the original text is valid (ADR-008
   spans). Recorded in the train protocol §5 and reconciled with Q5 / ADR-008 there (label half
   decided, runtime half unchanged).
3. **`AI/training/` ratified** as the official home of training code (`training/README.md`).
4. **No binary-only Colab run first**: the useful path is the binary + A-head run.
5. **Never used as A-head labels:** karaliste, OFF/NOT gold, baseline-model predictions.

## Second pass, 2026-09-18 — the first candidate was semantically misaligned; rule v2

The first GPU candidate reproduced its supervision: pseudo-label rule v1 labelled any terlik match
positive, and terlik's dictionary is mostly ordinary insults, which guideline v1.1 scores `0`
(`docs/training/runs/m3-berturk-multihead-2026-09-18.md`). No A threshold is derived from it.

- **Rule v2** (`protocols/m1_lexicon_train_labels_protocol.md`, amendment): positive only on
  terlik's `sexual` class plus the roots the sealed guideline names (`bok`, `piç`, `oç`); ordinary
  insults, threats and sacred-concept entries excluded; 11 undecided roots masked (`null`), not
  guessed. Train: 1,463 positive / 25,398 negative / 131 masked (rule v1: 2,514). Dev: 239 / 4,489
  / 36 (rule v1: 449).
- **Owner decision still required:** the 11-root REVIEW table in that amendment (orospu, gavat,
  pezevenk, kahpe, sürtük, kaltak, fahişe, ibne, puşt, oğlancı, tabanvansen). Deciding it makes
  the rule v3 and the files are regenerated.
- **Consequent question, not decided here:** m1 itself still emits the A1 carrier at runtime on
  every terlik match, ordinary insults included. Whether the runtime A-family signal should follow
  the same explicit-profanity class is a production decision for the owner; this pass changed
  only the training labels and the `amin` defect.
- The 500-row AI-assisted, human-adjudicated reference is evaluation only — never a training
  label, never a source of rule edits.

## Third pass, 2026-09-18 — rule v3 frozen (resolves the second pass's REVIEW table)

- **Owner decisions:** `kahpe`, `sürtük`, `kaltak`, `kancık` → EXCLUDED; `pezevenk`, `gavat` →
  POSITIVE (confirmed); `kevaşe` → EXCLUDED (confirmed); the rest of the rule-v3 taxonomy review
  approved as proposed.
- **Rule v3** (`protocols/m1_lexicon_train_labels_protocol.md`, amendment (b), committed at
  `abbd313` before any v3 label existed): A = an explicit obscene / profane lexical root; an explicit
  list of 17 POSITIVE and 130 EXCLUDED roots over the whole pinned dictionary; the REVIEW class is
  empty, so no row is masked.
- **Labels regenerated from rule v3:** train 1,528 positive / 25,464 negative / 0 masked; dev 257 positive / 4,507 negative / 0 masked.
- **Where each rule stands:** rule v1 — the supervision of the first GPU candidate, historical and
  semantically misaligned for A; rule v2 — an intermediate taxonomy experiment, superseded; rule v3
  — the current frozen A pseudo-label definition.
- **Unchanged:** the 500-row reference stays AI-assisted, human-adjudicated and evaluation-only; no
  A threshold is derived; the production m3 artifact stays `m3-berturk-pytorch-fp32-epoch1`; m1's
  runtime A1 on ordinary insults remains an open production question.
- **Open findings (not fixed here):** `amin!` with one `!` attached still reaches A1 through m2's
  LEET channel, because `!` is read as `i` and gives `amini`; m1's guard is deliberately not
  broadened, and no train or dev row is affected. m1 joins collision-evidence roots from a set, so
  their order in the evidence text depends on the Python hash seed; labels are unaffected.

Item (b) of the original decision request — which m3 output is compared with the baseline's
binary numbers — is answered by the handoff §28: the new artifact's **binary head** at the study's
0.5 reporting point on the same 4,764 dev rows, against the frozen baseline's 0.8271 [0.8139, 0.8405].

## What exists

| resource | state |
|---|---|
| Çöltekin OffensEval-TR training corpus, 31,756 rows, OFF/NOT only | on this machine (`diagnosis/data/coltekin/`), sha256 verified by the study |
| frozen split (26,992 train / 4,764 dev, seed 42) | committed (`diagnosis/data/splits/split_seed42.json`) |
| per-row terlik labels on the dev split (`lexicon_hit_raw`, matches, collisions) | committed (`eval/derived/m1_lexicon_dev_seed42.json`, protocol-bound) |
| official test set | SPENT and locked; never used |

## A head — "profanity present"

- The corpus has no "profanity present" gold; OFF/NOT is not it (an OFF post may have no profane
  root; 63.5 % of OFF posts in the study are lexicon-free).
- The derived-labels protocol proposes m1's terlik labels as the training signal for the A head
  (`protocols/m1_lexicon_dev_labels_protocol.md` §1). That file covers the **dev** split only;
  the same generator can label the train split.
- **Decision (owner, 2026-09-18, RESOURCES item 5): BOTH** — the terlik signal is the training
  label (a keyword label; it disagrees with the frozen karaliste slice on roughly half of the
  karaliste hits — Q19) **and** a human-labelled "profanity present" dev subset is required for
  any quality claim. See "Owner decisions" above.
- Engineering delivered: the train-split generator and the committed train file, the dev file
  regenerated on the implemented modules, the trainer's separate `--labels-a` (pseudo, supervision)
  and `--labels-a-human` (oracle, dev only, refused on train rows) inputs, and the annotation
  package (guideline, sampler, check / adjudicate / export).

## B head — `B1` degradation, `B2` threat, `B3` curse/exclusion, `B5` sexual aggression (multi-label)

- No corpus labelled with B codes exists in the repository or on this machine (RESOURCES item 6).
  The allowed sources in spec §5 (Toraman v2 tweet IDs, TDDİ-2023, ATC) are not present and each
  needs download, hydration (with the hydration loss reported) and a licence record; TDDİ's label
  scheme must not be copied as the taxonomy (spec §6).
- **Needed:** a B-labelled Turkish set under the project's guideline (`protocols/templates/annotation_guideline.md`,
  the B/C boundary rule of m4 spec §3), with at least 20 positives per code and multi-label cases
  (spec §9), plus agreement per code. Either an external corpus mapped to B1/B2/B3/B5 by a written
  mapping the owner approves, or in-house annotation.

## C head — `C1`–`C5`

- The C slice is being labelled by the owner with no date (RESOURCES item 7). Sample-size guidance
  in m4 spec §8 (400 positives → ±4.8 points). Negative controls of m4 spec §9 are mandatory
  (counter-speech, meta-discussion, self-criticism, factual group statements, negation).
- **Needed:** the labelled slice with per-category agreement and the sealed guideline, plus the
  frozen dev evaluation slice for the before/after numbers.

## What engineering delivers now

- `training/m3_encoder/`: dataset loading through the study's own reader (no `pandas`), the frozen
  split enforced, a three-head model (shared BERTurk, A sigmoid, B multi-label sigmoid, C softmax
  or sigmoid per the guideline), leakage guard (banned datasets refused by name; test set refused
  by the study's lock), seeds, checkpointing, artifact export with sha256, and a dev evaluation
  that writes per-code metrics with CIs on both channels. Runs on CPU for a smoke test; the real
  run is the Colab handoff.
- The banned-dataset written check and the truncation policy statement (m3 spec §9, §10).

## What happens meanwhile

m3 publishes `raw_score` (and, once m2 exists, `norm_score`) from the frozen binary artifact;
no content code is emitted; `implementation_status.json` lists the heads under `not_built`.
