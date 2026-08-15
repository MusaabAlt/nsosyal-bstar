"""Counterfactual token augmentation -- component 1 of the phase 03 defense.

Breaks the token<->label correlation that the phase 02 diagnosis found:

    The model detects offensive VOCABULARY rather than offensive ACTS.

Two symmetric operations, applied to the TRAINING split only. Dev is never
augmented.

  1a  mask the profanity in gold-OFF rows, keep the label OFF
      -> offense must be located in structure, not vocabulary
  1b  insert profanity into gold-NOT rows in a non-offensive function, keep NOT
      -> a profanity token is not by itself an offensive act

Provenance of the 1b patterns (constraint C1, phases/03_defense_design.md)
--------------------------------------------------------------------------
Every insertion pattern below is derived from TRAINING-SPLIT out-of-fold errors
(`results/03_defense/train_oof_predictions.csv`), never from the dev-set error
families measured in phase 02. Deriving them from dev would mean the reported
false-positive reduction partly measures the template rather than the model.

Two of the patterns -- NON_PERSON_TARGET and ADVERBIAL -- appear only in the
training-derived sample and were absent from the dev-derived design, which is
the clearest evidence the constraint changed the operator set rather than only
its provenance.

Constraint C2: 1a never fabricates label noise. It applies only to rows carrying
offensive structure independent of the profanity token, and the filter is
deliberately conservative -- fewer clean augmented rows beat more noisy ones.
Sarcasm is NOT detected: there is no high-precision cue for it, so sarcastic
frames are simply not claimed as a qualifying structure.
"""

import random
import re

from src import lexicon

MASK = "[MASK]"

# --------------------------------------------------------------------------
# 1a -- structural qualification (constraint C2)
# --------------------------------------------------------------------------

# Explicit second-person pronouns/possessives. A row addressing someone can
# carry offense in the address itself, which survives masking the profanity.
SECOND_PERSON_WORDS = {
    "sen", "sana", "seni", "senin", "senle", "seninle", "sende", "senden",
    "siz", "size", "sizi", "sizin", "sizle", "sizinle", "sizde", "sizden",
}

# Second-person verb inflections: -sın/-sin/-sun/-sün, -sınız/-siniz/..., and
# the -dın/-din/-dun/-dün past. Checked as suffixes on tokens >= 5 chars so
# short accidental matches (e.g. "sin") do not qualify a row.
SECOND_PERSON_SUFFIXES = (
    "sınız", "siniz", "sunuz", "sünüz",
    "sın", "sin", "sun", "sün",
    "dın", "din", "dun", "dün",
    "tın", "tin", "tun", "tün",
)

MIN_RESIDUAL_TOKENS = 8      # content left after masking, so the row still says something
MAX_PROFANITY_SHARE = 0.20   # above this the profanity IS the utterance -> skip

# Roots demonstrated in phase 02 to produce prefix FALSE matches. Masking these
# corrupts ordinary words -- the first review pass masked `malsef` (a typo for
# maalesef), `Allah'ın` in a religious phrase, and `MALLARI` -- which injects
# noise instead of removing a lexical cue. A row must be carried by at least one
# NON-suspect profanity token, and only non-suspect tokens are ever masked.
SUSPECT_ROOTS = {"allah", "ana", "emi", "mal", "cim", "sie", "göt", "gibis",
                 "yaram", "cikar", "oğlan", "meme"}

# Nominal insult constructions where the profanity IS the utterance: masking the
# head leaves the frame behind and the residual is no longer offensive.
# Caught in review: `Orospu çocukları` -> `[MASK] çocukları`.
INSULT_HEADS = {"çocuğu", "çocukları", "çocugu", "cocugu", "evladı", "avradını",
                "avradini", "sülalesi", "sulalesi"}

# Discourse fillers. Phase 02 measured 19 false positives where exactly these
# carry no offensive act at all. If a filler is the ONLY profanity in a gold-OFF
# row, masking it leaves a residual whose offensiveness cannot be vouched for --
# review caught `kalp dayanmaz [MASK] şu çocuğun arabasına bi bakın`, which is
# not offensive and would have entered training labelled OFF.
FILLER_TOKENS = {"amk", "aq", "mk", "amq", "awk", "lan", "ulan", "amcık", "amina"}


