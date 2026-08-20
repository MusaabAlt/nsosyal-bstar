# DOCX build pipeline — full session state

**Date:** 2026-08-20
**Repo:** `nsosyal-bstar` (`C:\Projects\NSosyal`), branch `master`
**Purpose of this file:** a complete, self-contained record of the docx build
pipeline session. If the session is lost, everything needed to resume is here —
every command run, its real output, the style definitions before and after the
change, the Word COM verification, the page count, and the open decisions.

**Headline result: the four drafts paginate at 44 pages against a 27-page body
budget — 17 pages over.**

---

## 0. Where things stand

| | |
|---|---|
| Builder | `report/build_docx.py`, 679 lines, committed at `f723b91` |
| Output | `report/build/report_draft.docx`, 2 516 060 bytes, **gitignored** |
| Page count | **44** (Word 16.0.20228) |
| Budget | 27 pages of body |
| Gap | **17 pages over** |
| Tree | clean (`git status --porcelain --untracked-files=no` is empty) |
| Branch | `master`, **ahead of `origin/master` by 3** — not pushed |

Commits added this session (oldest first):

```
fda8faf deps: pin python-docx for the report build
9a5b75c template: commit the KYS report template at the repo root
f723b91 report: docx builder that paginates the four drafts in the KYS template
```

Base commit before this session: `e0ce657 deps and demo docs: state the actual
runtime, drop gradio`.

Remote (unchanged, private):

```
origin  https://github.com/MusaabAlt/nsosyal-bstar.git (fetch)
origin  https://github.com/MusaabAlt/nsosyal-bstar.git (push)
```

Untracked files that were already present before this session and were **not**
touched:

```
?? docs/docx_build_environment_check_2026_08_20.md
?? docs/onboarding_readiness_audit_2026_08_18.md
?? docs/verification_sweep_2026_08_20.md
?? repo_conventions.md
```

### To reproduce from scratch

```bash
.venv/Scripts/python.exe -m pip install python-docx     # already done
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe report/build_docx.py
```

Then run the two PowerShell measurement scripts — their full source is in
§7.4 below (they live in the session scratchpad, which is **not** persistent).

---

## 1. Environment

```
python 3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]
python-docx 1.2.0
lxml 6.1.2
```

`.venv` is Python 3.14. Word is at
`C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE`, build
**16.0.20228** (Version 16.0). pandoc is **not** installed and was not used —
the builder writes OOXML directly through python-docx.

### 1a. Install — real output

```
$ .venv/Scripts/python.exe -m pip install python-docx

Collecting python-docx
  Downloading python_docx-1.2.0-py3-none-any.whl.metadata (2.0 kB)
Collecting lxml>=3.1.0 (from python-docx)
  Downloading lxml-6.1.2-cp314-cp314-win_amd64.whl.metadata (3.4 kB)
Requirement already satisfied: typing_extensions>=4.9.0 in c:\projects\nsosyal\.venv\lib\site-packages (from python-docx) (4.16.0)
Downloading python_docx-1.2.0-py3-none-any.whl (252 kB)
Downloading lxml-6.1.2-cp314-cp314-win_amd64.whl (4.1 MB)
   ---------------------------------------- 4.1/4.1 MB 3.0 MB/s eta 0:00:00
Installing collected packages: lxml, python-docx

Successfully installed lxml-6.1.2 python-docx-1.2.0
```

**The feared failure did not occur.** lxml ships a prebuilt
`cp314-cp314-win_amd64` wheel, so there was no source build and no fallback to
the Python 3.10 interpreter.

Import verified rather than assumed:

```
$ .venv/Scripts/python.exe -c "import docx, lxml.etree, sys; ..."
python 3.14.0 ...
python-docx 1.2.0
lxml 6.1.2
Document() ok, styles: 164
```

> **Correction to the earlier environment check.** That check recorded
> python-docx **1.1.2** under Python 3.10. `.venv` resolved **1.2.0**. The two
> interpreters now carry different versions. The build runs on 1.2.0. Decided:
> keep 1.2.0 and the `>=1.2` floor.

### 1b. `requirements.txt`

