# Annotation guideline - <dataset / batch id>

## Labels per item
- **Axis 1 content** - exactly ONE of A1-A4, B1-B5, C1-C5, D1, CLEAN.
  If several apply, take the most severe per `ACTION_PRECEDENCE` and note the others.
- **Axis 2 form** - ZERO or more FormCodes. Obfuscation never changes the content label.
- **Axis 3 target** - individual / group / non_human / none.
- **Axis 4 level** - post, or thread when the offence exists only through repetition.
- **Guards** - zero or more GuardCodes that explain why a surface-offensive item is CLEAN.

## Decision order for the annotator
1. Read the post de-obfuscated in your head; label content on meaning.
2. Record the obfuscation patterns you had to undo (Axis 2).
3. Resolve the target.
4. If it looks offensive but is CLEAN, name the guard.

## Hard cases (fill with examples from the batch)
| case | label | why |
|---|---|---|
| quoted slur in counter-speech | CLEAN + QUOTE_COUNTERSPEECH | |
| insult at a film / the weather | CLEAN + NON_HUMAN_TARGET | |
| SIKINTI / amca / sikke | CLEAN + SUBSTRING_COLLISION | |

## Agreement
- Double-annotated share: 
- Metric (Krippendorff's alpha per axis): 
- Adjudication rule: 

## Privacy
- Doxing items: mask identifiers in the stored text; keep the unmasked form out of the repo.