def _profane_tokens(text, lex_list, exclude_suspect=True):
    """Tokens matched by the FROZEN root matcher -- the same rule that defined
    the slices, imported rather than reimplemented.

    Returns (token, root) pairs. With exclude_suspect, tokens whose ONLY match is
    a demonstrated false-match root are not treated as profanity.
    """
    hits = []
    for t in lexicon.tokens(text):
        matched = [root for root in lex_list
                   if len(root) >= lexicon.MIN_ROOT_LEN and t.startswith(root)]
        if not matched:
            continue
        if exclude_suspect and all(r in SUSPECT_ROOTS for r in matched):
            continue
        hits.append((t, matched[0]))
    return hits


def has_second_person(text, profane):
    """Second-person address carried by a token that is NOT the profanity."""
    for t in lexicon.tokens(text):
        if t in profane:
            continue
        if t in SECOND_PERSON_WORDS:
            return True
        if len(t) >= 5 and t.endswith(SECOND_PERSON_SUFFIXES):
            return True
    return False


def qualifies_for_masking(text, lex_list):
    """Return (ok, reason). Conservative by design: anything uncertain is skipped.

    Qualifying structure = second-person address surviving the mask, plus enough
    residual content that the row still asserts something. Rows where the
    profanity carries most of the utterance are skipped -- masking those would
    leave a non-offensive string labelled OFF, which is exactly the label noise
    constraint C2 forbids.
    """
    toks = lexicon.tokens(text)
    pairs = _profane_tokens(text, lex_list)
    profane = {t for t, _ in pairs}
    if not profane:
        return False, "no_profanity_token"          # incl. suspect-root-only rows
    if len(profane) > 1:
        # Repetition means the profanity is carrying the utterance, not decorating
        # it. Caught in review: a sexual-solicitation ad with three masked tokens.
        return False, "multiple_profanity_tokens"
    if profane <= FILLER_TOKENS:
        return False, "profanity_is_only_a_filler"
    if not has_second_person(text, profane):
        return False, "no_second_person_address"
    for i, t in enumerate(toks[:-1]):
        if t in profane and toks[i + 1] in INSULT_HEADS:
            return False, "profanity_is_the_insult_head"
    residual = [t for t in toks if t not in profane]
    if len(residual) < MIN_RESIDUAL_TOKENS:
        return False, "too_little_residual_content"
    if len(profane) / max(1, len(toks)) > MAX_PROFANITY_SHARE:
        return False, "profanity_is_the_utterance"
    return True, "ok"


def mask_profanity(text, lex_list):
    """Replace every matched profanity token with [MASK], preserving position.

    Masked rather than deleted: deletion changes length and can leave a dangling
    fragment, and the model should learn that *something* was there whose
    identity does not settle the label.
    """
    profane = {t for t, _ in _profane_tokens(text, lex_list)}
    if not profane:
        return text

    def repl(m):
        return MASK if lexicon.tr_lower(m.group(0)) in profane else m.group(0)

    return re.sub(r"\w+", repl, text, flags=re.UNICODE)


# --------------------------------------------------------------------------
# 1b -- insertion patterns, ALL derived from training-split errors
# --------------------------------------------------------------------------

# Small inventory drawn from the frozen lexicon; these are the tokens that
# actually appear in the training-split false positives.
FILLERS = ["amk", "lan", "ya lan", "amk ya"]
SLURS = ["salak", "aptal", "gerizekalı", "şerefsiz", "mal"]
NON_PERSON_SUBJECTS = ["bu hava", "bu trafik", "bu internet", "bu sınav", "bu hastalık"]


def _cap(s):
    return s[0].upper() + s[1:] if s else s


# Each pattern returns a FRAGMENT; placement is handled by _splice() so the
# inserted span does not always land in final position. The first review pass
# appended everything, which would have taught "profanity at the end = NOT" --
# the positional shortcut flagged as a failure mode in the design.

def pat_filler(rng):
    """Filler / intensifier. From training FPs: `Ölecez diye gülmeyek mi amk`,
    `hastalığım geçsin ya da öleyim amk`, `dolar 6,33 ü gördü ... amk`."""
    return rng.choice(FILLERS)


def pat_adverbial(rng):
    """Manner adverb, not predication. Training-derived, absent from dev:
    `Salak salak gülmeme sebep olan insanlar`, `Aptalca sırıtarak`."""
    return rng.choice(["salak salak gülüyorum", "aptal aptal bakıyorum", "aptalca sırıttım"])


def pat_non_person_target(rng):
    """Slur aimed at a non-person. Training-derived, absent from dev:
    `sinüzit kadar şerefsiz bişey yok`."""
    return (f"{rng.choice(NON_PERSON_SUBJECTS)} kadar "
            f"{rng.choice(['şerefsiz', 'salak', 'aptal'])} bir şey yok")


