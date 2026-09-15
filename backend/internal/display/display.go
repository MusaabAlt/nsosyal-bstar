// Package display computes the few numbers docs/UI asks the screen to show
// that the AnalysisResult does not carry:
//
//	"16 kategoriden N'i değerlendirildi"         design-system 4.12
//	"Skor kendi eşiğini 0.32 puan aşıyor"        design-system 4.9
//	"Kontrol edilen diğer N kalıpta eşleşme yok" pages-spec stage 3
//	"Eşik altındaki N kategori gösterilmiyor"    pages-spec stage 5
//
// design-system 6 says the interface computes nothing, so the server computes
// them from the result and sends them beside it. Nothing here decides
// anything: which modules ran, which code fired and every threshold come from
// Python; this package only counts and subtracts what Python already sent.
package display

import (
	"encoding/json"
	"fmt"
	"slices"
	"strings"
)

// Modules in the pipeline (AI/contracts/codes.py ModuleName).
var AllModules = []string{"m0_charsafe", "m1_lexicon", "m2_deobf", "m3_encoder", "m4_implicit", "m5_sarcasm", "m6_target"}

// ContentCodes in contract order (AI/contracts/codes.py ContentCode).
var ContentCodes = []string{
	"A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "B5",
	"C1", "C2", "C3", "C4", "C5", "D1", "CLEAN",
}

// coverage says which modules must have run for a category to count as
// evaluated, taken from the module specs and ADRs:
//   - any: at least one of these produced a score for the code
//   - all: these must also have run for the code to exist
//
// A1-A3 are scored by m1 and m3 on the A1 carrier; A2/A3 are assigned from
// m6's target (ADR-005). A4 is m1 only. B1-B3 and B5 are m3's B head; B4
// (doxing) is m6. C1-C5 are m3's C head with m4's thresholds (ADR-006).
// D1 is m5's own model (ADR-003). CLEAN is a real judgement only when every
// other category was evaluated.
type rule struct{ any, all []string }

var coverage = map[string]rule{
	"A1": {any: []string{"m1_lexicon", "m3_encoder"}},
	"A2": {any: []string{"m1_lexicon", "m3_encoder"}, all: []string{"m6_target"}},
	"A3": {any: []string{"m1_lexicon", "m3_encoder"}, all: []string{"m6_target"}},
	"A4": {any: []string{"m1_lexicon"}},
	"B1": {any: []string{"m3_encoder"}},
	"B2": {any: []string{"m3_encoder"}},
	"B3": {any: []string{"m3_encoder"}},
	"B4": {any: []string{"m6_target"}},
	"B5": {any: []string{"m3_encoder"}},
	"C1": {any: []string{"m3_encoder"}, all: []string{"m4_implicit"}},
	"C2": {any: []string{"m3_encoder"}, all: []string{"m4_implicit"}},
	"C3": {any: []string{"m3_encoder"}, all: []string{"m4_implicit"}},
	"C4": {any: []string{"m3_encoder"}, all: []string{"m4_implicit"}},
	"C5": {any: []string{"m3_encoder"}, all: []string{"m4_implicit"}},
	"D1": {any: []string{"m5_sarcasm"}},
}

// m2Patterns are the form codes m2 checks (m2 spec section 4 table).
// EMOJI_SUB is listed there but declared unhandled in v1, so it is not
// "checked". ZERO_WIDTH, HOMOGLYPH and DOTLESS_I belong to m0 (stage 2).
var m2Patterns = []string{
	"LEET", "REPEAT", "SPACED", "PUNCT_SPLIT", "CHAR_DROP", "WORD_MERGE",
	"ABBREV", "DEASCII", "VOWEL_DROP", "SUFFIX_ON_MASKED", "DIALECT", "PHONETIC",
}

// Evaluated lists, in contract order, the categories whose modules ran.
func Evaluated(ran map[string]bool) []string {
	out := []string{}
	for _, code := range ContentCodes {
		if code == "CLEAN" {
			continue
		}
		if covered(coverage[code], ran) {
			out = append(out, code)
		}
	}
	if len(out) == len(ContentCodes)-1 {
		out = append(out, "CLEAN")
	}
	return out
}

func covered(r rule, ran map[string]bool) bool {
	for _, m := range r.all {
		if !ran[m] {
			return false
		}
	}
	return slices.ContainsFunc(r.any, func(m string) bool { return ran[m] })
}

