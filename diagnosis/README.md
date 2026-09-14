# Sözlükten Kaçan Saldırganlık: Türkçe İçerik Moderasyonunda Sözlük Bağımlılığını Ölçen Tanı ve İnceleme Sistemi

Türkçe saldırgan içeriğin büyük bölümü hiçbir küfür sözcüğü taşımaz. Bu depo, ince
ayarlı bir BERTurk sınıflandırıcısının başarımının ne kadarının küfür sözcük
dağarcığına dayandığını ölçer. Ölçüm iki katmanda ayrışır. Karar eşiğinde, sözlük
eşleşmeli kesit ile sözlük içermeyen kesit arasındaki saldırgan içerik geri çağırma
farkı **+0,3301**, %95 güven aralığı **[+0,2771; +0,3827]** (geliştirme kümesi,
n = 4.764, eşik 0,50). Sıralamada aynı iki kesit arasındaki ROC-AUC farkı ise **+0,0345**,
%95 güven aralığı **[+0,0103; +0,0585]**. Model, küfür içermeyen saldırgan
içeriği sıralayabiliyor; onu karar eşiğinin üstüne çıkaramıyor.

Kaynaklar: `results/03_defense/comparison.json` (`/runs/raw/recall_gap`) ve
`results/09_deeper_analysis/stage_1/stage1_auc.json` (`/primary`).

## 1. Yeniden üretilebilirlik durumu

**Önce şunu bilin:** ham derlem ve satır düzeyi tahmin dökümleri bu depoda
dağıtılmaz. `.gitignore` `data/**` yolunu ve `results/**/*predictions*.csv`
desenini hariç tutar. Bu nedenle temiz bir klonda `data/coltekin/*.tsv`,
`data/lexicon/karaliste.txt` ve `results/01_baseline_berturk/dev_predictions.csv`
**bulunmaz**. Gerekçe lisans ve boyuttur; dağıtılmayan derlem dosyalarının kimliği
yine de sonuç dosyalarına yazılı sha256 özetleriyle bağlıdır, bkz. bölüm 6.

Ayrıca `src/obfuscation.py` bu kamuya açık kopyadan **çıkarılmıştır**: modül
işlevsel kaçırma metni üretir ve yayımlanması amaçlanmamıştır.

| Ne | Temiz bir klondan yeniden üretilebilir mi? |
|---|---|
| `results/` altındaki sonuç dosyaları | **Evet.** Tüm ölçüm JSON dosyaları depoda; doğrudan okunur, çalıştırma gerektirmez. |
| Şekiller | **Kısmen.** Beş şeklin üçü (sözlük eşleşme dağılımı, risk-kapsam eğrisi, geçişler ve AUC farkı) yalnızca depodaki `day1_report.json`, `04_calibration/calibration.json` ve `09_deeper_analysis/stage_1b/stage1b_defense_auc.json` dosyalarından çizilir. İkisi (kesit başına P(OFF) birikimli dağılımı ve kesit başına ROC eğrisi) `dev_predictions.csv` dökümünü ister; bu dosya dağıtılmaz, dolayısıyla o iki şekil temiz bir klonda **çizilemez**. AUC değerlerinin kendisi depodadır, eğrinin noktaları değildir. |
| Eğitim çalışması | **Hayır, olduğu gibi değil.** GPU zorunludur: `phase01_baseline.py` çalışma başlamadan `torch.cuda.is_available()` doğrular ve `+cpu` derlemesini reddeder. Derlem dağıtılmadığı için önce Çöltekin verisinin ayrıca edinilmesi gerekir. Kayıtlı hiperparametreler: 3 dönem, yığın 32, öğrenme oranı 2e-5, `max_len` 128, fp16, %10 doğrusal ısınma, tohum 42. Kullanılan GPU adı sonuç dosyasına yazılmamıştır. |
| Resmî test kümesi değerlendirmesi | **Hayır.** Küme tek kullanımlıktır ve harcanmıştır. `results/05_final_test/TEST_SET_SPENT.json` depoda mevcuttur ve `src/data_io.load_coltekin_test()` bu dosya varken yüklemeyi reddeder. Kilit kodla uygulanır, hatırlamayla değil. |

Bu tabloda hiçbir "hayır" yumuşatılmamıştır.

