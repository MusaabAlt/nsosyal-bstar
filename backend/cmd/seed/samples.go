package main

// The demo catalogue: invented posts and comments, invented nicknames.
//
// Nothing here is a real NSosyal user, a real account or a real message. The
// offensive samples are deliberately masked or written with obfuscation
// (leet, spacing, punctuation splits) so the screen stays presentable on a
// projector while still exercising the deobfuscation story the panel tells.
//
// Weight is the relative frequency of a sample in the generated stream, so
// the dashboard's distribution looks like a real feed: mostly clean, a long
// tail of implicit aggression, few threats.

type sample struct {
	Text string
	// Content code the decision layer settles on; "" means no code fired.
	Code string
	// Fused score for Code (max over channels), 0 when Code is "".
	Score float64
	// m3's channel-level offensive probability on the raw text.
	Raw float64
	// m2 form patterns found in the text.
	Forms []string
	// Guards the lexicon raised; an active guard clears the code it covers.
	Guards []string
	// m6's published target: individual, group, non_human or none.
	Target string
	Weight int
}

// nicknames are invented handles in the shape NSosyal uses.
var nicknames = []string{
	"ayse_k", "mert61", "zeynep.demir", "kaan_yilmaz", "burak34", "elif.su",
	"onur_tekin", "selin06", "emre.kaya", "deniz_ada", "hakan_35", "ceren.ay",
	"tolga_bey", "irem.yildiz", "serkan16", "pinar_ozturk", "baris_42",
	"gamze.koc", "furkan_07", "nehir.akin", "yusuf_can", "melis27",
	"okan_arslan", "sude.polat", "cem_61", "duygu.eren", "arda_55",
	"nazli.gunes", "berk_tuna", "esra_06", "sinan.dogan", "yagmur_31",
}

// cleanSamples: ordinary talk on a social feed.
var cleanSamples = []sample{
	{Text: "Bugün hava çok güzel, sahilde yürüyüşe çıktım.", Weight: 8, Raw: 0.03},
	{Text: "Maçı izleyen var mı? Son on dakika nefes kesiciydi.", Weight: 8, Raw: 0.05},
	{Text: "Yeni açılan kafenin filtre kahvesi gerçekten iyiymiş.", Weight: 7, Raw: 0.02},
	{Text: "TEKNOFEST hazırlıkları hızlandı, ekip gece gündüz çalışıyor.", Weight: 7, Raw: 0.02},
	{Text: "Sabah trafiği yine kilit, metro çok daha mantıklı geliyor.", Weight: 7, Raw: 0.06},
	{Text: "Bu akşam kitap önerisi olan var mı? Türk edebiyatı olsun.", Weight: 6, Raw: 0.01},
	{Text: "Kargo iki gün erken geldi, doğrusu şaşırdım.", Weight: 6, Raw: 0.02},
	{Text: "Yazılım ekibine teşekkürler, güncelleme sorunsuz çalışıyor.", Weight: 6, Raw: 0.01},
	{Text: "Hafta sonu Ankara'ya gidiyorum, öneriniz var mı?", Weight: 6, Raw: 0.02},
	{Text: "Sınav sonuçları açıklandı, herkese kolay gelsin.", Weight: 5, Raw: 0.03},
	{Text: "Kedim yine klavyenin üstüne yattı, çalışmak imkânsız.", Weight: 5, Raw: 0.02},
	{Text: "Elektrik faturası bu ay çok yüksek geldi, kontrol edeceğim.", Weight: 5, Raw: 0.07},
	{Text: "Yeni telefonun pil ömrü beklediğimden iyi çıktı.", Weight: 5, Raw: 0.01},
	{Text: "Bisiklet yolu nihayet tamamlanmış, eline sağlık belediye.", Weight: 4, Raw: 0.02},
	{Text: "Akşam yemeğine mercimek çorbası yaptım, tavsiye ederim.", Weight: 4, Raw: 0.01},
	{Text: "Deprem tatbikatına katılan herkese teşekkürler.", Weight: 4, Raw: 0.04},
	{Text: "Konser biletleri tükendi, bir sonrakini kaçırmam.", Weight: 4, Raw: 0.02},
	{Text: "Bu bir test cümlesi.", Weight: 3, Raw: 0.02},
}

