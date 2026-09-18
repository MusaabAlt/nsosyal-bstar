# Annotation guideline — "profanity present" for m3's A head (dev oracle), v1.1

- **Status:** v1.1, SEALED on commit (2026-09-18). A change to a rule means a new version number,
  a re-read of every already-labelled row under the new rule, and a new sample id file. Labels
  produced under one version are never mixed with labels produced under another. v1.1 superseded
  v1.0 before any row was labelled, so no re-read was needed (§10, version history).
- **Purpose:** the **human evaluation oracle** for m3's A head ("profanity present", A1 carrier,
  ADR-005). Owner decision 2026-09-18 (HYBRID strategy): the A head is *trained* on terlik-derived
  pseudo-labels (train split) and *evaluated only* against this human-labelled dev subset. Every
  reported A-head quality number reads against these labels. Terlik agreement is never reported as
  accuracy.
- **Population:** a uniform random sample of the frozen DEV split (seed 42), drawn by
  `python -m eval.a_head_dev_sample draw` (§6). Never a train row, never the official test set.
- **Template:** `protocols/templates/annotation_guideline.md` (this guideline covers one binary
  question, not the full four-axis label; the axes it borders are listed in §3 so the annotator
  can say *why* a row is 0).
- **Owner:** Musaab. **Annotators:** named in the sample's ids file.

## 1. The question

For each post, answer **one** question:

> Does the post, as written, contain at least one **profane expression** — a swear word, an
> obscene sexual or scatological term, or a vulgar insult built on such a root — that is
> **used by the author** (not merely mentioned), on **any** target or on none?

- `1` = yes, profanity present.
- `0` = no.

"Profane expression" means a lexical item a Turkish speaker recognises as küfür / argo of the
**obscene** kind: an obscene or profane root and its inflected, suffixed, compounded, abbreviated
or obfuscated forms. The test is whether the root itself is obscene or profane — not whether the
word is insulting, and not whether it appears on a profanity word list, since such lists also hold
ordinary insults. An ordinary or mild insult that is derogatory but has no obscene or profane root
(`aptal`, `salak`, `eşek herif`) is `0`, unless the same post also contains a genuine profane
root. The judgement is about the **word**, not about how offensive the post is overall.

## 2. Decision procedure (in this order)

1. **Read the post de-obfuscated in your head.** Leet (`g0t`), separators (`s.i.k.t.i.r`),
   repetition (`siktiiiir`), missing Turkish letters (`sikinti` vs `sıkıntı`), spacing and
   abbreviations (`amk`, `aq`, `oç`) are all read as the word they stand for. Obfuscation never
   changes the answer (Axis 2 sits on top of content).
2. **Find the candidate word(s).** Is there a token whose root is a profane root?
3. **Apply the exclusions of §3 to each candidate.** If every candidate is excluded, the answer
   is `0`. If at least one candidate survives, the answer is `1`.
4. **Ignore the target and ignore the overall tone.** A profane word aimed at a film, the
   weather, a football club, a group, a person, or nobody is still `1`. A hateful post without a
   profane word is `0`.
5. **If you cannot decide after step 3, label your best reading and set `uncertain: true`**
   with a note saying which rule you could not apply. Never leave `label` null in a file you hand
   in.

## 3. What "profanity present" is NOT — the exclusions

