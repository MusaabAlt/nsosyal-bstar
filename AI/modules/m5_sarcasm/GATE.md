# m5_sarcasm — entry gate record

Required by `spec.md` §11 (Gate record) and §12 (Acceptance criteria). This file is the
project's record of **which dataset m5 actually obtained**, or of the D1 claim being
dropped. It is filled in as the gate resolves; entries are appended, never rewritten.

**Gate status: OPEN — no dataset obtained, no access request sent yet.**

No m5 code is written while this file says OPEN (`spec.md` §2, team file "Order of work").
`module.py` stays a stub and `test_unit.py` keeps its skipped tests.

---

## 1. Candidate datasets identified

Identification only. **Nothing has been requested or obtained.**

**The deciding field is "Excludes insult/profanity entries?"** (owner instruction, 2026-09-16).
A corpus that excluded them leaves us where `spec.md` §4 says we are: the sarcastic ∩
degrading intersection is untouched, and m5 is a transfer exercise. A corpus that kept them
is not a fallback — it is direct coverage. Every answer below is quoted from the paper's own
data-collection or annotation section; where a paper says nothing, the field reads
**not stated**, never an inference.

| | Candidate A | Candidate B | Candidate C |
|---|---|---|---|
| Exact name | **SarcasTürk** | **IronyTR** ("Extended Turkish Social Media Dataset for Irony Detection") | **Turkish Misunderstood Irony corpus** (no branded name) |
| **Excludes insult/profanity entries?** | **YES — deliberately.** The paper excludes "entries whose main function was direct abuse or swearing" at annotation time. | **NOT STATED.** The topic never appears. The only stated exclusion is close-vote items (4/7 annotators) "to prevent any ambiguity". | **NOT STATED — and abuse is demonstrably kept.** |
| Source of that answer | Paper §3.3.2 (annotation/filtering criteria), quoted above | Full-text sweep of the published PDF: *insult, abus\*, profan\*, offens\*, swear, toxic, hate, vulgar, obscene, slur, curse, küfür, hakaret, argo* — **0 occurrences each**. The whole "Data Collection and Data Set" section is four sentences and names no content filter; the README says only "All data is retrieved from Turkish social media portals." | Full-text sweep of the paper: *insult, abus\*, profan\*, offens\*, swear, toxic, hate, vulgar, obscene, slur* — **0 occurrences each**. No ethics or limitations section. The only stated filters are language (`langdetect`), length (<5 tokens), and irony-hashtag removal. |
| **Date checked** | 2026-09-16 | 2026-09-16 | 2026-09-16 |
| **Obtainable now?** | **Unknown until they reply.** Contact is a 2026 paper, so the addresses are current; no repo, no form, no stated turnaround. | **YES, verified by download today.** `ironic.txt` 25,687 B (300 items) and `non-ironic.txt` 24,930 B (300) under `IronyTR Dataset/`. Repo dormant since 2022-11-11 but live; both authors' pages are current (use `auozturk@ceng.metu.edu.tr` from Öztürk's live page, **not** the 2020 address in the SIU paper). | **YES, verified by download today.** `tr-irony.jsonl`, 1,910,126 bytes, 2,939 records, full text (no tweet-ID hydration). Data committed 2026-05-14. **Trap: the README still says "data (coming soon!)"** — judging availability from the repo page gives the wrong answer. |
| Authors | Niyazi Ahmet Metin, Sevde Yılmaz, Osman Enes Erdoğdu, Elif Sude Meydan, Oğul Sümer, Dilara Keküllüoğlu (Sabancı University) | Aslı Umay Öztürk, Yeşim Cemek, Pınar Karagöz (METU) | Çağrı Çöltekin, Güliz Güneş (University of Tübingen) |
| Publication | "SarcasTürk: Turkish Context-Aware Sarcasm Detection Dataset", SIGTURK 2026 (ACL), pp. 61–71 | "IronyTR: Irony Detection in Turkish Informal Texts", IJIIT 17(4), 2021, pp. 1–18 | "A Corpus of Misunderstood Irony on Turkish Social Media", LREC 2026, pp. 11252–11259 |
| Link (DOI / repo) | DOI 10.18653/v1/2026.sigturk-1.6 · https://aclanthology.org/2026.sigturk-1.6/ | DOI 10.4018/IJIIT.289965 · https://github.com/teghub/IronyTR | DOI 10.63317/3kehaa7yjjqc · https://github.com/coltekin/turkish-irony |
| Size | **1,515 entries** from 98 titles; 774 sarcasm / 741 no-sarcasm | **600 items**; 300 ironic / 300 non-ironic | 3,000 annotated, **2,939 released**; 589 ironic / 2,350 not (≈20%); 3 annotators, Fleiss' κ ≈ 0.56–0.58; per-annotator labels released |
| Version | none; the paper's "initial dataset" (1,000 entries, 53 titles) is an earlier subset, not a separate release | none; it is the extended successor of the 220-item SIU 2020 set | none |
| Licence | **not stated anywhere** — must be asked for in the access request | **none** — no LICENSE file (GitHub API `license: null`); the paper says only "open for research purposes", and the CC BY 3.0 on Crossref covers the article, not the data. All rights reserved by default. | **none at all** — no LICENSE file, no licence sentence in the paper. Default is all rights reserved, so written permission is needed before any submission use. |
| How access is obtained | e-mail to the authors only. No repo, no form. The paper says it "can be shared upon contacting the authors" because it holds sensitive and offensive language | public download from GitHub | public download from GitHub (but see the licence row) |
| Contact | dilara.kekulluoglu@sabanciuniv.edu (senior author), cc ahmet.metin@sabanciuniv.edu (first author) | karagoz@ceng.metu.edu.tr (Prof., verified on the METU faculty page), auozturk@ceng.metu.edu.tr (verified on her live page) | cagri.coeltekin@uni-tuebingen.de, gueliz.guenes@uni-tuebingen.de |

