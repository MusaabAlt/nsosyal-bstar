# Protocol M5-S1 — m5_sarcasm Stage 1: deterministic high-precision degrading-sarcasm detector

- **Status:** owner-approved amendment to the m5 entry gate (spec §2), written BEFORE the Stage-1 code.
- **Decided by:** project owner (Musaab), 2026-09-19, for the TEKNOFEST prototype.
- **Owner of the module:** Abdullah (m5_sarcasm); this protocol is the owner-approved exception.
- **Governs:** `modules/m5_sarcasm/module.py` 1.0.0 (Stage 1). ADR-003 amendment 2026-09-19.
- **Not changed:** the neural m5 path (`training/m5_sarcasm/`, `docs/training/m5_sarcasm.md`), the
  entry gate for that path, ADR-003's "m5 is its own model", `decision/thresholds.yaml`.

## 1. Purpose and honesty statement

Stage 1 is a **deterministic, rule-based detector** for a small set of explicit Turkish constructions
that deliver contempt toward a person through a literally positive element. It is **not** a trained
model, it is **not** a general sarcasm detector, and it is **not benchmarked**: no sarcasm or D1
corpus exists (docs/blockers/m5_sarcasm_corpus_gate.md). The only evidence for its behaviour is the
hand-written fixtures and unit tests named in §9. Every result must be presented as:

| item | value |
|---|---|
| m5 | ACTIVE, Stage 1 |
| method | deterministic rules M5-S1 (this file) |
| neural m5 (sequential transfer, ADR-003) | Stage 2, NOT TRAINED, NOT BENCHMARKED |
| D1 recall / precision | NOT MEASURED |

## 2. What D1 means here (spec §1, §3, §5 — unchanged)

D1 = abuse whose **literal polarity is positive** but whose intent is to humiliate **a person**. A
case is D1 only if a literally positive element exists inside the sentence (praise, congratulation,
admiration) — the polarity-inversion rule of spec §5. Stage 1 fires only when, in addition, an
**explicit marker** of the inversion is present in the raw text and the target is **the addressee**
(second person). Precision is preferred over recall: a missed D1 is acceptable, a D1 on sincere praise
or on sarcasm about a bus is not (spec §3, §8).

## 3. What Stage 1 deliberately does NOT detect

- sarcasm without an explicit marker, including the spec's own first example
  `Zekânı hayranlıkla izliyorum, gerçekten.` — without a marker it is indistinguishable from the same
  sentence said sincerely (spec §3 names this the hardest negative); a known Stage-1 miss;
- sarcasm aimed at objects, weather, software, transport, events (spec §8 control set) — the rules can
  recognise the construction but never emit D1 without a person anchor;
- sarcasm about a third person (`Ahmet çok zeki tabii`) — the person anchor is second person only;
- humour, jokes, banter (spec §3, out of scope);
- implicit abuse without polarity inversion (family C, m4) and direct insults (family B, m1);
- quoted or reported sarcasm (spec §11: "quoting sarcasm is not producing it");
- anything in the normalized channel (spec §7, §11: m5 reads the raw text).

## 4. Rule families (all conjunctive; one satisfied rule is enough)

Text handling: the raw `ctx.text`, lowercased with Turkish casing (`I`→`ı`, `İ`→`i`) and `â î û` read
as `a i u`, character by character so every span stays an offset into `ctx.text`. Sentences end at
`. ! ? …` and line breaks; clauses additionally end at `, ; :`.

**Person anchor (second person).** Any one of:
- a pronoun `sen sana seni senin senden sende siz size sizi sizin sizden sizde`;
- a verb in second-person past (`-dın -din -dun -dün -tın -tin -tun -tün`, + plural `-ız -iz -uz
  -üz`; words of five letters or more);
- a verb in second-person present, aorist, future or necessitative (`-yorsun`, `-ırsın` / `-arsın`
  family, `-acaksın`, `-malısın`, + plural) — a bare `-sın` is NOT enough, because the third-person
  imperative (`olsun`, `gelsin`) ends the same way;