// guardedSamples: something looks offensive but a guard clears it. These are
// the panel's false-positive story.
var guardedSamples = []sample{
	{Text: "Amcam geldi, akşam yemeğe kalacak.", Guards: []string{"SUBSTRING_COLLISION"}, Code: "A1", Score: 0.61, Raw: 0.18, Weight: 4},
	{Text: "Kimseye \"s4lak\" demeyin, bu kelime burada yasak.", Guards: []string{"METADISCUSSION"}, Code: "A1", Score: 0.58, Forms: []string{"LEET"}, Raw: 0.29, Weight: 3},
	{Text: "Ne kadar aptalım, anahtarı yine içeride unuttum.", Guards: []string{"SELF_DIRECTED"}, Code: "A1", Score: 0.55, Raw: 0.24, Weight: 3},
	{Text: "Bu klavye tam bir rezalet, iki ayda bozuldu.", Guards: []string{"NON_HUMAN_TARGET"}, Code: "A1", Score: 0.52, Target: "non_human", Raw: 0.21, Weight: 3},
	{Text: "\"Senin gibilerden adam olmaz\" diyenlere katılmıyorum.", Guards: []string{"QUOTE_COUNTERSPEECH"}, Code: "C1", Score: 0.64, Raw: 0.26, Weight: 2},
	{Text: "Kimseye salak demedim, tam tersini söyledim.", Guards: []string{"NEGATION"}, Code: "A1", Score: 0.57, Raw: 0.22, Weight: 2},
	{Text: "Hadi oradan be koçum, yine mi geç kaldın.", Guards: []string{"FRIENDLY_BANTER"}, Code: "B1", Score: 0.53, Raw: 0.31, Weight: 2},
}

