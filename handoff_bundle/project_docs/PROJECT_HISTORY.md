# NSosyal B* — Project History

The complete record, in English, of what was done, what was found, and what was
believed and later found to be wrong.

**Sourcing rule for this document.** Every number below is copied from
`docs/RESULTS_LOG.md`, a `results/*/findings.md`, or a `phases/*.md`, and every
commit SHA from `git log`. Nothing is reconstructed from memory, and nothing
appears here that does not appear in one of those files. Where a figure has been
corrected, the corrected value is given and the superseded one is shown beside
it — the corrections are part of the record, not noise to be tidied away.

`docs/RESULTS_LOG.md` is **append-only**: when a later result contradicts an
earlier one, a new row says so and the old row stays visible. This document
follows the same rule at the level of interpretation, which is what §11 is for.

---

## 1. The premise and the question

The corpus is Çöltekin's OffensEval-TR 2020 Turkish training set:
**31,756 rows, 25,625 `NOT` / 6,131 `OFF` (19.3%)**, sha256 `8509c01c…`. The
frozen profanity lexicon (`karaliste.txt`, sha256 `0f5a05f5…`) has **695
entries**. *(report §1.1–1.2, from `results/day1_report.json`.)*

Day 1 established the premise, and it is a fact about the **filter**, not about
any model:

| matching rule | `OFF` caught by the lexicon | `OFF` missed |
|---|---:|---:|
| exact word match | 1,787 | 4,344 |
| **root match (adopted)** | **2,239** | **3,892** |

**3,892 of 6,131 offensive messages (63.5%) match no lexicon root at all.**
Root matching was adopted deliberately even though it *weakens* the project's own
case — it makes the lexicon stronger and the lexicon-free slice smaller. Under
the weaker exact-match rule the reported gap would look larger. *(report §1.2.)*

The question the project asks: **does that gap survive a real trained
transformer, or does BERTurk learn the phenomenon on its own?**

---

## 2. The instruments, fixed before measurement

- **Split.** 85/15 stratified on label, seed 42, written once to
  `data/splits/split_seed42.json` and thereafter only read. Train 26,992 (5,211
  `OFF`) / dev 4,764 (920 `OFF`), both 19.3% `OFF`. Dev fingerprint
  **`034415af3a23b388`**, written into every result file; drivers abort if it
  differs.
- **Slices**, assigned by the frozen matcher independently of any model output:
  `lexicon_hit` **614 rows (355 OFF, 57.8%)**, `lexicon_free` **4,150 rows (565
  OFF, 13.6%)**.
- **Model.** `dbmdz/bert-base-turkish-cased`, 3 epochs, batch 32, lr 2e-5, linear
  warmup 10%, max_len 128, fp16, **no class weighting**, **decision threshold
  fixed at 0.5**, seed 42, NVIDIA L4. One configuration, no hyperparameter
  search — a sweep would favour whichever arm received it.
- **Test set.** Opened exactly once, in phase 05, and now **spent**.

---

## 3. Chronology

### Day 1 reproduction check — 2026-08-15

`day1_gate_en.py` + `tests/_verify_day1_reproduction.py`. **16/16 frozen fields
reproduce exactly**; corpus and lexicon hashes match the frozen record. The port
into `src/` had not drifted. *(RESULTS_LOG row 1.)*

### Phase 01 — baseline diagnosis

**Question:** does the lexicon-free gap survive a trained transformer?

**Pre-registration:** `phases/01_baseline_diagnosis.md`, committed **`197d953`**
before any BERTurk number existed. Two things were fixed in advance:

1. **A three-outcome decision rule** on the bootstrap CI of the recall gap —
   (1) CI excludes zero → gap survives; (2) CI includes zero *and* point estimate
   under ~5pp → gap genuinely closed, a real result that would have reweighted
   the whole project; (3) CI includes zero *but* the estimate is large →
   **INCONCLUSIVE ON DEV**, report the honest CI width, do **not** promote it to
   a finding, and do **not** touch the test set to resolve it.
2. **A power basis for outcome 3**: with 355 and 565 gold-`OFF` denominators the
   95% CI of the difference is roughly ±6pp, so a ~20pp gap is detectable and a
   ~4pp gap is not. "An underpowered null is silence, not evidence of absence."
3. **A binding constraint on every later phase**: cross-slice comparison is
   **OFF-recall only**, because the slices' base rates differ 57.8% vs 13.6% and
   per-slice macro-F1 or accuracy would report class balance as if it were model
   behaviour.

**Preflight** (`--stage preflight`, local): sanity gate PASS — the tagger
reproduces 3,892/6,131 on the full corpus. Keyword filter on dev: macro-F1
**0.6799 [0.6621, 0.6969]**, OFF-recall **0.3859 [0.3539, 0.4187]**,
OFF-precision 0.5782.

**Training run** (`--stage train`, commit `837c351`, result committed `685d4af`):

| | value | 95% CI |
|---|---:|---|
| macro-F1 | **0.8271** | [0.8139, 0.8405] |
| OFF-recall | 0.6902 | [0.6603, 0.7191] |
| OFF-precision | 0.7488 | — |
| `lexicon_hit` OFF-recall (355 OFF) | **0.8930** | [0.8618, 0.9248] |
| `lexicon_free` OFF-recall (565 OFF) | **0.5628** | [0.5210, 0.6010] |
| **recall gap** | **+0.3301** | **[+0.2771, +0.3827]** |

**Verdict applied: outcome 1 — the gap survives.** The CI excludes zero and sits
far above the ~6pp resolution floor.

A second finding was recorded in the same row: **the shortcut runs in both
directions.** False-positive rate on gold-`NOT` rows is **47/259 = 18.1%** inside
`lexicon_hit` against **166/3,585 = 4.6%** inside `lexicon_free` — roughly 4×.
Profanity presence over-triggers `OFF` and its absence under-triggers.