## 2. Yöntem disiplini

**Ön kayıt.** `phases/` altında sürüm denetimine alınmış **9** protokol dosyası
vardır. Bunlardan **7** tanesi sayı üreten bir fazın karar kurallarını, eşiklerini ve
başarısızlık koşullarını o fazın ilk sayısı var olmadan önce sabitler:
`01_baseline_diagnosis.md`, `03_defense_design.md`, `04_calibration.md`,
`08_lexical_analysis.md`, `09_deeper_analysis.md`, `11_prior_correction.md`,
`12_threshold_policy.md`. Kalan ikisi (`07_report.md`, `10_sablon_mapping.md`) rapor
ve şablon protokolleridir, sayı üretmez. Sıralama `git log --follow` ile denetlenebilir.

**Ekleme yalnızca yapılan deney kaydı.** `docs/RESULTS_LOG.md` tarihli **49** satır
taşır. Satırlar düzeltilmez; çelişki çıktığında yeni bir düzeltme satırı eklenir ve
eski okuma görünür kalır. Kayıt şu anda **6** düzeltme satırı ve **1** şartname
kusuru satırı içerir.

**Tek kullanımlık test kümesi.** Yukarıda anlatılan kilit. Kayıt dosyası, harcama
anını, çalıştıran ölçümü ve o andaki commit'i taşır.

**Her farkta güven aralığı.** Raporlanan her fark, işareti ne olursa olsun, %95
önyükleme yüzdelik aralığıyla verilir; tohum 42.

**Ön kayıt kapsamı dışında kalan bir ek.** Eşik politikası ön kaydının numaralı bir
maddesi (C12-16) uyarınca eklenen güven aralıkları, ilgili nokta kestirimlerinden
**sonra** hesaplanmıştır. Bunu bizim beyanımız olarak değil,
sonuç dosyasının kendi ifadesi olarak okuyun:
`results/12_threshold_policy/c12_16_intervals.json` `/ordering_disclosure` alanı
"This is estimation after the fact, not pre-registration." der. Bu README o
dosyadan daha sessiz olmamalıdır.

## 3. Depo düzeni

```
config.py        her yol ve sabit; hiçbir betik konum gömmez
src/             ölçümün tek kaynağı; betikler buradan içe aktarır
  data_io.py     derlem okuyucuları, biçim tuzağı korumaları, test kümesi kilidi
  lexicon.py     Türkçeye duyarlı küçültme, kök eşleştirme
  augment.py     ters olgusal veri artırımı
  models.py      BERTurk sarmalayıcıları ve eğitim döngüsü
  calibration.py sıcaklık ölçekleme, risk-kapsam, seçici tahmin
  evaluate.py    her sistemin paylaştığı tek metrik yolu
phase*.py        faz başına bir çalıştırıcı, depo kökünde
phases/          ön kayıt protokolleri; sayılarından önce işlenmiş
data/            dağıtılmaz; yalnızca satır kimlikleri taşıyan bölme dosyası hariç
results/         deney JSON dosyaları; satır düzeyi dökümler hariç
docs/            brifingler ve RESULTS_LOG.md
report/          Türkçe rapor metinleri ve docx üreticisi
demo/            çevrimdışı yan yana karşılaştırma arayüzü
tests/           doğrulanmış biçim tuzakları için gerileme testleri
```

`src/obfuscation.py` bu listede yoktur; birinci bölümde belirtildiği gibi
çıkarılmıştır.

## 4. Temel sonuçlar

Her satır kendi popülasyonunu ve n değerini adlandırır. Bu projede dört ayrı
popülasyon vardır ve onları karıştırmak, bu belgeyi raporla çelişkiye düşürmenin en
kolay yoludur.

Geliştirme kümesi ikiye ayrılmıştır: eşik, kalibrasyon yarısında uyarlanır ve
değerlendirme yarısında ölçülür. İki yarı ayrıktır, dolayısıyla eşiğin ölçüldüğü
satırlar onu seçen satırlar değildir.

### 4.1 Sözlük eşleşme ayrımı (etiketli derlem)

Popülasyon: 31.756 satırlık etiketli derlem (eğitim + geliştirme), resmî test kümesi
dışında. Saldırgan satır sayısı 6.131, taban oran %19,3.

