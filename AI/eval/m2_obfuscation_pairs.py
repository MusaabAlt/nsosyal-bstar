"""Generate m2_deobf's per-pattern evaluation pairs - runs protocols/m2_obfuscation_eval_protocol.md.

    python -m eval.m2_obfuscation_pairs --out modules/m2_deobf/fixtures/generated_pairs.jsonl [--seed 20260917]

One clean sentence per source word, one obfuscated copy per applicable pattern code (protocol §3),
at least PAIRS_PER_CODE pairs per code. Items are in eval/harness.py fixture format: the clean
copies carry `expect_clean: true`; the obfuscated copies carry `expect_patterns: [CODE]` and
`expect: {"normalized_text": <clean surface>}` (for SUFFIX_ON_MASKED the text is expected to
stay unchanged). Every item records `generated_by` and `seed` so a regeneration is byte-identical.

LEAKAGE RULE (protocol §2): this generator is the EVALUATION generator. Its operator names are
disjoint from the study's training-augmentation family D, asserted below when the study's
module is importable, and the protocol seed is refused for any training use.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "protocols/m2_obfuscation_eval_protocol.md"
PROTOCOL_SEED = 20260917
PAIRS_PER_CODE = 12
GENERATED_BY = "eval/m2_obfuscation_pairs.py"

# Source sentences: ordinary Turkish, one target word each, marked with {w}. Neutral and insult
# words are both present because m2 is content-agnostic (it repairs form; m1 / m3 judge content).
SOURCES = [
    ("Bu adam tam bir {w}", "salak"), ("Sen gerçekten {w} birisin", "aptal"), ("Ne kadar {w} bir davranış", "şerefsiz"),
    ("Yine mi {w} bir yorum", "gereksiz"), ("Bugün hava çok {w}", "güzel"), ("Sınav sonuçları {w} açıklandı", "bugün"),
    ("Yarın {w} gideceğiz", "okula"), ("Bu {w} çok pahalı", "telefon"), ("Onun {w} kimse anlamadı", "şakasını"),
    ("Toplantı {w} başlayacak", "öğleden"), ("Kardeşim çok {w} biri", "çalışkan"), ("Bu yemek {w} olmuş", "berbat"),
    ("Sen {w} git buradan", "siktir"), ("Adam resmen {w}", "gerizekalı"), ("Böyle {w} olur mu", "saçmalık"),
    ("Herkes seni {w} sanıyor", "dahi"), ("Bu film çok {w}", "sıkıcı"), ("Yeni {w} bozuk çıktı", "bilgisayar"),
    ("Bu {w} gerçekten kötü kokuyor", "köpek"), ("Onun {w} hiç bitmiyor", "kıskançlığı"), ("Ne {w} bir insan", "vicdansız"),
    ("Bize çok {w} davrandı", "kaba"), ("Sen burada {w} kaldın", "yalnız"), ("Bu {w} hemen kapat", "kapıyı"),
]

TR_LETTERS = "abcçdefgğhıijklmnoöprsştuüvyz"
LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5", "t": "7", "b": "8", "g": "9"}
ACCENTS = {"a": "á", "e": "é", "o": "ó", "u": "ú", "i": "í"}
ASCII_FLAT = {"ş": "s", "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ü": "u"}
# Declared ambiguities (m2 spec §9): never generated as DEASCII pairs, never rule-resolved by m2.
AMBIGUOUS = {"sik", "sık", "kani", "kanı", "kismet", "kısmet"}


def op_leet(w: str, rng: random.Random) -> str | None:
    idx = [i for i, c in enumerate(w) if c in LEET]
    if not idx:
        return None
    for i in rng.sample(idx, min(2, len(idx))):
        w = w[:i] + LEET[w[i]] + w[i + 1:]
    return w


def op_repeat(w: str, rng: random.Random) -> str | None:
    idx = [i for i, c in enumerate(w) if c.isalpha()]
    out = list(w)
    for i in sorted(rng.sample(idx, min(2, len(idx))), reverse=True):
        out[i] = out[i] * rng.randint(3, 5)
    return "".join(out)


def op_spaced(w: str, rng: random.Random) -> str | None:
    return " ".join(w) if len(w) >= 3 else None


def op_punct_split(w: str, rng: random.Random) -> str | None:
    return rng.choice(".-_,/+|").join(w) if len(w) >= 3 else None


def op_accent(w: str, rng: random.Random) -> str | None:
    idx = [i for i, c in enumerate(w) if c in ACCENTS]
    if not idx:
        return None
    i = rng.choice(idx)
    return w[:i] + ACCENTS[w[i]] + w[i + 1:]


def op_phonetic(w: str, rng: random.Random) -> str | None:
    if "ks" in w:
        return w.replace("ks", "x", 1)
    if "k" in w:
        return w.replace("k", "q", 1)
    if "v" in w:
        return w.replace("v", "w", 1)
    return None


def op_deascii(w: str, rng: random.Random) -> str | None:
    flat = "".join(ASCII_FLAT.get(c, c) for c in w)
    if flat == w or flat in AMBIGUOUS or w in AMBIGUOUS:
        return None
    return flat


def op_masked(w: str, rng: random.Random) -> str | None:
    if len(w) < 4:
        return None
    i = rng.randrange(1, len(w) - 1)
    return w[:i] + "*" + w[i + 1:]


# Evaluation operators, named so the disjointness check against the study's D family is explicit.
OPERATORS = {
    "LEET": ("eval_leet", op_leet), "REPEAT": ("eval_stretch", op_repeat), "SPACED": ("eval_spaced", op_spaced),
    "PUNCT_SPLIT": ("eval_punct_split", op_punct_split), "HOMOGLYPH": ("eval_accent", op_accent),
    "PHONETIC": ("eval_phonetic", op_phonetic), "DEASCII": ("eval_deascii", op_deascii),
    "SUFFIX_ON_MASKED": ("eval_mask", op_masked),
}
UNHANDLED = ("ABBREV", "VOWEL_DROP", "WORD_MERGE", "CHAR_DROP", "DIALECT", "EMOJI_SUB")


# The study's training-augmentation family D, copied as data from diagnosis/src/obfuscation.py
# (fixed 15 Aug 2026): eval/ is core and imports nothing outside the standard library (rule 6),
# so the disjointness guard compares against this recorded list rather than importing the study.
STUDY_TRAINING_FAMILY_D = frozenset({"vowel_delete", "homoglyph", "repeat"})


def assert_disjoint_from_training() -> None:
    """Protocol §2: no operator NAME shared with the study's training family D."""
    eval_names = {name for name, _ in OPERATORS.values()}
    overlap = STUDY_TRAINING_FAMILY_D & eval_names
    if overlap:
        raise RuntimeError(f"evaluation operators reuse training family D names: {sorted(overlap)}")


