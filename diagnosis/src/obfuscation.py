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


# --------------------------------------------------------------------------
# operators -- fixed 15 Aug 2026, BEFORE any robustness number was measured
# --------------------------------------------------------------------------
#
# D = training augmentation, H = held-out evaluation. The two sets share no
# operator: D perturbs characters WITHIN a token (delete / substitute / repeat),
# H changes the token's segmentation or its diacritics (split / strip / swap).
# Testing on D would measure memorisation of known operators, not robustness.

import random
import re

_VOWELS = "aeıioöuü"
_HOMOGLYPHS = {"i": "1", "ı": "1", "o": "0", "e": "3", "a": "4", "s": "5", "g": "9"}
_DIACRITIC = {"ş": "s", "ğ": "g", "ı": "i", "ö": "o", "ü": "u", "ç": "c"}


def _op_vowel_delete(tok, rng):
    """D: sik -> sk. Vowel dropping, the commonest Turkish chat abbreviation."""
    idx = [i for i, c in enumerate(tok) if c in _VOWELS]
    if not idx:
        return tok
    i = rng.choice(idx)
    return tok[:i] + tok[i + 1:]


def _op_homoglyph(tok, rng):
    """D: aptal -> 4ptal. Digit/letter lookalike substitution."""
    idx = [i for i, c in enumerate(tok) if c in _HOMOGLYPHS]
    if not idx:
        return tok
    i = rng.choice(idx)
    return tok[:i] + _HOMOGLYPHS[tok[i]] + tok[i + 1:]


def _op_repeat(tok, rng):
    """D: aptal -> aptaal. Character doubling."""
    i = rng.randrange(len(tok))
    return tok[:i + 1] + tok[i] + tok[i + 1:]


def _op_separate(tok, rng):
    """H: aptal -> a.p.t.a.l / a p t a l. Segmentation attack."""
    sep = rng.choice([".", " ", "-", "*"])
    return sep.join(tok)


def _op_deasciify(tok, rng):
    """H: şerefsiz -> serefsiz. Diacritic stripping."""
    return "".join(_DIACRITIC.get(c, c) for c in tok)


def _op_transpose(tok, rng):
    """H: aptal -> atpal. Adjacent character swap."""
    if len(tok) < 3:
        return tok
    i = rng.randrange(len(tok) - 1)
    return tok[:i] + tok[i + 1] + tok[i] + tok[i + 2:]


OPERATORS = {
    "D": {"vowel_delete": _op_vowel_delete, "homoglyph": _op_homoglyph, "repeat": _op_repeat},
    "H": {"separate": _op_separate, "deasciify": _op_deasciify, "transpose": _op_transpose},
}


def apply_family(text, family, lex_list, rng=None, max_tokens=2):
    """Obfuscate the profanity tokens in `text` with one operator from `family`.

    Only lexicon-matched tokens are perturbed: the attack being modelled is
    evasion of a keyword filter, not random corruption of the sentence.
    """
    if family not in OPERATORS:
        raise ValueError(f"unknown attack family {family!r}; known: {sorted(OPERATORS)}")
    rng = rng or random.Random(0)
    from src import lexicon

    targets = set()
    for t in lexicon.tokens(text):
        for root in lex_list:
            if len(root) >= lexicon.MIN_ROOT_LEN and t.startswith(root):
                targets.add(t)
                break
    if not targets:
        return text, []

    ops_used = []
    remaining = max_tokens

    def repl(m):
        nonlocal remaining
        word = m.group(0)
        if remaining <= 0 or lexicon.tr_lower(word) not in targets:
            return word
        name = rng.choice(sorted(OPERATORS[family]))
        remaining -= 1
        ops_used.append(name)
        return OPERATORS[family][name](word, rng)

    return re.sub(r"\w+", repl, text, flags=re.UNICODE), ops_used
