# 2. Yöntem

> **Taslak durumu.** KYS rapor şablonu yayımlanmadan önce yazılmıştır; başlık
> numaralandırması geçicidir. Bu bölümde verilen her yapılandırma değeri,
> çalıştırma anında üretilen `run_config.json` dosyalarından alınmıştır; hiçbiri
> sonradan yazılmamıştır.

Bu bölüm, yapılan işlemleri yeniden üretilebilecek ayrıntıda tanımlar. Bölüm 1
neyin ölçüldüğünü belirledi; bu bölüm nasıl ölçüldüğünü belirler.

## 2.1 Model ve eğitim yapılandırması

Temel model, Türkçe için önceden eğitilmiş `dbmdz/bert-base-turkish-cased`
(BERTurk) kodlayıcısıdır; üzerine iki sınıflı bir sınıflandırma başlığı
eklenerek ince ayar yapılmıştır.

| Hiperparametre | Değer |
|---|---|
| Model | `dbmdz/bert-base-turkish-cased` |
| Devir sayısı (epoch) | 3 |
| Yığın boyutu | 32 |
| Öğrenme oranı | 2 × 10⁻⁵ |
| Öğrenme oranı çizelgesi | doğrusal azalma, %10 ısınma |
| Ağırlık sönümü | 0,01 |
| En büyük dizi uzunluğu | 128 belirteç |
| Karma duyarlık | fp16 açık |
| Sınıf ağırlıklandırma | yok |
| Karar eşiği | 0,5 (sabit) |
| Tohum | 42 |
| Donanım | NVIDIA L4 |
| Kitaplıklar | torch 2.11.0+cu128, transformers 5.15.0, scikit-learn 1.6.1 |

*Kaynak: `results/01_baseline_berturk/run_config.json`. Eğitim süresi: 2026-08-15
16:12:34–16:18:18.*

Aynı yapılandırma, karşılaştırmaya giren **bütün** eğitim çalıştırmalarında
değiştirilmeden kullanılmıştır: temel model, üç savunma çeşitlemesi ve 5 katlı
çapraz doğrulamanın her katı.

### Neden hiperparametre taraması yapılmadı

Bu bilinçli bir tercihtir ve dört gerekçesi vardır.

**Birincisi, çalışmanın nesnesi bir karşılaştırmadır, bir eniyileme değildir.**
Tek bir sistemin hiperparametrelerini taramak, o sistemi diğerleri karşısında
kayırır. Karşılaştırmanın adil kalması için taramanın her kola eşit biçimde
uygulanması gerekirdi; bu da hesaplama maliyetini ızgara boyutu kadar
katlayacaktı.

**İkincisi, geliştirme kümesi tek tanı yüzeyimizdir.** Test kümesi tek
kullanımlıktır (§2.6), dolayısıyla geliştirme kümesi hem hata çözümlemesinin hem
de tasarımın dayandığı tek kaynaktır. Geliştirme kümesi üzerinde bir tarama
yapılsaydı, bu küme aynı zamanda bir *seçim* kaynağına dönüşür ve sonrasında
üzerinde ölçülen her sayı, miktarı ölçülemeyen bir iyimserlik taşırdı.

**Üçüncüsü, atfedilebilirlik.** Bütün kollarda yapılandırma birebir aynı olduğu
için, kollar arasındaki her fark müdahaleye atfedilebilir. Yapılandırma kollar
arasında değişseydi, gözlenen farkın müdahaleden mi yoksa hiperparametreden mi
kaynaklandığı ayrıştırılamazdı.

**Dördüncüsü, kullanılan değerler bize ait değildir.** 3 devir, 2 × 10⁻⁵ öğrenme
oranı, 32 yığın boyutu ve %10 ısınma, BERT ailesi için yayımlanmış standart ince
ayar reçetesidir. Bu değerlerin bizim tarafımızdan hiç ayarlanmamış olması,
geliştirme kümesinin kirlenmesine karşı en temiz savunmadır.

Aynı gerekçeyle **sınıf ağırlıklandırma uygulanmamış ve karar eşiği 0,5'te sabit
tutulmuştur.** Eşiğin ayarlanması, modelin kendi güven değerlerini bozar; oysa
Bölüm 4'teki kalibrasyon ve seçici tahmin çözümlemesi tam olarak bu güven
değerlerinin niteliğini ölçmektedir. Eşik önceden ayarlansaydı, o çözümleme
kendi müdahalesini ölçüyor olurdu.

