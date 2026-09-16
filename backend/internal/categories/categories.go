// Package categories serves the Kategoriler page (pages-spec 3): the
// categories the AI can detect today, each with its own threshold and action
// read from the one file the decision layer uses, AI/decision/thresholds.yaml.
//
// Which categories exist is not decided here: the inference service reports
// its capabilities in /health (AI/serving/capabilities.py). The thresholds
// file is re-read when its modification time changes, so the page always
// shows what Python is configured with.
package categories

import (
	"fmt"
	"os"
	"slices"
	"strings"
	"sync"
	"time"

	"go.yaml.in/yaml/v3"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/display"
)

type Category struct {
	// A content code (A1 ...) or display.BinaryOffensive.
	Code string `json:"code"`
	// Content code family (A, B, C, D, CLEAN), or "" for binary_offensive.
	Family    string   `json:"family"`
	Threshold *float64 `json:"threshold"`
	Action    *string  `json:"action"`
	// true when thresholds.yaml records this threshold as derived on dev
	// (artifact.derived_on names it); false means it is still a placeholder.
	Derived bool `json:"derived"`
	// live | stub | unknown (unknown when the Python service is not reachable).
	Status string `json:"status"`
	Module string `json:"module"`
}

type List struct {
	Source     string     `json:"source"`
	Categories []Category `json:"categories"`
}

type entry struct {
	Threshold *float64 `yaml:"threshold"`
	Action    *string  `yaml:"action"`
}

type file struct {
	Artifact struct {
		Status    string `yaml:"status"`
		DerivedOn string `yaml:"derived_on"`
	} `yaml:"artifact"`
	Categories      map[string]entry `yaml:"categories"`
	BinaryOffensive entry            `yaml:"binary_offensive"`
}

// derivedKeys reads artifact.derived_on, "binary_offensive: frozen dev ... ; A1: ...",
// into the set of rows it names. When status is derived and nothing is named,
// the whole file counts as derived.
func (f *file) derived(code string) bool {
	if f.Artifact.Status != "derived" {
		return false
	}
	named := false
	for _, part := range strings.Split(f.Artifact.DerivedOn, ";") {
		key, _, found := strings.Cut(strings.TrimSpace(part), ":")
		if !found {
			continue
		}
		named = true
		if strings.TrimSpace(key) == code {
			return true
		}
	}
	return !named
}

// Store loads and caches the thresholds file.
type Store struct {
	path string

	mu      sync.Mutex
	modTime time.Time
	parsed  *file
}

func NewStore(path string) *Store { return &Store{path: path} }

func (s *Store) load() (*file, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	info, err := os.Stat(s.path)
	if err != nil {
		return nil, fmt.Errorf("thresholds file: %w", err)
	}
	if s.parsed != nil && info.ModTime().Equal(s.modTime) {
		return s.parsed, nil
	}
	data, err := os.ReadFile(s.path)
	if err != nil {
		return nil, fmt.Errorf("thresholds file: %w", err)
	}
	var f file
	if err := yaml.Unmarshal(data, &f); err != nil {
		return nil, fmt.Errorf("thresholds file %s: %w", s.path, err)
	}
	s.parsed, s.modTime = &f, info.ModTime()
	return s.parsed, nil
}

// List builds the category rows for the given capabilities. degraded is the
// list of modules the Python service reports as not running; pythonKnown is
// false when the service could not be asked, in which case every status is
// "unknown".
func (s *Store) List(capabilities []display.Capability, degraded []string, pythonKnown bool) (List, error) {
	f, err := s.load()
	if err != nil {
		return List{}, err
	}
	out := List{Source: "AI/decision/thresholds.yaml", Categories: []Category{}}
	for _, capability := range capabilities {
		c := Category{Code: capability.Code, Module: capability.Module, Status: "unknown", Derived: f.derived(capability.Code)}
		var e entry
		if capability.Code == display.BinaryOffensive {
			e = f.BinaryOffensive
		} else {
			e = f.Categories[capability.Code]
			c.Family = familyOf(capability.Code)
		}
		c.Threshold, c.Action = e.Threshold, e.Action
		if pythonKnown {
			c.Status = "live"
			if slices.Contains(degraded, capability.Module) {
				c.Status = "stub"
			}
		}
		out.Categories = append(out.Categories, c)
	}
	return out, nil
}

func familyOf(code string) string {
	if code == "CLEAN" {
		return "CLEAN"
	}
	return code[:1]
}
