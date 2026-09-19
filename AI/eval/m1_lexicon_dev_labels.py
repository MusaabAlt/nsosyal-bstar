"""m1 lexicon labels on the frozen dev split - the entry point named by
protocols/m1_lexicon_dev_labels_protocol.md §7. Since the 2026-09-18 amendment it runs the
shared generator (eval/m1_lexicon_labels.py) with --split dev; nothing else lives here.

    python -m eval.m1_lexicon_dev_labels --out eval/derived/m1_lexicon_dev_seed42.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eval.m1_lexicon_labels import Spec, generate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--spot-check", type=int, default=20, help="hits printed for review")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return generate(Spec(split="dev"), args.out, spot_check=args.spot_check)


if __name__ == "__main__":
    sys.exit(main())
