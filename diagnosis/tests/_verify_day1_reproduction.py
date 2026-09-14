"""One-off check: does the ported src/ code reproduce the frozen Day 1 record?

Not part of the pytest suite -- it needs the real corpus, which is gitignored.
Run manually after any change to src/data_io.py or src/lexicon.py:

    python tests/_verify_day1_reproduction.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
original = json.loads((ROOT / "results" / "day1_report.json").read_text(encoding="utf-8"))
rerun = json.loads((ROOT / "results" / "day1_report_rerun.json").read_text(encoding="utf-8"))

# frozen_at is a timestamp; seed is a field the ported version added
ignore = {"frozen_at", "seed"}
diffs = {
    k: (original.get(k), rerun.get(k))
    for k in set(original) | set(rerun)
    if k not in ignore and original.get(k) != rerun.get(k)
}

if diffs:
    print("MISMATCH -- the port changed behaviour:")
    for k, (a, b) in sorted(diffs.items()):
        print(f"  {k}: frozen={a!r}  rerun={b!r}")
    sys.exit(1)

print(f"OK -- {len(set(original) - ignore)} fields reproduce the frozen Day 1 record exactly.")
