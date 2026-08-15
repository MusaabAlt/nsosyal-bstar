"""Offline demo: every system side by side, with the triage decision.

STUB -- not implemented yet. It depends on artifacts that do not exist:
trained checkpoints and a calibrated confidence threshold.

Competition constraint: this must run fully offline. No NSosyal API, no live
platform dependency, no network call at inference time.

When implemented, the screen must show, for one input text:
  * keyword filter verdict, BERTurk verdict, ConvBERTurk verdict, defense verdict
  * the defense's calibrated confidence
  * the resulting action -- AUTO-RESOLVE or SEND TO HUMAN REVIEW -- at a
    declared operating point from src/calibration.py, framed as a reviewer
    tool rather than a judgement about any individual account
"""

if __name__ == "__main__":
    raise NotImplementedError(
        "demo/app.py is a stub. It is written after the defense and the "
        "calibrated operating points exist -- see docs/phase_briefing.md S9.8."
    )
