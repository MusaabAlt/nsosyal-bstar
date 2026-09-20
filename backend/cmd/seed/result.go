package main

import (
	"fmt"
	"math/rand/v2"
	"strings"
)

// Turning one catalogue sample into the AnalysisResult the pipeline would
// have produced for it (AI/contracts/schema.py, AnalysisResult.to_dict()).
//
// The seeder stands in for the decision layer here, exactly once: it is the
// only place in this repository outside AI/decision that compares a score
// with a threshold, and it does it with the numbers from
// AI/decision/thresholds.yaml so a seeded row is indistinguishable in shape
// from a row the real pipeline wrote. The panel still derives nothing.

const (
	contentThreshold   = 0.50     // thresholds.yaml categories.*.threshold
	offensiveThreshold = 0.320188 // thresholds.yaml binary_offensive.threshold
	formMinConfidence  = 0.50     // thresholds.yaml form.min_confidence
	guardThreshold     = 0.50     // thresholds.yaml guards.*.threshold
)

// The human review band for the general offensive score, mirroring
// thresholds.yaml `binary_offensive.review_band` (project owner request,
// 2026-09-20). A comment that fired NO content code is put in front of a
// moderator only while that score is genuinely uncertain; above the band it is
// decisive on its own and the content is blocked without a person.
//
// It bands the general offensive channel ONLY, exactly as
// AI/decision/actions.py does. The per-category actions above are NOT banded:
// A4, B2, B4 and C3 are marked "STAYS HUMAN" in thresholds.yaml on purpose,
// and a high score is not a reason to overrule that.
//
// Kept in step with that file by hand, like contentThreshold above: a
// disagreement here would show the panel a verdict the live system would not
// have produced.
const (
	reviewBandLow      = 0.30
	reviewBandHigh     = 0.70
	reviewBandAbove    = "block"
	reviewBandBelow    = "nudge"
	binaryOffensiveAct = "review" // thresholds.yaml binary_offensive.action
)

// offensiveAction is the verdict for a comment that only the general
// offensive score flagged, after the band.
func offensiveAction(score float64) string {
	switch {
	case score > reviewBandHigh:
		return reviewBandAbove
	case score < reviewBandLow:
		return reviewBandBelow
	default:
		return binaryOffensiveAct
	}
}

// actionFor is thresholds.yaml categories.*.action. It must be kept in step
// with that file by hand: the seeder stands in for the decision layer, so a
// disagreement here would show the panel a verdict the live system would not
// have produced. Last checked against thresholds.yaml on 2026-09-18, after
// the action policy revision.
var actionFor = map[string]string{
	"A1": "nudge", "A2": "block", "A3": "block", "A4": "review",
	"B1": "nudge", "B2": "escalate", "B3": "nudge", "B4": "escalate", "B5": "block",
	"C1": "nudge", "C2": "nudge", "C3": "review", "C4": "escalate", "C5": "nudge",
	"D1": "nudge",
}

// labelFor is AI/contracts/codes.py TR_LABELS, used only for the Turkish
// explanation sentence the panel shows verbatim.
var labelFor = map[string]string{
	"A1": "Hedefsiz küfür", "A2": "Bireye yönelik küfür", "A3": "Gruba yönelik küfür",
	"A4": "Kutsal değerlere yönelik küfür",
	"B1": "Aşağılama", "B2": "Tehdit", "B3": "Lanetleme / dışlama",
	"B4": "Kişisel bilgi ifşası (doxing)", "B5": "Cinsel saldırganlık",
	"C1": "Kalıp yargı", "C2": "Aşağılık atfetme", "C3": "Kodlu dil",
	"C4": "Kışkırtma", "C5": "Karalama / iftira", "D1": "Aşağılayıcı alay",
}

var guardLabelFor = map[string]string{
	"SUBSTRING_COLLISION": "alt dizi çakışması", "NEGATION": "olumsuzlama",
	"QUOTE_COUNTERSPEECH": "alıntı / karşı söylem", "METADISCUSSION": "dil üzerine tartışma",
	"SELF_DIRECTED": "kendine yönelik", "FRIENDLY_BANTER": "dostça takılma",
	"DUAL_REGISTER": "çift anlamlı kullanım", "HOMONYM": "eş sesli sözcük",
	"NON_HUMAN_TARGET": "insan dışı hedef",
}