### Denetim noktası seçimi — açıkça belirtilmesi gereken bir nokta

Üç devrin sonunda, geliştirme kümesindeki makro-F1'e göre en iyi devir seçilir ve
değerlendirme bu denetim noktası üzerinden yapılır. Bu, geliştirme kümesine
dayanan **bir** seçim işlemidir ve gizlenmemelidir. Kapsamı üç seçenekle
sınırlıdır ve bütün kollara aynı biçimde uygulanır.

Temel modelde 1. ve 3. devirler makro-F1 üzerinde **birebir eşitlenmiştir**
(aynı karışıklık matrisi), ancak 4.764 geliştirme satırının 198'inde farklı
kararlar vermektedirler; seçim kuralı ilk devri almıştır. Bu nedenle 285 yanlış
negatifin en fazla 43'ü denetim noktasına özgüdür. Raporlanan bütün temel model
sayıları 1. devre aittir; savunma çeşitlemesi (`+1a+1b+D`) 3. devre aittir.

*Kaynak: `results/01_baseline_berturk/metrics.json` (`checkpoint_tie` alanı);
`docs/RESULTS_LOG.md`, 2026-08-15 BERTurk satırı; denetim noktası kimlikleri
`results/05_final_test/raw_output.txt` içinde yeniden basılmıştır.*

## 2.2 Bölünmenin dondurulması

Eğitim/geliştirme bölünmesi (§1.3) bir kez üretilir, bir dosyaya yazılır ve
sonrasında yalnızca okunur. Bunu sağlayan üç mekanizma vardır.

**Sıralama bağımsızlığı.** Satırlar, karıştırılmadan önce her etiket kovası
içinde kimliğe göre sıralanır. Böylece bölünme, dosyanın okunma sırasına bağlı
değildir; okuyucu kodunda ileride yapılacak bir değişiklik örnekleri sessizce
eğitim ile geliştirme arasında taşıyamaz.

**Derlem doğrulaması.** Bölünme dosyası, üretildiği derlemin SHA-256 özetini
saklar. Yükleme sırasında bu özet yeniden hesaplanır; uyuşmazlık varsa işlem
hata verir. Farklı baytlar üzerine kurulmuş bir bölünmeyle ölçüm yapılması
mümkün değildir.

**Kayma göstergesi.** Yükleme sırasında bölünme ayrıca yeniden üretilir ve
kaydedilen bölünmeyle karşılaştırılır; sonuç `matches_regeneration` alanına
yazılır. Bu alan, bölme algoritmasının kendisi değişmiş olsaydı bunu görünür
kılar. Raporlanan bütün çalıştırmalarda değeri `True`'dur.

Ayrıca eğitim ve geliştirme kümelerinin kesişimi her yüklemede denetlenir ve
geliştirme kümesinin parmak izi (§1.3) sonuç dosyalarına yazılır. Savunma ve
kalibrasyon sürücüleri, parmak izi beklenen değerden farklıysa çalışmayı
başlatmadan durur.

## 2.3 Dondurulmuş sözlük ve dilim etiketleme

Sözlük (§1.2), ilk ölçümden önce dondurulmuş ve sonrasında değiştirilmemiştir.
Dilim etiketleri (`lexicon_hit` / `lexicon_free`), tek bir işlevden —
`lexicon.hit_root` — üretilir. Bu işlev, dilimleri kullanan her yerde içe
aktarılır; hiçbir yerde yeniden yazılmaz. Gerekçe basittir: eşleşme kuralının
ikinci bir kopyası, zamanla ilkinden ayrılmakta serbest olurdu ve bu ayrışma
hiçbir toplam ölçütte görünmezdi. Aynı ilke çevrimdışı gösterim uygulamasında da
korunmuştur.

Her çalıştırmanın başında bir **sağlamlık kapısı** işletilir: tam derlem üzerinde
sözlüksüz `OFF` sayısı yeniden hesaplanır ve Gün 1'de dondurulan 3.892 / 6.131
değerleriyle karşılaştırılır. Uyuşmazlık halinde çalıştırma başlamaz. Böylece
raporlanan hiçbir sayı, dondurulmuş kayıttan farklı bir etiketleyiciyle
üretilemez.