| | Sayı | Pay |
|---|---|---|
| Sözlük kökü eşleşen saldırgan satırlar | 2.239 | %36,5 |
| Hiçbir kök eşleşmeyen saldırgan satırlar | **3.892** | **%63,5** |

Sözlük 695 girdilik dondurulmuş bir listedir (dosyada 698 satır; yükleyici Türkçeye
duyarlı küçültmeden sonra yinelenenleri ayıklar). Kaynak: `results/day1_report.json`.

### 4.2 Kesit başına saldırgan içerik geri çağırma, eşik 0,50

| Popülasyon | Kesit | n (saldırgan) | Geri çağırma | %95 GA |
|---|---|---|---|---|
| Tam geliştirme, n = 4.764 | sözlük eşleşmeli | 355 | 0,8930 | [0,8618; 0,9248] |
| Tam geliştirme, n = 4.764 | sözlük içermeyen | 565 | 0,5628 | [0,5210; 0,6010] |
| Tam geliştirme, n = 4.764 | **fark** | | **+0,3301** | **[+0,2771; +0,3827]** |
| Resmî test, n = 3.528 | sözlük eşleşmeli | 269 | 0,9071 | [0,8710; 0,9387] |
| Resmî test, n = 3.528 | sözlük içermeyen | 447 | 0,5101 | [0,4628; 0,5546] |
| Resmî test, n = 3.528 | **fark** | | **+0,3970** | **[+0,3418; +0,4542]** |

İki fark aralığı **örtüşür**: örtüşme bölgesi [+0,3418; +0,3827]. Sınırlar
karşılaştırılarak doğrulanmıştır. Farkın tutulduğu söylenebilir; test kümesinde
büyüdüğü söylenemez.

Kaynaklar: `results/01_baseline_berturk/metrics.json` (`/berturk`),
`results/03_defense/comparison.json` (`/runs/raw/recall_gap`),
`results/05_final_test/metrics.json` (`/systems/raw`).

### 4.3 Kesit başına ROC-AUC, tam geliştirme kümesi (n = 4.764)

| Kesit | n | AUC | %95 GA |
|---|---|---|---|
| sözlük eşleşmeli | 355 saldırgan / 259 saldırgan değil | 0,9306 | [0,9102; 0,9495] |
| sözlük içermeyen | 565 saldırgan / 3.585 saldırgan değil | 0,8962 | [0,8821; 0,9095] |
| **fark** | | **+0,0345** | **[+0,0103; +0,0585]** |

Ön kayıtlı karar: `INTERMEDIATE`. Bu belgedeki `INTERMEDIATE`, `FLAT`,
`ORDERING WORSENED` ve `SINGLE-THRESHOLD-SUFFICIENT` gibi büyük harfli karar
etiketleri, ölçüm yapılmadan önce ön kayıt protokolünde sabitlenmiş değerlerdir:
etiket, sayı henüz yokken seçilmiştir. Önyükleme 10.000 yineleme, tohum 42, dört
kesit x altın etiket hücresi üzerinde katmanlı. Kaynak:
`results/09_deeper_analysis/stage_1/stage1_auc.json`.

Yorum sınırı: bu, sıralamanın karar eşiğinden çok daha az bozulduğunu gösterir. Model
küfür içermeyen saldırgan içeriği tespit **edememektedir** denemez; sıralamaktadır.

### 4.4 İnsan incelemesine devretme çalışma noktası

Eşik **0,663171**, geliştirme kümesinin kalibrasyon yarısında %90 kapsam hedefiyle
seçilmiştir ve üç popülasyonun tümünde aynıdır. Test kümesinde yeniden türetilmemiştir
(`thresholds_re_derived_on_test: false`).

| Popülasyon | n | Kapsam | %95 GA | Devredilen | Hata oranı | Makro-F1 |
|---|---|---|---|---|---|---|
| Geliştirme, değerlendirme yarısı | 2.382 | 0,9118 | [0,9005; 0,9236] | 210 | 0,0792 | 0,8504 |
| Tam geliştirme | 4.764 | 0,9060 | kayıtlı değil | 448 | 0,0765 | 0,8590 |
| Resmî test | 3.528 | 0,9016 | [0,8926; 0,9116] | 347 | 0,0852 | 0,8485 |