// verdictSentence is the one Turkish sentence the panel shows verbatim.
var verdictSentence = map[string]string{
	"block":    "%s (%s) nedeniyle içerik engellendi.",
	"escalate": "%s (%s) nedeniyle içerik üst incelemeye iletildi.",
	"review":   "%s (%s) nedeniyle içerik incelemeye alındı.",
	"nudge":    "%s (%s) tespit edildi, kullanıcı uyarıldı.",
}

// offensiveSentence is the explanation when no category threshold was crossed
// and only the general offensive score decided, by where in the human review
// band that score fell.
var offensiveSentence = map[string]string{
	"block":  "Belirli bir kategori eşiği aşılmadı; genel saldırganlık skoru belirsizlik bandının üstünde kaldığı için içerik engellendi.",
	"review": "Belirli bir kategori eşiği aşılmadı; genel saldırganlık skoru belirsizlik bandında olduğu için içerik insan incelemesine alındı.",
	"nudge":  "Belirli bir kategori eşiği aşılmadı; genel saldırganlık skoru belirsizlik bandının altında kaldığı için kullanıcı uyarıldı.",
}

// contentScore is one row of result.content and one analysis_results row.
type contentScore struct {
	Code      string   `json:"code"`
	Score     float64  `json:"score"`
	Source    string   `json:"source"`
	Span      []int    `json:"span"`
	Threshold *float64 `json:"threshold"`
	Fired     *bool    `json:"fired"`
}

// analysed is everything the seeder needs to write one comment's rows.
type analysed struct {
	Result       map[string]any
	Content      []contentScore
	Verdict      *string
	FiredTypes   []string
	GuardsActive []string
	Degraded     bool
	Explanation  string
	LatencyMS    float64
	QueueWaitMS  float64
	// Detected mirrors the panel's detectedSQL: a content code fired, or the
	// offensive score did. Kept so the seeder can aim for a target share.
	Detected bool
}

func ptrF(v float64) *float64 { return &v }
func ptrB(v bool) *bool       { return &v }
func ptrS(v string) *string   { return &v }

// deref reads a verdict that the caller has already established is not nil.
func deref(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}

// distractors are the codes the encoder also scored but that stayed low. A
// real result always carries a few, and the "Neden?" panel shows them.
var distractorPool = []string{"A1", "A2", "B1", "B2", "C1", "C4", "D1"}

func pickDistractors(rng *rand.Rand, exclude string, n int) []string {
	out := make([]string, 0, n)
	for len(out) < n {
		code := distractorPool[rng.IntN(len(distractorPool))]
		if code == exclude || contains(out, code) {
			continue
		}
		out = append(out, code)
	}
	return out
}

func contains(list []string, want string) bool {
	for _, v := range list {
		if v == want {
			return true
		}
	}
	return false
}

func round2(v float64) float64 { return float64(int(v*100+0.5)) / 100 }
func round3(v float64) float64 { return float64(int(v*1000+0.5)) / 1000 }
func jitter(rng *rand.Rand, base, spread float64) float64 {
	v := base + (rng.Float64()*2-1)*spread
	if v < 0 {
		return 0
	}
	if v > 1 {
		return 1
	}
	return round2(v)
}