Appended (new build-only section, matching the file's existing floor-pin style):

```
# --- Report build only; not needed to train, evaluate or run the demo ---
# report/build_docx.py opens the KYS template as a base document and writes
# report/build/report_draft.docx. Resolved 2026-08-20 in .venv on Python 3.14:
# python-docx 1.2.0, pulling lxml 6.1.2 (a cp314 wheel exists, no source
# build). Note this is NOT the 1.1.2 that the Python 3.10 interpreter carries.
python-docx>=1.2
```

### 1c. Template committed

| | |
|---|---|
| path | `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` (repo root) |
| size | 2 505 567 bytes |
| sha256 | `5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a` |
| commit | `9a5b75c` |
| blob | `a4186a2006b22c1444d3f27aa9f9bf6f966bd59f` |

`.gitattributes` sets `* -text`, so no EOL conversion occurred and the digest is
verifiable anywhere:

```
$ git show HEAD:NSosyal_..._eDrmR.docx | sha256sum
5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a
$ sha256sum NSosyal_..._eDrmR.docx
5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a
```

**Process note.** The first `git add requirements.txt` swept up the
already-staged `.docx` with it, so the template briefly landed inside the deps
commit under the wrong message. Split with `git reset --soft HEAD~1` +
`git restore --staged` before anything was pushed; the worktree file was never
touched and its sha256 was re-verified after the split. The intermediate hashes
are gone and nothing reachable was lost.

### 1d. Tree clean after step 1

```
$ git status --porcelain --untracked-files=no
(empty)
```

---

## 2. The template, as read from the file

Package parts: `word/document.xml`, `styles.xml`, `numbering.xml`,
`settings.xml`, `header1.xml`, `theme/theme1.xml`, `fontTable.xml`,
`webSettings.xml`, `endnotes.xml`, `footnotes.xml`,
`word/fonts/font1–5.odttf` (5 embedded fonts), `word/media/image1.jpg`,
`word/media/image2.jpeg`, `docProps/core.xml`, `docProps/app.xml`.

### 2.1 docDefaults

```xml
<w:docDefaults>
  <w:rPrDefault><w:rPr>
    <w:rFonts w:ascii="Arial" w:eastAsia="Arial" w:hAnsi="Arial" w:cs="Arial"/>
    <w:sz w:val="24"/><w:szCs w:val="24"/>
    <w:lang w:val="tr" w:eastAsia="tr-TR" w:bidi="ar-SA"/>
  </w:rPr></w:rPrDefault>
  <w:pPrDefault><w:pPr>
    <w:spacing w:after="160" w:line="360" w:lineRule="auto"/>
  </w:pPr></w:pPrDefault>
</w:docDefaults>
```

Arial 12 pt (sz 24 half-points), **line spacing 1.5** (`w:line=360`), 160 twips
after each paragraph.

### 2.2 sectPr

```xml
<w:sectPr>
  <w:headerReference w:type="default" r:id="rId8"/>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417"
           w:header="708" w:footer="708" w:gutter="0"/>
  <w:pgNumType w:start="1"/>
  <w:cols w:space="708"/>
</w:sectPr>
```

A4 portrait (11906 × 16838 twips = 21.0 × 29.7 cm), all four margins 1417 twips
= 2.50 cm. `header1.xml` is **empty** — no text runs, no image — so the two
media files were referenced from the body and are now unreferenced (harmless;
they inflate the output by ~2.4 MB along with the embedded fonts).

Body child census before stripping: `{'p': 144, 'tbl': 18, 'sdt': 1, 'sectPr': 1}`.
The `sdt` is a content control that python-docx's `paragraphs`/`tables`
collections would **not** have seen — this is why the strip removes raw body
children rather than iterating those collections.

### 2.3 Style inventory — the template is Turkish-localised

styleIds are `Balk1`…`Balk6`, `KonuBal` (Title), `Altyaz` (Subtitle),
`NormalTablo`. python-docx matches on `w:name` (`heading 1`, …), so
`doc.styles['Heading 1']` resolves correctly.

Paragraph styles: Normal, Heading 1–6, Title, Subtitle.
Character styles: Default Paragraph Font only.

**Table styles — a finding.** Only two are named:

| styleId | w:name | notes |
|---|---|---|
| `NormalTablo` | `Normal Table` | default, `w:semiHidden`, cell margins 0/108/0/108 |
| `TableNormal` | `TableNormal` | custom, cell margins 100 all round |
| `a`, `a0` … `af0` | **none** | 18 anonymous styles, `basedOn TableNormal`, band sizes only |

**Not one table style in the template defines `tblBorders`** — checked
recursively, including inside conditional `w:tblStylePr` blocks. There is no
"Table Grid". Consequence in §5.

### 2.4 docProps

```xml
<!-- docProps/core.xml -->
<cp:coreProperties>
  <cp:lastModifiedBy>Mustafa Furat</cp:lastModifiedBy>
  <cp:revision>4</cp:revision>
  <dcterms:created  xsi:type="dcterms:W3CDTF">2026-08-13T09:17:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2026-08-13T09:20:00Z</dcterms:modified>
</cp:coreProperties>
```

`dc:creator` is **absent**, not empty — confirming the concern that some tools
repopulate it from the OS user on save.

`docProps/app.xml` carries no personal name but stale template stats
(`Pages 13`, `Words 2174`, `Company` empty). python-docx does not touch
app.xml; Word refreshes it on save, and the build never saves from Word.

---

## 3. Source drafts — construct census

```
                     lines  words   bytes
01_veri_ve_deney_kurgusu.md    265   1709  14832
02_yontem.md                   331   2253  20547
04_bulgular.md                 692   5052  42762
05_sinirliliklar.md            427   2923  25975
                                    -----
                            total   11937 words
```

```
ATX headings           68        (H1 4, H2 39, H3 25, H4+ 0)
table separator rows   36        (10 + 5 + 19 + 2)
table pipe rows       243        max 6 columns
blockquote lines       35        -> 8 quote blocks
bullet list lines       5
ordered list lines      8
horizontal rules        1        (01_..., line 252)
code fences             0
images                  0
raw URLs                0
links "]("              0
footnotes "[^"          0
citations "[n]"         0
inline code spans     411        (822 backticks, 0 odd-backtick lines)
bold "**"             369
triple-star "***"       0
underscore emphasis     0
html tags               0
tabs                    0
```

Parser-relevant facts established by inspection:

- **98 lines have an odd `**` count** — bold spans wrap across soft-wrapped
  lines, so inline parsing must run on the *joined* paragraph, never per line.
- Bold spans **contain** inline code (e.g. ``**Birincil ölçüt: `lexicon_free`
  diliminde `OFF`-duyarlılık.**``), so the tokenizer must nest, not split.
- Literal `|` appears in body prose (``P(`OFF` | `sizin`)``) but never at line
  start, so "line begins with `|`" is a safe table test. 0 escaped pipes.
- `_` is never used as emphasis but appears constantly inside file and field
  names, so `_` emphasis is disabled in the parser.
- Lists use lazy continuation (indented follow-on lines).

---

## 4. Style redefinition — before and after

The change you directed: redefine the **style definitions** once, rather than
overriding Arial Black 12 / Arial bold 12 onto each heading paragraph, so 2a
("do not re-declare fonts in code") holds with no exception.

### Before (as the template ships)

```xml
<w:style w:type="paragraph" w:styleId="Balk1">      <!-- Heading 1 -->
  <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="240" w:after="0"/>
         <w:outlineLvl w:val="0"/></w:pPr>
  <w:rPr><w:rFonts w:ascii="Arial Black" w:eastAsia="Arial Black"
                   w:hAnsi="Arial Black" w:cs="Arial Black"/>
         <w:color w:val="323E4F"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
</w:style>

<w:style w:type="paragraph" w:styleId="Balk2">      <!-- Heading 2 -->
  <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="360" w:after="80"/>
         <w:outlineLvl w:val="1"/></w:pPr>
  <w:rPr><w:b/><w:bCs/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
</w:style>

<w:style w:type="paragraph" w:styleId="Balk3">      <!-- Heading 3 -->
  <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
  <w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="80"/>
         <w:outlineLvl w:val="2"/></w:pPr>
  <w:rPr><w:b/><w:bCs/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
</w:style>
```

### Summary table, before → after

| | before | after |
|---|---|---|
| **Heading 1** (`Balk1`) | `rFonts=Arial Black` (all 4 slots) `sz=28` (14 pt) `bold=—` | **unchanged, verified byte-identical** |
| **Heading 2** (`Balk2`) | `rFonts=none` → inherits Arial, `sz=36` (**18 pt**) `bold=on` | `rFonts=Arial Black` (all 4) `sz=24` (**12 pt**) `bold=—` |
| **Heading 3** (`Balk3`) | `rFonts=none` → inherits Arial, `sz=28` (**14 pt**) `bold=on` | `rFonts=Arial` (all 4) `sz=24` (**12 pt**) `bold=on` |

Real stdout from the build:

```
  BEFORE
    Heading 1  styleId=Balk1  rFonts[ascii=Arial Black/hAnsi=Arial Black/eastAsia=Arial Black/cs=Arial Black] sz=28 (14.0 pt) szCs=28 bold=None
    Heading 2  styleId=Balk2  rFonts[None] sz=36 (18.0 pt) szCs=36 bold=on
    Heading 3  styleId=Balk3  rFonts[None] sz=28 (14.0 pt) szCs=28 bold=on
  AFTER
    Heading 1  styleId=Balk1  rFonts[ascii=Arial Black/hAnsi=Arial Black/eastAsia=Arial Black/cs=Arial Black] sz=28 (14.0 pt) szCs=28 bold=None
    Heading 2  styleId=Balk2  rFonts[ascii=Arial Black/hAnsi=Arial Black/eastAsia=Arial Black/cs=Arial Black] sz=24 (12.0 pt) szCs=24 bold=None
    Heading 3  styleId=Balk3  rFonts[ascii=Arial/hAnsi=Arial/eastAsia=Arial/cs=Arial] sz=24 (12.0 pt) szCs=24 bold=on
  Heading 1 unchanged    : True

  Normal line_spacing set to 1.15 (docDefaults said w:line=360 = 1.5)
```

### Rationale, for the record

The template's written format rule is *"Başlık: Arial Black, 14 punto"*. Only
Heading 1 matches it. Heading 2 shipped at Arial **18 pt** bold — neither Arial
Black nor 14 pt, and **larger than Heading 1**. The template contradicts its own
rule. Redefining moves toward the written rule, not away from it.

**Worse than first described:** the shipped Heading 3 is also **14 pt** — the
same size as Heading 1. Three heading levels at sizes 14 / 18 / 14.

### Two sub-decisions taken inside the change

1. **Heading 2's bold is removed** (`<w:b/>`/`<w:bCs/>` deleted). Arial Black is
   already a heavy face and Heading 1 carries no bold, so H2 now mirrors H1's
   treatment. *Reversible in one line if you want it back — see
   `set_style_font(h2, "Arial Black", 12, bold=False)`.*
2. **All four `rFonts` slots** (ascii/hAnsi/eastAsia/cs) are written, plus
   `szCs` alongside `sz`, matching how the template's own Heading 1 does it.
   python-docx's `style.font.name` alone would set only ascii/hAnsi.

### Line spacing

`1.15` is asserted on the **Normal style**, overriding docDefaults'
`w:line=360` (1.5). Because it lives on Normal, every paragraph — body, quote,
list, table cell — inherits it from a style definition rather than from 336
repetitions of direct formatting.

**Justification is the one thing applied directly**, because Normal is what all
three heading styles are `basedOn`: putting `jc=both` on Normal would justify
the headings too, and Heading 1 had to stay exactly as shipped.

---

## 5. The builder — `report/build_docx.py`

679 lines, committed at `f723b91`. Run with:

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe report/build_docx.py
```

### 5.1 What it does, in order

1. Opens the committed template, prints its path/size/sha256.
2. **Strips the body**: removes every body child except `sectPr` (raw element
   removal, so the `sdt` goes too), then verifies styles and sectPr survived.
3. **Redefines Heading 2 / Heading 3** in the style definitions (§4).
4. Sets `Normal` line spacing to 1.15.
5. **Clears core properties** — author, last_modified_by, title, subject,
   category, comments, keywords all set to `""` explicitly.
6. Asserts the table style exists in the template, aborting if not.
7. Parses and writes the four drafts in numeric order (01, 02, 04, 05).
8. Saves, then **re-opens the saved file and verifies** it.

### 5.2 Markdown handling

- **Blocks:** heading / paragraph / table / blockquote / list / thematic break.
  Soft-wrapped lines are joined before inline parsing.
- **Inline:** a single left-to-right scan producing `(text, bold, italic,
  is_code)` runs, so code nested inside bold keeps both flags. `_` is not
  emphasis. Unbalanced markers and unclosed backticks are recorded as warnings,
  never silently mangled.
- **Table cells** are split on `|` with backtick-awareness, so a literal pipe
  inside a code span cannot split a cell.
- **Headings emit runs with no formatting at all** (`plain=True`) — delimiters
  stripped, no bold/italic. See §7.2 for why this was necessary.

### 5.3 Every direct (non-style) property the build emits

| target | property | reason |
|---|---|---|
| body / quote / list paragraphs | `alignment = JUSTIFY` | 2c asks for justification on body paragraphs; putting it on Normal would push it onto the heading styles, which are `basedOn Normal` |
| blockquote paragraphs | left indent 1.0 cm | template defines no Quote style and the build must not create one |
| list paragraphs | left indent 0.75 cm + literal marker (`• ` / `1. `) | template defines no List Bullet / List Number style; python-docx's built-ins would auto-create styles that are not in the template |
| table header cells | bold runs | markdown marks the header row structurally, not with emphasis; the table style has no header banding |
| table cell paragraphs | `space_after = 0` | docDefaults set 160 twips after every paragraph, ~a line per cell across 36 tables |

**Headings carry none of these.** Verified 0/68 twice — at the XML level and by
Word (§7.2).

### 5.4 Table style — open decision

Used **`TableNormal`**, asserted present in the template's style list with an
abort if missing. Confirmed in the output: `table styles referenced by the
body: ['TableNormal']`.

> **The 36 tables therefore have no borders**, because no table style in the
> template defines any (§2.3). Borders would require either auto-creating a
> style (2g forbids) or direct border formatting on every table (against the
> styles-not-direct-formatting principle). **Not decided — your call.**

### 5.5 Full build output (real stdout, final run)

```
==========================================================================
TEMPLATE
==========================================================================
  path   C:\Projects\NSosyal\NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx
  size   2505567 bytes
  sha256 5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a

==========================================================================
STRIP BODY  (2a)
==========================================================================
  removed 144 paragraphs, 18 tables, 1 other body children
  sectPr survived        : True
  sectPr is same element : True
  pgSz  before/after     : {w:11906, h:16838} / {w:11906, h:16838}
  pgMar before/after     : {top:1417 right:1417 bottom:1417 left:1417
                            header:708 footer:708 gutter:0} / (identical)
  headerReference kept   : True
  styles before/after    : 31 / 31  (identical: True)
  body children left     : 1

  [STYLE REDEFINITION block -- see section 4 above]

==========================================================================
CORE PROPERTIES  (2b)
==========================================================================
  before: author='' last_modified_by='Mustafa Furat' title=''
  after : author='' last_modified_by='' title='' subject='' category='' comments='' keywords=''

==========================================================================
TABLE STYLE  (2g)
==========================================================================
  requested          : 'TableNormal'
  present in template: True

==========================================================================
CONTENT
==========================================================================
  01_veri_ve_deney_kurgusu.md   blocks=57   {'heading': 9, 'para': 35, 'table': 10, 'quote': 2, 'list': 0, 'hrule': 1}
  02_yontem.md                  blocks=71   {'heading': 15, 'para': 50, 'table': 5, 'quote': 1, 'list': 0, 'hrule': 0}
  04_bulgular.md                blocks=141  {'heading': 23, 'para': 94, 'table': 19, 'quote': 4, 'list': 1, 'hrule': 0}
  05_sinirliliklar.md           blocks=94   {'heading': 21, 'para': 66, 'table': 2, 'quote': 1, 'list': 4, 'hrule': 0}
  TOTAL                         {'heading': 68, 'para': 245, 'table': 36, 'quote': 8, 'list': 5, 'hrule': 1}
  table separator paragraphs    1

==========================================================================
VERIFY OUTPUT  (read back from the saved file)
==========================================================================
  output       C:\Projects\NSosyal\report\build\report_draft.docx (2516060 bytes)
  paragraphs   336
  tables       36
  adjacent tbl->tbl pairs (Word merges these): 0  (must be 0)
  headings     {'Heading 1': 4, 'Heading 2': 39, 'Heading 3': 25}
  headings carrying ANY direct formatting: 0  (3: must be 0)
  fonts named anywhere in document.xml: none -- all inherited
  monospace fonts emitted (2e: must be none): none
  core.xml     <cp:coreProperties ...><cp:lastModifiedBy></cp:lastModifiedBy>
               <cp:revision>4</cp:revision>
               <dcterms:created>2026-08-13T09:17:00Z</dcterms:created>
               <dcterms:modified>2026-08-13T09:20:00Z</dcterms:modified>
               <dc:creator></dc:creator><dc:title></dc:title>
               <dc:subject></dc:subject><cp:category></cp:category>
               <dc:description></dc:description><cp:keywords></cp:keywords>
               </cp:coreProperties>
  'Mustafa' present in core.xml: False
  'Furat' present in core.xml: False
  dc:creator element present: True
  styles.xml   31 style definitions carried over
  page size    21.0 x 29.7 cm
  margins      top=2.5 right=2.5 bottom=2.5 left=2.5 cm
  table styles referenced by the body: ['TableNormal']

==========================================================================
WARNINGS  (1)
==========================================================================
  ! 01_veri_ve_deney_kurgusu.md: two tables are adjacent in the source;
    inserted an empty separator paragraph so Word does not merge them
```

Output sha256 of that build:
`c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1`

---

## 6. Content integrity

Character-level comparison of the four sources against text extracted from the
saved `.docx`, all markup delimiters and whitespace removed:

```
source chars (all markup + whitespace removed): 76844
docx   chars (all whitespace removed)          : 76868
similarity ratio: 0.999805
total differing opcodes: 16
```

**All 16 differences are artifacts of the comparison script, not lost content:**

| difference | count | explanation |
|---|---|---|
| `1.` `2.` `3.` … inserted in docx | 12 | list and H1 heading numbers; the comparator's `^\s*\d+[.)]\s+` regex stripped them from the *source* side, the document legitimately shows them |
| `---` present in source, absent in docx | 1 | the thematic break, which carries no text (rendered as an empty paragraph) |
| `\|` inserted in docx | 3 | literal pipes in prose (``P(`OFF` \| `sizin`)``); the comparator replaced `\|` with whitespace and then deleted it — the document preserved them correctly |

Turkish and symbol characters present in the output: `ı ğ ü ş ö ç İ Ü Ş Ö Ç → § —`
(`Ğ` does not occur in the sources). Zero unbalanced emphasis, zero unclosed
backticks, zero ragged tables.

---

## 7. Word COM verification

Word 16.0.20228, file opened **read-only**, `Repaginate()` called, closed with
`Saved = $true` so Word never wrote to the file.

### 7.1 Page count — the number

```
==============================================================
3a. PAGINATED PAGE COUNT
==============================================================
  PAGES             : 44
  words             : 10806
  lines             : 2127
  characters        : 76873
  paragraphs        : 1031
  tables            : 36
  last page via Range: 44
