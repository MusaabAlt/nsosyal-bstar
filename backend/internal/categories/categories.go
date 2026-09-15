// Package categories serves the Kategoriler page (pages-spec 3): every
// content category with its own threshold and action, read from the one
// file the decision layer uses, AI/decision/thresholds.yaml.
//
// The file is the source of truth and is never copied: it is re-read when
// its modification time changes, so the page always shows what Python is
// configured with.
package categories

import (
	"fmt"
	"os"
	"slices"
	"sync"
	"time"

	"go.yaml.in/yaml/v3"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/display"
)

type Category struct {
	Code      string   `json:"code"`
	Family    string   `json:"family"`
	Threshold *float64 `json:"threshold"`
	Action    *string  `json:"action"`
	// live | stub | unknown (unknown when the Python service is not reachable).
	Status string `json:"status"`
}

type List struct {
	// true while thresholds.yaml marks every value as a placeholder.
	Placeholder bool       `json:"placeholder"`
	Source      string     `json:"source"`
	Categories  []Category `json:"categories"`
}

type file struct {
	Artifact struct {
		Status string `yaml:"status"`
	} `yaml:"artifact"`
	Categories map[string]struct {
		Threshold *float64 `yaml:"threshold"`
		Action    *string  `yaml:"action"`
	} `yaml:"categories"`
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

// List builds the sixteen categories. degraded is the list of modules the
// Python service reports as not running; pythonKnown is false when the
// service could not be asked, in which case every status is "unknown".
func (s *Store) List(degraded []string, pythonKnown bool) (List, error) {
	f, err := s.load()
	if err != nil {
		return List{}, err
	}
	live := display.Evaluated(display.LiveModules(degraded))

	out := List{Placeholder: f.Artifact.Status == "placeholder", Source: "AI/decision/thresholds.yaml"}
	for _, code := range display.ContentCodes {
		c := Category{Code: code, Family: familyOf(code), Status: "unknown"}
		if entry, ok := f.Categories[code]; ok {
			c.Threshold, c.Action = entry.Threshold, entry.Action
		}
		if pythonKnown {
			c.Status = "stub"
			if slices.Contains(live, code) {
				c.Status = "live"
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
