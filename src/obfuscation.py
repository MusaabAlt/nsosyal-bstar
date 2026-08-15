"""Obfuscation attack families -- design set (D) and held-out set (H).

The attack generators themselves are STUBS (see models.py for why). What is
implemented here is the anti-circularity guard, because briefing S7.3 is the
rule that killed an earlier version of this idea and it must be enforced by
code, not by remembering:

    Obfuscation used for training augmentation MUST be disjoint from the
    obfuscation used for robustness evaluation. Testing on the operators you
    trained on measures memorisation, not robustness.

Note: this file generates functional evasion text. The repo stays private
until submission for that reason.
"""

# Family names are declared up front so the disjointness guard has something
# to check before any generator exists. D = design/training, H = held-out/eval.
DESIGN_FAMILIES = ("D",)
HELDOUT_FAMILIES = ("H",)


def assert_disjoint(train_families, eval_families):
    """Fail loudly if a robustness evaluation reuses a training attack family.

    Call this at the top of ANY script that both augments training data and
    reports an obfuscation-robustness number. It raises rather than warns:
    a warning in a notebook scrollback is not a guard.
    """
    train_set = {str(f).strip() for f in train_families}
    eval_set = {str(f).strip() for f in eval_families}
    overlap = train_set & eval_set
    if overlap:
        raise ValueError(
            f"ANTI-CIRCULARITY VIOLATION (briefing S7.3): attack families "
            f"{sorted(overlap)} appear in BOTH training augmentation and "
            f"robustness evaluation. Any number produced this way measures "
            f"memorisation of known operators, not robustness to unseen ones. "
            f"Use disjoint families: train on {sorted(DESIGN_FAMILIES)}, "
            f"evaluate on {sorted(HELDOUT_FAMILIES)}."
        )
    if not eval_set:
        raise ValueError("No evaluation attack family given -- nothing would be tested.")
    return True


def apply_family(*args, **kwargs):
    raise NotImplementedError(
        "Attack generators are stubs. The operator set for D and H is defined "
        "when the defense step is specified -- and D/H must be fixed BEFORE any "
        "robustness number is measured, not adjusted afterwards."
    )