def pat_negated(rng):
    """Explicit negation. From training FPs: `secmeni gerizekalı değil`."""
    return rng.choice([f"kimse {rng.choice(SLURS)} değil",
                       f"burada {rng.choice(SLURS)} olan yok"])


def pat_quoted(rng):
    """Someone else's slur, reported. From training FPs: quoted nicknames
    (`"Mert ama şerefsiz" gibi nicklerinize`) and reported speech."""
    slur = rng.choice(SLURS)
    return rng.choice([f'bana "{slur}" dedi', f'"{slur}" diyenler olmuş',
                       f'birisi "{slur}" yazmış'])


def pat_meta(rng):
    """The word mentioned, not used. From training FPs: `Hepsi çıkıp ana avrat
    küfür edecek`, and the ironic `Şerefsizlik yapın arkadaşlar`."""
    slur = rng.choice(SLURS)
    return rng.choice([f'insanlara "{slur}" demek doğru değil',
                       f'"{slur}" kelimesini kullanmaya gerek yok',
                       f'kimseye "{slur}" denmemeli'])


def pat_self(rng):
    """Self-directed. From training FPs: `beni bi salak olarak görüyorlardır`."""
    slur = rng.choice(SLURS)
    return rng.choice([f"ben ne {slur}ım", f"kendimi {slur} gibi hissettim"])


# Long rows are excluded as 1b sources: at max_len=128 an appended fragment can
# be truncated away, leaving a plain duplicate NOT row that teaches nothing.
MAX_SOURCE_WORDS = 40


def _splice(text, fragment, rng):
    """Place the fragment at the start, at the end, or after an internal CLAUSE
    boundary -- so position carries no signal.

    Insertion points are restricted to clause boundaries. The first review pass
    spliced at arbitrary word boundaries and produced ungrammatical rows
    (`Neden gelecek kişilere mâni burada salak olan yok oldunuz?`), which would
    have taught the model that broken syntax plus profanity means NOT.
    """
    words = text.split()
    # a boundary is a word ending in sentence/clause punctuation, not at the very end
    boundaries = [i + 1 for i, w in enumerate(words[:-1]) if w.endswith((".", "!", "?", ",", ";", ":"))]
    options = ["start", "end"] + (["inside"] if boundaries else [])
    where = rng.choice(options)
    if where == "start":
        return f"{_cap(fragment)} {text}".strip()
    if where == "end":
        return f"{text.rstrip()} {fragment}"
    i = rng.choice(boundaries)
    return " ".join(words[:i] + [_cap(fragment)] + words[i:])


INSERTION_PATTERNS = [
    ("FILLER", pat_filler),
    ("ADVERBIAL", pat_adverbial),
    ("NON_PERSON_TARGET", pat_non_person_target),
    ("NEGATED", pat_negated),
    ("QUOTED", pat_quoted),
    ("META", pat_meta),
    ("SELF", pat_self),
]

# Deliberately NOT implemented: inserting a fresh directed insult at a person.
# In the training errors the non-directed family is aimed at generic groups, and
# synthesising that reliably without tipping the row into genuinely offensive
# territory is not something this filter can guarantee -- it would be the
# mirror image of the 1a label-noise problem that constraint C2 forbids.


def build_1a(off_rows, lex_list):
    """Masked-profanity OFF rows. Returns (augmented, stats)."""
    out, reasons = [], {}
    for r in off_rows:
        ok, why = qualifies_for_masking(r["text"], lex_list)
        reasons[why] = reasons.get(why, 0) + 1
        if not ok:
            continue
        masked = mask_profanity(r["text"], lex_list)
        if masked == r["text"]:
            reasons["mask_was_a_noop"] = reasons.get("mask_was_a_noop", 0) + 1
            continue
        out.append({"id": f"{r['id']}_1a", "text": masked, "label": "OFF",
                    "source_id": r["id"], "op": "1a_mask"})
    return out, reasons


def build_1b(not_rows, n, seed=42):
    """Profanity inserted into NOT rows in a non-offensive function.

    Sources are restricted to rows short enough that the inserted span survives
    max_len truncation, and placement is randomised by _splice().
    """
    rng = random.Random(seed)
    pool = [r for r in not_rows if len(r["text"].split()) <= MAX_SOURCE_WORDS]
    rng.shuffle(pool)
    out = []
    for i, r in enumerate(pool[:n]):
        name, fn = INSERTION_PATTERNS[i % len(INSERTION_PATTERNS)]
        out.append({"id": f"{r['id']}_1b", "text": _splice(r["text"], fn(rng), rng),
                    "label": "NOT", "source_id": r["id"], "op": f"1b_{name}"})
    return out, len(pool)