Üç kapsam değeri de yaklaşık 0,90'a yuvarlanır ve **birbirinin yerine kullanılamaz**.
Hangi sayının hangi popülasyona ait olduğu yukarıda satır satır adlandırılmıştır.
Makro-F1 yalnızca sistem düzeyinde verilir; kesit başına makro-F1 hiçbir yerde
raporlanmaz, çünkü kesitlerin taban oranları birkaç kat farklıdır.

Kaynaklar: `results/04_calibration/calibration.json`
(`/variants/raw/operating_points`, `/variants/raw/deferral_full_dev`) ve
`results/05_final_test/metrics.json` (`/systems/raw/selective`).

### 4.5 Eşik kuralı karşılaştırması, değerlendirme yarısı (n = 2.382)

Dört kural aynı satırlarda ve aynı donmuş karar kuralıyla ("skor > t ise işaretle")
karşılaştırılır. Maliyet, kaçırılan bir saldırgan gönderiyi yanlış işaretlenmiş bir
gönderiden üç kat kötü sayan orana göre hesaplanır (r = 3); S1b'nin kesinlik kaybı bu
nedenle kuralın amaçlanan davranışıdır, bir kusur değil. **Önerilen kural S1b'dir**:
tek, veriden uyarlanmış eşik. S1a, 0,25 değerindeki çözümlemeli eşik, sıfır
parametreli bir iç kontroldür ve bir dağıtım adayı değildir.

| | S0 | S1a (kontrol) | **S1b (önerilen)** | S2 |
|---|---|---|---|---|
| Uyarlanan parametre | 0 | 0 | **1** | 2 |
| Eşik | 0,50 | 0,25 | **0,320188** | 0,303421 / 0,439296 |
| Çıkarımda sözlüğe başvurur mu | Hayır | Hayır | **Hayır** | Evet |
| Maliyet, satır başına (düşük olan iyi) | 0,2410 | 0,2208 | **0,2246** | 0,2338 |
| Saldırgan geri çağırma, sözlük eşleşmeli | 0,8681 | 0,9341 | **0,9121** | 0,9121 |
| Saldırgan geri çağırma, sözlük içermeyen | 0,5180 | 0,6906 | **0,6367** | 0,5468 |
| Saldırgan kesinlik (genel) | 0,7512 | 0,6094 | **0,6509** | 0,7082 |
| İşaretlenen satır | 402 | 594 | **527** | 449 |

Ön kayıtlı karar `SINGLE-THRESHOLD-SUFFICIENT`: kesit koşullu iki eşikli S2, tek
eşikli S1b'ye göre göreli maliyeti **+0,04112** değiştirir; artı işaret S2'nin **daha
pahalı** olduğu anlamına gelir. %95 güven aralığı **[-0,01596; +0,10484]**, sıfırı
içerir. Kesit başına ayrı eşik tutmanın maliyeti düşürdüğü gösterilemedi; sözlüğü
çıkarım anında okumayan basit kural yeterlidir.
Kaynak: `results/12_threshold_policy/metrics.json`.

### 4.6 Ters olgusal veri artırımı: ölçülmüş bir başarısızlık

Ters olgusal veri artırımı denendi ve amacına ulaşmadı. Bu bir başarı kadar açık
biçimde raporlanır. Tam geliştirme kümesi, n = 4.764, eşleştirilmiş önyükleme:

| Ölçüt | Fark | %95 GA | Sıfırı dışlıyor mu |
|---|---|---|---|
| Sistem makro-F1 | -0,0069 | [-0,0185; +0,0052] | Hayır |
| Saldırgan geri çağırma, sözlük içermeyen | +0,0336 | [+0,0052; +0,0662] | Evet |
| Saldırgan geri çağırma, sözlük eşleşmeli | -0,0423 | [-0,0778; -0,0109] | Evet |

Hedeflenen kesitte ölçülebilir bir kazanç vardır; karşılığında diğer kesitte
ölçülebilir bir kayıp vardır ve sistem düzeyinde net etki sıfırdan ayırt edilemez.
Sıralama da düzelmemiştir: sözlük içermeyen kesitte AUC farkı **-0,0056**
[-0,0134; +0,0024] (karar `FLAT`), sözlük eşleşmeli kesitte **-0,0254**
[-0,0429; -0,0086] (karar `ORDERING WORSENED`). Onarımın eşik katmanına
taşınmasının nedeni budur. Kaynaklar: `results/03_defense/comparison.json`,
`results/09_deeper_analysis/stage_1b/stage1b_defense_auc.json`.

