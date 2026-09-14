# DOCX pipeline — resume report

**Date:** 2026-08-20
**Source of truth:** `docs/docx_pipeline_state_2026_08_20.md` (read in full)
**Status:** paused at the one open decision. Nothing started beyond it.

---

## Verified against the live repo

Re-checked rather than paraphrased from the state doc:

| check | result |
|---|---|
| `report/build_docx.py` | present, 679 lines |
| `report/build/report_draft.docx` | present, 2 516 060 bytes |
| output sha256 | `c09103675d98ada2ebae82a9c802fdc620bb196625e165bd1cc27ee6ece8ebc1` — matches the recorded build |
| tracked tree | clean |
| untracked | the same 4 pre-existing files, untouched |
| branch | `master`, ahead of `origin/master` by **4**, not pushed |

**One drift from the state doc:** it records "ahead by 3". The state doc was
itself committed afterwards (`6731345 docs: full session state for the docx
build pipeline`), so the count is now 4. No other discrepancy.

Commits this pipeline added, oldest first:

```
fda8faf deps: pin python-docx for the report build
9a5b75c template: commit the KYS report template at the repo root
f723b91 report: docx builder that paginates the four drafts in the KYS template
6731345 docs: full session state for the docx build pipeline
```

---

## What is done

**Environment.** `.venv` on Python 3.14 with python-docx 1.2.0 / lxml 6.1.2 —
a prebuilt cp314 wheel existed, so the feared source build never happened.
`python-docx>=1.2` pinned in `requirements.txt` under a build-only section.
Note the Python 3.10 interpreter still carries 1.1.2; the build runs on 1.2.0.

**Template committed.** `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx`
at the repo root, 2 505 567 bytes, sha256 `5593d29b…89965a`, verified identical
in worktree and in the git blob (`.gitattributes` sets `* -text`, so no EOL
conversion).

**Builder.** `report/build_docx.py` opens the template, strips all 163 body
children except `sectPr` (raw removal, so the content-control `sdt` goes too),
redefines the Heading 2 / Heading 3 *style definitions*, sets Normal line
spacing to 1.15, clears the seven core properties, then writes the four drafts
and re-opens the saved file to verify it.

**Style change.** Heading 1 left byte-identical as shipped (Arial Black 14 pt).
Heading 2: Arial 18 pt bold → Arial Black 12 pt, bold removed. Heading 3: Arial
14 pt bold → Arial 12 pt bold. The template shipped H1/H2/H3 at 14 / 18 / 14 pt,
contradicting its own written rule; the change moves toward that rule. All four
`rFonts` slots plus `szCs` written, matching how the template's own H1 does it.

**Content.** 11 937 words across the four drafts → 336 paragraphs, 36 tables,
68 headings (H1 4, H2 39, H3 25). Character-level integrity check against the
sources: similarity 0.999805, and all 16 differing opcodes traced to artifacts
of the comparison script, not lost content.

**Verified by Word** (16.0.20228, opened read-only, `Saved = $true` on close, so
Word never wrote to the file): A4 portrait, 2.5 cm margins all round, body Arial
12 pt justified at 1.15, headings rendering exactly as their style definitions
say. **0 of 68 headings carry any direct formatting** — confirmed independently
at the XML level and by Word comparing rendered font against style font. No
personal name survives anywhere in the properties or in raw `core.xml`.

**One conversion bug found and fixed.** Two adjacent tables in
`01_veri_ve_deney_kurgusu.md` (lines 147/149) were being silently merged by Word
— caught because Word reported 35 tables where python-docx wrote 36. Fixed with
the standard OOXML empty separator paragraph; the build now aborts if any
adjacency remains. Word now reports 36.

---

## Page count — measured

**44 pages.**

Measured on the real document, not estimated. Cross-checked three ways, all
agreeing: `ComputeStatistics(wdStatisticPages)`,
`Content.Information(wdActiveEndPageNumber)`, and Word's own "Number of pages"
document property. Word also reports 10 806 words, 2 127 lines, 76 873
characters, 1 031 paragraphs, 36 tables.

**Budget is 27 pages of body. The document is 17 pages over.**

---

## What remains

### The blocking item

Closing the 17-page gap. Levers identified, none applied or costed:

- Cut or condense body text (11 937 words).
- Table density — 36 tables, up to 6 columns; `space_after = 0` already applied
  to cell paragraphs.
- Line spacing 1.15 and space-after 8 pt come from the written format rule;
  changing them means departing from it.
- Section page breaks are **not** inserted; adding them makes the count worse.

### Three open questions

1. **Table borders.** All 36 tables render borderless — not one table style in
   the template defines `tblBorders`, checked recursively including inside
   conditional `tblStylePr` blocks, and there is no "Table Grid". Options:
   accept; direct border formatting on every table; or add a bordered style to
   the template.
2. **Heading 2 bold.** Removed as a sub-decision. One line to restore.
3. **Template timestamp residue.** `cp:revision=4` and the 2026-08-13
   created/modified dates survive into the output. No name attached, but it is
   the template's authoring provenance. Not cleared, because the brief named
   seven fields and these were not among them.

### Known gaps, not defects

- `StyleAreaWidth` could not be enabled — this Word build does not expose it via
  IDispatch on `Window.View`, `Panes(1).View` or `ActivePane.View`. Reported,
  not worked around; the substantive requirement was met by the stronger
  direct-formatting audit instead.
- The two measurement PowerShell scripts lived in the session scratchpad, which
  is not persistent. They are gone; their key COM calls and the five PS 5.1
  traps are recorded in §7.5 of the state doc for rewriting.
- Unreferenced media (`image1.jpg`, `image2.jpeg`, five embedded `.odttf` fonts)
  survive the body strip — harmless, and the reason an 11 937-word document is
  2.5 MB.

### Not started

Per the brief, this build is a measurement instrument: no cover page, no table
of contents, no bibliography. The submission document is separate work.

---

**Stopped here, awaiting direction.**
