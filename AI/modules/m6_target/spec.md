# M6 — Target Resolution and Doxing

**Type:** signal
**Owner:** _assign_

---

## 1. Objective

Two jobs that share the same machinery:

1. **Target resolution** — decide who the abuse is aimed at. This is what upgrades `A1` (untargeted profanity) to `A2` (individual) or `A3` (group) — the decision layer assigns the code from this module's target (ADR-005) — and it is what the graded action policy depends on: insulting a program is not the same event as insulting a person.
2. **Doxing detection (B4)** — publishing identifying information without consent.

---

## 2. What it catches / does not catch

| Catches | Does not catch |
|---|---|
| Target type: `individual`, `group`, `non_human`, `none` | whether the post is offensive at all — target is resolved regardless |
| `B4` doxing, via patterns and named entities | any other content category → M3 / M4 / M5 |
| The evidence span that justifies the target decision | who the target actually is — no identification, no lookup, no enrichment |
| | thread-level repetition → counted by the pipeline |

**Privacy boundary — this is a hard line, not a preference.** M6 detects that
identifying information is *present*. It never resolves, verifies, enriches or
stores the identity behind it. No lookup against any external source, no
attempt to confirm that a phone number is real, no linking a mention to a
person. A moderation system that builds identity records while detecting doxing
has become the thing it was built to stop, and a jury will notice the
contradiction immediately.

**Also out of scope:**

- **Verifying group membership.** The module decides that a group is being
  addressed, not whether the claim about that group is true or whether the
  speaker belongs to it.
- **Severity.** Target type assigns the family-A code (`A1`/`A2`/`A3`) in the
  decision layer (ADR-005), not here. M6 reports the type and its evidence.
- **`B1`–`B3` and `B5`.** They sit in family B but they are semantic, and they
  belong to M3's B head. M6 owns `B4` only, because doxing is a pattern task.

---

## 3. Target taxonomy

| Value | Meaning | Signal |
|---|---|---|
| `individual` | a named person, a mention, a second-person pronoun | `@handle`, `sen`, vocatives |
| `group` | a group forming part of members' identity — ethnicity, gender, religion, political affiliation | group nouns, plural identity terms |
| `non_human` | institution, program, event, object | product names, org names |
| `none` | no target — untargeted profanity | — |

Note on scope: the reference Turkish corpus explicitly includes sports-club supporters as a group. Decide your own position on this and write it down; do not leave it to the annotator's instinct.

---

## 4. Three documented ambiguities you must handle explicitly

**4.1 The `siz` problem.** Turkish `siz` can address one person formally or several people. The reference Turkish corpus documents a concrete case where two annotators split between `group` and `individual` for exactly this reason. Resolve it with a **declared rule** in the guideline. Any rule is acceptable; an undeclared rule is not.

**4.2 Institution versus its members.** Attacking an institution and attacking the people in it are different events. In the reference taxonomy, an attack on an institution falls outside the harm taxonomy entirely, while the Turkish corpus places it in `other` — and `other` was reported as the single most confusing label for annotators. In the Turkish context (parties, directorates, partisan newspapers) this is the largest source of disagreement you will face. Declare the boundary.

**4.3 Religion versus its followers.** An attack on the followers of a religion is an identity attack; an attack on the religion itself is not. This distinction matters a great deal in the Turkish context, where religiously-framed insults are common. It interacts directly with `A4` in M1 — coordinate with that module's owner.

---

## 5. Doxing (B4)

Doxing is more pattern than semantics, which makes it the one B-family category detectable with high precision by rules.

**Detect:** phone numbers, addresses, workplace identification, national ID patterns, links to private profiles, references to medical or criminal records.

**Method:** named entity recognition plus regular expressions, both tuned for Turkish formats. Do not rely on the encoder for this.

**Precision before recall.** A false doxing alarm is more expensive than a missed case: it escalates a benign post to a human reviewer and, in the graded policy, may block it. Tune the operating point accordingly and say so in the report.

### Named tools

**Regex layer — write it yourself, for Turkish formats specifically.** Turkish
mobile numbers (`05xx`, `+90 5xx`), landline area codes, national ID number
shape and its checksum, IBAN starting `TR`, plate formats, and Turkish address
conventions (`Mah.`, `Sok.`, `No:`, `Daire`). Generic international regexes
miss most of these. The checksum matters: validating it is what separates a
real identifier from an arbitrary eleven-digit number, and it is the cheapest
precision win in this module.