```

Cross-checked three ways, all **44**: `ComputeStatistics(wdStatisticPages)`,
`Content.Information(wdActiveEndPageNumber)`, and Word's own "Number of pages"
document property.

### 7.2 Format, as Word reports the rendered document

```
  -- page geometry (PageSetup) --
     page size      : 21 x 29.7 cm
     orientation    : portrait (0)
     paper size code: 7   (7 = wdPaperA4)
     margin top     : 2.499 cm  (70.85 pt)
     margin bottom  : 2.499 cm  (70.85 pt)
     margin left    : 2.499 cm  (70.85 pt)
     margin right   : 2.499 cm  (70.85 pt)

  -- BODY (first long Normal paragraph) --
     style          : Normal
     font name      : 'Arial'   (NameAscii='Arial')
     font size      : 12 pt
     alignment      : JUSTIFY (3)
     line spacing   : 13.8 pt, rule = multiple (5)  -> multiple of 1.15
     space after    : 8 pt

  -- HEADING 1 (first) --
     style          : Heading 1
     font name      : 'Arial Black'     font size: 14 pt    bold: 0
     alignment      : left (0)          line spacing: 13.8 pt / multiple -> 1.15
     text           : 1. Veri ve Deney Kurgusu

  -- HEADING 2 (first) --
     style          : Heading 2
     font name      : 'Arial Black'     font size: 12 pt    bold: 0
     alignment      : left (0)          line spacing: 13.8 pt / multiple -> 1.15
     text           : 1.1 Veri kümesi

  -- HEADING 3 (first) --
     style          : Heading 3
     font name      : 'Arial'           font size: 12 pt    bold: -1 (on)
     alignment      : left (0)          line spacing: 13.8 pt / multiple -> 1.15
     text           : Bu bölümde kullanılan kaynakların özeti
