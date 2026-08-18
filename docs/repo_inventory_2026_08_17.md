# Repo inventory — 2026-08-17

A read-only snapshot of the repository taken to verify three answers the project
lead gave from memory, and to size the drafts against the KYS submission format.

**Scope.** Every command below was read-only. Nothing was trained, no forward
pass was run, no Colab or GPU was used. The official test set was not opened and
no `test_predictions.csv` exists in the tree (item 10). No report prose was
drafted, rewritten or edited. `git status --porcelain --untracked-files=no` was
empty before and after the inventory pass.

**This file itself is the one exception** — it was written afterwards, at the
project lead's explicit instruction, to capture the output that otherwise existed
only in a chat transcript.

**What was being verified.** The lead's stated answers were: drafts are markdown
at `report/01_veri_ve_deney_kurgusu.md`, `report/02_yontem.md`,
`report/04_bulgular.md`, `report/05_sinirliliklar.md`; no docx tooling has ever
existed; no figures exist; the demo is a single stdlib `http.server` page; demo
accessibility was never a design goal. Items 1, 2, 3 and 8 test those
independently. **Four confirm. One is partially contradicted — see item 8(b).**

---

## 1. Report file set — VERIFIED, matches the claim

```
$ find report -type f | sort
report/01_veri_ve_deney_kurgusu.md
report/02_yontem.md
report/04_bulgular.md
report/05_sinirliliklar.md

$ ls -la report/
total 124
drwxr-xr-x 1 HP 197609     0 Aug 17 16:45 ./
drwxr-xr-x 1 HP 197609     0 Aug 17 16:28 ../
-rw-r--r-- 1 HP 197609 14832 Aug 17 16:44 01_veri_ve_deney_kurgusu.md
-rw-r--r-- 1 HP 197609 20547 Aug 17 16:45 02_yontem.md
-rw-r--r-- 1 HP 197609 42762 Aug 17 16:44 04_bulgular.md
-rw-r--r-- 1 HP 197609 25975 Aug 17 16:45 05_sinirliliklar.md

EXISTS  report/01_veri_ve_deney_kurgusu.md
EXISTS  report/02_yontem.md
EXISTS  report/04_bulgular.md
EXISTS  report/05_sinirliliklar.md
```

**Other files under `report/`: none.** Four files, all markdown, all at exactly
the stated paths. **The file set matches the claim exactly.** Note `report/03` is
absent — consistent with four files, but it means the numbering has a gap.

---

## 2. Docx tooling — VERIFIED, none exists

```
$ grep -rn -i --exclude-dir=.venv --exclude-dir=.git --exclude-dir=__pycache__ \
    -E "pandoc|python-docx|python_docx|\bdocx\b|Makefile" .
./phases/07_report.md:11:PDF/DOCX/ODT/RTF anywhere in the tree; nothing ever added under such a name in
./phases/10_sablon_mapping.md:14:| File | `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` |
```

Both hits are prose. Neither is code, a dependency, or an invocation.

```
$ ls -la Makefile makefile GNUmakefile build.sh build.py noxfile.py tasks.py
ls: cannot access 'Makefile': No such file or directory
ls: cannot access 'makefile': No such file or directory
ls: cannot access 'GNUmakefile': No such file or directory
ls: cannot access 'build.sh': No such file or directory
ls: cannot access 'build.py': No such file or directory
ls: cannot access 'noxfile.py': No such file or directory
ls: cannot access 'tasks.py': No such file or directory
```

Build scripts touching `report/`:

```
$ grep -rn --include="*.py" --include="*.sh" --include="*.toml" --include="*.cfg" \
    --include="*.yml" --include="*.yaml" "report/" .
./tests/_dryrun_phase04.py:5:report/serialise path would execute for the first time on Colab -- which is the
```

That is the word "report" inside a docstring about phase-04 serialisation, not
the `report/` directory. **No script reads, writes, or converts anything under
`report/`.**

### Tooling availability — real output

```
$ which pandoc
which: no pandoc in (/c/Users/HP/.local/bin:/c/Users/HP/bin:/mingw64/bin:...)
$ pandoc --version
/usr/bin/bash: line 12: pandoc: command not found

$ python -c "import docx; ..."
ModuleNotFoundError: No module named 'docx'

$ python -c "import matplotlib; ..."
ModuleNotFoundError: No module named 'matplotlib'

$ python -c "import numpy; ..."          # control: the venv is live
numpy 2.5.2
```

**Verdict: matches the claim.** No pandoc, no python-docx, no matplotlib, no
Makefile, no build script. The numpy line confirms the interpreter is the project
venv, so the three failures are real absences and not a broken environment.

---

## 3. Figures — VERIFIED, DOES NOT EXIST

```
$ find . -path ./.venv -prune -o -path ./.git -prune -o -type f \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.svg" \
    -o -iname "*.pdf" -o -iname "*.drawio" -o -iname "*.gif" -o -iname "*.eps" \) -print
(end of list — empty above means none)

$ grep -rn -E "matplotlib|seaborn|plotly|pyplot|savefig|plt\.|altair|bokeh" .
(no matches)

$ git ls-files | grep -iE "\.(png|jpg|jpeg|svg|pdf|drawio|gif|eps)$"
(none tracked)
```

