# M1 POSITIVE-root matching precision — **M1-PREC-1** (pseudo-label **rule v4**)

- **Status:** pre-registered 2026-09-18, committed BEFORE any runtime code implements it and before
  any rule-v4 label exists. Owner decisions of 2026-09-18 are frozen in §6.
- **Scope:** how `m1_lexicon` accepts a terlik match of one of the 17 rule-v3 POSITIVE (family-A)
  roots. Nothing else. The A-head taxonomy, the runtime routing (M1-ROUTE-1 / 1.1), every
  EXCLUDED-root match and every threshold stay exactly as they are.
- **Consumers:** m1 at runtime (family-A hits reach users as `A1`); the A-head pseudo-labels,
  regenerated as **rule v4** (`m1_lexicon_train_labels_protocol.md` amendment (d),
  `m1_lexicon_dev_labels_protocol.md` amendment (e)).
- **Evidence behind it:** the read-only audits of 2026-09-18 on the frozen TRAIN / DEV text only:
  at least 358 of 1,528 train positives (23.4 %) and 43 of 257 dev positives (16.7 %) rest only on
  a spurious match. Not used, then or now: the locked test set, the 500-row AI-assisted,
  human-adjudicated evaluation reference, any candidate prediction or error, any threshold curve.

## 1. Why

terlik 0.1.0 (balanced) tolerates leet, separators, repetition and Turkish-letter folding, and it
maps a match found on its normalized text back to the WHOLE whitespace-delimited segment. On the
17 POSITIVE roots this produces systematic false family-A hits: `AK Parti` read as `aq` → `amk`;
`sıkıldım`, `şık`, `şike` folded into `sik`; `amacı`, `amma`, `I am`, `En'âm` read as `am`; digit
tokens (`59`, `6-7`, `4k`, `GOT7`) read as leet; letters harvested across words (`A mı`, `ama en`,
`T A M A M`); clean words behind punctuation (`(Amin)`, `sıkı.`, `ama!`). They reach users as
family-A hits and they are 23 % of the rule-v3 A-head supervision. The rules below are
deterministic, lexical and form-level; none names a corpus row.

## 2. Definitions

- **candidate** — a terlik match of a POSITIVE root after m1's existing tightening and clean-word
  checks (`CLEAN_PREFIXES`, `CLEAN_WORDS`). Its **surface** is its text on the scanned channel.
- **letter / digit / alphanumeric** — Python `str.isalpha()` / `str.isdigit()` / `str.isalnum()`.
- **whole word of a root** — a word W such that terlik's own compiled pattern for that root
  matches ALL of W in one of terlik's two matching spaces (W Turkish-lowercased, or W through
  terlik's normalizer), W is not on terlik's whitelist, and W is not one of m1's clean words.
- **valid word of a root** — a whole word of the root that also passes R2, R4 (b), R6, R7 and R8.

Character classes (machine-checked, `modules/m1_lexicon/test_unit.py`):

```text
PREC_EDGE_KEPT: @ $
PREC_EDGE_KEPT_LEADING: !
PREC_IN_WORD: * + !
PREC_IN_WORD_BETWEEN_LETTERS: . - _ ' ’ ‘
PREC_APOSTROPHES: ' ’ ‘
PREC_MASKS: * +
PREC_CROSS_WORD: &
```

## 3. The rules

Every rule applies to candidates of POSITIVE roots only. A rejected candidate is not a hit: m1
records it as a `SUBSTRING_COLLISION` with evidence `<root> in <surface> (rule-v4 R<n>: <reason>)`,
except when its span overlaps a kept POSITIVE hit (then it is the same evidence read wider and
is dropped silently).

**R1 — No letter.** A candidate whose surface contains no letter is rejected: `59`, `56`, `67`,
`566`, `6-7`, `97`. A numeric token is not profanity; a digit INSIDE lexical word evidence may be
obfuscation and is judged by R2.

**R2 — Edge digits (units, brands).** A word whose first or last character is a digit is
rejected: `4k`, `5g` (of `4.5g`), `GOT7`, `got7`. A digit strictly inside the word stays evidence:
`s1k`, `g0t`, `s1kt1r`.

