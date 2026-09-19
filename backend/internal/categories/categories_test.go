package categories

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/display"
)

var update = flag.Bool("update", false, "rewrite the frontend golden file")

const realThresholds = "../../../AI/decision/thresholds.yaml"

// Today's capabilities (AI/serving/capabilities.py) and the modules the real
// pipeline reports as degraded when the m3 checkpoint is present.
var (
	today       = []display.Capability{{Code: "A1", Module: "m1_lexicon"}, {Code: display.BinaryOffensive, Module: "m3_encoder"}}
	todaysStubs = []string{"m2_deobf", "m6_target", "m5_sarcasm"}
)

func TestReadsTheRealThresholdsFile(t *testing.T) {
	list, err := NewStore(realThresholds).List(today, todaysStubs, true)
	if err != nil {
		t.Fatal(err)
	}
	if len(list.Categories) != 2 {
		t.Fatalf("%d categories, want only what the AI detects", len(list.Categories))
	}
	a1, bo := list.Categories[0], list.Categories[1]
	if a1.Code != "A1" || a1.Family != "A" || a1.Threshold == nil || *a1.Threshold != 0.5 || a1.Action == nil || *a1.Action != "nudge" || a1.Derived || a1.Status != "live" {
		t.Fatalf("A1 = %+v", a1)
	}
	if bo.Code != display.BinaryOffensive || bo.Family != "" || bo.Threshold == nil || *bo.Threshold != 0.320188 || *bo.Action != "review" || !bo.Derived || bo.Status != "live" {
		t.Fatalf("binary_offensive = %+v", bo)
	}

	// Golden for the frontend's sample mode.
	path := filepath.Join("..", "..", "..", "frontend", "src", "api", "mocks", "categories.json")
	encoded, _ := json.MarshalIndent(list, "", "  ")
	encoded = append(encoded, '\n')
	if *update {
		if err := os.WriteFile(path, encoded, 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	if current, err := os.ReadFile(path); err != nil || string(current) != string(encoded) {
		t.Fatalf("%s is out of date: run go test ./internal/categories -update", path)
	}
}

func TestStatusFollowsHealth(t *testing.T) {
	s := NewStore(realThresholds)
	down, _ := s.List(today, []string{"m3_encoder"}, true)
	if down.Categories[0].Status != "live" || down.Categories[1].Status != "stub" {
		t.Errorf("m3 degraded: %+v", down.Categories)
	}
	unknown, _ := s.List(today, nil, false)
	if unknown.Categories[0].Status != "unknown" {
		t.Error("status must be unknown when Python could not be asked")
	}
	none, _ := s.List(nil, nil, true)
	if len(none.Categories) != 0 {
		t.Error("no capabilities reported means no categories, not all sixteen")
	}
}

func TestDerivedOnlyForNamedRows(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "thresholds.yaml")
	write := func(body string) {
		if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
			t.Fatal(err)
		}
		later := time.Now().Add(time.Duration(len(body)) * time.Second)
		_ = os.Chtimes(path, later, later)
	}
	caps := []display.Capability{{Code: "A1", Module: "m1_lexicon"}, {Code: display.BinaryOffensive, Module: "m3_encoder"}}
	s := NewStore(path)

	write("artifact: {status: placeholder}\ncategories:\n  A1: {threshold: 0.4, action: block}\nbinary_offensive: {threshold: 0.5, action: review}\n")
	l, err := s.List(caps, nil, true)
	if err != nil || l.Categories[0].Derived || l.Categories[1].Derived {
		t.Fatalf("placeholder file: %+v %v", l.Categories, err)
	}

	write("artifact: {status: derived, derived_on: \"A1: dev 2026; binary_offensive: dev\"}\ncategories:\n  A1: {threshold: 0.62, action: block}\nbinary_offensive: {threshold: 0.3, action: review}\n")
	l, _ = s.List(caps, nil, true)
	if !l.Categories[0].Derived || !l.Categories[1].Derived || *l.Categories[0].Threshold != 0.62 {
		t.Fatalf("reloaded derived file: %+v", l.Categories)
	}
}

func TestMissingFileIsAnError(t *testing.T) {
	if _, err := NewStore(filepath.Join(t.TempDir(), "nope.yaml")).List(today, nil, true); err == nil {
		t.Fatal("want error")
	}
}
