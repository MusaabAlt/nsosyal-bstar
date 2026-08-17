# 5. Sınırlılıklar

> **Taslak durumu.** KYS rapor şablonu yayımlanmadan önce yazılmıştır; başlık
> numaralandırması geçicidir.

Bu bölüm, çalışmanın ölçemediği ya da ölçüp de gideremediği şeyleri sıralar.
Sıralamanın biçimi bilinçlidir: her sınırlılık, mümkün olduğunda **bir sayıyla**
verilmiştir. Ölçülmemiş bir sınırlılık, bir özür; ölçülmüş bir sınırlılık ise
bir sonuçtur.

Birkaçının etkisi ölçüldüğünde, korkulanın **tersi** yönde çıkmıştır; bunlar da
aynı yerde raporlanmaktadır.

## 5.1 Etiketleme sözleşmesine bağımlılık

Türkçe saldırgan dil verisinde "saldırgan" tanımı, dilbilimsel bir olgu değil bir
sözleşmedir. Bu çalışma **Çöltekin'in sözleşmesini olduğu gibi benimsemiş ve
hiçbir satırı yeniden etiketlememiştir.**

Bunun büyüklüğü ölçülmüştür: sözlüksüz yanlış negatiflerden alınan yansız 40
satırlık örneklemin **21'i (%52,5)** saldırganlığı sözleşmeye bağlı satırlardır ve
bunların yaklaşık **13'ü** siyasetçilere veya kurumlara yöneltilmiş sert
eleştiridir (§4.4). Farklı bir sözleşme benimsenseydi bu satırların altın etiketi
değişebilir; bununla birlikte hem temel modelin `lexicon_free` duyarlılığı hem de
raporlanan duyarlılık farkı kayardı.

Bu satırlar raporlanan **her** sayının içinde sayılmaya devam etmektedir; ayıklanmış
bir "temiz" alt küme üretilmemiştir. Gerekçe, ayıklamanın kendisinin bir sözleşme
kararı olması ve bu kararı vermenin bu çalışmanın yetkisinde olmamasıdır.

## 5.2 Etiket gürültüsü

Sözlüksüz dilimde etiket gürültüsü oranı **%10** olarak ölçülmüştür (yansız 40
satırlık örneklemde 4 satır). Bu, raporlanan duyarlılık açığının bir bölümünün
modelin kaçırmasından değil, etiketin kendisinden kaynaklandığı anlamına gelir;
dolayısıyla **açık bir üst sınırdır.**

Bu sayının kendisi bir düzeltmedir. İlk okumada, en güvenle yanlış olan 60 satır
üzerinden %23,3'lük bir oran elde edilmişti. Ancak güvene göre sıralama, etiket
gürültüsünü **seçen** bir örneklemdir: model en yüksek güvenle yanlış olduğu
yerlerde çoğunlukla etiketin kendisi tartışmalıdır. Yanlı örneklemden elde edilen
oran dilime genellenemez. Savunulabilir olan %10'dur ve raporlanan budur.

Örneklem büyüklüğü 40'tır; %10'luk oranın kendisi de dar bir örnekleme dayanır ve
buna göre okunmalıdır.

## 5.3 Dilim tanımında iki bağımsız kirlenme — ikisi de ters yönde

Dondurulmuş dilim tanımında, birbirinden bağımsız **iki** kirlenme saptanmıştır.
İkisi de zıt yönlerde işlemekte, ancak **ikisi de raporlanan farkı olduğundan
küçük göstermektedir.** Hiçbiri sonuçlar görüldükten sonra düzeltilmemiştir;
sözlük ve eşleştirici dondurulmuş kalmaktadır.

### Birinci kirlenme: `lexicon_hit` dilimine giren yanlış eşleşmeler

Kök eşleşmesi, `lexicon_hit` diliminin **614 satırından 248'ini (%40)** yanlış
nedenle içine almaktadır (`eminim`, `malatya`, `götürür` gibi). Bu, Gün 1'de
dondurulmuş davranıştır.

