# NSosyal

[`diagnosis/`](diagnosis/) projenin merkezî bulgusunu üreten ölçüm çalışmasıdır: hiçbir
küfür sözcüğü içermeyen Türkçe saldırgan içerik model tarafından doğru sıralanır, ancak
karar eşiğinin altında kalır. Ön kayıt protokolleri, eğitim fazları, sonuçlar, rapor ve
demo bu klasördedir. Sayılar burada tekrarlanmaz; özet için
[`diagnosis/README.md`](diagnosis/README.md), ölçümlerin kendisi için
[`diagnosis/results/`](diagnosis/results/) ve tarihli kayıt için
[`diagnosis/docs/RESULTS_LOG.md`](diagnosis/docs/RESULTS_LOG.md) okunmalıdır.

[`AI/`](AI/) bu bulgu üzerine kurulan tespit sistemidir. Yedi modülden oluşur; saldırgan
söylemin her kategorisinin kendi motoru, kendi eşiği ve kendi eylemi vardır. Sistemin
uyguladığı eşik onarımı tanı çalışmasından gelir: eşik politikasının ön kaydı
[`diagnosis/phases/12_threshold_policy.md`](diagnosis/phases/12_threshold_policy.md),
sonucu [`diagnosis/results/12_threshold_policy/`](diagnosis/results/12_threshold_policy/)
altındadır.

[`frontend/`](frontend/) ve [`backend/`](backend/) arayüz çalışması için boş iskeletlerdir.

Başlamak için önce [`AI/CLAUDE.md`](AI/CLAUDE.md), ardından
[`AI/docs/HANDOVER.md`](AI/docs/HANDOVER.md) okunmalıdır.

## Kurulum

`AI/` ve `diagnosis/` farklı bağımlılıklar kullanır, bu yüzden her biri kendi sanal
ortamını ister. Taze bir klonda **ikisi de** ayrı ayrı kurulmalıdır; birinin ortamı
diğerinin testlerini çalıştırmaz. Python 3.11 veya üstü gerekir.

`AI/` yalnızca pyyaml ister:

```bash
cd AI
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt        # Windows: .venv\Scripts\python.exe
.venv/bin/python -m unittest discover -p "test_*.py"
```

`diagnosis/` torch ve transformers ister; kurulumu çok daha büyüktür:

```bash
cd diagnosis
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt        # Windows: .venv\Scripts\python.exe
.venv/bin/python -m pytest tests/ -q
```

Her iki ortamın komutları kendi klasöründen çalıştırılır.
