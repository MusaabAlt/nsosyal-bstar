"""Confidence calibration + selective prediction (risk-coverage).

STUB -- not implemented yet, for the same reason as models.py: it is written
against real dev-set logits, not in advance of them.

When implemented, this module must:
  * fit temperature scaling on the DEV split only, never on the official test
    set (briefing S7.2)
  * produce a risk-coverage curve and 2-3 DECLARED operating points, declared
    before the final test run rather than picked to flatter it
  * express the result in the operational form the report needs: "at X%
    automatic coverage, Y macro-F1 / Z% error, deferring (100-X)% to review"
"""


def fit_temperature(*args, **kwargs):
    raise NotImplementedError("src/calibration.py is a stub. See module docstring.")


def risk_coverage_curve(*args, **kwargs):
    raise NotImplementedError("src/calibration.py is a stub. See module docstring.")