Three loose ends were recorded rather than smoothed: a Day-1 impression that
30–35% of the lexicon-free slice was annotation noise (making the gap an upper
bound); and a checkpoint tie — epochs 1 and 3 have **identical confusion
matrices** but disagree on **198/4,764** dev rows, so up to 43 of the 285 false
negatives could be checkpoint-specific. All reported numbers are `best.pt` =
epoch 1.

### Phase 02 — failure analysis (read-only)

**Question:** what are the failures actually made of, and how much of the gap is
annotation noise?

All **285 false negatives** and all **213 false positives** were read and tagged
by hand. *(`results/02_failure_analysis/findings.md`; RESULTS_LOG rows 4–5;
commits `3063681`, `a500d08`.)*

**Finding 1 — the noise estimate was an artifact of how it was sampled.**

| tag | top-60 by confidence (biased) | random 40 of 247 (seed 42) |
|---|---:|---:|
| plausibly mislabeled | 14 (23%) | **4 (10%)** |
| genuine implicit offense | 18 (30%) | 14 (35%) |
| surface evasion | 6 (10%) | 1 (2.5%) |
| ambiguous — needs a human ruling | 22 (37%) | **21 (52.5%)** |

Sorting by confidence *selects* for label noise. The defensible rate is **~10%**,
not 30–35%. The largest single bucket in the unbiased sample is not noise and not
clear implicit offense but **convention-dependent (52.5%)**.

**Finding 2 — the false-positive side.** **95 of 213 (44.6%)** carry a profanity
token; of those, **84 (88.4%) perform no offensive act** — non-directed 26,
filler 19, sense-collision 16, meta-discussion 9, negated 6, quoted 5,
self-directed 3, and only **11** directed insults where the gold label looks
wrong. Within the 47 `lexicon_hit` false positives, **43 (91.5%)** are not a
directed offensive use.

**Finding 3 — slice contamination.** `hit_root` matches any token starting with a
lexicon entry of ≥3 characters, so `allah` alone accounts for ~130 of the 614
hit-slice rows, plus `emi`→`eminim`, `mal`→`malatya`, `göt`→`götürür`,
`cim`→`cimbom`.

**Finding 4 — checkpoint stability.** **0 of the top-60 FN** and **1 of the
top-40 FP** are checkpoint-specific; the 43 checkpoint-specific FN sit at the
boundary (median p_OFF **0.4017** vs **0.1724** for stable ones).

**Phase 02 close — the contamination sensitivity** *(`slice_sensitivity.json`)*.
A row is excluded only if **every** lexicon root matching **any** of its tokens
is in the suspect set `{allah, ana, cim, emi, göt, mal, sie}`:

| | hit recall | free recall | **gap** | 95% CI |
|---|---:|---:|---:|---|
| as reported (frozen definition) | 0.8930 | 0.5628 | **+0.3301** | [+0.2771, +0.3827] |
| 248 of 614 suspect-only rows excluded | 0.9291 | 0.5628 | **+0.3662** | [+0.3187, +0.4169] |

**Shift +0.0361 — the contamination was *understating* the gap.** The excluded
rows are 175 `NOT` / 73 `OFF`, i.e. overwhelmingly non-offensive, so they diluted
the hit slice toward the free slice.

**Rulings recorded here.** Çöltekin's annotation convention is adopted as given
and **nothing is relabelled**; the stated cost is that ~13 of the 40 unbiased
lexicon-free FN are criticism of politicians or institutions and stay counted in
every reported number. The headline stays **+0.3301** under the frozen
definition; the sensitivity is a robustness check, not a replacement.

**Central claim recorded at this point:** *the model detects offensive
**vocabulary** rather than offensive **acts***. See §11.2 — this claim was later
narrowed.

### Phase 03 — the defense

**Question:** can the diagnosis be turned into a fix?

**Pre-registered constraints:** `phases/03_defense_design.md`, first committed
with step 1 at **`5203ec5`**; the constraints are dated 15 Aug 2026 "before any
code".

- **C1 — insertion patterns must not be derived from dev.** 1b's patterns come
  from **out-of-fold** training errors only: 5-fold stratified CV inside the
  training split, seed 42, producing predictions for all 26,992 rows from models
  that did not see them. Dev's FP families are used *only* to check afterwards
  that the diagnosis generalises. Comparison permitted, derivation forbidden.
- **C2 — 1a must not inject label noise.** Masking applies only to gold-`OFF`
  rows carrying offensive structure independent of the profanity token.
- **C3 — attack-family disjointness.** Train on family **D** (vowel deletion,
  homoglyphs, character doubling), evaluate on **H** (punctuation injection,
  diacritic stripping, consonant transposition), asserted at both call sites.
- **C4 — deltas reported with CIs regardless of sign.**
- **A failure mode named in advance:** *"a within-gap trade where `lexicon_hit`
  recall falls and the gap narrows for the wrong reason — which is why all four
  metrics are reported together."* This prediction matters later (§11.6).

**Step 1** (`5203ec5`): out-of-fold macro-F1 **0.8230**, OFF-recall 0.6985,
OFF-precision 0.7280 — close to dev's 0.8271/0.6902/0.7488, which is why OOF was
chosen. 1,360 FP (251 hit / 1,109 free), 1,571 FN. The training side surfaced two
patterns dev never showed — a slur aimed at a non-person, and adverbial manner
use — and both entered the operator set.

**Step 2 — the review gate** (`9aa00cd`). 1a yield after tightening: **382 of
5,211 gold-`OFF` rows (7%)**. **Three defects were caught by reading**, not by
metrics: suspect-root false hits being masked; rows where the profanity *is* the
offense still qualifying; and 1b splicing mid-clause into ungrammatical rows.
Each became a rule plus a regression test. None would have been visible in any
aggregate afterwards.

**Steps 3–4 — four runs** (`00b9139`, `00c6521`, results `e92d306`):

