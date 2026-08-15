"""Turkish-aware text matching against the frozen profanity lexicon.

Fulfils briefing S3 (keyword-filter baseline), S6 (Turkish lowercasing) and
S7.1/S7.4 (frozen lexicon, self-censoring is qualitative evidence only).

Ported verbatim from the verified `day1_gate_en.py`. These functions produced
`results/day1_report.json`; changing their behaviour invalidates that frozen
record, so any change must be a deliberate, logged re-freeze -- not a cleanup.

The lexicon itself is FROZEN (S7.1): 695 entries, sha256 recorded in the Day 1
report. Do not add words to it after seeing a result. That is post-hoc tuning
and it would invalidate the lexicon-free measurement, which is the empirical
premise of the entire project.
"""

import re

# --------------------------------------------------------------------------
# Turkish casing -- the single most common silent bug in Turkish NLP
# --------------------------------------------------------------------------


def tr_lower(s):
    """Turkish-aware lowercasing: I -> ı and İ -> i, before the normal lower().

    Python's str.lower() maps I -> i, which is correct for English and wrong
    for Turkish. Every comparison against the lexicon goes through this.
    """
    return s.replace("I", "ı").replace("İ", "i").lower()


def load_lexicon(path=None):
    """Load the frozen lexicon as a sorted list of Turkish-lowercased entries.

    Lines starting with '#' are comments. Returns a list (order matters for
    reproducible root matching); callers wanting membership tests should build
    their own set().
    """
    if path is None:
        import config

        path = config.LEXICON_PATH
    with open(path, encoding="utf-8") as f:
        words = {tr_lower(w.strip()) for w in f if w.strip() and not w.startswith("#")}
    return sorted(words)


# --------------------------------------------------------------------------
# tokenisation + matching
# --------------------------------------------------------------------------

# Placeholders inserted by the corpus authors, not real tokens.
#
# KNOWN QUIRK, deliberately preserved: `tokens()` splits on \w+, which strips
# the '@', so the token produced from "@USER" is "user" and the "@user" entry
# here never fires. Verified harmless -- no lexicon entry equals or prefixes
# "user", and "user" is not in ABBREV_PROFANITY, so no Day 1 number changes.
# Left as-is because results/day1_report.json was frozen with this behaviour;
# altering it silently would break the frozen record's reproducibility. Fix it
# only as a deliberate, logged re-freeze.
SKIP = {"@user", "url"}

# Minimum root length for prefix matching. Below this, short roots match
# unrelated common words and the "lexicon-hit" count inflates.
MIN_ROOT_LEN = 3


def tokens(text):
    return [t for t in re.findall(r"\w+", tr_lower(text), flags=re.UNICODE) if t not in SKIP]


def hit_literal(text, lex_set):
    """Exact word match -- what a naive keyword filter does.

    Fails on every inflected form: aptalsın, aptallara, ... This is the
    baseline whose weakness the project measures.
    """
    return any(t in lex_set for t in tokens(text))


def hit_root(text, lex_list):
    """Root/prefix match -- catches inflected forms via Turkish agglutination.

    This is the ADOPTED definition of "the lexicon caught it". Using the
    stronger matcher makes the lexicon-free slice smaller, i.e. it argues
    against our own hypothesis -- which is why it is the honest choice.
    """
    for t in tokens(text):
        for root in lex_list:
            if len(root) >= MIN_ROOT_LEN and t.startswith(root):
                return True
    return False


# --------------------------------------------------------------------------
# slice refinement: what "lexicon-free" must NOT be allowed to smuggle in
# --------------------------------------------------------------------------

# Symbol-censored profanity ("o***"). The utterance IS profane; the lexicon
# missed it because of surface masking, not because the offense is implicit.
# Real-world obfuscation evidence (S7.4), not implicit toxicity.
CENSOR_PAT = re.compile(r"[a-zçğıiöşü]{1,3}\*{2,}", re.IGNORECASE)

# Abbreviated profanity: "aq" for "amına koyayım". Again surface-form evasion,
# not an offense expressed without profanity.
ABBREV_PROFANITY = {"aq", "mk", "amk", "oç", "sg", "sik", "siktir"}

# Political + religious markers. Used ONLY to curate demo/report examples --
# never to drop rows from a statistical evaluation, which would introduce
# selection bias into the headline numbers.
SENSITIVE_MARKERS = [
    # political
    "akp", "chp", "mhp", "hdp", "pkk", "ppkpyd", "ülkücü", "esad",
    "israil", "suriye", "reis", "parti", "seçim", "siyaset", "hain", "vatan",
    # religious
    "peygamber", "allah", "din", "dinsiz", "kafir", "namaz", "oruç", "kuran",
]


def is_censored(text):
    """Self-masked profanity, e.g. o***."""
    return bool(CENSOR_PAT.search(text))


def is_abbrev_profanity(text):
    """Abbreviated profanity, e.g. aq / mk."""
    return bool(set(tokens(text)) & ABBREV_PROFANITY)


def is_sensitive(text):
    """Political or religious content -- excluded from CURATED EXAMPLES ONLY.

    Never call this to filter an evaluation set. It exists so the demo and the
    report do not put the team in the position of adjudicating political or
    religious speech in a hand-picked showcase.
    """
    low = tr_lower(text)
    return any(m in low for m in SENSITIVE_MARKERS)
