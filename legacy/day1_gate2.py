#!/usr/bin/env python3
"""
NSosyal B* — اليوم الأول: تحميل صحيح + بوّابة القرار

يفعل ثلاثة أشياء فقط:
  1. يقرأ OffensEval-TR بالطريقة الصحيحة (بلا اقتباس، تقسيم يدوي على tab)
  2. يجمّد المعجم ويسجّل بصمته
  3. يقيس حجم شريحة "بلا معجم"  <-- هذا الرقم يقرّر بنية المشروع

التشغيل:
    python day1_gate.py --data ./offenseval2020-turkish --lexicon ./karaliste.txt
"""

import argparse, hashlib, json, os, sys
from datetime import datetime
from collections import Counter

# ----------------------------------------------------------------------
# 1. القراءة الصحيحة
# ----------------------------------------------------------------------
# README ينصّ: لا اقتباس ولا محارف هروب. الأسطر الجديدة صارت ثلاث مسافات.
# لذلك: قراءة سطراً سطراً + split('\t') يدوياً. لا pandas.read_csv بإعدادات افتراضية.

def read_offenseval_tsv(path, has_labels=True):
    rows = []
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for ln, line in enumerate(f, start=2):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if has_labels:
                if len(parts) < 3:
                    print(f"  [تحذير] سطر {ln}: {len(parts)} حقول فقط — تخطّي")
                    continue
                # id, tweet, subtask_a  (الحقول الزائدة تُدمج في النص احتياطاً)
                rows.append({
                    "id": parts[0],
                    "text": "\t".join(parts[1:-1]),
                    "label": parts[-1].strip(),
                })
            else:
                rows.append({"id": parts[0], "text": "\t".join(parts[1:])})
    return header, rows


def read_gold_labels(path):
    """ملف تسميات الاختبار: امتداده .tsv لكنه مفصول بفواصل (حسب README)."""
    gold = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                gold[parts[0].strip()] = parts[1].strip()
    return gold


