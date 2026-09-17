# BLOCKER — m3's three heads need labelled data the repository does not have

- **Component:** `m3_encoder` heads A (profanity present), B (`B1`,`B2`,`B3`,`B5` multi-label),
  C (`C1`–`C5`); downstream `m4_implicit` rows `C1`–`C5` and the stage-2 slice
- **State:** A = BLOCKED_BY_POLICY (label source undecided) + WAITING_FOR_GPU_ARTIFACT;
  B = BLOCKED_BY_DATA; C = BLOCKED_BY_DATA. Training code and the Colab handoff are engineering
  work and are provided (`docs/training/m3_encoder.md`).
- **Written:** 2026-09-17. Sources: `docs/team/abdullah/RESOURCES.md` open items 5–7, m3 spec §5, §9.

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
- **Decision required (owner, RESOURCES item 5):** (a) is the terlik signal accepted as the A-head
  training label (a keyword label, not a human label, and it disagrees with the frozen karaliste
  slice on roughly half of the karaliste hits — Q19), or is a human-labelled "profanity present"
  slice required? (b) Which m3 output is compared with the baseline's binary numbers?
- Engineering prepared: the training script accepts a label file per split so either answer plugs
  in without code change; the handoff describes both.

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