## 5. Ne çalıştırılabilir

```bash
python -m venv .venv
pip install -r requirements.txt
pytest tests/ -q
```

Veri gerektirmeyen adımlar bunlardır. Test paketinin bu belge yazılırken, commit
`90c70b7` üzerinde ölçülen durumu: **415 test geçti, 1 test kaldı.** Kalan test
`tests/test_demo.py::test_render_result_escapes_html`; çevrimdışı arayüzün
`render_result` işlevini, modül durumu doldurulmadan çağırdığı için `KeyError`
veriyor. Paket yeşil değildir ve yeşil olduğu söylenmemektedir.

Aşağıdaki komutlar dağıtılmayan dosyaları ister:

```bash
# Sözlük eşleşme sayımlarını yeniden üretir. data/lexicon/karaliste.txt ve
# data/coltekin/offenseval-tr-training-v1.tsv GEREKİR, ikisi de dağıtılmaz.
python day1_gate_en.py --out results/day1_report_rerun.json

# Yukarıdaki çıktıyı dondurulmuş kayıtla karşılaştırır. Yalnızca o çalıştırma
# yapıldıysa anlamlıdır.
python tests/_verify_day1_reproduction.py

# Model eğitimi. GPU ve derlem GEREKİR; her ikisi de dağıtılmaz.
python phase01_baseline.py --stage train
```

Resmî test kümesini yeniden değerlendiren bir komut yoktur ve olmayacaktır; kilit
bölüm 1'de anlatılmıştır.

Sonuçları okumak için hiçbir şey çalıştırmanız gerekmez: `results/` altındaki JSON
dosyaları depodadır ve bu belgedeki her sayı oradan okunur.

## 6. Veri, model ve lisans

| Rol | Kaynak | Not |
|---|---|---|
| Eğitim ve geliştirme | Çöltekin, Ç. (2020), A Corpus of Turkish Offensive Language on Social Media, LREC 2020, 6174-6184, ACL Anthology 2020.lrec-1.758 | 31.756 satır; tohum 42 ile %85 / %15 bölünür: 26.992 eğitim, 4.764 geliştirme. Dosya sha256 `8509c01c...2bcd4baa`. |
| Resmî test | Aynı derlemin resmî test kümesi ve altın etiketleri | 3.528 satır. Bir kez okundu, kilitlendi. sha256 `9052784e...2866b437`. |
| Sözlük | Oğuz, O., Türkçe Küfür Karaliste, https://github.com/ooguz/turkce-kufur-karaliste | 695 girdi, ölçüm başlamadan önce donduruldu, sha256 `0f5a05f5...3eace20b`. |
| Temel model | `dbmdz/bert-base-turkish-cased` | Yaklaşık 110 milyon parametre. |

**Lisans durumu, açıkça.** Sözlüğün kaynak deposu lisansını "Creative Commons
Attribution-ShareAlike 4.0 International" (CC BY-SA 4.0) olarak beyan etmektedir ve
yukarıdaki adresten doğrulanabilir. Ancak bu lisans **bu depoda hiçbir yerde kayıtlı
değildir**: `docs/phase_briefing.md`, sözlüğün "commit hash + lisans + tarih" ile
kaydedilmesini şart koşuyordu ve lisans alanı hiç doldurulmadı. Geçerli olan kaynağın
beyanıdır; eksik olan, bu deponun kendi kaydı. Projenin kendisi için de bir lisans
dosyası yoktur.

## 7. Sınırlılıklar

Yalnızca Türkçe, yalnızca metin, tek derlem. Derlemler arası genelleme ölçülmedi.
Kullanılabilirlik testi yapılmadı; arayüz için erişilebilirlik uygunluk süreci de
işletilmedi. Resmî test kümesi harcanmıştır: tek geçişten sonra üretilen her sayı
geliştirme kümesi kanıtıdır ve bu belgede öyle etiketlenmiştir.