// analyse produces the stored result for one sample. degraded forces the
// "Değerlendirme tamamlanmadı" state: a module failed, so the decision layer
// produced no verdict.
func analyse(s sample, rng *rand.Rand, degraded bool) analysed {
	normScore := round2(s.Score)
	rawScore := round2(s.Raw)
	// The normalized channel only ever adds evidence (fusion strategy: max).
	rawContent := s.Score
	if len(s.Forms) > 0 {
		rawContent = round2(s.Score * (0.55 + rng.Float64()*0.15))
	}

	guardsActive := make([]string, 0, len(s.Guards))
	guards := make([]any, 0, len(s.Guards))
	for _, g := range s.Guards {
		score := jitter(rng, 0.78, 0.12)
		active := score >= guardThreshold
		suppressed := []string{}
		if active && s.Code != "" {
			suppressed = append(suppressed, s.Code)
			guardsActive = append(guardsActive, g)
		}
		guards = append(guards, map[string]any{
			"code": g, "score": score, "source": "m1_lexicon",
			"evidence": "", "span": nil, "threshold": guardThreshold,
			"active": active, "suppressed": suppressed,
		})
	}
	suppressedByGuard := len(guardsActive) > 0

	// ---- content scores, fused channel then the channels themselves
	content := make([]contentScore, 0, 4)
	channelScores := make([]any, 0, 6)
	firedTypes := make([]string, 0, 1)
	source := "m3_encoder@raw"
	if len(s.Forms) > 0 {
		source = "m3_encoder@normalized"
	}
	if s.Code != "" {
		fired := s.Score >= contentThreshold && !suppressedByGuard
		content = append(content, contentScore{
			Code: s.Code, Score: normScore, Source: source, Span: nil,
			Threshold: ptrF(contentThreshold), Fired: ptrB(fired),
		})
		if fired {
			firedTypes = append(firedTypes, s.Code)
		}
		channelScores = append(channelScores, channelRow(s.Code, round2(rawContent), "m3_encoder@raw"))
		if len(s.Forms) > 0 {
			channelScores = append(channelScores, channelRow(s.Code, normScore, "m3_encoder@normalized"))
		}
	}
	for _, code := range pickDistractors(rng, s.Code, 2) {
		score := jitter(rng, 0.12, 0.10)
		content = append(content, contentScore{
			Code: code, Score: score, Source: "m3_encoder@raw", Span: nil,
			Threshold: ptrF(contentThreshold), Fired: ptrB(false),
		})
		channelScores = append(channelScores, channelRow(code, score, "m3_encoder@raw"))
	}

	// ---- form patterns (m2)
	patterns := make([]any, 0, len(s.Forms))
	active := make([]string, 0, len(s.Forms))
	for _, f := range s.Forms {
		confidence := jitter(rng, 0.88, 0.08)
		patterns = append(patterns, map[string]any{
			"code": f, "confidence": confidence, "evidence": "", "span": nil, "source": "m2_deobf",
		})
		if confidence >= formMinConfidence {
			active = append(active, f)
		}
	}

	// ---- the binary offensive score (m3 raw channel only)
	offensiveFired := rawScore >= offensiveThreshold
	binaryOffensive := map[string]any{
		"threshold": offensiveThreshold, "branch": "scalar", "signal": nil, "signal_value": nil,
		"channels": map[string]any{"raw": map[string]any{"score": rawScore, "fired": offensiveFired}},
		"fired":    offensiveFired, "action": binaryOffensiveAct,
	}

	// ---- target (m6)
	var target any
	targetType := s.Target
	if targetType == "" {
		targetType = "none"
	}
	if s.Code != "" || targetType != "none" {
		target = map[string]any{
			"type": targetType, "confidence": jitter(rng, 0.82, 0.12),
			"evidence": "", "span": nil, "source": "m6_target",
		}
	}

	// ---- verdict
	var verdict *string
	detected := len(firedTypes) > 0 || offensiveFired
	switch {
	case degraded:
		verdict = nil
	case len(firedTypes) > 0:
		verdict = ptrS(actionFor[firedTypes[0]])
	case offensiveFired:
		verdict = ptrS(offensiveAction(rawScore))
	default:
		verdict = ptrS("clean")
	}

	explanation := explain(verdict, firedTypes, guardsActive, offensiveFired, degraded)

	perModule := map[string]float64{
		"m0_charsafe": round3(0.2 + rng.Float64()*0.6),
		"m1_lexicon":  round3(2.5 + rng.Float64()*6),
		"m2_deobf":    round3(1.0 + rng.Float64()*4),
		"m3_encoder":  round3(24 + rng.Float64()*48),
		"m4_implicit": round3(3 + rng.Float64()*9),
		"m5_sarcasm":  round3(2 + rng.Float64()*7),
		"m6_target":   round3(1 + rng.Float64()*3),
	}
	latency := 0.0
	for _, ms := range perModule {
		latency += ms
	}
	latency = round3(latency + 2 + rng.Float64()*6)

	degradedModules := []any{}
	if degraded {
		degradedModules = append(degradedModules, map[string]any{
			"module": "m5_sarcasm", "kinds": []string{"failed"},
			"reasons": []string{"inference timed out"},
		})
	}

	result := map[string]any{
		"text":    s.Text,
		"verdict": verdict,
		"form":    map[string]any{"patterns": patterns, "active": active},
		"content": content,
		"target":  target,
		"guards":  guards,
		"thread":  nil,
		"signals": map[string]any{
			"m0_charsafe": map[string]any{
				"offsets_identity": true, "invisible_removed": 0,
				"homoglyphs_mapped": 0, "charsafe_changed": false,
			},
			"m1_lexicon": map[string]any{"lexicon_hit": len(s.Guards) > 0 || strings.Contains(source, "normalized")},
			"m2_deobf":   map[string]any{"patterns_checked": 16, "changed": len(s.Forms) > 0},
			"m3_encoder": map[string]any{
				"raw_score": rawScore, "norm_score": normScore, "artifact": "m3-berturk-pytorch-fp32-epoch1",
			},
			"pipeline": map[string]any{
				"degraded":    degradedModules,
				"emits_spans": map[string]bool{"m0_charsafe": false, "m1_lexicon": true, "m2_deobf": true, "m3_encoder": false},
			},
			"decision": map[string]any{
				"family_a":           familyASignal(s),
				"threshold_branches": branches(content),
				"binary_offensive":   binaryOffensive,
				"channel_scores":     channelScores,
				"post_offensive":     detected,
			},
		},
		"explanation":   explanation,
		"latency_ms":    latency,
		"per_module_ms": perModule,
		"fast_path":     false,
		"trace_id":      "",
		"artifact_hash": "",
		"notes":         []string{},
	}

	return analysed{
		Result: result, Content: content, Verdict: verdict,
		FiredTypes: firedTypes, GuardsActive: guardsActive, Degraded: degraded,
		Explanation: explanation, LatencyMS: latency,
		QueueWaitMS: round3(rng.Float64() * 18), Detected: detected,
	}
}