- a praise word with a second-person copula (`zekisin`, `harikasın`);
- a verbal noun with the second-person possessive immediately followed by a praise word
  (`yapman etkileyici`).

Words that only look like these endings are excluded by a fixed list: `kadın aydın odun altın metin
çetin kesin zaman kahraman düşman orman liman duman roman yaman ferman`.

**Praise lexicon** (literally positive element; stems, suffixes allowed):
- person praise: `zeki akıllı dahi deha bilge bilgili uzman profesör filozof entelektüel usta yetenekli
  başarılı çalışkan kibar nazik centilmen kahraman efsane derin parlak mantıklı`
- general praise: `harika mükemmel muhteşem süper müthiş şahane enfes etkileyici olağanüstü fevkalade`
- appearance words (`güzel yakışıklı tatlı`) are deliberately excluded: they are most often sincere.

| id | family | fires when | spec source |
|---|---|---|---|
| `R1_SCARE_QUOTE` | scare-quoted praise | a quoted segment of one or two words starting with a praise stem (`'derin'`, `"zeki"`), and a person anchor in the same sentence | spec §1 example 2, §11 "scare quotes" |
| `R2_CLAUSE_FINAL_TABII` | ironic tag | a clause that ends in `tabii` / `tabi` / `tabii ki` / `tabi ki` and contains a praise word and a person anchor | spec §8 control example, §11 "`tabii ki`" |
| `R3_CONGRATULATED_FAILURE` | polarity inversion | a congratulation formula at the start or the end of a sentence (`aferin bravo tebrikler "tebrik ederim" "helal olsun" harika süper mükemmel muhteşem şahane "ne güzel"`) and, in the same sentence, a second-person past verb of failure (§4.1) | spec §1, §5 (praise + a contradicting result) |
| `R4_IRONY_MARK` | orthographic irony mark | a praise word immediately followed by `(!)` — the TDK Yazım Kılavuzu marks irony and mockery this way — and a person anchor in the same sentence | spec §11 "exaggerated exclamation"; TDK ünlem işareti usage |

A congratulation formula standing alone as the sentence just before the failure sentence also counts
for R3 (`Aferin! Yine her şeyi berbat ettin.`).

### 4.1 Failure verbs (R3), second-person past only

`berbat ettin rezil ettin rezil oldun batırdın beceremedin başaramadın yapamadın çuvalladın
geç kaldın unuttun kaçırdın` and their plural (`-ınız -iniz -unuz -ünüz`). Deliberately NOT in the
list, because they are also praise in ordinary Turkish: `mahvettin` (`rakipleri mahvettin`),
`kırdın` (`rekor kırdın`), `yaktın` (`ortalığı yaktın`), `kaybettin` (`5 kilo kaybettin`); and
`sıçtın`, which is profane and belongs to m1. Third-person forms (`gelmedi`, `batırdı`) never satisfy
R3: they are what keeps `Harika, otobüs yine gelmedi.` benign. Negated forms (`unutmadın`) are not in
the list, so praise for NOT failing is never read as mockery.

### 4.2 Praise-word inflection

A praise word is the stem alone or the stem plus one copula or adverb ending: `-sın -sin -sun -sün`
(+ plural), `-(y)ım`, `-(y)ız`, `-dır` family, `-(y)dı` family, `-(y)mış` family, `-ca -ce -ça -çe`.
Prefix matching is not used (`süpermarket` is not `süper`). A praise word with a second-person copula
(`zekisin`, `harikasın`) is itself a person anchor.

## 5. Exclusions (checked after a rule matches; any one blocks D1)