```

`2.499 cm` is Word's round-trip of 1417 twips (1417/567 = 2.4991), not drift.

### 7.3 Styles pane / direct-formatting audit

```
  view type before   : 3  (3 = Print Layout)
  view type after    : 1  (1 = Draft)
  style area width   : NOT EXPOSED by this Word build via COM --
                       "The property 'StyleAreaWidth' cannot be found on this object."

  first 14 paragraphs as the style area labels them:
     [Heading 1 ]  1. Veri ve Deney Kurgusu
     [Normal    ]  Taslak durumu. Bu bölüm KYS rapor şablonu yayı...
     [Heading 2 ]  1.1 Veri kümesi
     [Normal    ]  Çalışmanın tek eğitim ve tanı kaynağı, OffensE...
     [Normal    ]  Özellik            <- table cells from here
     ...

  Styles pane, 'in this document' -- paragraph styles in use:
     Heading 1    font='Arial Black'   size=14    bold=0    builtIn=True
     Heading 2    font='Arial Black'   size=12    bold=0    builtIn=True
     Heading 3    font='Arial'         size=12    bold=-1   builtIn=True
     Heading 4    font='Arial'         size=12    bold=-1   builtIn=True
     Heading 5    font='Arial'         size=11    bold=-1   builtIn=True
     Heading 6    font='Arial'         size=10    bold=-1   builtIn=True
     Normal       font='Arial'         size=12    bold=0    builtIn=True
     Subtitle     font='Georgia'       size=24    bold=0    builtIn=True
     Title        font='Arial'         size=36    bold=-1   builtIn=True

  -- direct formatting audit over every heading paragraph --
     heading paragraphs checked                                       : 68
     headings whose rendered font differs from their style definition : 0
