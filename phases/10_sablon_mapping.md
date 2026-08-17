# Phase 10 — KYS şablonu coverage map

**This file is a map, not a draft.** It records, for each of the 60 individually
scored check items in the KYS template's scoring appendix, whether material that
satisfies it already exists in this repository, where that material is, and what
is missing. It contains no Turkish report prose, proposes no fix, no
intervention and no new experiment, and changes nothing under `report/` or
`results/` — both were opened read-only.

## Template provenance

| Field | Value |
|---|---|
| File | `NSosyal_Inovasyon_2026_-_Proje_Teknik_Raporu_1_eDrmR.docx` |
| Location at time of reading | `C:\Users\HP\Downloads\` (not in the repository) |
| Size | 2,505,567 bytes |
| SHA-256 | `5593d29b229ed337d73b79f892168b61f71798419b7079fe59ae89f00489965a` |
| Appendix read | `PUANLAMA VE DEĞERLENDİRME ESASLARI` |

Every "Kontrol Maddesi" string below is transcribed verbatim from that file,
including its original capitalisation — the template writes `amaç`, `altyapı`,
`arayüz`, `aşırı` and `akademik` in lower case at the start of several items, and
those are reproduced as found rather than corrected.

The template is **not committed to this repository**. It is a competition
document, it is outside the repo, and the mapping below is only as current as the
hash above.

### Point reconciliation

Each sub-item's check-item points were summed independently and compared against
the stated sub-item total. **All sixteen reconcile; no discrepancy to report.**

| Sub-item | Check items | Summed | Stated | OK |
|---|---:|---:|---:|:--:|
| 1.1 | 4 | 2+2+2+1 = 7 | 7 | ✔ |
| 1.2 | 5 | 2+2+2+1+1 = 8 | 8 | ✔ |
| 2.1 | 5 | 2+1+2+1+1 = 7 | 7 | ✔ |
| 2.2 | 5 | 2+2+2+1+1 = 8 | 8 | ✔ |
| 3.1 | 5 | 1+2+2+1+1 = 7 | 7 | ✔ |
| 3.2 | 4 | 2+2+1+1 = 6 | 6 | ✔ |
| 3.3 | 4 | 2+2+2+1 = 7 | 7 | ✔ |
| 4.1 | 2 | 3+2 = 5 | 5 | ✔ |
| 4.2 | 3 | 2+1+2 = 5 | 5 | ✔ |
| 4.3 | 3 | 2+2+1 = 5 | 5 | ✔ |
| 5.1 | 4 | 3+2+3+2 = 10 | 10 | ✔ |
| 6.1 | 3 | 2+2+1 = 5 | 5 | ✔ |
| 6.2 | 3 | 2+2+1 = 5 | 5 | ✔ |
| 7.1 | 4 | 2+1+1+1 = 5 | 5 | ✔ |
| 8.1 | 3 | 2+2+1 = 5 | 5 | ✔ |
| 9 | 3 | 2+2+1 = 5 | 5 | ✔ |
| **Total** | **60** | **100** | **100** | ✔ |

### Verdict definitions

| Verdict | Meaning |
|---|---|
| `COVERED` | material exists that satisfies the check item as written |
| `PARTIAL` | material exists but does not satisfy the item as written |
| `NONE` | nothing in the repo addresses this |
| `EXTERNAL` | cannot come from the repo at all; needs the project lead |

Every `COVERED` and `PARTIAL` below was produced by opening the cited file and
confirming the cited heading exists and says what is claimed. No verdict rests on
recall. Where existing material would have to be written from scratch to satisfy
an item — however short that writing would be — the verdict is `NONE`.

One boundary applied consistently: `PARTIAL` requires material on the *same
subject* as the check item, at the wrong altitude or with a component missing.
Material that is merely adjacent, or that a writer could use as raw input, does
not earn `PARTIAL`.

---

## 1. Check-item map

### 1.1 Proje Konusu ve amacı (0-7 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Proje konusu, sosyal medya ekosistemiyle ilişkili ve net biçimde tanımlanmış. | 2 | `PARTIAL` | `README.md#NSosyal B* — Turkish adversarial toxicity detection + review triage` (opening two paragraphs) | The subject is defined as a detection-and-triage system; the link to the **social media ecosystem** is never made. Also English, and outside `report/`. |
| Proje amacı açık bir dille ifade edilmiş. | 2 | `COVERED` | `report/01_veri_ve_deney_kurgusu.md#1.7 Birincil değerlendirme ölçütü` — opening sentence states the aim is to reduce the model's lexical dependence, not to raise overall accuracy | — |
| Hangi inovasyon dikeyine (tema) hitap ettiği açıkça belirtilmiş. | 2 | `NONE` | — | Nothing in the repo names *İçerik Ekonomisi*, *Sosyal Yapay Zeka* or *Kullanıcı Katılımı & Arayüz*. No theme declaration exists in any file. |
| amaç, yarışmanın Bölüm 1'de tanımlanan genel hedefleriyle tutarlı. | 1 | `EXTERNAL` | — | The competition şartname is not in the repo, so the goals to be consistent *with* are unavailable. Needs the lead. |