| the row is `0` when the only candidate is… | why | what it is instead |
|---|---|---|
| **general offensiveness without a profane word** (`Bu suratla aynaya nasıl bakıyorsun`, `Onlardan başka ne beklenir`) | the corpus's OFF/NOT label is a different question; 63.5 % of OFF posts carry no profane root (study) | B or C family, judged elsewhere |
| **a B-family expression** — a threat, a degrading remark, exclusion, sexual aggression **stated without a profane root** (`Seni bulurum`, `Çirkinsin`) | direct, literal harm is not lexical profanity | B1 / B2 / B3 / B5 (m3's B head) |
| **an ordinary or mild insult** — a derogatory word with **no obscene or profane root** (`aptal`, `salak`, `eşek herif`) | the A head is explicit profanity: an obscene or profane root must be present. Being insulting is not enough (owner decision, v1.1) | outside the A head (e.g. B1, as for `eşek herif`); `1` only if the post also carries a genuine profane root |
| **a C-family expression** — a stereotype, dehumanisation, coded or veiled expression, incitement, defamation whose harm is *implied* | the operational test of m4 spec §3: the harmful claim is reconstructed, not written | C1–C5 (m3's C head) |
| **a sacred-concept expression** (swearing built on `Allah`, `kitap`, `din` and the like) | `A4` is concept-based and its approved root table does not exist yet (`docs/blockers/m1_a4_sacred_concepts.md`). Until the owner approves an A4 definition, sacred-concept content is **not** "profanity present" for this oracle. Record it: `notes: "A4 candidate"` | pending A4 |
| **quoted or reported profanity** — the author repeats someone else's words to report, condemn or discuss them (`"…" demiş, ayıp`, counter-speech, meta-discussion about a swear word, a dictionary-style mention) | the word is *mentioned*, not *used*; the author is not swearing | CLEAN + quote guard, or another family |
| **a substring collision** — a profane root inside an innocent word (`sık` in `sıkıntı` / `SIKINTI`, `am` in `amca` / `ambulans`, `sik` in `psikoloji` / `sikke` / `klasik`, `göt` in `götürmek`, `piç` in `kerpiç`) | morpheme-boundary rule (m1 spec §4.1): a root counts only as a whole word or with legal suffixes | CLEAN + SUBSTRING_COLLISION |
| **a homonym** — a surface that is also an innocent word in context (`10 am`, `am/pm`; a proper name; a foreign word) | context decides; the innocent reading wins when it is the natural one | CLEAN + HOMONYM |
| **profanity aimed at a non-human target** — **this is NOT an exclusion.** `Bu film tam bir bok` is `1` | target does not change lexical profanity; the *code* (A1/A2/A3) and the NON_HUMAN_TARGET guard are decided downstream by m6 and the decision layer, not by this label | still `1` |

Two more rules:

- **Dual-register words** (words with an innocent sense and an obscene sense, e.g. body-part
  words): `1` only when the obscene sense is the one used. An animal word has an insulting sense
  but no obscene one, so it falls under the ordinary-insult row above: `Eşek gibi çalıştım` is `0`
  (ordinary sense) and `Eşek herif` is `0` (insult, no obscene root; it belongs to B1), unless the
  post also carries a profane root.
- **Self-directed or joking profanity** (`amına koyim ya, unutmuşum`): `1`. The oracle asks
  whether the word is present and used, not whether anyone is harmed.

## 4. Labels and the file format

Each annotator receives one jsonl file (`eval/annotation/private/…<annotator>.jsonl`, never
committed). One object per line, fields exactly:

| field | type | filled by | meaning |
|---|---|---|---|
| `row_id` | string | sampler | corpus id (do not edit) |
| `text` | string | sampler | the original post (do not edit) |
| `label` | `0` or `1` | annotator | §1 |
| `uncertain` | bool | annotator | `true` when §2 step 5 applied |
| `notes` | string | annotator | which candidate word, which exclusion, `"A4 candidate"`, `"quoted"` … — short, free text |

A file is complete when no `label` is null. Validate before handing it in:

```bash
python -m eval.a_head_dev_sample check eval/annotation/private/<file>.jsonl --ids eval/annotation/<ids file>
```

## 5. Adjudication (two or more annotators)

Every row is labelled independently by each annotator; nobody sees another file before handing
in. Then:

```bash
python -m eval.a_head_dev_sample adjudicate <ann1>.jsonl <ann2>.jsonl --ids <ids file> --out eval/annotation/private/<stem>.adjudication.jsonl
```

The command prints percent agreement and Cohen's κ per pair and writes an adjudication file:
agreed rows carry `final` already; disagreement rows carry `final: null`. The adjudicator (the
owner, or a third annotator who has not seen the two files) fills `final` for every disagreement
with a one-line `adjudicator_notes` naming the rule that decides it. **The adjudicator applies
this guideline, never a preference; a disagreement that the guideline cannot settle is recorded
as such in the notes and the rule is queued for v1.1.** Agreement is reported with the number
(spec §9 of m3: no acceptance number is claimed without a human-labelled slice **with its
agreement**).

## 6. Sample size, sampling and what the number means

- **Draw:** uniform random sample without replacement from the 4,764 dev ids, seed 42, default
  n = 500, presented in a seeded random order. No stratification by any prediction, lexicon flag
  or gold label: the sample estimates the dev distribution as is, so no weights are needed.
- **Expected positives:** the dev split holds 920 OFF rows (19.3 %), and roughly a third of OFF
  posts carry a profane root, so a 500-row sample is expected to contain on the order of 30–40
  positives — above m3 spec §9's floor of 20 positives per code, below what a tight confidence
  interval needs. The trainer reports `insufficient_sample` under 20 positives. A larger n (or a
  second draw with another seed, labelled under the same version) narrows the interval; both are
  reported with their n.
- **Single-annotator files are usable** (`export` accepts one checked file), but every number
  from a single-annotator oracle is reported as such; the project's claim needs the adjudicated
  file.

## 7. Export and use

```bash
python -m eval.a_head_dev_sample export eval/annotation/private/<stem>.adjudication.jsonl --ids <ids file> --out eval/annotation/private/a_dev_human.jsonl
```

writes the `{row_id, label}` jsonl the trainer and evaluator read as `--labels-a-human`, plus a
`.provenance.json` (source digest, ids digest, guideline digest, n, positives). The oracle file is
**dev only** (the trainer refuses a human label on a train row) and it is never fed to
`--labels-a`.

## 8. Privacy

The corpus is never committed: the private directory is git-ignored, and the committed ids file
holds ids only. Rows that contain personal identifiers are labelled like any other row; do not
copy them anywhere else.

## 9. Worked examples (illustrative, invented — not corpus rows, not labels of any sample row)

| post | label | note |
|---|---|---|
| `Sen ne aptal bir adamsın` | 0 | ordinary insult, no obscene root (`1` in v1.0 — corrected in v1.1) |
| `Salak herif, siktir git` | 1 | ordinary insult plus a genuine profane root (`siktir`): the profane root decides |
| `Bu film tam bir bok` | 1 | profane root, non-human target — target is irrelevant here |
| `s.i.k.t.i.r git` | 1 | obfuscated, read de-obfuscated |
| `Sıkıntı yok, amca geldi` | 0 | substring collisions only |
| `Saat 10 am'de görüşürüz` | 0 | homonym (`am` = time) |
| `Adam bana "siktir git" demiş, ayıp` | 0 | quoted / reported: the profane word is mentioned, not used |
| `Onlardan başka ne beklenir zaten` | 0 | C1 stereotype, no profane word |
| `Seni bulurum, bekle` | 0 | B2 threat, no profane word |
| `Allah belanı versin` | 0 | `A4 candidate` (sacred concept, pending) |
| `Eşek gibi çalıştım bugün` | 0 | animal word, ordinary sense, no obscene root |

## 10. Version history

| version | date | change | labelled rows affected |
|---|---|---|---|
| v1.0 | 2026-09-18 | first sealed version | none: never used for labelling |
| v1.1 | 2026-09-18 | Owner decision: the A head is **explicit profanity**. An ordinary or mild insult with no obscene or profane root (`aptal`, `salak`, `eşek herif`) is `0`, unless the post also carries a genuine profane root; general insult and offensiveness stay outside the A head. v1.0 contradicted itself here: §3 scored `Eşek herif` `0` as "a vulgar insult but not an obscene root" while §9 scored `aptal`, equally a non-obscene insult, `1`. Changed: §1 anchors "profane expression" to an obscene or profane root instead of "the roots a profanity lexicon is built from"; §2's de-obfuscation examples `s.a.l.a.k` and `aptaaaal` (both non-obscene insults, which read as profanity examples) become `s.i.k.t.i.r` and `siktiiiir`; §3 gains the ordinary-insult row and the dual-register rule's framing is corrected; §9 corrects `aptal` from `1` to `0`, adds one combination example, and its quotation example now quotes a genuine profane word instead of `aptal`. The de-obfuscation, quotation and every other rule are unchanged; only these examples and the definition changed | none |
