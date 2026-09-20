package display

import (
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

// go test ./internal/display -update rewrites frontend/src/api/mocks/extras.json,
// so the frontend's sample mode shows exactly the numbers this server sends.
var update = flag.Bool("update", false, "rewrite the frontend golden file")

var mocksDir = filepath.Join("..", "..", "..", "frontend", "src", "api", "mocks")

// Today's capabilities, as AI/serving/capabilities.py reports them: m1's
// routed codes (A2 / A3 are its A1 carrier after the decision layer applies
// m6's target), m6's doxing code, and the encoder's offensive score.
var today = []Capability{
	{Code: "A1", Module: "m1_lexicon"},
	{Code: "A2", Module: "m1_lexicon"},
	{Code: "A3", Module: "m1_lexicon"},
	{Code: "B1", Module: "m1_lexicon"},
	{Code: "B2", Module: "m1_lexicon"},
	{Code: "B3", Module: "m1_lexicon"},
	{Code: "B4", Module: "m6_target"},
	{Code: BinaryOffensive, Module: "m3_encoder"},
}

func readJSON(t *testing.T, name string) json.RawMessage {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(mocksDir, name))
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func normalizationFor(t *testing.T, text string) json.RawMessage {
	t.Helper()
	var all map[string]json.RawMessage
	if err := json.Unmarshal(readJSON(t, "normalization.json"), &all); err != nil {
		t.Fatal(err)
	}
	return all[text]
}

func textOf(t *testing.T, raw json.RawMessage) string {
	t.Helper()
	var r struct {
		Text string `json:"text"`
	}
	if err := json.Unmarshal(raw, &r); err != nil {
		t.Fatal(err)
	}
	return r.Text
}

func intIs(p *int, want int) bool { return p != nil && *p == want }

// show prints what a pointer field HOLDS. %v on a *int prints its address, so
// a failure here used to read "total 0x30872fc87e0 evaluated 0x30872fc87e8"
// and told the reader nothing.
func show(p any) string {
	switch v := p.(type) {
	case *int:
		if v == nil {
			return "<nil>"
		}
		return strconv.Itoa(*v)
	case *float64:
		if v == nil {
			return "<nil>"
		}
		return strconv.FormatFloat(*v, 'g', -1, 64)
	}
	return fmt.Sprintf("%v", p)
}

func TestSamplePayloads(t *testing.T) {
	type want struct {
		evaluated, hidden int
		checkedOther      *int
		margins           []float64
		binaryMargin      *float64
	}
	five, six := 5, 6
	f := func(v float64) *float64 { return &v }
	cases := map[string]want{
		// Every module has a timing and only m5_sarcasm is degraded, so every
		// capability's owner ran: all 8 evaluated. m5 owns no capability of its
		// own, which is why a stub does not reduce the count. content is empty,
		// so all 7 content codes were evaluated and returned nothing - hidden;
		// binary_offensive always has its own bar and is never hidden.
		// m2 ran with tier 2 off: six tier-1 patterns checked, none matched.
		"degraded": {evaluated: 8, hidden: 7, checkedOther: &six, margins: []float64{}, binaryMargin: f(-0.2987765196179151)},
		// Only m0 ran.
		"clean": {evaluated: 0, hidden: 0, margins: []float64{}},
		// m0, m2, m3, m6 ran: binary_offensive and m6's B4 evaluated; m1's six
		// codes not, because m1 has no timing. content is B2 and C4, so B4 is
		// the one evaluated code that returned nothing.
		// m2 checked its six tier-1 patterns and matched one (LEET).
		"flagged": {evaluated: 2, hidden: 1, checkedOther: &five, margins: []float64{0.37, -0.38}, binaryMargin: f(-0.06)},
		// m0, m1 ran: m1's six codes evaluated, A1 returned, the other five below.
		"guard": {evaluated: 6, hidden: 5, margins: []float64{0.22}},
	}

	golden := map[string]Display{}
	for _, name := range []string{"degraded", "clean", "flagged", "guard"} {
		t.Run(name, func(t *testing.T) {
			raw := readJSON(t, name+".json")
			d, err := Build(raw, normalizationFor(t, textOf(t, raw)), today)
			if err != nil {
				t.Fatal(err)
			}
			w := cases[name]
			if !intIs(d.CategoriesTotal, len(today)) || !intIs(d.CategoriesEvaluated, w.evaluated) || !intIs(d.CategoriesHidden, w.hidden) {
				t.Errorf("total %s evaluated %s hidden %s, want %d/%d/%d", show(d.CategoriesTotal), show(d.CategoriesEvaluated), show(d.CategoriesHidden), len(today), w.evaluated, w.hidden)
			}
			if (d.PatternsCheckedOther == nil) != (w.checkedOther == nil) ||
				(w.checkedOther != nil && *d.PatternsCheckedOther != *w.checkedOther) {
				t.Errorf("patterns checked other = %s, want %s", show(d.PatternsCheckedOther), show(w.checkedOther))
			}
			if len(d.ContentMargins) != len(w.margins) {
				t.Fatalf("margins = %d entries, want %d", len(d.ContentMargins), len(w.margins))
			}
			for i := range w.margins {
				if math.Abs(*d.ContentMargins[i]-w.margins[i]) > 1e-9 {
					t.Errorf("margin %d = %v, want %v", i, *d.ContentMargins[i], w.margins[i])
				}
			}
			if (d.BinaryOffensiveMargin == nil) != (w.binaryMargin == nil) ||
				(w.binaryMargin != nil && math.Abs(*d.BinaryOffensiveMargin-*w.binaryMargin) > 1e-9) {
				t.Errorf("binary margin = %s, want %s", show(d.BinaryOffensiveMargin), show(w.binaryMargin))
			}
			golden[name] = d
		})
	}

	path := filepath.Join(mocksDir, "extras.json")
	encoded, err := json.MarshalIndent(golden, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	encoded = append(encoded, '\n')
	if *update {
		if err := os.WriteFile(path, encoded, 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	current, err := os.ReadFile(path)
	if err != nil || string(current) != string(encoded) {
		t.Fatalf("%s is out of date: run go test ./internal/display -update", path)
	}
}

// The real pipeline's shape since m3 0.1.0: only the raw channel is published.
func TestBinaryOffensiveRawChannelOnly(t *testing.T) {
	result := json.RawMessage(`{"content":[],"per_module_ms":{"m3_encoder":40},
		"signals":{"pipeline":{"degraded":[]},"decision":{"binary_offensive":{"threshold":0.320188,"channels":{"raw":{"score":0.9}}}}}}`)
	d, err := Build(result, nil, today)
	if err != nil {
		t.Fatal(err)
	}
	if d.BinaryOffensiveMargin == nil || math.Abs(*d.BinaryOffensiveMargin-(0.9-0.320188)) > 1e-9 {
		t.Fatalf("binary margin = %v", d.BinaryOffensiveMargin)
	}
	if !intIs(d.CategoriesEvaluated, 1) || !intIs(d.CategoriesHidden, 0) {
		t.Fatalf("evaluated %v hidden %v", d.CategoriesEvaluated, d.CategoriesHidden)
	}
}

func TestNoBinaryScoreNoMargin(t *testing.T) {
	// m3 failed (checkpoint missing): the channel score is null.
	result := json.RawMessage(`{"signals":{"decision":{"binary_offensive":{"threshold":0.32,"channels":{"raw":{"score":null}}}}}}`)
	d, err := Build(result, nil, today)
	if err != nil {
		t.Fatal(err)
	}
	if d.BinaryOffensiveMargin != nil {
		t.Fatal("margin without a score")
	}
}

// A module that ran evaluated every one of its codes; the ones it did not
// return are the hidden ones. m1 owns six of today's eight categories.
func TestEvaluatedButNotReturnedIsHidden(t *testing.T) {
	result := json.RawMessage(`{"content":[],"per_module_ms":{"m1_lexicon":1},"signals":{"pipeline":{"degraded":[]}}}`)
	d, err := Build(result, nil, today)
	if err != nil {
		t.Fatal(err)
	}
	if !intIs(d.CategoriesEvaluated, 6) || !intIs(d.CategoriesHidden, 6) {
		t.Fatalf("evaluated %v hidden %v", d.CategoriesEvaluated, d.CategoriesHidden)
	}
}

func TestWithoutCapabilitiesCountsAreNotGuessed(t *testing.T) {
	d, err := Build(json.RawMessage(`{"content":[]}`), nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if d.CategoriesTotal != nil || d.CategoriesEvaluated != nil || d.CategoriesHidden != nil {
		t.Fatal("counts invented without capabilities")
	}
}

func TestRemovedCharactersAreCounted(t *testing.T) {
	result := json.RawMessage(`{"content":[],"form":{"patterns":[]},"per_module_ms":{"m2_deobf":1},"signals":{"pipeline":{"degraded":[]}}}`)
	norm := json.RawMessage(`{"text":"salak","changes":[{"code":"PUNCT_SPLIT","from_span":[1,2],"to_span":null,"from":".","to":""},{"code":"PUNCT_SPLIT","from_span":[3,4],"to_span":null,"from":"..","to":""}]}`)
	d, err := Build(result, norm, today)
	if err != nil {
		t.Fatal(err)
	}
	if d.Normalization == nil || d.Normalization.Removed != 3 || d.Normalization.Replaced != 0 {
		t.Fatalf("summary = %+v", d.Normalization)
	}
	// Tier 2 is off in this result (no m2_deobf signal), so only the six tier-1
	// patterns were checked and none matched.
	if !intIs(d.PatternsCheckedOther, 6) {
		t.Fatalf("m2 ran with no pattern: checked other = %v", d.PatternsCheckedOther)
	}
}

func TestNullThresholdHasNoMargin(t *testing.T) {
	d, err := Build(json.RawMessage(`{"content":[{"code":"B2","score":0.9,"threshold":null}]}`), nil, today)
	if err != nil {
		t.Fatal(err)
	}
	if d.ContentMargins[0] != nil {
		t.Fatal("margin computed without a threshold")
	}
}