### 1.2 Proje Kapsamı ve Yöntemi (0-8 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Projenin kapsamı/sınırları net biçimde tanımlanmış. | 2 | `COVERED` | `report/05_sinirliliklar.md#5.13 Kapsam notu`; `report/05_sinirliliklar.md#5.9 Genelleme sınırları`; `report/01_veri_ve_deney_kurgusu.md#1.6 Kayıt altına alınmayan veri kaynakları` | — |
| İzlenecek teknik ve akademik yöntem açıklanmış. | 2 | `COVERED` | `report/02_yontem.md` — all of §2.1 through §2.8 | — |
| Seçilen tema (İçerik Ekonomisi / Sosyal YZ / Kullanıcı Katılımı-UX) ile doğrudan ilişki kurulmuş. | 2 | `NONE` | — | Same absence as 1.1 item 3. No theme is named anywhere, so no relation to one is established. |
| Fikrin çalışan bir prototip ile destekleneceği belirtilmiş. | 1 | `COVERED` | `demo/README.md#What the screen shows`; `demo/README.md#Robustness` (selftest verified with all outbound sockets blocked, two cold starts) | — |
| Projenin yeni çalışmalara zemin hazırlama potansiyeli vurgulanmış. | 1 | `PARTIAL` | `results/09_deeper_analysis/stage_1/findings.md#10. Questions this opens (measurement, not proposals)`; `results/08_lexical_analysis/findings.md#9. What this closes and what it opens` | Both are internal next-measurement lists written under an explicit no-proposals constraint. Neither claims the work lays groundwork for other studies. |

### 2.1 Problem Tanımı ve Mevcut Çözümler (0-7 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Gerçek ve nesnel bir problem tanımlanmış. | 2 | `COVERED` | `report/04_bulgular.md#4.10 Bulguların özeti` row 1 — a lexicon filter structurally misses 63.5% of offensive content; `report/01_veri_ve_deney_kurgusu.md#1.2 Dondurulmuş sözlük ve eşleşme kuralı` | — |
| Problemin büyüklüğünü gösteren istatistik/veri sunulmuş. | 1 | `PARTIAL` | `report/01_veri_ve_deney_kurgusu.md#1.1 Veri kümesi` (31,756 rows, 6,131 `OFF`); `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü` | Magnitude is measured **inside one 31,756-row corpus**. No platform-level, sector-level or national prevalence figure exists — the template asks how big the problem is in the ecosystem, not in our sample. |
| En az bir resmî kaynak veya akademik veriyle desteklenmiş. | 2 | `PARTIAL` | `report/01_veri_ve_deney_kurgusu.md#1.1 Veri kümesi` — the Çöltekin OffensEval-TR corpus is named and hashed | Named by filename and SHA-256 only. There is **no bibliographic citation** of Çöltekin or of any other academic source anywhere in `report/`, and `report/` has no section-3 file at all. |
| Piyasadaki mevcut alternatif çözümler ele alınmış. | 1 | `PARTIAL` | `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü` → sub-heading `Genel başarım` — the keyword filter is benchmarked on both dev and the official test set | One incumbent **method** is benchmarked. No existing product or service is surveyed. |
| Mevcut çözümlerin eksik/yetersiz yönleri açıkça belirtilmiş. | 1 | `COVERED` | `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü` → `Genel başarım` — keyword filter macro-F1 0,6799 vs BERTurk 0,8271 on dev; `OFF` recall 0,3859 | — |

