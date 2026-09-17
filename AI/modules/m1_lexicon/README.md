# m1_lexicon

Runtime lexicon signal. `spec.md` is the source of truth; this file records the
resources used (spec §8: licence of every list).

Install: `python -m pip install -r modules/m1_lexicon/requirements.txt`.
Without `terlik` the module loads with `ok=False` and says so in its notes.

## Lists and licences

| Resource | Version | Licence | Used for |
|---|---|---|---|
| `terlik` (PyPI, Python port of `badursun/terlik.js`) | 0.1.0, pinned | MIT | roots, suffix engine, balanced mode; its `suffixable` flag per root is the two-tier (hard/soft) split of spec §4.2 |
| `CLEAN_PREFIXES` in `module.py` (`amca`, `sikinti`) | this repo | project | clean words terlik 0.1.0 reads as root + suffix; each has its reason in the code |
| `karaliste.txt` | frozen Day 1 | not used here | spec §5: historical comparison only; the study slice built from it is frozen in `AI/eval/frozen/study_slice_dev.json`; compared against terlik under `protocols/m1_terlik_vs_karaliste_protocol.md` (below) |
| `HOMONYMS` in `module.py` (`am` as the time abbreviation: `10 am`, `10:30 am`, `am/pm`) | this repo | project | spec §3 / §7 `HOMONYM` guard: a matched root whose standalone surface is an innocent word in a declared context; the guard carries the match's span so only that match is suppressed (ADR-001). Add a row here for every new entry, with its context rule |
| second-person / dual-register words (`moruk`, `lan`, `oğlum`) | — | — | not lexicon entries: spec §7 requires they never auto-fire; terlik 0.1.0 does not match them, pinned by `test_dual_register_words_never_auto_fire` and the fixtures |

## Spans

A terlik match containing a space is cut to the shortest token-boundary prefix terlik still
matches with the same root (`salak mısın` → `salak`, `s a l a k` stays whole), and a hit strictly
inside another hit is dropped (the spurious `a k` → `amk` inside a spaced word). Raw-channel spans
map through m0's `_offsets`, normalized-channel spans through m2's (ADR-008).

## terlik versus karaliste (spec §6, §8) — measured 2026-09-17 on the frozen dev split

`eval/results/m1_terlik_vs_karaliste.json` (committed under its protocol; 4,764 rows, 920 OFF,
2,000 bootstrap resamples, seed 42), each lexicon read as a predictor of OFF:

| lexicon | hits | recall | FPR |
|---|---|---|---|
| karaliste (frozen slice) | 614 | 0.386 | 0.067 |
| terlik balanced (m1) | 459 | 0.392 | 0.026 |
| terlik − karaliste | | +0.007 [−0.022, +0.037] | **−0.042 [−0.050, −0.034]** |

Disagreement: 311 rows hit only by karaliste, 156 only by terlik, 303 by both; on gold-OFF rows
91 karaliste-only vs 97 terlik-only. terlik reaches the same recall with less than half the false
positive rate. The frozen evaluation slice stays karaliste's (spec §1).

## Not built yet

- `A4` sacred-concept extension and its source table (spec §4.3, §8): needs the owner-approved
  table, `docs/blockers/m1_a4_sacred_concepts.md`.
- Recall / FPR with CIs on a *functional* test set (spec §6): only the dev-split comparison above
  exists; a functional set is an annotation task.
