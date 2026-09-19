# Protocol — m2_deobf per-pattern evaluation set and the leakage rule

- **Status:** pre-registered 2026-09-17, before any m2 capture-rate number exists (m2 spec §10:
  "Write this separation into the protocol file before producing any number").
- **Governs:** `modules/m2_deobf/fixtures/cases.jsonl` (the generated per-pattern pairs),
  `eval/m2_obfuscation_pairs.py` (the generator), the capture-rate and damage-rate numbers in
  `eval/results/m2_deobf.json`, and the clean-to-dirty flip rate on the trap list.

## 1. What is measured

Per pattern code (never aggregated, spec §8): the **capture rate** — the share of generated
clean↔obfuscated pairs for which m2's `normalized_text` restores the clean surface of the
obfuscated token, with the pattern reported — and, on the clean side of every pair and on the
trap list, the **damage rate** and the **clean-to-dirty flip rate**. Confidence intervals are
percentile bootstrap over pairs (harness default, 1000 resamples, seed 20240901).

The headline number of spec §8 (recall under pattern P before / after the channel) is **not**
produced under this protocol: it needs a detector scored on both channels and a labelled paired
set of positives outside training data; where that measurement lives is undecided (U-M2-3).

## 2. The leakage rule (spec §10)

The evaluation generator is separate from any training-augmentation generator:

| | evaluation (this protocol) | training augmentation (m3 / m4, if ever) |
|---|---|---|
| code | `eval/m2_obfuscation_pairs.py` | `diagnosis/src/obfuscation.py` family `D` (vowel delete, digit homoglyph, repeat) or a future `training/` generator |
| seed | 20260917 | anything else; never 20260917 |
| operators | the per-code rules of §3 below, written independently of `diagnosis/src/obfuscation.py` | the study's `D` operators |
| source words | the clean tokens of m2's own fixture sentences and the trap words; **no corpus row** | corpus rows |

`eval/m2_obfuscation_pairs.py` asserts at import that its operator names are disjoint from
`diagnosis.src.obfuscation.OPERATORS["D"]` when that module is importable, and refuses to run with
seed 0 (the study's default rng) or any seed listed in a training protocol.

## 3. Generators, one per pattern code (v1 scope)

Each generator takes a clean token of ≥ 4 letters and returns the obfuscated surface and the
expected repaired surface. Pairs whose obfuscated form equals the clean form are discarded.

| code | operator | example |
|---|---|---|
| `LEET` | replace one or two letters by the table `a→4 e→3 i→1 o→0 s→5 t→7 b→8 g→9` | `salak → s4lak` |
| `REPEAT` | stretch one or two letters to 3–5 copies | `salak → saaalak` |
| `SPACED` | single spaces between every letter | `salak → s a l a k` |
| `PUNCT_SPLIT` | one separator from `. - _ , / + |` between every letter | `salak → s.a.l.a.k` |
| `HOMOGLYPH` (accent) | one vowel gets a non-Turkish accent (`á à ã é è ó ò ú ù`) | `aptal → áptal` |
| `PHONETIC` | `k→q`, `v→w`, `ks→x` where present | `siktir → siqtir` |
| `DEASCII` | Turkish letters flattened (`ş→s ç→c ğ→g ı→i ö→o ü→u`) on a token that has at least one and whose flattened form is not itself a declared ambiguity | `şerefsiz → serefsiz` |
| `SUFFIX_ON_MASKED` | one inner letter replaced by `*` | `siktir → s*ktir` (expected: reported, text unchanged) |

Patterns declared unhandled in v1 (`ABBREV`, `VOWEL_DROP`, `WORD_MERGE`, `CHAR_DROP`, `DIALECT`,
`EMOJI_SUB`) get no generated pairs and no number; the results file lists them as `unhandled`.

## 4. Sample sizes

At least 10 pairs per code (spec §9); a code with fewer reports "insufficient sample". The
generated set is committed in `fixtures/cases.jsonl` with `"generated_by": "eval/m2_obfuscation_pairs.py", "seed": 20260917`
on every generated item, so a regeneration is byte-identical.

## 5. Human spot-check (spec §8, §11)

Before a capture-rate number is quoted in any report, a sample of 20 generated pairs is read by a
human and the count of unnatural or wrong pairs is recorded in `eval/results/m2_deobf.json`
under `human_spot_check` (`{n, wrong, date, who}`). Missing → the number is labelled unverified.

## 6. The real-obfuscation slice (spec §8, §9)

A separately collected set of genuinely obfuscated Turkish posts, never used to tune the rules,
stored as `fixtures/real_obfuscation.jsonl` when it exists; its capture rate is reported next to
the generated one and the gap is a published number. Its collection is a human task and is
BLOCKED_BY_DATA until done; the results file says so.

## 7. Failure conditions

- Any trap in `eval/traps/traps.jsonl` that flips from no fired content code to a fired one when
  m2 runs (`clean_to_dirty_flip_rate` above `budgets.clean_to_dirty_flip_rate`) → tier 2 is
  disabled by configuration, tier 1 stays, the outcome is a measured negative (spec §11).
- A generated pair whose clean side is changed by m2 (damage) counts against the damage rate;
  a damage rate above zero on the clean fixture is reported, not hidden.
- Idempotency failure on any fixture (`f(f(x)) != f(x)`) fails the unit suite.