// LiveModules is every module not in the degraded list (used with /health,
// which reports only the degraded ones).
func LiveModules(degraded []string) map[string]bool {
	ran := map[string]bool{}
	for _, m := range AllModules {
		if !slices.Contains(degraded, m) {
			ran[m] = true
		}
	}
	return ran
}

// NormalizationSummary counts the changes m2 reported (pages-spec stage 4:
// "one line stating what changed").
type NormalizationSummary struct {
	Removed  int `json:"removed"`
	Replaced int `json:"replaced"`
}

// Display is sent beside the result in POST /api/comments.
type Display struct {
	CategoriesTotal     int `json:"categories_total"`
	CategoriesEvaluated int `json:"categories_evaluated"`
	CategoriesHidden    int `json:"categories_hidden"`
	// nil when m2 did not run: nothing was checked.
	PatternsCheckedOther *int `json:"patterns_checked_other"`
	// Same order as result.content; nil where the threshold is null.
	ContentMargins []*float64 `json:"content_margins"`
	// nil when no normalization was sent.
	Normalization *NormalizationSummary `json:"normalization"`
}

// resultFields is the part of the AnalysisResult this package reads.
type resultFields struct {
	Content []struct {
		Code      string   `json:"code"`
		Score     float64  `json:"score"`
		Threshold *float64 `json:"threshold"`
	} `json:"content"`
	Form struct {
		Patterns []struct {
			Code   string `json:"code"`
			Source string `json:"source"`
		} `json:"patterns"`
	} `json:"form"`
	PerModuleMS map[string]float64 `json:"per_module_ms"`
	Signals     struct {
		Pipeline *struct {
			Degraded []struct {
				Module string `json:"module"`
			} `json:"degraded"`
		} `json:"pipeline"`
	} `json:"signals"`
}

// Normalization is the optional m2 output sent beside the result.
type Normalization struct {
	Text    string   `json:"text"`
	Changes []Change `json:"changes"`
}

// Change is one repair: from_span in the original text, to_span in the
// normalized text (null when characters were removed).
type Change struct {
	Code     string  `json:"code"`
	FromSpan [2]int  `json:"from_span"`
	ToSpan   *[2]int `json:"to_span"`
	From     string  `json:"from"`
	To       string  `json:"to"`
}

// Build computes the display numbers for one result.
func Build(result json.RawMessage, normalization json.RawMessage) (Display, error) {
	var r resultFields
	if err := json.Unmarshal(result, &r); err != nil {
		return Display{}, fmt.Errorf("display: %w", err)
	}

	// A module ran when it has a timing and is not degraded.
	ran := map[string]bool{}
	for m := range r.PerModuleMS {
		ran[m] = true
	}
	if r.Signals.Pipeline != nil {
		for _, d := range r.Signals.Pipeline.Degraded {
			delete(ran, d.Module)
		}
	}

	evaluated := Evaluated(ran)
	returned := map[string]bool{}
	for _, c := range r.Content {
		returned[c.Code] = true
	}
	hidden := 0
	for _, code := range evaluated {
		if code != "CLEAN" && !returned[code] {
			hidden++
		}
	}

	d := Display{
		CategoriesTotal:     len(ContentCodes),
		CategoriesEvaluated: len(evaluated),
		CategoriesHidden:    hidden,
		ContentMargins:      make([]*float64, len(r.Content)),
	}

	if ran["m2_deobf"] {
		detected := map[string]bool{}
		for _, p := range r.Form.Patterns {
			if strings.HasPrefix(p.Source, "m2_deobf") && slices.Contains(m2Patterns, p.Code) {
				detected[p.Code] = true
			}
		}
		other := len(m2Patterns) - len(detected)
		d.PatternsCheckedOther = &other
	}

	for i, c := range r.Content {
		if c.Threshold != nil {
			margin := c.Score - *c.Threshold
			d.ContentMargins[i] = &margin
		}
	}

	if len(normalization) > 0 && string(normalization) != "null" {
		var n Normalization
		if err := json.Unmarshal(normalization, &n); err != nil {
			return Display{}, fmt.Errorf("display: normalization: %w", err)
		}
		s := &NormalizationSummary{}
		for _, ch := range n.Changes {
			if ch.ToSpan == nil {
				s.Removed += len([]rune(ch.From))
			} else {
				s.Replaced += len([]rune(ch.From))
			}
		}
		d.Normalization = s
	}
	return d, nil
}