**What candidate C's answer is worth, stated honestly.** It kept the abusive entries, which
by the owner's rule makes it the dataset we want rather than a fallback — but the
intersection it actually contains is tiny. Our own crude lexicon count over the released
file: about **4 strongly abusive ironic items** and at most ~60 mildly insulting ones, and
profanity is *less* frequent in ironic items (0.7%) than non-ironic ones (2.8%), because the
corpus targets misunderstood irony rather than attacks. It also carries **no offensiveness
label** — `annotations` is a boolean irony vote per annotator and nothing else. So it cannot
train the intersection; what it can do is measure whether a SarcasTürk-trained D1 head
degrades on abusive input, which is exactly the blind spot SarcasTürk's exclusion creates.
(Counts are our measurement, not a labelled statistic from the paper.)

**What candidate B's answer is worth.** "Not stated" is not the same as "kept". Our own
crude lexicon scan of the released 600 items found **zero hard profanity** and **6 mildly
insulting items, all in the ironic half (2.0%)** — so in practice IronyTR is effectively
profanity-free, but as an observed property of the text, not a documented criterion. It
carries no offensiveness label either, so it cannot support a joint irony × offensiveness
analysis without new annotation. It leaves us exactly where SarcasTürk does.

**Do not treat IronyTR and the 220-item SIU 2020 set as two corpora.** Verbatim overlap:
**96 of 110** SIU ironic items and **102 of 110** SIU non-ironic items appear inside IronyTR.
It is a superset, and using both double-counts ~90% of the smaller set. The two papers also
disagree on annotation (SIU: 3 annotators, majority vote; IronyTR: 7 annotators with a 4/7
close-vote exclusion), and IronyTR does not say whether the inherited items were
re-annotated.

**Format trap for candidate C:** despite the `.jsonl` extension the file is Python-repr,
not JSON — `json.loads` fails on every line, `ast.literal_eval` works.

**A caution that applies to any re-check of these numbers.** A plain substring grep for
Turkish insult roots is badly wrong: `lan` matches *olan/plan/bulan*, `mal` matches
*normal/olmalı/Kemal*, `sik` matches *sıkıntı/bisiklet*, `göt` matches *götür*. On IronyTR
that inflates the count from 6 to ~100. Word-boundary matching is required, which is the
same lesson m1's `SUBSTRING_COLLISION` fixtures encode.

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
| 2026-09-16 | Owner instruction: record the insult/profanity exclusion per candidate, with its source, plus date checked and whether access is live. Answers added: SarcasTürk **excludes** (stated), IronyTR **not stated**, Çöltekin & Güneş **not stated** (and abuse present in the released text). Candidate C added to the table. Still no request sent. |