## 2.4 Döngüsellik karşıtı protokol

Bu çalışmanın merkezî riski, bir sayının kendi türetildiği veriden ölçülmesidir.
Protokol üç ayrı yerde bu riski keser.

### 2.4.1 Veri rollerinin ayrılması

| Kaynak | İzin verilen kullanım |
|---|---|
| Eğitim bölümü (26.992 satır) | model eğitimi; veri türetme; hata çözümlemesi |
| Geliştirme bölümü (4.764 satır) | tanı, tasarım kararları, eşik seçimi, raporlanan geliştirme sayıları |
| Resmî test kümesi (3.528 satır) | yalnızca nihai ölçüm, tek sefer |

### 2.4.2 Eğitim ve değerlendirme gizleme ailelerinin ayrıklığı

Savunmanın ikinci bileşeni, sözlükte eşleşen belirteçleri bozarak gizleme
saldırılarına karşı dayanıklılık kazandırmayı amaçlar. Böyle bir kurgunun açık
tuzağı, modelin eğitildiği bozma işleçleriyle sınanmasıdır; bu durumda ölçülen
şey dayanıklılık değil, ezberdir.

İşleçler bu nedenle iki **ayrık** aileye bölünmüştür:

| Aile | Kullanım | İşleçler |
|---|---|---|
| **D** | yalnızca eğitim | ünlü düşürme (`sik` → `sk`), göz-benzeri karakter değişimi (`aptal` → `4ptal`), karakter yineleme (`aptal` → `aptaal`) |
| **H** | yalnızca değerlendirme | ayırma (`aptal` → `a.p.t.a.l`), aksan kaldırma (`şerefsiz` → `serefsiz`), bitişik karakter yer değiştirme (`aptal` → `atpal`) |

Ayrıklık bir kural değil, bir denetimdir: `assert_disjoint(['D'], ['H'])`
çağrısı, hem eğitim verisini üreten hem de dayanıklılık sayısı raporlayan
betiklerin başında yer alır ve uyarı vermek yerine hata fırlatır. Bir defter
çıktısındaki uyarı, denetim sayılmaz.

*Kaynak: `src/obfuscation.py`; `phases/03_defense_design.md` kısıt C3.*

### 2.4.3 Türetme kaynağının ayrılması — ve tasarım sırasında düzeltilen bir hata

Savunmanın 1b bileşeni, küfür içeren ancak saldırgan olmayan kullanımların
şablonlarına dayanır. Bu şablonların **hangi hatalardan** türetildiği yöntemsel
olarak belirleyicidir.

İlk tasarımda şablonlar, geliştirme kümesindeki yanlış pozitiflerin işlev
ailelerinden türetilmişti. Bu döngüseldir: şablonlar geliştirme kümesindeki
hatalardan çıkarılıp yine geliştirme kümesinde ölçülseydi, raporlanan iyileşmenin
bir bölümü modelin değil, şablonun kendisinin ölçümü olurdu. Hata, kod
yazılmadan önce tasarım incelemesinde yakalanmış ve düzeltilmiştir.

Düzeltilmiş yordam şudur: eğitim bölümünün içinde, etikete göre tabakalı **5
katlı çapraz doğrulama** yapılır; her kat için kalan dört kat üzerinde bir model
eğitilir ve o kat üzerinde tahmin üretilir. Böylece 26.992 eğitim satırının
tamamı için, o satırı görmemiş bir modelden gelen **kat dışı** tahminler elde
edilir. Bu, geliştirme kümesinin değerlendirildiği koşulun aynısıdır. Şablonlar
yalnızca bu kat dışı hatalardan türetilir; geliştirme kümesi türetmede hiç
kullanılmaz.

Kat dışı başarım, geliştirme başarımına yakındır — yordamın amaçlanan koşulu
ürettiğinin göstergesi:

| | Kat dışı (eğitim) | Geliştirme |
|---|---:|---:|
| Makro-F1 | 0,8230 | 0,8271 |
| `OFF`-duyarlılık | 0,6985 | 0,6902 |
| `OFF`-kesinlik | 0,7280 | 0,7488 |