Etkisi ölçülmüştür: şüpheli satırlar dışarıda bırakıldığında duyarlılık farkı
+0,3301'den **+0,3662'ye yükselmektedir** (kayma +0,0361; her iki aralık da sıfırı
dışlar). Hariç tutulan satırların %71'i `NOT` olduğundan `lexicon_hit` dilimini
seyreltmekte, yani onu `lexicon_free` dilimine yaklaştırmaktadırlar. Bu, bir
eleştirmenin bekleyeceğinin **tersi** yöndedir.

### İkinci kirlenme: `lexicon_free` dilimine sızan açık küfür

`MIN_ROOT_LEN = 3` kuralı gereği, kök eşleştiricisi **üç karakterden kısa** sözlük
girdilerini hiçbir zaman yakalayamaz. Dondurulmuş listede böyle beş girdi
bulunmaktadır: `ag`, `am`, `aq`, `oc`, `oç`. Bunları taşıyan satırlar, açık küfür
içermelerine rağmen `lexicon_free` diliminde yer almaktadır.

Geliştirme kümesinde, **altın `OFF` etiketli 565 `lexicon_free` satırından 28'i
(%4,96)** bu girdilerden birini taşımaktadır. Tek başına `aq` belirtecinin eğitim
kümesindeki koşullu olasılığı **P(OFF | `aq`) = 0,9860**'tır — yani bu satırlar
model açısından kolay satırlardır ve dilimin duyarlılığını yukarı çekmektedirler.

Etkisinin büyüklüğü **bir üst sınır olarak** verilebilir. Raporlanan
`lexicon_free` `OFF` duyarlılığı 0,5628 = 318/565'tir. Sızan 28 satırın
**tamamının doğru sınıflandırıldığı** varsayılırsa — etkiyi en büyük yapan, yani
üst sınırı veren varsayım — geri kalan satırlardaki duyarlılık 290/537 =
**0,5400**'e, fark ise +0,3301'den **+0,3529**'a çıkmaktadır.

**Bu bir üst sınırdır, bir ölçüm değildir.** Söz konusu 28 satırın tek tek doğru
sınıflandırılıp sınıflandırılmadığını saptamak `dev_predictions.csv` dosyasını
gerektirir; bu dosya derlem metni taşıdığı için depoya konmamakta ve yalnızca
Drive yansısında bulunmaktadır. Ölçüme dönüştürülmesi mümkündür, bu raporda
yapılmamıştır.

### İkisinin ortak yönü

Birinci kirlenme `lexicon_hit` dilimini kolay olmayan satırlarla seyreltmekte,
ikincisi `lexicon_free` dilimine kolay satırlar sokmaktadır. Mekanizmaları
birbirinden bağımsızdır, ancak **her ikisi de iki dilimi birbirine
yaklaştırmakta**, dolayısıyla ölçülen farkı küçültmektedir. Her iki düzeltme
altında da raporlanan **+0,3301 muhafazakâr taraftadır.**

Raporlanan başlık sayı yine de dondurulmuş Gün 1 tanımına göre verilmekte;
duyarlılık değerleri onun yerine geçirilmemektedir. Sözlük ve `MIN_ROOT_LEN`
değiştirilmemiştir — sonuç görüldükten sonra eşleştiriciyi düzeltmek, ölçtüğümüz
niceliği ölçüm sırasında değiştirmek olurdu.

## 5.4 Müdahalenin nedensel yorumu — en önemli sınırlılık

§4.6 ve §4.7'de raporlanan `lexicon_free` kazancı gerçektir ve yinelenmiştir.
**Ancak bu kazancın modele edimbilimsel bir ayrım kazandırdığı gösterilmemiştir.**

1b bileşeni, küfrün saldırgan olmayan kullanımlarını şablonlarla üretmektedir.
Geliştirme kümesi bu şablonların yaklaşık 20 metin parçasının hiçbirini
içermemektedir; bu, **birebir ezberi dışlar — ve yalnızca onu.** Daha sığ bir
dağılımsal ipucu şunlar gibi:

* "virgülden sonra yan tümcede geçen küfür",
* "ikinci tekil şahıs zamirine komşu olmayan küfür",
* "cansız özneli bir tümcede geçen küfür",