**Named-entity layer — v1: a gazetteer plus morphological analysis (`zeyrek` or
Zemberek)** (ADR-007). Turkish first names, surnames, place names and institution
names, matched with suffix awareness. No model and no extra encoder pass. No
transformer NER in v1: VNLP and the BERTurk-based NER models are not used.

Record the licence of every gazetteer source and of the analyser, and measure it.

**Precision before recall, operationally.** Set the operating point so that a
`B4` fires only on a validated pattern or a high-confidence entity. A false
doxing alarm escalates a benign post to a human and, under the graded policy,
may block it. State the chosen operating point and its measured precision in
the report rather than leaving it implicit.


---

## 6. Contract

**Reads:** `ctx.text` (raw — mentions and formatting matter)

**Writes:**
- `out.target` — a `TargetResult` with `type`, `evidence`, `confidence`
- `out.signals["target_type"]` (a `TargetType` value) and `out.signals["target_confidence"]` — the same target, published for M1, which raises `NON_HUMAN_TARGET` from it (ADR-005)
- `out.content` — `B4` when doxing patterns fire; every `B4` score carries the `span` of the exact substring that triggered it. No span is a contract violation (ADR-001).

**Never** sets `threshold` or `fired`.

---

## 7. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Treating an undeclared `siz` rule as "obvious" | Documented annotator disagreement in the reference Turkish corpus. |
| Importing the reference functional-suite labels for non-protected targets as-is | That suite labels abuse against non-protected targets as *not hateful*. Your project's definition follows the offensive-language convention, where such abuse **is** offensive with target `other`. Importing the labels unchanged inverts your gold standard. Relabel on localization. |
| Using the encoder as the primary doxing detector | Pattern task. Rules give higher precision at lower cost. |
| Resolving a non-human target as `individual` or `group` | M1 raises `NON_HUMAN_TARGET` only from a published `non_human` target, and the decision layer assigns `A2`/`A3` from the type (ADR-005): a wrong type turns "this program is terrible" into abuse of a person. |

---

## 8. Metrics this module must produce

- **Target-type accuracy** on a hand-labelled slice, with a confusion matrix — the `individual`/`group` confusion cell is the one to watch.
- **B4 precision first**, then recall, with CIs.
- **Non-human resolution proof** on abuse directed at objects, programs and institutions: the target resolves as `non_human`, from which M1 raises the `NON_HUMAN_TARGET` guard (ADR-005).
- **Agreement number** on the target label in your own annotation. Compare it to the reference corpus's reported full-label-set agreement so a reader can judge whether yours is normal.

---

## 9. Required fixtures

- Mentions, second-person singular and plural, vocatives.
- `siz` cases covering both readings.
- Institution-versus-members pairs.
- Religion-versus-followers pairs.
- Abuse aimed at a program, a bus, a match result — all must resolve target `non_human`.
- Doxing positives with Turkish-format phone numbers and addresses.
- Doxing near-misses: a public business address, a publicly announced event location. These must **not** fire.

---

## 10. Acceptance criteria

- [ ] All three ambiguities resolved by a written rule in the annotation guideline.
- [ ] Target-type confusion matrix reported.
- [ ] B4 precision reported before recall, with CIs.
- [ ] Target `non_human` resolved on every non-human target fixture, and published in `signals["target_type"]`.
- [ ] Every `B4` `ContentScore` carries the span of the exact triggering substring (ADR-001), asserted by a unit test.
- [ ] Agreement number reported and benchmarked against the reference corpus.
- [ ] Relabelling decision for non-protected targets documented explicitly.

---

## 11. Research pointers

- The OLID three-level scheme — level C defines individual / group / other.
- The Turkish OffensEval corpus paper — read its annotation notes for the `siz` case and the `other` confusion discussion.
- The unified harmful-content taxonomy — read its doxing definition and its identity-attack boundary rules.

---

## 12. Definition of done

Target types are resolved with a declared rule for each ambiguity, doxing fires precisely, non-human target resolution is proven by fixtures, and the relabelling decision is written down where a judge can find it.