Kat dışı çözümleme 1.360 yanlış pozitif (251 `lexicon_hit`, 1.109
`lexicon_free`) ve 1.571 yanlış negatif üretmiştir. `lexicon_hit` yanlış
pozitiflerinden tohumlanmış rastgele 60'ı işlevlerine göre etiketlenmiştir: anlam
çakışması %52, yönlendirilmemiş %18, dolgu %17, alıntı %5, üstdil %3, kalan %5.

Geliştirme kümesi bu aşamada yalnızca **tek bir amaçla** kullanılmıştır: eğitim
tarafındaki aile dağılımının geliştirme tarafındakine benzeyip benzemediğini
görmek, yani tanının genellenip genellenmediğini denetlemek. Türetme için
kullanılmamıştır. Eğitim tarafı ayrıca geliştirme kümesinde hiç görülmeyen iki
örüntü ortaya çıkarmıştır: insan olmayan bir hedefe yöneltilen sövgü
(`sinüzit kadar şerefsiz bişey yok`) ve tarz belirten ikileme kullanımı
(`salak salak gülmek`). Her ikisi de işleç kümesine girmiştir.

*Kaynak: `docs/RESULTS_LOG.md`, 2026-08-15 "Phase 03 step 1" satırı;
`phases/03_defense_design.md` kısıt C1.*

### 2.4.4 Üretilen eğitim verisinin gözle denetimi

Üretilen satırlar, eğitime girmeden önce okunmuştur. Bu, biçimsel bir adım
değildir: okuma sırasında üç ayrı kusur yakalanmış ve her biri bir kurala ve bir
gerileme testine dönüştürülmüştür — (i) sözlükte yanlış eşleşen köklerin
maskelenmesi (`malsef` sözcüğünün `mal` üzerinden eşleşmesi gibi), (ii) küfrün
kendisinin saldırının taşıyıcısı olduğu satırların da maskelenmesi, (iii) tümce
ortasına yapılan eklemelerin dilbilgisi dışı satırlar üretmesi. Hiçbiri toplam
bir ölçütte görünür olmazdı.

Süzgeç bilinçli olarak dar tutulmuştur: 5.211 altın `OFF` satırının yalnızca
382'si (%7) 1a için uygun bulunmuştur. Gerekçe, `phases/03_defense_design.md`
kısıt C2'de şöyle kayıtlıdır: *az sayıda temiz satır, çok sayıda gürültülü
satırdan iyidir.*

*Kaynak: `results/03_defense/augmentation_review.json`; `docs/RESULTS_LOG.md`,
2026-08-15 "Phase 03 step 2" satırı.*

## 2.5 Ön kayıt uygulaması

Ölçüm yapılmadan önce yazılan ve sonrasında değiştirilmeyen kararlar, tarih
damgalı olarak sürüm denetimine işlenmiştir. Uygulanan ön kayıtlar:

| Belge | Sabitlenen karar |
|---|---|
| `phases/01_baseline_diagnosis.md` | üç yönlü karar kuralı (güven aralığı sıfırı dışlıyorsa / içeriyorsa / sonuçsuzsa ne yapılacağı) ve bunun güç temeli; dilimler arası karşılaştırmanın yalnızca `OFF`-duyarlılıkla yapılması |
| `phases/03_defense_design.md` | müdahalenin hedefi (§1.7); türetme kaynağının ayrılması (C1); veri gürültüsüne karşı yapısal süzgeç (C2); D/H ayrıklığı (C3); dört ölçütün birlikte raporlanması |
| `phases/04_calibration.md` | kalibrasyon bölünmesi ve ECE tanımı; eşiğin seçildiği ve ölçüldüğü kümelerin ayrılması; iki çalışma noktasının kuralla belirlenmesi; sıcaklık ölçeklemenin risk–kapsam eğrisini değiştiremeyeceği öngörüsü |
| `phases/08_lexical_analysis.md` | belirteç istatistiklerinin **yalnızca eğitim bölmesinden** çıkarılması (C8-1); sıralama ölçütü ve eşiği (C8-4, C8-5); sözlük üyeliğinin `hit_root` ile tanımlanması (C8-6); adım 3'ün yorum kuralının önceden sabitlenmesi (C8-7); müdahale yasağı (C8-11) |
| `phases/09_deeper_analysis.md` (Aşama 1) | dilim içi ROC-AUC'nin tanımı ve beraberlik kuralı (C9-2); bootstrap kurgusu (C9-3); "büyük" ve "küçük" farkın **sayısal** eşikleri, tasarım hesabından (C9-4); beş dallı, sıralı ve tüketici karar kuralı (C9-5); her kararın raporda neyi zorunlu kıldığı (C9-6); PR-AUC'nin karara kanıt olarak kullanılamayacağı (C9-9); duyarlılık denetimlerinin kararı **devirememesi** (C9-10) |
| `phases/09_deeper_analysis.md` (Aşama 1b) | denetimin `run_raw` olması ve **yerine başka bir dosya konulamaması** (C9-12); eşleştirilmiş bootstrap kurgusu (C9-13); dört dallı yorum kuralı ve 0,01 tabanı (C9-15); **denetim diliminin öngörüsünün ölçümden önce yazılması** — mekanizma küresel bir puan kayması ise `lexicon_hit` AUC'sinin de düz kalması gerektiği (C9-16) |