### 2.2 Çözüm Fikri, Özgünlük ve Yerlilik (0-8 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Çözüm fikri probleme/amaca uygun ve net biçimde ifade edilmiş. | 2 | `COVERED` | `report/04_bulgular.md#4.6 Müdahalenin bileşen düzeyindeki etkisi` (the 1a/1b/D intervention, four separable runs); `demo/README.md#What the screen shows` (the shipped configuration and the 0,6632 review threshold) | — |
| Çözümün güçlü ve yenilikçi yönleri belirtilmiş. | 2 | `PARTIAL` | `report/04_bulgular.md#4.10 Bulguların özeti` (ten numbered findings with evidence pointers) | The report makes **no innovation claim at all**, by design — §4.10 is a findings table, not a strengths argument. The genuinely distinctive elements (pre-registration, threshold-free slice evaluation, single-use test accounting) are presented as method, never as an advantage. |
| Mevcut çözümlerden farkı somut piyasa kıyaslarıyla gösterilmiş. | 2 | `PARTIAL` | `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü` → `Genel başarım` | The comparator is an internal keyword baseline, not a market product. No third-party system is measured against. |
| Çözümün pazarda uygulanabilir olduğu gösterilmiş. | 1 | `NONE` | — | No market, pricing, deployment or adoption material exists in any file. |
| En az bir yerli bileşen/teknoloji kullanıldığı/geliştirildiği belirtilmiş. | 1 | `PARTIAL` | `report/01_veri_ve_deney_kurgusu.md#1.2 Dondurulmuş sözlük ve eşleşme kuralı` (the frozen 695-entry karaliste); `report/02_yontem.md#2.3 Dondurulmuş sözlük ve dilim etiketleme` (`lexicon.hit_root`, Turkish-aware casing) | The lexicon and the Turkish matching rule are the team's own, but **no yerlilik claim is made**. Note the counter-fact the writer will have to handle: the base encoder `dbmdz/bert-base-turkish-cased` (`report/02_yontem.md#2.1 Model ve eğitim yapılandırması`) is Turkish-*language*, not Turkish-*origin*. |

### 3.1 İzlenecek Yöntem, altyapı ve Sürüm Kontrolü (0-7 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Kullanılacak yazılım dilleri/teknolojiler belirtilmiş. | 1 | `COVERED` | `report/02_yontem.md#2.1 Model ve eğitim yapılandırması` (torch 2.11.0+cu128, transformers 5.15.0, scikit-learn 1.6.1); `requirements.txt` | — |
| Veri setleri ve analiz yöntemleri açıklanmış. | 2 | `COVERED` | `report/01_veri_ve_deney_kurgusu.md#1.1 Veri kümesi`; `report/02_yontem.md#2.7 Değerlendirme` | — |
| Teknik altyapı eksiksiz tanımlanmış. | 2 | `COVERED` | `report/02_yontem.md#2.1 Model ve eğitim yapılandırması` (NVIDIA L4); `report/02_yontem.md#2.8 Yeniden üretilebilirlik` (`run_config.json` per run); `demo/README.md#Checkpoint sizes and where they must live` | — |
| GitHub/Bitbucket repo bağlantısı paylaşılmış. | 1 | `PARTIAL` | `README.md#Status` — names the remote `MusaabAlt/nsosyal-bstar`, private, verified 404 unauthenticated | Not a URL, not in any `report/` section, and **the repo is private** — a jury following it would be refused. `README.md#NSosyal B* …` states the repo stays private until submission because `src/obfuscation.py` generates functional evasion text, so access is a decision for the lead, not a wording fix. |
| Commit geçmişiyle takip edilebilir bir geliştirme süreci belirtilmiş. | 1 | `COVERED` | `report/02_yontem.md#2.8 Yeniden üretilebilirlik` (git SHA written into every `run_config.json`; `docs/RESULTS_LOG.md` append-only); `docs/PROJECT_HISTORY.md` (36 cited commit SHAs) | — |

### 3.2 Model ve Veri Doğrulama (0-6 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Veri ön işleme süreci açıklanmış. | 2 | `COVERED` | `report/01_veri_ve_deney_kurgusu.md#1.1 Veri kümesi` (unquoted-TSV trap, manual tab parsing); `#1.3 Eğitim / geliştirme ayrımı`; `#1.4 Dilimleme`; `report/02_yontem.md#2.3 Dondurulmuş sözlük ve dilim etiketleme` | — |
| Model eğitimi süreci açıklanmış. | 2 | `COVERED` | `report/02_yontem.md#2.1 Model ve eğitim yapılandırması` — full hyperparameter table, identical across all arms | — |
| aşırı öğrenme (overfitting) önlemleri belirtilmiş. | 1 | `COVERED` | `report/02_yontem.md#2.1 …` → `Neden hiperparametre taraması yapılmadı` and `Denetim noktası seçimi — açıkça belirtilmesi gereken bir nokta`; `#2.2 Bölünmenin dondurulması`; `#2.4 Döngüsellik karşıtı protokol`; `#2.6 Tek kullanımlık test kümesi muhasebesi` | — |
| Performans metrikleri (doğruluk, F1, vb.) sunulmuş. | 1 | `COVERED` | `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü`; `#4.6 Müdahalenin bileşen düzeyindeki etkisi`; `#4.7 Sistem düzeyindeki etki ve bedeller`; `#4.10 Bulguların özeti` | — |

Note (3.2): the template attaches a conditional to this sub-item — *"Projede
yapay zeka/veri bileşeni yoksa bu alt kriter değerlendirme dışı bırakılır"* — which
does not apply here. This is the only sub-item scoring `COVERED` on every check
item, and it is worth **6 of 100 points**. See §2 below.

