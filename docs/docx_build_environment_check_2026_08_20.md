# Environment Check — Document Build Pipeline

**Date:** 2026-08-20
**Scope:** Read-only inspection plus tool-availability checks. Nothing built, nothing installed.
**Working tree:** `git status --porcelain --untracked-files=no` was empty before and after
every check in sections A–C — identical. No file was created, edited, moved or deleted
during the inspection itself. (This report file is a subsequent, explicitly requested addition.)

---

## A. WHAT IS ON THIS MACHINE

### A1. pandoc — **DOES NOT EXIST**

```
$ pandoc --version
/usr/bin/bash: line 1: pandoc: command not found          (exit 127)
```

```
PS> pandoc --version
The term 'pandoc' is not recognized as the name of a cmdlet, function, script file,
or operable program.
PS> Get-Command pandoc  ->  NOT FOUND
$ where.exe pandoc      ->  INFO: Could not find files for the given pattern(s).
```

Also checked the four usual install locations — `C:\Program Files\Pandoc\`,
`C:\Program Files (x86)\Pandoc\`, `%LOCALAPPDATA%\Pandoc\`,
`C:\ProgramData\chocolatey\bin\` — all absent.

**No version number to report; pandoc is not installed.**

### A2. python-docx in `.venv` (Python 3.14) — **NOT IMPORTABLE**

```
$ ./.venv/Scripts/python.exe --version
Python 3.14.0

$ ./.venv/Scripts/python.exe -c "import docx; print(docx.__version__)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import docx; print(docx.__version__)
    ^^^^^^^^^^^