Ön kayıtların işlevi, sonuçlar görüldükten sonra karar kuralının
değiştirilmesini engellemektir. Örneğin kalibrasyon ön kaydı, sıcaklık
ölçeklemenin risk–kapsam eğrisini **değiştiremeyeceğini** önceden ilan eder
(dönüşüm tekdüzedir, dolayısıyla satırların güven sıralamasını değiştiremez); bu, ölçümde
sayısal olarak doğrulanmış ve böylece "kalibrasyon seçici tahmini iyileştirdi"
biçiminde yanlış bir iddianın kazara kurulması engellenmiştir.

## 2.6 Tek kullanımlık test kümesi muhasebesi

Resmî test kümesinin tek kez kullanılması (§1.5) kod düzeyinde uygulanır.

`load_coltekin_test` işlevi, açık bir bayrak olmadan çağrıldığında hata verir.
Bayrak verildiğinde, baytlar okunmadan **önce** eklemeli bir açılış günlüğüne
kayıt düşer. Çalıştırma tamamlandığında ayrı bir "harcandı" kaydı yazılır; bu
kayıt var olduğu sürece işlev, hangi çalıştırmanın hangi işlemede kümeyi
harcadığını belirten bir hata mesajıyla reddeder. Her iki dosya da sürüm
denetimine dâhildir; dolayısıyla kısıt, deponun başka bir makinedeki kopyasında
da geçerlidir.

Sıralama önemlidir. Günlüğün okumadan önce yazılması, çöken bir çalıştırmanın
kayıttan silinememesini sağlar; "harcandı" kaydının yalnızca tamamlanmış bir
çalıştırmadan sonra yazılması ise, çöken bir denemeden sonra bir kez dürüst
yeniden deneme hakkı bırakır. Bu çalışmada kümenin iki kez açıldığı ve ilk
açılışın hiçbir sayı üretmeden çöktüğü §1.5'te kayıtlıdır.

Eşikler de aynı ilkeye tabidir: test üzerinde hiçbir eşik türetilmemiştir.
Seçici tahmin eşikleri kalibrasyon kaydından okunur ve değiştirilmeden
uygulanır; sonuç dosyası bunu `thresholds_re_derived_on_test: false` alanıyla
kayda geçirir.

## 2.7 Değerlendirme

**Ölçüt tanımları.** Makro-F1, iki sınıfın F1 değerlerinin ortalamasıdır; `NOT`
sınıfı da kendi ikili probleminin pozitif sınıfı olarak ele alınır.
`OFF`-duyarlılık ve `OFF`-kesinlik, `OFF` sınıfı için tanımlanır. Bütün ölçütler
bağımlılıksız bir modülde (`src/evaluate.py`) uygulanmış ve her çalıştırmada
scikit-learn'ün aynı ölçütüyle karşılaştırılmıştır; iki uygulama 10⁻⁹'dan fazla
ayrışırsa çalıştırma hata verir. Böylece ölçüt kodunun kendisi denetlenmiş olur.