### 3.3 Kullanıcı Deneyimi (UI/UX) (0-7 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Kullanıcı akışları (user flows) sunulmuş. | 2 | `PARTIAL` | `demo/README.md#What the screen shows` — one screen, four columns, and the AUTO-RESOLVE / DEFER routing decision | A single screen's column layout and one binary routing decision. No user flow diagram, no reviewer-side journey, no multi-step flow of any kind. |
| arayüz tasarım kararları gerekçelendirilmiş. | 2 | `PARTIAL` | `demo/README.md#Why not Gradio or Streamlit` — stdlib `http.server`, inline CSS/JS, offline by construction | The justification is about offline robustness and dependency risk, not interface design. `demo/README.md#Known limitations` states the opposite of a design case outright: *"Not a product. Legibility only — no styling work, no auth."* |
| Erişilebilirlik yaklaşımı belirtilmiş. | 2 | `NONE` | — | No accessibility material of any kind — no contrast, keyboard, screen-reader, WCAG or assistive-technology consideration anywhere in `demo/` or `report/`. |
| Kullanılabilirlik testi sonucu/özeti paylaşılmış. | 1 | `EXTERNAL` | — | `demo/README.md#Robustness` is an adversarial-input test table (empty input, emoji, 100k chars, control characters, malformed JSON) with **no human participants**. A usability test needs people; that cannot come from the repo. |

### 4.1 Verimlilik ve Etkinlik (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Verimlilik artışı somut argümanlarla gösterilmiş. | 3 | `COVERED` | `report/04_bulgular.md#4.9 Seçici tahmin ve çalışma noktaları` — %90,2 automatic coverage at 0,8485 macro-F1 / %8,52 error, %9,8 deferred, errors concentrated **3,59×** into the deferred queue, on the official test set | — |
| Etkinlik ölçülebilir biçimde ifade edilmiş. | 2 | `COVERED` | `report/04_bulgular.md#4.2 Temel çizgi ve açığın büyüklüğü`; `#4.9 Seçici tahmin ve çalışma noktaları` — every figure carries a 95% CI | — |

### 4.2 Hedef Kitle (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Hedef kitle açıkça tanımlanmış. | 2 | `NONE` | — | No audience definition exists. The single mention of a human role — *"bir incelemeci zamanının çoğunu örtük saldırıya ayırmaktadır"* in `report/04_bulgular.md#4.9 …` → `Devretme dilim körüdür — bir sıfır sonucu` — is a workload observation inside a null result, not a definition of who the product is for. |
| Hedef kitlenin genişliği/büyüklüğü belirtilmiş. | 1 | `NONE` | — | No audience size figure of any kind. |
| Ürünün hedef kitleyle uyumu kanıtlanmış. | 2 | `NONE` | — | Nothing addresses fit to an audience; no audience is named to be fitted to. |

### 4.3 Teknolojik Yenilik ve Uygulanabilirlik (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Teknolojik yenilik düzeyi teknik detaylarla ortaya konmuş. | 2 | `PARTIAL` | `report/02_yontem.md#2.4 Döngüsellik karşıtı protokol`; `report/04_bulgular.md#4.6 …` → `Kazancın mekanizması — eşik geçişi, sıralama iyileşmesi değil`; `phases/09_deeper_analysis.md` (C9-12…C9-17) | Technical detail is abundant and the level of novelty is never asserted. Same absence as 2.2 item 2: nothing in the repo says what is new about any of it. |
| Fikrin teknik olarak hayata geçirilebilir olduğu gösterilmiş. | 2 | `COVERED` | `demo/README.md#Robustness` (selftest passes offline on two cold starts); `report/04_bulgular.md#4.9 …` — dev-selected thresholds transferred to the official test set within 1–2 points of their dev coverage | — |
| Ölçeklenebilir bir yapı belirtilmiş. | 1 | `NONE` | — | Nothing claims scalability, and the repo records the opposite: `demo/README.md#Known limitations` — *"No batching, no persistence. One request at a time"*, and ~885 MB of fp32 weights slow to load on CPU. A writer will be asserting scalability against recorded evidence, not from it. |

### 5.1 Toplumsal Fayda ve Erişim Potansiyeli (0-10 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Geniş kullanıcı kitlelerine ulaşma potansiyeli gösterilmiş. | 3 | `NONE` | — | No reach, distribution or deployment-potential material exists. |
| Sosyal medya ekosistemine sağlayacağı katkı açıklanmış. | 2 | `NONE` | — | The ecosystem is never discussed in any file. |
| Toplumsal fayda oluşturma kapasitesi somut örneklerle gösterilmiş. | 3 | `NONE` | — | No societal-benefit material and no worked example of one. |
| Dijital yaşam kalitesine olumlu etkisi belirtilmiş. | 2 | `NONE` | — | Nothing addresses this. |

