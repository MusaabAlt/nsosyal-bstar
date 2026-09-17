# m6_target — target-resolution and doxing rules (annotation guideline, v1)

Written 2026-09-17 with the v1 implementation, from the template
`protocols/templates/annotation_guideline.md`. m6 spec §4 requires every ambiguity to be handled by
a **declared** rule; §5 requires the doxing operating point to be stated. Rules marked
**PENDING OWNER DECISION** are the behaviour v1 exhibits today so that it is declared rather than
implicit; they are not the owner's decision (OPEN_QUESTIONS Q28) and change when the owner decides.

## 1. Target types (spec §3)

| type | v1 evidence, in priority order | confidence recorded |
|---|---|---|
| `individual` | (a) an `@mention`; (b) a second-person token from the project's frozen deictic set (`diagnosis/data/deixis/address_tokens.json`: primary `sen siz sizin senin sizi sana size`, extended forms `seni sende senden seninle sence sizde sizden sizinle sizce sizler sizleri sizlere sizlerin`), matched by exact token after Turkish lowercasing, never by prefix; (c) a vocative particle (`lan`, `ulan`, `be`, `oğlum`, `kızım`, `moruk`, `kardeşim`, `abi`, `abla` when followed by punctuation or at the end); (d) a second-person copula / verb ending on a token of ≥ 4 letters (`-sın/-sin/-sun/-sün`, `-sınız/-siniz/-sunuz/-sünüz`, `-yorsun`, `-mısın …`) | (a) 0.95, (b) 0.90, (c) 0.75, (d) 0.60 |
| `group` | a stem of `gazetteers/groups_tr.txt` matched with suffix awareness (plural, possessive, case), e.g. `türkler`, `kadınlara`, `mültecilerin` | 0.85 with a plural or collective suffix, 0.70 bare stem |
| `non_human` | a stem of `gazetteers/non_human_tr.txt` with suffix awareness (`programı`, `otobüsler`, `hava`) | 0.80 |
| `none` | nothing above matched | — |

**Precedence when several match:** `individual` > `group` > `non_human`. Reason: a post that
addresses a person and mentions a program is aimed at the person; the spec's failure to avoid is a
non-human target resolved as a person, and the reverse error is not the one the guideline warns
about. The evidence span is the first (leftmost) match of the winning type.

**Never** resolves a non-human stem as `individual` or `group` (spec §7).

## 2. The three documented ambiguities (spec §4)

| case | v1 rule | status |
|---|---|---|
| **`siz`** (formal singular or plural) | `siz` and its inflected forms resolve `individual`: the project's frozen deictic set lists them as second-person *address* tokens, and address of an unnamed reader is the individual reading. Plural-marked `sizler` resolves `individual` as well (address), not `group`: a group in this taxonomy is an identity group, not "several readers". | **PENDING OWNER DECISION** — declared so the behaviour is visible; the owner may choose the group reading for `sizler` or for contexts with a group noun |
| **institution vs members** | an institution common noun (`belediye`, `banka`, `şirket`, `üniversite` …) resolves `non_human`, following the taxonomy row "institution" under `non_human`. No inference that the members are meant is made; the explicit members form `-deki(ler)` / `-daki(ler)` ("belediyedekiler", those at the municipality) is excluded from the match and resolves nothing. Party and organisation **proper names** (`AKP`, `CHP`, `TSK` …) are not in any gazetteer and resolve nothing; party **affiliation** nouns (`akpli`, `chpli`) are identity groups and resolve `group`. | **PENDING OWNER DECISION** on the members boundary; the affiliation/institution split above follows the spec's own taxonomy |
| **religion vs followers** | follower nouns (`müslüman`, `hristiyan`, `yahudi`, `alevi`, `ateist` …) resolve `group`; the religion itself (`islam`, `hristiyanlık`, `din`) is not in the gazetteer and resolves nothing. Coordination with m1's `A4` (spec §4.3) waits for the `A4` table (`docs/blockers/m1_a4_sacred_concepts.md`). | **PENDING OWNER DECISION** on whether an attack on the religion itself is an identity attack; v1 declines to resolve it |
| **sports-club supporters** (spec §3 note) | not listed; resolve nothing | **PENDING OWNER DECISION** |

## 3. Doxing `B4` (spec §5) — operating point: validated patterns only

`B4` fires only on a **validated** identifier or an address with a personal cue. Every `B4` score
carries the span of the exact triggering substring (ADR-001). Confidence is the pattern's
validation strength, never a threshold.

| pattern | validation | confidence |
|---|---|---|
| Turkish mobile number | `05xx xxx xx xx` or `+90 5xx …` / `0090 5xx …`, 10 digits after the leading 0 / country code, separators space, `-`, `.`, `(`, `)` | 0.95 |
| Turkish landline | `0` + 3-digit area code (`2xx`, `3xx`, `4xx`) + 7 digits | 0.85 |
| national ID (TC kimlik no) | 11 digits, first ≠ 0, both checksum digits valid (digit 10 = ((sum of odd positions × 7) − sum of even positions) mod 10; digit 11 = sum of the first ten mod 10) | 0.97 (checksum) |
| IBAN | `TR` + 24 digits, ISO 7064 mod-97 check = 1 | 0.97 (checksum) |
| licence plate | `dd [A-Z]{1,3} d{2,4}` with a valid province code 01–81 | 0.70 (plates are semi-public; reported, low confidence) |
| address | at least two address markers (`mah.`/`mahallesi`, `sok.`/`sokak`/`sokağı`, `cad.`/`caddesi`, `bulvarı`, `no:`/`no.`, `daire`, `kat`, `apt.`/`apartmanı`, `blok`) **and** a number, **and** a personal cue within the post (`evi`, `evinin`, `evine`, `adresi`, `oturuyor`, `yaşıyor`, `kalıyor`, a second-person token, or an `@mention`) **and** no public-place cue (`mağaza`, `dükkan`, `şube`, `ofis`, `etkinlik`, `konser`, `açılış`, `restoran`, `kafe`, `okul`, `hastane`) | 0.80 |
| e-mail address | RFC-shaped local@domain.tld | 0.60 (often public; reported low) |
| social-profile link | URL whose host is a social network and whose path names a profile (`instagram.com/<user>`, `x.com/<user>`, `twitter.com/<user>`, `facebook.com/<user>`, `tiktok.com/@<user>`) | 0.60 |

**Near-misses that must not fire** (spec §9): a public business address (public-place cue, no
personal cue), an announced event location, a phone number that fails the shape check, an
11-digit number that fails the checksum (order numbers, tracking numbers), an IBAN that fails
mod-97. The fixture file asserts each.

**Privacy boundary** (spec §2): nothing is looked up, verified against any source, stored or linked.

## 4. Relabelling decision for non-protected targets (spec §7, §10)

The reference functional suite labels abuse at non-protected targets as *not hateful*. This
project follows the offensive-language convention: such abuse **is** offensive; its target type is
whatever this guideline resolves (`individual`, `group`, `non_human`, `none`), and the
offensiveness is decided by the content modules, never by m6. m6 resolves targets regardless of
offensiveness (spec §2).

## 5. What v1 does not do

No person-name gazetteer (no licensed Turkish first-name / surname list in the repository); no
transformer NER (ADR-007); no identification of who a mention refers to; no thread context.