```

**`StyleAreaWidth` could not be turned on.** It is documented on `View`, but
this Word build does not expose it through IDispatch — `Window.View`,
`Panes(1).View` and `ActivePane.View` all fail identically with
`DISP_E_UNKNOWNNAME`. Setting it by reflection fails the same way. `View.Type`
**does** work (3 → 1, Draft confirmed), so this is specific to that one
property. Reported, not worked around.

The substantive requirement is met by the stronger route: **0 of 68 headings**
carry any direct formatting, confirmed independently by Word (rendered font vs
style font) and at the XML level (no `rPr` on heading runs, no `pPr` child
besides `pStyle`).

Getting to 0 required a build change: two headings contain inline code spans,
and italicising them counted as direct formatting, showing in the Styles pane as
"Heading 3 + Italic". Headings now emit unformatted runs (§5.2).

### 7.4 Document properties, as Word reports them

```
==============================================================
3c. DOCUMENT PROPERTIES AS WORD REPORTS THEM (via reflection)
==============================================================
  Title                  = <EMPTY>
  Subject                = <EMPTY>
  Author                 = <EMPTY>
  Keywords               = <EMPTY>
  Comments               = <EMPTY>
  Template               = Normal
  Last author            = <EMPTY>
  Revision number        = 4
  Application name       = Microsoft Office Word
  Company                = <EMPTY>
  Manager                = <null>
  Category               = <EMPTY>
  Content status         = <null>
  Content type           = <null>
  Number of pages        = 44
  Number of words        = 10806
  Number of characters   = 76873
  Last print date        = <no value set>
  Creation date          = 08/13/2026 12:17:00
  Last save time         = 08/13/2026 12:20:00
  custom document properties : 0

  -- personal-name probe over every value read above --
     'Mustafa' present : False
     'Furat' present : False
     'HP' present : False
     'Musaab' present : False
     'Altawil' present : False