geliştirme kümesine de test kümesine de aktarılır ve sayıları yükseltir; model
kullanım–anma ayrımına benzer hiçbir şey öğrenmemiş olsa bile.

Bu iki olasılık mevcut ölçümle **birbirinden ayrılamaz**, çünkü üretilen veri her
iki sinyali aynı anda taşımaktadır ve birini sabit tutup diğerini değiştiren bir
denetim kümesi yoktur. Böyle bir küme kurmak, şablonlardan farklı sözdizimsel
düzenlerde doğal küfür kullanımları toplamayı gerektirir; bu bir derlem toplama
işidir ve bu çalışmanın süresi dışındadır.

**Bu sınırlılık belirtilmiştir, giderilmemiştir.** Rapor, kazancı ölçülmüş bir
iyileşme olarak sunar; kazancın mekanizmasına ilişkin bir iddiada bulunmaz.

## 5.5 Dayanıklılık sınamasının zayıflığı

Gizlemeye dayanıklılık, eğitimde kullanılmayan H ailesiyle ölçülmüştür (§2.4.2).
Ölçüm, kurgu bakımından temizdir; ancak **sınamanın kendisi zayıftır.**

H bozması, temel modelin makro-F1'ini yalnızca **0,0149** düşürmektedir
(0,8271 → 0,8122). Bu küçük görünen sayının iki nedeni vardır ve ikisi de
belirtilmelidir.

**Birincisi yapısaldır ve daha önemlidir: bozma işleçleri yalnızca sözlükte
eşleşen belirteçleri değiştirir.** Dolayısıyla geliştirme kümesinin 4.764
satırından yalnızca **614'ü (%12,9)** — yani tam olarak `lexicon_hit` dilimi —
gerçekten bozulmaktadır; kalan %87,1 hiç değişmeden kalır. Küme genelindeki
0,0149'luk düşüş, bu nedenle **etkinin kendisini değil, seyreltilmiş bir
ortalamasını** göstermektedir.

Bozulan satırlar içindeki etki belirgin biçimde daha büyüktür: yanlış negatif
sayısı 285'ten 316'ya çıkmaktadır (+31) ve bu artışın tamamı, `lexicon_hit`
dilimindeki 355 altın `OFF` satırından gelmektedir — yani bozulan satırlar içinde
`OFF`-duyarlılık yaklaşık **8,7 puan** düşmektedir. Bir dayanıklılık sayısı
raporlanırken hangi paydanın kullanıldığı bu nedenle açıkça belirtilmelidir.

**İkincisi işleçlerin kendisiyle ilgilidir:** H ailesindeki aksan kaldırma
(`şerefsiz` → `serefsiz`), Türkçe günlük yazışmada zaten yaygındır; model bu
biçimi eğitim verisinde de görmüş olabilir. Bu, sınamanın zorluğunu ayrıca
azaltmaktadır.

Buna bağlı olarak D ailesinden H ailesine aktarım da küçüktür: **+0,0141.**
Sayı olumludur ve raporlanmaktadır, ancak üzerine büyük bir iddia
kurulmamalıdır. Daha güçlü bir dayanıklılık iddiası, Türkçe için hem daha zorlu
hem de gerçek kullanıcı davranışını temsil eden bir gizleme kümesi gerektirir.

## 5.6 Tek yapılandırma, tek tohum

Bütün eğitim çalıştırmaları **tek bir hiperparametre yapılandırmasıyla ve tek bir
tohumla (42)** yürütülmüştür. Bunun karşılaştırma açısından gerekçesi §2.1'de
verilmiştir; sınırlılık tarafı şudur:

**Raporlanan güven aralıkları, değerlendirme kümesinin örnekleme değişkenliğini
kapsar; eğitimin rastgeleliğini kapsamaz.** Aynı yapılandırma farklı tohumlarla
yeniden eğitilseydi, elde edilen farkların ne kadar oynayacağı ölçülmemiştir.
Bu, +0,0336 ve +0,0358'lik kazançların yorumunu doğrudan ilgilendirir: iki
bağımsız değerlendirme kümesinde yinelenmiş olmaları güven vericidir, ancak
tohumlar arası kararlılık ayrı bir soru olarak açık kalmaktadır.

