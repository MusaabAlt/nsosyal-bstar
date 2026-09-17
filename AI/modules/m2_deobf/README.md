# m2_deobf

Parallel de-obfuscation channel. `spec.md` is the source of truth; this file records the
resources used and their licences (spec §5: "Do not adopt a tool without recording its licence"),
and what v1 deliberately declares unhandled.

Install: `python -m pip install -r modules/m2_deobf/requirements.txt` (tier 2 only; tier 1 runs
on the standard library). Without `zeyrek` the module loads with tier 2 disabled and says so in
its notes.

## Resources and licences

| Resource | Version | Licence | Used for |
|---|---|---|---|
| `terlik` `LEET_MAP` (Python port of `badursun/terlik.js`) | 0.1.0 | MIT | the tier-1 leet table, copied as data into `module.py` with attribution; terlik is not imported here (its detection verdict belongs to m1, spec §5) |
| `zeyrek` (Zemberek's Turkish lexicon and rule-based analyser in Python) | 0.1.3, pinned | MIT | tier 2: morphological **validation** of a DEASCII candidate ("is this a legal Turkish word form"); word-level parser only, no sentence tokeniser, no network |
| `nltk` (pulled in by zeyrek) | as required by zeyrek | Apache 2.0 | not called by this module; no NLTK data is downloaded |
| `unicodedata` (stdlib) | — | — | accent decomposition, category checks |

## Patterns handled in v1 and how

| Code | Tier | Rule |
|---|---|---|
| `LEET` | 1 | digit / symbol inside a token that also has letters, mapped by the fixed table (`4`→`a`, `3`→`e`, `1`→`i`, `0`→`o`, `5`→`s`, `7`→`t`, `8`→`b`, `6`/`9`→`g`, `@`→`a`, `$`→`s`, `!`→`i`, `2`→`i`); pure numbers, times, dates and protected tokens are never touched |
| `REPEAT` | 1 | a run of three or more identical letters folds to one (Turkish has legitimate doubles — `anne`, `elli` — never triples) |
| `SPACED` | 1 | three or more single letters separated by single spaces join into one token |
| `PUNCT_SPLIT` | 1 | three or more letters separated by the same punctuation character (`.`, `-`, `_`, `,`, `/`, `+`, `|`) join; `*` is excluded because it masks a letter rather than separating letters (spec §4) |
| `HOMOGLYPH` (accent) | 1 | non-Turkish accents stripped from Latin vowels (`áptal` → `aptal`); Turkish letters and the circumflex (`kâr`) are left alone. Reported under `HOMOGLYPH` because the frozen contract has no accent code; `source = m2_deobf` distinguishes it from m0's |
| `PHONETIC` | 1 | `q`→`k`, `w`→`v`, `x`→`ks` inside a token of Turkish letters; no Turkish word uses q/w/x |
| `DEASCII` | 2 | a token with no legal Turkish parse whose ASCII letters (`c g i o s u`) admit exactly ONE candidate with a legal parse is restored (`serefsiz` → `şerefsiz`); zero or several legal candidates → untouched. Declared ambiguities (`sık`/`sik`, `kanı`/`kani`, `kısmet`/`kismet`, spec §9) are never resolved even when the lexicon would. **Measured (2026-09-17, generated set, 14 pairs): capture 0.71 [0.46, 0.92]**, below the spec's 80 % acceptance line. The four misses are the rule being conservative, not a defect: `sikici` and `kopek` are themselves legal forms in the lexicon (so the token is left as typed, which is exactly the `sık`/`sik` protection), and `bugun` / `sakasini` admit more than one legal Turkish reading (`bugün` / `buğun`, `şakasını` / …). A looser rule would guess; the spec forbids guessing. Recorded as a measured negative for this pattern |
| `SUFFIX_ON_MASKED` | 2 | a token of letters with one or more mask characters (`*`, `#`) inside it is reported; the text is not altered (no lexicon can say which letter was masked) |

## Declared unhandled in v1 (spec §3 allows declaring a pattern rather than half-handling it)

`ABBREV`, `VOWEL_DROP`, `WORD_MERGE`, `CHAR_DROP`, `DIALECT` need a curated Turkish lexicon or
map that the repository does not contain; `EMOJI_SUB` is out of scope by spec §3. Each is listed
in `eval/implementation_status.json` under `not_built` so no report can read as covering it.

## Protection pass (spec §5)

Before any repair, tokens that look like evasion but are not are masked from every rule:
URLs, e-mail addresses, `@mentions`, `#hashtags`, tokens mixing digits and letters in brand style
(`3M`, `COVID-19`, `TeknoFest2026`, `Ar-Ge`), phone-number and IBAN shapes, and capitalised proper
nouns (a token capitalised in the ORIGINAL text that is not sentence-initial, including
apostrophe-suffixed forms `Turkcell'in`, `Ayşe'yi`). m2 reads m0's lowercased `charsafe_text`, so
capitalisation is read from `ctx.text` through m0's offset map.

## Offsets (ADR-008, proposed)

`signals["_offsets"]` holds the original-text index of every character of `normalized_text`
(m0's convention); `signals["offsets_identity"]` is true when nothing moved. m1 maps
normalized-channel spans through it. `signals["repairs"]` lists every repair as
`{code, span, before, after}` for the demo UI and the eval.