**DOES NOT EXIST** — no image, vector, or diagram file of any kind, tracked or
untracked, anywhere outside `.venv`/`.git`. **No plotting script exists**: not one
reference to any plotting library in the entire tree. Matches the claim.

---

## 4. Word counts

```
$ wc -w report/01_veri_ve_deney_kurgusu.md report/02_yontem.md \
       report/04_bulgular.md report/05_sinirliliklar.md
  1709 report/01_veri_ve_deney_kurgusu.md
  2253 report/02_yontem.md
  5052 report/04_bulgular.md
  2923 report/05_sinirliliklar.md
 11937 total

$ wc -w -l -c report/*.md
   265   1709  14832 report/01_veri_ve_deney_kurgusu.md
   331   2253  20547 report/02_yontem.md
   692   5052  42762 report/04_bulgular.md
   427   2923  25975 report/05_sinirliliklar.md
  1715  11937 104116 total
```

**Combined total: 11,937 words** (`wc -w`), 1,715 lines, 104,116 bytes.

That raw figure counts markdown table syntax as tokens. Decomposed:

| File | wc -w | prose | table cells | headings |
|---|---:|---:|---:|---:|
| `report/01_veri_ve_deney_kurgusu.md` | 1,709 | 1,205 | 451 | 53 |
| `report/02_yontem.md` | 2,253 | 1,713 | 449 | 91 |
| `report/04_bulgular.md` | 5,052 | 3,384 | 1,527 | 141 |
| `report/05_sinirliliklar.md` | 2,923 | 2,380 | 411 | 132 |
| **TOTAL** | **11,937** | **8,682** | **2,838** | **417** |

### Heading trees

**`report/01_veri_ve_deney_kurgusu.md`**

```
L1  1. Veri ve Deney Kurgusu
L2    1.1 Veri kümesi
L2    1.2 Dondurulmuş sözlük ve eşleşme kuralı
L2    1.3 Eğitim / geliştirme ayrımı
L2    1.4 Dilimleme
L2    1.5 Resmî test kümesi ve tek kullanım muhasebesi
L2    1.6 Kayıt altına alınmayan veri kaynakları
L2    1.7 Birincil değerlendirme ölçütü
L3      Bu bölümde kullanılan kaynakların özeti
```

**`report/02_yontem.md`**

```
L1  2. Yöntem
L2    2.1 Model ve eğitim yapılandırması
L3      Neden hiperparametre taraması yapılmadı
L3      Denetim noktası seçimi — açıkça belirtilmesi gereken bir nokta
L2    2.2 Bölünmenin dondurulması
L2    2.3 Dondurulmuş sözlük ve dilim etiketleme
L2    2.4 Döngüsellik karşıtı protokol
L3      2.4.1 Veri rollerinin ayrılması
L3      2.4.2 Eğitim ve değerlendirme gizleme ailelerinin ayrıklığı
L3      2.4.3 Türetme kaynağının ayrılması — ve tasarım sırasında düzeltilen bir hata
L3      2.4.4 Üretilen eğitim verisinin gözle denetimi
L2    2.5 Ön kayıt uygulaması
L2    2.6 Tek kullanımlık test kümesi muhasebesi
L2    2.7 Değerlendirme
L2    2.8 Yeniden üretilebilirlik
```

**`report/04_bulgular.md`**

```
L1  4. Bulgular
L2    4.1 Birincil ölçüt — özet
L2    4.2 Temel çizgi ve açığın büyüklüğü
L3      Genel başarım
L3      Dilimler arası duyarlılık farkı
L3      Eşikten bağımsız karşılaştırma — dilim içi ROC-AUC
L2    4.3 Açık iki yönlüdür
L3      Terimsel açıklama: "küfür taşımayan yanlış pozitif" üç ayrı büyüklüktür
L3      İkinci yordayıcı: muhatap alma
L2    4.4 Hata çözümlemesi — sayım
L3      Yanlış negatifler: etiket gürültüsü mü, gerçek kaçırma mı
L3      En büyük öbek: kararı insan yargısına bağlı satırlar
L3      Yanlış pozitifler: küfrün işlevi
L3      Denetim noktası kararlılığı
L2    4.5 Dilim tanımının duyarlılık denetimi
L2    4.6 Müdahalenin bileşen düzeyindeki etkisi
L3      Kazancın mekanizması — eşik geçişi, sıralama iyileşmesi değil
L2    4.7 Sistem düzeyindeki etki ve bedeller
L3      Ön kayıtta uyarılan takas gerçekleşmiştir
L2    4.8 Kalibrasyon
L2    4.9 Seçici tahmin ve çalışma noktaları
L3      Devretme dilim körüdür — bir sıfır sonucu
L2    4.10 Bulguların özeti
```

**`report/05_sinirliliklar.md`**

