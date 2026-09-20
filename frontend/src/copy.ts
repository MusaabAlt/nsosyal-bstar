/*
 * Every Turkish string on screen that does not come from the API response or
 * from the generated contract labels, kept in one file so the wording can be
 * reviewed in one place. The panel strings follow the ATI-SOSYAL Paneli design;
 * status, verdict and stage words are the ones the report model uses.
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

/**
 * The partitive suffix after a formatted percent, so a sentence can read
 * "analiz edilen içeriğin %12,5'i".
 *
 * A percent is spoken ending in its decimal digit - "%12,5" is "yüzde on iki
 * virgül beş", "%100,0" is "yüzde yüz virgül sıfır" - and formatPercent always
 * prints exactly one decimal, so the last character decides the suffix. A fixed
 * "'i" is wrong for seven of the ten digits: "%100,0'i" instead of "%100,0'ı".
 */
export function percentSuffix(percent: string): string {
  const last = percent.charCodeAt(percent.length - 1) - 48
  return last >= 0 && last <= 9 ? accusative(last) : "'i"
}

export const copy = {
  app: {
    brand: 'ATI-SOSYAL',
    demoMarker: 'Temsili veri',
    analyzeCta: 'Metin Analiz Et',
    darkMode: 'Karanlık mod',
    searchPlaceholder: 'Mesaj veya kullanıcı ara',
    searchLabel: 'Ara',
    openMenu: 'Menüyü aç',
    closeMenu: 'Menüyü kapat',
    operator: 'Operatör',
    liveFeed: 'Canlı Akış',
    liveFeedEmpty: 'Henüz mesaj yok.',
    systemStatus: 'Sistem durumu',
    unreachable: 'Sunucuya ulaşılamadı. Yeniden deneniyor…',
    nav: {
      overview: 'Genel Bakış',
      live: 'Canlı Analiz',
      queue: 'Moderasyon Kuyruğu',
      engines: 'Tespit Motorları',
      rules: 'Kurallar & Eşikler',
      history: 'Olay Geçmişi',
      health: 'Sistem Sağlığı',
    },
  },

  panel: {
    generalFamily: 'Genel',
    noDetection: 'Tespit yok',
    unavailable: 'veri yok',
    ranges: { live: 'Canlı', today: 'Bugün', week: '7 Gün' } as Record<string, string>,
    rangeWindow: { live: 'son 1 saat', today: 'bugün', week: 'son 7 gün' } as Record<string, string>,
    rangeCount: { live: 'son 1 saatte tespit', today: 'bugün tespit', week: 'son 7 günde tespit' } as Record<string, string>,
    kpi: {
      analysed: 'Analiz edilen mesaj',
      detected: 'Tespit edilen saldırganlık',
      automatic: 'Otomatik işlem',
      pending: 'İnsan incelemesi bekleyen',
      pendingTotal: (n: string) => `toplam ${n} bekleyen`,
      noPrevious: 'önceki dönem yok',
    },
    engines: 'Tespit motorları',
    enginesNote: 'Her saldırganlık türü için ayrı motor, ayrı eşik, ayrı eylem',
    enginesEmpty: 'Yapay zekâ hizmeti şu anda hiçbir kategori bildirmiyor.',
    threshold: (t: string) => `Eşik ${t}`,
    noThreshold: 'Eşik yok',
    status: { live: 'Aktif', stub: 'Modül hazır değil', unknown: 'Durum bilinmiyor' } as Record<string, string>,
    chartTitle: 'Kategoriye göre tespit (zaman)',
    chartEmpty: 'Bu aralıkta tespit yok.',
    patterns: 'Kaçış kalıpları',
    patternsEmpty: 'Bu aralıkta etkin bir gizleme kalıbı görülmedi.',
    patternCount: (n: string) => `${n} tespit`,
    recent: 'Son tespitler',
    recentEmpty: 'Henüz tespit yok.',
    goQueue: 'Kuyruğa git',
    score: 'skor',
    actions: {
      approve: 'Onayla',
      hide: 'Gizle',
      remove: 'Kaldır',
      queue: 'Kuyruğa ekle',
      false_positive: 'Yanlış pozitif bildir',
    } as Record<string, string>,
    actionDone: {
      approve: 'Onaylandı',
      hide: 'Gizlendi',
      remove: 'Kaldırıldı',
      queue: 'Kuyruğa eklendi',
      false_positive: 'Yanlış pozitif bildirildi',
    } as Record<string, string>,
    actionFailed: 'İşlem kaydedilemedi.',
    retry: 'Tekrar dene',
    loadMore: 'Daha fazla yükle',
    loadFailed: 'Veriler alınamadı.',
    system: {
      model: 'Model sürümü',
      latency: 'Gecikme p95',
      devices: 'Aktif cihaz (5 dk)',
      engines: 'Aktif motor',
    },
  },

  /*
   * Genel Bakış. The page answers four questions in order: how much was
   * analysed, what the system found, how it is distributed, and what a
   * moderator is looking at right now.
   */
  overview: {
    totalLabel: 'Analiz edilen içerik',
    totalUnit: 'gönderi ve yorum',
    totalWindow: { live: 'son 1 saatte', today: 'bugün', week: 'son 7 günde' } as Record<string, string>,
    detectedLabel: 'Tespit edilen saldırganlık',
    automaticLabel: 'Otomatik işlem',
    offensiveLabel: 'Genel saldırganlık sinyali',
    handledLabel: 'Moderatör işlemi',

    humanReview: 'İnsan incelemesi',
    humanReviewNote: 'Sistem kesin karar veremedi veya politika gereği moderatör onayı istiyor.',
    // Of everything analysed, not of the detections: the fail-closed rule sends
    // comments that fired nothing to a person too, so they are in this count
    // without being in "tespit". Over detections the card read %125,0.
    humanReviewShare: (pct: string) => `analiz edilen içeriğin ${pct}${percentSuffix(pct)}`,
    humanReviewTotal: (n: string) => `şu anda kuyrukta ${n} bekliyor`,
    humanReviewCta: 'Kuyruğa git',

    classes: 'Moderasyon sınıfları',
    classesNote: 'Her sınıf kendi modülü, kendi eşiği ve kendi eylemiyle değerlendirilir',
    classEmpty: 'Bu aralıkta tespit yok',
    classTotal: 'toplam tespit',
    // Sözleşme dört sınıfın da kodlarını tanımlar; yapay zekâ bugün hepsini
    // üretmiyor. Üretilmeyen bir kod 0 değil, "ölçülmedi" olarak gösterilir.
    classPending: 'henüz üretilmiyor',
    classPendingRow: 'Bu kodu üreten modül henüz devrede değil',
    classPendingNote: 'Bu sınıfın modülü henüz devrede değil, kodları ölçülmüyor',
    classPartial: (n: string) => `${n} kod henüz ölçülmüyor`,

    distribution: 'Kategori dağılımı',
    distributionEmpty: 'Bu aralıkta hiçbir kategori tespit edilmedi.',
    statusTitle: 'Moderasyon durumu',
    statusNote: 'Karar katmanının bu aralıkta verdiği sonuçlar',

    recent: 'Son moderasyon hareketleri',
    recentFilter: { detected: 'Tespitler', all: 'Tüm akış' } as Record<string, string>,
    recentEmpty: 'Bu aralıkta gösterilecek içerik yok.',
    columns: {
      content: 'İçerik',
      user: 'Kullanıcı',
      category: 'Kategori',
      status: 'Durum',
      time: 'Zaman',
    },
    why: 'Neden?',
    whyTitle: 'Karar gerekçesi',
    whyClose: 'Kapat',
    whyModules: 'Katkıda bulunan modüller',
    whyScores: 'Kategori skorları',
    whyGuards: 'Koruyucu kontroller',
    whyNoGuards: 'Hiçbir koruyucu kontrol tetiklenmedi.',
    whyNoScores: 'Yanıtta kategori skoru yok.',
    whyVerdict: 'Sistem kararı',
    whyModuleEmpty: 'Bu modül bu karara katkı vermedi.',
    whyLatency: 'Modül süreleri',
    // The pipeline's modules in the order they run (AI/contracts ModuleName).
    modules: {
      m0_charsafe: 'Karakter güvenliği',
      m1_lexicon: 'Sözlük eşleşmesi',
      m2_deobf: 'Gizleme çözme',
      m3_encoder: 'Dil modeli sınıflandırma',
      m4_implicit: 'Örtük saldırganlık',
      m5_sarcasm: 'Alaycılık',
      m6_target: 'Hedef belirleme',
    } as Record<string, string>,
    moduleNoSignal: 'sinyal yok',
    moduleDegraded: 'modül yanıt vermedi',
    charsafeClean: 'şüpheli karakter yok',
    charsafeChanged: (removed: number, mapped: number) => `${removed} görünmez karakter, ${mapped} benzer karakter`,
    lexiconHit: 'sözlük eşleşmesi var',
    lexiconMiss: 'sözlük eşleşmesi yok',
    deobfNone: 'gizleme kalıbı yok',
    targetLine: (kind: string, score: string) => `${kind} · güven ${score}`,
    offensiveLine: (score: string, threshold: string) => `skor ${score} · eşik ${threshold}`,
    whyContribution: 'Katkı',
    whyFired: 'Eşiği aştı',
    whyNotFired: 'Eşik altında',
    whyUndecided: 'Karar yok',
    whySuppressed: 'Koruyucu bastırdı',
  },

  live: {
    placeholder: 'Analiz etmek için bir mesaj yazın…',
    inputLabel: 'Analiz edilecek mesaj',
    presets: 'Hazır örnekler',
    clear: 'Temizle',
    language: 'Dil: TR',
    submit: 'Analiz Et',
    submitting: 'Analiz ediliyor',
    characters: (n: string) => `${n} / 5000`,
    emptyTitle: 'Henüz bir analiz yapılmadı',
    emptyText:
      'Yukarıya bir mesaj yazın ve “Analiz Et”e basın. Her kategori aynı metni kendi motoru ve kendi eşiğiyle ayrı ayrı değerlendirir.',
    input: 'Girdi',
    normalized: 'Normalize',
    normalizationStub: 'Normalleştirme modülü hazır değil',
    normalizationNone: 'Normalleştirilmiş metin yanıtta yok',
    noChanges: 'Değişiklik yok',
    detected: 'Tespit',
    below: 'Eşik altında',
    undecided: 'Karar yok',
    noMatch: 'Eşleşme yok',
    noMatchNote: 'Bu kategori metinde eşiğe yaklaşan bir bulgu bildirmedi.',
    moduleStub: 'Modül hazır değil',
    action: (a: string) => `Eylem: ${a}`,
    noAction: 'Eylem: yok',
    explanation: 'Açıklama',
    noSpans: 'Yanıt, metinde işaretlenecek bir bölüm bildirmedi.',
    finalDecision: (word: string) => `Nihai karar: ${word}`,
    notRun: (modules: string) => `Çalışmayan modüller: ${modules}`,
  },

  queue: {
    tabs: { pending: 'Bekleyen', reviewed: 'İncelenen', auto: 'Otomatik işlenen' } as Record<string, string>,
    detectedOnly: 'Yalnızca tespit edilenler',
    allCategories: 'Tüm kategoriler',
    search: 'Mesajda veya kullanıcıda ara',
    empty: 'Şu anda incelenecek mesaj bulunmamaktadır.',
    selected: (n: string) => `${n} seçili`,
    clearSelection: 'Seçimi kaldır',
    detail: 'Detay',
    selectHint: 'Ayrıntılarını görmek için listeden bir mesaj seçin.',
    scores: 'Motor skorları',
    category: 'Kategori',
    score: 'Skor',
    threshold: 'Eşik',
    outcome: 'Sonuç',
    context: 'Önceki mesajlar',
    noContext: 'Bu kullanıcının önceki mesajı yok.',
    history: 'Geçmiş',
    noHistory: 'Henüz moderatör işlemi yok.',
    decision: 'Sistem kararı',
    keyboard: 'A onayla · H gizle · R kaldır',
    status: { pending: 'Bekliyor', reviewed: 'İncelendi', auto: 'Otomatik', none: 'İşlem gerekmedi' } as Record<string, string>,
    selectLabel: 'Mesajı seç',
    notFound: 'Mesaj bulunamadı.',
  },

  engines: {
    module: 'Modül',
    action: 'Varsayılan eylem',
    thresholdSource: 'Eşik kaynağı',
    derived: 'Geliştirme verisinde türetildi',
    placeholder: 'Geçici değer',
    today: 'bugün tespit',
    test: 'Test et',
    queue: 'Kuyrukta gör',
  },

  rules: {
    note: 'Eşikler ve eylemler karar katmanının yapılandırmasından okunur ve bu panelden değiştirilemez. Her kategori yalnızca kendi eşiğiyle karşılaştırılır.',
    source: (file: string) => `Kaynak: ${file}`,
    columns: {
      category: 'Kategori',
      code: 'Kod',
      family: 'Aile',
      threshold: 'Eşik',
      action: 'Eylem',
      module: 'Modül',
      source: 'Eşik kaynağı',
      status: 'Durum',
    },
  },

  history: {
    tabs: { all: 'Tümü', moderator: 'Moderatör', system: 'Sistem' } as Record<string, string>,
    system: 'Sistem',
    unknownActor: 'Moderatör',
    searchResults: (q: string) => `“${q}” için sonuçlar`,
    clearSearch: 'Aramayı temizle',
    empty: 'Bu filtrede olay yok.',
    export: 'Dışa aktar',
    open: 'Kuyrukta aç',
  },

  health: {
    devices: 'Aktif cihaz (5 dk)',
    rps: 'İstek/sn (son dakika)',
    latency: 'Analiz gecikmesi p95',
    errors: 'Hata oranı (30 dk)',
    latencyChart: 'Analiz gecikmesi (ms, dakikalık)',
    requestsChart: 'İstek sayısı (dakikalık)',
    last30: 'son 30 dakika',
    services: 'Servisler',
    alertDegraded: 'Bir veya daha fazla servis sağlıklı değil.',
    alertSlow: (ms: string) => `Analiz gecikmesi yüksek: p95 ${ms} ms üzerinde.`,
    ok: 'Çalışıyor',
    down: 'Yanıt vermiyor',
    uptime: 'Çalışma süresi',
    goroutines: 'Goroutine',
    ping: 'Yanıt süresi',
    breaker: 'Devre kesici',
    artifact: 'Model',
    degradedModules: 'Hazır olmayan modüller',
    queue: 'Analiz kuyruğu',
    queueDepth: 'Bekleyen / kapasite',
    rejected: 'Reddedilen',
    batches: 'Model çağrısı',
    writer: 'Veritabanı yazıcı',
    written: 'Yazılan',
    dropped: 'Düşürülen',
    cache: 'Önbellek',
    cacheHits: 'İsabet / ıskalama',
    seriesP50: 'p50',
    seriesP95: 'p95',
    seriesAnalyses: 'Analiz',
    seriesAll: 'Tüm istekler',
    pythonStatus: { ok: 'Çalışıyor', loading: 'Yükleniyor', error: 'Hata', unreachable: 'Ulaşılamıyor' } as Record<string, string>,
    go: 'Go API',
    postgres: 'PostgreSQL',
    python: 'Model sunucusu',
    none: 'yok',
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
    // "Üretilebilen" names the universe the count is measured against: the
    // categories the AI can produce TODAY (AI/serving/capabilities.py), not
    // every category the contract defines. Without that word the line reads as
    // "the whole assessment completed" and contradicts the verdict above it,
    // which says the opposite whenever a module did not run.
    evaluated: (total: number, n: number) => `Üretilebilen ${total} kategoriden ${n}${accusative(n)} değerlendirildi`, // design-system 4.12
    // The other half of that sentence, in the same words the dashboard uses
    // for an unproduced code. Deliberately NOT attributed to the module named
    // on the next line: most of these are simply not built, and only D1
    // belongs to the stub.
    notProduced: (n: string) => `${n} kategori henüz üretilmiyor`,
  },

  /*
   * The four words the dashboard shows for a final classification. They name
   * the OUTCOME of a decision, where copy.verdict names the ACTION the
   * decision layer asks for; both come from the same final_action.
   */
  moderation: {
    clean: 'Temiz',
    warning: 'Uyarı',
    review: 'İnceleme',
    blocked: 'Engellendi',
    incomplete: 'Tamamlanmadı',
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

} as const
