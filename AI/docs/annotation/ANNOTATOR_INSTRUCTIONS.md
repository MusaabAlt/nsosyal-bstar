# Annotator instructions — "profanity present" (A-head dev pilot)

This page is a **short summary** of the sealed guideline. It adds no rule and changes no rule.

> **The guideline is authoritative.** If anything here seems to differ from
> `AI/docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md` (**v1.1**, sha256
> `72e61d196eb6f5c33a27b58528d524c6d50cbc4bb2761a2e90e84de66915a0dd`), the guideline wins.
> Read it once in full before you start.

## Your task

You have one file containing **500 Turkish posts**. For each post answer **one** question:

> Does the post, as written, contain at least one **profane expression** — a swear word, an
> obscene sexual or scatological term, or a vulgar insult built on such a root — that is
> **used by the author** (not merely mentioned), on **any** target or on none?

- write `1` for yes, profanity present
- write `0` for no

**The root itself must be obscene or profane.** Being insulting is not enough, and neither is
appearing on a profanity word list. An ordinary or mild insult with no obscene or profane root —
`aptal`, `salak`, `eşek herif` — is `0`, unless the same post also contains a genuine profane
root. The judgement is about the **word**, not about how offensive the post is overall.

## How to decide (in this order)

1. **Read the post de-obfuscated in your head.** `g0t`, `s.i.k.t.i.r`, `siktiiiir`, missing
   Turkish letters, and abbreviations such as `amk`, `aq`, `oç` count as the word they stand for.
2. **Find the candidate word(s)** whose root is a profane root.
3. **Apply the exclusions below** to each candidate. If every candidate is excluded, answer `0`.
   If at least one survives, answer `1`.
4. **Ignore the target and the overall tone.** Profanity aimed at a film, the weather, a club, a
   group, a person, or nobody is still `1`. A hateful post with no profane word is `0`.
5. **Still unsure?** Write your best answer, set `uncertain` to `true`, and say in `notes` which
   rule you could not apply.

## What does NOT count — answer `0`

| the only candidate is… | example |
|---|---|
| offensiveness with no profane word | `Onlardan başka ne beklenir` |
| a threat, degrading remark, exclusion or sexual aggression **without** a profane root | `Seni bulurum`, `Çirkinsin` |
| an **ordinary or mild insult** — derogatory, but with **no obscene or profane root** | `aptal`, `salak`, `eşek herif` |
| a stereotype, dehumanisation, coded or veiled expression, incitement or defamation whose harm is **implied**, with no profane word | a harmful claim you have to reconstruct because it is not written out |
| swearing built on a **sacred concept** (`Allah`, `kitap`, `din` …) — write `notes: "A4 candidate"` | `Allah belanı versin` |
| profanity that is **quoted or reported**, not used by the author | `Adam bana "siktir git" demiş, ayıp` |
| a profane root **inside an innocent word** | `sıkıntı`, `amca`, `ambulans`, `psikoloji`, `götürmek`, `kerpiç` |
| a **homonym** whose innocent reading is the natural one | `10 am`, `am/pm`, a proper name |
| an animal word used in its ordinary sense | `Eşek gibi çalıştım` |

A word with both an innocent sense and an obscene sense (for example a body-part word) counts
only when its **obscene** sense is the one used.

## What DOES count — answer `1`

- Profanity aimed at a **non-human target**: `Bu film tam bir bok` is `1`. Target never changes the
  answer.
- **Self-directed or joking** profanity: `amına koyim ya, unutmuşum` is `1`.
- An insult **plus** a genuine profane root: `Salak herif, siktir git` is `1`. The insult alone
  would be `0`; the profane root `siktir` decides.

The guideline has further worked examples in §9 — read them there. When the rules do not settle a
case for you, write your best answer, mark it `uncertain`, and say in `notes` which rule you could
not apply. Do not invent a rule.

## Filling in the file

Each line of your file looks like this. Edit **only** the last three fields:

```json
{"row_id": "…", "text": "…", "label": null, "uncertain": false, "notes": ""}
```

| field | what to write |
|---|---|
| `row_id` | do not edit |
| `text` | do not edit |
| `label` | the number `0` or the number `1`. Not `"1"`, not `true`/`false`. Never leave it `null` in a file you hand in |
| `uncertain` | `true` only when step 5 applied, otherwise leave `false` |
| `notes` | short free text: the candidate word, the exclusion you used, `"A4 candidate"`, `"quoted"` … |

When you are done, check your file. The command stops and names any row that is still empty or
malformed:

```bash
python -m eval.a_head_dev_sample check eval/annotation/private/a_head_dev_sample_seed42_n500.<you>.jsonl --ids eval/annotation/a_head_dev_sample_seed42_n500.ids.json
```

## Work independently

- **Judge the text alone.** Your answer must come from reading the post and applying the rules.
- **Do not look up any model or lexicon output.** Do not open anything that could tell you how the
  system scored a post: model predictions or scores, terlik / lexicon matches, pseudo-labels,
  training-run outputs or evaluation results. In this project that includes `AI/eval/derived/`,
  `AI/eval/results/`, `diagnosis/results/` and the training runs on Drive. Knowing what the
  system said would make your label useless as an independent check of it.
- **Do not discuss rows or compare files** with the other annotator before both files are handed in.
- **Do not add or remove rows.** The check command refuses a file whose rows differ from the sample.

## What happens after

Both files are compared automatically. Rows where you and the other annotator agree are settled.
Rows where you disagree go to an **adjudicator**, who decides each one by applying the guideline —
never a personal preference. A disagreement the guideline cannot settle is recorded and the rule is
queued for the next guideline version. You will not be asked to change your own labels.

## Privacy

Your file contains real posts. Keep it private: do not share it, upload it publicly, paste rows
elsewhere, or commit it. It stays in `eval/annotation/private/`, which git ignores.