| metric | raw | +1a | +1a+1b | +1a+1b+D |
|---|---:|---:|---:|---:|
| macro-F1 | 0.8271 | 0.8244 | 0.8173 | 0.8202 |
| `lexicon_free` OFF-recall | 0.5628 | 0.5204 | 0.5841 | **0.5965** |
| `lexicon_hit` OFF-recall | 0.8930 | 0.8873 | 0.8282 | 0.8507 |
| `lexicon_hit` FP rate | 0.1815 | 0.1737 | 0.1853 | **0.1931** |
| recall gap | +0.3301 | +0.3670 | +0.2441 | +0.2542 |
| false positives (total) | 213 | 182 | 232 | 245 |
| — no profanity token (proxy) | 185 | 156 | 205 | 215 |
| H-perturbed OFF-recall | 0.6565 | 0.6261 | 0.6652 | 0.6793 |

Paired deltas against raw (1,000 resamples, identical rows):

| | macro-F1 | `lexicon_free` OFF-R | `lexicon_hit` OFF-R |
|---|---|---|---|
| +1a | −0.0027 [−0.0125, +0.0065] | **−0.0425 [−0.0722, −0.0110]** | −0.0056 [−0.0310, +0.0194] |
| +1a+1b | −0.0098 [−0.0208, +0.0006] | +0.0212 [−0.0087, +0.0502] | **−0.0648 [−0.0978, −0.0315]** |
| +1a+1b+D | −0.0069 [−0.0185, +0.0052] | **+0.0336 [+0.0052, +0.0662]** | **−0.0423 [−0.0778, −0.0109]** |

**1a made the model worse at exactly what it targeted** (−0.0425, CI excludes
zero); the likely mechanism is a `[MASK]` token present in training and never at
inference. **1b weakened the lexical cue without replacing it**: the
`lexicon_hit` FP rate it was built to cut went *up*, 0.1815 → 0.1853. The
four-run design attributed the no-profanity FP rise (185 → 215) to **1b and D,
not 1a** — 1a alone lowered it to 156. A combined run would have misattributed
it.

### Phase 04 — calibration and risk–coverage

**Question:** does the model know when it is wrong?

**Pre-registration:** `phases/04_calibration.md`, C4-1…C4-8, committed
**`ab225ad`** before any calibration number existed. It fixed the CAL/EVAL split
(2,382/2,382, stratified, seed 42), the ECE definition (15 bins, with 10 and 20
reported as sensitivity), the operating-point protocol (threshold on CAL, metrics
on EVAL), and — C4-3 — **the prediction that risk–coverage is invariant to
temperature**, because a monotone transform cannot reorder rows.

**Calibration** (`8012c71`), no retraining, no forward pass:

| | raw | +1a+1b+D |
|---|---:|---:|
| fitted temperature | **0.9948** | **1.9732** |
| NLL before → after | 0.2616 → 0.2616 | 0.3831 → 0.2914 |
| ECE (15 bins) | **0.0205 → 0.0191** | **0.0786 → 0.0270** |
| ECE (20 bins) | 0.0206 → **0.0211** | 0.0784 → 0.0313 |
| MCE (15 bins) | 0.1184 | 0.3487 → 0.2056 |
| signed gap (acc − conf) | −0.0091 | −0.0739 |
| saturated (6dp) rows | 0 / 4,764 | 0 / 4,764 |

**Raw BERTurk needs no calibration.** At 20 bins ECE gets marginally *worse* after
scaling — what a no-op plus bin noise looks like — and that was reported rather
than hidden behind the 15-bin headline. **The defense variant is 3.8× worse
calibrated**, putting 1,958 of 2,382 EVAL rows in the top bin at 0.9943 mean
confidence for **93.72%** accuracy. Phase 03 measured accuracy, which barely
moved; confidence quality moved a great deal, downward.

**C4-3 verified exactly**: max absolute difference **0.00e+00**. No claim that
calibration improved selective prediction is available, and none was made.

**Operating points**, thresholds on CAL and metrics on EVAL:

> **High-automation** — 91.2% coverage, **0.8504** macro-F1 / **7.92%** error,
> deferring 8.8%. CI: macro-F1 [0.8287, 0.8721], error [0.0681, 0.0899].
> Threshold **0.6632**.

> **High-precision** — 81.6% coverage, **0.8756** macro-F1 / **5.81%** error,
> deferring 18.4%. CI: macro-F1 [0.8522, 0.8963], error [0.0481, 0.0684].
> Threshold **0.8009**. Selected as the largest coverage with CAL error ≤5.0%;
> realised EVAL error 5.81% — reported, not retuned.

The deferred 8.8% carries **33.3% of all errors, a 3.78× capture lift**, with
41.0% error inside the queue against 7.9% outside. The 5%-error rule picked 80%
coverage for raw but **70% for the defense variant** — its miscalibration
expressed in headcount.

**The null result.** Deferral is **error-selective but slice-blind**:
`lexicon_free` 9.4% vs `lexicon_hit` 9.6% at high-automation, and at
high-precision the ordering **reverses** (23.1% vs 18.6%). `lexicon_free` is
86.8% of the queue against an 87.1% base rate — proportion, not selection. After
deferral `lexicon_hit` is the *worse* residual slice (10.99% vs 7.15% error),
because its error rate is dominated by the 18.1% FP rate. See §11.4.

### Phase 05 — the official test set, single pass

**Question:** does the finding hold on data no design decision ever saw?

3,528 rows (2,812 `NOT` / 716 `OFF`); `lexicon_hit` 491, `lexicon_free` 3,037.
Thresholds **read** from `calibration.json` and applied unchanged;
`thresholds_re_derived_on_test: false`. Run at commit `9af62f9`, results
`5604586`.

| system | macro-F1 | 95% CI | OFF-R | OFF-P |
|---|---:|---|---:|---:|
| keyword filter | 0.6657 | [0.6456, 0.6857] | 0.3757 | 0.5479 |
| **BERTurk raw** | **0.8095** | [0.7930, 0.8261] | 0.6592 | 0.7295 |
| +1a+1b+D | 0.8093 | [0.7927, 0.8255] | 0.6718 | 0.7168 |

