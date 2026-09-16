# m5_sarcasm — entry gate record

Required by `spec.md` §11 (Gate record) and §12 (Acceptance criteria). This file is the
project's record of **which dataset m5 actually obtained**, or of the D1 claim being
dropped. It is filled in as the gate resolves; entries are appended, never rewritten.

**Gate status: OPEN — no dataset obtained, no access request sent yet.**

No m5 code is written while this file says OPEN (`spec.md` §2, team file "Order of work").
`module.py` stays a stub and `test_unit.py` keeps its skipped tests.

---

## 1. Candidate datasets identified

Identification only. Neither has been requested or obtained yet.

| | Primary candidate | Fallback candidate |
|---|---|---|
| Exact name | **SarcasTürk** | **IronyTR** ("Extended Turkish Social Media Dataset for Irony Detection") |
| Authors | Niyazi Ahmet Metin, Sevde Yılmaz, Osman Enes Erdoğdu, Elif Sude Meydan, Oğul Sümer, Dilara Keküllüoğlu (Sabancı University) | Aslı Umay Öztürk, Yeşim Cemek, Pınar Karagöz (METU) |
| Publication | "SarcasTürk: Turkish Context-Aware Sarcasm Detection Dataset", SIGTURK 2026 (ACL), pp. 61–71 | "IronyTR: Irony Detection in Turkish Informal Texts", IJIIT 17(4), 2021, pp. 1–18 |
| Link (DOI / repo) | DOI 10.18653/v1/2026.sigturk-1.6 · https://aclanthology.org/2026.sigturk-1.6/ | DOI 10.4018/IJIIT.289965 · https://github.com/teghub/IronyTR |
| Size | **1,515 entries** from 98 titles; 774 sarcasm / 741 no-sarcasm | **600 items**; 300 ironic / 300 non-ironic |
| Version | none; the paper's "initial dataset" (1,000 entries, 53 titles) is an earlier subset, not a separate release | none; it is the extended successor of the 220-item SIU 2020 set |
| Licence | **not stated anywhere** — must be asked for in the access request | no LICENCE file in the repo; the paper says "open for research purposes" (the article itself is CC BY 3.0 per Crossref) |
| How access is obtained | e-mail to the authors only. No repo, no form. The paper says it "can be shared upon contacting the authors" because it holds sensitive and offensive language | public download from GitHub |
| Contact | dilara.kekulluoglu@sabanciuniv.edu (senior author), cc ahmet.metin@sabanciuniv.edu (first author) | karagoz@ceng.metu.edu.tr (senior author), auozturk@ceng.metu.edu.tr |

**Why SarcasTürk is the right primary.** Every property in `spec.md` §2 and §6 matches it:
1,515 samples, distributed on request, accuracy 0.73 without title context and 0.76 with it
(fine-tuned BERTurk), and entries "whose main function was direct abuse or swearing" excluded
at annotation time — which is exactly the untouched intersection `spec.md` §4 builds on.

**Two corrections to the spec's own description**, both for Musaab:
- The corpus is built from **Ekşi Sözlük** entries with LLM-written title-level context
  summaries, not from news headlines or Zaytung. The Zaytung-based resource is Onan &
  Toçoğlu's **satire** corpus, a different and much larger dataset.
- The exclusion of abusive entries is a **filtering rule, not a cleanliness claim**: the
  paper's ethics section warns the data still contains uncensored slurs, swearing and
  sexual content. Handling it needs the same care as the Çöltekin corpus.

**Identity warning (spec §2), concretely.** Small Turkish irony sets in the literature run
to 144 (Dülger 2018), 194 (Taslıoğlu & Karagöz 2017), 220 (Cemek et al., SIU 2020) and 600
(IronyTR). The 220 and the 600 come from the same METU group and share a GitHub org, and are
routinely conflated; IronyTR is the correct citation for the 600. A count of 1,000 for
SarcasTürk refers to its initial subset, not the release.

**A fourth option, not chosen, recorded so it is not rediscovered later:** Çöltekin & Güneş
(2026), "A Corpus of Misunderstood Irony on Turkish Social Media" (LREC 2026, 3,000 tweets
with conversational context, DOI 10.63317/3kehaa7yjjqc). Larger than IronyTR and carries
context, but its data-distribution URL and class balance are unverified. Musaab decides
whether it displaces IronyTR as the fallback.

**Identity warning (spec §2).** At least two distinct small Turkish irony datasets with
different sizes circulate in citations. The name, version and size above are recorded
exactly as the authors state them, and any dataset used later must match this row.

---

## 2. Access request

| Field | Value |
|---|---|
| Dataset requested | SarcasTürk (primary candidate) |
| Sent to | dilara.kekulluoglu@sabanciuniv.edu, cc ahmet.metin@sabanciuniv.edu |
| Date sent | **not sent** — draft in [`ACCESS_REQUEST_DRAFT.md`](ACCESS_REQUEST_DRAFT.md) |
| Sent by | Abdullah |
| Channel | e-mail (the only route the paper documents) |
| Reply received | _none_ |
| Date of reply | _none_ |
| Outcome | **pending** — granted / refused / no reply |

Seen by Musaab before sending: **not yet**. The team file requires the corpus to be
named and reported to Musaab before any access request leaves.

---

## 3. Outcome and what follows (spec §2)

| Outcome | Action | Status |
|---|---|---|
| Corpus granted | Proceed with the full plan | not reached |
| Not granted | Fall back to the public irony dataset; every result labelled **exploratory** | not reached |
| Neither available | **Drop the D1 claim** from the project, with the reason recorded here | not reached |

Silence is an acceptable outcome for this module (spec §2). A dropped claim documented
here is a delivered result, not a failure.

---

## 4. Numbers (filled only after the gate passes)

Left blank on purpose: no dataset, no numbers. Precision on the benign-sarcasm control
set is reported **before** recall (spec §10, §12).

| Metric | Value | 95% CI | Notes |
|---|---|---|---|
| Control-set precision (gates acceptance) | _blank_ | _blank_ | |
| D1 recall | _blank_ | _blank_ | |
| Annotation agreement on the D1 slice | _blank_ | _blank_ | published however low |
| D1 ↔ family C confusion count | _blank_ | — | proves the polarity rule works |
| Exploratory label applied? | _blank_ | — | yes if the fallback dataset was used |

---

## 5. Log

| Date | Entry |
|---|---|
| 2026-09-16 | Gate record created. Status OPEN, no request sent, no dataset obtained. |
| 2026-09-16 | Candidates identified from primary sources: SarcasTürk (primary), IronyTR (fallback). Recorded in `spec.md` §2.1 as a proposed change awaiting Musaab. Access request drafted, not sent. |