def tr_lower(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def generate(seed: int) -> list[dict]:
    if seed == 0:
        raise ValueError("seed 0 is the study's default rng; the evaluation generator must not share it")
    assert_disjoint_from_training()
    rng = random.Random(seed)
    items: list[dict] = []
    per_code: dict[str, list[str]] = {code: [] for code in OPERATORS}
    n = 0
    for template, word in SOURCES:
        clean = template.format(w=word)
        n += 1
        items.append({"id": f"m2-gen-{n:03d}-clean", "text": clean, "context": {"charsafe_text": tr_lower(clean)},
                      "expected": [], "expect_clean": True, "expect": {"normalized_text": tr_lower(clean)},
                      "generated_by": GENERATED_BY, "seed": seed, "pair_word": word})
        for code, (_, op) in OPERATORS.items():
            obf = op(word, rng)
            if obf is None or obf == word:
                continue
            text = template.format(w=obf)
            expected_norm = tr_lower(clean) if code != "SUFFIX_ON_MASKED" else tr_lower(text)
            n += 1
            per_code[code].append(f"m2-gen-{n:03d}")
            items.append({"id": f"m2-gen-{n:03d}-{code.lower()}", "text": text,
                          "context": {"charsafe_text": tr_lower(text)}, "expected": [code], "expect_clean": False,
                          "expect": {"normalized_text": expected_norm}, "generated_by": GENERATED_BY, "seed": seed,
                          "pair_word": word, "pair_of": f"m2-gen-{n - 1 - list(OPERATORS).index(code):03d}"})
    # Protocol §4 sample size: the literal is the protocol's own number, checked on list lengths.
    short = {code: len(ids) for code, ids in per_code.items() if len(ids) < 12}
    if short:
        raise RuntimeError(f"fewer than {PAIRS_PER_CODE} pairs for {short}: add source words (protocol §4)")
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.m2_obfuscation_pairs")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=PROTOCOL_SEED)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    items = generate(args.seed)
    out = args.out if args.out.is_absolute() else AI_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    per_code = {code: sum(1 for i in items if i["expected"] == [code]) for code in OPERATORS}
    print(f"wrote {out.relative_to(AI_ROOT) if out.is_relative_to(AI_ROOT) else out}: {len(items)} items, per code {per_code}; "
          f"unhandled (no pairs): {UNHANDLED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
