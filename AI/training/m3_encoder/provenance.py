"""What the A head's published metadata says about its evaluation reference. Standard library only,
so the trainer, the evaluator and the metadata-correction tool share ONE wording.

The A head is trained on terlik-derived pseudo-labels and judged only against a declared
evaluation reference on DEV rows. The reference's provenance kind is resolved from the command line
(evaluate.resolve_a_reference) and every published sentence about A-head quality is built from that
kind: nothing calls a reference "human" unless its kind is "human".

Deliberately does NOT: decide a threshold, judge a reference's quality, or know any file path.
"""
from __future__ import annotations

REFERENCE_KINDS = ("human", "ai-assisted-human-adjudicated")

# What each kind IS, in the words the artifact publishes.
REFERENCE_DESCRIPTIONS = {
    "human": "a fully human-labelled DEV evaluation reference",
    "ai-assisted-human-adjudicated": "an AI-assisted, human-adjudicated DEV evaluation reference "
                                     "(AI annotation, disagreements decided by a human); NOT a human oracle",
}

# Published key for the rows of the evaluation reference in label_coverage / label_sources.
REFERENCE_KEY = "a_reference"
# The key exports used before 2026-09-18 (third pass). It read as "human labels" whatever the
# reference was; it is never emitted again, and correct_metadata renames it in old artifacts.
LEGACY_REFERENCE_KEY = "a_human"

PSEUDO_LABEL_AGREEMENT_NOTE = ("agreement with terlik-derived pseudo-labels (keyword labels); "
                               "NOT accuracy, NOT a quality claim")
NO_REFERENCE_NOTE = ("no evaluation reference rows: NO A-head quality claim can be made "
                     "(docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md)")
# Earlier wordings, recognised only so that correct_metadata can replace them.
LEGACY_NO_REFERENCE_NOTE = ("no human A labels: NO A-head quality claim can be made "
                            "(docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md)")


def describe_reference(kind: str) -> str:
    if kind not in REFERENCE_DESCRIPTIONS:
        raise ValueError(f"reference kind {kind!r} is not one of {REFERENCE_KINDS}")
    return REFERENCE_DESCRIPTIONS[kind]


def a_head_supervision(kind: str | None) -> str:
    """heads.json `a_head_supervision`. `kind` is the resolved evaluation-reference kind, or None
    when the run was given no evaluation reference."""
    head = ("terlik-derived pseudo-labels (keyword; files and digests in label_sources.a); pseudo-label "
            "agreement (dev_eval.json 'a_pseudo_label_agreement') is NOT accuracy and NOT a quality claim; ")
    if kind is None:
        return head + "no evaluation reference was given, so this artifact makes NO A-head quality claim"
    return (head + f"A-head quality claims only against the declared evaluation reference (dev_eval.json 'a', "
                   f"kind '{kind}'): {describe_reference(kind)}")