# ----------------------------------------------------------------------
# 2. تجميد المعجم
# ----------------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def tr_lower(s):
    """تصغير واعٍ بالتركية: I->ı  و  İ->i  قبل lower() العادي."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def load_lexicon(path):
    with open(path, encoding="utf-8") as f:
        words = {tr_lower(w.strip()) for w in f if w.strip() and not w.startswith("#")}
    return sorted(words)


# ----------------------------------------------------------------------
# 3. المطابقة: حرفية مقابل جذرية (الالتصاق التركي)
# ----------------------------------------------------------------------

SKIP = {"@user", "url", "@USER", "URL"}

def tokens(text):
    import re
    return [t for t in re.findall(r"\w+", tr_lower(text)) if t not in SKIP]


def hit_literal(text, lex_set):
    """مطابقة تامة للكلمة — تفشل مع aptalsın, aptallara ..."""
    return any(t in lex_set for t in tokens(text))


def hit_root(text, lex_list):
    """مطابقة على الجذر — تمسك الصيغ المصرَّفة."""
    toks = tokens(text)
    for t in toks:
        for root in lex_list:
            if len(root) >= 3 and t.startswith(root):
                return True
    return False


# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="مجلد offenseval2020-turkish")
    ap.add_argument("--lexicon", required=True, help="ملف المعجم (karaliste.txt / swears.txt)")
    ap.add_argument("--out", default="./day1_report.json")
    args = ap.parse_args()

    # --- تحديد الملفات ---
    train_path = None
    for root, _, files in os.walk(args.data):
        for fn in files:
            if fn.endswith(".tsv") and "training" in fn:
                train_path = os.path.join(root, fn)
    if not train_path:
        sys.exit("لم أجد ملف التدريب. تحقّق من مسار --data")

    print(f"ملف التدريب: {train_path}")
    print(f"SHA256      : {sha256(train_path)}\n")

    header, rows = read_offenseval_tsv(train_path)
    print(f"العناوين    : {header}")
    print(f"عدد الصفوف  : {len(rows):,}")

    dist = Counter(r["label"] for r in rows)
    print(f"التوزيع     : {dict(dist)}")
    off_total = dist.get("OFF", 0)
    print(f"نسبة OFF    : {off_total / len(rows) * 100:.1f}%")

    # فحص سلامة: يجب ألا توجد تسميات غريبة
    unexpected = set(dist) - {"OFF", "NOT"}
    if unexpected:
        print(f"\n⚠️  تسميات غير متوقعة: {unexpected}  <-- القراءة فاسدة، أوقف كل شيء")
        sys.exit(1)

    # --- تجميد المعجم ---
    lex_list = load_lexicon(args.lexicon)
    lex_set = set(lex_list)
    lex_hash = sha256(args.lexicon)
    print(f"\nالمعجم      : {args.lexicon}")
    print(f"عدد المداخل : {len(lex_list):,}")
    print(f"SHA256      : {lex_hash}")

    # --- البوّابة: شريحة بلا-معجم ---
    off_rows = [r for r in rows if r["label"] == "OFF"]
    lit_hits = sum(hit_literal(r["text"], lex_set) for r in off_rows)
    root_hits = sum(hit_root(r["text"], lex_list) for r in off_rows)

    lex_free_literal = len(off_rows) - lit_hits
    lex_free_root = len(off_rows) - root_hits

    print("\n" + "=" * 58)
    print("بوّابة اليوم الأول — شريحة بلا معجم (على أمثلة OFF)")
    print("=" * 58)
    print(f"إجمالي OFF                      : {len(off_rows):,}")
    print(f"تصيبها المطابقة الحرفية          : {lit_hits:,}")
    print(f"تصيبها المطابقة الجذرية          : {root_hits:,}")
    print(f"فارق الالتصاق (جذرية − حرفية)   : {root_hits - lit_hits:,}  <-- رقم تركي-خصوصي للتقرير")
    print(f"\nبلا معجم (حرفية)                : {lex_free_literal:,}")
    print(f"بلا معجم (جذرية)  ← المعتمَد    : {lex_free_root:,}")

    print("\nالحكم:")
    if lex_free_root >= 800:
        print(f"  ✅ {lex_free_root:,} ≥ 800 — الشريحة كافية. امضِ بـB* كاملاً (محورا التهرّب).")
    elif lex_free_root >= 400:
        print(f"  ⚠️  {lex_free_root:,} — حدّية. أضف مصدر Mayda اليوم قبل المتابعة.")
        print("      لا تعدّل المعجم لتكبير الشريحة — ذلك اختيار انتقائي.")
    else:
        print(f"  ❌ {lex_free_root:,} < 400 — غير كافٍ.")
        print("      أعد الهيكلة اليوم حول محور التشويه وحده. لا تؤجّل للغد.")

    # --- تنقية الشريحة: بذاءة مُرقَّبة رمزياً (censored) لا يُفترض حسابها "ضمنية" ---
    import re
    CENSOR_PAT = re.compile(r"[a-zçğıiöşü]{1,3}\*{2,}", re.IGNORECASE)

    def is_censored(text):
        return bool(CENSOR_PAT.search(text))

    off_free = [r for r in off_rows if not hit_root(r["text"], lex_list)]
    censored = [r for r in off_free if is_censored(r["text"])]
    clean_free = [r for r in off_free if not is_censored(r["text"])]

    print(f"\nتنقية الشريحة:")
    print(f"  بلا-معجم (خام)               : {len(off_free):,}")
    print(f"  منها: بذاءة مُرقَّبة رمزياً (o***) : {len(censored):,}  <-- احصدها كأدلة تمويه واقعية، لا تحسبها ضمنية")
    print(f"  ضمنية نظيفة (المُعتمَدة فعلياً)  : {len(clean_free):,}")

    # --- علم سياسي (heuristic بسيط) — للحيطة في اختيار أمثلة العرض والتقرير فقط ---
    POLITICAL_MARKERS = ["akp", "chp", "mhp", "hdp", "pkk", "ppkpyd", "ülkücü",
                          "esad", "i̇srail", "israil", "suriye", "reis", "parti",
                          "seçim", "siyaset", "hain", "vatan"]

    def is_political(text):
        low = tr_lower(text)
        return any(m in low for m in POLITICAL_MARKERS)

    demo_safe = [r for r in clean_free if not is_political(r["text"])]
    print(f"  منها: غير سياسية (آمنة للعرض/التقرير) : {len(demo_safe):,}")
    print("  (الشريحة الكاملة تبقى في الإحصاء الكلي — هذا الفرز للعرض والأمثلة التوضيحية فقط،")
    print("   لا لإسقاط بيانات من التقييم الإحصائي — إسقاطها يُدخل تحيّز معاينة)")

    print("\n10 أمثلة آمنة للعرض والتقرير (ضمنية، غير سياسية، بلا ترقيب رمزي):")
    for i, r in enumerate(demo_safe[:10], 1):
        print(f"  {i:2}. {r['text'][:110]}")

    print("\n5 أمثلة من البذاءة المُرقَّبة رمزياً (أدلّة تمويه واقعية — احفظها لعائلة هجوم 'self-censoring'):")
    for i, r in enumerate(censored[:5], 1):
        print(f"  {i:2}. {r['text'][:110]}")

    # --- سجلّ التجميد ---
    report = {
        "frozen_at": datetime.now().isoformat(timespec="seconds"),
        "train_file": os.path.basename(train_path),
        "train_sha256": sha256(train_path),
        "n_rows": len(rows),
        "label_dist": dict(dist),
        "lexicon_file": os.path.basename(args.lexicon),
        "lexicon_sha256": lex_hash,
        "lexicon_size": len(lex_list),
        "off_total": len(off_rows),
        "lexicon_hit_literal": lit_hits,
        "lexicon_hit_root": root_hits,
        "lexicon_free_root": lex_free_root,
        "agglutination_delta": root_hits - lit_hits,
        "censored_selfmasked": len(censored),
        "clean_lexicon_free": len(clean_free),
        "demo_safe_apolitical": len(demo_safe),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nسجلّ التجميد -> {args.out}")
    print("احفظ هذا الملف في المستودع الآن. هو دليلك أمام اللجنة أن المعجم جُمِّد قبل أي قياس.")


if __name__ == "__main__":
    main()