```
L1  5. Sınırlılıklar
L2    5.1 Etiketleme sözleşmesine bağımlılık
L2    5.2 Etiket gürültüsü
L2    5.3 Dilim tanımında iki bağımsız kirlenme — ikisi de ters yönde
L3      Birinci kirlenme: `lexicon_hit` dilimine giren yanlış eşleşmeler
L3      İkinci kirlenme: `lexicon_free` dilimine sızan açık küfür
L3      İkisinin ortak yönü
L3      Aynı düzeltme, iki ölçütte zıt yön — çözülmemiş bir gerilim
L2    5.4 Müdahalenin nedensel yorumu — en önemli sınırlılık
L3      Mekanizmanın bir bölümü artık adlandırılabilmektedir
L2    5.5 Dayanıklılık sınamasının zayıflığı
L2    5.6 Tek yapılandırma, tek tohum
L2    5.7 Denetim noktası seçimi
L2    5.8 Vekil ölçütün mutlak değeri
L2    5.9 Genelleme sınırları
L2    5.10 İşletme katmanının sınırları
L2    5.11 Öngörülüp bağlayıcı çıkmayan bir sınırlılık
L2    5.12 Duyarlılık açığının kaynağı ayrıştırılamamaktadır
L3      Ölçüm tasarımında düzeltilen bir kusur — bulgu değil, tanım hatası
L2    5.13 Kapsam notu
L2    5.14 Özet
```

Heading counts: 9 / 15 / 23 / 21 = **68 headings** across the four files.

---

## 5. Page estimate

### The assumption, derived not asserted

**Page geometry.** A4 is 210 × 297 mm. With 25 mm margins on all four sides the
text block is 160 × 247 mm = **453.5 × 700.2 pt** (1 pt = 0.352778 mm).

**Characters per line.** Arial's average advance width for lowercase-dominant
running text is ~0.50–0.55 em. At 12 pt that is 6.00–6.60 pt per character:

```
avg char width 0.50 em = 6.00 pt -> 75.6 chars/line
avg char width 0.55 em = 6.60 pt -> 68.7 chars/line
```

**Lines per page.** Word's "single" spacing for Arial 12 pt is ≈ 1.15 × font size
= 13.80 pt. The required 1.15 line spacing gives 13.80 × 1.15 = **15.87 pt per
line**, so 700.2 / 15.87 = **44.1 lines per full page**.

**Characters per word — measured from these files, not assumed.** Over the 9,353
alphanumeric prose tokens in the four drafts: mean length **6.29 characters**,
median 6. Adding one space gives **7.29 characters per word**. This is why
English rules of thumb understate the page count here — Turkish agglutination
makes the words long.

**Words per page:**

```
   wide glyphs (0.55 em):  9.4 words/line -> 416 words/page dense, 353 after whitespace
 narrow glyphs (0.50 em): 10.4 words/line -> 457 words/page dense, 389 after whitespace
```

The "after whitespace" figures deduct 15% of vertical space for blank lines
between paragraphs and for heading space — 68 headings across 1,715 lines is a
lot of interruption.

**Words-per-page band used: 350–460.** The estimate is given as a range across
that band rather than a point value.

### The estimate

Basis: prose (8,682) + headings (417) = **9,099 words**. Table cell words (2,838)
are excluded.

| words/page | pages (prose only) | pages (prose + headings) |
|---:|---:|---:|
| 460 | 18.9 | 19.8 |
| 420 | 20.7 | 21.7 |
| 390 | 22.3 | 23.3 |
| 350 | 24.8 | 26.0 |

### **ESTIMATE: 19.8 – 26.0 pages**

### Against the 30-page cap

The cap includes cover, contents, references and appendices. The template also
requires 3 separate pages for Kapak, İçindekiler and Kaynakça.

```
cap 30 pp, cover + contents + references = 3 pp -> 27 pp available for body
   at 19.8 pp body: headroom +7.2 pp
   at 26.0 pp body: headroom +1.0 pp
```

**Headroom at the optimistic end: +7.2 pages. At the pessimistic end: +1.0
page.** No surplus at either end — but the pessimistic end leaves one page for
everything not yet written.

### Explicitly NOT in this estimate

- **Tables.** 36 tables, 171 body rows + 36 header rows = **207 rendered rows**
  minimum. At 15.87 pt per row that is ≥ 3,285 pt ≈ **4.7 additional pages before
  any cell wraps**, and several tables have 5–6 columns of Turkish text that will
  wrap. Not added above.
- **Any future figures.** None exist (item 3), so none are counted.
- **All currently-unwritten content**: no team section, no timeline, no
  bibliography, no cover, no contents page.

---

## 6. Limitations section

**14 numbered limitations**, `## 5.1` through `## 5.14`. Headings only:

| # | Heading | Line |
|---|---|---:|
| 5.1 | Etiketleme sözleşmesine bağımlılık | 14 |
| 5.2 | Etiket gürültüsü | 31 |
| 5.3 | Dilim tanımında iki bağımsız kirlenme — ikisi de ters yönde | 47 |
| 5.4 | Müdahalenin nedensel yorumu — en önemli sınırlılık | 133 |
| 5.5 | Dayanıklılık sınamasının zayıflığı | 203 |
| 5.6 | Tek yapılandırma, tek tohum | 235 |
| 5.7 | Denetim noktası seçimi | 251 |
| 5.8 | Vekil ölçütün mutlak değeri | 262 |
| 5.9 | Genelleme sınırları | 272 |
| 5.10 | İşletme katmanının sınırları | 292 |
| 5.11 | Öngörülüp bağlayıcı çıkmayan bir sınırlılık | 311 |
| 5.12 | Duyarlılık açığının kaynağı ayrıştırılamamaktadır | 322 |
| 5.13 | Kapsam notu | 387 |
| 5.14 | Özet | 404 |