**R3 — Safe edge punctuation; the word of a match.**
(a) *Edge stripping.* From the START of the surface remove every character that is not
alphanumeric and not in `PREC_EDGE_KEPT` or `PREC_EDGE_KEPT_LEADING`; from the END remove every
character that is not alphanumeric and not in `PREC_EDGE_KEPT`. Removed therefore: quotes,
brackets, period, comma, colon, semicolon, question mark, ellipsis, a word-final `!`, the hashtag
marker `#` (the word after it is judged), `*` / `+` at a word edge, emoji and other symbols at an
edge. Never removed: letters, digits, `@` and `$` anywhere, `!` except word-final, and anything
inside the word (`@Q`, `a*mina`, `g+t`, `s!k`, `s1k`, the dots of `a.q`, `o.ç`, `g.t`).
(b) *Whole word.* The stripped word must be a whole word of the root (§2). Clean words behind
punctuation are rejected here: `(Amin)`, `...Amin`, `#AMİN` → `amin` (m1's prayer word); `‘amca`
→ `amca`; `sıkı.` → `sıkı`, `sıkma...` → `sıkma`, `ama!` → `ama` (terlik's whitelist).
(c) *Glued words.* terlik maps a normalized-text match to the whole whitespace segment, so one
candidate can span several words glued by punctuation. When the stripped word fails (b), it is
split at every internal character that is not alphanumeric, not in `PREC_IN_WORD`, and not a
`PREC_IN_WORD_BETWEEN_LETTERS` character standing between two letters; each piece is
edge-stripped and tested by (b); every piece that passes is a word of the match. Kept:
`bozuntusu:'Amına` → `Amına`; `[piç(3)` → `piç`; `"Hassiktir"çeken` → `Hassiktir`. No piece
passes → rejected.
(d) *Span.* A kept hit's span is its word: `#sikiş` → `sikiş`; `'pezevenk'` → `pezevenk`.

**R4 — Apostrophes and masks inside a word.**
(a) A word that begins right after an apostrophe (`PREC_APOSTROPHES`) or a mask (`PREC_MASKS`)
which itself follows a letter is the tail of a longer word, not a word: rejected. `Bel'am`,
`En'âm` (its `âm`), `istanbul'a` (its `a`), `ta*ak` (its `ak`). No `am` is harvested across an
apostrophe boundary.
(b) When a word contains an apostrophe between two letters, the part before the first such
apostrophe must itself be a valid word of the same root: `taşAK'larını` → `taşAK` ✓;
`En'âm` → `En` ✗; `istanbul'a` → `istanbul` ✗.

**R5 — Cross-word matching.** A candidate that still contains whitespace or `&` after m1's
tightening:
(a) *Punctuation cut* (M1-ROUTE-1.1 §2, extended to POSITIVE roots): if a leading
whitespace-token prefix ends in punctuation and, with that punctuation removed, its word is a
valid word of the same root, the candidate is cut to that word: `sik, sin` → `sik`; `göt, e` →
`göt`. It never adds a match terlik did not make and never lengthens a span.
(b) *Complete spaced spelling.* Otherwise the candidate must lie inside a **spaced run**: a
maximal sequence of at least two single-character tokens separated by exactly ONE space. Two or
more spaces, or any other whitespace, end the run — the wider gap between spaced words
(`L Ü T F E N  B O K` holds the runs `L Ü T F E N` and `B O K`). The run's characters joined
without spaces must be a valid word of the root; the kept span is the whole run. `B O K` →
`BOK` ✓; `T A M A M` → `TAMAM` ✗; `S I K I L D I K` → `SIKILDIK` → R6 ✗;
`B A Ş A R A M A Y A C A K` ✗.
(c) Anything else is rejected: `A mı`, `ama en`, `istanbul'a mı`, `ama cam`, `A. MALLARI`, `A&M`.
Dotted abbreviations contain no whitespace and are not cross-word matches (`a.q`, `o.ç`, `g.t`).

**R6 — Turkish-letter precision.** For the two POSITIVE roots whose Turkish-letter spelling is an
ordinary Turkish word, a word whose letters (Turkish-lowercased; `. - _` and apostrophes removed;
runs of one letter collapsed) BEGIN with one of these stems is that ordinary word, not the root:

```text
PREC_TURKISH_STEMS (2): sik = sık, şık, şik; oç = öç, öc
```

(`sık` often / tight / to squeeze, `sıkılmak` to be bored; `şık` chic; `şike` match-fixing, `şikayet`;
`öç` revenge.) Exception — a harmony break only the obscene root explains: after the back-vowel
stems `sık` / `şık`, the rest of the word contains one of `PREC_HARMONY_BREAK_VOWELS` outside the
invariant suffix `-ken`:

```text
PREC_HARMONY_BREAK_VOWELS: e, ö, ü
PREC_INVARIANT_SUFFIXES: ken
```

Kept (evasion): `sıkecek`, `sıkmek`, `sıkıcıler`, `SIKERIM` (read `sıkerım`). Rejected: `sık`,
`sıkı`, `sıkıldım`, `sıkıyor`, `sıkma`, `sıklıkla`, `sıkarken`, `sıkıyim`, `şık`, `şike`, `öç`.
`ı`/`i` alternation is NOT counted as a break: dotted / dotless confusion is ordinary informal
typing. The rule is NOT applied to roots whose Turkish-letter spelling is no word (`PIÇ` read
`pıç`, `HASSIKTIR` read `hassıktır` stay matches). ASCII spellings contain no Turkish letter and
are unaffected: `sik`, `sikildim`, `sikici`, `siktir`, `s!k`, `s!ktir`, `s1k`, `s1kt1r`.

**R7 — `am` morphology.** For the root `am`, a word of letters only (`â` → `a`, `î` → `i`) must be
`am`, one of its case / possessive inflections, or an `amcık` form:

```text
PREC_AM_FORMS: am(?:c[ıiu]k\w*|c[ıi]|dan|da|la|lar\w*|[ıi](?:n(?:[ıiae]|d[ae]n?|[ıi]n|[ıi]z\w*)?|m(?:[ıiae]|d[ae]n?|la|[ıi]z\w*)?|yla)?)?
```

Kept: `am`, `amı`, `ami`, `amini`, `aminin`, `amindan`, `amdan`, `amcık`. Rejected: `amacı`,
`amaca`, `amma`, `amirim`, `amirlik`, `amade`, `amme`, `amenna`, `ammar`, `aamca`, `amık`. The
bare word `am` right after the English pronoun `I` (a lone `I` / `i` token, then whitespace) is
rejected (`I am`). Words with digits or symbols (`a*mina`, `@m`) are judged by the other rules
only. The prayer word stays clean, extended to the circumflex spelling: m1's `CLEAN_WORDS`
`amin` pattern accepts `amin`, `AMİN`, `âmin`, `amîn`, elongated (`amiiin`).

**R8 — Stable clean forms.** Deterministic, form-level; no phrase list:

```text
PREC_CLEAN_FORMS (7): amk = ak; amk = ananı; göt = gt; göt = gta; göt = GOT; piç = pc; bok = book
```

| root | form | matched against | meaning |
|---|---|---|---|
| `amk` | `ak` | the word Turkish-lowercased, `a+[._-]?k+` (`ak`, `AK`, `akk`, `A.K`) | ordinary word "white", the party name AK; never `amk` evidence (owner decision 1) |
| `amk` | `ananı` | the word folded, `anani` + at most two terlik suffixes (`ananı`, `ananıda`, `anani`) | "your mother": not an obscene root (owner decision 5); `ananısikeyim` still holds `sik` and stays |
| `göt` | `gt` | the word Turkish-lowercased, `g+t+` (`GT`, `gt`) | Twitter "follow back"; `g.t`, `g*t`, `g+t` stay |
| `göt` | `gta` | the word Turkish-lowercased, exactly `gta` | game title |
| `göt` | `GOT` | the word AS WRITTEN, exactly `GOT` | an all-capitals title (`#GOT`); lowercase `got` stays (owner decision 7) |
| `piç` | `pc` | the word Turkish-lowercased, exactly `pc` | computer |
| `bok` | `book` | the word Turkish-lowercased, exactly `book` | English |

`GOT7` / `got7` are rejected by R2; `öç` by R6.

**R9 — Masked-root alignment (owner decision 2; conditional, §9.4).** One asterisk `*` stands for
exactly one hidden letter. A whitespace token, edge-stripped by R3 (a), that contains an `*`
with an alphanumeric character on both sides, and that overlaps no kept POSITIVE hit and no
EXCLUDED candidate, is aligned with every spelling (root and dictionary variants) of every
POSITIVE root: the token's first `len(spelling)` characters must equal the spelling (compared
after terlik's letter folding), each `*` taking the spelling's letter at its position, with every
`*` inside the aligned part. The reconstructed word (spelling + the token's remaining characters)
must then be a valid word of that root. Then the token is a hit of that root, span = the token:
`ta*ak` → `taşak`. It is the same obfuscation as `g*t`, which terlik already reads (there `gt` is
itself a dictionary variant). `+` and `.` are NOT masks for R9: they are arithmetic and
abbreviation marks.

## 4. Order and place in m1

In `m1_lexicon._scan`, per channel, after terlik matching, m1's tightening and m1's clean-word
checks, and BEFORE the nested-hit filter (a rejected glued segment must not hide the valid word
inside it, `[piç(3)` → `piç`):

1. POSITIVE candidates strictly inside an EXCLUDED candidate are dropped (the nested-hit filter's
   existing effect on them, unchanged).
2. Each remaining POSITIVE candidate: R1 → R5 → R3 → R4 → R2 → R6 → R7 → R8.
3. R9 on the tokens it covers.
4. Nested-hit filter among the kept POSITIVE hits (and the EXCLUDED candidates, as before).
5. EXCLUDED candidates: the nested-hit filter over ALL terlik candidates, then M1-ROUTE-1 §5 and
   M1-ROUTE-1.1 — exactly as before, so every EXCLUDED hit, collision and route is unchanged.

## 5. Invariants (machine-checked)

- The lexical family-A roots are exactly the 17 rule-v3 POSITIVE roots: `ROUTE_A` equals the
  generator's `POSITIVE_ROOTS`; the taxonomy digest stays
  `5b8ebe315cd2217c4decc8b0180eb2027a62aa2718405356c2066a29a0375ce5` (taxonomy version 3); no
  EXCLUDED root returns to A. Only matching precision changes.
- Routing A / B1 / B2 / B3 / NONE, the COMPOUND list and every EXCLUDED-root rule are unchanged.
- Raw / normalized channel evidence, original spans, collision guards, homonym guards and the
  private `_matches` signal keep their meaning. The generator still reads matches from `_matches`
  and never reads the route.
- `decision/thresholds.yaml` does not change (no number, no list).

## 6. Owner decisions (frozen) and accepted costs

1. `ak` is never evidence for `amk` (`AK Parti`, `ak renk`, `ak`). Accepted loss: a writer who
   meant `ak` as an abbreviation of `amk`.
2. `ta*ak` is preserved only through R9, a general masked-root rule — never by restoring `ak` →
   `amk`. If R9 creates unexpected matches it is withdrawn (§9.4) and `ta*ak` is an accepted miss.
3. Harmony-consistent Turkish forms `sıkım`, `sıkımı`, `sıktır` are not whitelisted: accepted
   loss. The same letters typed in capitals with a dotless `I` (`SIKTIR` → `sıktır`) are the same
   word to m1 and share that cost.
4. `amık`: no exception; accepted lexical miss.
5. `ananı` alone is not evidence of an obscene root.
6. `M.K.` (initials): no broad initials rule; the collision `M.K` → `amk` is accepted residue.
7. Lowercase English `got`: not suppressed (`got` is also an ASCII spelling of `göt`); accepted
   residue (`she's got …`).
- Audit rows: train 28720 (`B O K`) and 24432 (`[piç(3)`) stay positive; train 45204
  (`A. MALLARI`) loses its `am` match.

## 7. Acceptance lists (machine-checked: `modules/m1_lexicon/test_unit.py` runs every entry through m1)

Clean — no POSITIVE-root hit on either channel:

```text
ACCEPT_CLEAN (80): AK Parti | ak renk | ak | akk | A.K. Parti | amacı | amaca | amma | amirim | amirlik | amade | amme | amenna | ammar | aamca | I am here | i am here | En'âm | Bel'am | sıkıldım | canım sıkıldı | sık sık | sıkı. çok güzel | sıkıyor | sıkma... öyle | sıklıkla | sıkarken | sıkıyim | şık | şıklık | şike | ŞİKE | 6-7 | 59 | 56 | 67 | 566 | 97 | 4k | 4.5g | GOT7 | got7 | GT | &GT | gta | GOT | #GOT çok iyi | pc | book | öç almak | Öc | (Amin) inşallah güzel olur | Allah kabul etsin ...Amin | #AMİN çok güzel | ama! öyle değil | ‘amca geldi’ dedi şöyle | T A M A M | S I K I L D I K | B A Ş A R A M A Y A C A K | A mı | ama en | istanbul'a mı | ama cam | YA A. SİZE NE A. MALLARI | A&M | ananı | ananıda | anani | ananı avradını | amin | AMİN | âmin | amîn | Amiiin! | ta+ak | sıkım | sıkımı | sıktır git | SIKTIR GIT | amık
```

(The last five are owner-accepted misses, pinned so the cost stays visible.)

Genuine — a hit of the named root:

```text
ACCEPT_GENUINE (74): sik => sik | sikildim => sik | sikici => sik | siktir => sik | s!k => sik | s!ktir => sik | s1k => sik | s1kt1r => sik | g0t => göt | #sikiş => sik | #sikiş çok güzel => sik | #göt => göt | #am => am | #amcık => am | #sakso => sakso | #yarrak => yarrak | #gavat => gavat | #orospu => orospu | #YaRRaĞıMıYe => yarrak | a.q => amk | A.q => amk | aq => amk | mk => amk | mq => amk | amq => amk | amg => amk | o.ç => oç | O.Ç => oç | oc => oç | sg => sg | g.t => göt | g*t => göt | g*tü => göt | g*tümüzde => göt | g..tünde => göt | g...tünüz => göt | g+t => göt | a*mina => amk | @Q => amk | B O K => bok | L Ü T F E N  B O K => bok | [piç(3) nalan(5)] => piç | 'pezevenk' => pezevenk | "orospuluk => orospu | "Hassiktir"çeken => hassiktir | bozuntusu:'Amına => amk | taşAK'larını => taşak | am => am | ami => am | amı => am | amini => am | aminin => am | amindan => am | amdan => am | amcık => am | amına => amk | sıkecek => sik | sıkmek => sik | sıkıcıler => sik | SIKERIM => sik | ananısikeyim => amk | ananı sikeyim => sik | got yalamayı => göt | gotunu => göt | gotten => göt | pic => piç | picler => piç | yarak => yarrak | PIÇ => piç | HASSIKTIR => hassiktir | sik, sin => sik | göt, e => göt | amk😂 çok güzel => amk | sik/göt öyle => sik
```

Accepted residue — still a hit (owner decisions 6 and 7):

```text
ACCEPT_RESIDUE (2): M.K. Atatürk => amk | she's got the look => göt
```

Masked-root rule R9 — a hit only while R9 stands (§9.4):

```text
ACCEPT_MASKED (1): ta*ak geçtim => taşak
```

## 8. Label regeneration (rule v4) and the flip report

- TRAIN and DEV are regenerated with `eval/m1_lexicon_labels.py` (6.0.0: `a_label_rule.version`
  4, taxonomy version 3, `matching_protocol` M1-PREC-1), from a clean tree, after this protocol,
  the m1 code and its tests are committed. The `a_label` formula is rule v3's; only m1's
  POSITIVE-root matching differs.
- **History is not rewritten.** The files the rule-v3 artifact was trained on stay retrievable,
  byte-exact, at git `7f5e003` (train `78d845a5fed8dd38441d9ef23f416b85ed8d2ba747d94f5943509550d9fc50c8`,
  dev `8f4dcdfeec707bd8cb9b52744ff6b72a675cdb94790b64d167b87c12fd603ee7`); the last rule-v3
  regeneration stays at `dd6a855` (train `ce3ef280…`, dev `79afe7b9…`). Tests keep pinning both.
- **Flip report** (`eval/m1_lexicon_rule_v4_flips.py`): every row whose `a_label` differs between
  the rule-v3 training bytes (`7f5e003`) and the rule-v4 files, per split: row id, rule-v3 and
  rule-v4 `a_label`, every rule-v3 POSITIVE match (root, channel, span, surface), its rule-v4
  outcome with the responsible rule (from m1's collision evidence), the rule-v4 POSITIVE roots.
  The committed report (`eval/derived/m1_lexicon_rule_v4_flips.{json,md}`) carries NO corpus text
  and NO gold, like the derived files. The full report with the original text and the corpus
  OFF/NOT label (context only, never a decision input) is written to the git-ignored
  `eval/derived/private/`.
- Simulation expectation (NOT a target; the implementation is not tuned to it): about 358 train
  and 44 dev positive → negative. Every difference is explained in the report.

## 9. Acceptance and stop conditions

1. Every `ACCEPT_*` entry behaves as listed; the full suite passes.
2. On every train and dev row, every EXCLUDED-root match m1 publishes in `_matches` (root, channel,
   span, route) equals what m1 0.2.1 (`dd6a855`) publishes, and every row's EXCLUDED roots equal the
   `dd6a855` files'.
3. Compared with the audited set of legitimate positives, no genuine row is lost except the
   owner-accepted misses of §6 (`sıkım` / `sıkımı` / `sıktır`, `ak` meant as `amk`, `amık`) and,
   if R9 is withdrawn, `ta*ak`. **Any other genuine loss: STOP before preparing training** and
   report it.
4. R9 safety: every R9 hit on the train and dev text is listed. If any is not a masked spelling of
   a POSITIVE root word, R9 is withdrawn (the rest of rule v4 stands), `ta*ak` is recorded as an
   accepted miss, and the withdrawal is reported — never a weaker rule v4.
5. No threshold, no test-set row, no evaluation-reference row and no candidate prediction is read
   or changed; the rule-v3 artifact's weights (`41d98d7f…`) are untouched; M3 is not retrained here.
