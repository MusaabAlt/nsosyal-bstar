package domain

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// The five real sample payloads are shared with the frontend; parsing them
// proves Go reads the same contract the screen renders.
func readMock(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "..", "frontend", "src", "api", "mocks", name+".json"))
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestParseRealPayloads(t *testing.T) {
	cases := []struct {
		name     string
		verdict  string
		degraded bool
		fired    []string
		guards   []string
	}{
		{"degraded", ActionReview, true, []string{}, []string{}},
		{"clean", ActionClean, false, []string{}, []string{}},
		{"flagged", ActionEscalate, false, []string{"B2"}, []string{}},
		{"guard", ActionClean, false, []string{}, []string{"SUBSTRING_COLLISION"}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			s, err := ParseResult(readMock(t, c.name))
			if err != nil {
				t.Fatal(err)
			}
			if s.Verdict == nil || *s.Verdict != c.verdict {
				t.Errorf("verdict = %v, want %s", s.Verdict, c.verdict)
			}
			if s.Degraded() != c.degraded {
				t.Errorf("degraded = %v, want %v", s.Degraded(), c.degraded)
			}
			if got := s.FiredTypes(); !reflect.DeepEqual(got, c.fired) {
				t.Errorf("fired = %v, want %v", got, c.fired)
			}
			if got := s.ActiveGuards(); !reflect.DeepEqual(got, c.guards) {
				t.Errorf("guards = %v, want %v", got, c.guards)
			}
			if s.Explanation == "" || s.ArtifactHash == "" {
				t.Error("explanation or artifact_hash empty")
			}
		})
	}
}

func TestParseRejectsBadShapes(t *testing.T) {
	for name, raw := range map[string]string{
		"not json":        `{`,
		"unknown verdict": `{"verdict": "hide"}`,
	} {
		if _, err := ParseResult([]byte(raw)); err == nil {
			t.Errorf("%s: want error", name)
		}
	}
	s, err := ParseResult([]byte(`{"verdict": null, "explanation": "Karar verilemedi"}`))
	if err != nil || s.Verdict != nil {
		t.Fatalf("verdict null must parse as nil: %v %v", s.Verdict, err)
	}
}

func TestMissingPipelineSignalsFailClosed(t *testing.T) {
	s, err := ParseResult([]byte(`{"verdict": "clean", "signals": {}}`))
	if err != nil {
		t.Fatal(err)
	}
	if !s.Degraded() {
		t.Fatal("a result without pipeline signals must count as degraded")
	}
}

func TestEngineFor(t *testing.T) {
	for source, want := range map[string]string{
		"m1_lexicon@raw":        "lexicon",
		"m3_encoder@normalized": "model",
		"m5_sarcasm@raw":        "model",
		"m6_target":             "rule",
		"m2_deobf":              "rule",
		"something_new@raw":     "model",
	} {
		if got := EngineFor(source); got != want {
			t.Errorf("EngineFor(%q) = %q, want %q", source, got, want)
		}
	}
}