Two of the fourteen are not limitations in themselves: 5.13 is a scope note and
5.14 is the summary — so **12 substantive limitation subsections**.

The §5.14 summary table enumerates **20 rows**, with these identifiers (numbers
only):

```
1  2  3a  3b  3c  4  4b  5  6  7  8  9  10  11  12  13  14  15  16  17
```

Seventeen numbered limitations with three lettered splits (3a/3b/3c, 4/4b) — so
the summary table tracks more entries than there are subsections.

---

## 7. Existing tables — 36 total

Caption / header-row content only.

### `report/01_veri_ve_deney_kurgusu.md` — 10 tables, 35 body rows

| # | Line | Under | Header row | Body rows |
|---|---:|---|---|---:|
| T01 | 15 | 1.1 Veri kümesi | Özellik \| Değer | 5 |
| T02 | 45 | 1.2 Dondurulmuş sözlük… | Özellik \| Değer | 3 |
| T03 | 64 | 1.2 Dondurulmuş sözlük… | Eşleşme tanımı \| Sözlüğün yakaladığı `OFF` \| Sözlüğün kaçırdığı `OFF` | 2 |
| T04 | 83 | 1.3 Eğitim / geliştirme ayrımı | (boş) \| Toplam \| `NOT` \| `OFF` \| `OFF` oranı | 3 |
| T05 | 112 | 1.4 Dilimleme | Dilim \| Satır \| `OFF` \| `NOT` \| `OFF` taban oranı | 2 |
| T06 | 142 | 1.5 Resmî test kümesi… | Özellik \| Değer | 4 |
| T07 | 149 | 1.5 Resmî test kümesi… | Dilim \| Satır \| `OFF` \| `NOT` \| `OFF` taban oranı | 2 |
| T08 | 168 | 1.5 Resmî test kümesi… | Açılış \| Sonuç | 2 |
| T09 | 217 | 1.7 Birincil değerlendirme ölçütü | Ölçüt \| Neden birlikte raporlanıyor | 4 |
| T10 | 256 | Bu bölümde kullanılan kaynakların özeti | Kaynak dosya \| Sağladığı değerler | 8 |

### `report/02_yontem.md` — 5 tables, 27 body rows

| # | Line | Under | Header row | Body rows |
|---|---:|---|---|---:|
| T11 | 17 | 2.1 Model ve eğitim yapılandırması | Hiperparametre \| Değer | 13 |
| T12 | 137 | 2.4.1 Veri rollerinin ayrılması | Kaynak \| İzin verilen kullanım | 3 |
| T13 | 152 | 2.4.2 …gizleme ailelerinin ayrıklığı | Aile \| Kullanım \| İşleçler | 2 |
| T14 | 187 | 2.4.3 Türetme kaynağının ayrılması… | (boş) \| Kat dışı (eğitim) \| Geliştirme | 3 |
| T15 | 232 | 2.5 Ön kayıt uygulaması | Belge \| Sabitlenen karar | 6 |

### `report/04_bulgular.md` — 19 tables, 86 body rows

| # | Line | Under | Header row | Body rows |
|---|---:|---|---|---:|
| T16 | 14 | 4.1 Birincil ölçüt — özet | Sistem \| `lexicon_free` `OFF`-duyarlılık (geliştirme) \| (resmî test) | 4 |
| T17 | 51 | Genel başarım | Sistem \| Makro-F1 \| %95 GA \| `OFF`-duyarlılık \| `OFF`-kesinlik | 7 |
| T18 | 77 | Dilimler arası duyarlılık farkı | (boş) \| `lexicon_hit` \| `lexicon_free` \| **Fark** \| %95 GA \| Sıfırı dışlıyor mu | 3 |
| T19 | 121 | Eşikten bağımsız karşılaştırma… | Dilim (geliştirme) \| Taban oran \| **ROC-AUC** \| %95 GA \| `OFF`-duyarlılık (0,5) | 3 |
| T20 | 148 | Eşikten bağımsız karşılaştırma… | Dilim \| Sınıf \| n \| Ortalama \| Medyan \| ≤ 0,5 payı | 4 |
| T21 | 176 | 4.3 Açık iki yönlüdür | Dilim (geliştirme) \| Altın `NOT` \| Yanlış pozitif \| Yanlış pozitif oranı | 2 |
| T22 | 210 | Terimsel açıklama… | Terim \| Tanım \| Temel modelde değer | 3 |
| T23 | 301 | Yanlış negatifler… | Örneklem \| MISLABEL \| IMPLICIT \| EVASION \| AMBIG \| Yanlış etiket oranı | 2 |
| T24 | 349 | Yanlış pozitifler: küfrün işlevi | İşlev \| Sayı | 8 |
| T25 | 393 | 4.5 Dilim tanımının duyarlılık denetimi | (boş) \| `lexicon_hit` duyarlılık \| `lexicon_free` duyarlılık \| Fark \| %95 GA | 2 |
| T26 | 419 | 4.6 Müdahalenin bileşen düzeyindeki etkisi | Ölçüt (geliştirme) \| Temel \| +1a \| +1a+1b \| +1a+1b+D | 8 |
| T27 | 433 | 4.6 Müdahalenin bileşen düzeyindeki etkisi | (boş) \| Makro-F1 \| `lexicon_free` `OFF`-duyarlılık \| `lexicon_hit` `OFF`-duyarlılık | 3 |
| T28 | 471 | Kazancın mekanizması… | Dilim \| ROC-AUC `run_raw` \| ROC-AUC `+1a+1b+D` \| **ΔAUC** \| %95 GA \| Ön kayıtlı karar | 2 |
| T29 | 502 | 4.7 Sistem düzeyindeki etki ve bedeller | Ölçüt (resmî test) \| Fark (+1a+1b+D − temel) \| %95 GA \| Sıfırı dışlıyor mu | 5 |
| T30 | 545 | Ön kayıtta uyarılan takas… | (boş) \| `lexicon_hit` \| `lexicon_free` \| Dilim farkı | 2 |
| T31 | 572 | 4.8 Kalibrasyon | (boş) \| BERTurk (temel) \| +1a+1b+D | 7 |
| T32 | 612 | 4.9 Seçici tahmin ve çalışma noktaları | Kapsam \| Makro-F1 \| Hata oranı \| `OFF`-duyarlılık | 6 |
| T33 | 653 | Devretme dilim körüdür… | Çalışma noktası (resmî test) \| `lexicon_free` devretme oranı \| `lexicon_hit` devretme oranı \| `lexicon_free`'nin kuyruktaki payı | 2 |
| T34 | 678 | 4.10 Bulguların özeti | # \| Bulgu \| Kanıt | 13 |

