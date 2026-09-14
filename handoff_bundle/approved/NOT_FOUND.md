# §A1 — approved Turkish text for sections 1.1 / 1.2 / 2.1 / 2.2

**Verdict: state 3 — NOT IN THE REPOSITORY AT ALL.**

Nothing was reconstructed. This directory is deliberately empty of prose.

Searched, all negative:

- working tree, including ignored files:
  `find . -iname '*final*' -o -iname '*approved*' -o -iname 'CONTENT_*'`
- `report/` contains exactly six files: the four raw drafts, `build_docx.py`,
  and the gitignored `build/` output. There is no `report/final/`.
- full history, every branch:
  `git log --all --diff-filter=A --name-only -- 'report/**'` returns only the
  four drafts and `build_docx.py`. Nothing was ever added and later moved or
  deleted (`--diff-filter=D` is empty).
- `git grep -l -i "proje konusu\|katma değer ve yenilikçilik" $(git rev-list --all)`
  hits **one** path only, in every commit: `phases/10_sablon_mapping.md`.
  That file is the KYS coverage map — it self-describes as *"a map, not a
  draft"* and contains no Turkish report prose.

**Numbering trap for whoever writes this.** The template's 1.1/1.2/2.1/2.2 are
*Proje Konusu ve amacı*, *Proje Kapsamı ve Yöntemi*, *Problem Tanımı ve Mevcut
Çözümler*, *Çözüm Fikri, Özgünlük ve Yerlilik* (7+8+7+8 = the 30 points).
The raw drafts also have sections numbered 1.1/1.2/2.1/2.2, but they are
*Veri kümesi*, *Dondurulmuş sözlük*, *Model ve eğitim yapılandırması*,
*Bölünmenin dondurulması* — different content entirely. The two numbering
schemes must not be conflated.

Per the brief, this text is to be recovered from the writing conversation.