| system | hit OFF-R | free OFF-R | gap | 95% CI |
|---|---:|---:|---:|---|
| BERTurk raw | 0.9071 | 0.5101 | **+0.3970** | **[+0.3418, +0.4542]** |
| +1a+1b+D | 0.8810 | 0.5459 | +0.3352 | [+0.2803, +0.3964] |

**The gap replicates and is if anything larger: +0.3970 on test against +0.3301
on dev.** The intervals overlap over [+0.3418, +0.3827], so **the increase is not
itself an established difference** — recorded explicitly as its own log row, so
the two statements always travel together.

The widening has a mechanism: dev → test, `lexicon_hit` recall **rose 1.4pp**
while `lexicon_free` recall **fell 5.3pp**, against an ordinary 1.8pp overall
macro-F1 drop. The model improved on the slice it was already good at and
degraded on the slice it was already bad at.

**Thresholds transferred.** Achieved coverage within 1–2pp of dev in all four
cases; high-automation **90.2% coverage, 0.8485 macro-F1, 8.52% error**, capture
lift **3.59×**; high-precision **79.8%, 0.8900, 5.43%**, lift **3.15×**. The
≤5%-error point set on dev landed at 5.43% — reported, not retuned. **Phase 04's
slice-blindness null replicated exactly** (9.8% vs 10.0%; 20.3% vs 19.6%).

**The defense on test** (`f918ba7`, paired, from saved predictions):
`lexicon_free` OFF-recall **+0.0358 [+0.0043, +0.0665]** — CI excludes zero;
macro-F1 **−0.0002 [−0.0129, +0.0118]**; `lexicon_hit` OFF-recall −0.0260
[−0.0593, +0.0077] — **does not** reach significance, unlike on dev.

**Single-use accounting.** The test set was **opened twice** and this is
recorded, not hidden: 11:09:00 crashed before any forward pass
(`AttributeError: 'Tee' object has no attribute 'isatty'`) producing no
predictions and no numbers; 11:10:36 was the complete run, spend record written
11:11:44. The open log is written *before* the bytes are read precisely so a
crashed attempt cannot disappear. The set is **SPENT**.

### Phase 06 — offline demo

`demo/app.py` on the Python stdlib, verified on an L4 with **all outbound sockets
blocked** by a `sitecustomize` shim. Asset bundle **885.9 MB**; frozen operating
point threshold **0.6632**. Two cold starts, byte-identical output; a hostile
input set (empty, emoji-only, 100k chars, control characters, XSS, malformed
JSON) all survived. Gradio and Streamlit were rejected because both fetch CDN
assets at page load, so an "offline" demo built on either fails as a blank page
at the worst possible moment. *(Commits `5207fa6`, `e02b6ee`.)*

The demo was chosen to show the limitation as readily as the capability: the
`NONDIR` false positive is **deferred** by the review layer, while the implicit
false negatives are **auto-resolved wrongly** — the phase 04 null made visible.

### Phase 07 — technical report

Outline and evidence map committed `05de1fa`, with the KYS template absent and
**six gaps flagged rather than written around**: ConvBERTurk (no evidence, now
unfixable since the test set is spent), Mayda/Beyhan cross-corpus (no data on
disk), held-out obfuscation on test (not measurable now), unverified related-work
figures, quotable failure examples not in the committed record, and two operating
points where the briefing suggested two to three. Sections 1, 2, 4, 5 were
drafted in Turkish (`3697ca9`, `28ff263`, `765fd5c`, `5d6258c`, `cc1744b`,
`fceef1b`); **section 3 remains deliberately empty** pending citation
verification from primary sources.

### Phase 08 — word-level lexical dependence

**Question, from the academic advisor:** what explains the 118 false positives
that carry no profanity token at all?

**Pre-registration:** `phases/08_lexical_analysis.md`, C8-1…C8-11, committed
**`b127d44`** before any token count existed. It fixed: statistics from the
**training split only**; document-frequency counting; a top-200 pool; **binomial
z** as the primary ranking with excess-`OFF`-rows as a linear-weighted secondary;
**|z| ≥ 3.6623** (Bonferroni over 200 tests, two-sided α = 0.05) plus a 1.5×
effect floor; `hit_root` — *not* exact match — as the lexicon-membership rule,
specifically because exact matching would push inflected profanity into the
"non-lexicon" group and **manufacture the very finding under test**; and the
step-3 interpretation **both ways**, so a null could not be reframed afterwards.

**Results** (`7ef51a0`). Training base rate computed, not assumed: **0.193057**.
Of the top 200 tokens by document frequency, **2** are in the karaliste
(`amk` P(OFF|t) = 0.9554, z = 31.68; `allah` 0.2784, z = 5.59), **19** are
non-lexicon strong-`OFF`, **5** are strong-`NOT`, and **174 are unremarkable** —
skew is concentrated in a small vocabulary, not diffuse.

The two weightings disagree instructively: by excess-`OFF`-rows the top entries
are `user` (+282.0) and `bu` (+255.1) — a placeholder and a demonstrative, both
*unremarkable* under the declared thresholds. High-frequency tokens accumulate
large absolute excesses from trivial skews, which is why z was primary.

**The pre-registered test:** A = the 118 no-profanity false positives; B = 3,631
true negatives (dev gold-`NOT` 3,844 minus the 213 FP ids), reweighted to A's
(lexicon-hit × token-count-quartile) distribution.

| comparison | A | matched B | difference | verdict |
|---|---:|---:|---|---|
| **group 2 (pre-registered)** | 0.3983 (47/118) | 0.1917 | **+0.2066 [+0.1216, +0.2960]** | **SUPPORT** |
| wider pool (df ≥ 30) | 0.6017 (71/118) | 0.3000 | +0.3017 [+0.2155, +0.3872] | — |
| **group-3 control (strong-`NOT`)** | — | — | **−0.0032 [−0.0500, +0.0506]** | **null** |

