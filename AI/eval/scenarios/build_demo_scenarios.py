"""Build AI/eval/scenarios/demo_scenarios.jsonl - the functional / demo scenario matrix.

EVALUATION ONLY. Nothing here changes runtime behaviour. The builder READS (never writes):
  * the M1 routing tables (modules/m1_lexicon/module.py ROUTE_*, COMPOUND_ROOTS) and terlik's
    dictionary metadata (the per-root `suffixable` flag), so that every currently routed root gets
    scenarios - the taxonomy is introspected, not copied by hand;
  * the M1-PREC-1 protocol's machine-checked ACCEPT_* lines
    (protocols/m1_positive_matching_precision_protocol.md), so the Rule-v4 regression lists enter
    the matrix verbatim.
It writes only demo_scenarios.jsonl next to itself.

Expectations are written from the contracts, specs and protocols (each case cites its source in
`source_ref`), never from observed pipeline output. Vocabulary of the checks: see
run_demo_scenarios.py (module docstring).

supported_status:
  SUPPORTED        the architecture claims the behaviour -> PASS / FAIL
  LIMITATION       the architecture does not claim it (declared unhandled, accepted cost, no producer,
                   not promised) -> always KNOWN_LIMITATION; `ideal` records what a user would want and
                   the runner reports whether it happened anyway
  NOT_IMPLEMENTED  the owning module / code is a stub or not built (m5 D1, A4, B5) -> NOT_IMPLEMENTED
  M3_DEPENDENT     the claim is about M3's learned heads -> evaluated only when the exact Rule-v4
                   artifact is loaded; otherwise BLOCKED (BLOCKED_ARTIFACT_NOT_LOCAL)

Usage (from AI/, with AI/.venv):  python -m eval.scenarios.build_demo_scenarios
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

AI_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from modules.m1_lexicon.module import (COMPOUND_ROOTS, ROUTE_A, ROUTE_B1, ROUTE_B2, ROUTE_B3,  # noqa: E402
                                       ROUTE_NONE)

OUT = Path(__file__).with_name("demo_scenarios.jsonl")
PRECISION_PROTOCOL = AI_ROOT / "protocols" / "m1_positive_matching_precision_protocol.md"

REF_ROUTE = "protocols/m1_runtime_routing_protocol.md (M1-ROUTE-1 §2-§3)"
REF_ROUTE11 = "protocols/m1_runtime_routing_protocol.md amendment (a) M1-ROUTE-1.1"
REF_PREC = "protocols/m1_positive_matching_precision_protocol.md (M1-PREC-1)"
REF_ADR005 = "protocols/ADR-005-family-a-by-target.md + decision/thresholds.yaml family_a"
REF_M6 = "protocols/m6_target_guideline.md §1-§3"
REF_M2 = "modules/m2_deobf/module.py docstring + README.md"
REF_M0 = "modules/m0_charsafe/module.py docstring"
REF_GUARDS = "decision/thresholds.yaml guards + protocols/m1_runtime_routing_protocol.md §4"
REF_PIPE = "pipeline/run.py docstring (nothing a module does crashes the request; fail closed)"

# ------------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------------
_SCENARIOS: list[dict[str, Any]] = []
_IDS: set[str] = set()


def tr_upper(s: str) -> str:
    return "".join("İ" if c == "i" else "I" if c == "ı" else c.upper() for c in s)


def tr_cap(s: str) -> str:
    return tr_upper(s[:1]) + s[1:] if s else s


_BACK = set("aıouâû")
_VOWELS = set("aeıioöuüâîû")


def last_vowel(word: str) -> str:
    return next((c for c in reversed(word) if c in _VOWELS), "a")


def plural(word: str) -> str:
    return word + ("lar" if last_vowel(word) in _BACK else "ler")


def question(word: str) -> str:
    v = last_vowel(word)
    return {"a": "mısın", "ı": "mısın", "â": "mısın", "e": "misin", "i": "misin", "î": "misin",
            "o": "musun", "u": "musun", "û": "musun", "ö": "müsün", "ü": "müsün"}[v]


def slug(s: str) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")
    out = re.sub(r"[^A-Za-z0-9]+", "_", s.translate(table)).strip("_")
    return out[:40] or "x"


def add(case_id: str, category: str, subcategory: str, text: str, *, status: str = "SUPPORTED",
        expected: dict[str, Any] | None = None, signals: dict[str, Any] | None = None,
        ideal: dict[str, Any] | None = None, notes: str = "", source_ref: str = "",
        taxonomy: dict[str, str] | None = None, demo: bool = False) -> None:
    if case_id in _IDS:
        raise ValueError(f"duplicate case_id {case_id}")
    if status not in ("SUPPORTED", "LIMITATION", "NOT_IMPLEMENTED", "M3_DEPENDENT"):
        raise ValueError(status)
    if status == "LIMITATION" and not ideal:
        raise ValueError(f"{case_id}: a LIMITATION case must state its ideal behaviour")
    _IDS.add(case_id)
    _SCENARIOS.append({
        "case_id": case_id, "category": category, "subcategory": subcategory, "text": text,
        "supported_status": status, "expected": expected or {}, "expected_module_signals": signals or {},
        "ideal": ideal or {}, "notes": notes, "source_ref": source_ref,
        **({"taxonomy": taxonomy} if taxonomy else {}), **({"demo_critical": True} if demo else {}),
    })


A_FAMILY = ["A1", "A2", "A3", "A4"]
NO_A = {"rule_fired_exclude": ["A"]}
M3_NO_A = {"m3": {"a_head_fired": False}}          # M3-dependent sub-check, blocked without Rule-v4


def need(route: frozenset[str], root: str) -> None:
    if root not in route:
        raise ValueError(f"root {root!r} is not in its route any more - rebuild the case table")


# ------------------------------------------------------------------------------------------------
# terlik metadata (suffixable flag) - read as DATA, never imported: eval/ is core (stdlib + pyyaml
# only, tests/test_architecture.py); same approach as eval/m1_lexicon_labels.py::terlik_tr_dictionary
# ------------------------------------------------------------------------------------------------
def terlik_suffixable() -> dict[str, bool]:
    import importlib.util
    spec = importlib.util.find_spec("terlik")
    if spec is None or spec.origin is None:
        raise RuntimeError("terlik is not installed (use AI/.venv)")
    path = Path(spec.origin).resolve().parent / "lang" / "tr" / "dictionary.json"
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    return {e["root"]: bool(e.get("suffixable")) for e in entries}


SUFFIXABLE = terlik_suffixable()


# ------------------------------------------------------------------------------------------------
# 1. CLEAN / BENIGN
# ------------------------------------------------------------------------------------------------
CLEAN = [
    ("neutral", "Bugün hava çok güzel, parka gidelim mi?"),
    ("neutral", "Yarın saat 10'da toplantımız var."),
    ("neutral", "Annem akşam yemeğine mantı yaptı."),
    ("neutral", "Otobüs durağında yarım saat bekledim."),
    ("neutral", "Kitabı bitirdim, sonu çok etkileyiciydi."),
    ("positive", "Harika bir iş çıkardın, tebrikler!"),
    ("positive", "Seni çok seviyorum, iyi ki varsın."),
    ("positive", "Bu konser hayatımın en güzel gecesiydi."),
    ("negative_opinion", "Bu filmi hiç beğenmedim, senaryo zayıftı."),
    ("negative_opinion", "Hizmet çok yavaştı, bir daha gelmeyeceğim."),
    ("negative_opinion", "Bu karar bence yanlış ve adaletsiz."),
    ("disagreement", "Sana katılmıyorum, bence konu çok daha karmaşık."),
    ("disagreement", "Açıkçası bu fikre karşıyım ama saygı duyuyorum."),
    ("question", "Bu akşam ne yapıyorsun?"),
    ("question", "Kütüphane kaçta kapanıyor?"),
    ("question", "Sınav sonuçları ne zaman açıklanacak?"),
    ("news", "İstanbul'da yarın kuvvetli yağış bekleniyor."),
    ("news", "Merkez Bankası faiz oranını sabit tuttu."),
    ("news", "Deprem bölgesinde arama kurtarma çalışmaları sürüyor."),
    ("technical", "Sunucu 500 hatası veriyor, logları kontrol eder misin?"),
    ("technical", "Python'da bir liste nasıl ters çevrilir?"),
    ("technical", "Yeni ekran kartı 16 GB bellekle geliyor."),
    ("food", "Mercimek çorbası tarifini paylaşır mısın?"),
    ("food", "Domates, biber ve patlıcanla güzel bir yemek yaptım."),
    ("food", "Kaşarlı tost ve bir çay alabilir miyim?"),
    ("property", "Evin kirası bu ay yine arttı."),
    ("property", "Tapu işlemleri için yarın müdürlüğe gideceğim."),
    ("property", "Arsa satışı için noterden randevu aldım."),
    ("school", "Öğretmenimiz yarın sınav yapacağını söyledi."),
    ("school", "Matematik ödevini bitirmem lazım."),
    ("work", "Patronum bu hafta fazla mesai istedi."),
    ("work", "Yeni projede ekip arkadaşlarımla çok uyumluyuz."),
    ("sports", "Galatasaray dün akşam 3-1 kazandı."),
    ("sports", "Hakem son dakikada penaltı verdi."),
    ("sports", "Maç 59. dakikada golle açıldı."),
    ("politics_neutral", "Seçim sonuçları yarın resmen açıklanacak."),
    ("politics_neutral", "Meclis yeni bütçeyi görüşmeye başladı."),
    ("politics_neutral", "AK Parti ve CHP temsilcileri bir araya geldi."),
    ("slang_non_abusive", "Kanka naber, akşam çıkıyor muyuz?"),
    ("slang_non_abusive", "Moruk ne haber, uzun zaman oldu."),
    ("slang_non_abusive", "Lan gel buraya, sana bir şey göstereyim."),
    ("slang_non_abusive", "Oha, bu ne güzel bir manzara!"),
    ("slang_non_abusive", "Abi harikasın, eline sağlık."),
    ("slang_non_abusive", "Oğlum bak şuraya, ne güzel olmuş."),
    ("slang_non_abusive", "Vay be, efsane bir maçtı."),
]
CLEAN_SUSPICIOUS = [
    "Amcam ambulansla hastaneye gitti.",
    "Psikoloji bölümünü kazandım.",
    "Eski sikke koleksiyonu çok değerli.",
    "Canım sıkıldı, dışarı çıkalım.",
    "Bu elbise çok şık olmuş.",
    "Maçta şike iddiası gündemde.",
    "Malzeme listesini hazırladım.",
    "Amacımız herkese ulaşmak.",
    "Polis şüpheliyi bir süre alıkoydu.",
    "Usta malayı alıp duvarı sıvadı.",
    "Gotik mimari çok etkileyici.",
    "Kasım ayında tatile gideceğiz.",
    "Dolmabahçe Sarayı'nı gezdik.",
    "Sıkıntı yok, hallederiz.",
    "Memleketimi çok özledim.",
    "Klasik müzik dinlemeyi severim.",
    "Kerpiç evler depreme dayanıksız.",
    "Ampulü değiştirmen lazım.",
    "Şikayetinizi aldık, en kısa sürede dönüş yapacağız.",
    "Bokser köpekleri çok enerjik.",
    "Ahlak felsefesi dersini çok seviyorum.",
    "Sık sık buraya geliyoruz.",
    "Amir bey toplantıya geç kaldı.",
    "Çok sıkı çalışman gerekiyor.",
    "Tabii ki yardım ederim, ama önce işimi bitireyim.",
]


def build_clean() -> None:
    for i, (sub, text) in enumerate(CLEAN, 1):
        add(f"CLEAN-{i:03d}", "CLEAN", sub, text, expected={"rule_fired_exact": []}, signals=M3_NO_A,
            notes="Ordinary Turkish; no lexical or doxing code may fire. The final verdict cannot be "
                  "'clean' while m5 is a stub (fail closed).",
            source_ref="modules/m1_lexicon/spec.md; tests/test_end_to_end.py clean case")
    for i, text in enumerate(CLEAN_SUSPICIOUS, 1):
        add(f"CLEAN-SUB-{i:03d}", "CLEAN", "suspicious_substring", text,
            expected={"rule_fired_exact": []}, signals=M3_NO_A,
            notes="Contains a substring that collides with a lexicon root; a root inside a longer word is a "
                  "collision, never a match (m1 spec §5); Turkish-stem / whitelist words are M1-PREC-1 clean.",
            source_ref="modules/m1_lexicon/module.py docstring; eval/traps/traps.jsonl; " + REF_PREC)


# ------------------------------------------------------------------------------------------------
# 2. TAXONOMY - every routed root
# ------------------------------------------------------------------------------------------------
A_TABLE: dict[str, dict[str, Any]] = {
    "am": {"plain": "am", "targeted": "Sen tam bir amcıksın", "suffix": "amından", "punct": "am?", "upper": "AM"},
    "amcı": {"plain": "amcı", "targeted": "Sen amcı mısın?", "punct": "amcı!", "upper": "AMCI"},
    "amk": {"plain": "amk", "targeted": "Sana ne amk", "punct": "amk...", "upper": "AMK"},
    "bok": {"plain": "bok", "targeted": "Senin yaptığın iş bok gibi", "punct": "(bok)", "upper": "BOK"},
    "gavat": {"plain": "gavat", "targeted": "Sen tam bir gavatsın", "suffix": "gavatlar", "punct": "gavat!",
              "upper": "GAVAT"},
    "göt": {"plain": "göt", "targeted": "Götünü kaldır lan", "suffix": "götler", "punct": "göt?", "upper": "GÖT"},
    "hassiktir": {"plain": "hassiktir", "targeted": "Hassiktir lan oradan", "punct": "hassiktir!",
                  "upper": "HASSİKTİR"},
    "orospu": {"plain": "orospu", "targeted": "Seni orospu çocuğu seni", "suffix": "orospular",
               "punct": "\"orospu\"", "upper": "OROSPU"},
    "oç": {"plain": "oç", "targeted": "Lan oç", "punct": "oç!", "upper": "OÇ"},
    "pezevenk": {"plain": "pezevenk", "targeted": "Sen tam bir pezevenksin", "suffix": "pezevenkler",
                 "punct": "pezevenk...", "upper": "PEZEVENK"},
    "piç": {"plain": "piç", "targeted": "Sen bir piçsin", "suffix": "piçler", "punct": "[piç]", "upper": "PİÇ"},
    "sakso": {"plain": "sakso", "targeted": "Git sakso çek lan", "suffix": "saksocular", "punct": "sakso?",
              "upper": "SAKSO"},
    "sg": {"plain": "sg", "targeted": "sg lan", "punct": "sg!", "upper": "SG"},
    "sik": {"plain": "sik", "targeted": "Seni sikerim", "suffix": "siktiler", "punct": "sik!", "upper": "SİK"},
    "sktrgt": {"plain": "sktrgt", "targeted": "sktrgt lan", "punct": "sktrgt!", "upper": "SKTRGT"},
    "taşak": {"plain": "taşak", "targeted": "Taşak mı geçiyorsun sen?", "suffix": "taşaklar", "punct": "taşak!",
              "upper": "TAŞAK"},
    "yarrak": {"plain": "yarrak", "targeted": "Sen tam bir yarraksın", "suffix": "yarraklar", "punct": "yarrak...",
               "upper": "YARRAK"},
}

B1_PUNCT = ["{W}!", "{w}...", "\"{w}\"", "({w})", "{w}?", "{W}!!!", "'{w}'", "{W}."]
B1_TARGETED_OVERRIDE = {"çüş": "Çüş lan!"}

B2_TABLE: dict[str, dict[str, str]] = {
    "boğazınıkeserim": {"natural": "boğazını keserim", "targeted": "Senin boğazını keserim",
                        "punct": "Boğazını keserim!", "upper": "BOĞAZINI KESERİM"},
    "canınıalırım": {"natural": "canını alırım", "targeted": "Seni bulup canını alırım",
                     "punct": "Canını alırım...", "upper": "CANINI ALIRIM"},
    "ensenibulurum": {"natural": "enseni bulurum", "targeted": "@mehmet enseni bulurum",
                      "punct": "Enseni bulurum!", "upper": "ENSENİ BULURUM"},
    "gömerler": {"natural": "Seni buraya gömerler", "targeted": "Lan seni gömerler",
                 "punct": "Gömerler seni!", "upper": "GÖMERLER"},
    "kafanıkırarım": {"natural": "kafanı kırarım", "targeted": "Lan kafanı kırarım",
                      "punct": "Kafanı kırarım, bak!", "upper": "KAFANI KIRARIM"},
    "mezarınıkazarım": {"natural": "mezarını kazarım", "targeted": "Senin mezarını kazarım",
                        "punct": "Mezarını kazarım!", "upper": "MEZARINI KAZARIM"},
    "öldürücem": {"natural": "Onu öldürücem", "targeted": "Seni öldürücem", "punct": "Öldürücem!",
                  "upper": "ÖLDÜRÜCEM"},
}
B3_TABLE: dict[str, dict[str, str]] = {
    "allahbelanıversin": {"natural": "Allah belanı versin", "targeted": "Allah belanı versin senin",
                          "punct": "Allah belanı versin!", "upper": "ALLAH BELANI VERSİN"},
    "asılası": {"natural": "asılası herif", "targeted": "Sen asılası birisin", "punct": "Asılası!",
                "upper": "ASILASI"},
    "belanıbulurum": {"natural": "belanı bulurum", "targeted": "Senin belanı bulurum", "punct": "Belanı bulurum!",
                      "upper": "BELANI BULURUM"},
    "cehenneme": {"natural": "Hepsi cehenneme", "targeted": "Sen de cehenneme git", "punct": "Cehenneme git!",
                  "upper": "CEHENNEME"},
    "defol": {"natural": "Defol git", "targeted": "Defol git buradan lan", "punct": "Defol!", "upper": "DEFOL"},
    "geber": {"natural": "Geber", "targeted": "Sen de geber", "punct": "Geber!", "upper": "GEBER"},
    "gömülesi": {"natural": "gömülesi herif", "targeted": "Sen gömülesi birisin", "punct": "Gömülesi!",
                 "upper": "GÖMÜLESİ"},
    "kesilesi": {"natural": "Dilin kesilesi", "targeted": "Senin dilin kesilesi", "punct": "Dilin kesilesi!",
                 "upper": "KESİLESİ"},
    "yakılası": {"natural": "yakılası herif", "targeted": "Sen yakılası birisin", "punct": "Yakılası!",
                 "upper": "YAKILASI"},
}
NONE_TABLE: dict[str, dict[str, str]] = {
    "dingil": {"context": "Arabanın dingili kırıldı.", "upper": "DİNGİL", "punct": "dingil?"},
    "dolandırıcı": {"context": "Telefon dolandırıcıları yaşlıları hedef alıyor.", "upper": "DOLANDIRICI",
                    "punct": "dolandırıcı!"},
    "döl": {"context": "Döl yatağı kanseri taraması yapıldı.", "upper": "DÖL", "punct": "döl?"},
    "fuhuş": {"context": "Fuhuş operasyonunda beş kişi gözaltına alındı.", "upper": "FUHUŞ", "punct": "fuhuş!"},
    "glk": {"context": "glk ne demek bilen var mı?", "upper": "GLK", "punct": "glk?"},
    "hapiyedin": {"context": "Bu sefer hapı yedin", "upper": "HAPİYEDİN", "punct": "hapiyedin!"},
    "kalpazan": {"context": "Polis kalpazanları yakaladı.", "upper": "KALPAZAN", "punct": "kalpazan!"},
    "kaybol": {"context": "Kaybol gözümün önünden!", "upper": "KAYBOL", "punct": "kaybol!"},
    "kaşar": {"context": "Kaşar peyniri çok pahalandı.", "upper": "KAŞAR", "punct": "kaşar?"},
    "kerhane": {"context": "Eski kerhane binası yıkıldı.", "upper": "KERHANE", "punct": "kerhane!"},
    "meme": {"context": "Meme kanseri erken teşhisle tedavi edilebilir.", "upper": "MEME", "punct": "meme?"},
    "tabanvansen": {"context": "tabanvansen dedi ve gitti", "upper": "TABANVANSEN", "punct": "tabanvansen!"},
    "tokmakçı": {"context": "Tokmakçı usta kapıyı onardı.", "upper": "TOKMAKÇI", "punct": "tokmakçı?"},
    "yıkık": {"context": "Yıkık bir binanın önünden geçtik.", "upper": "YIKIK", "punct": "yıkık!"},
}


def build_taxonomy() -> None:
    # --- A (17): the family-A carrier; A1 / A2 by m6's target (ADR-005) ---------------------------
    if set(A_TABLE) != set(ROUTE_A):
        raise ValueError(f"A table out of date: {sorted(set(ROUTE_A) ^ set(A_TABLE))}")
    for root in sorted(ROUTE_A):
        row, tax = A_TABLE[root], {"root": root, "route": "A"}
        m1 = {"family_a_roots_include": [root]}
        for variant in ("plain", "punct", "upper", "suffix"):
            if variant not in row:
                continue
            add(f"TAX-A-{slug(root)}-{variant}", "TAXONOMY_A", variant, row[variant],
                expected={"rule_fired_exact": ["A1"], "verdict_min": "nudge"}, signals={"m1": m1},
                notes=f"Family-A root '{root}' ({variant}); no target -> A1 carrier stays A1.",
                source_ref=f"{REF_ROUTE}; {REF_PREC}; {REF_ADR005}", taxonomy=tax)
        add(f"TAX-A-{slug(root)}-targeted", "TAXONOMY_A", "targeted", row["targeted"],
            expected={"rule_fired_exact": ["A2"], "verdict_min": "review"},
            signals={"m1": m1, "m6": {"target_type": "individual"}},
            notes=f"Family-A root '{root}' aimed at a person: m6 individual -> decision recodes A1 to A2.",
            source_ref=f"{REF_ADR005}; {REF_M6}", taxonomy=tax)

    # --- B1 (100): ordinary insult / degradation, never family A -----------------------------------
    for i, root in enumerate(sorted(ROUTE_B1)):
        tax, m1 = {"root": root, "route": "B1"}, {"roots_include": [root], "routes_include": ["B1"]}
        exact = {"rule_fired_exact": ["B1"], "verdict_min": "review"}
        add(f"TAX-B1-{slug(root)}-plain", "TAXONOMY_B1", "plain", root, expected=exact, signals={"m1": m1},
            notes="EXCLUDED root routed to B1: B1 fires, never family A.", source_ref=REF_ROUTE, taxonomy=tax)
        targeted = B1_TARGETED_OVERRIDE.get(root, f"Sen {root} {question(root)}?")
        add(f"TAX-B1-{slug(root)}-targeted", "TAXONOMY_B1", "targeted", targeted, expected=exact,
            signals={"m1": m1, "m6": {"target_type": "individual"}},
            notes="Targeted degradation: m6 individual; B1 is not target-recoded (only family A is).",
            source_ref=f"{REF_ROUTE}; {REF_M6}", taxonomy=tax)
        if SUFFIXABLE.get(root):
            add(f"TAX-B1-{slug(root)}-suffix", "TAXONOMY_B1", "suffix", f"Hepsi {plural(root)}", expected=exact,
                signals={"m1": m1}, notes="Plural suffix on a terlik-suffixable root.",
                source_ref="modules/m1_lexicon/module.py docstring (legal Turkish suffixes); " + REF_ROUTE,
                taxonomy=tax)
        punct = B1_PUNCT[i % len(B1_PUNCT)].format(w=root, W=tr_cap(root))
        add(f"TAX-B1-{slug(root)}-punct", "TAXONOMY_B1", "punct", punct, expected=exact, signals={"m1": m1},
            notes="Punctuation adjacent to the root.", source_ref=REF_ROUTE, taxonomy=tax)
        add(f"TAX-B1-{slug(root)}-upper", "TAXONOMY_B1", "upper", tr_upper(root), expected=exact,
            signals={"m1": m1}, notes="Turkish uppercase (I/İ) through m0's Turkish casing.",
            source_ref=f"{REF_ROUTE}; {REF_M0}", taxonomy=tax)
    for root, parts in sorted(COMPOUND_ROOTS.items()):
        need(ROUTE_B1, root)
        add(f"TAX-B1-{slug(root)}-spaced_standard", "TAXONOMY_B1", "compound_standard_spelling", " ".join(parts),
            expected={"rule_fired_exact": ["B1"]}, signals={"m1": {"roots_include": [root]}},
            notes="Standard two-word spelling of a compound root (M1-ROUTE-1.1 §1).", source_ref=REF_ROUTE11,
            taxonomy={"root": root, "route": "B1"})

    # --- B2 (7): threat -----------------------------------------------------------------------------
    if set(B2_TABLE) != set(ROUTE_B2):
        raise ValueError("B2 table out of date")
    for root in sorted(ROUTE_B2):
        row, tax = B2_TABLE[root], {"root": root, "route": "B2"}
        m1 = {"roots_include": [root], "routes_include": ["B2"]}
        base = {"rule_fired_include": ["B2"], "rule_fired_exclude": ["A", "B1", "B3"], "verdict_min": "escalate"}
        add(f"TAX-B2-{slug(root)}-plain", "TAXONOMY_B2", "plain_dictionary_spelling", root,
            expected={"rule_fired_exact": ["B2"], "verdict_min": "escalate"}, signals={"m1": m1},
            notes="Dictionary (glued) spelling of the threat root.", source_ref=REF_ROUTE, taxonomy=tax)
        for variant in ("natural", "punct", "upper"):
            add(f"TAX-B2-{slug(root)}-{variant}", "TAXONOMY_B2", variant, row[variant], expected=base,
                signals={"m1": m1},
                notes="Standard spaced spelling of a verb-phrase root passes uninflected (M1-ROUTE-1.1 note).",
                source_ref=f"{REF_ROUTE}; {REF_ROUTE11}", taxonomy=tax)
        add(f"TAX-B2-{slug(root)}-targeted", "TAXONOMY_B2", "targeted", row["targeted"], expected=base,
            signals={"m1": m1, "m6": {"target_type": "individual"}},
            notes="B2 keeps its own code whatever the target (not target-recoded).",
            source_ref=f"{REF_ROUTE}; {REF_M6}", taxonomy=tax)

    # --- B3 (9): curse / exclusion --------------------------------------------------------------------
    if set(B3_TABLE) != set(ROUTE_B3):
        raise ValueError("B3 table out of date")
    for root in sorted(ROUTE_B3):
        row, tax = B3_TABLE[root], {"root": root, "route": "B3"}
        m1 = {"roots_include": [root], "routes_include": ["B3"]}
        base = {"rule_fired_include": ["B3"], "rule_fired_exclude": ["A", "B1", "B2"], "verdict_min": "review"}
        add(f"TAX-B3-{slug(root)}-plain", "TAXONOMY_B3", "plain_dictionary_spelling", root,
            expected={"rule_fired_exact": ["B3"], "verdict_min": "review"}, signals={"m1": m1},
            notes="Dictionary spelling of the curse / exclusion root.", source_ref=REF_ROUTE, taxonomy=tax)
        for variant in ("natural", "punct", "upper"):
            add(f"TAX-B3-{slug(root)}-{variant}", "TAXONOMY_B3", variant, row[variant], expected=base,
                signals={"m1": m1}, notes="B3 must not be converted to A.",
                source_ref=f"{REF_ROUTE}; {REF_ROUTE11}", taxonomy=tax)
        add(f"TAX-B3-{slug(root)}-targeted", "TAXONOMY_B3", "targeted", row["targeted"], expected=base,
            signals={"m1": m1, "m6": {"target_type": "individual"}},
            notes="B3 keeps its own code whatever the target.", source_ref=f"{REF_ROUTE}; {REF_M6}", taxonomy=tax)

    # --- NONE (14): matched internally, no content code ------------------------------------------------
    if set(NONE_TABLE) != set(ROUTE_NONE):
        raise ValueError("NONE table out of date")
    for root in sorted(ROUTE_NONE):
        row, tax = NONE_TABLE[root], {"root": root, "route": "NONE"}
        add(f"TAX-NONE-{slug(root)}-plain", "TAXONOMY_NONE", "plain", root, expected={"rule_fired_exact": []},
            signals={"m1": {"roots_include": [root], "routes_include": ["NONE"]}},
            notes="Topic / neutral vocabulary: a real dictionary match that emits NO content code.",
            source_ref=f"{REF_ROUTE} §2 NONE row, §6", taxonomy=tax)
        add(f"TAX-NONE-{slug(root)}-upper", "TAXONOMY_NONE", "upper", row["upper"], expected={"rule_fired_exact": []},
            signals={"m1": {"roots_include": [root], "routes_include": ["NONE"]}},
            notes="Uppercase; still no content code.", source_ref=REF_ROUTE, taxonomy=tax)
        add(f"TAX-NONE-{slug(root)}-punct", "TAXONOMY_NONE", "punct", row["punct"], expected={"rule_fired_exact": []},
            notes="Punctuation adjacency; no content code.", source_ref=REF_ROUTE, taxonomy=tax)
        add(f"TAX-NONE-{slug(root)}-context", "TAXONOMY_NONE", "in_sentence", row["context"],
            expected={"rule_fired_exact": []},
            notes="Ordinary sentence using the word; the decision must not invent A/B from this route.",
            source_ref=REF_ROUTE, taxonomy=tax)


# ------------------------------------------------------------------------------------------------
# 3. A - explicit profanity
# ------------------------------------------------------------------------------------------------
def build_a_family() -> None:
    cases = [
        ("capitalization", "SİKTİR GİT", ["A1"]), ("capitalization", "Siktir Git", ["A1"]),
        ("capitalization", "OROSPU ÇOCUĞU", ["A1"]),
        ("suffix", "siktiler", ["A1"]), ("suffix", "orospuluk yapma", ["A1"]), ("suffix", "piçler", ["A1"]),
        ("punctuation", "siktir!", ["A1"]), ("punctuation", "Orospu...", ["A1"]), ("punctuation", "piç?", ["A1"]),
        ("hashtag", "#orospu", ["A1"]), ("hashtag", "#amk bugün de böyle", ["A1"]),
        ("quotes", "\"orospu\"", ["A1"]), ("quotes", "'siktir'", ["A1"]),
        ("brackets", "[piç]", ["A1"]), ("brackets", "(siktir)", ["A1"]), ("brackets", "{amk}", ["A1"]),
        ("sentence_internal", "Bu ne bok gibi bir gün.", ["A1"]),
        ("sentence_final", "Yine geç kaldı amk", ["A1"]),
        ("non_targeted", "Amk ya, yine geç kaldım", ["A1"]),
        ("repeated_chars", "siiiiiktir", ["A1"]), ("repeated_chars", "orospuuuu", ["A1"]),
        ("repeated_chars", "amkkkkk", ["A1"]),
        ("spaced_complete", "S İ K T İ R", ["A1"]), ("spaced_complete", "o r o s p u", ["A1"]),
    ]
    for i, (sub, text, codes) in enumerate(cases, 1):
        add(f"A-{i:03d}", "A_PROFANITY", sub, text, expected={"rule_fired_exact": codes, "verdict_min": "nudge"},
            notes="Explicit family-A profanity; no target -> A1.", source_ref=f"{REF_PREC}; {REF_ADR005}")
    targeted = [
        ("targeted_individual", "@ali siktir git", ["A2"], "individual"),
        ("targeted_individual", "Sen tam bir orospu çocuğusun", ["A2"], "individual"),
        ("targeted_individual", "Lan piç", ["A2"], "individual"),
        ("targeted_group", "Solcuların hepsi piç", ["A3"], "group"),
        ("targeted_group", "Bütün faşistler orospu çocuğu", ["A3"], "group"),
    ]
    for i, (sub, text, codes, target) in enumerate(targeted, 1):
        verdict = "block" if codes == ["A3"] else "review"
        add(f"A-T{i:02d}", "A_PROFANITY", sub, text, expected={"rule_fired_exact": codes, "verdict_min": verdict},
            signals={"m6": {"target_type": target}},
            notes=f"m6 {target} -> decision assigns {codes[0]} (ADR-005); action from thresholds.yaml.",
            source_ref=f"{REF_ADR005}; {REF_M6}")
    for i, (text, word) in enumerate([("Bu program tam bir bok", "program"), ("Siktir, yine yağmur yağıyor", "yağmur")], 1):
        add(f"A-NH{i:02d}", "A_PROFANITY", "non_human_target_suppression", text,
            expected={"rule_fired_exact": [], "rule_suppressed_include": ["A1"],
                      "guard_suppressed": [["NON_HUMAN_TARGET", "A1"]]},
            signals={"m6": {"target_type": "non_human"}},
            notes=f"'{word}' resolves non_human; m1 raises NON_HUMAN_TARGET on its own hit and the decision "
                  "suppresses the family-A score (ADR-005 amendment). DEMO CAVEAT for the second case: an "
                  "untargeted expletive next to a non-human noun is also suppressed by design.",
            source_ref=f"{REF_GUARDS}; tests/test_end_to_end.py non-human case")
    safe = ["Psikolog randevusu aldım.", "Sikke müzesini gezdik.", "Ambulans çağırın!", "Amatör futbol ligi başladı.",
            "Eşyaları götürmek zorundayım.", "Amaçsızca dolaşıyorum."]
    for i, text in enumerate(safe, 1):
        add(f"A-SAFE{i:02d}", "A_PROFANITY", "safe_compound_boundary", text,
            expected={"rule_fired_exclude": ["A"]}, signals={"m1": {"family_a_roots_exact": []}, **M3_NO_A},
            notes="A root inside a longer ordinary word is a collision, never a match.",
            source_ref="modules/m1_lexicon/spec.md §5; eval/traps/traps.jsonl")
    add("A-A4-01", "A_PROFANITY", "A4_sacred", "Allahını sikeyim", status="NOT_IMPLEMENTED",
        ideal={"rule_fired_include": ["A4"]},
        notes="A4 (profanity against the sacred) has no producer: m1's A4 table is BLOCKED_BY_DATA "
              "(docs/blockers/m1_a4_sacred_concepts.md). The profane root still yields a family-A A1-A3 code.",
        source_ref="docs/blockers/m1_a4_sacred_concepts.md; eval/implementation_status.json m1 not_built")


# ------------------------------------------------------------------------------------------------
# 4. OBFUSCATION / M2 (and m0 Unicode)
# ------------------------------------------------------------------------------------------------
def build_obfuscation() -> None:
    supported = [
        ("digit_substitution", "s4l4k", ["B1"], {"m2": {"form_include": ["LEET"], "normalized_text": "salak"}}),
        ("digit_substitution", "5al4k", ["B1"], {"m2": {"form_include": ["LEET"], "normalized_text": "salak"}}),
        ("digit_substitution", "ş3r3fs1z", ["B1"], {"m2": {"form_include": ["LEET"], "normalized_text": "şerefsiz"}}),
        ("digit_substitution", "ap7al herif", ["B1"], {"m2": {"form_include": ["LEET"]}}),
        ("interior_leet", "s!kt!r git", ["A1"], {"m2": {"form_include": ["LEET"]}}),
        ("interior_leet", "or0spu çocuğu", ["A1"], {"m2": {"form_include": ["LEET"]}}),
        ("interior_leet", "s1kt1r", ["A1"], {}),
        ("interior_leet", "g0t", ["A1"], {}),
        ("spaced_letters", "s a l a k", ["B1"], {"m2": {"form_include": ["SPACED"], "normalized_text": "salak"}}),
        ("spaced_letters", "a p t a l", ["B1"], {"m2": {"form_include": ["SPACED"], "normalized_text": "aptal"}}),
        ("punctuation_insertion", "s.a.l.a.k", ["B1"],
         {"m2": {"form_include": ["PUNCT_SPLIT"], "normalized_text": "salak"}}),
        ("punctuation_insertion", "a-p-t-a-l", ["B1"],
         {"m2": {"form_include": ["PUNCT_SPLIT"], "normalized_text": "aptal"}}),
        ("punctuation_insertion", "s.i.k.t.i.r git", ["A1"], {"m2": {"form_include": ["PUNCT_SPLIT"]}}),
        ("masking", "s*ktir", ["A1"], {"m2": {"form_include": ["SUFFIX_ON_MASKED"]}}),
        ("masking", "o*ospu", ["A1"], {}),
        ("masking", "p*ç", ["A1"], {}),
        ("masking", "g*t", ["A1"], {}),
        ("masking", "ta*ak", ["A1"], {}),
        ("repeated_letters", "saaalaaak", ["B1"], {"m2": {"form_include": ["REPEAT"], "normalized_text": "salak"}}),
        ("repeated_letters", "aptaaaaal", ["B1"], {"m2": {"form_include": ["REPEAT"]}}),
        ("repeated_letters", "siiiktiiir", ["A1"], {"m2": {"form_include": ["REPEAT"]}}),
        ("mixed_casing", "SaLaK", ["B1"], {"m0": {"charsafe_text": "salak"}}),
        ("mixed_casing", "sAlAk HeRiF", ["B1"], {}),
        ("de_ascii", "serefsiz", ["B1"], {"m2": {"form_include": ["DEASCII"], "normalized_text": "şerefsiz"}}),
        ("de_ascii", "gerizekali", ["B1"], {}),
        ("phonetic", "siqtir", ["A1"], {"m2": {"form_include": ["PHONETIC"], "normalized_text": "siktir"}}),
        ("phonetic", "salaq", ["B1"], {"m2": {"form_include": ["PHONETIC"], "normalized_text": "salak"}}),
        ("accent", "áptal", ["B1"], {"m2": {"form_include": ["HOMOGLYPH"], "normalized_text": "aptal"}}),
        ("unicode_fullwidth", "ａｐｔａｌ", ["B1"], {"m0": {"form_include": ["HOMOGLYPH"], "charsafe_text": "aptal"}}),
        ("unicode_cyrillic_mixed", "sаlаk", ["B1"],
         {"m0": {"form_include": ["HOMOGLYPH"], "charsafe_text": "salak"}}),
        ("unicode_zero_width", "sa\u200blak", ["B1"], {"m0": {"form_include": ["ZERO_WIDTH"], "charsafe_text": "salak"}}),
        ("unicode_combining_stuffing", "s\u0336a\u0336l\u0336a\u0336k\u0336", ["B1"],
         {"m0": {"form_include": ["ZERO_WIDTH"], "charsafe_text": "salak"}}),
        ("unicode_math_bold", "\U0001d42c\U0001d422\U0001d424\U0001d42d\U0001d422\U0001d42b", ["A1"],
         {"m0": {"form_include": ["HOMOGLYPH"], "charsafe_text": "siktir"}}),
        ("unicode_circled", "ⓢⓐⓛⓐⓚ", ["B1"], {"m0": {"form_include": ["HOMOGLYPH"]}}),
        ("unicode_hangul_filler", "sa\u3164lak", ["B1"], {"m0": {"form_include": ["ZERO_WIDTH"]}}),
    ]
    for i, (sub, text, codes, sig) in enumerate(supported, 1):
        add(f"OBF-{i:03d}", "OBFUSCATION_M2", sub, text, expected={"rule_fired_exact": codes}, signals=sig,
            notes="Supported single obfuscation strategy (m2 tier 1/2, m0 safety, terlik tolerance, M1-PREC-1 R9).",
            source_ref=f"{REF_M2}; {REF_M0}; {REF_PREC}")
    limitation = [
        ("combination_spaced_leet", "s 4 l 4 k", "not promised: SPACED joins single LETTERS only"),
        ("combination_punct_leet", "s.4.l.4.k", "not promised: PUNCT_SPLIT joins letters, a digit is not a letter"),
        ("combination_repeat_leet", "saaal4k", "not promised: combination of tier-1 rules untested in fixtures"),
        ("combination_cyrillic_leet", "Е4lаk", "not promised: m0 homoglyph + m2 leet in one token"),
        ("combination_mask_spaced", "s * k t i r", "not promised"),
        ("vowel_drop", "slk", "VOWEL_DROP declared unhandled in m2 v1"),
        ("vowel_drop", "şrfsz", "VOWEL_DROP declared unhandled in m2 v1"),
        ("abbreviation", "gzkl", "ABBREV declared unhandled in m2 v1"),
        ("word_merge", "salakherif", "WORD_MERGE declared unhandled; a root inside a longer token is a collision"),
        ("word_merge", "sensalaksın", "WORD_MERGE declared unhandled"),
        ("char_drop", "aptl", "CHAR_DROP declared unhandled in m2 v1"),
        ("dialect", "şerefsüz", "DIALECT declared unhandled in m2 v1"),
        ("emoji_substitution", "Sen tam bir \U0001f437", "EMOJI_SUB out of scope (m2 spec §3)"),
        ("emoji_substitution", "\U0001f595\U0001f595\U0001f595", "EMOJI_SUB out of scope (m2 spec §3)"),
        ("reversed_text", "kalas", "reversed spelling is not a declared pattern"),
        ("rtl_override", "\u202ekalas", "m0 removes the RTL override; the reversed letters are not re-ordered"),
        ("mixed_separators", "s.a-l_a.k", "PUNCT_SPLIT requires the SAME separator between every letter"),
        ("newline_split_letters", "s\na\nl\na\nk", "SPACED requires single spaces"),
        ("hash_mask", "s#ktir", "R9 masked-root alignment reads '*' only"),
        ("edge_digit_leet", "0r0spu çocuğu", "M1-PREC-1 R2: a digit at the word edge rejects a family-A match"),
        ("edge_digit_leet", "5ik", "M1-PREC-1 R2: a digit at the word edge rejects a family-A match"),
        ("uppercase_dotless", "SIKTIR GIT", "M1-PREC-1 §6 decision 3: ASCII capitals read sıktır (accepted cost)"),
        ("cyrillic_full_word", "салак", "m0 maps cross-script homoglyphs INSIDE Latin words"),
    ]
    for i, (sub, text, why) in enumerate(limitation, 1):
        ideal = {"rule_fired_any": ["A1", "A2", "A3", "B1"]}
        add(f"OBF-LIM-{i:03d}", "OBFUSCATION_M2", sub, text, status="LIMITATION", ideal=ideal,
            notes=f"KNOWN_LIMITATION by declaration: {why}. Do NOT fix in this task.",
            source_ref=f"{REF_M2} 'Declared unhandled'; eval/implementation_status.json; {REF_PREC}")


# ------------------------------------------------------------------------------------------------
# 5. RULE-V4 PRECISION REGRESSIONS
# ------------------------------------------------------------------------------------------------
def protocol_list(name: str) -> list[str]:
    body = re.search(rf"^{re.escape(name)} \((\d+)\): (.*)$", PRECISION_PROTOCOL.read_text(encoding="utf-8"), re.M)
    if body is None:
        raise ValueError(f"{name} missing from the protocol")
    items = body.group(2).split(" | ")
    if len(items) != int(body.group(1)):
        raise ValueError(f"{name}: {len(items)} entries, declared {body.group(1)}")
    return items


ACCEPTED_MISSES = {"sıkım", "sıkımı", "sıktır git", "SIKTIR GIT", "amık"}   # protocol §7: "the last five"


def build_rule_v4() -> None:
    clean = protocol_list("ACCEPT_CLEAN")
    if clean[-5:] != ["sıkım", "sıkımı", "sıktır git", "SIKTIR GIT", "amık"]:
        raise ValueError("the protocol's accepted-miss tail changed; re-read §7")
    for i, text in enumerate(clean, 1):
        if text in ACCEPTED_MISSES:
            add(f"V4-CLEAN-{i:03d}", "RULE_V4_PRECISION", "accepted_miss", text, status="LIMITATION",
                expected={"rule_fired_exclude": ["A1", "A2", "A3"]},
                signals={"m1": {"family_a_roots_exact": []}},
                ideal={"rule_fired_any": ["A1", "A2", "A3"]},
                notes="Owner-accepted miss (M1-PREC-1 §6): genuine profanity the rule deliberately does not "
                      "catch. `expected` = the documented behaviour (no family-A hit).",
                source_ref=f"{REF_PREC} §6, §7 ACCEPT_CLEAN tail")
            continue
        add(f"V4-CLEAN-{i:03d}", "RULE_V4_PRECISION", "accept_clean", text,
            expected={"rule_fired_exclude": ["A1", "A2", "A3"]},
            signals={"m1": {"family_a_roots_exact": []}, **M3_NO_A},
            notes="ACCEPT_CLEAN: no POSITIVE-root (family-A) hit on either channel.",
            source_ref=f"{REF_PREC} §7 ACCEPT_CLEAN")
    for list_name, prefix in (("ACCEPT_GENUINE", "V4-GEN"), ("ACCEPT_MASKED", "V4-MASK")):
        for i, entry in enumerate(protocol_list(list_name), 1):
            text, root = entry.rsplit(" => ", 1)
            add(f"{prefix}-{i:03d}", "RULE_V4_PRECISION", list_name.lower(), text,
                expected={"rule_fired_any": ["A1", "A2", "A3"]},
                signals={"m1": {"family_a_roots_include": [root]}},
                notes=f"{list_name}: a family-A hit of root '{root}' is preserved under Rule-v4.",
                source_ref=f"{REF_PREC} §7 {list_name}")
    for i, entry in enumerate(protocol_list("ACCEPT_RESIDUE"), 1):
        text, root = entry.rsplit(" => ", 1)
        add(f"V4-RESIDUE-{i:03d}", "RULE_V4_PRECISION", "accepted_residue", text, status="LIMITATION",
            expected={"rule_fired_any": ["A1", "A2", "A3"]}, signals={"m1": {"family_a_roots_include": [root]}},
            ideal={"rule_fired_exclude": ["A1", "A2", "A3"]},
            notes="Owner-accepted residue (M1-PREC-1 §6 decisions 6, 7): a known false positive that still fires.",
            source_ref=f"{REF_PREC} §6, §7 ACCEPT_RESIDUE")
    extra_clean = ["sık", "sıkı", "öç", "Öc", "I am", "A.K.", "gt", "SIK", "A. MALLARI", "amîn", "şık", "şike"]
    for i, text in enumerate(extra_clean, 1):
        add(f"V4-XCLEAN-{i:03d}", "RULE_V4_PRECISION", "user_listed_clean", text,
            expected={"rule_fired_exclude": ["A1", "A2", "A3"]},
            signals={"m1": {"family_a_roots_exact": []}, **M3_NO_A},
            notes="Task-listed Rule-v4 clean form (standalone) - R1/R3/R5/R6/R7/R8.", source_ref=f"{REF_PREC} §3")
    safe_contexts = [
        ("mal varlığı", "mal", True), ("mal sahibi", "mal", True), ("mal müdürlüğü", "mal", True),
        ("mal ve hizmet", "mal", True), ("domuz eti", "domuz", True), ("domuz gribi", "domuz", True),
        ("allık", "alık", False),
    ]
    for i, (text, root, homonym) in enumerate(safe_contexts, 1):
        exp: dict[str, Any] = {"rule_fired_exact": []}
        if homonym:
            exp["guard_suppressed"] = [["HOMONYM", "B1"]]
            sig = {"m1": {"roots_include": [root]}}
            why = "HOMONYM guard (closed next-word list) suppresses the span-scoped B1 match."
        else:
            sig = {"m1": {"roots_exclude": [root], "collision": True}}
            why = "clean word allık (blush) is a SUBSTRING_COLLISION, not the EXCLUDED root alık."
        add(f"V4-SAFE-{i:03d}", "RULE_V4_PRECISION", "known_safe_context", text, expected=exp, signals=sig,
            notes=why, source_ref=f"{REF_ROUTE} §4, §5.1")
    genuine_extra = [("[piç(3)", "piç", ["A1"]), ("ta*ak", "taşak", ["A1"])]
    for i, (text, root, codes) in enumerate(genuine_extra, 1):
        add(f"V4-XGEN-{i:03d}", "RULE_V4_PRECISION", "user_listed_genuine", text,
            expected={"rule_fired_exact": codes}, signals={"m1": {"family_a_roots_include": [root]}},
            notes="Task-listed genuine form (standalone).", source_ref=f"{REF_PREC} §3 R3, R9")
    compounds = [("geri zekalısın", "gerizekalı"), ("kötü niyetliler", "kötüniyetli"),
                 ("üç kâğıtçılıkları", "üçkağıtçı")]
    for i, (text, root) in enumerate(compounds, 1):
        add(f"V4-COMPOUND-{i:03d}", "RULE_V4_PRECISION", "valid_compound", text,
            expected={"rule_fired_exact": ["B1"]}, signals={"m1": {"roots_include": [root]}},
            notes="M1-ROUTE-1.1: standard two-word compound spelling with a suffix on the last component.",
            source_ref=REF_ROUTE11)


# ------------------------------------------------------------------------------------------------
# 6-9. B1 / B2 / B3 / NONE families (hand-written contexts)
# ------------------------------------------------------------------------------------------------
def build_b_families() -> None:
    b1 = [
        ("direct", "Sen bir aptalsın.", "individual"), ("direct", "Salak mısın sen?", "individual"),
        ("direct", "Tam bir gerizekalısın.", "individual"), ("direct", "Şerefsiz herif!", None),
        ("direct", "@ayse çok ukalasın", "individual"),
        ("targeted", "Senin gibi beyinsiz birini görmedim.", "individual"),
        ("targeted", "Sen hayatımda gördüğüm en görgüsüz insansın.", "individual"),
        ("third_person", "Bu adam tam bir sahtekar.", "none"), ("third_person", "Komşumuz çok görgüsüz biri.", "none"),
        ("third_person", "Müdür denen o kalleş yine yalan söyledi.", "none"),
        ("identity_based", "Sen ibnenin tekisin", "individual"), ("identity_based", "Kürtler aptal.", "group"),
        ("identity_based", "Kadınlar beyinsiz.", "group"), ("identity_based", "Suriyeliler pislik.", "group"),
        ("case_punct", "APTALLAR!", None), ("case_punct", "salaklar...", None), ("case_punct", "GERİZEKALI", None),
        ("case_punct", "SEREFSIZ", None),
        ("still_fires", "Mal mısın sen?", "individual"), ("still_fires", "Mal gibi bakma.", None),
        ("still_fires", "Domuz herif!", None), ("still_fires", "Domuzlar!", None),
    ]
    for i, (sub, text, target) in enumerate(b1, 1):
        sig = {"m6": {"target_type": target}} if target else {}
        add(f"B1-{i:03d}", "B1_DEGRADATION", sub, text,
            expected={"rule_fired_exact": ["B1"], "verdict_min": "review"}, signals=sig,
            notes="Ordinary insult -> B1 (degradation); must never become family A (M1-ROUTE-1). B1 is not "
                  "target-recoded; m6's target is reported on its own axis.",
            source_ref=f"{REF_ROUTE}; {REF_M6}")
    protected = [
        ("Bakanın mal varlığı açıklandı.", "HOMONYM"), ("Mal sahibi kirayı artırdı.", "HOMONYM"),
        ("Mal müdürlüğüne dilekçe verdim.", "HOMONYM"), ("Mal ve hizmet alımı ihalesi yapıldı.", "HOMONYM"),
        ("Mal beyanında bulundu.", "HOMONYM"), ("Domuz eti yemiyorum.", "HOMONYM"),
        ("Domuz gribi salgını yayılıyor.", "HOMONYM"),
        ("Bu film çok aptal.", "NON_HUMAN_TARGET"), ("Bu oyun tam bir salak işi.", "NON_HUMAN_TARGET"),
        ("Bu uygulama çok aptal tasarlanmış.", "NON_HUMAN_TARGET"),
    ]
    for i, (text, guard) in enumerate(protected, 1):
        add(f"B1-GUARD-{i:03d}", "B1_DEGRADATION", "contextual_benign_guarded", text,
            expected={"rule_fired_exact": [], "guard_suppressed": [[guard, "B1"]]},
            notes=f"The B1 match is suppressed by m1's span-scoped {guard} guard (thresholds.yaml lists B1).",
            source_ref=f"{REF_GUARDS}")
    unprotected = [
        "Eşek arısı soktu.", "Hayvanat bahçesinde bir maymun gördük.", "Çiftlikte öküz ve inek var.",
        "Yerdeki pislik temizlendi.", "Rezil oldum, herkesin önünde düştüm.", "Manyak bir maçtı, çok eğlendik!",
    ]
    for i, text in enumerate(unprotected, 1):
        add(f"B1-LIM-{i:03d}", "B1_DEGRADATION", "literal_sense_unprotected", text, status="LIMITATION",
            ideal={"rule_fired_exclude": ["B1"]},
            notes="Literal / self-directed / slang-positive sense of a B1 root. The HOMONYM table is a closed "
                  "list (mal, domuz, am) and SELF_DIRECTED has no producer, so the lexical B1 fires.",
            source_ref=f"{REF_ROUTE} §4 (closed HOMONYM list); decision/thresholds.yaml guards")

    b2 = [
        ("with_profanity", "Seni öldürücem orospu çocuğu", ["B2", "A2"], "individual"),
        ("implied_target", "Bir daha yazarsan kafanı kırarım.", ["B2"], None),
        ("third_person", "Onu öldürücem.", ["B2"], None),
        ("non_human_mention", "Bu oyun yüzünden kafanı kırarım.", ["B2"], "non_human"),
        ("caps_punct", "KAFANI KIRARIM!!!", ["B2"], None),
        ("direct", "Öldürücem seni, bekle.", ["B2"], "individual"),
        ("direct", "Mezarını kazarım senin.", ["B2"], "individual"),
    ]
    for i, (sub, text, codes, target) in enumerate(b2, 1):
        exp: dict[str, Any] = {"rule_fired_exact": codes, "verdict_min": "escalate"}
        if sub == "non_human_mention":
            exp["guards_active_include"] = ["NON_HUMAN_TARGET"]
        add(f"B2-{i:03d}", "B2_THREAT", sub, text, expected=exp,
            signals={"m6": {"target_type": target}} if target else {},
            notes="Threat -> B2 (escalate). NON_HUMAN_TARGET does NOT list B2, so a non-human mention cannot "
                  "suppress a threat. B2 identity is preserved through m6 / decision.",
            source_ref=f"{REF_ROUTE}; {REF_GUARDS}")
    b2_lim = ["Seni öldüreceğim.", "Evini yakarım.", "Seni bıçaklarım.", "Ailene zarar veririm.", "Kafana sıkarım.",
              "Seni bulacağım ve pişman edeceğim."]
    for i, text in enumerate(b2_lim, 1):
        add(f"B2-LIM-{i:03d}", "B2_THREAT", "threat_outside_lexicon", text, status="LIMITATION",
            ideal={"rule_fired_include": ["B2"]},
            notes="Threat wording outside the 7 lexical B2 roots. The M3 B head is untrained (BLOCKED_BY_DATA), "
                  "so only the lexical list produces B2.",
            source_ref="docs/audit/PROJECT_COMPLETION_STATUS.md m3 B head row; " + REF_ROUTE)

    b3 = [
        ("non_targeted", "Hepsi cehenneme gitsin.", ["B3"], None), ("imperative", "Defol git buradan!", ["B3"], None),
        ("imperative", "Geber!", ["B3"], None), ("targeted", "Allah belanı versin senin!", ["B3"], "individual"),
        ("with_insult", "Allah belanı versin şerefsiz", ["B3", "B1"], None),
        ("caps", "ALLAH BELANI VERSİN", ["B3"], None), ("exclusion", "Cehenneme kadar yolun var.", ["B3"], None),
    ]
    for i, (sub, text, codes, target) in enumerate(b3, 1):
        add(f"B3-{i:03d}", "B3_CURSE_EXCLUSION", sub, text,
            expected={"rule_fired_exact": codes, "verdict_min": "review"},
            signals={"m6": {"target_type": target}} if target else {},
            notes="Curse / exclusion -> B3 (review); never converted to A.", source_ref=REF_ROUTE)
    b3_lim = [("Allah seni kahretsin.", {"rule_fired_include": ["B3"]}),
              ("Allah hepsinin belasını versin.", {"rule_fired_include": ["B3"]}),
              ("Defolun gidin!", {"rule_fired_include": ["B3"]}), ("Gebersin hepsi.", {"rule_fired_include": ["B3"]}),
              ("Kahrolsun!", {"rule_fired_include": ["B3"]}),
              ("Cehenneme giden yol iyi niyet taşlarıyla döşelidir.", {"rule_fired_exclude": ["B3"]})]
    for i, (text, ideal) in enumerate(b3_lim, 1):
        add(f"B3-LIM-{i:03d}", "B3_CURSE_EXCLUSION", "outside_lexicon_or_no_context", text, status="LIMITATION",
            ideal=ideal,
            notes="Inflected forms of non-suffixable roots, curses outside the 9 lexical roots, or a proverb the "
                  "lexicon cannot tell from a curse (no context model).",
            source_ref=f"{REF_ROUTE}; terlik suffixable flags")

    none_ctx = ["Meme kanseri erken teşhisle tedavi edilebilir.", "Kaşar peyniri çok pahalandı.",
                "Polis kalpazanlık çetesini çökertti.", "Fuhuş operasyonunda beş kişi gözaltına alındı.",
                "Kaybol gözümün önünden!", "Dolandırıcılar yaşlıları hedef aldı.", "Yıkık dökük bir evde yaşıyorlar."]
    for i, text in enumerate(none_ctx, 1):
        add(f"NONE-{i:03d}", "NONE_ROUTE", "no_content_code", text, expected={"rule_fired_exact": []},
            notes="NONE-route vocabulary: matched internally, no content code, and the decision layer must not "
                  "invent A/B from it. ('kaybol' is routed NONE by owner decision although exclusion-like.)",
            source_ref=f"{REF_ROUTE} §2-§3, §6")


# ------------------------------------------------------------------------------------------------
# 10. TARGET / M6
# ------------------------------------------------------------------------------------------------
def tckn(first9: str) -> str:
    d = [int(c) for c in first9]
    tenth = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
    eleventh = (sum(d) + tenth) % 10
    return first9 + str(tenth) + str(eleventh)


def build_target() -> None:
    sup = [
        ("second_person", "Sen çok aptalsın.", "individual", ["B1"]),
        ("second_person", "Seni sevmiyorum.", "individual", []),
        ("mention", "@veli bugün geliyor musun?", "individual", []),
        ("vocative", "Lan salak!", "individual", ["B1"]),
        ("vocative", "Moruk sen de mi geldin?", "individual", []),
        ("copula_ending", "Aptalsın!", "individual", ["B1"]),
        ("copula_ending_A", "Orospusun!", "individual", ["A2"]),
        ("siz_declared_pending", "Siz ne biçim insanlarsınız?", "individual", []),
        ("group_plural", "Türkler bu konuda haklı.", "group", []),
        ("group_plural", "Kadınlar da seçimde aday olmalı.", "group", []),
        ("group_bare", "Türk kahvesi içtik.", "group", []),
        ("group_affiliation", "Akpliler toplantı yaptı.", "group", []),
        ("group_religion_followers", "Müslümanlar bayramı kutluyor.", "group", []),
        ("object_property", "Bu telefon berbat.", "non_human", []),
        ("object_property", "Arabam yine bozuldu.", "non_human", []),
        ("institution", "Belediye hiçbir şey yapmıyor.", "non_human", []),
        ("no_human_target", "Hava çok soğuk bugün.", "non_human", []),
        ("generic_statement", "İnsanlar bazen hata yapar.", "none", []),
        ("precedence_individual_over_non_human", "Sen bu programı kullanma.", "individual", []),
        ("precedence_individual_over_group", "Sen Türkleri hiç anlamıyorsun.", "individual", []),
        ("members_form_declared_pending", "Belediyedekiler geldi.", "none", []),
        ("party_proper_name_declared", "AKP ve CHP bugün toplandı.", "none", []),
        ("religion_itself_declared", "İslam hakkında bir kitap okudum.", "none", []),
    ]
    for i, (sub, text, target, codes) in enumerate(sup, 1):
        add(f"M6-{i:03d}", "TARGET_M6", sub, text, expected={"rule_fired_exact": codes},
            signals={"m6": {"target_type": target}},
            notes="m6 v1 target resolution as declared in the guideline (precedence individual > group > non_human; "
                  "declared-pending rows are v1 behaviour, not owner decisions).",
            source_ref=REF_M6)
    lim = [
        ("named_person_no_mention", "Ahmet Yılmaz çok aptal.", {"m6": {"target_type": "individual"}},
         "no person-name gazetteer and no NER (ADR-007): a name without @ resolves nothing"),
        ("third_person_pronoun", "O tam bir salak.", {"m6": {"target_type": "individual"}},
         "third-person pronouns are not in the frozen deictic set"),
        ("self_reference", "Ben çok aptalım.", {"rule_fired_exclude": ["B1"]},
         "SELF_DIRECTED guard has no producer; a self-insult still fires B1"),
        ("reported_speech_target", "Ahmet bana salak dedi.", {"rule_fired_exclude": ["B1"]},
         "no reported-speech handling; the lexical B1 fires"),
        ("sports_supporters", "Fenerliler yine kaybetti.", {"m6": {"target_type": "group"}},
         "sports supporters are not listed (declared pending owner decision)"),
        ("ambiguous_target", "Kim yaptıysa çok aptal.", {"m6": {"target_type": "individual"}},
         "an indefinite referent is not resolved"),
    ]
    for i, (sub, text, ideal, why) in enumerate(lim, 1):
        add(f"M6-LIM-{i:03d}", "TARGET_M6", sub, text, status="LIMITATION", ideal=ideal,
            notes=f"Beyond m6 v1: {why}.", source_ref=f"{REF_M6} §5; protocols/ADR-007-m6-ner-gazetteer.md")
    valid_id = tckn("123456789")
    dox = [
        ("doxing_phone", "Onun numarası 0532 123 45 67, herkes arasın.", ["B4"]),
        ("doxing_iban", "IBAN'ı TR33 0006 1005 1978 6457 8413 26, para isteyin.", ["B4"]),
        ("doxing_national_id", f"TC kimlik numarası {valid_id} olan kişi bu.", ["B4"]),
        ("doxing_address", "Evinin adresi Çiçek Mah. Gül Sok. No: 12 Daire 3, herkes bilsin.", ["B4"]),
        ("doxing_email", "Bana ali.veli@ornek.com adresinden ulaşabilirsiniz.", ["B4"]),
        ("doxing_profile_link", "https://instagram.com/ali.veli hesabına bakın.", ["B4"]),
        ("doxing_near_miss_public", "Mağazamız Çiçek Mah. Gül Sok. No: 12 adresinde hizmet veriyor.", []),
        ("doxing_near_miss_checksum", "Sipariş numaram 12345678901, kargo nerede?", []),
    ]
    for i, (sub, text, codes) in enumerate(dox, 1):
        exp: dict[str, Any] = {"rule_fired_exact": codes}
        if codes:
            exp["verdict_min"] = "escalate"
        add(f"M6-DOX-{i:03d}", "TARGET_M6", sub, text, expected=exp,
            notes="B4 doxing fires only on a validated identifier (guideline §3). DEMO CAVEAT: any e-mail address, "
                  "even the writer's own, is reported (confidence 0.60 >= B4 threshold 0.50) and escalated.",
            source_ref=f"{REF_M6} §3")


# ------------------------------------------------------------------------------------------------
# 11. CHARACTER SAFETY / M0
# ------------------------------------------------------------------------------------------------
def build_m0() -> None:
    sup = [
        ("normal_turkish", "Çiçekler açmış, güneş parlıyor.", [], {"form_exclude": ["ZERO_WIDTH", "HOMOGLYPH"]}),
        ("turkish_casing", "SIKINTI YOK", [], {"charsafe_text": "sıkıntı yok", "form_include": ["DOTLESS_I"]}),
        ("turkish_casing", "İSTANBUL'A GİDİYORUM", [], {"form_include": ["DOTLESS_I"]}),
        ("turkish_casing", "KERPİÇ", [], {"form_include": ["DOTLESS_I"]}),
        ("homoglyph_cyrillic_in_latin", "аptаl", ["B1"], {"charsafe_text": "aptal", "form_include": ["HOMOGLYPH"]}),
        ("mixed_alphabet_sentence", "Merhaba мир, nasılsın?", [], {"form_exclude": ["HOMOGLYPH"]}),
        ("mixed_alphabet_sentence", "Merhaba مرحبا dünya", [], {}),
        ("combining_stuffing", "a\u0336p\u0336t\u0336a\u0336l\u0336", ["B1"], {"charsafe_text": "aptal",
                                                                             "form_include": ["ZERO_WIDTH"]}),
        ("decomposed_letter", "s\u0327erefsiz", ["B1"], {"charsafe_text": "şerefsiz"}),
        ("zero_width_inside_word", "ap\u200btal herif", ["B1"], {"form_include": ["ZERO_WIDTH"]}),
        ("zero_width_joiner_emoji", "\U0001f468\u200d\U0001f469\u200d\U0001f467 ailemle tatildeyiz", [],
         {"form_exclude": ["ZERO_WIDTH"]}),
        ("bom_leading", "\ufeffMerhaba arkadaşlar", [], {}),
        ("variation_selector_emoji", "❤\ufe0f seni seviyorum", [], {}),
        ("regional_indicator_flag", "\U0001f1f9\U0001f1f7 Türkiye", [], {"form_exclude": ["HOMOGLYPH"]}),
        ("emoji_adjacency", "aptal\U0001f602", ["B1"], {}),
        ("emoji_adjacency", "\U0001f621salak\U0001f621", ["B1"], {}),
        ("symbol_heavy", "!!!???***###@@@$$$", [], {}),
        ("symbol_heavy", "%%% +++ === ~~~ ^^^", [], {}),
        ("fullwidth", "ｓａｌａｋ", ["B1"], {"charsafe_text": "salak", "form_include": ["HOMOGLYPH"]}),
        ("small_capitals", "ꜱᴀʟᴀᴋ", ["B1"], {"form_include": ["HOMOGLYPH"]}),
        ("invisible_filler", "ap\u3164tal", ["B1"], {"form_include": ["ZERO_WIDTH"]}),
        ("control_chars", "Merhaba\x00\x1b dünya", [], {}),
    ]
    for i, (sub, text, codes, m0) in enumerate(sup, 1):
        add(f"M0-{i:03d}", "CHARSAFE_M0", sub, text, expected={"rule_fired_exact": codes},
            signals={"m0": m0} if m0 else {},
            notes="m0 declared behaviour: invisible / styled / cross-script characters mapped with a FormPattern; "
                  "Turkish I casing; ZWJ inside emoji and flags kept.",
            source_ref=REF_M0)
    add("M0-MALFORMED-001", "CHARSAFE_M0", "lone_surrogate", "abc\ud800def",
        expected={"no_crash": True, "allow_degraded": True},
        notes="Malformed UTF-16 (lone surrogate) as it can arrive from a JSON escape. Requirement: the request "
              "never crashes (fail closed); a module may degrade.",
        source_ref=REF_PIPE)
    add("M0-MALFORMED-002", "CHARSAFE_M0", "rtl_override_clean", "\u202eMerhaba", expected={"rule_fired_exact": []},
        notes="Bidi override removed as an invisible character.", source_ref=REF_M0)


# ------------------------------------------------------------------------------------------------
# 12. M3 SEMANTIC, 13. M4 STAGE 1, 14. M5
# ------------------------------------------------------------------------------------------------
def build_models() -> None:
    m3 = [
        ("clean_semantic", "Bugün harika bir gün geçirdim, herkese teşekkürler.", {"binary_offensive_fired": False,
                                                                                 "a_head_fired": False}),
        ("clean_semantic", "Toplantı notlarını e-posta ile gönderdim.", {"binary_offensive_fired": False,
                                                                        "a_head_fired": False}),
        ("offensive_no_profanity", "Senin gibi insanlar bu ülkeye yük.", {"binary_offensive_fired": True,
                                                                         "a_head_fired": False}),
        ("offensive_no_profanity", "Beynini kullanmayı bir dene istersen.", {"binary_offensive_fired": True,
                                                                            "a_head_fired": False}),
        ("explicit_A", "Siktir git orospu çocuğu", {"binary_offensive_fired": True, "a_head_fired": True}),
        ("explicit_A", "Amına koyayım böyle işin", {"binary_offensive_fired": True, "a_head_fired": True}),
        ("m1_sees_nothing", "Kafası çalışmayan biri ancak böyle yazar.", {"binary_offensive_fired": True}),
        ("m1_sees_nothing", "Senin annen de senin gibi mi düşünüyor?", {}),
        ("benign_negative_emotion", "Çok üzgünüm, bugün berbat bir gün geçirdim.", {"binary_offensive_fired": False,
                                                                                   "a_head_fired": False}),
        ("benign_negative_emotion", "Bu habere çok sinirlendim, inanılmaz bir adaletsizlik.",
         {"binary_offensive_fired": False, "a_head_fired": False}),
        ("borderline", "Bu fikir gerçekten saçma.", {}),
        ("borderline", "Biraz daha düşünerek konuşsan iyi olur.", {}),
        ("obfuscation_beyond_m1", "0r0spu çocuğu", {}),
        ("obfuscation_beyond_m1", "srfsz herif", {}),
    ]
    for i, (sub, text, exp) in enumerate(m3, 1):
        add(f"M3-{i:03d}", "M3_SEMANTIC", sub, text, status="M3_DEPENDENT", signals={"m3": exp},
            notes="Learned-head behaviour. Evaluated only with the exact Rule-v4 artifact; thresholds exactly as "
                  "configured (A family 0.50 per A-OP-1 carrier thresholds; binary_offensive from thresholds.yaml). "
                  "An empty expectation = borderline, recorded only.",
            source_ref="protocols/m3_a_head_operating_policy.md; decision/thresholds.yaml")
    mech = ["Bugün hava çok güzel.", "Sen bir aptalsın.", "Bu program tam bir aptal.", "Kadınlar araba kullanmayı bilmez.",
            "Seni öldürücem.", "Siktir git"]
    for i, text in enumerate(mech, 1):
        add(f"M4-MECH-{i:03d}", "M4_STAGE1", "stage1_mechanics", text,
            signals={"m4": {"c_family_note": True, "binary_consistent": True}},
            notes="Stage 1 = ONE global binary_offensive threshold on m3's raw_score (scalar branch, raw channel "
                  "only, action review, not guard-suppressible); m4 itself emits only the C1-C5 note. These are "
                  "artifact-independent mechanics.",
            source_ref="modules/m4_implicit/module.py; decision/thresholds.yaml binary_offensive; ADR-006")
    impl = [("Senin gibilerin yüzünden bu ülke bu halde.", True), ("Kafası çalışmayan biri ancak böyle yazar.", True),
            ("Bugün çok yorgunum, erken yatacağım.", False)]
    for i, (text, fired) in enumerate(impl, 1):
        add(f"M4-IMPL-{i:03d}", "M4_STAGE1", "stage1_implicit_attack", text, status="M3_DEPENDENT",
            signals={"m3": {"binary_offensive_fired": fired}},
            notes="Whether the stage-1 binary threshold catches an implicit attack depends on the M3 artifact's "
                  "scores (and the threshold is derived for the baseline artifact only).",
            source_ref="decision/thresholds.yaml binary_offensive; protocols/threshold_derivation_binary_offensive_stage1.md")
    c_family = [("C1_stereotype", "Kadınlar araba kullanmayı bilmez."), ("C1_stereotype", "Çingeneler hırsızdır."),
                ("C2_inferiority", "Göçmenler bizden daha aşağı insanlar."),
                ("C3_coded", "Biliyorsunuz kimleri kastettiğimi, 'onlar' yine aramızda."),
                ("C4_incitement", "Hepsini bu ülkeden kovmamız lazım, sokağa dökülün!"),
                ("C5_defamation", "Belediye başkanı rüşvet alıyor, herkes bilsin.")]
    for i, (sub, text) in enumerate(c_family, 1):
        add(f"M4-S2-{i:03d}", "M4_STAGE1", f"stage2_{sub}", text, status="LIMITATION",
            ideal={"fired_any": ["C1", "C2", "C3", "C4", "C5"]},
            notes="C1-C5 need m3's C head + m4 stage 2 (BLOCKED_BY_POLICY + WAITING_FOR_GPU_ARTIFACT). Stage 2 is "
                  "not built: KNOWN_LIMITATION, not a failure.",
            source_ref="docs/training/m4_stage2.md; eval/implementation_status.json")
    m5 = ["Ne kadar da zekisin, maşallah!", "Aferin sana, yine harika bir iş çıkardın!", "Vay be, dahi misin nesin?",
          "Çok yardımcı oldun gerçekten, sayende her şey mahvoldu.", "Tabii canım, sen her şeyi bilirsin zaten.",
          "Bravo, yine son dakikada hatırladın.", "Bu kadar zeki olmak yorucu olmalı.",
          "Tebrikler, bu kadar aptalca bir fikri ancak sen bulabilirdin."]
    for i, text in enumerate(m5, 1):
        add(f"M5-{i:03d}", "M5_SARCASM", "degrading_sarcasm", text, status="NOT_IMPLEMENTED",
            signals={"m5": {"stub_degraded": True}}, ideal={"fired_any": ["D1"]},
            notes="D1 degrading sarcasm: m5_sarcasm is a declared stub (entry gate, no corpus). It emits nothing and "
                  "degrades every result. The system must NOT be presented as detecting sarcasm.",
            source_ref="modules/m5_sarcasm/module.py; docs/blockers/m5_sarcasm_corpus_gate.md")


# ------------------------------------------------------------------------------------------------
# 15. QUOTATION / REPORTED SPEECH, 16. EDGE CASES, 17. COMBINED
# ------------------------------------------------------------------------------------------------
def build_quote_edge_combined() -> None:
    quotes = [
        ("quote", "Maçta biri \"orospu çocuğu\" diye bağırdı, çok ayıptı.", ["A1", "A2", "A3"]),
        ("reported_speech", "Ahmet bana aptal dedi, çok üzüldüm.", ["B1"]),
        ("news_report", "Haberlere göre taraftarlar hakeme 'şerefsiz' diye bağırdı.", ["B1"]),
        ("metadiscussion", "'Salak' kelimesi TDK sözlüğünde nasıl tanımlanıyor?", ["B1"]),
        ("educational", "Çocuklara 'aptal' demek özgüvenlerini zedeler.", ["B1"]),
        ("negation", "Sana aptal demiyorum, sadece dikkatli ol.", ["B1"]),
        ("metadiscussion", "'Siktir git' demek hiç hoş değil.", ["A1", "A2", "A3"]),
        ("educational", "Küfür etmeyin: 'amk' gibi kısaltmalar da küfürdür.", ["A1", "A2", "A3"]),
    ]
    for i, (sub, text, codes) in enumerate(quotes, 1):
        add(f"QUOTE-{i:03d}", "QUOTATION_REPORTED", sub, text, status="LIMITATION",
            expected={"rule_fired_any": codes}, ideal={"rule_fired_exclude": codes},
            notes="QUOTE_COUNTERSPEECH / METADISCUSSION / NEGATION exist in the code book but have NO producer "
                  "(only m1's SUBSTRING_COLLISION, HOMONYM, NON_HUMAN_TARGET are configured): quoted, reported and "
                  "educational uses fire like direct abuse. `expected` = documented behaviour.",
            source_ref="decision/thresholds.yaml guards (comment: only guards with a producer are configured)")
    direct = [("direct_abuse_reference", "Sen bir aptalsın.", ["B1"]),
              ("direct_abuse_reference", "Orospu çocuğu seni!", ["A2"]),
              ("direct_abuse_reference", "Siktir git!", ["A1"])]
    for i, (sub, text, codes) in enumerate(direct, 1):
        add(f"QUOTE-DIRECT-{i:03d}", "QUOTATION_REPORTED", sub, text, expected={"rule_fired_exact": codes},
            notes="Direct abuse, for comparison with the quoted forms above.", source_ref=REF_ROUTE)

    long_clean = ("Bugün sabah erkenden kalktım, kahvaltımı yaptım ve işe gittim. Toplantılar uzun sürdü ama "
                  "verimliydi. Akşam arkadaşlarımla buluşup yemek yedik, sonra sahilde yürüyüş yaptık. ") * 12
    long_attack = long_clean + "Bu arada sen tam bir gerizekalısın."
    edge = [
        ("empty", "", {"rule_fired_exact": []}, {"m1": {"lexicon_hit": False}}),
        ("whitespace_only", "   ", {"rule_fired_exact": []}, {}),
        ("whitespace_mixed", "\t\n  \n", {"rule_fired_exact": []}, {}),
        ("one_char", "a", {"rule_fired_exact": []}, {}),
        ("punctuation_only", "?", {"rule_fired_exact": []}, {}),
        ("punctuation_only", "...!!!???", {"rule_fired_exact": []}, {}),
        ("emoji_only", "\U0001f600\U0001f600\U0001f600", {"rule_fired_exact": []}, {}),
        ("numbers_only", "12345", {"rule_fired_exact": []}, {}),
        ("numbers_only", "3.14 ve 2.71", {"rule_fired_exact": []}, {}),
        ("url", "https://www.ornek.com.tr/haber/12345 linkine bak", {"rule_fired_exact": []}, {}),
        ("hashtag", "#MutluPazarlar herkese", {"rule_fired_exact": []}, {}),
        ("username", "@kullanici_123 merhaba", {"rule_fired_exact": []}, {"m6": {"target_type": "individual"}}),
        ("very_long_clean", long_clean, {"rule_fired_exact": []}, {"m3_truncated": True}),
        ("very_long_attack_at_end", long_attack, {"rule_fired_exact": ["B1"]}, {"m3_truncated": True}),
        ("repeated_punctuation", "!!!!!!!!!!!!!!!!!!!!!!!!", {"rule_fired_exact": []}, {}),
        ("repeated_characters", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaa", {"rule_fired_exact": []}, {}),
        ("multiline_clean", "Merhaba\nnasılsın\niyi misin?", {"rule_fired_exact": []}, {}),
        ("newline_separated_attack", "Sen\nbir\naptalsın", {"rule_fired_exact": ["B1"]},
         {"m6": {"target_type": "individual"}}),
        ("mixed_turkish_english", "Bro you are such an aptal", {"rule_fired_exact": ["B1"]}, {}),
        ("mixed_turkish_english", "I am here, bugün geliyorum", {"rule_fired_exact": []}, {}),
        ("all_uppercase_clean", "BU GERÇEKTEN ÇOK GÜZEL BİR GÜN", {"rule_fired_exact": []}, {}),
        ("all_uppercase_attack", "SEN BİR APTALSIN", {"rule_fired_exact": ["B1"]}, {}),
        ("all_lowercase_attack", "sen bir aptalsın", {"rule_fired_exact": ["B1"]}, {}),
        ("padded_whitespace", "   aptal   ", {"rule_fired_exact": ["B1"]}, {}),
        ("zero_width_only", "\u200b\u200b\u200b", {"rule_fired_exact": []}, {}),
        ("five_thousand_chars", "a" * 5000, {"rule_fired_exact": []}, {}),
    ]
    for i, (sub, text, exp, sig) in enumerate(edge, 1):
        add(f"EDGE-{i:03d}", "EDGE_CASES", sub, text, expected=exp, signals=sig,
            notes="Edge input: the request must not crash and must not invent content.", source_ref=REF_PIPE)
    add("EDGE-LIM-001", "EDGE_CASES", "english_profanity", "what the fuck is this", status="LIMITATION",
        ideal={"rule_fired_any": ["A1", "A2", "A3"]},
        notes="The lexicon is Turkish (terlik tr); English profanity is outside its scope.",
        source_ref="modules/m1_lexicon/README.md")

    combined = [
        ("obfuscation_profanity_target", "Sen tam bir or0spu çocuğusun", ["A2"], "review", {"m2": {"form_include": ["LEET"]}}),
        ("threat_profanity", "Seni öldürücem piç kurusu", ["A2", "B2"], "escalate", {}),
        ("degradation_unicode", "Sen tam bir sаlаk", ["B1"], "review", {"m0": {"form_include": ["HOMOGLYPH"]}}),
        ("target_spacing_attack", "@ahmet o r o s p u", ["A2"], "review", {"m2": {"form_include": ["SPACED"]}}),
        ("curse_obfuscation", "Allah belanı v3rs1n", ["B3"], "review", {"m2": {"form_include": ["LEET"]}}),
        ("multiple_categories", "Seni öldürücem şerefsiz, Allah belanı versin, siktir git", ["A2", "B1", "B2", "B3"],
         "escalate", {}),
        ("abusive_then_benign", "Salak herif. Neyse, yarın toplantı saat 10'da.", ["B1"], "review", {}),
        ("benign_substring_plus_attack", "Amcam psikoloji okuyor ama sen tam bir gerizekalısın.", ["B1"], "review",
         {"m1": {"family_a_roots_exact": [], "collision": True}}),
        ("doxing_plus_insult", "Şerefsizin evinin adresi Çiçek Mah. Gül Sok. No: 12 Daire 3", ["B1", "B4"], "escalate", {}),
        ("masked_plus_suffix", "o*ospu çocukları", ["A1"], "nudge", {}),
        ("zero_width_threat", "Seni öldü\u200brücem", ["B2"], "escalate", {"m0": {"form_include": ["ZERO_WIDTH"]}}),
        ("repeat_plus_target", "Lan saaalaaak", ["B1"], "review", {"m6": {"target_type": "individual"}}),
    ]
    for i, (sub, text, codes, vmin, sig) in enumerate(combined, 1):
        exp: dict[str, Any] = {"rule_fired_exact": codes, "verdict_min": vmin}
        add(f"COMB-{i:03d}", "COMBINED", sub, text, expected=exp, signals=sig,
            notes="Realistic combination; records which modules fire and the final decision.",
            source_ref=f"{REF_ROUTE}; {REF_M2}; {REF_M0}; {REF_ADR005}")


# ------------------------------------------------------------------------------------------------
# 18. DEMO-CRITICAL
# ------------------------------------------------------------------------------------------------
def build_demo() -> None:
    demo = [
        ("DEMO-01", "explicit_abuse", "Siktir git lan!", "SUPPORTED", {"rule_fired_exact": ["A2"], "verdict_min": "review"},
         {"m6": {"target_type": "individual"}}, {}, "Explicit profanity aimed at a person (vocative 'lan') -> A2."),
        ("DEMO-02", "obfuscated_abuse", "s.i.k.t.i.r git", "SUPPORTED", {"rule_fired_exact": ["A1"]},
         {"m2": {"form_include": ["PUNCT_SPLIT"]}}, {}, "Punctuation-split obfuscation repaired on m2's parallel channel."),
        ("DEMO-03", "homonym_false_positive_avoidance", "Canım çok sıkıldı, bu akşam sıkı bir antrenman yapacağım.",
         "SUPPORTED", {"rule_fired_exact": []}, {"m1": {"family_a_roots_exact": []}}, {},
         "Rule-v4 R6: sık-/sıkı are ordinary Turkish words, not the obscene root."),
        ("DEMO-04", "homonym_guard", "Bakanın mal varlığı açıklandı.", "SUPPORTED",
         {"rule_fired_exact": [], "guard_suppressed": [["HOMONYM", "B1"]]}, {}, {},
         "'mal' as property: HOMONYM guard suppresses the lexical B1 match."),
        ("DEMO-05", "B1_degradation", "Sen tam bir gerizekalısın.", "SUPPORTED",
         {"rule_fired_exact": ["B1"], "verdict_min": "review"}, {"m6": {"target_type": "individual"}}, {},
         "Ordinary insult -> B1, NOT profanity (A)."),
        ("DEMO-06", "B2_threat", "Seni öldürücem.", "SUPPORTED", {"rule_fired_exact": ["B2"], "verdict_min": "escalate"},
         {"m6": {"target_type": "individual"}}, {}, "Threat -> B2 -> escalate."),
        ("DEMO-07", "B3_curse", "Allah belanı versin!", "SUPPORTED", {"rule_fired_exact": ["B3"], "verdict_min": "review"},
         {}, {}, "Curse -> B3."),
        ("DEMO-08", "target_individual", "@ali siktir git", "SUPPORTED", {"rule_fired_exact": ["A2"], "verdict_min": "review"},
         {"m6": {"target_type": "individual"}}, {}, "@mention -> individual -> A2."),
        ("DEMO-09", "target_group", "Solcuların hepsi piç.", "SUPPORTED", {"rule_fired_exact": ["A3"], "verdict_min": "block"},
         {"m6": {"target_type": "group"}}, {}, "Group noun -> group -> A3 -> block."),
        ("DEMO-10", "semantic_offensive", "Senin gibi insanlar bu ülkeye yük.", "M3_DEPENDENT", {},
         {"m3": {"binary_offensive_fired": True, "a_head_fired": False}}, {},
         "No lexical cue: only M3's binary head can flag it."),
        ("DEMO-11", "clean_message", "Yarın saat 10'da toplantımız var, görüşürüz.", "SUPPORTED",
         {"rule_fired_exact": []}, {}, {}, "Clean message: no content code. The verdict is still 'review' "
                                           "(degraded) because m5 is a stub - explain this in the demo."),
        ("DEMO-12", "known_limitation_sarcasm", "Ne kadar da zekisin, maşallah!", "NOT_IMPLEMENTED", {},
         {"m5": {"stub_degraded": True}}, {"fired_any": ["D1"]}, "Sarcasm (D1) is NOT implemented (m5 stub)."),
        ("DEMO-13", "known_limitation_vowel_drop", "Sen tam bir srfszsn", "LIMITATION", {}, {},
         {"rule_fired_any": ["B1"]}, "Vowel-drop obfuscation is declared unhandled in m2 v1."),
        ("DEMO-14", "doxing", "Evinin adresi Çiçek Mah. Gül Sok. No: 12 Daire 3, herkes bilsin.", "SUPPORTED",
         {"rule_fired_exact": ["B4"], "verdict_min": "escalate"}, {}, {}, "Validated address with a personal cue -> B4."),
        ("DEMO-15", "non_human_target", "Bu film tam bir bok.", "SUPPORTED",
         {"rule_fired_exact": [], "guard_suppressed": [["NON_HUMAN_TARGET", "A1"]]}, {"m6": {"target_type": "non_human"}},
         {}, "Profanity aimed at a film: NON_HUMAN_TARGET suppresses the lexical A score."),
    ]
    for cid, sub, text, status, exp, sig, ideal, note in demo:
        add(cid, "DEMO_CRITICAL", sub, text, status=status, expected=exp, signals=sig, ideal=ideal, notes=note,
            source_ref="see the corresponding family", demo=True)


# ------------------------------------------------------------------------------------------------
# Post-first-run additions: they MEASURE THE REACH of findings of the first run and test a demo
# alternative. No expectation of an existing case was changed; each case says why it was added.
# ------------------------------------------------------------------------------------------------
ADDED = "ADDED AFTER THE FIRST RUN to measure the reach of a first-run finding (no existing expectation changed). "


def build_post_run_additions() -> None:
    groups = [("Türklerin hepsi burada.", "türk"), ("Kürtlerin bayramı kutlu olsun.", "kürt"),
              ("Rusların hepsi geldi.", "rus"), ("Kadınların hepsi geldi.", "kadın")]
    for i, (text, stem) in enumerate(groups, 1):
        add(f"M6-GRP-{i:03d}", "TARGET_M6", "group_plural_plus_case", text, expected={"rule_fired_exact": []},
            signals={"m6": {"target_type": "group"}},
            notes=ADDED + f"Group stem '{stem}' + plural + case suffix: the guideline declares plural / possessive / "
                          "case suffix awareness (its own example: 'mültecilerin'). First-run finding: A-T04 / DEMO-09.",
            source_ref=REF_M6 + " §1 group row")
    add("A-AQ-001", "A_PROFANITY", "abbreviation_aq_in_sentence", "Ne diyorsun aq",
        expected={"rule_fired_any": ["A1", "A2", "A3"]}, signals={"m1": {"family_a_roots_include": ["amk"]}},
        notes=ADDED + "'aq' is an ACCEPT_GENUINE form of amk. First-run finding: V4-GEN-020/021/022.",
        source_ref=f"{REF_PREC} §7 ACCEPT_GENUINE")
    add("A-AQ-002", "A_PROFANITY", "abbreviation_amq_control", "Ne diyorsun amq",
        expected={"rule_fired_any": ["A1", "A2", "A3"]}, signals={"m1": {"family_a_roots_include": ["amk"]}},
        notes=ADDED + "Control for A-AQ-001: 'amq' normalizes to 'amk', not to the clean form 'ak'.",
        source_ref=f"{REF_PREC} §7 ACCEPT_GENUINE")
    add("B1-NH-001", "B1_DEGRADATION", "non_human_word_elsewhere_in_post", "Hava çok soğuk, aptal herif.",
        status="LIMITATION", ideal={"rule_fired_include": ["B1"]},
        notes=ADDED + "Target type is resolved per POST: any non-human stem ('hava') makes m1 raise NON_HUMAN_TARGET "
                      "on ALL its content spans, so an insult aimed at an unnamed person is suppressed "
                      "(ADR-005 design; QUOTE-001 was suppressed the same way through 'Maçta').",
        source_ref=f"{REF_GUARDS}; protocols/ADR-005-family-a-by-target.md")
    add("B1-NH-002", "B1_DEGRADATION", "individual_precedence_control", "Maç kötüydü ama sen tam bir salaksın.",
        expected={"rule_fired_exact": ["B1"]}, signals={"m6": {"target_type": "individual"}},
        notes=ADDED + "Control for B1-NH-001: a second-person token takes precedence (individual > non_human), "
                      "so no NON_HUMAN_TARGET guard is raised.",
        source_ref=REF_M6 + " §1 precedence")
    add("B1-NH-003", "B1_DEGRADATION", "homograph_kara", "Kara kalpli şerefsiz herif.", status="LIMITATION",
        ideal={"rule_fired_include": ["B1"]},
        notes=ADDED + "'kara' (black) is also the dative of the non-human stem 'kar' (snow): m6 resolves non_human "
                      "and the B1 is suppressed. A gazetteer has no sense disambiguation. First-run finding: "
                      "TAX-B1-yuzkarasi-spaced_standard.",
        source_ref=REF_M6 + " §1 non_human row; modules/m6_target/gazetteers/non_human_tr.txt")
    add("B1-LIM-SUFFIX-001", "B1_DEGRADATION", "genitive_or_mutation_suffix", "Salağın tekisin.", status="LIMITATION",
        ideal={"rule_fired_include": ["B1"]},
        notes=ADDED + "terlik 0.1.0 accepts a root only before a suffix it knows: no '-nin/-nın' after a vowel and no "
                      "k->ğ mutation ('salağın'). First-run finding: B1-011 ('ibnenin').",
        source_ref="modules/m1_lexicon/module.py docstring (suffix engine); terlik dictionary.json suffixes")
    add("DEMO-09B", "DEMO_CRITICAL", "target_group_alternative", "Solcular hep piç.",
        expected={"rule_fired_exact": ["A3"], "verdict_min": "block"}, signals={"m6": {"target_type": "group"}},
        notes=ADDED + "Tested alternative for DEMO-09 (plural without a case suffix).", source_ref=REF_ADR005,
        demo=True)


# ------------------------------------------------------------------------------------------------
# JSONL writer that keeps invisible characters visible as escapes
# ------------------------------------------------------------------------------------------------
_INVISIBLE = set("\u115f\u1160\u3164\uffa0\u2800")


def _escape(ch: str) -> str:
    """JSON \\u escape; an astral character becomes its UTF-16 surrogate pair."""
    units = ch.encode("utf-16-le", "surrogatepass")
    return "".join("\\u%04x" % int.from_bytes(units[k:k + 2], "little") for k in range(0, len(units), 2))


def visible_json(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False)
    out = []
    for ch in raw:
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Mn", "Me", "Zl", "Zp") or (cat == "Zs" and ch != " ") \
                or ch in _INVISIBLE:
            out.append(_escape(ch))
        else:
            out.append(ch)
    return "".join(out)


def main() -> int:
    build_clean()
    build_taxonomy()
    build_a_family()
    build_obfuscation()
    build_rule_v4()
    build_b_families()
    build_target()
    build_m0()
    build_models()
    build_quote_edge_combined()
    build_demo()
    build_post_run_additions()
    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        for scenario in _SCENARIOS:
            fh.write(visible_json(scenario) + "\n")
    by_cat: dict[str, int] = {}
    for s in _SCENARIOS:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"wrote {len(_SCENARIOS)} scenarios to {OUT}")
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat:22s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
