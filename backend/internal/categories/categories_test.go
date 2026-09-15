package categories

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"testing"
	"time"
)

var update = flag.Bool("update", false, "rewrite the frontend golden file")

const realThresholds = "../../../AI/decision/thresholds.yaml"

// The degraded modules the default pipeline reports today.
var todaysStubs = []string{"m2_deobf", "m6_target", "m1_lexicon", "m3_encoder", "m5_sarcasm"}

func TestReadsTheRealThresholdsFile(t *testing.T) {
	list, err := NewStore(realThresholds).List(todaysStubs, true)
	if err != nil {
		t.Fatal(err)
	}
	if len(list.Categories) != 16 {
		t.Fatalf("%d categories", len(list.Categories))
	}
	if !list.Placeholder {
		t.Error("thresholds.yaml marks itself placeholder; the list must say so")
	}
	b2 := list.Categories[5]
	if b2.Code != "B2" || b2.Family != "B" || b2.Threshold == nil || *b2.Threshold != 0.5 || b2.Action == nil || *b2.Action != "escalate" {
		t.Fatalf("B2 = %+v", b2)
	}
	clean := list.Categories[15]
	if clean.Code != "CLEAN" || clean.Threshold != nil || clean.Action != nil {
		t.Fatalf("CLEAN has no row in thresholds.yaml: %+v", clean)
	}
	for _, c := range list.Categories {
		if c.Status != "stub" {
			t.Errorf("%s status %s: with today's stubs nothing is live", c.Code, c.Status)
		}
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
	all, _ := s.List(nil, true)
	for _, c := range all.Categories {
		if c.Status != "live" {
			t.Errorf("%s not live with every module running", c.Code)
		}
	}
	unknown, _ := s.List(nil, false)
	if unknown.Categories[0].Status != "unknown" {
		t.Error("status must be unknown when Python could not be asked")
	}
}

func TestReloadsWhenFileChanges(t *testing.T) {
	path := filepath.Join(t.TempDir(), "thresholds.yaml")
	write := func(threshold string) {
		if err := os.WriteFile(path, []byte("artifact: {status: derived}\ncategories:\n  B2: {threshold: "+threshold+", action: block}\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	write("0.40")
	s := NewStore(path)
	first, err := s.List(nil, true)
	if err != nil || *first.Categories[5].Threshold != 0.40 || first.Placeholder {
		t.Fatalf("first = %+v, %v", first.Categories[5], err)
	}
	write("0.62")
	later := time.Now().Add(2 * time.Second)
	_ = os.Chtimes(path, later, later)
	second, _ := s.List(nil, true)
	if *second.Categories[5].Threshold != 0.62 {
		t.Fatalf("change not picked up: %v", *second.Categories[5].Threshold)
	}
}

func TestMissingFileIsAnError(t *testing.T) {
	if _, err := NewStore(filepath.Join(t.TempDir(), "nope.yaml")).List(nil, true); err == nil {
		t.Fatal("want error")
	}
}
