# NSosyal B* — Projenin Katmanlı Anlatımı

Bu belge, deponun tamamının (README, `docs/PROJECT_HISTORY.md`, `docs/RESULTS_LOG.md`,
`phases/*`, `src/*`, `phase*.py`, `results/*`, `demo/`, `report/`, git geçmişi)
okunmasından sonra yazılmış bir **anlatım** belgesidir. Yeni hiçbir ölçüm içermez;
her sayı depodaki kayıtlı bir dosyadan alınmıştır.

**Bu belgenin statüsü.** Açıklayıcıdır, otorite değildir. Bir sayı bu belge ile
`results/` altındaki bir JSON dosyası arasında çelişirse, **JSON dosyası geçerlidir.**
Ön kayıt protokolleri (`phases/*.md`), deney günlüğü (`docs/RESULTS_LOG.md`) ve
kayıt (`docs/PROJECT_HISTORY.md`) bu belgenin üstündedir.

**Okuma sırası.** Üç katman birbirinin üstüne biner: Katman 1 tek başına okunabilir,
Katman 2 sistemin nasıl işlediğini verir, Katman 3 her kararın gerekçesine iner.

---

## İçindekiler

- [Katman 1 — Basit anlatım](#katman-1--basit-anlatım)
- [Katman 2 — Sistem nasıl çalışıyor](#katman-2--sistem-nasıl-çalışıyor)
- [Katman 3 — Derinlemesine](#katman-3--derinlemesine)
  - [3.1 `src/data_io.py` — veri okuma ve üç tuzak](#31-srcdata_iopy--veri-okuma-ve-üç-tuzak)
  - [3.2 `src/lexicon.py` — Türkçe eşleştirme](#32-srclexiconpy--türkçe-eşleştirme)
  - [3.3 `src/evaluate.py` — metrik disiplini](#33-srcevaluatepy--metrik-disiplini)
  - [3.4 `src/calibration.py` — kalibrasyon ve seçici tahmin](#34-srccalibrationpy--kalibrasyon-ve-seçici-tahmin)
  - [3.5 `src/augment.py` — başarısız savunma](#35-srcaugmentpy--başarısız-savunma-ama-iyi-tasarlanmış-bir-başarısızlık)
  - [3.6 Faz 09 — projenin en keskin iki ölçümü](#36-faz-09--projenin-en-keskin-iki-ölçümü)
  - [3.7 Faz 08 — küfürsüz yanlış pozitifler](#37-faz-08--küfürsüz-yanlış-pozitifler-neden-oluyor)
  - [3.8 Faz 11 ve 12 — açık soruyu kapatmak ve onarımı yapmak](#38-faz-11-ve-12--açık-soruyu-kapatmak-ve-onarımı-yapmak)
  - [3.9 Demo](#39-demo-demoapppy)
  - [3.10 Rapor ve depo durumu](#310-rapor-ve-depo-durumu)
- [Bu projeyi ayıran şey](#bu-projeyi-diğerlerinden-ayıran-şey)
- [Açık kalan konular](#açık-kalan-konular-deponun-kendi-listesi)
- [Hızlı başvuru: sayı → kaynak dosya](#hızlı-başvuru-sayı--kaynak-dosya)

---

# KATMAN 1 — Basit anlatım

## Tek cümlelik özet

Bu proje bir **ürün** değil, bir **ölçüm çalışmasıdır**: Türkçe saldırgan içerik
tespitinde yapay zekâ modelinin ne kadarının aslında "küfür sözcüğü gördü mü?"
refleksinden ibaret olduğunu sayılarla ölçer — ve bu kusuru modeli yeniden
eğitmeden, karar eşiği katmanında onarmayı dener.

## Problem

Türkçe saldırgan içeriğin **%63,5'i hiçbir küfür sözcüğü içermez.**
("Senin gibilerin oyu yüzünden bu haldeyiz" — hakaret var, küfür yok.)
Klasik kara liste filtreleri bu içeriği hiç görmez. Genel varsayım şudur:
"BERT gibi bir model bu açığı kapatır."

## Bulgu

Kapatmıyor. Aynı model, aynı veri üzerinde:

| Kesit | Saldırgan içeriği yakalama oranı |
|---|---|
| Küfür **içeren** mesajlar | **%89,3** |
| Küfür **içermeyen** mesajlar | **%56,3** |
| **Fark** | **33 puan** (%95 GA sıfırı dışlıyor) |

Ayrık, tek kullanımlık resmî test kümesinde yeniden ölçüldü: fark **%39,7**.
Bulgu tesadüf değil, tekrarlanıyor.

> **Dikkat:** İki fark aralığı örtüşür ([+0,3418; +0,3827]). "Fark test kümesinde
> tutuyor" denebilir; "test kümesinde büyüdü" **denemez**.

## Asıl ince bulgu (projenin en değerli kısmı)

Model aslında küfürsüz saldırganlığı **tanıyor** — sıralama kalitesi (ROC-AUC)
0,8962 ve küfürlü kesitteki 0,9306'dan yalnızca 3,4 puan geride. Yapamadığı şey,
bu içeriği **0,50 karar eşiğinin üstüne çıkarmak**. Puanlar eşiğin hemen altında
yığılıyor.

> Kusur "model göremiyor"da değil, "model gördüğünü karara dönüştüremiyor"da.

Bu, projenin kendi başlangıç iddiasını sonradan **daraltmak** zorunda kaldığı
yerdir ve bu daraltma depoda açıkça kayıtlıdır.

## Çözüm denemeleri

1. **Modeli yeniden eğit** (ters olgusal veri artırımı: küfürleri maskele, masum
   cümlelere küfür ekle) → **BAŞARISIZ.** Hedef kesitte küçük bir kazanç, diğer
   kesitte eşit büyüklükte kayıp, sistem düzeyinde net etki sıfırdan ayırt
   edilemez. Rapor bunu açıkça bir başarısızlık olarak yazar.
2. **Eşiği düzelt** (maliyet türetimli tek eşik, S1b) → **ÇALIŞIYOR.** Eşiği
   0,50'den 0,320188'e indirmek küfürsüz kesitte geri çağırmayı
   0,5180 → 0,6367 çıkarır; bedeli kesinlik kaybıdır ve kaçırmanın yanlış
   işaretlemeden 3 kat pahalı sayıldığı maliyet modelinde bu **kabul edilmiş bir
   takastır**, bir kusur değil.
3. **İnsana devretme katmanı:** %90 kapsam, en emin olunmayan ~%10 insana gider;
   bu kuyruk tüm hataların üçte birini yakalar (dev'de 3,78×, test'te 3,59×).

## Projenin gerçek imzası

Sayılardan çok **yöntem disiplini**: her fazın karar kuralları sayılar üretilmeden
önce git'e işlenir (ön kayıt), sonuç günlüğü asla düzeltilmez (yanlış çıkan
yorumlar görünür kalır), test kümesi kodla kilitlenmiş tek kullanımlık bir
kaynaktır ve başarısızlıklar başarılarla aynı ayrıntıda raporlanır.

---

# KATMAN 2 — Sistem nasıl çalışıyor

## Veri hattı

```
Çöltekin OffensEval-TR 2020 (31.756 satır, %19,3 OFF)
        │  sha256 8509c01c… ile kimliklenmiş
        ├─► %85/%15 katmanlı bölünme (tohum 42) ─► eğitim 26.992 / geliştirme 4.764
        │     └─ data/splits/split_seed42.json'a YAZILIR, bir daha asla üretilmez
        │        dev parmak izi: 034415af3a23b388
        └─► resmî test 3.528 satır ─► KİLİTLİ (tek kullanım, harcandı)

karaliste.txt (695 girdi, dondurulmuş, sha256 0f5a05f5…)
        └─► hit_root() ile her satır etiketlenir:
              lexicon_hit  (614 dev satırı, %57,8 OFF)
              lexicon_free (4.150 dev satırı, %13,6 OFF)
```

**Kritik nokta:** kesitler modelden bağımsız belirlenir. Sözlük eşleşmesi bir
metin özelliğidir, model çıktısı değil. Bu yüzden karşılaştırma döngüsel değildir.

## Model

`dbmdz/bert-base-turkish-cased` (~110M parametre), 3 dönem, yığın 32, lr 2e-5,
`max_len` 128, fp16, %10 doğrusal ısınma, sınıf ağırlığı **yok**, karar eşiği
0,50'de **sabit**, tohum 42, NVIDIA L4.

Tek yapılandırma, hiperparametre taraması **yok** — çünkü tarama hangi kola
verilirse onu kayırır.

## Faz zinciri

| Faz | Ne yapar | Sonuç |
|---|---|---|
| Day 1 | Sözlük eşleşme sayımı | 3.892/6.131 = %63,5 kaçak |
| 01 | BERTurk eğit, kesit başına ölç | 33 puanlık fark **hayatta kalıyor** |
| 02 | 285 FN + 213 FP'yi elle oku | Kusur "kelime dağarcığı"; gürültü %10 (%30 değil) |
| 03 | Savunma: ters olgusal veri artırımı | Ölçülmüş **başarısızlık** |
| 04 | Kalibrasyon + risk-kapsam | Ham model zaten kalibre; devretme kesit-kör |
| 05 | Resmî test, tek geçiş | Fark tekrarlanıyor (+0,3970); küme **harcandı** |
| 06 | Çevrimdışı demo | 885,9 MB paket, sıfır ağ çağrısı |
| 07 | Rapor iskeleti | 6 boşluk açıkça işaretlendi |
| 08 | Sözcük düzeyi analiz | Küfürsüz FP'lerin kaynağı: **deiktik** dil |
| 09/1 | Eşikten bağımsız karşılaştırma (AUC) | **Merkezî iddia daraltıldı** |
| 09/1b | Kazanç sıralamadan mı, eşikten mi? | **19 satırın çizgiyi geçmesi** |
| 11 | Kesit başına kalibrasyon | Puan düşüklüğü **taban-oran-doğru** |
| 12 | Eşik politikası | **Tek eşik yeterli** (S1b) |
| 15 | Deiksis hücre sayımları | Yalnızca sayım, ölçüm yok |

> Faz 02, 05, 06, 07, 10 protokolleri ya sayı üretmez ya da okuma/rapor
> fazlarıdır. Sayı üreten yedi fazın hepsi ön kayıtlıdır.

## Dosya rolleri

| Yol | Rol |
|---|---|
| `config.py` | **Her yol burada.** Hiçbir betik konum gömmez. `NSOSYAL_ENV=colab\|kaggle` ile aynı kod yerelde, Colab'da, Kaggle'da değişmeden koşar. |
| `src/` | Ölçümün tek kaynağı. Betikler buradan içe aktarır, kural kopyalamaz. |
| `phase*.py` | Faz başına bir çalıştırıcı, depo kökünde. |
| `phases/*.md` | **Ön kayıt protokolleri**; sayıdan önce commit edilmiş. |
| `results/*/` | Makine okunur JSON + insan okunur `findings.md`. |
| `docs/RESULTS_LOG.md` | 60+ satırlık, **yalnızca ekleme yapılan** deney günlüğü. |
| `docs/PROJECT_HISTORY.md` | Tam kayıt — neyin yanlış çıktığı dahil. |
| `demo/app.py` | Stdlib `http.server` ile çevrimdışı arayüz. |
| `report/` | Türkçe rapor metinleri + docx üreticisi. |
| `tests/` | Doğrulanmış biçim tuzakları için gerileme testleri. |

---

# KATMAN 3 — Derinlemesine

## 3.1 `src/data_io.py` — veri okuma ve üç tuzak

Bu modül bir "CSV okuyucu" değil, bir **savunma katmanıdır**.

### Tuzak 1 — tırnaksız, kaçışsız TSV

Çöltekin TSV'sinde tırnak ve kaçış yoktur; orijinal tweet'lerdeki satır sonları
üç boşlukla değiştirilmiştir. `pandas.read_csv` bu dosyayı **sessizce bozar.**
Bu yüzden okuma satır satır, elle `\t` bölerek yapılır. Bir tweet'in içinde
gerçek bir tab varsa satır atılmaz — ortadaki alanlar tekrar birleştirilir,
çünkü **id her zaman ilk, etiket her zaman son alandır.**

### Tuzak 2 — yanlış uzantılı altın etiket dosyası

`offenseval-tr-labela-v1.tsv` adı `.tsv`, içeriği **virgül ayrımlıdır** ve
başlığı yoktur. Ayrı bir okuyucu (`read_gold_labels`) vardır.

### Tuzak 3 — 3'lü etiketin ikiliye indirgenmesi

Mayda/Beyhan 3'lü etiket kullanır. İndirgeme `LABEL_MAP_3TO2` adlı
**adlandırılmış sabittir**; betik içine gömülü bir karar değil. Haritada olmayan
bir etiket gelirse kod tahmin etmez, **gürültülü biçimde patlar** — çünkü
beklenmedik bir etiket değeri "kaynak dosya sandığımız şey değil" demektir.

### Etiket kontrolü kılığında ayrıştırma kontrolü

`assert_binary_labels()` `{OFF, NOT}` dışında bir değer görürse durur. Beklenmedik
etiket değerleri bozuk bir TSV okumasının imzasıdır.

### Bölünme disiplini

`stratified_split()` iki özelliği garanti eder:

- **Sıra bağımsızlığı** — karıştırmadan önce her etiket kovası id'ye göre
  sıralanır, yani dosya okuma sırası değişse bile bölünme değişmez.
- **Adımlar arası yeniden üretilebilirlik** — BERTurk, savunma ve kalibrasyon
  katmanı *aynı* dev kümesinde ölçülmelidir, yoksa karşılaştırma matrisi farklı
  verilerdeki sistemleri karşılaştırır.

**Dosya otoritedir, algoritma değil.** Bölünme bir kez üretilip
`data/splits/split_seed42.json`'a yazılır. Sonraki her çalıştırma dosyayı
**yükler ve doğrular**; ayrıca "taze bir bölünme aynısını üretir miydi?" diye
kontrol edip sonucu (`matches_regeneration`) sonuç dosyasına yazar — sessizce
düzeltmez, **rapor eder.**

`load_split()` üç şeyi reddeder:

1. Derlem hash'i değişmişse,
2. Kayıtlı bir id derlemde yoksa,
3. train/dev kesişiyorsa — *"her dev sayısı aslında eğitim doğruluğu olurdu."*

### Test kümesi kilidi — projenin en özgün mühendislik parçası

```python
load_coltekin_test(run_final_test=False)   # varsayılan: PermissionError
```

Üç katman:

1. Çağıran açıkça `run_final_test=True` geçmelidir (pratikte `--run_final_test 1`
   bayrağı).
2. `results/05_final_test/TEST_SET_SPENT.json` **depoda commit'lidir.** Varsa
   yükleme tümüyle reddedilir. Yani "sadece bir kez dokunuldu" sözü, *hatırlayan
   kişiye* değil, **taze bir klonda bile geçerli olan bir dosyaya** bağlıdır.
3. `TEST_SET_OPENED.json` — **baytlar okunmadan ÖNCE** yazılan ekleme-yalnızca
   günlük. Bu yüzden çöken bir çalıştırma bile iz bırakır. Dosya sistemi salt
   okunursa kod okumayı reddeder; muhasebeyi sessizce atlamaz.

**Ve bu gerçekten işledi.** Faz 05'te test kümesi **iki kez açıldı**:
11:09:00'daki deneme `AttributeError: 'Tee' object has no attribute 'isatty'`
ile hiçbir ileri geçiş yapmadan çöktü; 11:10:36 tam çalıştırmaydı; harcama kaydı
11:11:44'te yazıldı. Her ikisi de kayıtta. Gizlenmedi.

---

## 3.2 `src/lexicon.py` — Türkçe eşleştirme

```python
def tr_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()
```

Python'un `str.lower()`'ı `I → i` yapar; İngilizce için doğru, Türkçe için
yanlıştır. Sözlükle yapılan **her** karşılaştırma bu fonksiyondan geçer.

### İki eşleştirme kuralı

| Kural | Ne yapar | Yakalanan OFF |
|---|---|---|
| `hit_literal` | Tam sözcük eşleşmesi. Naif filtrenin yaptığı şey; her çekimde başarısız (*aptalsın, aptallara*). | 1.787 |
| `hit_root` | Kök/ön ek eşleşmesi (`MIN_ROOT_LEN = 3`). **Benimsenen tanım.** | 2.239 |

Buradaki dürüstlük hamlesi kritiktir: **güçlü eşleştirici seçilmiştir.** Çünkü
güçlü eşleştirici sözlüğü güçlendirir, `lexicon_free` kesitini küçültür ve
**projenin kendi tezini zayıflatır.** Zayıf kuralla raporlanan fark daha büyük
görünürdü.

### İki bilinen kusur — ikisi de aynı muhafazakâr yönde

| Kusur | Etki | Ölçülen sonuç |
|---|---|---|
| **Kirlenme**: `allah`→~130 satır, `emi`→`eminim`, `mal`→`malatya`, `göt`→`götürür`, `cim`→`cimbom` | 614 hit satırının 248'i şüpheli-kök-yalnız (175 NOT / 73 OFF) | Bunlar çıkarılınca fark **+0,3301 → +0,3662** *büyür* |
| **Kör nokta**: `MIN_ROOT_LEN=3` yüzünden `aq`, `am`, `ag`, `oc`, `oç` **hiç ateşlenemez** | 565 `lexicon_free` OFF satırının 28'i (%4,96) bunlardan taşır; `aq` için P(OFF\|t) = 0,9860 | Üst sınır: fark **+0,3529**'a çıkar |

Yani her iki bilinen tanım kusuru da raporlanan sayının **eksik tahmin** olduğunu
gösterir. Bu, savunulması en kolay hata yönüdür.

> İkinci satır bir **sınırdır, bir ölçüm değildir** — "28 satırın hepsi doğru
> sınıflandırılsaydı" varsayımına dayanır.

### Kasıtlı olarak korunan bir tuhaflık

`tokens()` `\w+` ile böler, `@` düşer, dolayısıyla `SKIP` içindeki `@user` girdisi
hiç ateşlenmez. Zararsız olduğu doğrulanmıştır (hiçbir sözlük girdisi `user`'a
eşit veya onun ön eki değildir) ve **kasten bırakılmıştır**: `day1_report.json`
bu davranışla dondurulmuştur; sessizce değiştirmek o kaydın yeniden
üretilebilirliğini bozardı. Düzeltilecekse **kayıtlı, kasıtlı bir yeniden
dondurma** olarak düzeltilmelidir.

### Kesit rafinasyonu

`lexicon_free` kesitinin içine kaçmaması gerekenler ayrıca işaretlenir:

- `is_censored()` — `o***` gibi sembolle maskelenmiş küfür. Söz **küfürlüdür**;
  sözlük yüzey maskelemesi yüzünden kaçırmıştır, örtük saldırganlık olduğu için
  değil.
- `is_abbrev_profanity()` — `aq`, `mk`, `amk` gibi kısaltmalar. Yine yüzey
  biçimi kaçırması.
- `is_sensitive()` — siyasi/dinî işaretçiler. **Yalnızca demo ve rapor örneği
  seçmek için**; asla istatistiksel değerlendirmeden satır düşürmek için değil
  (bu, manşet sayılara seçim yanlılığı sokardı).

---

## 3.3 `src/evaluate.py` — metrik disiplini

Bu modül, anahtar sözcük filtresi, BERTurk, savunma ve kalibre sistemin
**hepsinin tam olarak aynı kod yolundan** puanlanması için vardır. Sistem başına
biraz farklı hesaplanan bir metrik, karşılaştırma tablosunu anlamsız kılar.

### İki kasıtlı seçim

1. **Saf standart kütüphane.** Modül düzeyinde numpy/sklearn/torch yoktur. Sebep:
   metrikler yerel Python venv'inde birim testine tabi tutulabilsin — **GPU
   harcanmadan önce.**
2. **sklearn ile değiştirilmedi, sklearn'e karşı çapraz kontrol edildi.**
   `sklearn_report()` insan okunur raporu üretirken aynı çağrıda sklearn'ün
   makro-F1'iyle kendi hesabını `1e-9` toleransla karşılaştırır. Uyuşmazsa
   **çalıştırma durur**; ikisinden biri yanlıştır ve hangisi olduğu bilinmez.

### Üç ayrı önyükleme yordamı ve hangisinin nerede doğru olduğu

| Fonksiyon | Şema | Nerede kullanılır |
|---|---|---|
| `bootstrap_ci` | Tek sistem, tek küme | Tekil metrikler |
| `bootstrap_delta_ci` | **Eşleştirilmiş** — bir örneklem, iki sistem aynı satırlarda | Savunma vs. ham karşılaştırması |
| `bootstrap_gap_ci` | **Bağımsız** — ayrık kesitler ayrı örneklenir | Kesitler arası fark |

Bu ayrım basit ama kritiktir: iki sistem aynı satırları gördüğü için bağımsız
sayılamaz (ayrı GA'ları karşılaştırmak farkın belirsizliğini abartır ve gerçek
bir değişimi gizleyebilir); iki kesitte ise ortak satır yoktur, dolayısıyla
eşleştirilecek bir şey de yoktur.

Metriğin tanımsız kaldığı yeniden örneklemeler (ör. hiç OFF çekilmemişse
OFF-geri-çağırma) **0 sayılmaz** — düşürülür ve `n_boot_undefined` olarak
sayılır.

### Kodun içine yazılmış bağlayıcı kısıt

`score_by_slice` docstring'i şunu belgeler: kesitler arası karşılaştırma
**yalnızca OFF-geri-çağırma** ile yapılabilir. Çünkü taban oranlar %57,8'e karşı
%13,6'dır; makro-F1 veya doğruluk farkı **sınıf dengesini model davranışı gibi
raporlar.** OFF-geri-çağırma `gold=OFF` üzerine koşullandığı için bundan
bağışıktır.

Bu kısıt Faz 01 ön kaydında sabitlendi ve **sonraki her fazı bağlar.**

---

## 3.4 `src/calibration.py` — kalibrasyon ve seçici tahmin

İki şey kasten ayrı tutulur:

- **Kalibrasyon** karara iliştirilen olasılığı değiştirir; **kararı değiştirmez**
  (sıcaklık ölçekleme monotondur, argmax sabittir) ve satır **sıralamasını
  değiştirmez.**
- **Seçici tahmin** yalnızca o sıralamayı kullanır; olasılık değerlerini asla.

Sonuç mantıksal olarak zorunludur: **sıcaklık, risk-kapsam eğrisini hareket
ettiremez.** Bu, `phases/04_calibration.md` içinde **C4-3 olarak sayı görülmeden
önce tahmin edildi** ve `verify_rc_invariance()` ile sayısal olarak doğrulandı:
maksimum mutlak fark **0,00e+00**. Cebirden çıkarılıp "öyledir" denmedi; ölçüldü.

### Diğer tasarım ayrıntıları

- `fit_temperature` — `log T` üzerinde altın-oran araması; önce kaba bir ızgara
  minimumu kuşatır. Türev gerekmez (bağımlılıksız kalır). `T` bir ölçek
  parametresi olduğu için arama log uzayındadır: yarıya indirmek ve iki katına
  çıkarmak aynı sayıda adım tutmalıdır.
- **Sınır bayrağı** (`at_boundary`) — arama sınırına oturan bir uyum, uyum
  değildir; NLL kenarda hâlâ düşüyor demektir ve bu, skorların etiket hakkında
  az bilgi taşıdığının işaretidir. Sınırı "sıcaklık" diye raporlamak bir ölçüm
  gibi görünürdü, bu yüzden bayraklanır.
- `EPS = 5e-7` — tahmin dökümleri 6 ondalıkla yazıldığı için `0.000000` gerçekte
  `[0, 5e-7)` demektir; orta nokta savunulabilir tek değerdir.
  `saturated_count()` bu tabana/tavana çarpan satırları **sessizce emmez,
  raporlar** (C4-5).
- `ece()` — **işaretli** boşluk da döndürür. ECE tek başına işaretsizdir ve
  "aşırı mı, eksik mi güvenli?" sorusunu yanıtlayamaz; negatif işaret güvenin
  doğruluğu aştığını, yani aşırı güveni gösterir.
- `apply_threshold` — devretme kararının kesit başına dökümünü de üretir.
  `capture_lift` 1'den büyükse devretme, hataları yakalamada rastgeleden iyidir.
- `bootstrap_operating_point` — eşik **sabit tutularak** yeniden örnekler, çünkü
  eşik CAL üzerinde seçilmiştir; her yeniden örneklemede yeniden seçmek farklı,
  kendi kendini ayarlayan bir yordamı ölçerdi.

### Ölçülen sonuç

Ham BERTurk'ün uydurulan sıcaklığı **0,9948** — yani zaten kalibredir. 20 kutuda
ECE ölçekleme sonrası hafifçe **kötüleşir**, ki bu bir no-op artı kutu
gürültüsünün görüntüsüdür ve 15-kutu manşetinin arkasına saklanmadan
raporlanmıştır. Savunma varyantı ise **3,8× daha kötü kalibredir** (T = 1,9732;
EVAL'in 2.382 satırının 1.958'i en üst kutuda, 0,9943 ortalama güvenle %93,72
doğruluk).

---

## 3.5 `src/augment.py` — başarısız savunma, ama iyi tasarlanmış bir başarısızlık

İki simetrik operasyon, **yalnızca eğitim bölütünde** (dev asla artırılmaz):

- **1a** — gold-OFF satırlarda küfrü maskele, etiket OFF kalsın → saldırganlık
  kelimede değil yapıda aransın.
- **1b** — gold-NOT satırlara saldırgan olmayan bir işlevde küfür ekle, etiket
  NOT kalsın → küfür varlığı tek başına saldırgan bir eylem değildir.

### C1 kısıtı — desenler dev'den türetilemez

1b'nin ekleme desenleri, eğitim bölütü içindeki **5-katlı çapraz doğrulamanın
kat-dışı (OOF) hatalarından** çıkarılır. Dev'den türetmek, raporlanan yanlış
pozitif azalmasının bir kısmının modeli değil **şablonu** ölçmesi demek olurdu.

Kısıtın operatör kümesini gerçekten değiştirdiğinin kanıtı: `NON_PERSON_TARGET`
(*"sinüzit kadar şerefsiz bişey yok"*) ve `ADVERBIAL` (*"salak salak
gülüyorum"*) desenleri **yalnızca eğitim örnekleminde** göründü, dev-türevli
tasarımda yoktu.

OOF makro-F1 0,8230 / OFF-R 0,6985 / OFF-P 0,7280 — dev'in
0,8271 / 0,6902 / 0,7488 değerlerine yakın olması, OOF'un seçilme gerekçesidir.

### C2 kısıtı — 1a etiket gürültüsü üretmemeli

`qualifies_for_masking()` kasten muhafazakârdır. Bir satır ancak şu koşullarda
maskelenir:

1. Şüpheli-kök-olmayan bir küfür token'ı taşır (`SUSPECT_ROOTS` dışlanır),
2. Birden fazla küfür yoktur (tekrar, küfrün cümleyi taşıdığı anlamına gelir),
3. Küfür yalnızca bir dolgu değildir (`FILLER_TOKENS`),
4. **İkinci kişi hitabı** küfür dışındaki bir token'la taşınır (zamirler veya
   `-sın/-siniz/-dın` ekleri, ≥5 karakterli token'larda),
5. Küfür bir hakaret başının önünde değildir (`orospu çocukları` →
   `[MASK] çocukları` felaketi),
6. Maskeleme sonrası ≥8 içerik token'ı kalır,
7. Küfür payı ≤%20'dir.

**Sarkazm kasten tespit edilmez**: yüksek kesinlikli bir ipucu yoktur, dolayısıyla
nitelendirici bir yapı olarak iddia edilmez.

Verim: 5.211 gold-OFF satırın yalnızca **382'si (%7)**. Az ama temiz satır, çok
ama gürültülü satırdan iyidir.

### İnceleme kapısı — metriklerin göremeyeceği üç kusur

Eğitim başlamadan önce artırılmış satırlar **elle okundu** ve üç kusur yakalandı:

1. Şüpheli kök yanlış eşleşmeleri maskeleniyordu (`malsef` → *maalesef* yazım
   hatası, dinî bir ifadedeki `Allah'ın`, `MALLARI`),
2. Küfrün *kendisinin* hakaret olduğu satırlar niteleniyordu,
3. 1b cümle ortasına ekleme yapıp bozuk sözdizimi üretiyordu (*"Neden gelecek
   kişilere mâni burada salak olan yok oldunuz?"*) — bu, modele **"bozuk
   sözdizimi + küfür = NOT"** öğretirdi.

Her biri bir kurala **ve bir gerileme testine** dönüştü. **Hiçbiri sonradan bir
toplam metrikte görünmezdi.**

`_splice()` ayrıca konumu rastgeleleştirir (başa / sona / cümle sınırına) —
çünkü ilk sürüm her şeyi sona ekliyordu, ki bu **"sondaki küfür = NOT"**
konumsal kestirmesini öğretirdi. Uzun satırlar 1b kaynağı olarak dışlanır:
`max_len=128`'de eklenen parça budanabilir ve geriye hiçbir şey öğretmeyen bir
kopya NOT satırı kalır.

**Kasten uygulanmayan bir desen var:** bir kişiye yöneltilmiş taze bir hakaret
eklemek. Bunu satırı gerçekten saldırgan hâle getirmeden güvenilir biçimde
sentezlemek bu filtrenin garanti edemeyeceği bir şeydir — C2'nin yasakladığı
etiket gürültüsü probleminin ayna görüntüsü olurdu.

### Ve sonuç yine de başarısız

| Ölçüt | ham | +1a | +1a+1b | +1a+1b+D |
|---|---|---|---|---|
| makro-F1 | 0,8271 | 0,8244 | 0,8173 | 0,8202 |
| `lexicon_free` OFF-R | 0,5628 | 0,5204 | 0,5841 | **0,5965** |
| `lexicon_hit` OFF-R | 0,8930 | 0,8873 | 0,8282 | 0,8507 |
| `lexicon_hit` FP oranı | 0,1815 | 0,1737 | 0,1853 | **0,1931** |
| Yanlış pozitif (toplam) | 213 | 182 | 232 | 245 |
| — küfür token'ı yok (vekil) | 185 | 156 | 205 | 215 |

Ham'a karşı eşleştirilmiş farklar (tam geliştirme kümesi, n = 4.764):

| Ölçüt | Fark | %95 GA | Sıfırı dışlıyor mu |
|---|---|---|---|
| Sistem makro-F1 | −0,0069 | [−0,0185; +0,0052] | Hayır |
| `lexicon_free` OFF-R | **+0,0336** | [+0,0052; +0,0662] | **Evet** |
| `lexicon_hit` OFF-R | **−0,0423** | [−0,0778; −0,0109] | **Evet** |

Okunuşu:

- **1a hedeflediği şeyde modeli kötüleştirdi** (−0,0425, GA sıfırı dışlıyor).
  Muhtemel mekanizma: eğitimde `[MASK]` token'ı var, çıkarımda hiç yok.
- **1b kendi amacını ıskaladı**: düşürmek için inşa edildiği `lexicon_hit` FP
  oranı **yükseldi** (0,1815 → 0,1853).
- **Dört ayrı çalıştırma yapılmasının bedeli tam burada ödendi**: küfürsüz FP
  artışı (185 → 215) doğru şekilde **1b ve D'ye** atfedildi; 1a tek başına onu
  156'ya *düşürmüştü*. Birleşik tek bir çalıştırma 1a'yı suçlardı.

---

## 3.6 Faz 09 — projenin en keskin iki ölçümü

### Stage 1 — eşikten bağımsız karşılaştırma

**Soru:** 33 puanlık farkın ne kadarı "eşik nerede duruyor", ne kadarı "model ne
kadar iyi sıralıyor"?

Ön kayıtta eşikler **veriden değil, bir tasarım hesabından** sabitlendi:
Hanley–McNeil standart hataları, yalnızca dört dondurulmuş payda ve *varsayılan*
bir AUC ile, bu veri kümesinin farkı ancak **±0,03–0,04** çözünürlükte
ayırabileceğini söylüyordu. Dolayısıyla:

- **LARGE**: G ≥ 0,05
- **SMALL**: G < 0,02
- **Arası**: önceden **sonuçsuz** ilan edildi — sonradan yorumlanmaya açık
  bırakılmadı.

Ayrıca sabitlenenler: beraberlik yakınsaması (yarım kredi), katmanlı önyükleme
şeması, **beş dallı, sıralı, tüketici bir karar kuralı** (veri yüklenmeden önce
her sınırın iki yanında birim testine tabi tutuldu), sonradan tarafları
savunmak için **PR-AUC devşirmenin açık yasağı** (PR-AUC taban orana duyarlıdır)
ve **içerikle köken doğrulama**: girdi dökümü sha256 ile sabitlendi ve aşama,
kayıtlı sekiz Faz-01 sayısını yeniden üretmedikçe hiçbir şey hesaplamadı. Üretti.

| | `lexicon_hit` | `lexicon_free` |
|---|---|---|
| taban oran | 0,5782 | 0,1361 |
| **ROC-AUC** | **0,9306 [0,9102; 0,9495]** | **0,8962 [0,8821; 0,9095]** |
| 0,50'de OFF-R | 0,8930 | 0,5628 |

**G = +0,0345 [+0,0103; +0,0585] → `INTERMEDIATE`.** Aralık sıfırı dışlar
(gerçek bir sıralama farkı vardır) ama nokta kestirim "önemsiz" bandındadır ve
**aralık üç bandın hepsine yayılır** — tam da tasarım hesabının öngördüğü
çözünürlük.

Skor dağılımları, gold-OFF: medyan **0,9650** (hit) vs **0,5861** (free);
0,5'in altında kalan pay **%10,7** vs **%43,7**.

Duyarlılıklar: S1 (`MIN_ROOT_LEN` sızıntısı giderilmiş) fark **+0,0399**;
S2 (şüpheli-kök satırları çıkarılmış) fark **+0,0062** — küçüklük tabanının
altında; S3 (beraberlik yakınsaması) **tam olarak hiçbir şey** değiştirmedi.
AP değerleri (0,9477 vs 0,6479) raporlandı ve C9-9 gereği karara **kabul
edilmedi.**

#### Bu ölçüm merkezî iddiayı daralttı

- **Eskiden:** *"model saldırgan kelime dağarcığını tespit ediyor, saldırgan
  eylemi değil."*
- **Şimdi:** model küfürsüz saldırganlığı **sıralıyor**, ama **eşiğin altına
  puanlıyor.**

Eski iddia yanlıştı çünkü tümüyle sabit 0,50 eşiğindeki davranıştan
çıkarılmıştı ve sabit eşikteki bir geri çağırma farkı "daha kötü sıralıyor" ile
"daha düşük puanlıyor"u **ayırt edemez.** Faz 08'e kadarki her faz geri çağırma
kullandı — taban orandan bağışık ama **eşiğe bağımlı** bir ölçüt.

**Tanı geri çekilmedi, taşındı:** ayırt etmeden karara. Operasyonel başarısızlık
değişmedi — dağıtılan eşikte küfürsüz saldırgan içeriğin neredeyse yarısı
işaretlenmiyor.

### Stage 1b — kazanç sıralamadan mı, eşikten mi?

`+1a+1b+D`'nin +0,0336'lık `lexicon_free` kazancı daha iyi sıralamadan mı,
kayan puanlardan mı geldi?

Ön kayıt (C9-12…C9-17) şunları sabitledi: eşleştirilmiş önyükleme; **kontrol
olarak `run_raw`, ikame edilemez** (her kayıtlı skalerde Faz-01 dökümüyle
uyuşsa bile); AUC'nin kendi ölçeğinde gerekçelendirilmiş **0,01 tabanı** (0,01 =
o kesitteki 565 × 3.585 = 2.025.525 OFF/NOT çiftinin %1'i); ve **C9-16: sayı
var olmadan önce kaydedilmiş bir tahmin** — eğer mekanizma küresel bir puan
kayması ise, `lexicon_hit` AUC'si de düz kalmalı, geri çağırması düşerken.

| kesit | AUC kontrol | AUC tedavi | **ΔAUC** | karar |
|---|---|---|---|---|
| `lexicon_free` (birincil) | 0,8962 | 0,8906 | **−0,005587 [−0,013387; +0,002366]** | **`FLAT`** |
| `lexicon_hit` (kontrol) | 0,9306 | 0,9052 | **−0,025401 [−0,042863; −0,008646]** | **`ORDERING WORSENED`** |

`FLAT`, önceden *"eşik geçişi, daha iyi sıralama değil"* diye adlandırılmış
2. daldır. **Sınırlı** bir null'dır: üst uç +0,0024, önceden sabitlenmiş 0,01
tabanının bir mertebe altındadır. Yani +0,0336'yı açıklayacak büyüklükte bir
sıralama kazancı **kanıtlanmamış değil, dışlanmıştır.**

**Mekanizma tam olarak sayıldı: tüm etki 19 satırın çizgiyi geçmesidir.**
`lexicon_free` gold-OFF geçişleri **+52/−33 = net +19**; `lexicon_hit`
**+13/−28 = net −15**. 19/565 ve −15/355 kayıtlı geri çağırma farklarını
**on ondalığa kadar birebir** yeniden üretir; gold-NOT netleri (+29, +3)
toplamı +32, kayıtlı 213 → 245 yanlış pozitif artışıyla eşleşir.

**Ve tekdüze bir kayma da değil:** `lexicon_free` gold-OFF medyanı
0,5861 → 0,7818 yükselirken **Q1 düşer** (0,2162 → 0,0776) ve Q3 yükselir
(0,8193 → 0,9921) — puanlar iki uca birden itilmiştir. Bu, kayıtlı aşırı
güvenle (T = 1,9732, ECE 3,8×) **tutarlıdır** ve onun tarafından **kanıtlanmış
değildir.**

**C9-16'nın tahmini başarısız oldu — ve bilgilendirici olan kısım budur.**
Kontrol düz kalmadı; orada sıralama ölçülebilir biçimde kötüleşti. Yani müdahale
tekdüze bir yeniden kalibrasyon değildir: küfrün *bulunduğu* yerde sıralamayı
bozdu, yardım etmek için inşa edildiği kesitte ise sıkı bir sınır içinde
değiştirmedi. Kesitler arası AUC farkı **+0,0345 → +0,0146**'ya daralır — ama
`lexicon_free` yükseldiği için değil, `lexicon_hit` düştüğü için. Bu, Faz 03'ün
**tasarım anında adlandırdığı başarısızlık modunun** (yanlış nedenle daralan
fark) gerçekleştiği anlamına gelir; üstelik artık eşik yerleşimine bağlı
olmayan bir ölçütte görünür, ki geri çağırma sürümü tartışmayla savuşturulabilirdi.

### C9-8 — bir şekil kanıt olmaktan çekildi

Stage 1'in "eşleştirilmiş çalışma noktaları" maddesi, *"eşik karışıklığını
gidermenin iki farklı yolu"* olarak tanımlanmıştı. İlk taslak manşeti:
`lexicon_free` geri çağırma **0,9681**, `lexicon_hit`'in işaretleme oranında —
*"sıralama en başından oradaydı"* diye okunmuştu.

**Şartname kusurluydu.** O karşılaştırmalar **eşik** karışıklığını giderir,
**taban oran** karışıklığını tümüyle bırakır: kesinlik doğrudan taban orana
bağlıdır ve sabit bir işaretleme oranındaki geri çağırma da öyledir, çünkü bir
kesitin tepe %q'sunda hangi satırların bulunduğu o kesitin karışımına bağlıdır.
%57,8 ve %13,6 taban oranlı iki kesit arasında — yani aşamanın kontrol etmek
için var olduğu tam değişken — hiçbiri sıralama kalitesi hakkında kanıt olamaz.
0,9681 rakamı **kesinlik 0,2224** karşılığında, %13,6'sı saldırgan olan bir
kesitin %59'u işaretlenerek satın alınmıştı.

**Dört şekil de kanıt olmaktan çekildi ve raporda hiçbir yerde görünmüyor.**
C9-8 maddesi **commit edildiği hâliyle bırakıldı**, üzerine kusuru belirten
tarihli bir ek yazıldı — sonuç günlüğüyle aynı disiplin. Bu bir **şartname
kusuru** olarak kaydedildi, bir bulgu olarak değil: ölçülen hiçbir şey yanlış
değildi, şartname yanlıştı.

---

## 3.7 Faz 08 — küfürsüz yanlış pozitifler neden oluyor?

Akademik danışmanın sorusu: hiç küfür token'ı taşımayan 118 yanlış pozitifi ne
açıklıyor?

Ön kayıt (C8-1…C8-11) şunları sayı üretilmeden önce sabitledi: istatistikler
**yalnızca eğitim bölütünden**, belge frekansı sayımı, top-200 havuz, birincil
sıralama **binom z**, ikincil olarak fazla-OFF-satır sayısı, eşik
**|z| ≥ 3,6623** (200 test üzerinde Bonferroni, iki yönlü α = 0,05) artı 1,5×
etki tabanı, ve sözlük üyeliği kuralı olarak **`hit_root` — tam eşleşme değil.**

Son madde kritiktir: tam eşleşme, çekimli küfrü "sözlük dışı" gruba iter ve
**test edilen bulguyu imal ederdi.**

### Sonuçlar

Eğitim taban oranı varsayılmadı, hesaplandı: **0,193057**. Belge frekansına göre
ilk 200 token'ın **2'si** karalistede (`amk` P(OFF|t) = 0,9554, z = 31,68;
`allah` 0,2784, z = 5,59), **19'u** sözlük dışı güçlü-OFF, **5'i** güçlü-NOT,
**174'ü** kayda değer değil. Yani çarpıklık küçük bir kelime dağarcığında
yoğunlaşmıştır, yayılmış değildir.

İki ağırlıklandırma öğretici biçimde ayrışır: fazla-OFF-satır sayısına göre ilk
sıralar `user` (+282,0) ve `bu` (+255,1) — bir yer tutucu ve bir işaret sıfatı,
ikisi de beyan edilen eşiklere göre *kayda değer değil*. Yüksek frekanslı
token'lar önemsiz çarpıklıklardan büyük mutlak fazlalıklar biriktirir; z'nin
birincil olmasının sebebi budur.

### Ön kayıtlı test

A = 118 küfürsüz FP; B = 3.631 doğru negatif (dev gold-NOT 3.844 eksi 213 FP),
A'nın (sözlük eşleşmesi × token-sayısı çeyreği) dağılımına yeniden
ağırlıklandırılmış.

| karşılaştırma | A | eşleşmiş B | fark | karar |
|---|---|---|---|---|
| **grup 2 (ön kayıtlı)** | 0,3983 (47/118) | 0,1917 | **+0,2066 [+0,1216; +0,2960]** | **DESTEK** |
| geniş havuz (df ≥ 30) | 0,6017 (71/118) | 0,3000 | +0,3017 [+0,2155; +0,3872] | — |
| **grup 3 kontrolü (güçlü-NOT)** | — | — | **−0,0032 [−0,0500; +0,0506]** | **null** |

**Yük taşıyan sonuç kontroldür.** Eğer 118 satır sadece daha uzun veya daha
tuhaf olsaydı, **her iki** çarpıklık yönünde de yükselme gösterirlerdi.
Göstermiyorlar — etki uzunluğa veya kayda değil, **OFF-çarpık kelime
dağarcığına** özgüdür.

İki bağımsız birleştirme kontrolü geçti: 118'in 6'sı sözlük-eşleşmeli satırlarda
oturuyor (Faz 02'nin ayrıca kaydettiği sayıyla aynı) ve `aq` bunların
**hiçbirinde** geçmiyor.

### Bileşim (post-hoc, karar alanı yok)

Yüksek çarpıklıklı 19 sözlük-dışı token'ın 10'u **deiktik**, **5'i ikinci kişi
zamiri** (`sen`, `senin`, `siz`, `sizin`, `sizi`); yanlarında `lan`, `bak`,
`adam`, `bunlar`, `onlar`. P(OFF|`sizin`) = **0,4533** (375 satır),
P(OFF|`bunlar`) = **0,4592** (233 satır) — taban oran 0,1931'e karşı.

Danışmanın **yapısal hipotezi tuttu**, **içerik hipotezi** önerilen çözünürlükte
tutmadı: top-200 bandında yalnızca iki siyasi/kimlik terimi vardır ve
**+0,0111 [−0,0138; +0,0437]** gösterirler — destek yok. df ≥ 30'da 26 terim
görünür ve 118'in 23'ünde **+0,1494 [+0,0825; +0,2224]**; aynı çözünürlükte
deiktik alt küme daha büyüktür: 40 satırda **+0,2106 [+0,1263; +0,2982]**.
Token kümeleri ayrıktır ama satırlar değildir — **118'in 9'u ikisini birden
taşır**, dolayısıyla sayılar toplanmaz.

**118'in 47'si (%39,8) test edilen hiçbir kelime dağarcığında güçlü çarpık token
taşımıyor ve açıklanamamış kalıyor.**

### Sınıf dengesi sorusu, üç parçada

1. `lexicon_free` geri çağırmasının **mutlak düzeyi** üzerinde dengesizlik
   makul biçimde katkıda bulunur ve **dışlanamaz** — 1:4,18 oran, sınıf ağırlığı
   yok, eşik 0,5'te sabit; ağırlıklı hiçbir varyant eğitilmedi, dolayısıyla
   katkısı **ölçülmemiştir.**
2. **Fark** üzerinde hayır — tek model, tek eşik, iki ayrık alt küme; küresel bir
   dengesizlik ikisini de aynı şekilde bastırır.
3. **Kesit-koşullu önseller** üzerinde (sözlük eşleşmesi verildiğinde 0,5535 vs
   verilmediğinde 0,1410; 3,92× oran) soru çözülür — çünkü bu *zaten* sözlüksel
   bağımlılığın kendisidir, model davranışı olarak değil **derlem özelliği**
   olarak ölçülmüş hâlidir.

---

## 3.8 Faz 11 ve 12 — açık soruyu kapatmak ve onarımı yapmak

### Faz 11 — puan düşüklüğü doğru mu?

**Soru:** `lexicon_free` puanlarının düşüklüğü *%13,6 taban oranına doğru
kalibrasyon* mu, yoksa *gerçek özgüven eksikliği* mi? Faz 04 kalibrasyonu
yalnızca **küresel** olarak ölçmüştü (T = 0,9948, ECE = 0,0205) ve "ham BERTurk
kalibrasyona ihtiyaç duymuyor" demişti. Kesit başına kalibrasyon bu projede hiç
hesaplanmamıştı.

**Sonuç:** `lexicon_free` eşik-altı bandında (n = 1.846) işaretli boşluk
**−0,004567 [−0,012807; +0,003546]** → karar **`BASE-RATE-CORRECT`**.

Yani model %13,6 taban oranlı bir kesitte düşük puan vermekte **haklıdır**;
operasyonel başarısızlık modelin değil, **heterojen bir popülasyona tek küresel
eşik uygulamanın** kusurudur. Bu, `PROJECT_HISTORY` §7'deki açık soruyu
(**dev-only** olarak) kapatır.

Burada da bir tahmin (**C11-12**) **başarısız oldu** ve öyle kaydedildi.
Run B (Saerens EM prior düzeltmesi, kesit başına Platt / isotonik regresyon)
**proje lideri tarafından reddedildi** ve bir *karar* olarak günlüğe yazıldı —
bir eksiklik olarak değil.

Karşılaştırma ekseni de ön kayıtta belirlendi: Surana (arXiv:2605.14074, tek
yazarlı ön baskı, hakem denetiminden geçmemiş) Civil Comments'ta yapısal olarak
benzer bir örüntü bildirir — mükemmele yakın toplam kalibrasyon yanında her alt
grupta anlamlı kalibrasyon bozukluğu. **Yön farkı önceden yazıldı:** Surana'nın
alt grupları *aşırı* güvenlidir (yanlış pozitif üretir); buradaki hipotez
*eksik* puanlamadır (yanlış negatif üretir). İkisini aynı bulgu sayan her cümle
yanlıştır.

### Faz 12 — kesit başına ayrı eşik gerekli mi?

Faz 11 tanıyı eşiğe taşıdığına göre soru şudur: kesit koşullu iki eşik, tek
eşikten iyi midir?

Dört sistem, aynı satırlar, aynı donmuş karar kuralı (`skor > t`), maliyet
`Cost(r) = (FP + r·FN)/N`, r = 3 (kaçırma, yanlış işaretlemeden üç kat kötü):

| | S0 | S1a (kontrol) | **S1b (önerilen)** | S2 |
|---|---|---|---|---|
| Uyarlanan parametre | 0 | 0 | **1** | 2 |
| Eşik | 0,50 | 0,25 (Elkan analitik) | **0,320188** | 0,303421 / 0,439296 |
| Çıkarımda sözlük okur mu | Hayır | Hayır | **Hayır** | **Evet** |
| Maliyet, satır başına | 0,2410 | 0,2208 | **0,2246** | 0,2338 |
| `lexicon_hit` OFF-R | 0,8681 | 0,9341 | **0,9121** | 0,9121 |
| `lexicon_free` OFF-R | 0,5180 | 0,6906 | **0,6367** | 0,5468 |
| OFF kesinlik (genel) | 0,7512 | 0,6094 | **0,6509** | 0,7082 |
| İşaretlenen satır | 402 | 594 | **527** | 449 |

**Karar `SINGLE-THRESHOLD-SUFFICIENT`**: S2, S1b'ye göre göreli maliyeti
**+0,04112 [−0,01596; +0,10484]** değiştirir — artı işaret S2'nin **daha pahalı**
olduğu anlamına gelir ve aralık sıfırı içerir. C12-10'un ön kayıtlı tahmini
**tuttu.**

S1a (0,25 analitik Elkan eşiği) **sıfır parametreli bir iç kontroldür**, bir
dağıtım adayı değildir.

**Bunun mühendislik anlamı büyüktür:** önerilen sistem çıkarım anında sözlüğe
**hiç bakmaz.** Sözlük yalnızca bir *ölçüm* aracıdır; dağıtılan karar kuralının
parçası değildir. Sözlüğe bağımlılığı ölçen bir projenin kendi çözümünde
sözlüğe bağımlı olmaması, tasarımın en temiz sonucudur.

**Bir dürüstlük notu:** C12-16 kapsamındaki güven aralıkları **nokta kestirimleri
yayımlandıktan sonra** hesaplandı. Sonuç dosyasının kendi `/ordering_disclosure`
alanı bunu yazar: *"This is estimation after the fact, not pre-registration."*
README bu ifadeyi kendi cümlesi olarak değil, **dosyanın kendi beyanı olarak**
aktarır.

### Faz 15 — sayım, ölçüm değil

`src/phase15_deixis.py` deiksis bayrağını (`data/deixis/address_tokens.json`,
Stage 4'ün yedi token'lık birincil kümesi, **tam eşleşme** — `hit_root` değil)
dondurur ve yalnızca **hücre sayılarını** üretir. Modül açıkça hiçbir
kalibrasyon büyüklüğü hesaplamaz: işaretli boşluk yok, ECE yok, AUC yok, geri
çağırma yok, karar yok. Yalnızca tam sayılar, oranlar ve hash'ler.

Gerekçesi ince: duyarlılık paydaları ve CAL yarısı uyum hücreleri **herhangi bir
bant ya da istatistik sabitlenmeden önce** biliniyor olmalı ki, bandın sonradan
"ne kazandıracağı görülerek" seçilmesi mümkün olmasın.

Köken kapısı olarak Faz 11'in `load_and_gate` fonksiyonu **değiştirilmeden içe
aktarılır** — bu aşama ile Faz 11 Run A aynı kontrollerle ayakta durur ya da
birlikte düşer.

---

## 3.9 Demo (`demo/app.py`)

- **Çevrimdışı inşa gereği.** Gradio ve Streamlit **isimleriyle reddedildi**:
  ikisi de sayfa yüklenirken CDN'den yazı tipi ve telemetri çeker, dolayısıyla
  "ağsız" bir demo tam da bağlantı kesildiği anda **boş sayfa** olarak çöker.
  Yerine stdlib `http.server` + satır içi CSS. `requirements.txt`'te gradio
  bağımlılığı bu gerekçeyle kaldırıldı — pinlemek belgeyle çelişiyordu.
- **İçe aktarma sırası bir hata değil, tasarım.** `HF_HUB_OFFLINE` /
  `TRANSFORMERS_OFFLINE` **transformers içe aktarılmadan önce** ayarlanır ve ağır
  içe aktarmalar fonksiyon içine ertelenmiştir, çünkü `huggingface_hub` bu
  değişkeni içe aktarma anında okur. Modül düzeyinde bir `import transformers`
  değeri erkenden mühürlerdi.
- **Doğrulama.** L4 üzerinde **tüm giden soketler `sitecustomize` shim'i ile
  kapatılarak** çalıştırıldı. İki soğuk başlangıç, bayt-aynı çıktı. Düşmanca
  girdi kümesi (boş, yalnız emoji, 100 bin karakter, kontrol karakterleri, XSS,
  bozuk JSON) hepsi atlatıldı.
- **Paket:** 885,9 MB. İki checkpoint 442,5 MB'lık fp32 BERTurk'lerdir
  (110M × 4 bayt ≈ 440 MB); git'te değildirler. Dondurulmuş çalışma noktası
  eşiği 0,6632.
- **En önemlisi:** demo, yeteneği gösterdiği kadar **sınırlılığı da** gösterecek
  şekilde seçildi. `NONDIR` yanlış pozitifi inceleme katmanı tarafından
  **devredilir**, örtük yanlış negatifler ise **otomatik olarak yanlış
  çözülür** — yani Faz 04'ün null bulgusu ekranda görünür kılınmıştır.
- Sertleştirme sonrası: devretme anında model etiketi gizlenir (karşılaştırma
  tablosunun bu gizlemeyi bozduğu tespit edildi ve düzeltildi) ve erişilebilirlik
  boşlukları kaynağında kapatıldı.

---

## 3.10 Rapor ve depo durumu

- `report/final/` — **onaylanmış** Türkçe KYS metinleri (bölüm 1.1, 1.2, 2.1, 2.2
  = 30 puan), proje liderinden geldiği gibi **kelimesi kelimesine** commit
  edilmiştir. `PROVENANCE.md` iki tedariki ve aralarındaki **tek satırlık** farkı
  (karşılaştırma tablosunun inceleme tarihi, `20.08.2026 → 23.08.2026`) `diff`
  ile doğrulayarak kaydeder — okuyarak değil.
- `report/build_docx.py` — KYS şablonunu temel belge olarak açar ve dört taslağı
  `report/build/report_draft.docx` içinde sayfalar (python-docx ≥ 1.2).
- **Rapor bölüm 3 (ilgili çalışmalar) kasten boştur** — birincil kaynaklardan
  doğrulama beklemektedir.
- `src/obfuscation.py` **kamuya açık kopyadan çıkarılmıştır**: modül işlevsel
  kaçırma metni üretir ve yayımlanması amaçlanmamıştır.
- **Dağıtılmayanlar:** ham derlem (`data/**`) ve satır düzeyi tahmin dökümleri
  (`results/**/*predictions*.csv`). Gerekçe lisans ve boyuttur; kimlikleri yine
  de sonuç dosyalarına yazılı sha256 özetleriyle bağlıdır.
- **Test durumu:** README, commit `90c70b7` üzerinde **415 geçti, 1 kaldı**
  der (`tests/test_demo.py::test_render_result_escapes_html`, modül durumu
  doldurulmadan `render_result` çağrıldığı için `KeyError`). Paket yeşil
  değildir ve depo yeşil olduğunu iddia etmez.
- **Lisans durumu:** sözlüğün kaynak deposu CC BY-SA 4.0 beyan eder ve bu
  doğrulanabilir; ancak **bu depoda hiçbir yerde kayıtlı değildir** —
  `docs/phase_briefing.md` "commit hash + lisans + tarih" kaydını şart koşuyordu
  ve lisans alanı hiç doldurulmadı. Projenin kendisi için de bir lisans dosyası
  yoktur.

---

# Bu projeyi diğerlerinden ayıran şey

Teknik olarak makul ama sıradan bir çalışma: BERTurk ince ayarı + kesit analizi.
Projeyi ayıran şey, **kanıt üretme rejimidir**:

1. **Ön kayıt, commit SHA'sıyla.** Yedi protokol, hepsi kendi fazının ilk
   sayısından önce git'te; `git log --follow` ile denetlenebilir. `INTERMEDIATE`,
   `FLAT`, `ORDERING WORSENED` ve `SINGLE-THRESHOLD-SUFFICIENT` kararları,
   sonradan yazılan bir kuralın farklı ifade etmeye eğilimli olacağı sonuçlardır.
2. **Ekleme-yalnızca günlük.** 60+ satır, altı düzeltme, bir şartname kusuru.
   Yanlış çıkan yorumların **orijinal ifadesi hâlâ okunabilir.**
3. **Sayıdan önce kaydedilen tahminler.** C4-3 **tuttu** (0,00e+00);
   C9-16 ve C11-12 **tutmadı** — ve tutmayanlar bilgilendirici olan yarısıydı.
4. **Refüte edebilen kontroller.** Faz 08'in güçlü-NOT kontrolü ve Stage 1b'nin
   `lexicon_hit` kontrolü ikisi de manşeti çürütebilirdi; biri tuttu, biri
   tutmadı.
5. **İçerikle köken doğrulama, sonra hash.** Stage 1, yeni hiçbir şey
   hesaplamadan önce girdi dökümünün **kayıtlı sekiz Faz-01 sayısını yeniden
   üretmesini** şart koştu. Sonra Drive aynası hash'lendi ve **bayt-aynı**
   bulundu (`a2f5bddf…538a6346`, 736.591 bayt) — bu arada `run_raw` ile Faz 01
   temel çizgisinin **tek dosya** olduğu ortaya çıktı.
6. **Eğitmeden önce veriyi okumak.** Faz 03'ün inceleme kapısı, hiçbir toplam
   metriğin göstermeyeceği üç kusuru yakaladı.
7. **Bir yerine dört ayrı çalıştırma.** Küfürsüz FP artışı (185 → 215) doğru
   şekilde 1b ve D'ye atfedildi; birleşik bir çalıştırma 1a'yı suçlardı — oysa
   1a tek başına onu 156'ya düşürüyordu.
8. **Dosyayla uygulanan tek kullanımlık muhasebe**, açma günlüğü okumadan
   *önce* yazılır — bu yüzden hiçbir sayı üretmeden çöken bir deneme bile
   kayıttadır.
9. **Başarısızlıklar başarılarla aynı ayrıntıda.** `PROJECT_HISTORY.md` §6,
   güvenle savunulup sonra çöken **dört erken okumayı** ve üç daraltmayı adım
   adım anlatır — ve her birinin *neden o zaman makul olduğunu* açıklar; çünkü
   apaçık hatalardan oluşan bir liste hiçbir şey öğretmez.

---

# Açık kalan konular (deponun kendi listesi)

- **Eşik yerleşimi mi, gerçek özgüven eksikliği mi** — dev'de kapandı (Faz 11:
  taban-oran-doğru); test kümesinde asla doğrulanamaz.
- **118 küfürsüz FP'nin 47'si (%39,8) açıklanamamış.**
- **Modelin deiksis sinyalini kullanıp kullanmadığı bilinmiyor**; yalnızca
  eğitim verisinde *mevcut* olduğu gösterildi. Atıf ya da ablasyon
  çalıştırılmadı.
- **Bileşen atfı**: yalnızca birleşik `+1a+1b+D` karşılaştırıldı; 1a, 1b ve D
  ayrıştırılamaz.
- **Test kümesindeki +0,0358 kazancın mekanizması** — Stage 1b yalnızca dev'dir.
- **Sınıf dengesizliğinin katkısı ölçülmedi** — ağırlıklı hiçbir varyant
  eğitilmedi.
- **Tek tohum, tek yapılandırma**: raporlanan güven aralıkları değerlendirme
  örneklemesini kapsar, eğitim rastgeleliğini değil.
- **Derlemler arası genelleme yok**: Mayda ve Beyhan hiç edinilmedi. İddia
  **aynı-derlem** ile sınırlıdır.
- **ConvBERTurk hiç çalıştırılmadı** ve test kümesi harcandığı için artık
  bağımsız bir sayı alamaz.
- **Rapor bölüm 3** (ilgili çalışmalar) doğrulama bekliyor.
- **Faz 09 aşama 2–6** açılmadı; 5 ve 6 eğitim ve ayrı yetkilendirme gerektirir.
- **`manifest.json` yazılıyor ama hiç okunmuyor** — beyan edilen güvence
  çalışmıyor; kaydedildi, düzeltilmedi.
- **Lisans kaydı eksik** (bkz. 3.10).

---

# Hızlı başvuru: sayı → kaynak dosya

| Sayı | Kaynak |
|---|---|
| %63,5 sözlük kaçağı (3.892/6.131) | `results/day1_report.json` |
| Geliştirme kesit geri çağırmaları ve +0,3301 fark | `results/01_baseline_berturk/metrics.json`, `results/03_defense/comparison.json` (`/runs/raw/recall_gap`) |
| Test kümesi +0,3970 fark | `results/05_final_test/metrics.json` (`/systems/raw`) |
| Kesit ROC-AUC'leri ve +0,0345 | `results/09_deeper_analysis/stage_1/stage1_auc.json` (`/primary`) |
| ΔAUC `FLAT` / `ORDERING WORSENED` | `results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json` |
| Sıcaklık, ECE, çalışma noktaları, 0,663171 eşiği | `results/04_calibration/calibration.json` |
| Savunma dört-çalıştırma tablosu ve eşleştirilmiş farklar | `results/03_defense/comparison.json` |
| Elle etiketlenmiş hata aileleri, kirlenme duyarlılığı | `results/02_failure_analysis/` |
| Token istatistikleri, deiksis bulgusu | `results/08_lexical_analysis/token_stats.json` |
| `BASE-RATE-CORRECT` kararı | `results/11_prior_correction/metrics.json` (`/primary`) |
| S0/S1a/S1b/S2 tablosu ve `SINGLE-THRESHOLD-SUFFICIENT` | `results/12_threshold_policy/metrics.json` |
| C12-16 sonradan-hesaplanma beyanı | `results/12_threshold_policy/c12_16_intervals.json` (`/ordering_disclosure`) |
| Deiksis hücre sayımları | `results/15_deixis/cell_counts.json` |
| Test kümesi harcama kaydı | `results/05_final_test/TEST_SET_SPENT.json`, `TEST_SET_OPENED.json` |
