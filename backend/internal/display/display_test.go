package display

import (
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"testing"
)

// go test ./internal/display -update rewrites frontend/src/api/mocks/extras.json,
// so the frontend's sample mode shows exactly the numbers this server sends.
var update = flag.Bool("update", false, "rewrite the frontend golden file")

var mocksDir = filepath.Join("..", "..", "..", "frontend", "src", "api", "mocks")

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

func TestSamplePayloads(t *testing.T) {
	type want struct {
		evaluated, hidden int
		checkedOther      *int
		margins           []*float64
		replaced          int
		normalization     bool
	}
	eleven := 11
	f := func(v float64) *float64 { return &v }
	cases := map[string]want{
		// Default pipeline today: only m0 and m4 run, nothing is evaluated.
		"degraded": {evaluated: 0, hidden: 0, margins: []*float64{}},
		// Only m0 ran.
		"clean": {evaluated: 0, hidden: 0, margins: []*float64{}},
		// m0, m2, m3 ran: A1, B1, B2, B3, B5. Content returned B2 and C4, so A1, B1, B3, B5 are hidden.
		"flagged": {evaluated: 5, hidden: 4, checkedOther: &eleven, margins: []*float64{f(0.37), f(-0.38)}, replaced: 1, normalization: true},
		// m0, m1 ran: A1 and A4. A1 was returned, A4 is hidden.
		"guard": {evaluated: 2, hidden: 1, margins: []*float64{f(0.22)}},
	}

	golden := map[string]Display{}
	for _, name := range []string{"degraded", "clean", "flagged", "guard"} {
		t.Run(name, func(t *testing.T) {
			raw := readJSON(t, name+".json")
			d, err := Build(raw, normalizationFor(t, textOf(t, raw)))
			if err != nil {
				t.Fatal(err)
			}
			w := cases[name]
			if d.CategoriesTotal != 16 || d.CategoriesEvaluated != w.evaluated || d.CategoriesHidden != w.hidden {
				t.Errorf("total %d evaluated %d hidden %d", d.CategoriesTotal, d.CategoriesEvaluated, d.CategoriesHidden)
			}
			if (d.PatternsCheckedOther == nil) != (w.checkedOther == nil) ||
				(d.PatternsCheckedOther != nil && *d.PatternsCheckedOther != *w.checkedOther) {
				t.Errorf("patterns checked other = %v, want %v", ptrStr(d.PatternsCheckedOther), ptrStr(w.checkedOther))
			}
			if len(d.ContentMargins) != len(w.margins) {
				t.Fatalf("margins = %d entries, want %d", len(d.ContentMargins), len(w.margins))
			}
			for i := range w.margins {
				if math.Abs(*d.ContentMargins[i]-*w.margins[i]) > 1e-9 {
					t.Errorf("margin %d = %v, want %v", i, *d.ContentMargins[i], *w.margins[i])
				}
			}
			if (d.Normalization != nil) != w.normalization || (d.Normalization != nil && d.Normalization.Replaced != w.replaced) {
				t.Errorf("normalization = %+v", d.Normalization)
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

func ptrStr(p *int) string {
	if p == nil {
		return "nil"
	}
	return fmt.Sprint(*p)
}

func TestEvaluatedRules(t *testing.T) {
	all := LiveModules(nil)
	if got := Evaluated(all); len(got) != 16 || got[15] != "CLEAN" {
		t.Fatalf("all modules live: %v", got)
	}
	// Without m6 no target can be assigned, so A2, A3 and B4 are not evaluated, and CLEAN is not a real judgement.
	noTarget := LiveModules([]string{"m6_target"})
	got := Evaluated(noTarget)
	for _, code := range []string{"A2", "A3", "B4", "CLEAN"} {
		for _, g := range got {
			if g == code {
				t.Errorf("%s evaluated without m6", code)
			}
		}
	}
	if len(got) != 12 {
		t.Errorf("evaluated without m6 = %v", got)
	}
	if got := Evaluated(LiveModules(AllModules)); len(got) != 0 {
		t.Errorf("nothing live but evaluated %v", got)
	}
}

func TestRemovedCharactersAreCounted(t *testing.T) {
	result := json.RawMessage(`{"content":[],"form":{"patterns":[]},"per_module_ms":{"m2_deobf":1},"signals":{"pipeline":{"degraded":[]}}}`)
	norm := json.RawMessage(`{"text":"salak","changes":[{"code":"PUNCT_SPLIT","from_span":[1,2],"to_span":null,"from":".","to":""},{"code":"PUNCT_SPLIT","from_span":[3,4],"to_span":null,"from":"..","to":""}]}`)
	d, err := Build(result, norm)
	if err != nil {
		t.Fatal(err)
	}
	if d.Normalization == nil || d.Normalization.Removed != 3 || d.Normalization.Replaced != 0 {
		t.Fatalf("summary = %+v", d.Normalization)
	}
	if d.PatternsCheckedOther == nil || *d.PatternsCheckedOther != 12 {
		t.Fatalf("m2 ran with no pattern: checked other = %v", d.PatternsCheckedOther)
	}
}

func TestNullThresholdHasNoMargin(t *testing.T) {
	d, err := Build(json.RawMessage(`{"content":[{"code":"B2","score":0.9,"threshold":null}]}`), nil)
	if err != nil {
		t.Fatal(err)
	}
	if d.ContentMargins[0] != nil {
		t.Fatal("margin computed without a threshold")
	}
}