```

**No personal name survives**, confirmed by Word and independently in raw
`core.xml`. `dc:creator` is present-and-empty rather than absent, which was the
whole point.

> **Residue to decide on:** `cp:revision=4`, `dcterms:created` and
> `dcterms:modified` (2026-08-13) are inherited from the template and survive.
> No name, but it is the template's authoring provenance. Clearable via
> `core_properties`; not done, because the brief listed seven fields and these
> were not among them.

### 7.5 Measurement scripts

Both lived in the session scratchpad, which is **not persistent**. They are
plain PowerShell using `New-Object -ComObject Word.Application`; the key calls
are:

```powershell
$word = New-Object -ComObject Word.Application
$word.Visible = $false ; $word.DisplayAlerts = 0
$doc = $word.Documents.Open($path, $false, $true, $false)   # ReadOnly
$doc.Repaginate()
$doc.ComputeStatistics(2)          # 2=Pages 0=Words 1=Lines 3=Chars 4=Paragraphs
$doc.Content.Information(4)        # wdActiveEndPageNumber
$doc.PageSetup.TopMargin / 28.3464567     # points -> cm
$p = $doc.Paragraphs.Item($i) ; $p.Style.NameLocal ; $p.Range.Font.Name
$p.Format.Alignment                # 0 left 1 center 2 right 3 justify
$p.Format.LineSpacing              # points; /12 = multiple
$doc.Styles.Item(-1)               # Normal (-2 H1, -3 H2, -4 H3)
# direct-formatting audit: compare $p.Range.Font.{Name,Size,Bold,Italic}
#                          against $p.Style.Font.{...}
# properties, by reflection (see PS 5.1 traps below):
[System.__ComObject].InvokeMember('Item','GetProperty',$null,$doc.BuiltInDocumentProperties,@($name))
finally { $doc.Saved = $true; $doc.Close(); $word.Quit() }
```

**PS 5.1 traps hit and fixed — re-hit these if the scripts are rewritten:**

1. `$word.Quit(0)` / `$doc.Close(0)` throw *"Argument '1' should be a
   `System.Management.Automation.PSReference`. Use `[ref]`."* Call them with
   **no arguments**.
2. `$doc.BuiltInDocumentProperties.Item($n).Value` cannot be late-bound; use
   `[System.__ComObject]::InvokeMember` reflection.
3. **Naming a function parameter `$args` shadows PowerShell's automatic
   variable** — this silently made every reflection call fail and returned
   `<no value set>` for all 34 properties. Renamed to `$argv`.
4. `powershell.exe` is not on PATH in this environment; invoke the script with
   `& <path>.ps1`.
5. `Marshal::GetITypeInfoForObject` does not exist in PS 5.1.

### 7.6 Process hygiene

```
WINWORD.EXE processes running: 0
  none -- Word COM session closed cleanly
