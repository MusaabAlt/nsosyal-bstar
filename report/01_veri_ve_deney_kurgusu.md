# 1. Veri ve Deney Kurgusu

> **Taslak durumu.** Bu bölüm KYS rapor şablonu yayımlanmadan önce yazılmıştır;
> başlık numaralandırması geçicidir ve şablon geldiğinde yeniden düzenlenecektir.
> Metindeki her sayı, `docs/RESULTS_LOG.md` içindeki kayıtlı bir çalıştırmaya ya
> da `results/` altındaki bir bulgu dosyasına dayanır; kaynak, ilgili tablonun
> altında belirtilmiştir. Kayıtta bulunmayan hiçbir değer yazılmamıştır.

## 1.1 Veri kümesi

Çalışmanın tek eğitim ve tanı kaynağı, OffensEval-TR 2020 Türkçe alt görevinin
Çöltekin tarafından yayımlanan derlemidir. Etiket şeması ikilidir: `OFF`
(saldırgan) ve `NOT` (saldırgan değil).

| Özellik | Değer |
|---|---|
| Dosya | `offenseval-tr-training-v1.tsv` |
| SHA-256 | `8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa` |
| Satır sayısı | 31.756 |
| `NOT` | 25.625 (%80,7) |
| `OFF` | 6.131 (%19,3) |

*Kaynak: `results/day1_report.json` (dondurulma zamanı 2026-08-14T14:43:33).*

Derlemin okunması yüzeysel göründüğü kadar basit değildir ve bu, sonraki bütün
sayıları etkileyen bir ayrıntıdır. Dosya tırnaklanmamış TSV biçimindedir ve
metin alanlarında gömülü satır sonları üç boşlukla değiştirilmiştir; standart
bir CSV okuyucusu bu dosyayı sessizce yanlış ayrıştırır ve satır sayısını
değiştirir. Bu nedenle okuma işlemi elle sekme ayrıştırmasıyla yapılmakta
(`src/data_io.py`), sonuç ise derlemin SHA-256 özetiyle birlikte kayıt altına
alınmaktadır: raporlanan her sayı, hangi baytlar üzerinde ölçüldüğünü
kanıtlayabilir durumdadır.

