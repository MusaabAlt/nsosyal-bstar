# eval/testsuite

End-to-end gold set for the WHOLE pipeline (all axes), as opposed to the
per-module `modules/<name>/fixtures/dev.jsonl`.

- `dev.jsonl` - used for threshold derivation and error analysis.
- `test.jsonl` - held out. Not in the repository; loaded from a path given at
  evaluation time and only for final reports. Never used to tune anything.

Item format (one JSON object per line):

```json
{"id": "ts-000001", "text": "...", "content": "CLEAN", "form": [], "target": "none",
 "level": "post", "guards": [], "split": "dev", "source": "...", "annotators": 2}
```

`content` is the single Axis 1 gold label; `form` and `guards` are lists.
`dev.jsonl` below holds format examples only, not real data.
