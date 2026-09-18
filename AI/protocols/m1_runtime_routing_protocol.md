# M1 runtime routing protocol — **M1-ROUTE-1**

Owner approval, 2026-09-18. Committed BEFORE any runtime code implements it. It freezes which
content code m1 emits for each terlik root, the guards that go with the routing, and the narrow
EXCLUDED-root match fixes. It does not change what the A head is trained on.

## 1. Why

Pseudo-label rule v3 (`protocols/m1_lexicon_train_labels_protocol.md`, amendment (b)) defines
family A narrowly: an explicit obscene or profane lexical root, 17 roots. m1 emitted EVERY terlik
match on the family-A carrier, so ordinary insults (`aptal`, `salak`, `kahpe`, …) reached users
as "küfür". Excluding a root from A must not mean ignoring it: m1 keeps detecting all 147 roots
and routes each to the content code whose contract meaning fits.

## 2. The classes (contract meanings, `contracts/codes.py`, unchanged)

| class | code m1 emits | meaning |
|---|---|---|
| A | `A1` carrier, score 1.0; the decision layer assigns `A1` / `A2` / `A3` from m6's target (ADR-005) | explicit obscene / profane lexical root — exactly the rule-v3 POSITIVE set |
| B1 | `B1`, score 1.0 | degradation: an ordinary insult, no profane root |
| B2 | `B2`, score 1.0 | threat |
| B3 | `B3`, score 1.0 | curse / exclusion |
| NONE | no content score | a real dictionary match whose root is not itself abusive (topic or neutral vocabulary); still reported as a hit and a matched root |

The B family is read as "non-profane abuse; no profane root required" (owner, 2026-09-18), not
literally "must be non-lexical": a deterministic lexical B code is allowed, as m6's `B4` already
is. B1 / B2 / B3 keep their own codes: m6's target does not recode them. Their existing
`thresholds.yaml` entries (0.50, action `review`) are unchanged.

## 3. The routing table (machine-checked: `tests/test_m1_lexicon_labels.py`)

```text
ROUTE_A (17): am, amcı, amk, bok, gavat, göt, hassiktir, orospu, oç, pezevenk, piç, sakso, sg, sik, sktrgt, taşak, yarrak
ROUTE_B1 (100): ahlaksız, ahmak, akılsız, alçak, alık, andaval, aptal, arsız, avanak, ağzıbozuk, aşağılık, aşifte, baldırıçıplak, beyinamip, beyinsiz, budala, dalkavuk, dallama, dangalak, dangoz, densiz, denyo, domuz, dümenci, dürzü, edepsiz, embesil, enayi, ezik, eşek, eşoğlueşek, fahişe, fırıldak, gerizekalı, gerzek, görgüsüz, hayasız, haysiyetsiz, hergele, hödük, hımbıl, hınzır, ibne, ikiyüzlü, kafasız, kahpe, kalleş, kaltak, kalınkafalı, kancık, kansız, karaktersiz, kepaze, kevaşe, kötüniyetli, küstah, kıro, kıtakıllı, madrabaz, maganda, magat, mal, mankafa, manyak, maymun, müptezel, namussuz, nankör, onursuz, oğlancı, pislik, puşt, rezil, sahtekar, salak, saloz, sersem, serseri, soysuz, sürtük, terbiyesiz, ukala, utanmaz, vefasız, yalaka, yarımakıllı, yavşak, yobaz, yüzkarası, yüzsüz, zonta, zugar, zukkafa, çomar, çüş, öküz, üçkağıtçı, şapşal, şarlatan, şerefsiz
ROUTE_B2 (7): boğazınıkeserim, canınıalırım, ensenibulurum, gömerler, kafanıkırarım, mezarınıkazarım, öldürücem
ROUTE_B3 (9): allahbelanıversin, asılası, belanıbulurum, cehenneme, defol, geber, gömülesi, kesilesi, yakılası
ROUTE_NONE (14): dingil, dolandırıcı, döl, fuhuş, glk, hapiyedin, kalpazan, kaybol, kaşar, kerhane, meme, tabanvansen, tokmakçı, yıkık
```

- `ROUTE_A` equals the rule-v3 POSITIVE set: the 17 roots are the ONLY lexical family-A roots.
- `ROUTE_B1 ∪ ROUTE_B2 ∪ ROUTE_B3 ∪ ROUTE_NONE` equals the rule-v3 EXCLUDED set (130 roots);
  none of them returns to family A.
