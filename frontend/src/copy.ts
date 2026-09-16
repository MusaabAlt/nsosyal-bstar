/*
 * Every Turkish string on screen that does not come from the API response or
 * from the generated contract labels. Kept in one file so the wording can be
 * reviewed in one place. Strings quoted in docs/UI are copied verbatim; the
 * rest are marked "ours".
 */
/**
 * Turkish accusative suffix after a number, by how the number is read:
 * 4'ü (dört), 5'i (beş), 6'sı (altı), 0'ı (sıfır), 10'u (on), 16'sı (on altı).
 */
export function accusative(n: number): string {
  const units = ["'ı", "'i", "'si", "'ü", "'ü", "'i", "'sı", "'si", "'i", "'u"]
  const tens = ["", "'u", "'si", "'u", "'ı", "'si", "'ı", "'i", "'i", "'ı"]
  const abs = Math.abs(Math.trunc(n))
  if (abs % 10 !== 0 || abs === 0) return units[abs % 10] ?? "'i"
  if (abs % 100 !== 0) return tens[(abs / 10) % 10] ?? "'i"
  if (abs % 1000 !== 0) return "'ü" // yüz
  return "'i" // bin
}

export const copy = {
  app: {
    sidebarHeading: 'İçerik Moderasyon Paneli', // pages-spec 1
    navAnaliz: 'Analiz',
    navKategoriler: 'Kategoriler',
    demoMarker: 'Temsili veri', // design-system 4.19
  },

  analiz: {
    title: 'Analiz',
    placeholder: 'Analiz edilecek metni girin', // pages-spec 2.1
    submit: 'Analiz et', // design-system 5
    submitting: 'Analiz ediliyor',
    retry: 'Tekrar dene',
    inputLabel: 'Analiz edilecek metin', // ours: accessible name for the text area
    presetsLabel: 'Hazır örnekler', // ours: accessible name for the preset group
  },

  status: {
    passed: 'geçti', // design-system 4.7
    triggered: 'tetiklendi',
    below: 'eşik altında',
    notApplied: 'uygulanmadı',
    moduleUnavailable: 'modül hazır değil',
    noData: 'veri yok',
  },

  verdict: {
    block: 'Engelle', // design-system 4.11
    review: 'İncele',
    sensitive: 'Hassas içerik',
    clean: 'Temiz',
    incomplete: 'Değerlendirme tamamlanmadı', // 4.12
    latencyLabel: 'Gecikme', // ours: accessible name for the latency metric
    notRunHeading: 'Çalışmayan modüller', // ours
    moduleStatusMissing: 'Yanıt modül durumunu içermiyor.', // ours
    evaluated: (total: number, n: number) => `${total} kategoriden ${n}${accusative(n)} değerlendirildi`, // design-system 4.12
  },

  comparison: {
    keyword: 'Anahtar kelime filtresi', // design-system 4.14
    ours: 'Bu sistem',
  },

  stages: {
    input: 'Girdi', // pages-spec 2.3
    charsafe: 'Karakter güvenliği',
    obfuscation: 'Gizleme tespiti',
    normalization: 'Normalleştirme',
    content: 'İçerik sınıflandırma',
    target: 'Hedef',
    guards: 'Koruyucu kontroller',
    thread: 'Zincir değerlendirmesi',
    reason: 'Karar gerekçesi',

    characters: 'karakter', // ours: "19 karakter"
    showAll: 'Tamamını göster', // ours: long-input expand control
    showLess: 'Kısalt',

    charsafeNone: 'Şüpheli karakter bulunamadı', // pages-spec stage 2
    obfuscationNone: 'Gizleme kalıbı bulunamadı', // ours
    rawText: 'ham metin', // design-system 4.10
    recoveredText: 'çözülmüş metin',
    normalizationNone: 'Yanıt ham ve çözülmüş metin skorlarını içermiyor.', // ours
    normalizationMissing: 'Çözülmüş metin yanıtta yok.', // ours
    removedChars: (n: number) => `${n} karakter kaldırıldı`, // pages-spec stage 4 (`4 ayırıcı karakter kaldırıldı`)
    replacedChars: (n: number) => `${n} karakter değiştirildi`, // ours, same form
    noChanges: 'Metinde değişiklik yapılmadı', // ours
    patternsCheckedOther: (n: number) => `Kontrol edilen diğer ${n} kalıpta eşleşme yok`, // pages-spec stage 3
    hiddenCategories: (n: number) => `Eşik altındaki ${n} kategori gösterilmiyor`, // pages-spec stage 5
    marginAbove: (points: string) => `Skor kendi eşiğini ${points} puan aşıyor`, // design-system 4.9
    marginBelow: (points: string) => `Skor kendi eşiğinin ${points} puan altında`, // ours, the same sentence for a code that did not fire
    contentNone: 'Eşiği aşan kategori bulunmadı', // ours
    thresholdPrefix: 'eşik', // design-system 4.9: "eşik 0.62"
    thresholdMissing: 'eşik yok', // ours
    firedSentence: 'Skor kendi eşiğini aşıyor.', // ours: 4.9 relationship in words, without a computed difference
    notFiredSentence: 'Skor kendi eşiğinin altında.',
    undecidedSentence: 'Karar katmanı bu skor için karar vermedi.',
    suppressedSentence: (guard: string) => `${guard} kontrolü bu kategoriyi bilerek bastırdı.`,
    targetNone: 'Hedef bulunamadı', // ours
    binaryOffensive: 'Genel saldırganlık', // ours: the BERTurk offensive score, not a contract code
    targetWords: { individual: 'birey', group: 'grup', non_human: 'insan dışı', none: 'yok' } as Record<string, string>, // pages-spec stage 6
    guardsNone: 'Hiçbir koruyucu kontrol tetiklenmedi', // pages-spec stage 7
    guardPrevented: (guard: string, codes: string) => `${guard} kontrolü şu sinyali bastırdı: ${codes}.`, // ours
    guardDeliberate:
      'Sistem bu eşleşmeyi içeren sözcüğü tanıdı ve bilerek işaretlemedi; bu sessizlik bir karardır.', // ours, per pages-spec stage 7
    threadSinglePost: 'Bu girdi tek gönderi olarak değerlendirildi.', // ours, per pages-spec stage 8
    repeatCount: 'Aynı hedefe yönelik tekrar sayısı', // ours
    reasonStages: 'Sonucu üreten aşamalar', // ours
    reasonNoStage: 'Hiçbir aşama tetiklenmedi.', // ours
    moduleFailed: 'Modül çalıştı ancak geçerli çıktı üretmedi.', // ours
    moduleStub: 'Bu aşamanın modülü henüz uygulanmadı.', // ours
    noOutput: 'Bu aşama için yanıtta veri yok.', // ours
  },

  consequence: {
    heading: 'Kullanıcıya görünen', // pages-spec 2.5
    displayName: 'Kullanıcı', // ours: mock post author
    handle: '@kullanici',
    timestamp: 'şimdi',
    queued: 'Bu gönderi incelemeye alındı.', // ours
    withheld: 'Bu gönderi yayımlanmadı.', // ours
    incomplete: 'Değerlendirme tamamlanmadı; gönderi onaylanmış sayılmaz.', // ours
    sensitive:
      'Bu gönderide, bazı insanların saldırgan, kırıcı veya rahatsız edici bulabileceği hassas içerikler var.', // verbatim, NSosyal i18n
    show: 'Göster',
    idle: 'Analiz sonrası gönderinin kullanıcıya nasıl görüneceği burada gösterilir.', // ours
    actions: {
      comment: 'Yorum',
      repost: 'Yeniden paylaş',
      rocket: 'Roket',
      stats: 'İstatistik',
      bookmark: 'Kaydet',
      share: 'Paylaş',
    },
  },

  errors: {
    network: 'Analiz servisi yanıt vermedi.', // pages-spec 4
    rejected: 'Analiz servisi isteği kabul etmedi.', // ours (4xx)
    tooLarge: 'Metin, analiz servisinin kabul ettiği boyutu aşıyor.', // ours (413)
    busy: 'Analiz servisi şu anda meşgul.', // ours (503 queue_full)
    modelLoading: 'Model yükleniyor; birkaç saniye sonra tekrar deneyin.', // ours (503 model_loading)
    modelRestarting: 'Model yeniden başlatılıyor; birkaç saniye sonra tekrar deneyin.', // ours (503 model_unavailable)
    modelError: 'Model bu metni analiz edemedi.', // ours (502 model_error)
    rateLimited: 'Çok sık istek gönderildi; bir saniye sonra tekrar deneyin.', // ours (429)
    timeout: 'Analiz zamanında tamamlanamadı.', // ours (504)
    database: 'Veritabanı şu anda yanıt vermiyor.', // ours (503 database_unavailable)
  },

  kategoriler: {
    title: 'Kategoriler',
    placeholderNote: (labels: string) => `Eşiği henüz geliştirme verisinde türetilmedi, değer geçicidir: ${labels}.`, // ours: thresholds.yaml placeholder rows
    generalGroup: 'Genel', // ours: heading for the offensive score, which belongs to no family
    empty: 'Yapay zekâ hizmeti şu anda hiçbir kategori bildirmiyor.', // ours
    live: 'canlı', // ours: module status column
    loadError: 'Kategori listesi alınamadı.', // ours
    columns: {
      code: 'Kod',
      label: 'Etiket',
      definition: 'Tanım',
      threshold: 'Eşik',
      action: 'Eylem',
      module: 'Modül durumu',
    },
  },
} as const