ModuleNotFoundError: No module named 'docx'          (exit 1)
```

`.venv` holds 43 packages (torch, transformers, scikit-learn, pytest, …) — no
`python-docx`, no `lxml`.

**However** — python-docx **does** exist on this machine, in the system Python 3.10:

```
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe
3.10.0 (tags/v3.10.0:b494f59, Oct  4 2021, 19:00:18) [MSC v.1929 64 bit (AMD64)]
C:\Users\HP\AppData\Local\Programs\Python\Python310\lib\site-packages\docx\__init__.py
1.1.2
```

Python 3.13 is on PATH but the directory **DOES NOT EXIST** (stale PATH entry).
Python 3.10 + python-docx 1.1.2 was used to read the template for section B.

### A3. LibreOffice / Microsoft Word

- **LibreOffice — DOES NOT EXIST.** Not in `C:\Program Files\LibreOffice\`, not in
  `Program Files (x86)`; `soffice`/`libreoffice` not on PATH (bash or PowerShell).
- **Microsoft Word — PRESENT.**

```
C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE
ProductName    : Microsoft Office
ProductVersion : 16.0.20228.20190
FileVersion    : 16.0.20228.20190
Word.Application ProgID: registered (COM automation available)
```

Verification of an output .docx is therefore possible, but **only through Word** —
interactively, or scripted via COM. There is no headless `soffice --convert-to pdf`
path for automated visual diffing.

### A4. OS and shell

```
MINGW64_NT-10.0-19045 Musaab 3.6.6-1cdd4371.x86_64 2026-01-15 22:20 UTC x86_64 Msys
BASH_VERSION=5.2.37(1)-release
Microsoft Windows [Version 10.0.19045.6456]      (Windows 10 Enterprise, 22H2)
```

Two shells available: Git Bash (MSYS2/MINGW64) and Windows PowerShell 5.1.

---

## B. THE TEMPLATE

### B1. The template is **NOT** at the repository root

Full listing of `C:\Projects\NSosyal` contains **no `.docx`, `.dotx`, `.doc`, `.odt`
or `.rtf` file** — 12 Python files, `README.md`, `repo_conventions.md`, `config.py`,
`conftest.py`, `requirements.txt`, and the directories
`.claude .git .idea .pytest_cache .venv __pycache__ data demo docs legacy notebooks
phases report results src tests`.

A repo-wide search confirms it:

```
$ find . (excl .git/.venv) -iname "*.docx" -o -iname "*.dotx" -o ... ->  (no results)
$ git ls-files | grep -iE '\.(docx|dotx|doc|dot|odt|rtf)$'          ->  (no results)
```

So the premise "the project lead has placed the KYS report template at the repository
root" is **not true of this working copy.** The tracked file `phases/10_sablon_mapping.md`
records the template's provenance, which located the real file:

```
| File | NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx |
| Location at time of reading | C:\Users\HP\Downloads\ (not in the repository) |
```

That file still exists:

| | |
|---|---|
| **Exact filename** | `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` |
| **Location** | `C:\Users\HP\Downloads\` — **not** the repo root |
| **Size** | 2,505,567 bytes |
| **sha256** | `5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a` |
| **mtime** | 2026-08-17 15:56 |

Note the name is **NSosyal İnovasyon 2026 – Proje Teknik Raporu**, not "KYS" — no file
named `*kys*` exists anywhere in the repo, Downloads, Documents, or Desktop. "KYS şablonu"
appears to be the internal shorthand used in `phases/10_sablon_mapping.md`. Everything in
B3/B4 below is read from the file above.

### B2. Tracked in git? — **NO**

```
$ git ls-files --error-unmatch NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx
error: pathspec '...' did not match any file(s) known to git
```

It is not tracked, not staged, and not even inside the working tree. `.gitignore` contains
no rule mentioning `docx` — the file is simply absent. A build that consumes it depends on
a file living in the user's Downloads folder, outside version control.

### B3. Actual format settings, read from the file

**Default paragraph font and size** — from `docDefaults/rPrDefault` in `styles.xml`:

| Setting | Value |
|---|---|
| Font (ascii / hAnsi / eastAsia / cs) | **Arial** (all four) |
| Size | **12.0 pt** (`w:sz val="24"`), complex-script 12.0 pt |

The `Normal` style itself defines **no** font and **no** size of its own — it inherits both
from `docDefaults`. So the effective body default is Arial 12 pt.

**Heading style fonts and sizes** — read from each style's `rPr`/`pPr`:

| Style | Font | Size | Bold | Space before/after (twips) |
|---|---|---|---|---|
| Normal | *(none — inherits Arial)* | *(none — inherits 12 pt)* | — | — |
| Heading 1 | **Arial Black** | **14.0 pt** | not set | 240 / 0 |
| Heading 2 | *(none — inherits Arial)* | **18.0 pt** | yes | 360 / 80 |
| Heading 3 | *(none — inherits Arial)* | **14.0 pt** | yes | 280 / 80 |
| Heading 4 | *(none — inherits Arial)* | *(none — inherits 12 pt)* | yes | 240 / 40 |
| Title | *(none — inherits Arial)* | **36.0 pt** | yes | 480 / 120 |
| Body Text | **NOT DEFINED in this file** | — | — | — |

Heading 5, Heading 6 and Subtitle are also defined.

> **Oddity in the template, not a reading error:** **Heading 2 (18 pt) is larger than
> Heading 1 (14 pt)**, and only Heading 1 overrides the font family (Arial Black).
> That inversion is what the file actually contains.

**Line spacing** — two different values are present, and they disagree:

- `docDefaults/pPrDefault/spacing`: `line="360" lineRule="auto"`, `after="160"`
  → **1.5 lines**, 8 pt space after.
- Actual body paragraphs: 37 non-empty paragraphs carry an **explicit
  `line_spacing = 1.15`**; 30 carry none (inheriting 1.5).

The document default is 1.5 but most real paragraphs in the template body override to 1.15.
Both are in the file; which one the competition intends cannot be determined from the file.

**Paragraph alignment:**

- No `jc` (alignment) element in `docDefaults`, and none in `Normal` or any Heading style —
  so no style-level alignment is defined.
- In the actual body: **45 paragraphs explicitly JUSTIFY**, 22 with no explicit
  alignment (→ left).

**Page margins, all four** — from `sectPr` (single section, portrait):

| Margin | Value |
|---|---|
| Top | **2.50 cm** |
| Bottom | **2.50 cm** |
| Left | **2.50 cm** |
| Right | **2.50 cm** |
| Header distance | 1.25 cm |
| Footer distance | 1.25 cm |
| Gutter | 0.00 cm |

**Page size:** 21.00 cm × 29.70 cm — **A4**, portrait, one section, `start_type=NEW_PAGE`.

Template body content: 67 non-empty paragraphs (56 `Normal`, 11 `Heading 1`),
**18 tables**, 13 pages, 2,174 words per its own `app.xml`.

### B4. Document properties — **one personal name present**

Full `docProps/core.xml`:

```xml
<cp:coreProperties ...><cp:lastModifiedBy>Mustafa Furat</cp:lastModifiedBy>
<cp:revision>4</cp:revision>
<dcterms:created  xsi:type="dcterms:W3CDTF">2026-08-13T09:17:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-08-13T09:20:00Z</dcterms:modified>
</cp:coreProperties>
```

| Field | Value |
|---|---|
| author | `''` (empty) |
| **last_modified_by** | **`'Mustafa Furat'`** ← **personal name** |
| title / subject / category / comments / keywords | `''` (all empty) |
| content_status / identifier / language / version | `''` (all empty) |
| created | 2026-08-13 09:17 UTC |
| modified | 2026-08-13 09:20 UTC |
| revision | 4 |
| **Company** (app.xml) | `''` (empty element) |
| Manager | **ABSENT** |
| Application | `Microsoft Office Word`, AppVersion 16.0000 |
| Template | `Normal` |

**One field carries a personal name: `cp:lastModifiedBy = "Mustafa Furat"`.** It is the
template author's name, not a team member's — but it matters directly: **if the build uses
this file as a reference.docx or as a base document, that string is inherited into the
output unless explicitly cleared.** `dc:creator` (author) is not merely empty, it is
*absent* from the XML, which some tools repopulate on save. Any build must set core
properties explicitly rather than trusting them to stay blank.

---

## C. WHAT WILL BE RENDERED

### C1. Size and heading tree

| File | `wc -w` | `wc -c` | Headings |
|---|---:|---:|---:|
| `report/01_veri_ve_deney_kurgusu.md` | 1,709 | 14,832 | 9 |
| `report/02_yontem.md` | 2,253 | 20,547 | 15 |
| `report/04_bulgular.md` | 5,052 | 42,762 | 23 |
| `report/05_sinirliliklar.md` | 2,923 | 25,975 | 21 |
| **total** | **11,937** | **104,116** | **68** |

Headings are ATX only — no setext headings, and none found inside fenced blocks.

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

Two headings in `05` contain **inline code spans** (`lexicon_hit`, `lexicon_free`) —
relevant to C3, since heading-level inline code needs a character style to survive
conversion.

### C2. Tables — **36 tables, 171 data rows**

| File | Tables | Header rows | Data rows | Max columns |
|---|---:|---:|---:|---:|
| `01_veri_ve_deney_kurgusu.md` | 10 | 10 | 35 | 5 |
| `02_yontem.md` | 5 | 5 | 27 | 3 |
| `04_bulgular.md` | 19 | 19 | 86 | 6 |
| `05_sinirliliklar.md` | 2 | 2 | 23 | 4 |
| **TOTAL** | **36** | **36** | **171** | **6** |

Since "rows" is ambiguous, all three counts: **171** data rows (body only); **207**
including header rows; **243** if the separator lines are also counted.
The headline figure: **36 tables / 171 data rows**.

All are GFM pipe tables. Widest is 6 columns (in `04_bulgular.md`) — that fits A4 portrait
at 2.5 cm margins (16 cm text width), though 6 columns of Turkish text will be tight.

### C3. Conversion-risk constructs

| Construct | 01 | 02 | 04 | 05 | Present? |
|---|---:|---:|---:|---:|---|
| Images | 0 | 0 | 0 | 0 | **No — none anywhere** |
| Footnotes | 0 | 0 | 0 | 0 | **No** |
| Fenced code blocks | 0 | 0 | 0 | 0 | **No** |
| Indented (4-space) code | 0 | 0 | 0 | 0 | **No** |
| Nested lists | 0 | 0 | 0 | 0 | **No** |
| HTML blocks/tags | 0 | 0 | 0 | 0 | **No** |
| Math (inline, display, escaped-paren) | 0 | 0 | 0 | 0 | **No** |
| Links (inline, autolink, bare URL) | 0 | 0 | 0 | 0 | **No** |
| **Block quotes** | **10** | **4** | **19** | **2** | **YES — all four files, 35 lines** |
| **Inline code** | **78** | **70** | **202** | **61** | **YES — all four files, 411 spans** |

Only two risk constructs are actually present:

1. **Block quotes — 35 lines across all four files.** These map to Word's
   `Quote`/`Intense Quote` style. The template defines **neither** — it has only Normal,
   Title, Subtitle, and Heading 1–6. A pandoc reference-docx run would emit a
   `Block Text`/`Quote` style that does not exist in the template and would fall back to an
   auto-generated one, which will not match the competition's look.
2. **Inline code — 411 spans**, including two inside headings. Maps to Word's
   `Verbatim Char`/`Code` character style — **also not defined in the template**. Same
   fallback problem, and the fallback typically injects a monospace font
   (Consolas/Courier), breaking the all-Arial requirement in 411 places.

Nothing else on the standard risk list appears. No images means no figure handling, no DPI
issues, and no `--extract-media`.

### C4. `report/03` and bracket citations

- **`report/03` — DOES NOT EXIST.** `ls report/03*` → `No such file or directory`. The
  `report/` directory contains exactly four files: `01_veri_ve_deney_kurgusu.md`,
  `02_yontem.md`, `04_bulgular.md`, `05_sinirliliklar.md`. The numbering gap at 03 is real,
  and the heading tree confirms it — sections run 1, 2, 4, 5 with no section 3 anywhere.
- **Bracket citations — count is 0.** Zero in every one of the four files. A search for
  `[Author 2024]` and `(Yazar, 2024)` styles also returned zero. There is no citation
  apparatus in these drafts at all.

---

## APPROACH

**Available today: python-docx programmatically — and only after installing python-docx
into `.venv`. Neither approach works as-is right now.**

Item by item, from what is actually on this machine:

**pandoc with the template as reference.docx — NOT AVAILABLE.** pandoc is not installed
anywhere on this machine. Beyond that, even after installing it, the reference-docx route is
a poor fit here for reasons this inspection surfaced:

- The template defines **no `Quote` and no code character style**, but the drafts contain
  35 block-quote lines and 411 inline-code spans. Pandoc would auto-generate styles that do
  not match the template.
- Pandoc's reference.docx mechanism copies styles, **not** the `sectPr`, so the A4 / 2.5 cm
  margins would need re-asserting anyway.
- The template's own line spacing is internally inconsistent (docDefaults 1.5 vs. 1.15 on
  most body paragraphs); pandoc would apply the style default, 1.5, to everything — likely
  wrong.

**python-docx programmatically — AVAILABLE, after one install.** python-docx 1.1.2 already
works on this machine under Python 3.10 and read the template cleanly (styles, `sectPr`,
core properties all parsed). It is **not** in `.venv` (Python 3.14), which is where the
build should live. This route also directly solves the problems above: you control
block-quote and inline-code rendering explicitly, you set `lastModifiedBy`/`author`
explicitly (mandatory here — the template carries **"Mustafa Furat"** in `lastModifiedBy`),
and 36 tables with a known max of 6 columns is very tractable with `add_table`.

**To unblock, one install:**

```
.venv\Scripts\python.exe -m pip install python-docx
```

That pulls `lxml` and `typing_extensions` (already present). Nothing else is required — no
pandoc, no LaTeX, no LibreOffice. **This has not been run.** One caveat worth checking at
install time: python-docx 1.1.2 predates Python 3.14, and `lxml` needs a 3.14-compatible
wheel. If pip has none, fall back to running the build under the Python 3.10 that already
has it working.

### Three findings that need a decision before any script is written

1. **The template is not in the repo and not in git.** It sits at
   `C:\Users\HP\Downloads\NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx`,
   untracked, outside the working tree. A build depending on a Downloads-folder path is not
   reproducible. It should be copied into the repo and committed.
2. **`report/03` does not exist.** Four drafts, sections numbered 1, 2, 4, 5. Either
   section 3 is unwritten or it lives elsewhere; a single .docx assembled from these four
   will have a visible gap.
3. **Verification is Word-only.** No LibreOffice means no headless `--convert-to pdf` for
   automated checking. Word 16.0.20228 with COM registered can be scripted for that, but it
   is heavier and needs a Windows session.