| id | exclusion | reason |
|---|---|---|
| `X_REPORTED` | the match lies inside a quotation (a quoted segment of three or more words, or any quoted segment followed within two words by a reporting verb `dedi demiş diyor der diye dediği söyledi söylemiş yazdı yazmış diyen`), or a reporting verb follows the match in the same sentence | spec §11 reported speech |
| `X_MENTION` | the scare-quoted word is followed by `kelimesi sözcüğü kelimesini sözcüğünü` (a word being discussed, not used) | meta-discussion is not use |
| `X_NEGATED` | `değil` within two words after the praise word (`zeki değilsin tabii`) | no positive element, no inversion (spec §5) — a direct statement |
| `X_QUESTION` | the clause of R2 ends in `?` | a question is not an ironic assertion |
| `X_NO_PERSON` | the construction is present but no person anchor applies | spec §8: benign sarcasm at things is the control set |
| `X_EXPLICIT_CONTENT` | m1 published `lexicon_hit: true` | spec §3 precedence: "explicit content wins"; D1 is for abuse that has no other way to be caught |

`X_EXPLICIT_CONTENT` reads `ctx.signals["m1_lexicon"]["lexicon_hit"]`, which m1 publishes before m5
runs (registry order). It is the one signal m5 reads besides `ctx.text` (spec §7 amended). When the
signal is absent (m1 unavailable, or m5 run alone) the precedence rule cannot be applied; D1 is
emitted and a note says so. m5 does not read m6: its person anchor is part of each rule.

## 6. Output and score semantics

- One `ContentScore(code=D1, score=1.0, source="m5_sarcasm@raw", span=<first satisfied rule's
  evidence span>)` when at least one rule is satisfied and no exclusion applies; nothing otherwise.
- **`1.0` means "a deterministic Stage-1 rule is satisfied". It is not a probability** and carries no
  confidence. There is no weighting between rules.
- `emits_spans` stays `False` (D1 is a post-level code, spec §3); the span is evidence for audit.
- Public signals (no copy of the post, decision 17): `stage` 1, `detector` `"deterministic"`,
  `rules_version`, `matched_rules` (ids of satisfied, unexcluded rules), `excluded` (up to 5
  `{rule, reason, span}` records of constructions found and not emitted), `precedence_checked`.
- Notes: when the precedence rule could not be checked; when D1 was withheld for explicit content.

## 7. Decision interaction (unchanged configuration)

`decision/thresholds.yaml` `categories.D1`: threshold `0.50` — **PLACEHOLDER policy threshold**, not
derived (a deterministic 1.0 clears any threshold below 1); action `nudge` — **PLACEHOLDER policy**.
D1 is not suppressible by any configured guard. The verdict is the most severe action among the fired
codes, `binary_offensive` and the thread rule (ACTION_PRECEDENCE, unchanged). m5 is no longer a stub,
so it no longer degrades the result; CLEAN becomes reachable when nothing fires.

## 8. Known limitations

- recall is low by design: only the four constructions of §4, only second-person targets;
- the lexicons are small, hand-written and Turkish-only; slang and misspellings are not covered;
- no benchmark: precision on the spec §8 control set and D1 recall are NOT MEASURED;
- the second-person endings are surface patterns (no morphological analysis), guarded by the fixed
  exclusion list of §4;
- precedence uses m1's `lexicon_hit`, which also counts ordinary insults (B1): a sarcastic post with
  any lexicon hit gets its m1 code, never D1.

## 9. Evidence (fixtures and tests, not a benchmark)

`modules/m5_sarcasm/test_unit.py` (behaviour tests: every rule, every exclusion, sincere praise,
benign sarcasm, direct insults, reported speech, clean, determinism, edge inputs) and
`modules/m5_sarcasm/fixtures/cases.jsonl` (every D1 positive carries its `inversion_span`, spec §11).
End to end: `tests/test_end_to_end.py`, `eval/scenarios/run_active_modules.py`.

## 10. Transition to the neural m5 (Stage 2)

Unchanged plan (spec §6, ADR-003): sequential transfer on m5's own small model once the entry gate
resolves. The Stage-1 rules then become (a) a labelled seed set of explicit positives and hard
negatives for the annotation guideline, and (b) a baseline the neural model must beat on the control
set. Stage 1 is replaced, not ensembled, unless a protocol written before that comparison says
otherwise. `rules_version` changes with every rule or lexicon edit.