**This is the single largest sub-item in the template (10 points) and the repo
addresses none of it.**

### 6.1 Ticarileştirme Potansiyeli ve İş Modeli (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Gelir/iş modeli net biçimde tanımlanmış. | 2 | `NONE` | — | No revenue or business-model material exists. |
| Sektöre/ülke ekonomisine katma değer potansiyeli gösterilmiş. | 2 | `NONE` | — | Nothing addresses sector or national economic value. |
| Yeni iş ortaklıkları/işbirlikleri kurma potansiyeli belirtilmiş. | 1 | `NONE` | — | No partnership material exists. |

### 6.2 Finansal, Teknik ve Sosyal Sürdürülebilirlik (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Finansal sürdürülebilirlik açıklanmış. | 2 | `NONE` | — | No cost, funding or financial material of any kind. |
| Teknik sürdürülebilirlik (bakım, ölçeklenme) açıklanmış. | 2 | `PARTIAL` | `report/02_yontem.md#2.8 Yeniden üretilebilirlik` (per-run `run_config.json`, append-only log, 166 unit tests); `README.md#Layout` (`src/` as single source of truth, stubs raise `NotImplementedError` rather than drift) | Maintainability is genuinely documented. **Scaling is not** — see 4.3 item 3; the recorded evidence runs the other way. |
| Değişen kullanıcı ihtiyaçlarına uyum sağlama yaklaşımı belirtilmiş. | 1 | `NONE` | — | Nothing addresses adaptation to changing user needs. |

### 7.1 İş Paketleri ve Zamanlama (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| İş paketleri ve alt faaliyetler detaylandırılmış. | 2 | `PARTIAL` | `phases/01_baseline_diagnosis.md`, `phases/03_defense_design.md`, `phases/04_calibration.md`, `phases/07_report.md`, `phases/08_lexical_analysis.md`, `phases/09_deeper_analysis.md` | These are execution specs for work **already done**, with sub-activities and constraints. There is no forward work package running to 24 Aug / 2–7 Sep / 14 Sep 2026. |
| Kilometre taşları belirlenmiş. | 1 | `PARTIAL` | `docs/RESULTS_LOG.md` (34 dated data rows); `docs/PROJECT_HISTORY.md` (chronological, Day 1 through Stage 1b) | Past milestones are recorded to the day. **No future milestone exists.** |
| Görsel bir şema/tablo ile sunulmuş. | 1 | `PARTIAL` | `README.md#Status` — a step/state table | It is a status table, not a timeline, and **it is stale**: it lists the row "Phase 2 — failure analysis + defense design" with state "not started", while `results/02_failure_analysis/` and `results/03_defense/` both exist and are cited throughout the report. Anything reused from it would carry that error forward. |
| Takvim gerçekçi ve yarışma takvimiyle (Ek: 24 ağu / 2-7 Eyl / 14 Eyl 2026) uyumlu. | 1 | `NONE` | — | No forward calendar exists, so there is nothing to be consistent or inconsistent with. |

### 8.1 Takım Organizasyonu ve Roller (0-5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Görev dağılımı tablolaştırılmış. | 2 | `EXTERNAL` | — | Team composition is not recorded anywhere in the repo. Needs the lead. |
| Farklı disiplinlerden üyelerin projeye katkısı belirtilmiş. | 2 | `EXTERNAL` | — | Member disciplines and contributions are not recorded. Needs the lead. |
| Ekip büyüklüğü/yapısı (2-5 kişi) proje ihtiyaçlarını karşılıyor. | 1 | `EXTERNAL` | — | Team size is not recorded. Needs the lead. |

The template adds a constraint that applies when this is written: *"Değerlendirme
esasları gereği takım üyelerinin isim ve fotoğraf gibi kişisel bilgilerine yer
verilmemelidir."*

### 9. Kaynakça — Formata Uygunluk (0- 5 Puan)