### `report/05_sinirliliklar.md` — 2 tables, 23 body rows

| # | Line | Under | Header row | Body rows |
|---|---:|---|---|---:|
| T35 | 108 | Aynı düzeltme, iki ölçütte zıt yön… | (boş) \| Duyarlılık farkı \| ROC-AUC farkı | 3 |
| T36 | 406 | 5.14 Özet | # \| Sınırlılık \| Ölçülen büyüklük \| Durum | 20 |

**COUNT: 36 tables**, 171 body rows, 207 rendered rows including headers.
Distribution is lopsided — `04_bulgular.md` holds 19 of the 36.

---

## 8. Demo — section 3.3 evidence

Read from `demo/app.py` (421 lines, 17,306 bytes) and its inline CSS/JS.

### (a) The actual user-facing flow

**Architecture:** confirmed a single page served by `BaseHTTPRequestHandler` /
`HTTPServer` with `protocol_version = "HTTP/1.1"`. CSS and JS are inlined into one
f-string in `render_page()`. **One screen, no routes other than `/` and
`/api/classify`. Matches the claim.**

**What the user sees on load** — from `render_page()`:

1. `<h1>` — "NSosyal B* — Turkish offensive language, three systems side by side"
2. A `.sub` line stating it runs fully offline, local checkpoints only, and the
   device in use
3. A `<textarea id="inp">` with placeholder `Türkçe bir metin yapıştırın…`
4. A `<button onclick="run()">` labelled **"Classify (Ctrl+Enter)"**
5. An empty `<div id="out">`
6. `<h2>` "Examples from our analysed rows", then the 8 examples in two labelled
   family groups, each a small button
7. A `<footer>` giving the review-layer threshold, its provenance, and the
   test-set coverage/F1/error/lift figures

**What the user inputs:** free Turkish text into the textarea, or one click on an
example button which injects that row's text.

**What happens on submit:** `run()` POSTs `{text: …}` as JSON to `/api/classify`.
Server side, `classify()` runs `clean_input()` (control-character strip, 4,000-char
truncation, empty rejection, a flag if the text has no alphanumeric characters),
then three systems in sequence — `keyword_decision()` via `lexicon.hit_root`, and
`model_decision()` for `raw` and `1a1b_d` under `torch.no_grad()`. The response is
an **HTML fragment**, injected via `r.innerHTML`.

**What is returned on screen** — from `render_result()`: a 4-column table, one row
per system:

```
| system | decision | P(OFF) | detail |
```

with `keyword filter` / `BERTurk raw` / `BERTurk +1a+1b+D`. The decision cell is a
`<span class='tag'>` inside a `<td class='OFF'>` or `class='NOT'`. The keyword
row's detail lists which lexicon roots fired (display only) or "no lexicon root
matched"; the model rows show `P(OFF) = 0.xxxx`. Below the table, a
character/token count line noting the model sees only the first 128 wordpieces.

**How the deferral path renders.** Selective prediction uses the **raw** model
only:

```python
conf = max(p, 1.0 - p)
auto = conf >= op["threshold"]
out["selective"] = {..., "route": "AUTO-RESOLVE" if auto else "DEFER TO REVIEW",
                    "decision": out["systems"]["raw"]["decision"] if auto else None,
                    "margin": conf - op["threshold"]}
```

It renders as a single `<div class='route'>` — a bordered box, not a separate
view, not a colour change, not an icon:

> Review layer at the 90.2%-coverage operating point → **AUTO-RESOLVE** as **OFF**
> decision confidence max(p, 1-p) = `0.xxxx`, threshold `0.6632`, margin `+0.xxxx`

On deferral the `as <b>{decision}</b>` clause is **omitted entirely** — the box
reads only **DEFER TO REVIEW**, deliberately withholding the label. The visual
difference between the two paths is the text string and the presence or absence of
that clause. `.route` has one style; there is no distinct styling, colour, or
emphasis for the deferred state.

### (b) Accessibility and semantics — **this partially contradicts the stated answer**

The stated answer was that accessibility "was never a design goal." That is
consistent with the intent, but **the code does contain several
accessibility-relevant constructs**, so a flat "none" would be wrong.

**PRESENT:**

| Construct | Where | Evidence |
|---|---|---|
| `lang="tr"` on `<html>` | app.py:267 | `<!doctype html><html lang="tr">` |
| `<meta charset="utf-8">` | app.py:267 | |
| viewport meta | app.py:268 | `width=device-width, initial-scale=1` |
| Semantic landmarks | app.py:269, 283 | `<main>`, `<footer>` |
| Heading hierarchy | app.py:270, 278 | one `<h1>`, then `<h2>` — correct order, no skips |
| Real interactive elements | app.py:274–275 | `<textarea>` and `<button>`, not click-handled `<div>`s — natively focusable and keyboard-operable |
| Keyboard handler | app.py:206–208 | `keydown` listener firing `run()` on Ctrl/Cmd+Enter |
| Colour-scheme support | app.py:160, 165 | `:root { color-scheme: light dark; }` and `@media (prefers-color-scheme: dark)` |
| Relative units throughout | CSS block | `rem` sizing, `max-width: 60rem` |
| Output escaping | throughout | `html.escape()` on every interpolated value |

**ABSENT — searched for explicitly, zero occurrences:**

- **No ARIA attribute of any kind.** No `aria-live` on `<div id="out">`, which is
  the one place it would matter: results are injected asynchronously and a screen
  reader is given no announcement.
- **No `<label>`.** The textarea is identified only by a `placeholder`, which is
  not an accessible name.
- **No focus management.** No `.focus()` call, no `tabindex`, no focus move to
  results after classification.
- **No `:focus` or `:focus-visible` style.** `button:hover` is styled; the focus
  state is not — so keyboard users get only the browser default, and
  `border: 1px solid #8886` is a translucent border.
- **No `alt` attribute** (no images exist).
- **No deliberate contrast choice.** Colours are `#1a1a1a` on `#fbfbfa` (light)
  and `#e6e6e6` on `#16181c` (dark). Both happen to pass WCAG AA for body text,
  but nothing in the code or comments records contrast as a consideration;
  secondary text is set with `opacity: .7`, `.65`, `.8` and `.75`, which reduces
  effective contrast without any stated floor.

**Precise verdict: the demo has correct document semantics and one keyboard
shortcut, but no assistive-technology support.** The semantics look like the
by-product of writing plain, unfussy HTML rather than evidence of accessibility
work — consistent with the stated intent, but a flat "no accessibility features
exist" would be inaccurate if a jury inspected the source.

### (c) `demo/examples.json` — 8 rows

**ROW TEXT IS PRESENT IN THIS FILE.** Each row carries a `text` field holding the
corpus tweet. **It is not reproduced here.** Fields per row: `family`, `gold`,
`id`, `note`, `phase02_tag`, `slice`, `text`.

| # | gold | phase02_tag | slice | family | expected outcome (`note` field) |
|---|---|---|---|---|---|
| 1 | OFF | IMPLICIT | lexicon_free | implicit offense, no profanity token | gold OFF; raw BERTurk predicted NOT — a false negative |
| 2 | OFF | IMPLICIT | lexicon_free | implicit offense, no profanity token | gold OFF; raw BERTurk predicted NOT — a false negative |
| 3 | OFF | IMPLICIT | lexicon_free | implicit offense, no profanity token | gold OFF; raw BERTurk predicted NOT — a false negative |
| 4 | OFF | IMPLICIT | lexicon_free | implicit offense, no profanity token | gold OFF; raw BERTurk predicted NOT — a false negative |
| 5 | NOT | NONDIR | lexicon_hit | profanity token present, no offensive act | gold NOT; raw BERTurk predicted OFF — a false positive |
| 6 | NOT | FILL | lexicon_hit | profanity token present, no offensive act | gold NOT; raw BERTurk predicted OFF — a false positive |
| 7 | NOT | META | lexicon_hit | profanity token present, no offensive act | gold NOT; raw BERTurk predicted OFF — a false positive |
| 8 | NOT | NEG | lexicon_hit | profanity token present, no offensive act | gold NOT; raw BERTurk predicted OFF — a false positive |

Four false negatives, four false positives; four `lexicon_free`, four
`lexicon_hit`; balanced by construction.

**Additional finding, reported because it is factual and was found while
checking:** this file **is tracked in git** —

```
$ git ls-files --error-unmatch demo/examples.json
demo/examples.json
```

— while `.gitignore` excludes per-row prediction dumps on the stated grounds that
they carry corpus text:

```
32:# ...with one exception, listed last so it wins: any per-row prediction dump
33:# carries corpus text (licensing, briefing S5) and is large. Analyses read them
35:results/**/*predictions*.csv
```

Eight rows of corpus text are therefore committed to the repository under a rule
written to keep corpus text out of it.

### (d) Screenshots

**DOES NOT EXIST.** Item 3's search covers the whole tree; there is no `.png`,
`.jpg`, `.jpeg`, `.gif`, `.svg` or `.pdf` file anywhere outside `.venv`/`.git`,
tracked or untracked. No screenshot of the demo exists.

---

## 9. Repo access

```
$ git remote -v
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (fetch)
origin	https://github.com/MusaabAlt/nsosyal-bstar.git (push)
```

**Remote URL: `https://github.com/MusaabAlt/nsosyal-bstar.git`**

**Private — confirmed.** `git ls-remote` succeeded, but that is not evidence of
publicness: `git config --get credential.helper` returns `manager`, so it
authenticated from the cached credential. The unauthenticated checks are
authoritative:

```
GitHub API  /repos/MusaabAlt/nsosyal-bstar  -> HTTP 404
GitHub HTML page                            -> HTTP 404
```

A 404 on both is GitHub's response for a private repository to an unauthenticated
client. **Confirmed private.**

**Remote is behind local:**

```
$ git ls-remote origin HEAD
98e27c1a96b163a12997aeccb4d6f0817bfe1ff4	HEAD
local  HEAD: c67eabe78920ce69c37cf0e3baae6b553a121ba0
```

The phase-10 commit is not on the remote.

**README exists.** `README.md`, 6,133 bytes, **131 lines, 804 words**.

```
L1  NSosyal B* — Turkish adversarial toxicity detection + review triage
L2    Status
L2    Layout
L2    Setup
L2    Running on Kaggle / Colab
L2    Ground rules
L2    Data sources
```

**Reproduction guide / runbook: PARTIAL — one exists, for phase 01 only.**

`notebooks/colab_phase01_runbook.md`, 16,718 bytes, 2,236 words:

```
L1  Colab runbook — session rebuild + phase run cells
L2    Prerequisites (do these once, outside the notebook)
L2    Section 1 — one-paste rebuild
L2    Section 2 — the same seven cells, separately
L2    Section 3 — run cells (launch only when a phase is open)
L2    Section 4 — hardware: T4 is about 3x slower than L4
L2    Section 5 — failures actually hit in this project
```

It covers environment rebuild, Drive mount, pinned versions, split loading, and
phase-01/03 launch cells. **No end-to-end guide covering phases 02–09 exists.**
`README.md#Setup` and `#Running on Kaggle / Colab` cover environment only.

**Phases index: DOES NOT EXIST as a standalone file.** No `INDEX.md`, no
`phases/README.md`. The nearest thing is the pre-registration table in
`docs/PROJECT_HISTORY.md:552-557`, which lists six phase specs with their commit
SHAs — but it indexes pre-registrations, not the phase set, and omits
`phases/07_report.md` and `phases/10_sablon_mapping.md`.

Two handoff documents exist: `docs/HANDOFF.md` (860 words) and
`docs/handoff_2026_08_15.md` (1,670 words).

---

## 10. File map

### `phases/` — 7 files

```
-rw-r--r-- 1 HP 197609 14405 Aug 15 16:39 01_baseline_diagnosis.md
-rw-r--r-- 1 HP 197609  6028 Aug 15 20:33 03_defense_design.md
-rw-r--r-- 1 HP 197609  6907 Aug 16 13:36 04_calibration.md
-rw-r--r-- 1 HP 197609 11381 Aug 16 14:53 07_report.md
-rw-r--r-- 1 HP 197609  8867 Aug 17 13:02 08_lexical_analysis.md
-rw-r--r-- 1 HP 197609 24861 Aug 17 16:19 09_deeper_analysis.md
-rw-r--r-- 1 HP 197609 36032 Aug 17 18:20 10_sablon_mapping.md
```

| File | Bytes | Words |
|---|---:|---:|
| `phases/01_baseline_diagnosis.md` | 14,405 | 2,175 |
| `phases/03_defense_design.md` | 6,028 | 896 |
| `phases/04_calibration.md` | 6,907 | 1,095 |
| `phases/07_report.md` | 11,381 | 1,725 |
| `phases/08_lexical_analysis.md` | 8,867 | 1,379 |
| `phases/09_deeper_analysis.md` | 24,861 | 3,845 |
| `phases/10_sablon_mapping.md` | 36,032 | 5,666 |

Numbering gaps: no `02`, `05`, `06`. Seven files, numbered to 10.

### `results/` — 10 directories

