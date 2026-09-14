"""Measure m5_sarcasm alone: python -m modules.m5_sarcasm.eval"""
from __future__ import annotations

from eval.harness import main_for

if __name__ == "__main__":
    raise SystemExit(main_for("m5_sarcasm"))