func channelRow(code string, score float64, source string) map[string]any {
	return map[string]any{
		"code": code, "score": score, "source": source, "span": nil,
		"threshold": contentThreshold, "fired": score >= contentThreshold,
	}
}

func branches(content []contentScore) []any {
	out := make([]any, 0, len(content))
	for _, c := range content {
		out = append(out, map[string]any{
			"code": c.Code, "source": c.Source, "threshold": contentThreshold,
			"branch": "scalar", "signal": nil, "signal_value": nil,
		})
	}
	return out
}

// familyASignal records how ADR-005 assigned the A-family code from m6's target.
func familyASignal(s sample) any {
	if s.Code == "" || s.Code[0] != 'A' || s.Code == "A4" {
		return nil
	}
	target := s.Target
	if target == "" {
		target = "none"
	}
	return map[string]any{"target": target, "assigned": s.Code, "target_min_confidence": 0.50}
}

func explain(verdict *string, firedTypes, guardsActive []string, offensiveFired, degraded bool) string {
	switch {
	case degraded:
		return "Bir modül yanıt vermediği için değerlendirme tamamlanmadı."
	case len(firedTypes) > 0:
		code := firedTypes[0]
		return fmt.Sprintf(verdictSentence[actionFor[code]], labelFor[code], code)
	case offensiveFired:
		return offensiveSentence[deref(verdict)]
	case len(guardsActive) > 0:
		return fmt.Sprintf("Eşleşme %s bağlamında olduğu için tespit düşürüldü; içerik temiz.", guardLabelFor[guardsActive[0]])
	default:
		return "Hiçbir kategori eşiği aşılmadı; içerik temiz."
	}
}