Bunu kapatmanın yolu, her kolu birkaç tohumla yeniden eğitmek ve tohumlar arası
dağılımı raporlamaktır; hesaplama bütçesi bu çalışmada buna yetmemiştir.

## 5.7 Denetim noktası seçimi

Değerlendirilen model, üç devir arasından geliştirme makro-F1'ine göre
seçilmiştir. Temel modelde 1. ve 3. devirler bu ölçütte **birebir eşittir**, ancak
4.764 geliştirme satırının 198'inde farklı karar vermektedirler. Bu nedenle 285
yanlış negatifin **en fazla 43'ü** denetim noktasına özgüdür.

Hata çözümlemesinin bu oynaklığın üzerine kurulmadığı ayrıca denetlenmiştir:
etiketlenen ilk 60 yanlış negatifin **0'ı**, ilk 40 yanlış pozitifin **1'i**
denetim noktasına özgüdür.

## 5.8 Vekil ölçütün mutlak değeri

§4.3'te tanımlanan otomatik "şüpheli-kök dışı sözlük eşleşmesi bulunmayan yanlış
pozitif" ölçütü (temel modelde 185), elle sayılan 118 ile **aynı büyüklük
değildir.** Vekil, sözlükte bulunmayan ve gizlenmiş küfür biçimlerini kaçırır.

Bu ölçütün **yalnızca çalıştırmalar arasındaki farkları** anlamlıdır; mutlak
değeri "kaç yanlış pozitifte küfür yoktur" sorusunun yanıtı olarak
okunmamalıdır.

## 5.9 Genelleme sınırları

**Derlem-içi.** Bütün ölçümler tek bir derlem üzerindedir (Çöltekin
OffensEval-TR). Planlanan iki bağımsız Türkçe derlem (Mayda, Beyhan)
**edinilmemiştir** ve hiçbir ölçümde kullanılmamıştır. Dolayısıyla bu çalışma
**derlemler arası aktarım iddiası taşımaz.** Farklı bir kaynaktan gelen Türkçe
metinde açığın büyüklüğü ölçülmemiştir.

**Tek mimari.** Bulgular tek bir önceden eğitilmiş modelle (BERTurk) elde
edilmiştir. İkinci bir mimari (ConvBERTurk) çalıştırılmamıştır; bu nedenle
"sözcüksel kısayol bütün Türkçe dönüştürücülerde görülür" biçiminde bir
genelleme **desteklenmemektedir.** Gözlenen olgunun mimariye özgü mü yoksa genel
mi olduğu **açık bir sorudur.**

**Test kümesi harcanmıştır.** Resmî test kümesi tek kez kullanılmış ve
harcanmıştır (§2.6). Bu, dürüstlük açısından bir kazanç, esneklik açısından bir
kısıttır: bundan sonra üretilecek hiçbir sistem — yeni bir mimari dâhil — aynı
küme üzerinde bağımsız bir sayı alamaz. Sonraki her ölçüm geliştirme kümesiyle
sınırlıdır ve raporda öyle etiketlenmelidir.

## 5.10 İşletme katmanının sınırları