```

One orphan (`/Automation -Embedding`, no window title, no user document) was
left by the first crashed run — where `Quit(0)` threw before releasing the COM
object — identified as this session's and terminated. **If a future run
crashes, check for exactly that signature before killing anything**, so a
real user Word instance is never taken down.

---

## 8. Conversion issues

### 8.1 Fixed: adjacent tables silently merged

`01_veri_ve_deney_kurgusu.md` lines **147 / 149** hold two different tables
separated only by a blank line. Two `<w:tbl>` siblings with no `<w:p>` between
them are **merged into a single table by Word**, forcing the second table's
columns into the first's grid.

Detected because Word's first run reported **35 tables where python-docx wrote
36**. Fixed with an empty separator paragraph — the standard OOXML requirement,
structural rather than invented content — recorded as a build warning, and the
build now **aborts** if any adjacency remains. Word now reports 36.

### 8.2 Deliberate choices, not defects

- **No page break between the four sections.** Nothing asked for one, and three
  breaks would change the page count. Adding them is a lever if sections should
  start on fresh pages (§9).
- **Lists** render as indented paragraphs with literal `• ` / `1. ` markers,
  because the template defines no List Bullet / List Number style and
  python-docx's built-ins would auto-create styles absent from the template.
- **The thematic break** renders as an empty paragraph — it carries no text, and
  a border would mean inventing a style.
- **Unreferenced media survive.** `image1.jpg`, `image2.jpeg` and the five
  embedded `.odttf` fonts stay in the package after the body strip, which is why
  the 11 937-word output is 2.5 MB.

---

## 9. What remains

### The decision

**44 pages measured against a 27-page body budget — 17 pages over.** This is the
open item; nothing else blocks.

Levers, none of them yet applied or costed:

- Cut or condense body text (11 937 words across 36 tables and 68 headings).
- Table density: 36 tables, up to 6 columns, currently at body size with
  `space_after = 0` already applied.
- Line spacing 1.15 and `space after 8 pt` come straight from the written format
  rule; changing them means departing from it.
- Section page breaks are **not** currently inserted; adding them makes it worse,
  not better.

### Open questions for you

1. **Table borders.** 36 tables currently render **borderless** because no table
   style in the template defines borders (§2.3, §5.4). Options: accept; add
   direct border formatting; or add a bordered style to the template.
2. **Heading 2 bold.** Removed as a sub-decision (§4). One line to restore.
3. **Template timestamp residue.** `cp:revision=4` and the 2026-08-13
   created/modified dates survive into the output (§7.4). Clear them or not.

### Explicitly not started

Per the brief, this build is a measurement instrument: **no cover page, no table
of contents, no bibliography**. The submission document is separate work and was
not begun.

---

## 10. File map

| path | state |
|---|---|
| `report/build_docx.py` | committed `f723b91`, 679 lines |
| `report/build/report_draft.docx` | **gitignored** (`.gitignore:59`), 2 516 060 bytes |
| `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` | committed `9a5b75c` |
| `requirements.txt` | `python-docx>=1.2` added, committed `fda8faf` |
| `.gitignore` | `report/build/` added, committed `f723b91` |
| `report/0{1,2,4,5}_*.md` | **inputs, never modified** |
| `docs/docx_build_environment_check_2026_08_20.md` | untracked, pre-existing |
| `docs/verification_sweep_2026_08_20.md` | untracked, pre-existing |