```
[results]
    day1_report.json  (671 bytes)
    day1_report_rerun.json  (686 bytes)
[results/01_baseline_berturk]
    classification_report.txt  (2005 bytes)
    dev_predictions.csv  (736591 bytes)
    metrics.json  (5524 bytes)
    results_log_row.md  (1900 bytes)
    run_config.json  (2330 bytes)
[results/02_failure_analysis]
    findings.md  (12180 bytes)
    fn_tags.json  (4372 bytes)
    fp_function_tags.json  (6136 bytes)
    slice_sensitivity.json  (2406 bytes)
[results/03_defense]
    augmentation_review.json  (1023 bytes)
    comparison.json  (4543 bytes)
    findings.md  (8255 bytes)
    train_oof_summary.json  (1111 bytes)
[results/03_defense/run_1a]
    metrics.json  (3825 bytes)
[results/03_defense/run_1a1b]
    metrics.json  (3832 bytes)
[results/03_defense/run_1a1b_d]
    metrics.json  (3840 bytes)
[results/03_defense/run_raw]
    metrics.json  (3271 bytes)
[results/04_calibration]
    calibration.json  (46790 bytes)
    findings.md  (10932 bytes)
[results/05_final_test]
    TEST_SET_OPENED.json  (176 bytes)
    TEST_SET_SPENT.json  (901 bytes)
    findings.md  (8740 bytes)
    metrics.json  (20114 bytes)
    paired_deltas.json  (1189 bytes)
    raw_output.txt  (7464 bytes)
[results/08_lexical_analysis]
    findings.md  (17982 bytes)
    token_stats.json  (89324 bytes)
[results/09_deeper_analysis]
    (no files at this level)
[results/09_deeper_analysis/stage_1]
    findings.md  (15335 bytes)
    stage1_auc.json  (6159 bytes)
[results/09_deeper_analysis/stage_1b]
    findings.md  (8354 bytes)
    stage1b_defense_auc.json  (4203 bytes)
```

**No `test_predictions.csv` exists anywhere under `results/`.** The only
prediction dump on disk is `results/01_baseline_berturk/dev_predictions.csv` (dev,
gitignored). It was not opened for this inventory.

---

## 11. Git

```
$ git rev-parse --abbrev-ref HEAD
master

$ git rev-parse HEAD
c67eabe78920ce69c37cf0e3baae6b553a121ba0

$ git status --porcelain --untracked-files=no
[exit=0] — no output above means clean

$ git status --porcelain
[end plain]
```

**Branch: `master`. HEAD: `c67eabe78920ce69c37cf0e3baae6b553a121ba0`. Clean.**
Both forms of `git status --porcelain` returned empty at the time of the
inventory — the plain flag agreed with `--untracked-files=no`, so there was no
false dirty report in that state.

```
$ git rev-list --count HEAD
47

$ git log --oneline -5
c67eabe Phase 10: KYS sablonu coverage map — 60 check items, no drafting
98e27c1 docs/PROJECT_HISTORY.md: the complete record, including what we got wrong
1db1354 Narrow what the intervention demonstrates; apply Stage 1b to 4.6, 4.7 and 5.4
09ce5f8 Phase 09 Stage 1b: the recall gain is threshold crossing, not better ranking
6b4a451 Narrow the central claim in the report; Stage 1b coded but BLOCKED
```

**Commit count: 47.**

**`phases/10_sablon_mapping.md`: COMMITTED.**

```
$ git ls-files --error-unmatch phases/10_sablon_mapping.md
phases/10_sablon_mapping.md

introduced by:
c67eabe78920ce69c37cf0e3baae6b553a121ba0  Phase 10: KYS sablonu coverage map — 60 check items, no drafting

word count (committed blob):  5666
word count (working tree):    5666
```

**SHA `c67eabe78920ce69c37cf0e3baae6b553a121ba0`, 5,666 words.** Blob and working
tree agree. The commit is local only — `origin/master` is at `98e27c1`.

---

## BLOCKERS

Only items that would prevent a compliant 24 August submission: format, missing
tooling, page overrun.

1. **No path from markdown to the required DOCX/KYS format.** Four `.md` files; no
   pandoc on PATH, no python-docx importable, no Makefile, no build script, no
   converter of any kind in the tree. The template mandates Arial 12 pt, Arial
   Black 14 pt headings, 1.15 spacing, justified text, 2.5 cm margins — none of
   which markdown carries. Conversion is currently manual with no tooling.

2. **Page budget is between +1.0 and +7.2 pages of headroom, before tables.** The
   estimate of 19.8–26.0 pages excludes 36 tables / 207 rendered rows, which add
   ≥ 4.7 pages before any cell wraps. Taking the pessimistic end plus tables
   exceeds the 27 pages available after the 3 mandatory pages. Nothing yet written
   for the team section, timeline, bibliography, cover or contents is counted in
   either figure.

3. **No bibliography exists, and section 3 of the report is absent.** `report/` has
   files 01, 02, 04, 05 — no section-3 file. There is no reference list in any
   format, and no `[n]` in-text citation anywhere in the drafts. The template
   requires a dedicated Kaynakça page with specified digital and academic formats
   and bracketed in-text citations.

4. **No figures and no capability to produce them.** Zero image files in the tree,
   and matplotlib is not importable. Every quantitative claim currently renders as
   a table.

5. **The repository is private (HTTP 404 unauthenticated) and the report contains
   no repository link.** The submission asks for a repo link shareable for jury
   review in section 3.1; following the current remote URL without credentials
   returns 404.

6. **The phase-10 commit is not pushed.** Local `master` is at `c67eabe`;
   `origin/master` is at `98e27c1`.
