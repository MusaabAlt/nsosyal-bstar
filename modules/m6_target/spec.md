# M6 — Target Resolution and Doxing

**Type:** signal
**Owner:** _assign_

---

## 1. Objective

Two jobs that share the same machinery:

1. **Target resolution** — decide who the abuse is aimed at. This is what upgrades `A1` (untargeted profanity) to `A2` (individual) or `A3` (group), and it is what the graded action policy depends on: insulting a program is not the same event as insulting a person.
2. **Doxing detection (B4)** — publishing identifying information without consent.

---

## 2. Target taxonomy

| Value | Meaning | Signal |
|---|---|---|
| `individual` | a named person, a mention, a second-person pronoun | `@handle`, `sen`, vocatives |
| `group` | a group forming part of members' identity — ethnicity, gender, religion, political affiliation | group nouns, plural identity terms |
| `non_human` | institution, program, event, object | product names, org names |
| `none` | no target — untargeted profanity | — |

Note on scope: the reference Turkish corpus explicitly includes sports-club supporters as a group. Decide your own position on this and write it down; do not leave it to the annotator's instinct.

---

## 3. Three documented ambiguities you must handle explicitly

**3.1 The `siz` problem.** Turkish `siz` can address one person formally or several people. The reference Turkish corpus documents a concrete case where two annotators split between `group` and `individual` for exactly this reason. Resolve it with a **declared rule** in the guideline. Any rule is acceptable; an undeclared rule is not.

**3.2 Institution versus its members.** Attacking an institution and attacking the people in it are different events. In the reference taxonomy, an attack on an institution falls outside the harm taxonomy entirely, while the Turkish corpus places it in `other` — and `other` was reported as the single most confusing label for annotators. In the Turkish context (parties, directorates, partisan newspapers) this is the largest source of disagreement you will face. Declare the boundary.

**3.3 Religion versus its followers.** An attack on the followers of a religion is an identity attack; an attack on the religion itself is not. This distinction matters a great deal in the Turkish context, where religiously-framed insults are common. It interacts directly with `A4` in M1 — coordinate with that module's owner.

---

## 4. Doxing (B4)

Doxing is more pattern than semantics, which makes it the one B-family category detectable with high precision by rules.

**Detect:** phone numbers, addresses, workplace identification, national ID patterns, links to private profiles, references to medical or criminal records.

**Method:** named entity recognition plus regular expressions, both tuned for Turkish formats. Do not rely on the encoder for this.

**Precision before recall.** A false doxing alarm is more expensive than a missed case: it escalates a benign post to a human reviewer and, in the graded policy, may block it. Tune the operating point accordingly and say so in the report.

---

## 5. Contract

**Reads:** `ctx.text` (raw — mentions and formatting matter)

**Writes:**
- `out.target` — a `TargetResult` with `type`, `evidence`, `confidence`
- `out.content_scores` — `B4` when doxing patterns fire
- `out.guards` — `NON_HUMAN_TARGET`

**Never** sets `threshold` or `fired`.

---

## 6. Forbidden — with reasons

| Forbidden | Why |
|---|---|
| Treating an undeclared `siz` rule as "obvious" | Documented annotator disagreement in the reference Turkish corpus. |
| Importing the reference functional-suite labels for non-protected targets as-is | That suite labels abuse against non-protected targets as *not hateful*. Your project's definition follows the offensive-language convention, where such abuse **is** offensive with target `other`. Importing the labels unchanged inverts your gold standard. Relabel on localization. |
| Using the encoder as the primary doxing detector | Pattern task. Rules give higher precision at lower cost. |
| Firing on a non-human target without the guard | The guard is what proves precision on "this program is terrible" cases. |

---

## 7. Metrics this module must produce

- **Target-type accuracy** on a hand-labelled slice, with a confusion matrix — the `individual`/`group` confusion cell is the one to watch.
- **B4 precision first**, then recall, with CIs.
- **Zero-firing proof** on abuse directed at objects, programs and institutions, via the `NON_HUMAN_TARGET` guard.
- **Agreement number** on the target label in your own annotation. Compare it to the reference corpus's reported full-label-set agreement so a reader can judge whether yours is normal.

---

## 8. Required fixtures

- Mentions, second-person singular and plural, vocatives.
- `siz` cases covering both readings.
- Institution-versus-members pairs.
- Religion-versus-followers pairs.
- Abuse aimed at a program, a bus, a match result — all must trigger the guard.
- Doxing positives with Turkish-format phone numbers and addresses.
- Doxing near-misses: a public business address, a publicly announced event location. These must **not** fire.

---

## 9. Acceptance criteria

- [ ] All three ambiguities resolved by a written rule in the annotation guideline.
- [ ] Target-type confusion matrix reported.
- [ ] B4 precision reported before recall, with CIs.
- [ ] Zero firing on the non-human target fixtures.
- [ ] Agreement number reported and benchmarked against the reference corpus.
- [ ] Relabelling decision for non-protected targets documented explicitly.

---

## 10. Research pointers

- The OLID three-level scheme — level C defines individual / group / other.
- The Turkish OffensEval corpus paper — read its annotation notes for the `siz` case and the `other` confusion discussion.
- The unified harmful-content taxonomy — read its doxing definition and its identity-attack boundary rules.

---

## 11. Definition of done

Target types are resolved with a declared rule for each ambiguity, doxing fires precisely, the non-human guard is proven by fixtures, and the relabelling decision is written down where a judge can find it.