**The control is the load-bearing result.** If the 118 were merely longer or
odder, they would show elevated rates of *both* skew directions. They show the
matched-baseline rate for strong-`NOT` tokens, so the effect is specific to
`OFF`-skewed vocabulary rather than to length or register. Two independent join
checks passed: 6 of the 118 sit on lexicon-hit rows, matching phase 02's
separately-recorded count of 6; and `aq` appears in **zero** of the 118.

**Composition — post-hoc, exploratory, reported with no verdict field.** Ten of
the 19 high-skew non-lexicon tokens are deictic and **five are second-person
pronouns** (`sen`, `senin`, `siz`, `sizin`, `sizi`), with `lan`, `bak`, `adam`,
`bunlar`, `onlar`. P(OFF|`sizin`) = **0.4533** (375 rows), P(OFF|`bunlar`) =
**0.4592** (233 rows), against 0.1931.

**The advisor's structural hypothesis held; the content hypothesis did not at the
resolution proposed.** At the top-200 band only two political/identity terms
exist and they show **+0.0111 [−0.0138, +0.0437]** — no support. At df ≥ 30,
26 appear and show **+0.1494 [+0.0825, +0.2224]** across 23 of the 118, while the
deictic subset at the same resolution is larger: **+0.2106 [+0.1263, +0.2982]**
across 40. The token sets are disjoint but the rows are not — **9 of the 118
carry both**, so the counts do not add. **47 of the 118 (39.8%) carry no strongly
skewed token at any vocabulary tested and remain unexplained.**