**Devretme dilim körüdür.** Güven temelli devretme hataları güçlü biçimde
yoğunlaştırmakta (3,59 kat), ancak tanının işaret ettiği sözlüksüz zayıflığı
özel olarak hedeflememektedir: iki dilim neredeyse aynı oranda devredilmektedir
(%9,8'e karşı %10,0) ve `lexicon_free`'nin kuyruktaki payı (%85,9), kümedeki
payından (%86,1) farksızdır. **Katman çalışmaktadır; ancak tanının tarif ettiği
mekanizma üzerinden çalışmamaktadır.**

**Tek kalibrasyon yöntemi.** Yalnızca sıcaklık ölçekleme uygulanmıştır ve bu
ön kayıtlıdır. İzotonik regresyon veya Platt ölçekleme, özellikle
kalibrasyonsuz olduğu ölçülen savunma çeşitlemesi için daha iyi sonuç verebilir;
denenmemiştir.

**Eşiğin genellemesi kusursuz değildir.** "En fazla %5 hata" kuralıyla seçilen
çalışma noktası, seçildiği yarıda hedefi tutturmakta, ayrılan yarıda %5,81'e,
resmî test kümesinde %5,43'e denk gelmektedir. Üretim ortamında bir eşik,
2.382 satırdan daha geniş bir veri üzerinde belirlenmelidir.

## 5.11 Öngörülüp bağlayıcı çıkmayan bir sınırlılık

Kalibrasyon ön kaydında, tahmin dosyalarının olasılıkları 6 ondalık basamağa
yuvarlanmış olarak sakladığı ve doymuş satırların (`0,000000` / `1,000000`) uç
bölgeyi sıkıştırarak sıcaklık uyarlamasını yanıltabileceği bir risk olarak
belirtilmişti.

Ölçümde bu risk **gerçekleşmemiştir**: her iki çeşitlemede de doymuş satır sayısı
**sıfırdır.** Sınırlılık gerçek bir risk olarak önceden yazılmış, ölçüldüğünde
bağlayıcı çıkmamıştır. Her iki yönüyle de burada belirtilmektedir.

## 5.12 Kapsam notu

Bu çalışma bir yarışma teslimidir, bir araştırma makalesi değildir. Yukarıdaki
sınırlılıkların birkaçı — özellikle §5.4'teki nedensel belirsizlik, §5.6'daki
tek tohum, §5.9'daki tek derlem ve §5.3'teki ikinci kirlenmenin üst sınırdan
ölçüme dönüştürülmesi — kapatılabilir sorulardır; kapatılmaları ek ölçüm ve ek
hesaplama süresi gerektirir.

Bu çalışmada tercih, **eldeki süreyi bir zayıflığı gizlemeye değil, kesin biçimde
ölçmeye ve yazmaya ayırmak** olmuştur. Raporlanan her sınırlılığın yanında ya bir
sayı ya da o sayının neden elde edilemediğinin açık bir gerekçesi bulunmaktadır.

## 5.13 Özet

| # | Sınırlılık | Ölçülen büyüklük | Durum |
|---|---|---|---|
| 1 | Etiketleme sözleşmesine bağımlılık | yansız örneklemin %52,5'i; ~13/40 siyasi eleştiri | belirtildi |
| 2 | Etiket gürültüsü | %10 (40 satırlık örneklem) | ölçüldü, açık bir üst sınırdır |
| 3a | Dilim kirlenmesi — `lexicon_hit` içine | 248/614; fark +0,0361 **artıyor** | ölçüldü, ters yönde |
| 3b | Dilim kirlenmesi — `lexicon_free` içine (`MIN_ROOT_LEN`) | 28/565; fark en çok +0,0228 **artıyor** | **üst sınır**, ölçüm değil |
| 4 | Kazancın mekanizması | ayrıştırılamıyor | **belirtildi, giderilmedi** |
| 5 | Dayanıklılık sınaması zayıf | H bozması yalnızca 0,0149 maliyet | ölçüldü |
| 6 | Tek tohum, tek yapılandırma | tohumlar arası oynaklık ölçülmedi | açık |
| 7 | Denetim noktası oynaklığı | 198/4.764 satır; ≤43/285 YN | ölçüldü, çözümleme etkilenmiyor |
| 8 | Vekil ölçütün mutlak değeri | 185 ≠ 118 | tanımlandı, yalnızca farkları kullanılıyor |
| 9 | Derlemler arası genelleme | ölçüm yok | kapsam dışı |
| 10 | İkinci mimari | ölçüm yok | açık soru |
| 11 | Test kümesi harcandı | tek ölçüm | tasarım gereği |
| 12 | Devretme dilim körü | %9,8'e karşı %10,0 | ölçüldü, sıfır sonucu |
| 13 | Tek kalibrasyon yöntemi | ölçüm yok | kapsam dışı |
| 14 | Eşiğin genellemesi | %5,00 → %5,81 → %5,43 | ölçüldü |
| 15 | 6 basamak yuvarlama | 0 doymuş satır | öngörüldü, bağlayıcı çıkmadı |
