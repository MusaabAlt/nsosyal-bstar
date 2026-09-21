# NSosyal

**Canlı demo: <https://nsosyal.daqqiq.com>**

Türkçe saldırgan içerik tespiti için uçtan uca bir sistem: araştırma çalışması, yedi
modüllü tespit hattı ve canlı bir moderasyon paneli. Yukarıdaki adres çalışan sistemin
kendisidir — kayıt yoktur, kimlik doğrulama yoktur, açılır açılmaz kullanılabilir.

> Canlı demo turnuva kullanımı için **bilerek** herkese açık bırakılmıştır. Yazma uçları
> (`POST /api/sessions`, `POST /api/comments`, `POST /api/panel/actions`) dahil her şey
> açıktır; paneldeki durum size özel değildir, aynı anda başka bir ziyaretçi de veri
> yazabilir. Ayrıntı: [`infra/README.md` §6](infra/README.md).

---

## İçindekiler

1. [Sistem ne yapar](#1-sistem-ne-yapar)
2. [Mimari](#2-mimari)
3. [Bir mesaj analiz edildiğinde ne oluyor](#3-bir-mesaj-analiz-edildiğinde-ne-oluyor)
4. [Yapay zekâ hattı (`AI/`)](#4-yapay-zekâ-hattı-ai)
5. [Bugün neyi tespit ediyor](#5-bugün-neyi-tespit-ediyor)
6. [Backend (`backend/`, Go)](#6-backend-backend-go)
7. [Panel (`frontend/`, Vue 3)](#7-panel-frontend-vue-3)
8. [Araştırma çalışması (`diagnosis/`)](#8-araştırma-çalışması-diagnosis)
9. [Kurulum](#9-kurulum)
10. [Çalıştırma](#10-çalıştırma)
11. [Demo modu](#11-demo-modu)
12. [Testler](#12-testler)
13. [Yapılandırma ve bilinen tuzaklar](#13-yapılandırma-ve-bilinen-tuzaklar)
14. [Dağıtım](#14-dağıtım)
15. [Bilinen sınırlar](#15-bilinen-sınırlar)
16. [Depo düzeni ve belge haritası](#16-depo-düzeni-ve-belge-haritası)

---

## 1. Sistem ne yapar

Türkçe saldırgan içeriğin büyük bölümü hiçbir küfür sözcüğü taşımaz. Projenin çıkış
noktası bu ölçümdür: [`diagnosis/`](diagnosis/) altındaki çalışma, ince ayarlı bir
BERTurk sınıflandırıcısının küfür sözcüğü içermeyen saldırgan içeriği **sıralayabildiğini
ama karar eşiğinin üstüne çıkaramadığını** gösterir. Karar eşiğinde sözlük eşleşmeli ve
sözlük içermeyen kesitler arasındaki geri çağırma farkı **+0,3301** (%95 GA
[+0,2771; +0,3827]), sıralamada ROC-AUC farkı ise yalnızca **+0,0345** (%95 GA
[+0,0103; +0,0585]).

[`AI/`](AI/) bu bulgunun üzerine kurulan tespit sistemidir. Tek bir büyük sınıflandırıcı
yerine **yedi bağımsız modül** çalışır; saldırgan söylemin her kategorisinin kendi motoru,
kendi eşiği ve kendi eylemi vardır. Hattın tamamı **çevrimdışı, CPU üzerinde** koşar —
çıkarım sırasında hiçbir platform API'si veya ağ çağrısı yoktur.

[`backend/`](backend/) (Go) ve [`frontend/`](frontend/) (Vue 3) bunun üzerindeki canlı
moderasyon panelidir: mesaj gelir, analiz edilir, karar PostgreSQL'e yazılır, panel
kararları ve gerekçelerini gösterir.

### Sistemin uyduğu tek kural

**Ekrandaki her sayı gerçektir ve karar yalnızca yapay zekâya aittir.**

- `verdict`, `fired`, `active` ve `suppressed` alanlarını Python'daki karar katmanı
  belirler. Go bunları saklar, asla yeniden hesaplamaz.
- Arayüz hiçbir zaman bir skoru bir eşikle karşılaştırmaz, skorları toplamaz veya
  ortalamasını almaz (`frontend/src/design-rules.test.ts` bunu test olarak zorlar).
- Var olmayan bir değer `0` olarak değil, **"veri yok" / `—`** olarak gösterilir. Sıfır,
  "bakıldı ve bulunamadı" demektir; ölçülmemiş bir şey için kullanılamaz.
- Eksik çalışan bir sonuç asla temiz gösterilmez: nihai karar "Değerlendirme
  tamamlanmadı" der ve çalışmayan modülleri sayar.

---

## 2. Mimari

Üç süreç. Yerel demoda tek bir dizüstünde, canlı dağıtımda iki Docker Swarm yığınında
çalışır — kod aynıdır, değişen tek şey yapılandırmadır.

```
  tarayıcılar                                     sunucu / demo dizüstü
 ─────────────                    ┌────────────────────────────────────────────────┐
                                  │                                                │
  browser ── HTTPS/HTTP ────────► │  Go sunucusu (backend/)                        │
                                  │   • Vue panelini sunar (binary'ye gömülü)      │
                                  │   • /api/*  REST API                           │
                                  │   • kuyruk + mikro-toplama, önbellek, hız sınırı│
                                  │        │                       │               │
                                  │        │ HTTP :8001            │ SQL :5432     │
                                  │        ▼                       ▼               │
                                  │  Python çıkarımı          PostgreSQL           │
                                  │  (AI/serving, FastAPI)    yorumlar, kararlar,  │
                                  │  AI/pipeline'ı koşturur   moderatör eylemleri, │
                                  │                           istek metrikleri     │
                                  └────────────────────────────────────────────────┘
```

| Parça | Sorumluluğu |
|---|---|
| **Go sunucusu** (`backend/`) | Ağdan erişilebilen tek süreç. Paneli ve API'yi sunar, modeli aşırı yükten korur, her şeyi Postgres'e yazar. Yerel kurulumda Python servisini kendisi başlatır ve denetler. |
| **Python çıkarım servisi** (`AI/serving/`) | `AI/pipeline` üzerine ince bir HTTP sarmalayıcı. Yalnızca localhost'u dinler. Hiçbir karar vermez; hattın ürettiği `AnalysisResult`'ı olduğu gibi döner. |
| **PostgreSQL** | Analiz edilen her mesaj, yapay zekânın verdiği karar, her moderatör eylemi ve her isteğin süresi. |

Canlı dağıtımda Go, Python sürecini **başlatmaz**: `NSOSYAL_PYTHON_ENABLED=false` ile
yalnızca izleme kipinde çalışır ve `NSOSYAL_INFERENCE_URL` üzerinden ayrı bir konteynere
bağlanır. Bu sayede iki servis bağımsız bellek sınırlarıyla ve bağımsız hızda
güncellenebilir (42 MB'lık uygulama imajı ile 1,99 GB'lık çıkarım imajı).

---

## 3. Bir mesaj analiz edildiğinde ne oluyor

1. Tarayıcı `POST /api/comments {session_id, text}` gönderir.
2. Go hız sınırını, metni ve oturumu doğrular, ardından önbelleğe bakar
   (anahtar: **birebir metnin** sha256'sı + model sürümü — `s4l4k` ile `salak` asla aynı
   anahtara düşmez).
3. Önbellekte yoksa metin sınırlı bir kuyruğa girer. İşçiler bekleyen metinleri küçük
   gruplara toplar ve Python'a `POST /predict_batch` ile gönderir.
4. Python hattı çalıştırır ve `AnalysisResult` döner.
5. Go tarayıcıya sonucu, birkaç ekran sayısını (`internal/display`) ve süreleri **hemen**
   yanıtlar. Veritabanı yazımı arka planda yapılır; yavaş bir disk yanıtı geciktirmez.
6. Panel gösterge tabloları, kuyruk ve geçmiş için saklanan veriyi `/api/panel/*`
   üzerinden okur.

---

## 4. Yapay zekâ hattı (`AI/`)

### Modüller ve sıra

```
metin ─► m0_charsafe ─► m2_deobf ─► m6_target ─► m1_lexicon ─► m3_encoder ─► m4_implicit ─► m5_sarcasm
         (karakter      (paralel    (hedef,      (ham+normal   (A/B/C       (C eşikleri)    (D1, kendi
          güvenliği)     kanal)      yayımlanır)  kanal,        başlıkları)                   modeli)
                                                  koruyucular)
                                    ─► decision/: kanalları birleştir → eşikler → koruyucular → thread → karar
```

| Modül | Ne yapar | Durum |
|---|---|---|
| `m0_charsafe` | Karakter güvenliği; diğer her modülün okuduğu `charsafe_text`'i üretir. | Çalışıyor |
| `m2_deobf` | Gizleme çözme (leet, aksan, fonetik). Paralel bir "normalleştirilmiş kanal" üretir. Tier 2 (DEASCII) `zeyrek` ile doğrulanır. | Çalışıyor |
| `m6_target` | Hedef çözümlemesi (birey / grup / insan-dışı) ve B4 (doxing: telefon, TCKN, IBAN, plaka, adres, e-posta, profil bağlantısı). | Çalışıyor (v1) |
| `m1_lexicon` | Sözlük tabanlı tespit; her iki kanalda da çalışır. Koruyucuları üretir: `SUBSTRING_COLLISION`, `HOMONYM`, `NON_HUMAN_TARGET`. | Çalışıyor |
| `m3_encoder` | BERTurk kodlayıcı. Dondurulmuş epoch-1 ikili sınıflandırıcı `raw_score` / `norm_score` yayımlar. A/B/C başlıkları etiket ve GPU çalışması bekliyor. | Çalışıyor |
| `m4_implicit` | C1–C5'i m3'ün C başlığından okur (ADR-006). Başlık olmadığı için bugün hiçbir şey üretmez — tasarım gereği. | Çalışıyor |
| `m5_sarcasm` | D1 (aşağılayıcı alay), kendi modeliyle (ADR-003). |Çalışıyor v1 |

**Modüllerin uyduğu kurallar** ([`AI/modules/README.md`](AI/modules/README.md)): bir modül
başka bir modülü içe aktarmaz, orijinal metni değiştirmez, **asla bir eşik uygulamaz** ve
kendi başına çalıştırılabilir/ölçülebilir olmak zorundadır. Sıra yalnızca
`AI/modules/registry.py` içindeki `PIPELINE_ORDER` tarafından bilinir.

### Karar katmanı

Modüller yalnızca skor yayımlar (`code` / `score` / `source`). Skorları eşiklerle
karşılaştırıp bir eylem seçen tek yer [`AI/decision/`](AI/decision/) klasörüdür; tüm
sayılar tek bir dosyada, [`AI/decision/thresholds.yaml`](AI/decision/thresholds.yaml)
içinde durur.

Eylem sıralaması: `block > escalate > review > nudge > clean`.

- **`binary_offensive` eşiği `0,320188`** — türetilmiş tek sayıdır (`r = 3` maliyet oranı,
  dondurulmuş geliştirme bölmesinin CAL yarısı, `m3-berturk-pytorch-fp32-epoch1`).
  Dosyadaki diğer her sayı hâlâ **yer tutucudur**.
- **İnsan incelemesi bandı** (`review_band`, 0,30 – 0,70): genel saldırganlık kanalı
  yalnızca skor bu aralıktayken bir moderatör ister. Üstünde karar zaten kesindir
  (`block`), altında yazar uyarılır (`nudge`). Bant yalnızca *insan isteyen* bir eylemi
  değiştirir; `A4`, `B2`, `B4` ve `C3` bilerek "İNSANDA KALIR" olarak işaretlidir.
- **Koruyucular (guards)** yanlış pozitifleri temizler: örneğin `NON_HUMAN_TARGET`,
  "aptal film" cümlesindeki A1/A2/A3/B1 ateşlemelerini bastırır. Bir kodu hangi
  koruyucunun bastırdığı kayda geçer, panelde görünür.
- **Hata durumunda kapanır (fail closed):** bir modül çalışmazsa sonuç "degraded"
  işaretlenir ve `clean` kararına ulaşılamaz. `m5_sarcasm` taslak olduğu sürece her sonuç
  eksiktir, dolayısıyla zararsız bir cümle bile `review` ile biter. Bu bilinçli bir
  politikadır (Faz 9).

### Kod kitabı (16 kod, dondurulmuş)

[`AI/contracts/codes.py`](AI/contracts/codes.py) dondurulmuştur.

| Sınıf | Kodlar |
|---|---|
| **A — Küfür** | A1 Hedefsiz küfür · A2 Bireye yönelik küfür · A3 Gruba yönelik küfür · A4 Kutsal değerlere yönelik küfür |
| **B — Açık saldırganlık** | B1 Aşağılama · B2 Tehdit · B3 Lanetleme / dışlama · B4 Kişisel bilgi ifşası (doxing) · B5 Cinsel saldırganlık |
| **C — Örtük saldırganlık** | C1 Kalıp yargı · C2 Aşağılık atfetme · C3 Kodlu dil · C4 Kışkırtma · C5 Karalama / iftira |
| **D — Aşağılayıcı ironi** | D1 Aşağılayıcı alay |

A1/A2/A3 aynı skordur; karar katmanı m6'nın çözdüğü hedefe göre kodu yeniden atar
(ADR-005).

### Model dosyaları (artifact'ler) git'te değildir

Çalışma zamanında önemli olan iki dosya `diagnosis/` çalışmasından gelir:

- `m3-berturk-pytorch-fp32-epoch1` → `AI/artifacts/m3_encoder/berturk_epoch1.pt`
- `m3-berturk-tokenizer` → `AI/artifacts/m3_encoder/tokenizer/`

Hepsi sha256 özetleriyle [`AI/artifacts/MANIFEST.md`](AI/artifacts/MANIFEST.md) içinde
listelidir. **`m3_encoder` hattın tek eğitilmiş modelidir** — m1 bir sözcük listesi, m2
karakter tabloları, m6 sözlükçelerdir. Dosyalar yoksa hiçbir şey skorlanmaz.

Modüller kendi sha256'larını doğrular ve uyuşmazlıkta **gürültülü biçimde hata verir**;
yani yanlış ama makul görünen bir dosya yakalanır. **Eksik dosya ise hata değil, bir
körelmedir (degradation).**

---

## 5. Bugün neyi tespit ediyor

Tek kaynak: [`AI/serving/capabilities.py`](AI/serving/capabilities.py). Panel yalnızca bu
listeyi sayar.

| Kod | Anlamı | Üreten modül |
|---|---|---|
| `A1` | Hedefsiz küfür | `m1_lexicon` |
| `A2` | Bireye yönelik küfür | `m1_lexicon` (+ m6 hedefi) |
| `A3` | Gruba yönelik küfür | `m1_lexicon` (+ m6 hedefi) |
| `B1` | Aşağılama | `m1_lexicon` |
| `B2` | Tehdit | `m1_lexicon` |
| `B3` | Lanetleme / dışlama | `m1_lexicon` |
| `B4` | Doxing | `m6_target` |
| `binary_offensive` | "Genel saldırganlık" | `m3_encoder` (BERTurk) |

Üretilmeyenler: `A4`, `B5`, `C1–C5` (m3'ün C başlığını bekliyor), `D1` (m5 taslak).
Panelde bunlar `0` değil, **`—` "henüz üretilmiyor"** olarak görünür.

### Sistem sessizce körelir — bunu bilin

Hat, bir modül yüklenemediğinde çalışmaya devam edecek şekilde **bilerek** yazılmıştır.
Eksik veya uyumsuz bir model dosyası hiçbir şeyi çökertmez. Sonuç: sağlıklı bir konteyner,
`200` dönen bir `/health` ve **hiçbir şey tespit etmeyen bir dedektör**.

> **Gerçek sinyal `/health` gövdesindeki `degraded_modules` alanıdır. HTTP durum kodu
> değildir.**

`/health` gövdesini bir modül adı için baştan sona `grep`'lemeyin: `capabilities` dizisi
**her zaman** `m3_encoder` içerir, yani böyle bir kontrol m3 tamamen sağlıklıyken bile
eşleşir. Yalnızca `degraded_modules` ayrıştırılmalıdır. Bu hata bir kez
`infra/verify-deploy.sh` dosyasına girdi ve kontrolün asla geçememesine yol açtı.

Bugün `degraded_modules` içinde beklenen tek girdi: **`m5_sarcasm`** (uygulanmamış taslak,
arıza değil).

---

## 6. Backend (`backend/`, Go)

Tek çalıştırılabilir dosya: paneli ve REST API'yi tek porttan sunar, Python servisini
başlatıp denetler, her şeyi PostgreSQL'e yazar. Vue SPA `backend/web/dist` içine derlenip
`//go:embed all:dist` ile binary'ye gömülür — ayrı bir statik site yoktur ve frontend'in
API adresine ihtiyacı yoktur.

### Paketler

| Paket | Sorumluluk |
|---|---|
| `cmd/server` | Giriş noktası. Her şeyi bağlar; sırayla kapatır (HTTP → kuyruk → yazıcı → Python → havuz). |
| `cmd/migrate` | Şemayı elle uygula/geri al (`up`, `down`, `reset`, `status`). |
| `cmd/mockinfer` | Python servisinin yerine geçen sahte servis; örnek yükleri döner. |
| `cmd/seed` | Demo beslemesi üretir (aşağıya bkz.). |
| `internal/config` | Varsayılanlar → `config.yaml` → `.env` → ortam değişkenleri. |
| `internal/queue` | Sınırlı kuyruk + mikro-toplama işçileri. Kuyruk doluysa anında `503 queue_full`. |
| `internal/inference` | Python için HTTP istemcisi + devre kesici; son `/health` yanıtını önbellekler. |
| `internal/supervisor` | Python servisini proje venv'inden başlatır, sağlığını ölçer, geri çekilmeli yeniden başlatır, süreç ağacını öldürür. `:8001`'de zaten biri varsa sadece izler. |
| `internal/cache` | Sonuç LRU'su; anahtar sha256(birebir metin) + artifact özeti. |
| `internal/store` | Postgres havuzu, gömülü göçler, okuma sorguları, asenkron toplu yazıcı ve panel sorguları. |
| `internal/display` | Ekranda görünen ama sonucun taşımadığı birkaç sayı. Yalnızca sayar ve çıkarır. |
| `internal/categories` | Panel için kategori satırları; eşik ve eylem `AI/decision/thresholds.yaml`'dan (dosya değişince yeniden okunur). |
| `internal/metrics` | Bellekte son 5 dakikanın gecikme pencereleri (p50/p95/p99). |
| `internal/http/middleware` | Panik kurtarma, istek günlüğü, IP başına hız sınırı, istek süre sınırı, geliştirme CORS. |
| `internal/http/handlers` | Uç noktalar (`handlers.go`, `panel.go`). |
| `internal/http/respond` | Tek JSON hata biçimi. |

### Veritabanı

Göçler binary'ye gömülüdür ve açılışta çalışır (`database.migrate_on_start: true`).

| Tablo | Yazan | İçerik |
|---|---|---|
| `sessions` | `POST /api/sessions` | Anonim takma ad + IP. Parola yok, hesap yok. |
| `comments` | asenkron yazıcı | Metin, sha256, tam `AnalysisResult` (JSON), gecikme, önbellek bayrağı. |
| `analysis_results` | asenkron yazıcı | İçerik kodu başına bir satır: skor, eşik, `fired`, motor, kaynak. |
| `moderation_decisions` | asenkron yazıcı | Yapay zekânın kararı, ateşleyen kodlar, etkin koruyucular, eksiklik bayrağı, açıklama. |
| `moderator_actions` | `POST /api/panel/actions` | `approve`, `hide`, `remove`, `queue`, `false_positive`. |
| `request_metrics` | asenkron yazıcı | Her API isteğinin yolu, durumu ve gecikmesi. |

### API

Hatalar tek biçimdedir:
`{"error": {"code": "queue_full", "message": "...", "retry_after_ms": 2000}}`.

**Analiz ve durum**

| Uç nokta | Amaç |
|---|---|
| `POST /api/sessions` | Anonim oturum oluştur `{nickname}` (1–32 karakter). |
| `POST /api/comments` | Metni analiz et `{session_id, text}` (≤ 5000 karakter) → sonuç, normalleştirme, ekran sayıları, süreler, yorum kimliği. |
| `GET /api/comments` | Akış, en yeni önce, imleçli sayfalama. |
| `GET /api/moderation/flagged` | Temiz olmayan yorumlar ve türe göre gerekçeleri. |
| `GET /api/stats` | Veritabanı sayıları, gecikme, kuyruk, önbellek ve yazıcı istatistikleri. |
| `GET /api/health` | Go, Python ve Postgres durumu. Go ayaktayken **daima 200**. |
| `GET /api/categories` | Yapay zekânın bugün tespit ettiği kategoriler; eşik, eylem, modül, durum. |

**Panel API'si**

| Uç nokta | Amaç |
|---|---|
| `GET /api/panel/overview?range=live\|today\|week` | KPI'lar (önceki döneme göre değişimle), kategori zaman serileri, kaçırma kalıpları, kuyruk sayıları, sistem bilgileri. 1 sn önbellekli. |
| `GET /api/panel/items?status&detected&code&q&limit&cursor` | Analiz edilmiş mesajlar, sonuçları ve son moderatör eylemi. |
| `GET /api/panel/items/{id}` | Tek mesaj, moderatör geçmişi ve gönderenin önceki 3 mesajı. |
| `GET /api/panel/queue-counts` | Bekleyen, bekleyen-ve-tespitli, incelenen, otomatik. |
| `POST /api/panel/actions` | 1–100 yorum kimliği için eylem kaydet. Henüz yazılmamışsa `404` (panel tekrar dener). |
| `GET /api/panel/events?kind&q&limit&cursor` | Geçmiş: moderatör eylemleri ve sistem tespitleri. |
| `GET /api/panel/metrics` | 30 dakikalık dakika bazlı istek sayıları ve gecikme, istek/sn, hata oranı, etkin cihaz, yavaşlık bayrağı. |

### Panelin dayandığı tanımlar

Bunlar karardır, tahmin değil — [`docs/FULLSTACK.md` §3](docs/FULLSTACK.md) içinde tam
gerekçeleriyle yazılıdır.

- **Tespit edildi** = karar katmanı en az bir içerik kodunu *veya* ikili saldırganlık
  skorunu ateşledi. `verdict` kullanılmaz, çünkü m5 taslakken her sonuç eksiktir ve temiz
  bir cümle bile `review` ile biter.
- **Kuyruk durumu**: `reviewed` (son eylem approve/hide/remove), `pending` (son eylem
  queue/false_positive ya da eylem yok + karar review/escalate/eksik), `auto` (eylem yok +
  karar block/nudge).
- **Otomatik işlem** = `block` veya `nudge` kararı.
- **İnsan incelemesi** = `review` + `escalate`; payı **analiz edilen her şeyin** içindedir,
  tespitlerin değil. Altı karar kovası analiz edilen satırları tam olarak böler, bu yüzden
  pay %100'ü geçemez.
- **Değişim %** = pencerenin geçen kısmını, hemen öncesindeki eşit uzunlukta bir zaman
  dilimiyle karşılaştırır. Önceki dönem boşsa `null`.
- **Etkin cihaz** = son 5 dakikada yorum gönderen farklı IP sayısı (yalnızca okuyanlar
  sayılmaz).
- **Yavaş** = son 5 dakikada analiz p95'i 200 ms'nin üstünde.
- **Zaman pencereleri**: `live` = son 1 saat (5 dk kovalar), `today` = yerel gece
  yarısından beri (1 saat), `week` = son 7 gün (1 gün).

### Dayanıklılık

- Kuyruk dolu → anında `503 queue_full`, asla askıda kalmaz.
- Model yükleniyor → `503 model_loading`; tekrarlanan hatalarda devre kesici açılır.
- Python ölür veya kilitlenir → denetleyici geri çekilmeli yeniden başlatır.
- Postgres yavaş veya kapalı → yanıtlar yine gider; yazımlar tekrar denenir, sonra düşer
  ve sayılır.
- Panik → yalnızca o istek için `500`.
- IP başına hız sınırı, istek süre sınırı, kuyruğu boşaltıp yazımları flush eden sıralı
  kapanış.

---

## 7. Panel (`frontend/`, Vue 3)

**ATI-SOSYAL Moderasyon Paneli.** Vue 3 + Vue Router + Vuetify + Tailwind, TypeScript.
Ekrandaki her değer Go API'sinden gelir; frontend'in kendi örnek verisi yoktur.

Tamamen çevrimdışı çalışır: Inter fontu paketlenmiştir, ikonlar satır içi SVG'dir ve
`npm run check:offline` herhangi bir dış URL'de derlemeyi başarısız kılar.

### Sayfalar

| Yol | Sayfa | Gösterdiği |
|---|---|---|
| `/` | **Genel Bakış** | Başlık kartı (toplam analiz, tespit + pay, otomatik işlem, genel saldırganlık sinyali, moderatör eylemi), öne çıkan **İnsan incelemesi** kartı, her moderasyon sınıfı (A/B/C/D) için bir kart, kategori dağılımı, moderasyon durumu ve her satırı **Neden?** açan son etkinlik tablosu. Sekmeler: Canlı, Bugün, 7 Gün. |
| `/analiz` | **Canlı Analiz** | Hazır cümlelerle besteci → normalleştirme şeridi, kategori başına sonuç kartı (skor, eşik işareti, ateşledi mi, eylem, modül süresi), kanıt panelleri (Gizleme tespiti, Hedef, Koruyucu kontroller), vurgulu açıklama, nihai karar + "Yanlış pozitif bildir" / "Kuyruğa ekle". |
| `/kuyruk` | **Moderasyon Kuyruğu** | Bekleyen / İncelenen / Otomatik işlenen sekmeleri, filtreler, toplu eylemler, detay paneli (skor tablosu, sistem kararı, önceki mesajlar, geçmiş). Kısayollar: A / H / R. |
| `/motorlar` | **Tespit Motorları** | Kategori başına bir kart: modül, durum, eşik, varsayılan eylem, eşik türetilmiş mi yer tutucu mu, bugünkü sayı ve eğilim. |
| `/kurallar` | **Kurallar & Eşikler** | Her kategorinin eşiği ve eylemi, kaynak dosyasıyla — salt okunur. |
| `/gecmis` | **Olay Geçmişi** | Moderatör eylemleri ve sistem tespitleri, güne göre gruplu; Tümü / Moderatör / Sistem sekmeleri; CSV dışa aktarım. |
| `/saglik` | **Sistem Sağlığı** | Cihazlar, istek/sn, p95 gecikme, hata oranı; gecikme ve istek grafikleri; Go / Postgres / model / kuyruk durumu. |

**Neden?** penceresi kararın kanıtıdır: mesaj, karar ve Türkçe açıklaması, hat modülü
başına ne katkı verdiği ve ne kadar sürdüğü, skorlanan her kategori eşiğiyle ve sonucuyla
(ateşledi / eşiğin altında / koruyucu bastırdı) ve koruyucuların temizlediği kodlar.
Yalnızca saklanan sonucu okur; hiçbir şey türetmez.

Her zaman görünür: kenar çubuğu (bekleyen rozetiyle), üst arama, geniş ekranlarda
**Sistem durumu** rayı, **Canlı Akış** dock'u, koyu/açık tema anahtarı ve model servisi
temsilî veri bildirdiğinde **Temsili veri** işareti. Sayfalar 3–10 saniyede bir yoklama
yapar ve sekme gizliyken durur.

**Telefonda:** her sayfanın 900 px ve 600 px altında ayrı düzeni vardır. Küçük ekranda
hiçbir şey gizlenmez; aynı sayılar tek sütunda görünür. Kenar çubuğu çekmeceye,
tablolar satır başına bir karta dönüşür, **Neden?** alt sayfa olarak açılır.

**Bilerek yapılmayanlar** (arkasında gerçek veri olmadığı için): Gizlenmiş Küfür Sözlüğü,
Değerlendirme, Ayarlar, motor başına F1/precision/recall, yeniden başlatma düğmeleri,
kullanıcı hesapları.

---

## 8. Araştırma çalışması (`diagnosis/`)

Projenin merkezî bulgusunu üreten ölçüm çalışması. Ön kayıt protokolleri, eğitim fazları,
sonuçlar, rapor ve çevrimdışı demo bu klasördedir.

Yöntem disiplini: `phases/` altında **9** sürüm denetimli protokol (7'si sayı üreten fazın
karar kurallarını o fazın ilk sayısı var olmadan önce sabitler), `docs/RESULTS_LOG.md`
içinde **49** tarihli satırlık yalnızca-ekleme günlüğü, tek kullanımlık ve **harcanmış**
resmî test kümesi (kod düzeyinde kilitli), ve raporlanan her farkta %95 önyükleme güven
aralığı.

Sayılar burada tekrarlanmaz:

- Özet → [`diagnosis/README.md`](diagnosis/README.md)
- Ölçümlerin kendisi → [`diagnosis/results/`](diagnosis/results/)
- Tarihli kayıt → [`diagnosis/docs/RESULTS_LOG.md`](diagnosis/docs/RESULTS_LOG.md)
- Eşik politikası ön kaydı → [`diagnosis/phases/12_threshold_policy.md`](diagnosis/phases/12_threshold_policy.md)

Ham derlem ve satır düzeyi tahmin dökümleri lisans ve boyut nedeniyle **dağıtılmaz**;
`src/obfuscation.py` bu kamuya açık kopyadan çıkarılmıştır. `diagnosis/` dağıtıma da
girmez — `.dockerignore` ile her iki imaj bağlamından dışlanmıştır.

---

## 9. Kurulum

Python 3.11+, Go 1.27+, Node.js. Paket yöneticisi **npm**'dir (`package-lock.json`).

### `AI/` ve `diagnosis/` ayrı ortamlar ister

Farklı bağımlılıklar kullanırlar; temiz bir klonda **ikisi de** ayrı ayrı kurulmalıdır.
Birinin ortamı diğerinin testlerini çalıştırmaz.

```bash
# AI/ çekirdeği: yalnızca pyyaml
cd AI
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
.venv/Scripts/python.exe -m unittest discover -p "test_*.py"
```

```bash
# diagnosis/: torch + transformers, çok daha büyük
cd diagnosis
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest tests/ -q
```

### Çalışma zamanı Python ortamı — **beş** dosya gerekir

Her modül kendi `requirements.txt` dosyasını taşır. Çalışan bir çıkarım servisi için:

```
AI/requirements.txt
AI/serving/requirements.txt
AI/modules/m1_lexicon/requirements.txt     # terlik
AI/modules/m2_deobf/requirements.txt       # zeyrek
AI/modules/m3_encoder/requirements.txt     # torch, transformers
```

> m1 (terlik) veya m2 (zeyrek) atlanırsa o modüller **sessizce körelir**.
> `AI/training/*` çalışma zamanı değildir.

> **CPU torch'u `--index-url https://download.pytorch.org/whl/cpu` ile kurun**,
> `--extra-index-url` ile değil — aksi hâlde pip, PyPI'dan birkaç GB'lık CUDA
> tekerleğini çözer.

### Tam yerel kurulum (demo dizüstü, Windows / Git Bash)

```bash
# Depo kökünde AI servisi için venv
python -m venv .venv
cd AI && ../.venv/Scripts/python.exe -m pip install -r requirements.txt -r serving/requirements.txt \
  -r modules/m1_lexicon/requirements.txt -r modules/m2_deobf/requirements.txt \
  -r modules/m3_encoder/requirements.txt && cd ..

# PostgreSQL: yerel kurulum ya da backend/ içinde `make db-up` (Docker, port 5433)
cp backend/.env.example backend/.env      # içine gerçek veritabanı adresini yazın

cd frontend && npm install && cd ..
```

Model dosyalarını (`berturk_epoch1.pt` + `tokenizer/`) `AI/artifacts/m3_encoder/` altına
koyun. Yoksa sistem çalışır ama **hiçbir şey skorlanmaz**.

---

## 10. Çalıştırma

### Tek komutla (demo)

```bash
cd backend
make build                 # paneli web/dist içine derler, sonra bin/nsosyal-server.exe
bin/nsosyal-server.exe     # göçleri uygular, Python'u başlatır, http://<ip>:8080 sunar
```

Günlük açılacak LAN adreslerini yazar, örn. `open="http://192.168.1.118:8080"`.

### Geliştirirken

```bash
cd backend && make run     # go run ./cmd/server
cd frontend && npm run dev # http://127.0.0.1:5173, /api'yi Go sunucusuna proxy'ler
```

### Yalnızca yapay zekâ hattı

```bash
cd AI
python -m pipeline.run "Bu bir test cümlesi"      # tam sözleşme JSON'unu basar
python -m eval.run_all                            # her modül kendi dev fixture'ında
python -m modules.m0_charsafe.eval                # tek modül değerlendirmesi
```

### Çıkarım servisini elle çalıştırma

```bash
cd AI
../.venv/Scripts/python.exe -m uvicorn serving.app:create_app --factory --host 127.0.0.1 --port 8001
```

`GET /health` ve `POST /predict_batch` sunar. Hattı arka plan iş parçacığında yükler
(BERTurk zaman alır); o ana kadar `/health` `loading` der ve `/predict_batch` `503` döner.
Modüller iş parçacığı güvenli belgelenmediği için aynı anda tek analiz çalışır. Tek bir
metnin hata vermesi toplu isteği düşürmez.

### Yararlı `make` hedefleri (`backend/`)

| Komut | Ne yapar |
|---|---|
| `make build` | Paneli derler, sonra tek dosyalık sunucu binary'si üretir. |
| `make frontend` | Yalnızca paneli `web/dist` içine derler (dış URL kontrolüyle). |
| `make mock` | Gerçek model yerine `cmd/mockinfer`'i `:8001`'de çalıştırır. |
| `make ai` | Gerçek Python servisini elle çalıştırır. |
| `make ai-setup` | Çalışma zamanı Python ortamını kurar. |
| `make migrate-up / -down / -reset / -status` | Şemayı elle yönetir. |
| `make db-up` / `db-down` | Docker'da Postgres (port 5433). |
| `make run-loadtest` → `make loadtest` | Hız sınırları yükseltilmiş sunucu, sonra k6 (150 kullanıcı). |

---

## 11. Demo modu

Sunum için panelin arkasında bir besleme gerekir. Modele hiç dokunmadan iki komut:

```bash
cd backend
make demo-mock             # :8001'de sahte çıkarım, her kategori canlı bildirilir
make demo-seed             # YIKICI: veritabanını demo beslemesiyle değiştirir
make run
```

- `cmd/seed`, uydurma bir besleme yazar: uydurma takma adlar, uydurma gönderiler, günlük
  trafik eğrisini izleyen 14 gün boyunca ~40.000 yorum. Hiçbir gerçek NSosyal kullanıcısı
  veya mesajı bu yoldan geçmez. Satırlar çalışan sistemin yazdığıyla **aynı biçimdedir**,
  dolayısıyla panelin sayıları yine saklanan veriden aynı sorgularla sayılır — ekranda
  hiçbir şey yer tutucu değildir. Bayraklar: `-days`, `-comments`, `-seed`,
  `-degraded-pct`, `-artifact`.
- `-reset` ilgili tabloları boşaltır. Bu bayrak olmadan komut, içinde yorum bulunan bir
  veritabanında çalışmayı **reddeder**.
- `mockinfer -demo`, `thresholds.yaml`'daki her kategoriyi canlı bildirir, böylece panel
  her moderasyon sınıfı için bir kart gösterir.
- İki haftalık veri bilerek varsayılandır: "7 Gün" aralığı kendini önceki haftayla
  karşılaştırır ve arkasında hiçbir şey olmayan bir pencere absürt bir değişim yüzdesi
  gösterir.

---

## 12. Testler

```bash
cd backend && go test ./...                          # birim testleri (Postgres testleri atlanır)
cd backend && make test-integration                  # + Postgres testleri (nsosyal_test)
cd frontend && npm test && npm run typecheck
cd AI && ../.venv/Scripts/python.exe -m unittest serving.test_app
cd AI && python -m unittest discover -p "test_*.py"
cd AI && BASE_REF=<commit> bash scripts/check.sh     # birleştirme öncesi tam kontrol
cd backend && make run-loadtest                      # sonra ayrı terminalde: make loadtest
```

`frontend/src/design-rules.test.ts` tasarım kurallarını zorlar: bileşenlerde hex renk yok
(yalnızca token'lar), arayüzde emoji yok, uzak URL yok, ve arayüz asla bir skoru bir
eşikle karşılaştırmaz / `fired`·`active`·`suppressed`·`verdict` atamaz / skorları toplayıp
ortalamaz.

---

## 13. Yapılandırma ve bilinen tuzaklar

Ortam değişkeni adları `backend/config.yaml` içindeki YAML yolundan `NSOSYAL_` önekiyle
türetilir (`backend/internal/config/config.go:9`). Örnek: `queue.batch_max_wait` →
`NSOSYAL_QUEUE_BATCH_MAX_WAIT`. Öncelik: **ortam > `.env` > yaml > varsayılanlar**.

Ana gruplar: `server`, `queue`, `inference`, `python`, `rate_limit`, `cache`, `database`,
`writer`, `decision.thresholds_file`, `log`.

### Tuzak 1 — çıkarım adresi `inference:` altındadır, `python:` altında değil

```yaml
inference:
  url: "http://127.0.0.1:8001"   # -> NSOSYAL_INFERENCE_URL
python:
  # YEREL denetleyici için command/args/workdir; burada `url` anahtarı YOKTUR
```

**`NSOSYAL_PYTHON_URL` hiçbir anahtarla eşleşmez ve sessizce yok sayılır.** Bu durumda
uygulama varsayılan `127.0.0.1:8001` adresini, yani kendi kendisini çağırır; her analiz
isteği başarısız olurken `/api/health` yeşil kalır. Bu hata bir kez yapılmıştır.

### Tuzak 2 — `NSOSYAL_PYTHON_ENABLED=false` izleme kipidir

Go denetleyicisi yerel bir Python süreci başlatmaz, yalnızca yapılandırılmış çıkarım
adresini yoklar (`backend/internal/supervisor/python.go`). Uygulamanın ve çıkarım
servisinin **kod değişikliği olmadan** ayrı konteynerlerde çalışabilmesini sağlayan şey
budur.

### Tuzak 3 — bu dizüstünde 8080 portu Apache'de

`backend/.env` içine `NSOSYAL_SERVER_ADDR=0.0.0.0:8090`, `frontend/.env.local` içine
`API_PROXY_TARGET=http://127.0.0.1:8090` yazın. Her demodan önce portu kontrol edin.

### Tuzak 4 — yorumlayıcı seçimi m2'yi sessizce kısar

m2'nin tier 2'si (DEASCII) `zeyrek` ister ve bu yalnızca `AI/.venv` içindedir. Depo
kökündeki `.venv` altında servis yine çalışır, `tier2_enabled` `false` olur ve panel sekiz
yerine altı kalıp saydığını doğru biçimde bildirir.

---

## 14. Dağıtım

Canlı adres: **<https://nsosyal.daqqiq.com>**. Tam runbook:
**[`infra/README.md`](infra/README.md)** — herhangi bir operasyonel değişiklikten önce
okuyun.

### Yapı

`tevekkul` VPS üzerinde iki Docker Swarm yığını:

| Servis | Yığın | Boyut | Bellek sınırı / rezervasyonu |
|---|---|---|---|
| `nsosyal_app` | `nsosyal` ([`infra/docker-stack.yml`](infra/docker-stack.yml)) | 42,2 MB | 256M / 64M |
| `nsosyal_infer` | `nsosyal` | 1,99 GB | 2048M / 1024M |
| `nsosyal-data_postgres` | `nsosyal-data` ([`infra/data-stack.yml`](infra/data-stack.yml)) | — | 384M / 128M |

Traefik TLS'i sonlandırır, Cloudflare önde proxy yapar, ana makine güvenlik duvarı 443'te
yalnızca Cloudflare IP aralıklarını kabul eder.

### Ana makine hakkında bilinmesi gereken iki şey

1. **Aynı makinede müşteriye dönük bir mağaza (`sahhil-alsayed`) ve `workbench` çalışıyor.**
   Asla `docker stack rm` yapmayın, asla prune etmeyin, sizin dağıtmadığınız bir servisi
   asla yeniden başlatmayın. `infra/verify-deploy.sh` tam da bu yüzden mağazanın zarar
   görmediğini kontrol eder — **her değişiklikten sonra çalıştırın**.
2. **Makine bellek kısıtlıdır** (toplam 3819 MB, üç yönlü paylaşılıyor). `docker build`
   komutuna **her zaman** bellek sınırı verin. Uygulama imajı `--memory=2g` ister, çünkü
   `vue-tsc` varsayılan yığını ~510 MB'da tüketip `exit 134` ile düşer; torch imajı
   `--memory=1g` ile sorunsuzdur. Sezgiye aykırı ama ölçülmüştür.

### CI/CD yoktur

İmajlar ana makinede, `HEAD`'in temiz bir arşivinden derlenir; güncellemeler elle yapılır.
Kullanılan `gh` belirteci `workflow` kapsamına sahip olmadığı ve kullanıcı depo yöneticisi
olmadığı için GitHub Actions bu dağıtım için erişilebilir değildir.

### Dağıtım kapısı

```bash
ssh root@<host> /srv/verify-deploy.sh   # depo kopyası: infra/verify-deploy.sh
```

Kontrol ettikleri: üç servisin de tam replika sayısında olması, `nsosyal_infer`'in
`/health` çıktısının `status: ok` **ve** `m3_encoder`'ın `degraded_modules` içinde
**olmaması**, genel adresin HTTPS üzerinden `200` dönmesi, `sahhil-alsayed` / `workbench` /
Traefik'in sağlam olması, ve bellek boşluğu raporu.

> `PRE_WEIGHTS=1` bayrağı m3 kontrolünü uyarıya çevirirdi. **Model dosyaları teslim
> edildi (2026-09-20), bayrak emekliye ayrıldı ve bir daha asla kullanılmamalıdır** —
> dedektörün kör olmadığını kanıtlayan tek kontrolü bastırır.

### Model dosyaları teslim edildikten sonraki doğrulama (2026-09-20)

`m3_encoder` artık `degraded_modules` içinde değil; `artifact_hash` `1bbfcce1…`. Yalnızca
sağlık kontrolüyle değil, işlevsel olarak doğrulandı: zararsız Türkçe cümle `0,0056`,
saldırgan Türkçe cümle `0,9839` skorladı — türetilmiş eşik `0,320188`'e karşı.
BERTurk ölçülen bellek maliyeti ~700 MB RSS'tir (tasarımın öngördüğü 1,5–3 GB değil).

### Bilinçli eksikler

- **Veritabanı yedeklenmiyor** — demo verisidir, `/srv/backup-db.sh` ile kasıtlı olarak
  bağlanmamıştır.
- **CI/CD yok** (yukarıya bkz.).
- **`diagnosis/` dağıtılmıyor** — ~886 MB'lık araştırma klasörüdür, her iki imaj
  bağlamından `.dockerignore` ile dışlanmıştır.

---

## 15. Bilinen sınırlar

- **`m5_sarcasm` kalan tek taslaktır.** Tek bir taslak bile her sonucu "eksik" işaretlemeye
  ve `clean` kararını ulaşılamaz kılmaya yeter (hata durumunda kapanır), bu yüzden zararsız
  bir cümle hâlâ `review` ile biter. Gerçek bir tespit ise kendi başına `nudge`, `escalate`
  veya `block`'a ulaşır. `D1` ve `C1–C5` üretilmez.
- **Hata durumunda kapanma, temiz cümleleri hâlâ bir insana gönderir.** Bu, kuyruğun
  dolmasının ikinci nedenidir ve bilinçlidir: bir sayı ayarlanarak değil, son taslak
  uygulandığında ortadan kalkar.
- **İnsan inceleme bandı (0,30 / 0,70) yer tutucu politikadır.** Proje sahibi tarafından
  seçilmiştir, geliştirme bölmesinde türetilmemiştir. Üzerine oturduğu türetilmiş eşik
  (`0,320188`) değişmemiştir — bant, bir ateşlemenin ardından hangi *eylemin* geleceğini
  değiştirir, kanalın ateşleyip ateşlemeyeceğini değil.
- **Eşikler panelden düzenlenemez.** `AI/decision/thresholds.yaml` içinde yaşarlar ve karar
  katmanının sahibine aittirler. `A1`'in eşiği orada hâlâ yer tutucudur.
- **Hazır cümleler (presets) gerçek modelde hiçbir kategoriyi ateşlemez.** Bugün uçtan uca
  ateşleyen bir cümle: `s4l4k herif, sen ne anlarsın` (B1, LEET, bireysel hedef).
- **Moderatör kimliği** tarayıcının anonim oturum takma adıdır ("Operatör"); hesap yoktur.
- **Kimlik doğrulama yoktur ve bu bilinçlidir.** Sistem tek bir çevrimdışı LAN demosu
  (bir dizüstü, oda Wi-Fi'ında ~70 kişi) için tasarlanmıştır; bu varsayım her yerde
  görünür. Bir dizüstünün ötesine taşınan her şey bunu hesaba katmak zorundadır.

---

## 16. Depo düzeni ve belge haritası

```
AI/           yedi modüllü tespit hattı, sözleşmeler, karar katmanı, çıkarım servisi
backend/      Go sunucusu: REST API, kuyruk, önbellek, Postgres, gömülü panel
frontend/     Vue 3 moderasyon paneli
diagnosis/    araştırma çalışması: protokoller, fazlar, sonuçlar, rapor
docs/         sistem belgeleri, UI şartnamesi (tarihsel), ekip
infra/        Docker Swarm yığınları, Dockerfile'lar, dağıtım kapısı, runbook
```

| Konu | Dosya |
|---|---|
| Tüm sistemin ayrıntılı anlatımı | [`docs/FULLSTACK.md`](docs/FULLSTACK.md) |
| Proje açıklaması | [`docs/PROJE_ACIKLAMASI.md`](docs/PROJE_ACIKLAMASI.md) |
| Yapay zekâ kuralları (önce okunmalı) | [`AI/CLAUDE.md`](AI/CLAUDE.md) |
| Modül içinde çalışma kuralları | [`AI/modules/README.md`](AI/modules/README.md) |
| Yapay zekâ devir notu | [`AI/docs/HANDOVER.md`](AI/docs/HANDOVER.md) |
| Eşikler ve eylemler (tek kaynak) | [`AI/decision/thresholds.yaml`](AI/decision/thresholds.yaml) |
| Model dosyaları ve sha256'ları | [`AI/artifacts/MANIFEST.md`](AI/artifacts/MANIFEST.md) |
| Bugün tespit edilenler | [`AI/serving/capabilities.py`](AI/serving/capabilities.py) |
| Backend pratik kılavuzu | [`backend/README.md`](backend/README.md) |
| Go ⇄ Python sözleşmesi | [`backend/docs/inference-contract.md`](backend/docs/inference-contract.md) |
| Frontend yapısı ve komutları | [`frontend/README.md`](frontend/README.md) |
| Araştırma özeti | [`diagnosis/README.md`](diagnosis/README.md) |
| Deney günlüğü | [`diagnosis/docs/RESULTS_LOG.md`](diagnosis/docs/RESULTS_LOG.md) |
| Operasyon runbook'u | [`infra/README.md`](infra/README.md) |
| Dağıtım öncesi/sonrası kontrolü | [`infra/verify-deploy.sh`](infra/verify-deploy.sh) |
| Kimin neyden sorumlu olduğu | [`docs/team/`](docs/team/) |
| Dağıtım tuzakları (kök notlar) | [`CLAUDE.md`](CLAUDE.md) |
