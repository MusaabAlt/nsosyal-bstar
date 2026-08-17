# 4. Bulgular

> **Taslak durumu.** KYS rapor şablonu yayımlanmadan önce yazılmıştır; başlık
> numaralandırması geçicidir. Buradaki her sayı `results/` altındaki bir sonuç
> dosyasına ve `docs/RESULTS_LOG.md` içindeki bir kayda dayanır; kaynaklar tablo
> altlarında verilmiştir.

Bu bölüm, birincil ölçütle (§1.7) başlar: **sözlüksüz dilimdeki
`OFF`-duyarlılık.** Genel makro-F1, `lexicon_hit` maliyeti ve yanlış pozitif
sayıları aynı tablolarda, aynı bölümde raporlanır.

## 4.1 Birincil ölçüt — özet

| Sistem | `lexicon_free` `OFF`-duyarlılık (geliştirme) | (resmî test) |
|---|---:|---:|
| Anahtar kelime süzgeci | 0,0000 (tanım gereği) | 0,0000 (tanım gereği) |
| BERTurk (temel) | 0,5628 [0,5210; 0,6010] | 0,5101 [0,4628; 0,5546] |
| **BERTurk + 1a+1b+D** | **0,5965** (ayrı GA yok, aşağıya bakınız) | **0,5459 [0,5021; 0,5899]** |
| Müdahalenin etkisi (eşleştirilmiş fark) | **+0,0336 [+0,0052; +0,0662]** | **+0,0358 [+0,0043; +0,0665]** |

*Kaynak: `results/01_baseline_berturk/metrics.json`,
`results/03_defense/comparison.json`, `results/05_final_test/metrics.json`,
`results/05_final_test/paired_deltas.json`.*

Üç bulgu bu tablodan doğrudan okunur ve bölümün geri kalanı bunları ayrıntılandırır:

1. Anahtar kelime süzgeci bu dilimde **tanım gereği sıfırdır**; sözlüksüz içerik,
   sözlük temelli bir süzgeç için erişilemezdir.
2. Eğitilmiş bir dönüştürücü bu açığı kapatmaz: **sabit 0,5 eşiğinde** sözlüksüz
   saldırgan içeriğin ancak yarısını işaretler. Bu bir *işaretleme*
   başarısızlığıdır; modelin bu içeriği sıralayamadığı anlamına gelmez (§4.2,
   eşikten bağımsız ölçüm).
3. Tanıdan türetilen müdahale bu dilimde **ölçülebilir bir iyileşme** sağlar ve
   bu iyileşme, hiçbir tasarım kararının görmediği resmî test kümesinde
   **yinelenir** (+0,0336 → +0,0358). Her iki güven aralığı da sıfırı dışlar.

**Güven aralıkları hakkında bir not.** Tek tek sistemlerin dilim duyarlılıkları
için verilen aralıklar bağımsız bootstrap'lerdir. **Müdahalenin etkisi için
bakılması gereken aralık, son satırdaki eşleştirilmiş farktır.** İki sistem aynı
satırlar üzerinde puanlandığından, iki bağımsız aralığın örtüşmesine bakmak
farkın belirsizliğini olduğundan büyük gösterir (§1.7). Geliştirme kümesindeki
savunma çeşitlemesi için ayrı bir dilim aralığı kayıtta bulunmamaktadır: o
aşamada hesaplanan ve raporlanan büyüklük, doğrudan eşleştirilmiş farktır.

## 4.2 Temel çizgi ve açığın büyüklüğü

### Genel başarım

| Sistem | Makro-F1 | %95 GA | `OFF`-duyarlılık | `OFF`-kesinlik |
|---|---:|---|---:|---:|
| *Geliştirme kümesi* | | | | |
| Anahtar kelime süzgeci | 0,6799 | [0,6621; 0,6969] | 0,3859 | 0,5782 |
| BERTurk | 0,8271 | [0,8139; 0,8405] | 0,6902 | 0,7488 |
| *Resmî test kümesi* | | | | |
| Anahtar kelime süzgeci | 0,6657 | [0,6456; 0,6857] | 0,3757 | 0,5479 |
| BERTurk | 0,8095 | [0,7930; 0,8261] | 0,6592 | 0,7295 |
| BERTurk + 1a+1b+D | 0,8093 | [0,7927; 0,8255] | 0,6718 | 0,7168 |

*Kaynak: `results/01_baseline_berturk/metrics.json`,
`results/05_final_test/metrics.json`.*

### Dilimler arası duyarlılık farkı

Birincil ölçütün karşıtı, modelin sözlük eşleşmesi olan dilimdeki
duyarlılığıdır. İkisi arasındaki fark, çalışmanın **tanısal** bulgusudur.

Burada iki ayrı büyüklük vardır ve okuyucunun birini diğerine tercih etmesi
gerekmez; ikisi farklı işler görür. **Duyarlılık farkı, tanının kendisidir**:
sorunun var olduğunu, büyüklüğünü ve bir dönüştürücü tarafından kapatılmadığını
gösterir; bu, çalışmanın betimleyici katkısıdır. **`lexicon_free`
`OFF`-duyarlılığı ise müdahalenin ön kayıtlı hedefidir** (§1.7): tanıdan türetilen
girişimin başarısı bu ölçüt üzerinden değerlendirilir. Birincisi sorunu ölçer,
ikincisi çözüm denemesini ölçer.

| | `lexicon_hit` | `lexicon_free` | **Fark** | %95 GA | Sıfırı dışlıyor mu |
|---|---:|---:|---:|---|---|
| Geliştirme, BERTurk | 0,8930 | 0,5628 | **+0,3301** | [+0,2771; +0,3827] | evet |
| Resmî test, BERTurk | 0,9071 | 0,5101 | **+0,3970** | [+0,3418; +0,4542] | evet |
| Resmî test, +1a+1b+D | 0,8810 | 0,5459 | +0,3352 | [+0,2803; +0,3964] | evet |

*Kaynak: aynı dosyalar. Geliştirme dilim GA'ları: `lexicon_hit`
[0,8618; 0,9248], `lexicon_free` [0,5210; 0,6010].*

Yorum, iki cümle gerektirir ve ikisi birlikte verilmelidir:

**Açık yinelenmektedir.** Hiçbir tasarım kararının görmediği bir küme üzerinde
fark yine sıfırı belirgin biçimde dışlamaktadır. Bu, çalışmanın merkezî iddiasının
geliştirme kümesine özgü bir olgu olmadığını gösterir.

**Ancak farkın *büyümesi* kanıtlanmış bir bulgu değildir.** Geliştirme ve test
aralıkları [+0,3418; +0,3827] bandında örtüşmektedir; dolayısıyla +0,0669'luk
artış örnekleme değişkenliğiyle tutarlıdır ve ayrı bir bulgu olarak
sunulmamalıdır.

Büyümenin bir mekanizması vardır ve bu kayıt altındadır: geliştirmeden teste
geçerken genel makro-F1 yalnızca 1,8 puan düşerken (0,8271 → 0,8095), düşüş
dilimler arasında **eşit dağılmamıştır** — `lexicon_hit` duyarlılığı 1,4 puan
*yükselmiş*, `lexicon_free` duyarlılığı 5,3 puan *düşmüştür*. Model, zaten iyi
olduğu dilimde iyileşmiş, zaten kötü olduğu dilimde kötüleşmiştir.

### Eşikten bağımsız karşılaştırma — dilim içi ROC-AUC

Yukarıdaki bütün duyarlılık sayıları **sabit 0,5 eşiğinde** ölçülmüştür ve bu,
karşılaştırmaya yöneltilebilecek en güçlü itirazın kaynağıdır. İki dilimin taban
oranları belirgin biçimde farklıdır (%57,8'e karşı %13,6; §1.4). İyi kalibre
edilmiş bir model, seyrek sınıfın bulunduğu dilimde daha düşük olasılıklar üretir;
bu durumda sabit bir eşikte duyarlılık, model içeriği daha kötü *çözümlediği için*
değil, **eşiğin nereye düştüğü yüzünden** düşer. Duyarlılık farkının ne kadarı
eşik yerleşiminden, ne kadarı sıralama niteliğinden gelmektedir?

ROC-AUC bu soruyu yanıtlayabilir, çünkü **eşikten de taban oranından da
bağımsızdır**: aynı dilim içinden rastgele seçilen bir altın `OFF` satırının,
rastgele seçilen bir altın `NOT` satırından daha yüksek puan alma olasılığıdır.
Ölçüm, ölçüm yapılmadan **önce** işlenmiş eşiklerle yürütülmüştür
(`phases/09_deeper_analysis.md`, C9-1…C9-11, işleme `12afa74`): "büyük" fark
`≥ 0,05`, "küçük" fark `< 0,02`; aradaki bant önceden **sonuçsuz** ilan
edilmiştir.

| Dilim (geliştirme) | Taban oran | **ROC-AUC** | %95 GA | `OFF`-duyarlılık (0,5) |
|---|---:|---:|---|---:|
| `lexicon_hit` | %57,8 | **0,9306** | [0,9102; 0,9495] | 0,8930 |
| `lexicon_free` | %13,6 | **0,8962** | [0,8821; 0,9095] | 0,5628 |
| **Fark** | | **+0,0345** | **[+0,0103; +0,0585]** | **+0,3301** |

*Kaynak: `results/09_deeper_analysis/stage_1/stage1_auc.json`; 10.000 tabakalı
bootstrap yinelemesi, tohum 42.*

**Ön kayıtlı karar: `INTERMEDIATE` (sonuçsuz).** Güven aralığı sıfırı
dışlamaktadır — yani sıralama niteliğinde gerçek bir fark vardır — ancak nokta
kestirimi, önceden sonuçsuz ilan edilmiş banda düşmektedir. Dahası aralık, **üç
bandın tamamına yayılmaktadır**: alt ucu 0,02'nin altında, üst ucu 0,05'in
üstündedir. Bu, 355/259 ve 565/3.585 paydalarının çözünürlük sınırıdır ve ön
kayıttaki tasarım hesabında (Hanley–McNeil) ±0,03–0,04 olarak **önceden**
öngörülmüştür. Daha büyük bir geliştirme kümesi bu soruyu ayrıştırabilir; bu
çözümleme ayrıştıramaz.

**Yine de kesinleşen bir şey vardır: duyarlılık farkı, ağırlıklı olarak bir
sıralama niteliği farkı değildir.** +0,3301'lik duyarlılık farkı, +0,0345'lik bir
AUC farkının üzerinde durmaktadır. Model, küfür taşımayan saldırgan içeriği,
küfür taşımayan zararsız içeriğin **üzerinde sıralamaktadır** ve bunu, küfür
taşıyan dilimdekine yakın bir başarımla yapmaktadır (0,8962'ye karşı 0,9306).
Yapmadığı şey, bu içeriği 0,5 eşiğinin ötesine taşımaktır.

Farkın nerede olduğu, puan dağılımlarında doğrudan görünmektedir:

| Dilim | Sınıf | n | Ortalama | Medyan | ≤ 0,5 payı |
|---|---|---:|---:|---:|---:|
| `lexicon_hit` | altın `OFF` | 355 | 0,8524 | **0,9650** | **%10,7** |
| `lexicon_free` | altın `OFF` | 565 | 0,5285 | **0,5861** | **%43,7** |
| `lexicon_hit` | altın `NOT` | 259 | 0,2438 | 0,1057 | %81,9 |
| `lexicon_free` | altın `NOT` | 3.585 | 0,0999 | 0,0313 | %95,4 |

*Kaynak: aynı dosya.*

Küfür taşıyan saldırgan bir satırın medyan puanı 0,9650; küfür taşımayanınki
0,5861'dir — ikisi de eşiğin üzerindedir, ancak ikincisi karar sınırının hemen
üzerinde durmaktadır. **Küfürsüz saldırgan içeriğin %43,7'si eşiğin altında ya da
tam üzerinde (`p ≤ 0,5`) kalmakta, dolayısıyla işaretlenmemektedir; küfür taşıyan
içerikte bu oran %10,7'dir.** Dilimin
tamamı aşağı kaymıştır: zararsız satırlar güvenli bölgeye, saldırgan satırlar ise
karar sınırının içine.

**Ayrıştırılamayan nokta açıkça belirtilmelidir.** Bu aşağı kaymanın %13,6'lık
taban orana **doğru kalibrasyondan** mı yoksa modelin bu içerikteki **gerçek
güvensizliğinden** mi kaynaklandığı, bu çözümlemeyle **ayrılamamaktadır.** İki
katkının payları ölçülmemiştir ve bu rapor bir pay iddia etmemektedir (§5.12).

## 4.3 Açık iki yönlüdür

Bulgu yalnızca düşük duyarlılık değildir. Aynı kısayol, ters yönde de
işlemektedir: sözlük eşleşmesi bulunan satırlarda model gereğinden fazla `OFF`
demektedir.

| Dilim (geliştirme) | Altın `NOT` | Yanlış pozitif | Yanlış pozitif oranı |
|---|---:|---:|---:|
| `lexicon_hit` | 259 | 47 | **%18,1** |
| `lexicon_free` | 3.585 | 166 | **%4,6** |

*Kaynak: `results/01_baseline_berturk/metrics.json` dilim karışıklık matrisleri.*

Küfür belirtecinin varlığı `OFF` kararını yaklaşık dört kat daha olası
kılmaktadır. Duyarlılık açığıyla birleştiğinde ortaya çıkan tablo, tek bir
mekanizmanın iki yüzüdür: **modelin KARARINI belirleyen şey, ağırlıklı olarak
saldırgan sözcük dağarcığının varlığıdır — saldırgan eylemin kendisi değil.**

**Bu cümlenin sınırı, §4.2'deki eşikten bağımsız ölçümle çizilmiştir ve
çizilmelidir.** Buradaki bulgu, modelin küfür olmadan saldırganlığı
*ayırt edemediği* anlamına **gelmez**: `lexicon_free` diliminde ROC-AUC
**0,8962**'dir, yani model bu dilim içinde saldırgan içeriği zararsız içeriğin
üzerinde sıralamaktadır. Desteklenen iddia daha dardır ve şudur: **küfür
bulunmadığında puanlar sistematik olarak bastırılmakta** (altın `OFF` medyanı
0,5861'e karşı 0,9650), dolayısıyla **sabit eşikte model bu içeriği
işaretlememektedir** (%43,7'ye karşı %10,7). İşaretleme başarısızlığı gerçektir
ve işletme açısından bağlayıcıdır; sıralama yetersizliği iddiası ise
desteklenmemektedir.

Bu, tanının **birinci** parçasıdır ve tek başına yeterli değildir: küfür
belirteci hiç taşımayan 118 yanlış pozitifi açıklayamaz. İkinci parça, bu
bölümün sonundaki *İkinci yordayıcı: muhatap alma* alt başlığında verilmektedir.

### Terimsel açıklama: "küfür taşımayan yanlış pozitif" üç ayrı büyüklüktür

Bu raporda, yanlış pozitiflerin küfür içerip içermediğine ilişkin **üç farklı
ölçüm** kullanılmaktadır. Üçü de aynı 213 satır üzerinde tanımlıdır, farklı
sayılar verir ve **birbirinin yerine kullanılamaz.** Karışıklığı önlemek için her
biri kendi adıyla anılmaktadır.

| Terim | Tanım | Temel modelde değer |
|---|---|---:|
| **Sözlüksüz dilimdeki yanlış pozitif** | Dondurulmuş `hit_root` eşleştiricisinin hiçbir kök bulamadığı satırlar. Dilim üyeliğidir (§1.4). | **166** |
| **Elle sayılan, küfür belirteci taşımayan yanlış pozitif** | 213 satırın tamamının elle okunmasıyla, insan yargısına göre hiçbir küfür belirteci içermeyenler. Sözlükte bulunmayan ve gizlenmiş biçimleri de kapsar. | **118** |
| **Otomatik ölçüt: şüpheli-kök dışı sözlük eşleşmesi bulunmayan yanlış pozitif** | Eşleşmelerinin tamamı §4.5'teki şüpheli kökler kümesinden gelen satırlar, küfür taşımıyor sayılır. Yeniden üretilebilir bir vekildir. | **185** |

Üç sayı birbiriyle tutarlıdır: 213 = 47 (`lexicon_hit`) + 166 (`lexicon_free`) ve
213 = 28 + 185; aradaki 19 satır, tek eşleşmesi şüpheli bir kök olan yanlış
pozitiflerdir (47 − 28 = 185 − 166 = 19). Elle sayım (118) ikisinden de düşüktür,
çünkü bir insan okuyucu sözlüğün kaçırdığı biçimleri de küfür saymaktadır: elle
95 satırda küfür bulunurken, sözlüğün şüpheli-kök dışı eşleşmesi yalnızca 28
satırdadır.

**Hangisi nerede kullanılır.** Elle sayım (118) hata çözümlemesinin niteliksel
bulgusudur (§4.4). Otomatik vekil (185) çalıştırmalar arası karşılaştırma için
kullanılır (§4.6); mutlak değeri elle sayımla aynı büyüklük değildir ve öyleymiş
gibi okunmamalıdır — **yalnızca çalıştırmalar arasındaki farkları anlamlıdır.**
Bu sınırlılık `results/03_defense/findings.md` içinde de kayıtlıdır.

### İkinci yordayıcı: muhatap alma

Yukarıdaki tanı eksiktir. Sözcük dağarcığı açıklaması, küfür belirteci hiç
taşımayan **118 yanlış pozitifi** açıklayamaz: bu satırlarda modelin tepki
verdiği şey, tanımı gereği küfür değildir. Bu satırların nesi model tepkisini
tetiklediği, ayrı bir ölçümle araştırılmıştır (`results/08_lexical_analysis/`).

Ölçüm **yalnızca eğitim bölmesi** üzerinde yapılmıştır: her belirtecin satır
sıklığı, `OFF` satırlarındaki sıklığı ve koşullu olasılığı çıkarılmış, taban oran
**P(OFF) = 0,1931** ile karşılaştırılmıştır. Sıralama, seyrek ama uç oranlı
belirteçlerin listeyi ele geçirmemesi için sıklıkla ağırlıklandırılmıştır
(binom `z` değeri; ayrıntı §2 ve `phases/08_lexical_analysis.md`). Eşikler ve
yorum kuralı, **hiçbir sayı hesaplanmadan önce** yazılmış ve depoya
işlenmiştir.

En sık 200 belirteç arasında, sözlükte **bulunmayan** ancak `OFF` yönünde güçlü
sapma gösteren 19 belirteç bulunmaktadır. Bunların **on tanesi işaret edici
(deiktik), beş tanesi ikinci tekil/çoğul şahıs zamiridir**: `sen`, `senin`,
`siz`, `sizin`, `sizi` — yanlarında seslenme ünlemi `lan`, ikinci şahıs emir
kipi `bak`, kişi göndergesi `adam` ve dış grup işaretleyicileri `bunlar`,
`onlar`. Koşullu olasılıklar taban oranın belirgin biçimde üzerindedir:
P(`OFF` | `sizin`) = **0,4533** (375 satır), P(`OFF` | `bunlar`) = **0,4592**
(233 satır).

Bu belirteçler, 118 satırda eşleştirilmiş karşılaştırmada da yoğunlaşmaktadır.
118 satırın **%39,8'i (47/118)** güçlü sapmalı sözlük dışı bir belirteç
taşımakta; uzunluk ve dilim bakımından eşleştirilmiş doğru negatiflerde bu oran
**%19,2**'dir. Fark **+0,2066 [+0,1216; +0,2960]**'dır. Denetim ölçümü, bulgunun
uzunluk ya da üslup etkisi olmadığını göstermektedir: `NOT` yönünde güçlü sapma
gösteren belirteçler için aynı fark **−0,0032 [−0,0500; +0,0506]**, yani sıfırdan
ayırt edilemezdir.

**Tanı bu nedenle iki parçalıdır.** Model hem saldırgan **sözcük dağarcığına**
(§4.3, ilk kısım) hem de **muhatap alınmaya** tepki vermektedir; ikincisi
küfürden bağımsız bir `OFF` yordayıcısıdır. Bu, dilim ölçütünün göremeyeceği bir
örüntüdür: `lexicon_hit`/`lexicon_free` ayrımı küfür varlığı üzerinde ikili
tanımlıdır ve başka hiçbir şeye duyarlı değildir.

**Beklenen değil, ölçülen sonuç budur.** Çalışmanın başlangıcında sınanan
varsayım, 118 satırı **siyasi, dinî veya kimliksel terimlerin** açıkladığı
yönündeydi. Bu varsayım **çözünürlüğe bağlıdır ve önerildiği biçimde
doğrulanmamıştır**: en sık 200 belirteç arasında bu türden yalnızca iki terim
bulunmakta (`türk`, `oy`) ve tek başlarına ölçülebilir bir etki
vermemektedirler — **+0,0111 [−0,0138; +0,0437]**. Aday havuzu `df ≥ 30`
düzeyine genişletildiğinde bu türden 26 terim ortaya çıkmakta (`akp`, `chp`,
`hdp`, `pkk`, `fetö`, `atatürk`, `islam`, `israil`, `kürt`, `müslüman`,
`tayyip`, `vatan` …) ve etki görünür hale gelmektedir: 118 satırın 23'ünde,
**+0,1494 [+0,0825; +0,2224]**. Aynı genişletilmiş çözünürlükte işaret edici
küme yine daha büyüktür: 118 satırın 40'ında, **+0,2106 [+0,1263; +0,2982]**.
İki kümenin belirteçleri ayrık olmakla birlikte satırları ayrık değildir — 9
satır her ikisini birden taşır — dolayısıyla sayılar toplanmaz. Açıklama her iki
okumada da **kısmidir: 118 satırın 47'si (%39,8) sınanan hiçbir sözcük
dağarcığı düzeyinde güçlü sapmalı belirteç taşımamakta ve açıklanmadan
kalmaktadır.**

> **Bu bulgunun kanıt gücü.** Ölçülen şey **birlikte görülmedir**. Eğitimde
> sapma gösteren bir belirtecin bir hata satırında bulunması, o işaretin modelin
> öğrendiği veride **mevcut** olduğunu gösterir; modelin onu **kullandığını**
> göstermez. Kullanımın gösterilmesi öznitelik atfı (attribution) ya da çıkarma
> (ablation) çözümlemesi gerektirir; **bu çalışmada ikisi de yapılmamıştır.**
> Ayrıca belirteçlerin "işaret edici" ve "siyasi" kümelere ayrılması, sıralı
> liste görüldükten **sonra** yapılmış bir yorumdur; önceden yazılmış olan
> nicelik, 19 belirteçlik kümenin bütünüdür. Bölüm 5'teki sınırlılıklar bu
> ayrımı korumaktadır.

## 4.4 Hata çözümlemesi — sayım

Temel modelin geliştirme kümesindeki **285 yanlış negatifinin ve 213 yanlış
pozitifinin tamamı** elle okunmuş ve etiketlenmiştir.

### Yanlış negatifler: etiket gürültüsü mü, gerçek kaçırma mı

| Örneklem | MISLABEL | IMPLICIT | EVASION | AMBIG | Yanlış etiket oranı |
|---|---:|---:|---:|---:|---:|
| Güvene göre sıralı ilk 60 (**yanlı**) | 14 | 18 | 6 | 22 | %23,3 |
| 247 sözlüksüz YN içinden rastgele 40 (**yansız**, tohum 42) | 4 | 14 | 1 | 21 | **%10,0** |

*Kaynak: `results/02_failure_analysis/fn_tags.json`.*

İki satır arasındaki fark, kendi başına bir bulgudur. En güvenle yanlış olan
satırları okumak, etiket gürültüsünü **seçen** bir örneklemdir: model en yüksek
güvenle yanlış olduğu yerlerde çoğunlukla etiketin kendisi tartışmalıdır.
Bu nedenle %23,3, dilimin gürültü oranının bir tahmini değil, bir üst sınırıdır.
Yansız örneklem **%10** vermektedir ve savunulabilir olan budur.

Sonuç: sözlüksüz yanlış negatiflerin baskın kipi etiket gürültüsü **değildir.**
Yansız örneklemin %35'i (14/40) açık biçimde örtük saldırıdır — mecazlı hakaret,
alay, tehdit, gruba yönelik nefret.

### En büyük öbek: kararı insan yargısına bağlı satırlar

Yansız örneklemin **en kalabalık kategorisi ne gürültü ne de açık örtük saldırıdır:
21/40 satır (%52,5) AMBIG olarak etiketlenmiştir** — yani saldırgan sayılıp
sayılmayacağı, uygulanan işaretleme sözleşmesine bağlıdır. Bu öbek, bulgunun
raporlanmasında atlanamaz; tek başına diğer üç kategorinin toplamına yakındır.

Bu satırların büyük bölümü tek bir türdendir: **siyasetçilere ve kurumlara
yöneltilen sert eleştiri.** Yansız 40 satırlık örneklemin yaklaşık **13'ü** bu
banda düşmektedir. Bir siyasetçiye yöneltilen sert bir ifadenin "saldırgan" mı
yoksa "siyasi eleştiri" mi sayılacağı, dilbilimsel bir olgu değil, bir işaretleme
sözleşmesi kararıdır.

Bu çalışmada alınan tutum açıktır ve `docs/RESULTS_LOG.md` içinde kayıtlıdır:
**Çöltekin'in işaretleme sözleşmesi olduğu gibi benimsenmiş, hiçbir satır yeniden
etiketlenmemiştir.** Alternatif bir sözleşme benimsenseydi bu 13 satırın altın
etiketi değişebilir ve bununla birlikte hem temel modelin duyarlılığı hem de
raporlanan açık bir miktar kayardı. Bu, ölçümün ortadan kaldırılmış değil,
**belirtilmiş** bir sınırlılığıdır ve §5'te yeniden ele alınmaktadır.

Bu öbeğin varlığı, §4.4'ün ilk bulgusunu da nitelendirmektedir: sözlüksüz
yanlış negatiflerin baskın kipi etiket gürültüsü değildir, ancak "hepsi modelin
kaçırdığı gerçek saldırılardır" da denemez. Ölçülebilir olan üç şey vardır —
gürültü %10, açık örtük saldırı %35, sözleşmeye bağlı %52,5 — ve üçü birlikte
raporlanmalıdır.

### Yanlış pozitifler: küfrün işlevi

213 yanlış pozitifin **95'i (%44,6)** en az bir küfür belirteci taşımaktadır. Bu
95 satırın işlevlerine göre dağılımı:

| İşlev | Sayı |
|---|---:|
| Yönlendirilmemiş (`NONDIR`) | 26 |
| Dolgu / pekiştireç (`FILL`) | 19 |
| Anlam çakışması (`SENSE`) | 16 |
| Üstdil kullanım (`META`) | 9 |
| Olumsuzlanmış (`NEG`) | 6 |
| Alıntı (`QUOT`) | 5 |
| Kendine yönelik (`SELF`) | 3 |
| **Gerçekten yönlendirilmiş hakaret (`DIRECT`)** | **11** |

*Kaynak: `results/02_failure_analysis/fp_function_tags.json`.*

**Küfür taşıyan 95 yanlış pozitifin 84'ü (%88,4) hiçbir saldırgan eylem
gerçekleştirmemektedir.** `lexicon_hit` diliminin 47 yanlış pozitifi içinde bu
oran daha da belirgindir: 43'ü (%91,5) yönlendirilmiş bir saldırgan kullanım
değildir.

Kullanım–anma ayrımının dar tanımı (üstdil + olumsuzlanmış + alıntı) 213 satırın
20'sini kapsar; geri kalan küfür taşıyan yanlış pozitifler hedefsizlik, dolgu
işlevi ve anlam çakışmasından gelmektedir. Küfür taşımayan 118 yanlış pozitif ise
ayrı bir olgudur ve bu savunmanın konusu değildir; ne olduğu §4.3'teki *İkinci
yordayıcı: muhatap alma* alt başlığında ölçülmüştür. Bu satırların hata
çözümlemesi sırasında "din ve siyaset konusu" olarak nitelenmesi, sonradan
yapılan ölçümle **yalnızca kısmen** desteklenmiştir: siyasi/dinî terim varsayımı
çözünürlüğe bağlıdır ve tek başına baskın değildir (§4.3).

### Denetim noktası kararlılığı

Etiketlenen satırların denetim noktasına özgü olup olmadığı ayrıca denetlenmiştir:
ilk 60 yanlış negatifin **0'ı**, ilk 40 yanlış pozitifin **1'i** denetim noktasına
özgüdür. Çözümleme, iki devir arasında oynayan satırlar üzerine kurulmamıştır.

## 4.5 Dilim tanımının duyarlılık denetimi

Kök eşleşmesi (§1.2), bazı satırları yanlış nedenle `lexicon_hit` saymaktadır:
`allah`, `ana`, `emi`, `mal`, `göt`, `cim`, `sie` kökleri `eminim`, `malatya`,
`götürür` gibi tamamen zararsız sözcüklerle eşleşmektedir. Bu, dondurulmuş Gün 1
davranışıdır ve **sonradan değiştirilmemiştir**; bunun yerine etkisi ölçülmüştür.

`lexicon_hit` diliminin 614 satırının **248'i (%40)** yalnızca şüpheli bir kök
üzerinden eşleşmektedir (151 birebir, 97 yalnızca önek). Bu 248 satırın altın
dağılımı 175 `NOT` / 73 `OFF` iken, kalan 366 satırınki 84 `NOT` / 282 `OFF`'tur.

| | `lexicon_hit` duyarlılık | `lexicon_free` duyarlılık | Fark | %95 GA |
|---|---:|---:|---:|---|
| Raporlanan (dondurulmuş tanım) | 0,8930 | 0,5628 | +0,3301 | [+0,2771; +0,3827] |
| Duyarlılık (248 satır hariç) | 0,9291 | 0,5628 | **+0,3662** | [+0,3187; +0,4169] |

*Kaynak: `results/02_failure_analysis/slice_sensitivity.json`.*

**Kirlenme, farkı büyütmemekte, küçültmektedir.** Hariç tutulan satırların %71'i
`NOT` olduğundan, bu satırlar `lexicon_hit` dilimini `lexicon_free` yönünde
seyreltmektedir. Yani raporlanan +0,3301, temizlenmiş tanıma göre **muhafazakâr**
bir değerdir. Bu, bir eleştirmenin bekleyeceğinin tam tersi yöndedir ve
tartışılarak değil ölçülerek gösterilmiştir. Raporlanan başlık sayı yine de
dondurulmuş tanıma göre verilmektedir; duyarlılık değeri onun yerine geçmez.

**Ancak aynı düzeltme, §4.2'deki eşikten bağımsız ölçütü ters yöne
taşımaktadır**: 248 satır dışarıda bırakıldığında ROC-AUC farkı +0,0345'ten
**+0,0062**'ye, yani ön kayıtlı "küçük" eşiğinin de altına inmektedir. Tek bir
düzeltme, iki ölçütü zıt yönlerde hareket ettirmektedir. Bu, §5.3'te bir
sınırlılık olarak ele alınmakta ve **çözülmemektedir.**

## 4.6 Müdahalenin bileşen düzeyindeki etkisi

Müdahale, birbirinden ayrılabilir olması için **dört ayrı çalıştırma** halinde
ölçülmüştür. 1a ve 1b hem hacim hem mekanizma bakımından farklı olduğundan,
birleşik tek bir çalıştırma etkiyi bileşenlere atfedemezdi.

| Ölçüt (geliştirme) | Temel | +1a | +1a+1b | +1a+1b+D |
|---|---:|---:|---:|---:|
| Genel makro-F1 | 0,8271 | 0,8244 | 0,8173 | 0,8202 |
| **`lexicon_free` `OFF`-duyarlılık** | 0,5628 | 0,5204 | 0,5841 | **0,5965** |
| `lexicon_hit` `OFF`-duyarlılık | 0,8930 | 0,8873 | 0,8282 | 0,8507 |
| `lexicon_hit` yanlış pozitif oranı | 0,1815 | 0,1737 | 0,1853 | 0,1931 |
| Duyarlılık farkı | +0,3301 | +0,3670 | +0,2441 | +0,2542 |
| Yanlış pozitif (toplam) | 213 | 182 | 232 | 245 |
| — şüpheli-kök dışı sözlük eşleşmesi bulunmayan (otomatik vekil, §4.3) | 185 | 156 | 205 | 215 |
| H ailesiyle bozulmuş geliştirme, `OFF`-duyarlılık | 0,6565 | 0,6261 | 0,6652 | 0,6793 |

Temel modele karşı **eşleştirilmiş** farklar (aynı satırlar; GA sıfırı dışlıyorsa
gerçek bir değişim):

| | Makro-F1 | `lexicon_free` `OFF`-duyarlılık | `lexicon_hit` `OFF`-duyarlılık |
|---|---|---|---|
| +1a | −0,0027 [−0,0125; +0,0065] | **−0,0425 [−0,0722; −0,0110]** | −0,0056 [−0,0310; +0,0194] |
| +1a+1b | −0,0098 [−0,0208; +0,0006] | +0,0212 [−0,0087; +0,0502] | **−0,0648 [−0,0978; −0,0315]** |
| **+1a+1b+D** | −0,0069 [−0,0185; +0,0052] | **+0,0336 [+0,0052; +0,0662]** | **−0,0423 [−0,0778; −0,0109]** |

*Kaynak: `results/03_defense/comparison.json`, `findings.md`.*

Dört çalıştırmalı kurgunun maliyeti burada karşılığını vermektedir:

**1a tek başına hedeflediği şeyi kötüleştirmiştir** (−0,0425, GA sıfırı dışlıyor).
Olası mekanizma, eğitimde bulunup çıkarımda hiç görülmeyen bir `[MASK]`
belirtecinin modele yalnızca eğitim sırasında erişilebilir bir ipucu vermesidir;
model buna daha az `OFF` diyerek yanıt vermiştir (toplam yanlış pozitif 213 → 182).

**1b, `lexicon_hit` duyarlılığını düşürmüş** (−0,0648) ancak **kendi hedefine
ulaşamamıştır**: kesmek için tasarlandığı `lexicon_hit` yanlış pozitif oranı
0,1815'ten 0,1853'e *yükselmiştir*. Sözcüksel ipucu zayıflatılmış, yerine
edimbilimsel ayrım konulamamıştır.

**D ailesi küçük ama olumlu bir aktarım sağlamıştır**: H ailesiyle bozulmuş
geliştirme kümesinde `OFF`-duyarlılık `+1a+1b`'ye göre +0,0141 yükselmiştir. Bu,
yalnızca *görülmemiş gizlemeye dayanıklılık* olarak raporlanır. Ayrıca H bozması
temel modelin makro-F1'ini yalnızca 0,0149 düşürmektedir; bu, sınamanın kendisinin
zayıf olduğunu gösterir (§Sınırlılıklar).

**Tam çeşitlemede birincil ölçüt gerçek bir kazanç göstermektedir**: +0,0336, GA
sıfırı dışlıyor.

## 4.7 Sistem düzeyindeki etki ve bedeller

Aynı müdahalenin resmî test kümesindeki eşleştirilmiş farkları:

| Ölçüt (resmî test) | Fark (+1a+1b+D − temel) | %95 GA | Sıfırı dışlıyor mu |
|---|---:|---|---|
| **`lexicon_free` `OFF`-duyarlılık** | **+0,0358** | **[+0,0043; +0,0665]** | **evet** |
| Genel makro-F1 | −0,0002 | [−0,0129; +0,0118] | hayır |
| `OFF`-duyarlılık | +0,0126 | [−0,0126; +0,0364] | hayır |
| `OFF`-kesinlik | −0,0127 | [−0,0397; +0,0109] | hayır |
| `lexicon_hit` `OFF`-duyarlılık | −0,0260 | [−0,0593; +0,0077] | hayır |

*Kaynak: `results/05_final_test/paired_deltas.json`. Tek geçişte kaydedilmiş
tahminlerden hesaplanmıştır; test kümesi yeniden açılmamıştır.*

Bu tablo, iki ölçekli bir sonucu birlikte göstermektedir ve ikisi de raporlanır.

**Bileşen düzeyinde: kazanç gerçektir ve yinelenmiştir.** Ön kayıtta hedef olarak
ilan edilen ölçüt, iki bağımsız ölçümde de yaklaşık 3,5 puan yükselmiştir ve her
iki güven aralığı da sıfırı dışlamaktadır.

**Sistem düzeyinde: net etki yoktur.** Genel makro-F1 −0,0002'dir; bir sonucun
düz olabileceği kadar düzdür. Kazanç, kesinlik tarafındaki (−0,0127) ve
`lexicon_hit` tarafındaki (−0,0260) maliyetlerce soğurulmaktadır. Bu iki
maliyetin hiçbiri tek başına gürültüden ayırt edilebilir değildir; birlikte ise
kazancı götürmektedirler.

**Geliştirme ile test arasındaki bir farkın açıkça belirtilmesi gerekir.**
Geliştirmede `lexicon_hit` kaybı da sıfırı dışlıyordu (−0,0423
[−0,0778; −0,0109]); testte dışlamamaktadır (−0,0260 [−0,0593; +0,0077]).
Dolayısıyla "eşit büyüklükte bir kayıpla ödenmiş kazanç" ifadesi geliştirme
verisi için doğru, test verisi için kanıtlanmamıştır. Rapor bu ayrımı
düzleştirmez.

Ek bir maliyet, tasarım aşamasında öngörülmüş ve ölçülmüştür: §4.3'te tanımlanan
**otomatik vekil ölçütte** yanlış pozitifler 185'ten 215'e yükselmiştir. Dört
çalıştırmalı kurgu bunu **1a'ya değil** 1b ve D'ye atfetmektedir (1a tek başına
bu sayıyı 156'ya *düşürmüştür*). Birleşik tek bir çalıştırma, bu artışı
yanlışlıkla maskeleme işlecine yükleyecekti. Vekil ölçüt olduğu için burada
anlamlı olan **çalıştırmalar arasındaki +30'luk fark**tır, mutlak değer değil.

## 4.8 Kalibrasyon

Seçici tahmin katmanı modelin güven değerlerine dayandığından, bu değerlerin
niteliği ayrıca ölçülmüştür. Sıcaklık, geliştirme kümesinin yarısında (CAL)
uyarlanmış, bütün sayılar diğer yarısında (EVAL) raporlanmıştır.

| | BERTurk (temel) | +1a+1b+D |
|---|---:|---:|
| Uyarlanan sıcaklık *T* | **0,9948** | **1,9732** |
| NLL (önce → sonra) | 0,2616 → 0,2616 | 0,3831 → 0,2914 |
| ECE, 10 kutu (önce → sonra) | 0,0162 → 0,0154 | 0,0773 → 0,0296 |
| **ECE, 15 kutu (önce → sonra)** | **0,0205 → 0,0191** | **0,0786 → 0,0270** |
| ECE, 20 kutu (önce → sonra) | 0,0206 → 0,0211 | 0,0784 → 0,0313 |
| MCE, 15 kutu | 0,1184 | 0,3487 → 0,2056 |
| İşaretli sapma (doğruluk − güven) | −0,0091 | −0,0739 |

*Kaynak: `results/04_calibration/calibration.json`.*

**Temel modelin kalibrasyona ihtiyacı yoktur.** *T* birimden yarım yüzde
uzaktadır, NLL dört ondalık basamakta değişmemektedir ve ECE 0,0205'ten yalnızca
0,0191'e inmektedir. 20 kutuda değer bir miktar *kötüleşmektedir* (0,0206 →
0,0211); bu, etkisiz bir dönüşümün üstüne kutulama gürültüsü eklendiğinde
beklenen davranıştır ve 15 kutuluk başlık değerin arkasına gizlenmemiştir.

**Savunma çeşitlemesi ise belirgin biçimde kalibrasyonsuzdur** — ECE, temel
modelin 3,8 katıdır. Güvenilirlik tablosu nedeni göstermektedir: EVAL'deki 2.382
satırın 1.958'ini en yüksek güven kutusuna, ortalama 0,9943 güvenle yerleştirmekte,
ancak bu kutuda yalnızca %93,72 doğruluk göstermektedir. Sıcaklık ölçekleme bu
bozukluğun büyük bölümünü onarır (0,0786 → 0,0270) ancak temel modelin ham
değerine ulaşamaz.

Bu, Bölüm 3'ün göremeyeceği bir maliyettir: orada ölçülen doğruluktu ve doğruluk
neredeyse hiç değişmemişti; değişen, **güvenin niteliğiydi.**

## 4.9 Seçici tahmin ve çalışma noktaları

**Ön kayıtlı bir öngörü, ölçümle doğrulanmıştır.** Sıcaklık ölçekleme tekdüze bir
dönüşüm olduğundan satırların güven sıralamasını değiştiremez; dolayısıyla
risk–kapsam eğrisini de değiştiremez. Ölçülen fark **tam olarak sıfırdır**
(en büyük mutlak fark 0,00e+00). Bu nedenle "kalibrasyon seçici tahmini
iyileştirdi" biçiminde bir iddia mevcut değildir ve kurulmamıştır. Kalibrasyonun
sağladığı şey, hedeflenen bir hata oranına hangi *eşik değerinin* karşılık
geldiğidir; hangi satırların devredileceği değil.

Risk–kapsam eğrisi (geliştirme, temel model):

| Kapsam | Makro-F1 | Hata oranı | `OFF`-duyarlılık |
|---:|---:|---:|---:|
| %100 | 0,8271 | %10,45 | 0,6902 |
| %90 | 0,8621 | %7,39 | 0,7143 |
| %80 | 0,8927 | %5,12 | 0,7584 |
| %70 | 0,9222 | %3,21 | 0,8058 |
| %60 | 0,9354 | %2,52 | 0,8343 |
| %50 | 0,9497 | %1,93 | 0,8630 |

*Kaynak: `results/04_calibration/calibration.json` (tam eğri %5 aralıklarla
orada verilmiştir).*

İki çalışma noktası, eğri görülmeden önce kuralla belirlenmiş; eşikleri CAL
yarısında seçilmiş ve **resmî test kümesine değiştirilmeden** uygulanmıştır:

> **Yüksek otomasyon.** %90,2 otomatik kapsamda sistem **0,8485** makro-F1 /
> **%8,52** hata ile çalışmakta, **%9,8**'ini insan incelemesine devretmektedir.
> (GA: makro-F1 [0,8320; 0,8653]; hata [0,0752; 0,0944].)

> **Yüksek kesinlik.** %79,8 otomatik kapsamda sistem **0,8900** makro-F1 /
> **%5,43** hata ile çalışmakta, **%20,2**'sini insan incelemesine
> devretmektedir. (GA: makro-F1 [0,8741; 0,9075]; hata [0,0457; 0,0628].)

*Kaynak: `results/05_final_test/metrics.json`.*

Eşikler aktarılabilmektedir: gerçekleşen kapsam, dört durumda da geliştirme
değerinin 1–2 puan yakınındadır. Bu, bir inceleme katmanının pratikte
gerektirdiği iddiadır — geliştirme verisiyle belirlenen bir eşik, görülmemiş
veride söylediği işi yapmaktadır.

**Devretme, hataları yoğunlaştırmaktadır.** Yüksek otomasyon noktasında
devredilen %9,8'lik dilim, bütün hataların **%35,3'ünü** içermektedir: rastgele
yönlendirmeye göre **3,59 kat** yoğunlaşma. Kuyruk içindeki hata oranı %42,65,
dışındaki %8,52'dir. Yüksek kesinlik noktasında %20,2'lik dilim hataların
%63,5'ini taşımaktadır (3,15 kat).

### Devretme dilim körüdür — bir sıfır sonucu

Tanının işaret ettiği beklenti, güven temelli devretmenin özellikle sözlüksüz
hataları insana yönlendirmesiydi. **Bu gerçekleşmemektedir.**

| Çalışma noktası (resmî test) | `lexicon_free` devretme oranı | `lexicon_hit` devretme oranı | `lexicon_free`'nin kuyruktaki payı |
|---|---:|---:|---:|
| Yüksek otomasyon | %9,8 | %10,0 | %85,9 |
| Yüksek kesinlik | %20,3 | %19,6 | %86,5 |

*Kaynak: `results/05_final_test/metrics.json`. `lexicon_free`'nin test
kümesindeki payı %86,1'dir.*

İki dilim neredeyse aynı oranda devredilmektedir ve `lexicon_free`'nin kuyruktaki
payı (%85,9), kümedeki payından (%86,1) farklı değildir. Bu bir *seçim* değil, bir
*orantıdır*. Mekanizma hataya duyarlıdır, dilime kör. Güven, hataları nerede
olurlarsa olsunlar bulmakta; ancak tanının işaret ettiği sözcüksel zayıflığı
özel olarak bulmamaktadır.

Aynı davranış geliştirme kümesinde de gözlenmiş ve teste yinelenmiştir; bu
nedenle tek bir denetim noktasının özelliği değil, bu görevde güven temelli
seçici tahminin genel bir özelliği olarak raporlanmaktadır.

İşletme açısından iki nitelendirme birlikte geçerlidir: inceleme kuyruğunun
%86'sı yine de sözlüksüz içeriktir, yani bir incelemeci zamanının çoğunu örtük
saldırıya ayırmaktadır; ancak bu, taban orandan kaynaklanmakta, mekanizmanın
seçiciliğinden değil.

## 4.10 Bulguların özeti

| # | Bulgu | Kanıt |
|---|---|---|
| 1 | Sözlük temelli süzgeç, saldırgan içeriğin %63,5'ini yapısal olarak kaçırır | §1.2, Gün 1 kaydı |
| 2 | Eğitilmiş dönüştürücü açığı **sabit eşikte** kapatmaz: geliştirmede +0,3301, testte +0,3970 | §4.2 |
| 2b | **Bu bir işaretleme başarısızlığıdır, sıralama başarısızlığı değildir.** Eşikten bağımsız ölçümde dilim içi ROC-AUC 0,9306'ya karşı **0,8962**; fark yalnızca **+0,0345 [+0,0103; +0,0585]** ve ön kayıtlı karara göre **sonuçsuz** banttadır. Puanlar küfürsüz dilimde sistematik olarak bastırılmıştır (altın `OFF` medyanı 0,5861'e karşı 0,9650; ≤0,5 payı %43,7'ye karşı %10,7). Eşik yerleşimi ile gerçek güvensizlik **ayrıştırılamamaktadır** | §4.2, §5.12, `results/09_deeper_analysis/stage_1/` |
| 3 | Açık iki yönlüdür: `lexicon_hit` yanlış pozitif oranı 4 kat yüksektir | §4.3 |
| 3b | **Tanı iki parçalıdır: model hem saldırgan sözcük dağarcığına hem de muhatap alınmaya tepki verir.** Sözlük dışı güçlü sapmalı 19 belirtecin 10'u işaret edici, 5'i ikinci şahıs zamiridir; 118 satırda +0,2066 [+0,1216; +0,2960], `NOT` yönlü denetimde sıfır. Siyasi terim varsayımı çözünürlüğe bağlıdır (`df ≥ 30`'da +0,1494); 47/118 açıklanmadan kalır. Birlikte görülme, işaretin **mevcut** olduğunu gösterir, **kullanıldığını** değil | §4.3, `results/08_lexical_analysis/` |
| 4 | Etiket gürültüsü baskın değildir (%10); açık örtük saldırı %35'tir; **en büyük tek kategori (%52,5) işaretleme sözleşmesine bağlıdır ve insan yargısı gerektirir** | §4.4 |
| 5 | Küfür taşıyan yanlış pozitiflerin %88,4'ü saldırgan eylem içermez | §4.4 |
| 6 | Dilim kirlenmesi farkı **küçültmektedir**; raporlanan değer muhafazakârdır | §4.5 |
| 7 | **Müdahale birincil ölçütte gerçek ve yinelenen bir kazanç sağlar (+0,0336 / +0,0358)** | §4.1, §4.6, §4.7 |
| 8 | Sistem düzeyinde net etki yoktur (makro-F1 −0,0002) ve maliyetler raporlanır | §4.7 |
| 9 | Temel modelin kalibrasyona ihtiyacı yoktur; savunma çeşitlemesi kalibrasyonsuzdur | §4.8 |
| 10 | İnceleme katmanı hataları 3,59 kat yoğunlaştırır; ancak dilim körüdür | §4.9 |
