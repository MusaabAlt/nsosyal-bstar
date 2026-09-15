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
| `karaliste.txt` | frozen Day 1 | not used here | spec §5: historical comparison only; the study slice built from it is frozen in `AI/eval/frozen/study_slice_dev.json` |

## Not built yet

- `A4` sacred-concept extension and its source table (spec §4.3, §8).
- `HOMONYM` guard (spec §3).
- terlik vs karaliste comparison, recall/FPR with CIs on a functional test set (spec §6, §8).
