# Error analysis - <module> - <result file + commit>

## False positives (sample N = )
| id | text (PII masked) | predicted | gold | form codes | missed guard? | root cause |
|---|---|---|---|---|---|---|
| | | | | | | |

## False negatives (sample N = )
| id | text (PII masked) | predicted | gold | form codes | root cause |
|---|---|---|---|---|---|
| | | | | | |

## Root-cause tally
| cause | count | owner module | proposed fix | new trap added? |
|---|---|---|---|---|
| substring collision | | m1_lexicon | | |
| normalization flip | | m2_deobf | | |
| identity-term shortcut | | m4_implicit | | |

## Follow-ups
- New traps for `eval/traps/traps.jsonl`: 
- Spec changes: 