- The five lists partition the pinned terlik 0.1.0 dictionary (147 roots). m1 refuses to load if
  the installed dictionary holds a root the table does not route.
- Owner decisions behind the non-obvious rows: `ibne`, `puşt`, `oğlancı`, `mal`, `fahişe` → B1;
  `kaşar`, `kaybol`, `dolandırıcı` → NONE; `dingil`, `tokmakçı` → NONE (their ordinary senses,
  axle and mallet-maker, dominate). Reasons per root: the reviewed taxonomy tables of 2026-09-18.

## 4. Guards

| guard | change | why |
|---|---|---|
| `NON_HUMAN_TARGET` | suppresses `[A1, A2, A3, B1]` (was `[A1, A2, A3]`) | "aptal film", "manyak film": an insult aimed at a thing. B2 / B3 are NOT added: threats and curses aim at people |
| `HOMONYM` | suppresses `[A, B1]` (was `[A]`) | the new B1 homonym entries below |

`decision/thresholds.yaml`: guard LISTS only; no number changes.

New HOMONYM entries in m1 (span-scoped, ADR-001; the context is the text right AFTER the match,
Turkish-lowercased; the matched word must be exactly the bare root):

| surface | protected when the next word … | still fires |
|---|---|---|
| `mal` | starts with `varlı` / `varli`, `sahib`, `mülk` / `mulk`, `beyan`, `bildirim`, `müdür` / `mudur`, or is `ve hizmet` | `mal`, `mal mısın`, `mal gibi` |
| `domuz` | is exactly `eti`, `et` or `gribi` | `domuz`, `domuzlar`, `domuz herif` |

## 5. EXCLUDED-root match fixes (POSITIVE-root matching is NOT changed here)

Applied only to matches of a rule-v3 EXCLUDED root, and only AFTER m1's existing nested-hit
filter, so every POSITIVE-root hit — including whether one is nested inside another match — is
exactly what it was:

1. **Clean word `allık`** (blush) for the root `alık`: a whole match `a+l{2,}[ıi]+k+` is a
   `SUBSTRING_COLLISION`, not a hit.
2. **Split across words.** terlik's separator tolerance can join letters across a word boundary
   and accept the rest as a suffix ("Ali Kınık" read as `alık` + `ınık`). A match of an EXCLUDED
   root that still contains whitespace after m1's tightening is kept only if its letters ARE the
   root: both sides pass through terlik's own normalizer (Turkish lowercasing, folding, leet map),
   then every non-letter is removed and every run of one letter collapses to one. Otherwise it is
   a `SUBSTRING_COLLISION` with evidence `<root> in <matched> (split across words, not the bare
   root)`. Kept: `a l ı k`, `sal ak`, `ap tal`, `salak mısın` (tightened to `salak`). Rejected:
   `Ali Kınık`, `ali, kimi`, `Ali kim`. Accepted cost: a split AND inflected EXCLUDED root
   (`s a l a k l a r`) is no longer a hit.

The same problems exist for POSITIVE roots ("A mı", "ama en", digit tokens, edge punctuation);
they change A pseudo-labels and belong to the separate, still-open matching-precision task.

## 6. Private match signal (generator independence)

m1 publishes `signals["_matches"]`: every hit that survives the rules above, on every channel
with an offset map, as `{"root", "channel", "span", "route"}` (`span` in original offsets,
`route` one of `A`, `B1`, `B2`, `B3`, `NONE`). The pipeline keeps `_` keys out of the response
(`pipeline/run.py::public_signals`); it is not a content code and not user-facing. The public
signals (`lexicon_hit*`, `matched_roots`, `engine`) keep their meaning: every dictionary match,
whatever its route.

The pseudo-label generator (`eval/m1_lexicon_labels.py` 5.0.0) reads matches from `_matches`,
never from content scores, and never reads `route`. Rule v3 is unchanged: `a_label = 1` iff a
valid hit holds a rule-v3 POSITIVE root.

## 7. Acceptance (checked before the regenerated label files are committed)

- Every A pseudo-label VALUE on the 26,992 train and 4,764 dev rows is identical to the files the
  rule-v3 artifact was trained on (git `7f5e003`; `tests/test_m1_lexicon_labels.py`).
- The rule-v3 artifact's weights are untouched (`41d98d7f…`); M3 is not retrained.
- No threshold is derived and no number in `thresholds.yaml` changes. The test set is not used.
