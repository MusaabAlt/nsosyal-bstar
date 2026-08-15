# Phase 02 — Failure analysis (read-only)

Source: `results/01_baseline_berturk/dev_predictions.csv` (BERTurk `best.pt` = epoch 1,
commit `837c351`, dev fingerprint `034415af3a23b388…`, 4,764 rows, 285 FN / 213 FP).
No defense is proposed here and no technique is named — this document reports what the
failures are. Design happens in a later step, from these findings.

**All tagging below is my reading of Turkish text, not ground truth.** It is a model
judging labels. The ambiguous bucket is deliberately large; those rows need the team's
judgment, not mine.

---

## Finding 1 — The 30–35% noise estimate was inflated by confidence-sorting bias

Day 1 estimated ~30–35% annotation noise in the lexicon-free slice. That figure came
from reading the *most confidently wrong* examples. **Sorting by model confidence
selects for label noise**: the model is confident a row is NOT offensive precisely when
the text really isn't offensive, so mislabeled rows concentrate at the top of that
ordering. Reading the head and generalising to the slice overstates the rate.

Measured both ways, on the same 247 lexicon-free false negatives:

| Tag | top-60 by confidence | random 40 of 247 (seed 42) |
|---|---|---|
| Plausibly **mislabeled** | 14 (23%) | **4 (10%)** |
| Genuine **implicit offense**, no profanity | 18 (30%) | 14 (35%) |
| **Surface evasion** (obfuscated/abbreviated profanity) | 6 (10%) | 1 (2.5%) |
| Ambiguous — needs a human ruling | 22 (37%) | 21 (52.5%) |

**The defensible figure is ~10%, not 30–35%.** The correction is itself a result: the
earlier number was a methodological artifact, and the 33pp recall gap is far less
noise-contaminated than the Day 1 caveat implied. The gap remains an upper bound, but a
tighter one.

Note the ambiguous bucket is *larger* than the mislabel bucket in the unbiased sample
(52.5%), and roughly a third of the random sample is criticism of politicians or
institutions whose offensiveness is an annotation-convention question. **Those rows are
left tagged ambiguous by instruction — the team writes that convention before it is
applied.**

### What the genuine implicit failures look like

Second-person insult by metaphor, sarcasm, mockery of a named target, conditional
threats, sexual solicitation, and group-directed hate — none carrying a lexicon token:

- `Bence ara sıra aynaya bak.:))` — "look in the mirror occasionally" (p_OFF 0.0342)
- `ha duvarla konuşmuşum ha seninle` — "talking to you is like talking to a wall" (0.0262)
- `Sana 2 yüzlü desem 3ün hatrı kalır` — two-faced insult by wordplay (0.0704)
- `cesaretin varsa dm ye gel adresini numaranı ver geleyim hemen` — threat (0.0344)
- `Biri var kafasını klozete sokup … tuvalet paspasını yüzüne değdirmek istiyorum` (0.1980)
- `Kürdistan üç çetenin … üçünün de imha edilmesi` — call for annihilation (0.3002)
- `Türk'ler düşünmek için, Arap'lar kaşınmak için namaz kılıyormuş` — ethnic mockery (0.3834)
- `Profil fotona yarı çıplak foto koymamız için libidomuzun yüzde kaç olması lazım??` (0.3442)

Surface evasion still leaks past both the lexicon and the model: `Soxum`, `ananskm`,
`slk`, `mk`, `hastır`, and English `what the fuck`.

---

## Finding 2 — The false-positive side is a use–mention failure, and it is large

This is the half the recall gap does not describe, and it may be the stronger claim: the
model keys on **the presence of a token**, not on who it targets or whether it is being
used, quoted, negated, or discussed.

All 213 false positives were classified by hand.

**95 of 213 (45%) contain a profanity or slur token** (any form, including forms outside
the frozen lexicon). The other 118 (55%) contain none — the model fired on topic,
register, or subword artifacts.

Function of the token in those 95:

| Function | n | % of the 95 | Example |
|---|---:|---:|---|
| **Non-directed** (generic or absent third party) | 26 | 27% | `İzleyiciyi salak yerine koymaya devam etsinler` |
| **Filler / intensifier / exclamation** | 19 | 20% | `yeter amk uyku düzenim düzene girsin artık` |
| **Sense collision** (homograph, kinship term, religious formula, false lexicon hit) | 16 | 17% | `AYIPLI MALININ` (defective *goods*); `yumrugu siktim` (*punched*) |
| **Directed insult — gold label looks wrong** | 11 | 12% | `Zaten başakşehir şerefsizi yine yenmiş` |
| **Meta-discussion** (the word is mentioned, not used) | 9 | 9% | `Bir insana şerefsiz demek için 2 değil 40 defa düşünün` |
| **Negated** | 6 | 6% | `Fark adamlıkta yüreklikte şerefsizlikte değil` |
| **Quoted** (someone else's slur, reported) | 5 | 5% | `senin it köpek dediğin insanlar bizim müşterilerimiz` |
| **Self-directed** | 3 | 3% | `nasıl yıkık bir malmışım`; `namussuzum ben` |

**84 of the 95 (88%) are cases where a profanity token is present but no offensive act is
being performed toward anyone.** The classic use–mention family alone — meta-discussion,
negation, quotation — is 20 rows (21% of the profanity-bearing FPs, 9% of all FPs). The
single clearest instance is a row *advising people not to use the slur* being classified
as offensive at p_OFF 0.8469.

### The 47 `lexicon_hit` false positives specifically

| Function | n | % of 47 |
|---|---:|---:|
| Sense collision / false lexicon hit | 13 | 28% |
| Non-directed | 7 | 15% |
| Filler / intensifier | 6 | 13% |
| No profanity at all (matcher artifact) | 6 | 13% |
| Meta-discussion | 4 | 9% |
| Directed insult — gold looks wrong | 4 | 9% |
| Negated | 3 | 6% |
| Self-directed | 2 | 4% |
| Quoted | 2 | 4% |

**43 of 47 (91%) are not a directed offensive use.** Only 4 (9%) look genuinely
mislabeled. Combined with the 18.1% vs 4.6% false-positive-rate asymmetry from phase 01,
the lexical shortcut is not a marginal effect on the FP side — it accounts for nearly the
whole of it.

---

## Finding 3 — The lexicon slice definition is contaminated by prefix matching

`hit_root` matches any token that *starts with* a lexicon entry of ≥3 characters. On the
614 `lexicon_hit` dev rows this produces large numbers of false hits:

```
130x  root 'allah' matched 'allah'   (+ allahım, allaha, allahümme, allahını…)
  8x  root 'emi'   matched 'eminim', 'emirhan', 'eminönü', 'emiliano'
  7x  root 'ana'   matched 'anadolu', 'anadilde', 'anadilini'
  4x  root 'mal'   matched 'malum', 'malatya', 'malcolm', 'malesef'
  3x  root 'göt'   matched 'götürür'      'cim' → 'cimbom'      'sie' → 'siesta'
       'cikar' → 'cikaracagim'   'yaram' → 'yaramazlık'   'gibis' → 'gibisinden'
```

`allah` alone accounts for roughly 130 of the 614 hit-slice rows (~21%). Some are genuine
Turkish curses (`allah belanı versin`); many are ordinary religious speech.

This is **frozen Day 1 behaviour and is not being changed** — changing it after seeing
results would be post-hoc tuning and would invalidate the frozen record. But it means the
two slices are not cleanly "has profanity / does not", and the 33pp gap should be reported
with that stated. Direction of the bias is not obvious and has not been measured: false
hits move non-profane rows *into* the hit slice, which if anything makes the two slices
more alike and would *understate* the gap.

---

## Finding 4 — Every failure mode above is checkpoint-stable

Phase 01 found epochs 1 and 3 tie exactly on macro-F1 with identical confusion matrices
while disagreeing on 198/4,764 dev rows, so up to 43 of the 285 FN could have been
checkpoint artifacts. They are not:

- **0 of the top-60 false negatives** are checkpoint-specific.
- **1 of the top-40 false positives** is (`mesela amy adams`, p_OFF 0.9282 — almost
  certainly `am` surfacing from wordpiece; flagged and excluded from any conclusion).
- The 43 checkpoint-specific FN sit near the decision boundary: median p_OFF **0.4017**,
  minimum 0.0821, versus median **0.1724** for the 242 stable ones.

Disagreement between the two checkpoints is a boundary phenomenon. The confidently-wrong
failures — which is all this analysis rests on — are stable across both.

---

## What is not settled

- The mislabel rate is my judgment; ±several points depending on where the political line
  is drawn. The 52.5% ambiguous bucket is the team's to rule on.
- The political / institutional-criticism band is untouched by instruction.
- The direction and size of the slice-contamination bias (Finding 3) is unmeasured.

## Files

| File | Contents |
|---|---|
| `findings.md` | this document |
| `fp_function_tags.json` | all 213 FP: row_id, function tag, checkpoint-specific flag |
| `fn_tags.json` | top-60 and random-40 FN: row_id, tag, checkpoint-specific flag |

Row **text** is deliberately not stored here — it is corpus content under the same
licensing rule that keeps `dev_predictions.csv` out of git. Join on `row_id` against
`dev_predictions.csv` on the Drive mirror to recover it.