// detectedSamples: one block per family. Texts are masked on purpose.
var detectedSamples = []sample{
	// A - açık küfür
	{Text: "Bu trafik ne b0k ya, iki saattir aynı yerdeyim.", Code: "A1", Score: 0.71, Raw: 0.63, Forms: []string{"LEET"}, Target: "none", Weight: 9},
	{Text: "Lan yine kaçırdım treni, kahretsin ya.", Code: "A1", Score: 0.58, Raw: 0.44, Target: "none", Weight: 7},
	{Text: "a.p.t.a.l mısın sen, iki kere anlattım.", Code: "A2", Score: 0.83, Raw: 0.72, Forms: []string{"PUNCT_SPLIT"}, Target: "individual", Weight: 6},
	{Text: "g3r1z3k4l1 herif, ne dediğini bile bilmiyor.", Code: "A2", Score: 0.88, Raw: 0.79, Forms: []string{"LEET"}, Target: "individual", Weight: 5},
	{Text: "Hepiniz s a l a k sürüsüsünüz, hiçbiriniz okumamışsınız.", Code: "A3", Score: 0.86, Raw: 0.74, Forms: []string{"SPACED"}, Target: "group", Weight: 4},
	{Text: "Bu grubun tamamı b3yinsiz, tartışmaya değmez.", Code: "A3", Score: 0.81, Raw: 0.69, Forms: []string{"LEET"}, Target: "group", Weight: 3},
	{Text: "İnandığın her şey uydurma, hepsi masal.", Code: "A4", Score: 0.67, Raw: 0.48, Target: "group", Weight: 2},

	// B - sözcük dışı saldırganlık
	{Text: "Senin gibi cahil biriyle tartışmak vakit kaybı.", Code: "B1", Score: 0.79, Raw: 0.58, Target: "individual", Weight: 8},
	{Text: "Bu kadar basit bir şeyi anlamaman acınası gerçekten.", Code: "B1", Score: 0.72, Raw: 0.51, Target: "individual", Weight: 7},
	{Text: "Hiçbir işe yaramıyorsun, kimse seni ciddiye almıyor.", Code: "B1", Score: 0.76, Raw: 0.55, Target: "individual", Weight: 6},
	{Text: "Seni b1tireceğim, nerede oturduğunu biliyorum.", Code: "B2", Score: 0.91, Raw: 0.84, Forms: []string{"LEET"}, Target: "individual", Weight: 4},
	{Text: "Karşıma çıkma, sonu senin için iyi olmaz.", Code: "B2", Score: 0.87, Raw: 0.78, Target: "individual", Weight: 3},
	{Text: "Defol git buradan, seni burada görmek istemiyoruz.", Code: "B3", Score: 0.74, Raw: 0.61, Target: "individual", Weight: 5},
	{Text: "Allah belanı versin, iki yakan bir araya gelmesin.", Code: "B3", Score: 0.77, Raw: 0.64, Target: "individual", Weight: 4},
	{Text: "Adresini paylaşıyorum, herkes nerede oturduğunu bilsin.", Code: "B4", Score: 0.84, Raw: 0.57, Target: "individual", Weight: 2},
	{Text: "İma ettiğin şeyler iğrenç, bu mesajları herkes görüyor.", Code: "B5", Score: 0.80, Raw: 0.66, Target: "individual", Weight: 2},

	// C - örtük saldırganlık
	{Text: "Senin gibilerin oyu yüzünden bu haldeyiz.", Code: "C1", Score: 0.78, Raw: 0.42, Target: "group", Weight: 8},
	{Text: "Bunlardan adam olmaz zaten, hep aynı hikâye.", Code: "C1", Score: 0.73, Raw: 0.39, Target: "group", Weight: 7},
	{Text: "Sizin gibiler hep ikinci sınıf kalmaya mahkûm.", Code: "C2", Score: 0.75, Raw: 0.44, Target: "group", Weight: 5},
	{Text: "O malum tipler yine iş başında, anlayan anladı.", Code: "C3", Score: 0.69, Raw: 0.35, Target: "group", Weight: 5},
	{Text: "Toplanın da gösterelim onlara haddini, yeter artık.", Code: "C4", Score: 0.82, Raw: 0.56, Target: "group", Weight: 3},
	{Text: "Bu adam kesin rüşvet almıştır, herkes biliyor ama söylemiyor.", Code: "C5", Score: 0.71, Raw: 0.40, Target: "individual", Weight: 4},
	{Text: "Parayı nereden buldu acaba, sorgulayan yok tabii.", Code: "C5", Score: 0.66, Raw: 0.37, Target: "individual", Weight: 3},

	// D - aşağılayıcı ironi
	{Text: "Harika bir fikir, tabii ki sen dâhisin, biz anlamayız.", Code: "D1", Score: 0.70, Raw: 0.33, Target: "individual", Weight: 6},
	{Text: "Bravo, yine mükemmel bir iş çıkardın, her zamanki gibi.", Code: "D1", Score: 0.64, Raw: 0.30, Target: "individual", Weight: 5},
	{Text: "Vay be, ne büyük keşif, kimse düşünememişti.", Code: "D1", Score: 0.61, Raw: 0.28, Target: "individual", Weight: 4},
}

// borderlineSamples sit just under every content threshold: no code fires,
// but the offensive score clears its own threshold, so the decision layer
// asks for a person. This is the Human Review story.
var borderlineSamples = []sample{
	{Text: "Bu kadar saçma bir karar görmedim, kim onayladı bunu?", Code: "B1", Score: 0.46, Raw: 0.42, Target: "individual", Weight: 5},
	{Text: "Yine mi aynı hata, ciddi olamazsınız.", Code: "B1", Score: 0.41, Raw: 0.38, Target: "none", Weight: 4},
	{Text: "Sanki çok iyi biliyorsun da anlatıyorsun.", Code: "D1", Score: 0.48, Raw: 0.36, Target: "individual", Weight: 4},
	{Text: "Onlar hep böyle yapar zaten, alışığız.", Code: "C1", Score: 0.44, Raw: 0.35, Target: "group", Weight: 4},
	{Text: "Çok mu zor anlaması, gerçekten merak ediyorum.", Code: "B1", Score: 0.43, Raw: 0.39, Target: "individual", Weight: 3},
}