Bu okuma yolunun kararlılığı ayrıca doğrulanmıştır: Gün 1'de dondurulan 16
alanın tamamı, bağımsız bir yeniden çalıştırmada birebir yeniden üretilmiştir
(`results/day1_report_rerun.json`; `docs/RESULTS_LOG.md`, 2026-08-15 "Day 1
reproduction check" satırı).

## 1.2 Dondurulmuş sözlük ve eşleşme kuralı

Karşılaştırmanın temel çizgisi olan anahtar kelime süzgeci, ölçüm yapılmadan
**önce** dondurulmuş bir küfür/hakaret sözlüğüne dayanır. Sözlük, sonuçlar
görüldükten sonra hiçbir aşamada değiştirilmemiştir.

| Özellik | Değer |
|---|---|
| Dosya | `karaliste.txt` |
| SHA-256 | `0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b` |
| Girdi sayısı | 695 |

*Kaynak: `results/day1_report.json`.*

Türkçe sondan eklemeli bir dil olduğu için, birebir kelime eşleşmesi sözlüğün
kapsamını sistematik biçimde olduğundan düşük gösterir. Bu nedenle **kök
eşleşmesi** (`hit_root`) benimsenmiştir: bir belirteç, sözlükteki en az üç
karakterlik bir girdiyle başlıyorsa eşleşme sayılır. Türkçeye özgü küçük harfe
çevirme kuralları (`I→ı`, `İ→i`) uygulanır.

Bu tercihin yönü önemlidir ve dürüstlük gereği açıkça belirtilmelidir: kök
eşleşmesi, birebir eşleşmeye kıyasla sözlüğü **daha güçlü** kılar, dolayısıyla
sözlüksüz dilimi küçültür ve çalışmanın kendi savını zayıflatır. Daha zayıf olan
birebir eşleşme seçilseydi, raporlanan boşluk daha büyük görünecekti.

| Eşleşme tanımı | Sözlüğün yakaladığı `OFF` | Sözlüğün kaçırdığı `OFF` |
|---|---:|---:|
| Birebir eşleşme | 1.787 | 4.344 |
| **Kök eşleşmesi (benimsenen)** | **2.239** | **3.892** |

*Kaynak: `results/day1_report.json`; ayrıca `results/01_baseline_berturk/metrics.json`
içindeki `sanity_gate` bloğu bu iki sayıyı (3.892 / 6.131) her çalıştırmada
yeniden doğrular ve uyuşmazlık halinde çalıştırmayı durdurur.*

Çekim eklerinin getirdiği kazanç 452 örnektir. Nihai tablo şudur: **6.131
saldırgan iletinin 3.892'si (%63,5) hiçbir sözlük köküyle eşleşmez.** Bu sayı,
çalışmanın çıkış noktasıdır ve bir modelin değil, süzgecin özelliğidir.

## 1.3 Eğitim / geliştirme ayrımı

Derlem, etikete göre tabakalı biçimde ve sabit tohumla bölünmüştür. Bölünme bir
kez üretilmiş, dosyaya yazılmış ve sonrasında yalnızca okunmuştur; her sonraki
aşama aynı dosyayı yeniden kullanır.

| | Toplam | `NOT` | `OFF` | `OFF` oranı |
|---|---:|---:|---:|---:|
| Eğitim | 26.992 | 21.781 | 5.211 | %19,3 |
| Geliştirme (dev) | 4.764 | 3.844 | 920 | %19,3 |
| **Toplam** | **31.756** | **25.625** | **6.131** | **%19,3** |

*Kaynak: `data/splits/split_seed42.json` (oluşturulma: 2026-08-15T15:02:14,
tohum 42, geliştirme oranı 0,15).*

Bölünmenin kimliği bir **parmak izi** ile sabitlenmiştir: geliştirme kümesindeki
satır kimliklerinin sıralanmış listesinin SHA-256 özeti,
`034415af3a23b388…`. Bu değer üretilen her sonuç dosyasına yazılır. Amacı
şudur: iki sonuç dosyası birbiriyle çeliştiğinde, bunların aynı örnekler
üzerinde ölçülüp ölçülmediği tartışma konusu olmaktan çıkar. Kalibrasyon ve
savunma aşamalarının sürücüleri, parmak izi beklenen değerden farklıysa
çalışmayı başlatmadan durur.

Bölünme dosyası, ham derlemin aksine, sürüm denetimine dâhil edilmiştir. Gerekçe
pratiktir: dosya yalnızca satır kimliklerini içerir, kişisel veri taşımaz ve
kodla birlikte taşınması gerekir; aksi hâlde uzak bir çalışma ortamında depo
klonlandığında bölünme yeniden üretilir ve sessizce farklı bir geliştirme kümesi
oluşabilirdi.

## 1.4 Dilimleme

Çalışmanın merkezî ölçümü, geliştirme kümesinin sözlüğe göre ikiye ayrılmasına
dayanır. Dilim etiketi, §1.2'deki dondurulmuş eşleştiriciyle, model çıktısından
tamamen bağımsız olarak atanır.

| Dilim | Satır | `OFF` | `NOT` | `OFF` taban oranı |
|---|---:|---:|---:|---:|
| `lexicon_hit` | 614 | 355 | 259 | %57,8 |
| `lexicon_free` | 4.150 | 565 | 3.585 | %13,6 |

*Kaynak: `results/01_baseline_berturk/metrics.json`.*

İki dilimin taban oranları belirgin biçimde farklıdır (%57,8'e karşı %13,6).
Bunun doğrudan bir yöntemsel sonucu vardır ve ölçüm yapılmadan önce yazılı
olarak sabitlenmiştir: **dilimler arası karşılaştırma yalnızca `OFF`-duyarlılık
(recall) üzerinden yapılır.** Makro-F1 ve doğruluk gibi ölçütler taban orana
duyarlıdır; iki dilim arasında karşılaştırılmaları yanıltıcı olurdu. Bu kısıt
`phases/01_baseline_diagnosis.md` içinde ön kayıt olarak yer alır ve sonraki
bütün aşamalarda bağlayıcıdır.

## 1.5 Resmî test kümesi ve tek kullanım muhasebesi

Resmî Çöltekin test kümesi, projenin tamamında **tek bir kez** ölçüm için
kullanılmıştır. Geliştirme sırasında — "yalnızca bakmak" amacıyla bile —
okunmamıştır; okunsaydı, sonrasında alınan her tasarım kararı bu kümeden bilgi
almış olacak ve nihai sayı bağımsızlığını yitirecekti.

| Özellik | Değer |
|---|---|
| Test dosyası SHA-256 | `9052784e13248e58…` |
| Altın etiket dosyası SHA-256 | `ae9b0837e948c3d9…` |
| Satır sayısı | 3.528 |
| `NOT` / `OFF` | 2.812 / 716 (%20,3 `OFF`) |

| Dilim | Satır | `OFF` | `NOT` | `OFF` taban oranı |
|---|---:|---:|---:|---:|
| `lexicon_hit` | 491 | 269 | 222 | %54,8 |
| `lexicon_free` | 3.037 | 447 | 2.590 | %14,7 |

*Kaynak: `results/05_final_test/metrics.json`.*

Dilim yapısı geliştirme kümesindekiyle uyumludur (`lexicon_hit` payı geliştirmede
%12,9, testte %13,9), yani iki küme aynı olguyu ölçmektedir.

Tek kullanım kuralı bir söz değil, bir dosyadır. `load_coltekin_test`
çağrıldığında baytlar okunmadan **önce** eklemeli bir açılış günlüğüne kayıt
düşer; çalışma tamamlandığında ayrı bir "harcandı" kaydı yazılır ve bu kayıt
mevcut olduğu sürece aynı fonksiyon çağrıldığında hata verir. Her iki dosya da
sürüm denetimine dâhildir, dolayısıyla kısıt deponun başka bir makinedeki
kopyasında da geçerlidir.

Kayıt, kümenin **iki kez açıldığını** göstermektedir ve bu gizlenmemiştir:

| Açılış | Sonuç |
|---|---|
| 2026-08-16T11:09:00 | Model çıkarımı başlamadan çöktü (stdout yönlendirme sınıfında eksik bir yöntem). Hiçbir tahmin üretilmedi, hiçbir sayı elde edilmedi. |
| 2026-08-16T11:10:36 | Raporlanan tam çalıştırma; "harcandı" kaydı 11:11:44'te yazıldı. |

*Kaynak: `results/05_final_test/TEST_SET_OPENED.json`,
`results/05_final_test/TEST_SET_SPENT.json`.*

Açılış günlüğünün okuma işleminden önce yazılmasının nedeni tam olarak budur:
başarısız bir denemenin kayıttan silinmesi mümkün olmamalıdır. İlk okuma hiçbir
sonuç üretmediği için hiçbir karara etki etmemiştir; ancak "hiçbir şey üretmedi"
ifadesi, kanıt gerektiren bir iddiadır, beyan değil.

## 1.6 Kayıt altına alınmayan veri kaynakları

Dürüstlük gereği belirtilmelidir: proje planında yer alan iki bağımsız Türkçe
derlem (Mayda ve Beyhan) **edinilmemiş ve hiçbir aşamada kullanılmamıştır.**
İlgili dizinler boştur ve bu kaynaklara ilişkin hiçbir ölçüm `docs/RESULTS_LOG.md`
içinde yer almaz. Dolayısıyla bu çalışma, **derlem-içi** (same-source) bir
genelleme iddiası taşır; farklı bir derleme aktarım (cross-corpus transfer)
iddiası taşımaz. Bu sınırlılık §"Sınırlılıklar" bölümünde yeniden ele alınmıştır.

## 1.7 Birincil değerlendirme ölçütü

Bu çalışmanın katkısı, genel sınıflandırma başarımını yükseltmek değil, modelin
**sözlüksel bağımlılığını azaltmaktır.** Değerlendirme ölçütü de buna göre
seçilmiştir.

**Birincil ölçüt: `lexicon_free` diliminde `OFF`-duyarlılık.** Yani, hiçbir küfür
belirteci taşımayan saldırgan içeriğin ne kadarının yakalandığı. Çalışmanın
tanısı bu dilimdeki açığa ilişkindir; müdahale bu dilim için tasarlanmıştır;
dolayısıyla başarının ölçüldüğü yer de bu dilimdir.

Bu ölçütün seçimi **sonuçlar görüldükten sonra yapılmamıştır.** Müdahalenin
hedefi, herhangi bir savunma sayısı üretilmeden önce yazılı olarak sabitlenmiştir:

> "**Targets.** 1a → the lexicon-free false negatives (implicit offense, 35% of
> the unbiased dev sample). 1b → the profanity-bearing false positives that
> perform no offensive act."
>
> — `phases/03_defense_design.md`, tasarım aşamasında, ölçümden önce.

Bu ayrım yöntemsel olarak belirleyicidir. Birden çok ölçüt arasından sonradan
lehte olanı seçmek geçersiz bir uygulamadır; önceden ilan edilmiş bir hedef
üzerinde ölçüm yapmak ise geçerli bir katkı iddiasıdır. Bu raporun iddiası
ikincisidir ve dayanağı, tarih damgalı ön kayıttır.

**İkincil ölçütler — her tabloda birincil ölçütle birlikte raporlanır:**

| Ölçüt | Neden birlikte raporlanıyor |
|---|---|
| Genel makro-F1 | Sistem düzeyinde net etkiyi gösterir; birincil ölçütteki kazanç bunu iyileştirmiyorsa, bu açıkça yazılmalıdır |
| `lexicon_hit` `OFF`-duyarlılık | Modelin zaten iyi olduğu dilimdeki olası bozulmayı gösterir |
| `lexicon_hit` yanlış pozitif oranı | 1b bileşeninin kendi hedefine ulaşıp ulaşmadığını gösterir |
| Duyarlılık farkı (`hit` − `free`) | Farkın *hangi yönden* daraldığını ayırt etmeyi sağlar |

Bu birlikte raporlama zorunluluğu da tasarım aşamasında, olası bir başarısızlık
biçimine karşı önlem olarak yazılmıştır: farkın "yanlış nedenle" daralması, yani
`lexicon_free` yükseldiği için değil `lexicon_hit` düştüğü için daralması. Tasarım
belgesi bunu şöyle kaydeder: *"a within-gap trade where `lexicon_hit` recall falls
and the gap narrows for the wrong reason — which is why all four metrics are
reported together."*

Sonuç olarak bu rapor, birincil ölçütteki kazancı **ölçülmüş bir iyileşme**
olarak sunar ve bu kazancın bedellerini — genel makro-F1'in değişmemesi ve
`lexicon_hit` tarafındaki maliyet — aynı bölümde, aynı tablolarda ve gizlemeden
raporlar. Kazanç da bedel de aynı ön kayıttan doğmaktadır.

**İstatistiksel protokol.** Tüm ölçütler için güven aralıkları, satırlar üzerinde
1.000 yeniden örneklemeli parametrik olmayan bootstrap ile hesaplanır. İki sistem
aynı satırlar üzerinde karşılaştırıldığında **eşleştirilmiş** (paired) bootstrap
kullanılır: satırlar bir kez yeniden örneklenir ve her iki sistem aynı örneklem
üzerinde puanlanır; iki bağımsız güven aralığının karşılaştırılması farkın
belirsizliğini olduğundan büyük gösterirdi. Ayrık dilimler karşılaştırıldığında
(örneğin `hit` ile `free`) bağımsız yeniden örnekleme uygulanır. Farklar,
**işaretine bakılmaksızın** güven aralıklarıyla birlikte raporlanır.

---

### Bu bölümde kullanılan kaynakların özeti

| Kaynak dosya | Sağladığı değerler |
|---|---|
| `results/day1_report.json` | derlem ve sözlük özetleri, 31.756 satır, 6.131 `OFF`, 695 sözlük girdisi, 1.787 / 2.239 / 3.892 eşleşme sayıları |
| `results/day1_report_rerun.json` | 16/16 alanın yeniden üretilmesi |
| `data/splits/split_seed42.json` | eğitim/geliştirme sayıları, tohum, parmak izi |
| `results/01_baseline_berturk/metrics.json` | geliştirme dilim sayıları ve taban oranları, `sanity_gate` |
| `results/05_final_test/metrics.json` | test satır ve dilim sayıları, dosya özetleri |
| `results/05_final_test/TEST_SET_{OPENED,SPENT}.json` | tek kullanım muhasebesi |
| `phases/01_baseline_diagnosis.md` | dilimler arası karşılaştırmanın `OFF`-duyarlılıkla sınırlanması (ön kayıt) |
| `phases/03_defense_design.md` | müdahalenin hedefinin ölçümden önce sabitlenmesi; dört ölçütün birlikte raporlanma zorunluluğu (ön kayıt) |