**Dilim ölçümleri.** Dilim içi karışıklık matrisleri ham sayılarla saklanır.
Dilim başına makro-F1 ise bilinçli olarak **raporlanmaz**: taban oranlar
farklıdır (§1.4) ve dilimler arası karşılaştırılması yanıltıcı olurdu. Sonuç
dosyalarında bu alan boş bırakılır ve gerekçesi alanın yanına yazılır.

**Dilim içi ROC-AUC.** Duyarlılık karşılaştırması sabit 0,5 eşiğine bağlı
olduğundan (§1.4), dilimler ayrıca **eşikten bağımsız** bir ölçütle
karşılaştırılmıştır (§4.2). Tanım, Mann–Whitney U biçimidir: aynı dilim içinden
rastgele bir altın `OFF` satırının rastgele bir altın `NOT` satırından yüksek
puan alma olasılığı; **beraberlikler yarım puanla** sayılır. Puan olarak modelin
`P(OFF)` değeri kullanılır.

Bu ölçütün dilimler arasında karşılaştırılabilir olmasının nedeni, makro-F1'den
farklı olarak **taban orandan bağımsız** olmasıdır: bir dilimin `NOT`
satırlarının çoğaltılması AUC'yi değiştirmez. Bu değişmezlik, iddia edilmekle
kalmayıp birim testinde gösterilmiştir (`tests/test_stage1_auc.py`).

**Ortalama kesinlik (PR-AUC) aynı ayrıcalığa sahip değildir** ve taban orana
duyarlıdır; bu nedenle ön kayıtta, dilimler arası karara **kanıt olarak
kullanılması yasaklanmıştır** (C9-9). Rapora bu gerekçeyle girmemektedir.

Güven aralıkları, dört (dilim × altın sınıf) hücresinin her biri **kendi
büyüklüğüne** yeniden örneklenerek, 10.000 yinelemeli tabakalı bootstrap ve
yüzdelik aralıkla hesaplanır (tohum 42). Karar eşikleri — hangi farkın "büyük",
hangisinin "küçük" sayılacağı — sayı üretilmeden önce, yalnızca paydalara ve
varsayılan bir AUC değerine dayanan bir tasarım hesabından sabitlenmiştir.

**Güven aralıkları ve farklar.** Protokol §1.7'de tanımlanmıştır: satırlar
üzerinde 1.000 yeniden örneklemeli bootstrap; aynı satırlar üzerindeki iki sistem
için eşleştirilmiş yordam; ayrık dilimler için bağımsız yeniden örnekleme;
farklar işaretine bakılmaksızın raporlanır. Bir ölçütün tanımsız kaldığı
yeniden örneklemeler (örneğin hiç `OFF` örneği çekilmemişse) sıfır sayılmaz;
atılır ve sayıları kaydedilir.

## 2.8 Yeniden üretilebilirlik

Her çalıştırma; kod işlemesini (git SHA), kitaplık sürümlerini, donanımı,
girdi dosyalarının SHA-256 özetlerini, geliştirme parmak izini ve tam
hiperparametre kümesini bir `run_config.json` dosyasına yazar. Sonuçlar
`docs/RESULTS_LOG.md` içine kronolojik olarak eklenir; bu günlük yalnızca
eklemelidir — sonraki bir sonuç öncekiyle çeliştiğinde eski kayıt düzeltilmez,
yeni bir düzeltme kaydı eklenir. Günlükte şu anda **dört** düzeltme kaydı vardır.

Kod tabanı 166 birim testiyle denetlenmektedir; bunlar bölünme ve ölçüt
değişmezlerini, veri üretme kurallarını, kalibrasyon özelliklerini, test kümesi
muhasebesini, gösterim uygulamasının girdi işlemesini ve eşikten bağımsız ölçütün
taban orandan bağımsızlığını kapsar — bu sonuncusu, §4.2'deki karşılaştırmanın
neden geçerli olduğunun kendisidir ve bu nedenle iddia edilmekle bırakılmayıp
sınanmaktadır. Ayrıca, ağır
çalıştırmaların rapor ve kayıt yolları, gerçek çalıştırmadan önce yapay verilerle
kuru olarak sınanır; amaç, saatler süren bir hesaplamadan sonra biçimsel bir
hatanın keşfedilmesini önlemektir.