| Kontrol Maddesi (verbatim TR) | Max | Verdict | Source (file#anchor) | What is missing |
|---|---:|---|---|---|
| Kaynakça eksiksiz listelenmiş. | 2 | `NONE` | — | There is **no bibliography in the repository**. `report/` contains files 01, 02, 04 and 05 only — no section-3 file exists, which the project record notes was deliberately left unwritten pending citation verification from primary sources. `report/01_veri_ve_deney_kurgusu.md#Bu bölümde kullanılan kaynakların özeti` is a provenance table of internal result files, not literature. |
| Dijital/Web ve akademik Kaynak formatı kurallarına uyulmuş. | 2 | `NONE` | — | No reference entry exists in any format, correct or otherwise. |
| Metin içi atıflar (köşeli parantez) doğru kullanılmış. | 1 | `NONE` | — | The report cites internally, by section (`§4.2`) and by file path. There is not one `[n]` citation in `report/`, and no numbered list for one to point at. |

---

## 2. Fazla Kapsam / Over-coverage

The 30-page cap makes this a cost, not a comfort. Length estimates below are word
counts converted at **450 words/page**, which is a reasonable rate for the
template's format rules (Arial 12 pt, 1.15 spacing, 2.5 cm margins). The estimate
is **conservative in one direction that matters**: `report/` contains **36 tables
across 243 table rows**, and a table row occupies far more vertical space than its
word count implies. Real page counts will be higher than these figures, not lower.

### 2.1 The whole of `report/` maps to 31 of 100 points

| File | Words | ≈ pages |
|---|---:|---:|
| `report/01_veri_ve_deney_kurgusu.md` | 1,662 | 3.7 |
| `report/02_yontem.md` | 2,209 | 4.9 |
| `report/04_bulgular.md` | 4,992 | 11.1 |
| `report/05_sinirliliklar.md` | 2,839 | 6.3 |
| **Total** | **11,702** | **26.0** |

The template reserves 3 pages for cover, contents and bibliography. 26 + 3 = **29
of the 30 available pages**, before a single word is written for the 37 `NONE`
points, the 7 `EXTERNAL` points, or the gaps inside the 25 `PARTIAL` points.

### 2.2 What lands on 3.2 (6 points) — the specific answer

Sub-item **3.2 Model ve Veri Doğrulama is worth 6 points**. Everything below is
data preprocessing, model training, overfitting control, or performance metrics —
i.e. it lands on those four check items and nowhere else:

| Material | Words | ≈ pages |
|---|---:|---:|
| `report/01_veri_ve_deney_kurgusu.md` §1.1–§1.6 (corpus, lexicon, split, slicing, test accounting, excluded sources) | 1,059 | 2.4 |
| `report/02_yontem.md` §2.1–§2.7 (model config, split freeze, slice labelling, anti-circularity, pre-registration, single-use accounting, evaluation) | 2,033 | 4.5 |
| `report/04_bulgular.md` all except §4.9 (findings, gap size, error analysis, component effects, system effects, calibration, summary) | 4,547 | 10.1 |
| `report/05_sinirliliklar.md` in full (limitations) | 2,839 | 6.3 |
| **Total on a 6-point sub-item** | **10,478** | **23.3** |

**10,478 of the 11,702 words currently in `report/` — 89.5% — sit on a sub-item
worth 6 points.** At the conversion rate above that is 23.3 pages for 6 points,
against 10 points for 5.1 which currently has zero pages.

Two blocks inside that total are worth naming separately, because their ratio is
sharper still:

**a. The overfitting block: ≈3.2 pages for 1 point.** These sections address only
`aşırı öğrenme (overfitting) önlemleri belirtilmiş (0-1 Puan)`:

| Section | Words |
|---|---:|
| `report/02_yontem.md#Neden hiperparametre taraması yapılmadı` | 204 |
| `report/02_yontem.md#Denetim noktası seçimi — açıkça belirtilmesi gereken bir nokta` | 103 |
| `report/02_yontem.md#2.2 Bölünmenin dondurulması` | 141 |
| `report/02_yontem.md#2.4 Döngüsellik karşıtı protokol` (incl. §2.4.1–§2.4.4) | 576 |
| `report/02_yontem.md#2.5 Ön kayıt uygulaması` | 282 |
| `report/02_yontem.md#2.6 Tek kullanımlık test kümesi muhasebesi` | 144 |
| **Total** | **1,450** (≈3.2 pages) |

**b. `report/05_sinirliliklar.md` in full: 2,839 words, ≈6.3 pages, 0 points.**
No check item anywhere in the 60 asks for limitations. §5 is not scored by
anything in the template — not in 3.2, not in 4.3, not in 9. Its longest
subsections are `#5.3 Dilim tanımında iki bağımsız kirlenme` (520 w), `#5.4
Müdahalenin nedensel yorumu` (457 w), `#5.12 Duyarlılık açığının kaynağı
ayrıştırılamamaktadır` (417 w) and `#5.14 Özet` (376 w).

Whether that is over-coverage or the report's integrity is a judgment for the
lead, not a mapping decision. This map records only that the template allocates
it nothing.

### 2.3 Other over-coverage

| Where | Length | Check item it lands on | Note |
|---|---:|---|---|
| `report/04_bulgular.md#Eşikten bağımsız karşılaştırma — dilim içi ROC-AUC` | 485 w (≈1.1 p) | 3.2, `Performans metrikleri … sunulmuş` (1 pt) | The Phase 09 Stage 1 result, at full method depth. |
| `report/04_bulgular.md#İkinci yordayıcı: muhatap alma` | 493 w (≈1.1 p) | 3.2 (1 pt) | The Phase 08 lexical result. |
| `report/02_yontem.md#2.4.3 Türetme kaynağının ayrılması — ve tasarım sırasında düzeltilen bir hata` | 276 w (≈0.6 p) | 3.2, overfitting (1 pt) | A methodology self-correction narrative. |
| `report/04_bulgular.md#Devretme dilim körüdür — bir sıfır sonucu` | 159 w (≈0.4 p) | 4.1 (5 pts) | A null result inside the sub-item that carries the efficiency claim. |

### 2.4 Depth held outside `report/` — not counted against the cap

The seven `findings.md` files under `results/` hold a further **13,151 words**
(02: 1,946 · 03: 1,322 · 04: 1,825 · 05: 1,380 · 08: 3,001 · 09 Stage 1: 2,383 ·
09 Stage 1b: 1,294). None of it is report text and none of it consumes the 30
pages. It is recorded here only so the cap is not miscounted against it.

---

## 3. Repo dışı gereksinimler

Five check items, worth **7 points**, cannot be answered from this repository at
all. Each is phrased below as a question the project lead can answer directly.

| # | Check item | Pts | Question for the project lead |
|---|---|---:|---|
| 1 | 1.1 — *amaç, yarışmanın Bölüm 1'de tanımlanan genel hedefleriyle tutarlı.* | 1 | Can you supply the competition şartname's Bölüm 1 (general goals) text? The repo has no copy, so consistency with it cannot be checked or claimed. |
| 2 | 3.3 — *Kullanılabilirlik testi sonucu/özeti paylaşılmış.* | 1 | Has anyone outside the build team used the demo screen? If so: how many people, who were they, what were they asked to do, and what was observed? If nobody has, is there time to run one before 24 August? |
| 3 | 8.1 — *Görev dağılımı tablolaştırılmış.* | 2 | Who is on the team, and which work packages does each person own? (The template forbids names and photos, so roles and responsibilities only.) |
| 4 | 8.1 — *Farklı disiplinlerden üyelerin projeye katkısı belirtilmiş.* | 2 | What discipline does each member come from (software, AI, data science, security, product, UI/UX, design, entrepreneurship), and what did each contribute? |
| 5 | 8.1 — *Ekip büyüklüğü/yapısı (2-5 kişi) proje ihtiyaçlarını karşılıyor.* | 1 | How many people are on the team? The template's scored range is 2–5. |

Two further items are not `EXTERNAL` but still need a decision only the lead can
make, and are listed here so they are not lost:

- **3.1, repo link (1 pt, `PARTIAL`).** `MusaabAlt/nsosyal-bstar` is private, and
  `README.md` records the reason: `src/obfuscation.py` generates functional
  evasion text. The check item awards its point for a link the jury can follow.
  Whether the repo is opened, opened partially, or left private with the link
  stated is a call for the lead.
- **2.2, yerlilik (1 pt, `PARTIAL`).** The lexicon and Turkish matching rule are
  the team's own; the base encoder is `dbmdz/bert-base-turkish-cased`, which is
  Turkish-language but not Turkish-origin. What is claimed here should be the
  lead's decision, since it is a claim about the project rather than a finding.

---

## 4. Summary

Points are allocated per check item, so this table distributes each sub-item's
maximum across the four verdict classes at check-item granularity.

| Sub-item | Max | COVERED | PARTIAL | NONE | EXTERNAL |
|---|---:|---:|---:|---:|---:|
| 1.1 Proje Konusu ve amacı | 7 | 2 | 2 | 2 | 1 |
| 1.2 Proje Kapsamı ve Yöntemi | 8 | 5 | 1 | 2 | 0 |
| 2.1 Problem Tanımı ve Mevcut Çözümler | 7 | 3 | 4 | 0 | 0 |
| 2.2 Çözüm Fikri, Özgünlük ve Yerlilik | 8 | 2 | 5 | 1 | 0 |
| 3.1 İzlenecek Yöntem, altyapı ve Sürüm Kontrolü | 7 | 6 | 1 | 0 | 0 |
| 3.2 Model ve Veri Doğrulama | 6 | 6 | 0 | 0 | 0 |
| 3.3 Kullanıcı Deneyimi (UI/UX) | 7 | 0 | 4 | 2 | 1 |
| 4.1 Verimlilik ve Etkinlik | 5 | 5 | 0 | 0 | 0 |
| 4.2 Hedef Kitle | 5 | 0 | 0 | 5 | 0 |
| 4.3 Teknolojik Yenilik ve Uygulanabilirlik | 5 | 2 | 2 | 1 | 0 |
| 5.1 Toplumsal Fayda ve Erişim Potansiyeli | 10 | 0 | 0 | 10 | 0 |
| 6.1 Ticarileştirme Potansiyeli ve İş Modeli | 5 | 0 | 0 | 5 | 0 |
| 6.2 Finansal, Teknik ve Sosyal Sürdürülebilirlik | 5 | 0 | 2 | 3 | 0 |
| 7.1 İş Paketleri ve Zamanlama | 5 | 0 | 4 | 1 | 0 |
| 8.1 Takım Organizasyonu ve Roller | 5 | 0 | 0 | 0 | 5 |
| 9. Kaynakça — Formata Uygunluk | 5 | 0 | 0 | 5 | 0 |
| **TOTAL** | **100** | **31** | **25** | **37** | **7** |

Column totals: 31 + 25 + 37 + 7 = **100**. ✔

**By verdict class, across all 60 check items:**

| Verdict | Check items | Points | Share |
|---|---:|---:|---:|
| `COVERED` | 18 | **31** | 31% |
| `PARTIAL` | 17 | **25** | 25% |
| `NONE` | 20 | **37** | 37% |
| `EXTERNAL` | 5 | **7** | 7% |
| | **60** | **100** | |

Three observations that follow from the table and from nothing else:

1. **`COVERED` concentrates in one place.** 17 of the 31 covered points are in
   3.1 (6) and 3.2 (6) and 4.1 (5) — the technical-method and efficiency
   sub-items. The four sub-items that are entirely or almost entirely `NONE`
   (4.2, 5.1, 6.1, 9) are worth **25 points between them** and are addressed by
   nothing in the repository.

2. **The largest single sub-item is the emptiest.** 5.1 is worth 10 points, more
   than any other, and scores `NONE` on all four of its check items.

3. **The length is already spent on the wrong sub-item.** 89.5% of existing
   report text serves a 6-point sub-item, and the 30-page budget is ~29/30
   consumed by material covering 31 points.

---

## 5. Verification record

Every claim in §1–§4 was checked mechanically before this file was committed, so
that a wrong citation or a mis-added column fails loudly rather than reading as
fact. The checks, and what each one would have caught:

| # | Check | Result | What it catches |
|---|---|---|---|
| 1 | Each of the 60 `Kontrol Maddesi` strings matched, whitespace-normalised, against the text extracted from `word/document.xml` | **60/60 verbatim** | A paraphrased or half-remembered check item — which would silently change what the verdict is a verdict *about* |
| 2 | Each `file#anchor` citation resolved: file exists, and the anchor matches a real heading in it | **56/56 resolved** | The defect named in the task brief — a citation to a section that does not exist |
| 3 | Per-sub-item verdict points re-summed from the tables themselves and compared to each stated max | **16/16 reconcile** | A row whose `Max` was mistyped, or a missing row |
| 4 | Summary table (§4) columns re-derived from the §1 tables and compared cell by cell | **agrees; columns sum to 100** | A summary that drifts from the detail it summarises |
| 5 | Every markdown table checked for a consistent cell count per row | **no ragged tables** | A stray pipe character inside a cell silently splitting a row (this fired once, on the quoted `README` status row, and was fixed) |
| 6 | `git status` and `git diff` over `report/` and `results/` | **byte-identical, no diff** | The hard constraint that the evidence source is read-only |
| 7 | Repository test suite | **166 passed** | Unrelated breakage introduced alongside a docs change |

Check 2 initially failed on **15 shorthand citations** that named a report file by its
number prefix alone instead of its full filename. All were expanded to full paths; none were
approximations of a real heading, but the short form is exactly the failure mode
rule 2 of the task brief exists to prevent, so it was treated as a defect rather
than a formatting preference.

**Point reconciliation against the figures supplied with the task** (`1.1=7
1.2=8 2.1=7 2.2=8 3.1=7 3.2=6 3.3=7 4.1=5 4.2=5 4.3=5 5.1=10 6.1=5 6.2=5 7.1=5
8.1=5 9=5`): every sub-item's check items sum to its stated figure, and the
sixteen figures sum to 100. **No discrepancy to report** — see the table in
*Template provenance* above.

**Commit:** `c4b3229` — *"Phase 10: KYS sablonu coverage map — 60 check items, no
drafting"*, on `master`, one commit, this file only.

---

## Scope of this file

This is a coverage map produced from a read-only pass over the template, the
report drafts, the results files and the phase specs. It drafts nothing, proposes
no fix, no intervention and no new experiment, and it made no change to any file
under `report/` or `results/`. What to write, what to cut, and what to claim are
decisions for the project lead.

**What this file does not settle.** Whether the 37 `NONE` points get written,
whether the 23 pages currently sitting on a 6-point sub-item get cut, and whether
the report's limitations section — 6.3 pages that the template scores at zero —
stays as it is. Those are trade-offs between the scoring rubric and the record's
integrity, and this map deliberately stops at naming them.
