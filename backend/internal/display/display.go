// Package display computes the few numbers docs/UI asks the screen to show
// that the AnalysisResult does not carry:
//
//	"2 kategoriden 1'i değerlendirildi"          design-system 4.12
//	"Skor kendi eşiğini 0.32 puan aşıyor"        design-system 4.9
//	"Kontrol edilen diğer N kalıpta eşleşme yok" pages-spec stage 3
//	"Eşik altındaki N kategori gösterilmiyor"    pages-spec stage 5
//
// design-system 6 says the interface computes nothing, so the server computes
// them from the result and sends them beside it. Nothing here decides
// anything: which modules ran, which code fired and every threshold come from
// Python; this package only counts and subtracts what Python already sent.
//
// "Categories" means what the AI can detect today, as the inference service
// reports it in /health (AI/serving/capabilities.py), not the sixteen codes
// the contract defines.
package display

import (
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

// BinaryOffensive is the decision layer's channel-level offensive score. It
// is not a ContentCode, but it is a category the AI detects.
const BinaryOffensive = "binary_offensive"

// Capability is one thing the AI detects and the module that produces it.
type Capability = domain.Capability

// m2Tier1 and m2Tier2 are the form codes m2_deobf 0.1.1 actually checks, the
// two tiers of its module docstring. ABBREV, VOWEL_DROP, WORD_MERGE,
// CHAR_DROP, DIALECT and EMOJI_SUB are declared unhandled in v1 (m2 README),
// so they are not "checked" and must not be counted: the line this feeds
// promises the reader those patterns were looked for. ZERO_WIDTH and DOTLESS_I
// belong to m0 (stage 2); m2's HOMOGLYPH is its accent rule, which is its own.
var (
	m2Tier1 = []string{"LEET", "REPEAT", "SPACED", "PUNCT_SPLIT", "HOMOGLYPH", "PHONETIC"}
	// Tier 2 is morphology-backed and turns itself off when zeyrek is missing;
	// Python says which in signals.m2_deobf.tier2_enabled.
	m2Tier2 = []string{"DEASCII", "SUFFIX_ON_MASKED"}
)

// m2Checked is the pattern list m2 examined for this analysis.
func m2Checked(tier2Enabled bool) []string {
	if !tier2Enabled {
		return m2Tier1
	}
	return append(append([]string{}, m2Tier1...), m2Tier2...)
}

// NormalizationSummary counts the changes m2 reported (pages-spec stage 4:
// "one line stating what changed").
type NormalizationSummary struct {
	Removed  int `json:"removed"`
	Replaced int `json:"replaced"`
}

// Display is sent beside the result in POST /api/comments.
type Display struct {
	// nil when the inference service did not report its capabilities.
	CategoriesTotal     *int `json:"categories_total"`
	CategoriesEvaluated *int `json:"categories_evaluated"`
	CategoriesHidden    *int `json:"categories_hidden"`
	// nil when m2 did not run: nothing was checked.
	PatternsCheckedOther *int `json:"patterns_checked_other"`
	// Same order as result.content; nil where the threshold is null.
	ContentMargins []*float64 `json:"content_margins"`
	// Score minus threshold of signals.decision.binary_offensive; nil without both.
	BinaryOffensiveMargin *float64 `json:"binary_offensive_margin"`
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
		M2Deobf *struct {
			Tier2Enabled bool `json:"tier2_enabled"`
		} `json:"m2_deobf"`
		Decision *struct {
			BinaryOffensive *struct {
				Threshold *float64 `json:"threshold"`
				Channels  map[string]struct {
					Score *float64 `json:"score"`
				} `json:"channels"`
			} `json:"binary_offensive"`
		} `json:"decision"`
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

// BinaryOffensiveScore picks the channel score the decision layer used: raw
// first (the only channel with a derived threshold), then normalized.
func binaryOffensiveScore(channels map[string]struct {
	Score *float64 `json:"score"`
}) *float64 {
	for _, name := range []string{"raw", "normalized"} {
		if c, ok := channels[name]; ok && c.Score != nil {
			return c.Score
		}
	}
	return nil
}

// Build computes the display numbers for one result.
func Build(result, normalization json.RawMessage, capabilities []Capability) (Display, error) {
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

	d := Display{ContentMargins: make([]*float64, len(r.Content))}

	if len(capabilities) > 0 {
		returned := map[string]bool{}
		for _, c := range r.Content {
			returned[c.Code] = true
		}
		total, evaluated, hidden := len(capabilities), 0, 0
		for _, c := range capabilities {
			if !ran[c.Module] {
				continue
			}
			evaluated++
			// binary_offensive always has its own bar; only content codes can be hidden.
			if c.Code != BinaryOffensive && !returned[c.Code] {
				hidden++
			}
		}
		d.CategoriesTotal, d.CategoriesEvaluated, d.CategoriesHidden = &total, &evaluated, &hidden
	}

	if ran["m2_deobf"] {
		checked := m2Checked(r.Signals.M2Deobf != nil && r.Signals.M2Deobf.Tier2Enabled)
		detected := map[string]bool{}
		for _, p := range r.Form.Patterns {
			if strings.HasPrefix(p.Source, "m2_deobf") && slices.Contains(checked, p.Code) {
				detected[p.Code] = true
			}
		}
		other := len(checked) - len(detected)
		d.PatternsCheckedOther = &other
	}

	for i, c := range r.Content {
		if c.Threshold != nil {
			margin := c.Score - *c.Threshold
			d.ContentMargins[i] = &margin
		}
	}

	if dec := r.Signals.Decision; dec != nil && dec.BinaryOffensive != nil && dec.BinaryOffensive.Threshold != nil {
		if score := binaryOffensiveScore(dec.BinaryOffensive.Channels); score != nil {
			margin := *score - *dec.BinaryOffensive.Threshold
			d.BinaryOffensiveMargin = &margin
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