**Class balance** (the advisor's second question) was answered in three parts:
(1) on the *absolute level* of `lexicon_free` recall, imbalance plausibly
contributes and **cannot be ruled out** — 1:4.18, no class weighting, threshold
fixed at 0.5, and no weighted variant was ever trained, so its contribution is
**unmeasured**; (2) on the *gap*, no — one model, one threshold, two disjoint
subsets, so a global imbalance depresses both alike; (3) on **slice-conditional
priors** (0.5535 given a lexicon hit vs 0.1410 given none, a 3.92× ratio) the
question dissolves, because that *is* lexical dependence measured as a corpus
property rather than a model behaviour.

**A new limitation was found here.** Five karaliste entries are shorter than
`MIN_ROOT_LEN = 3` (`ag`, `am`, `aq`, `oc`, `oç`), so `hit_root` can **never**
fire on them. **28 of the 565 gold-`OFF` `lexicon_free` dev rows (4.96%)** carry
one; `aq` alone has P(OFF|t) = 0.9860. Bound: if all 28 are correctly classified,
`lexicon_free` recall on the remainder is 290/537 = **0.5400** and the gap widens
+0.3301 → **+0.3529**. **This is a bound, not a measurement.** It is the
*opposite* leak to the one phase 02 measured, and **both known slice-definition
defects push the headline in the same conservative direction.**

### Phase 09 Stage 1 — threshold-free slice comparison

**Question:** how much of the 33pp recall gap is where the 0.5 threshold sits
rather than how well the model ranks? The slices are 57.8% and 13.6% `OFF`, and a
well-calibrated model assigns lower probabilities in the rarer slice.

**Pre-registration:** `phases/09_deeper_analysis.md` C9-1…C9-11, committed
**`12afa74`** before any number existed. The spec as received is at `bcb4b70`;
the diff between them is the sharpening. What was fixed:

- **The thresholds, from a design calculation, not the data.** Hanley–McNeil
  standard errors using only the four frozen denominators and an *assumed* AUC
  said this dataset resolves a difference to about **±0.03–0.04**. Therefore
  **LARGE = G ≥ 0.05**, **SMALL = G < 0.02**, and the band between them was
  declared **inconclusive in advance** rather than left available for spin.
- Tie convention (half credit), the stratified bootstrap scheme, a **five-branch,
  ordered, exhaustive verdict rule** unit-tested on both sides of every boundary
  *before* the data was loaded, what each verdict obliges in the report, three
  sensitivities that may qualify but **may not overturn** the verdict, and an
  explicit ban on recruiting PR-AUC — which is base-rate sensitive — to argue
  either side afterwards.
- **Provenance by content:** the input dump is pinned by sha256 and the stage
  aborts unless it first reproduces all eight recorded phase-01 figures. It did.

**Results** (`120eead`), 10,000 stratified bootstrap replicates, seed 42:

| | `lexicon_hit` | `lexicon_free` |
|---|---|---|
| base rate | 0.5782 | 0.1361 |
| **ROC-AUC** | **0.9306 [0.9102, 0.9495]** | **0.8962 [0.8821, 0.9095]** |
| OFF-recall at 0.5 | 0.8930 | 0.5628 |

**G = +0.0345 [+0.0103, +0.0585] → verdict `INTERMEDIATE`.** The interval
excludes zero, so a ranking-quality difference is real, but the point estimate
lands in the band declared inconclusive, and **the interval spans all three
bands** — exactly the resolution the design calculation predicted.

Score distributions, gold-`OFF`: median **0.9650** in `lexicon_hit` against
**0.5861** in `lexicon_free`; **43.7%** at or below 0.5 against **10.7%**.

Sensitivities: S1 (`MIN_ROOT_LEN` leak removed) gap **+0.0399**; **S2
(suspect-root rows removed) gap +0.0062** — below the smallness floor; S3 (tie
convention) worth **exactly nothing**, identical to four decimals at credit 0,
0.5 and 1. AP 0.9477 vs 0.6479, reported and **inadmissible** to the verdict by
C9-9.

### Phase 09 Stage 1b — ranking or placement?

**Question:** did `+1a+1b+D`'s **+0.0336** `lexicon_free` recall gain come from
better ranking or from moved scores?

**Pre-registration:** C9-12…C9-17, committed **`910d21e`** before any number
existed. It fixed the paired bootstrap; **`run_raw` as the control, not
substitutable** by the phase-01 dump even though they agree on every recorded
scalar; a **four-branch rule with a 0.01 floor** justified on AUC's own scale
(0.01 = 1% of the 565 × 3,585 = 2,025,525 `OFF`/`NOT` pairs in that slice); and —
C9-16 — **a prediction recorded before the number existed**: if the mechanism is
a global score shift, `lexicon_hit` AUC should also be flat while its recall
falls.

**Results** (`09ce5f8`), run against the Drive mirror, 10,000 paired replicates:

| slice | AUC control | AUC treatment | **ΔAUC** | verdict |
|---|---:|---:|---|---|
| `lexicon_free` **(primary)** | 0.8962 | 0.8906 | **−0.005587 [−0.013387, +0.002366]** | **`FLAT`** |
| `lexicon_hit` (control) | 0.9306 | 0.9052 | **−0.025401 [−0.042863, −0.008646]** | **`ORDERING WORSENED`** |

`FLAT` is branch 2, named in advance as *"threshold crossing, not better
ordering"*. It is a **bounded** null: the upper end is **+0.0024**, an order of
magnitude below the 0.01 floor, so an ordering gain large enough to explain
+0.0336 is **excluded**, not merely unproven.

**The whole reported dev effect is 19 rows crossing a line.** Gold-`OFF`
crossings: **+52/−33 = net +19** in `lexicon_free`, **+13/−28 = net −15** in
`lexicon_hit`. 19/565 = +0.0336283 and −15/355 = −0.0422535 reproduce the
recorded recall deltas **exactly to ten decimals**; the gold-`NOT` nets (+29, +3)
sum to +32, matching the recorded 213 → 245 false positives.

**And it is not a uniform shift.** `lexicon_free` gold-`OFF` median rises
0.5861 → 0.7818 while **Q1 falls** 0.2162 → 0.0776 and Q3 rises 0.8193 → 0.9921 —
scores pushed toward both extremes, **consistent with** the recorded
overconfidence (*T* = 1.9732 vs 0.9948, ECE 3.8×) and explicitly **not
demonstrated** by it.

**C9-16's prediction failed, and that is the informative part.** The control did
not stay flat; ordering there measurably worsened. So the intervention is not a
uniform recalibration — it degraded ranking precisely where profanity is present
while leaving it unchanged, within a tight bound, in the slice it was built to
help. The slice AUC gap narrows **+0.0345 → +0.0146**, driven by `lexicon_hit`
falling rather than `lexicon_free` rising (which fell too, to 0.8906).

---

## 4. Pre-registration index

| protocol | file | committed | fixed before any number |
|---|---|---|---|
| Phase 01 | `phases/01_baseline_diagnosis.md` | **`197d953`** | three-outcome decision rule, power basis, OFF-recall-only constraint |
| Phase 03 | `phases/03_defense_design.md` | **`5203ec5`** | C1 derivation source, C2 noise filter, C3 D/H disjointness, C4 signed CIs |
| Phase 04 | `phases/04_calibration.md` | **`ab225ad`** | C4-1…C4-8: CAL/EVAL split, ECE definition, temperature-invariance prediction, rule-defined operating points |
| Phase 08 | `phases/08_lexical_analysis.md` | **`b127d44`** | C8-1…C8-11: train-only statistics, ranking statistic and threshold, `hit_root` grouping, interpretation both ways |
| Phase 09 Stage 1 | `phases/09_deeper_analysis.md` | **`12afa74`** | C9-1…C9-11: numeric LARGE/SMALL from a design calculation, five-branch verdict, PR-AUC ban |
| Phase 09 Stage 1b | `phases/09_deeper_analysis.md` | **`910d21e`** | C9-12…C9-17: non-substitutable control, paired scheme, 0.01 floor, C9-16's recorded prediction |

Two pre-registered predictions were checked against reality: **C4-3 held exactly**
(temperature invariance, 0.00e+00), and **C9-16 failed** — which is what made the
Stage 1b control worth having.

---

## 5. Corrections and supersessions

Five correction rows exist in `docs/RESULTS_LOG.md`. In every case the superseded
text was left in place.

**C1 — Phase 03 framing** *(2026-08-16, commit `19ce53c`)*. Superseded the
*reading*, not the numbers, of the phase 03 rows. Original: *"the defense did not
work as designed"*, treating the `lexicon_free` gain as cancelled by an equal and
opposite loss — the honest reading of dev alone, where the loss (−0.0423
[−0.0778, −0.0109]) excluded zero. On test the same loss is −0.0260 [−0.0593,
+0.0077] and does not reach significance. Replaced by **"the component works, the
system does not"**. Two costs explicitly *not* softened: 1b failed its own stated
purpose, and the variant is badly miscalibrated.

**C2 — two confidence intervals mis-transcribed** *(2026-08-17, commit
`4fb4132`)*. The wider-pool and group-3 control CIs had been quoted from a
**200-resample smoke run** instead of the final 10,000-resample run.

| | logged | correct |
|---|---|---|
| wider pool | +0.3017 [+0.2187, +0.3784] | +0.3017 **[+0.2155, +0.3872]** |
| group-3 control | −0.0032 [−0.0454, +0.0429] | −0.0032 **[−0.0500, +0.0506]** |

Point estimates and every verdict were correct; only the bounds were wrong, and
**both correct intervals are wider** — the error made the results look *more*
precise than the run supports, which is the flattering direction, so it was
corrected explicitly. Root cause recorded: both runs were viewed in one session.
The automated findings-vs-record checker now covers interval bounds, not only
point estimates.

**C3 — the central claim narrowed** *(2026-08-17, commit `6b4a451`)*. Forced by
Stage 1. See §11.2.

**C4 — spec defect, C9-8** *(2026-08-17, commit `910d21e`)*. See §11.5. Logged as
a **SPEC DEFECT** rather than a correction because nothing measured was wrong;
the specification was.

**C5 — what the intervention demonstrates, narrowed** *(2026-08-17, commit
`1db1354`)*. Forced by Stage 1b. See §11.3.

**One recovery, not a correction** *(2026-08-16, commit `8691303`)*.
`results/03_defense/comparison.json` had lived only in an ephemeral Colab clone,
because `phase03_compare.py` writes to the results directory but had no mirror
step. It was regenerated from the saved prediction dumps at a fixed seed and
**reproduced the published table exactly**. The dev deltas were never at risk —
they were in the committed findings and in the log — but the machine-readable
evidence behind them was missing from the repo.

---

## 6. Interpretations later proven wrong

This is the part nothing else in the repo records: not the numbers, which are all
logged, but the readings that were held with confidence and then failed. Each
entry gives what was believed, what replaced it, and why the first belief was
reasonable at the time — because a list of errors that were obviously errors
teaches nothing.

### 6.1 Four early readings, all held confidently, all wrong

**(a) "Annotation noise in the lexicon-free slice is 30–35%."**
Held after Day 1. **Actual: ~10%** (4 of an unbiased random 40, seed 42).
*Why it was wrong:* the estimate came from reading the **most confidently wrong**
rows, and sorting by confidence *selects* for label noise — the model is
confident a row is not offensive precisely when it really isn't. The head of that
ordering is not the slice. **What replaced it:** an unbiased random sample, and
the discovery that the largest bucket is neither noise nor clear offense but
**convention-dependent (52.5%)**. The correction *strengthened* the headline: the
33pp gap is far less noise-contaminated than the Day-1 caveat implied.

**(b) "Use–mention is the central false-positive family."**
It is not. Use–mention proper — meta-discussion, negation, quotation — is
**20 of 213 rows (9%)**. The real family is broader and blunter: **84 of the 95
profanity-bearing false positives (88.4%) perform no offensive act at all**,
dominated by non-directed use (26), filler (19), and sense collision (16).
*Why it was wrong:* use–mention is the linguistically interesting category and
the one that comes to mind first; it was mistaken for the bulk of the phenomenon
because it is the most articulable part of it. **What replaced it:** the wider
claim, which is also the stronger one — the model keys on token *presence*, not
on function.

**(c) "Slice contamination is inflating the headline."**
The opposite. Excluding the 248 suspect-only rows **widens** the gap
+0.3301 → +0.3662 (**shift +0.0361**). *Why it was wrong:* the intuition is that
false lexicon hits pad the `lexicon_hit` slice with easy rows and flatter its
recall. In fact the excluded rows are **175 `NOT` / 73 `OFF`** — overwhelmingly
non-offensive — so they diluted the hit slice *toward* the free slice.
**What replaced it:** a measured sensitivity showing the reported figure is
**conservative**. Phase 08 later found a *second*, opposite contamination
(`MIN_ROOT_LEN`, bound +0.3529) — and **both push the headline in the same
conservative direction**.

**(d) "Confidence-based deferral will preferentially catch `lexicon_free`
errors."** This was the hoped-for bridge from the phase 02 diagnosis to a working
mechanism. It does not exist. Deferral is **error-selective but slice-blind**:
9.4% vs 9.6% at high-automation, and at high-precision the ordering **reverses**
(23.1% `lexicon_hit` vs 18.6% `lexicon_free`). The queue is 86.8% `lexicon_free`
because dev is 87.1% `lexicon_free` — proportion, not selection. Replicated
exactly on the test set (9.8% vs 10.0%). *Why it was wrong:* the queue's
composition looked like selection. **What replaced it:** a reported null. The
review layer works — 3.78× capture lift on dev, 3.59× on test — it simply does
not work *through* the weakness the diagnosis identified.

### 6.2 The central claim was narrowed — Stage 1

**Was:** *"the model detects offensive **vocabulary** rather than offensive
**acts**"*, recorded as the phase 02 central claim and carried into report §4.3
in that form.

**Now:** the model **ranks** profanity-free offensive content above
profanity-free benign content nearly as well as it ranks the profanity-carrying
slice — **AUC 0.8962 against 0.9306** — but **scores it below the threshold**:
gold-`OFF` median **0.5861** against **0.9650**, with **43.7%** at or below 0.5
against **10.7%**.

*Why the original was wrong:* it was inferred entirely from behaviour at a fixed
0.5 threshold, and a recall difference at a fixed threshold cannot distinguish
"ranks worse" from "scores lower". Every phase up to 08 used recall, which is
base-rate-free but **threshold-dependent** — a distinction the phase-01
constraint (OFF-recall only) was necessary for but not sufficient against.

*What is left standing:* the diagnosis is **relocated, not withdrawn** — from
discrimination to **decision**. The lexical shortcut still governs what the model
*decides*, and the operational failure is unchanged: at the deployed threshold
nearly half of profanity-free offensive content goes unflagged.

*What is still not known:* whether the downward shift is **correct calibration to
a 13.6% base rate** or **genuine under-confidence**. The verdict was
`INTERMEDIATE`, and the interval spans all three pre-registered bands. This is a
resolution limit of 355/259 and 565/3,585, known before the run, and it closes
only with a larger evaluation set.

### 6.3 The intervention's mechanism — Stage 1b

**Was:** the phase 03 / phase 05 gain (+0.0336 dev, +0.0358 test, both CIs
excluding zero) was real and replicated, and its mechanism was declined rather
than named — report §5.4 stated that the measurement could not separate literal
memorisation from a shallower distributional cue.

**Now:** the mechanism is **threshold crossing, not improved ordering**.
ΔAUC on `lexicon_free` = **−0.0056 [−0.0134, +0.0024]**, verdict `FLAT`. The
entire dev effect is **19 gold-`OFF` rows** changing sides of a fixed line
(+52/−33), reproducing the recorded recall delta exactly.

**An ordering improvement large enough to explain the gain is *excluded*, not
merely unproven** — the interval's upper end is +0.0024 against a floor of 0.01
fixed in advance.

*What did not change:* the gain is not withdrawn or weakened. It is real,
replicated, and still the pre-registered target metric. What is withdrawn is what
it **demonstrates**: no sentence implying the model learned to detect offense
without profanity is supported.

*A second thing was learned by the control failing:* it is not a uniform
recalibration either. `lexicon_hit` ordering **worsened** (−0.0254 [−0.0429,
−0.0086]). And the within-gap trade that phase 03 named as a failure mode at
design time **occurred** — the AUC gap narrows +0.0345 → +0.0146 driven by
`lexicon_hit` falling, now visible on a metric that does not depend on threshold
placement, where the recall version of the same narrowing could have been argued
away.

### 6.4 A figure was withdrawn as evidence — the C9-8 spec defect

**Was:** Stage 1's matched operating points were specified as *"two different ways
of removing the threshold confound"*, and the first draft of the Stage 1 findings
read the two directions as pointing opposite ways and treated **that** as a
result. The headline figure was `lexicon_free` recall **0.9681** at
`lexicon_hit`'s flagging rate, read as "the ranking was there all along".

**Now:** the specification was defective. Those comparisons remove the
**threshold** confound and leave the **base-rate** confound fully intact —
precision depends on the base rate directly, and recall at a fixed flagging rate
does too, because which rows sit in the top *q* of a slice depends on that
slice's mixture. Between slices at 57.8% and 13.6% — the exact variable the stage
exists to control for — neither can be evidence about ranking quality.

**All four figures are withdrawn as evidence and appear nowhere in the report.**
The 0.9681 was bought at precision **0.2224**, flagging 59% of a slice that is
13.6% offensive. C9-8 itself was **left exactly as committed**, with a dated
addendum stating the defect — the same discipline the results log uses.

This is recorded as a **specification defect, not a finding**. ROC-AUC is the only
genuinely base-rate-free comparison in the stage, which is why C9-3 made it
primary; that part of the design survived intact, and its invariance is
demonstrated in `tests/test_stage1_auc.py` rather than asserted.

### 6.5 The framing of the problem moved

**Was:** *teach the model* — the phase 03 defense was built on the premise that
the model's weakness was in what it could recognise, so the fix was to break the
token↔label correlation during training and force it to read structure.

**Now:** the ranking was never the broken part. **AUC 0.8962** says the ordering
in `lexicon_free` is nearly as good as in `lexicon_hit`; **ΔAUC `FLAT`** says the
one intervention that produced a real gain did so without improving that ordering
at all. What fails is where the scores land relative to a fixed decision
threshold — a property of the **decision mechanism**, not of what the model can
distinguish.

**This is a change in how the problem is understood, not a proposal.** No
intervention follows from it and none is proposed here: C8-11, C9-11 and C9-17
each forbid turning any of these measurements into a feature, and no threshold
derived in phase 09 is an operating point. The reframing is recorded because it
is the single largest shift in the project's understanding of its own subject,
and because it is the thing a reader would otherwise have to infer from a
scattered set of results.

---

## 7. What is still open

- **Threshold placement versus genuine under-confidence** — not separable at this
  evaluation-set size. Needs more data, not more computation.
- **47 of the 118 no-profanity false positives (39.8%)** carry no strongly skewed
  token at any vocabulary tested, and remain unexplained.
- **Whether the model *uses* the deixis signal.** Co-occurrence shows it was
  **available** in the training data, not that it was used; attribution or
  ablation would be required and **neither was run**.
- **Component attribution** for the intervention: only the combined `+1a+1b+D`
  run was compared, so 1a, 1b and D cannot be separated.
- **The mechanism behind the +0.0358 test gain** — Stage 1b is dev-only.
- **Class imbalance's contribution** to the absolute level of `lexicon_free`
  recall: no class-weighted variant was ever trained, so it is unmeasured.
- **Seed and checkpoint variance**: one seed, one configuration; the reported CIs
  cover evaluation sampling, not training randomness.
- **Cross-corpus generalisation**: Mayda and Beyhan were never acquired. The study
  carries a **same-corpus** claim only.
- **A second architecture**: ConvBERTurk was never run, and since the test set is
  spent it can no longer receive an independent number.
- **Report section 3** (related work) is deliberately empty pending verification
  from primary sources.
- **Phase 09 stages 2–6** are unopened; 5 and 6 require training and separate
  authorisation.

---

## 8. The practices that produced this record

Listed because several of the findings above exist *only* because of them.

- **Pre-registration with a commit SHA**, and an interpretation rule fixed in both
  directions before any number exists. The `INTERMEDIATE` verdict in Stage 1 and
  the `FLAT` verdict in Stage 1b are both outcomes that a rule written afterwards
  would have been tempted to phrase differently.
- **An append-only log.** Every superseded reading in §6 is still readable in
  `docs/RESULTS_LOG.md` in its original wording.
- **Predictions recorded before the numbers.** C4-3 held; **C9-16 failed**, and
  its failure is the informative half of Stage 1b.
- **Provenance by content, then by hash.** Stage 1 required its input dump to
  reproduce eight recorded phase-01 figures before computing anything new; the
  Drive mirror was later hashed and found **byte-identical**
  (`a2f5bddf…538a6346`, 736,591 bytes), which also revealed that `run_raw` and
  the phase-01 baseline are **one file**.
- **Reading the data before training on it.** The phase 03 review gate caught
  three defects that no aggregate metric would have shown.
- **Four separate runs instead of one.** The no-profanity FP rise (185 → 215) was
  correctly attributed to 1b and D; a combined run would have blamed 1a, which
  alone *lowered* it to 156.
- **Controls that can fail.** Phase 08's strong-`NOT` control and Stage 1b's
  `lexicon_hit` control were both capable of refuting the headline; one held and
  one did not.
- **Single-use accounting for the test set**, with the open log written *before*
  the read — which is why a crashed attempt that produced nothing is still on the
  record.
