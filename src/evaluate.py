"""Unified metric computation across every system in the comparison matrix.

STUB -- not implemented yet.

This module exists so that the keyword filter, BERTurk, ConvBERTurk and the
defense are all scored by literally the same code path. Briefing S8 compares
them cell by cell; a metric computed slightly differently per system would
make that table meaningless.

When implemented, this module must:
  * report macro-F1 AND OFF-recall with bootstrap confidence intervals
  * evaluate the lexicon-hit and lexicon-free slices separately, using
    src.lexicon.hit_root as the slice definition (the same matcher Day 1 froze)
  * take predictions as input rather than models, so it cannot accidentally
    trigger a test-set load
"""


def score(*args, **kwargs):
    raise NotImplementedError("src/evaluate.py is a stub. See module docstring.")


def bootstrap_ci(*args, **kwargs):
    raise NotImplementedError("src/evaluate.py is a stub. See module docstring.")
