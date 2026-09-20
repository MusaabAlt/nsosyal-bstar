// Command mockinfer stands in for the Python inference service so the backend
// can be built and load-tested before the real models exist.
//
// It speaks the same contract as the FastAPI service (POST /predict_batch,
// GET /health) and answers with the real sample payloads from
// docs/team/AMIN_BRIEF.md section 7 (copied in frontend/src/api/mocks):
//
//	"Seni b1tireceğim"    -> flagged  (test-double scores)
//	"amcam geldi"         -> guard    (test-double scores)
//	"Bu bir test cumlesi" -> clean
//	anything else         -> degraded (what the real pipeline returns today)
//
//	go run ./cmd/mockinfer -delay 40ms -per-item 5ms -fail-rate 0.02 -load-time 5s
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type item struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

type result struct {
	ID            string          `json:"id"`
	OK            bool            `json:"ok"`
	Result        json.RawMessage `json:"result,omitempty"`
	Normalization json.RawMessage `json:"normalization,omitempty"`
	Error         string          `json:"error,omitempty"`
}

type server struct {
	payloads      map[string]map[string]any  // name -> payload
	byText        map[string]string          // text -> payload name
	normalization map[string]json.RawMessage // text -> optional m2 normalization
	artifactHash  string
	delay         time.Duration
	perItem       time.Duration
	failRate      float64
	itemFailRate  float64
	readyAt       time.Time
	// demo reports every configured category as live, so the panel shows one
	// card per moderation class next to the seeded demo feed (cmd/seed).
	demo bool
	log  *slog.Logger
}

func main() {
	addr := flag.String("addr", "127.0.0.1:8001", "listen address (keep it on localhost)")
	mocks := flag.String("mocks", filepath.Join("..", "frontend", "src", "api", "mocks"), "folder with degraded/clean/flagged/guard.json")
	delay := flag.Duration("delay", 30*time.Millisecond, "base time per batch (simulated model work)")
	perItem := flag.Duration("per-item", 5*time.Millisecond, "extra time per text in a batch")
	failRate := flag.Float64("fail-rate", 0, "probability a whole batch returns HTTP 500")
	itemFailRate := flag.Float64("item-fail-rate", 0, "probability one item returns ok:false")
	loadTime := flag.Duration("load-time", 0, "answer 503 loading for this long after start")
	demo := flag.Bool("demo", false, "report every category in thresholds.yaml as live (for the seeded demo panel)")
	flag.Parse()

	log := slog.New(slog.NewTextHandler(os.Stderr, nil))
	s, err := newServer(*mocks)
	if err != nil {
		log.Error("load mocks", "error", err)
		os.Exit(1)
	}
	s.delay, s.perItem, s.failRate, s.itemFailRate = *delay, *perItem, *failRate, *itemFailRate
	s.readyAt = time.Now().Add(*loadTime)
	s.demo = *demo
	s.log = log

	mux := http.NewServeMux()
	mux.HandleFunc("POST /predict_batch", s.predict)
	mux.HandleFunc("GET /health", s.health)
	log.Info("mock inference service", "addr", *addr, "delay", *delay, "per_item", *perItem, "fail_rate", *failRate, "load_time", *loadTime, "demo", *demo)
	srv := &http.Server{Addr: *addr, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	if err := srv.ListenAndServe(); err != nil {
		log.Error("serve", "error", err)
		os.Exit(1)
	}
}

func newServer(dir string) (*server, error) {
	s := &server{payloads: map[string]map[string]any{}, byText: map[string]string{}}
	for _, name := range []string{"degraded", "clean", "flagged", "guard"} {
		data, err := os.ReadFile(filepath.Join(dir, name+".json"))
		if err != nil {
			return nil, err
		}
		var p map[string]any
		if err := json.Unmarshal(data, &p); err != nil {
			return nil, fmt.Errorf("%s.json: %w", name, err)
		}
		s.payloads[name] = p
		if name != "degraded" {
			s.byText[p["text"].(string)] = name
		}
	}
	s.artifactHash, _ = s.payloads["degraded"]["artifact_hash"].(string)

	// Optional m2 output for the samples whose run included m2.
	s.normalization = map[string]json.RawMessage{}
	if data, err := os.ReadFile(filepath.Join(dir, "normalization.json")); err == nil {
		var all map[string]json.RawMessage
		if err := json.Unmarshal(data, &all); err != nil {
			return nil, fmt.Errorf("normalization.json: %w", err)
		}
		for text, n := range all {
			if !strings.HasPrefix(text, "_") {
				s.normalization[text] = n
			}
		}
	}
	return s, nil
}

func (s *server) loading() bool { return time.Now().Before(s.readyAt) }

func (s *server) health(w http.ResponseWriter, _ *http.Request) {
	status := "ok"
	if s.loading() {
		status = "loading"
	}
	// What the real service reports today (AI/serving/capabilities.py).
	capabilities := []map[string]string{
		{"code": "A1", "module": "m1_lexicon"},
		{"code": "A2", "module": "m1_lexicon"},
		{"code": "A3", "module": "m1_lexicon"},
		{"code": "B1", "module": "m1_lexicon"},
		{"code": "B2", "module": "m1_lexicon"},
		{"code": "B3", "module": "m1_lexicon"},
		{"code": "B4", "module": "m6_target"},
		{"code": "binary_offensive", "module": "m3_encoder"},
	}
	// m5_sarcasm is the one module still a stub: m2 and m6 landed 2026-09-17,
	// and m4 is not a stub (it has nothing to score until m3's C head exists).
	degraded := []string{"m5_sarcasm"}
	if s.demo {
		capabilities, degraded = demoCapabilities, []string{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"status":           status,
		"artifact_hash":    s.artifactHash,
		"degraded_modules": degraded,
		"capabilities":     capabilities,
		// Sample data: the UI shows the Temsili veri marker while this service runs.
		"representative": true,
	})
}

func (s *server) predict(w http.ResponseWriter, r *http.Request) {
	if s.loading() {
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "loading"})
		return
	}
	var req struct {
		Items []item `json:"items"`
	}
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 4<<20)).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	// Simulated model work, cut short if Go gives up on the batch.
	select {
	case <-time.After(s.delay + time.Duration(len(req.Items))*s.perItem):
	case <-r.Context().Done():
		return
	}
	if rand.Float64() < s.failRate {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "internal error: RuntimeError"})
		return
	}

	results := make([]result, 0, len(req.Items))
	for _, it := range req.Items {
		if rand.Float64() < s.itemFailRate {
			results = append(results, result{ID: it.ID, OK: false, Error: "internal error: RuntimeError"})
			continue
		}
		raw, err := s.payloadFor(it)
		if err != nil {
			results = append(results, result{ID: it.ID, OK: false, Error: err.Error()})
			continue
		}
		results = append(results, result{ID: it.ID, OK: true, Result: raw, Normalization: s.normalization[it.Text]})
	}
	writeJSON(w, http.StatusOK, map[string]any{"artifact_hash": s.artifactHash, "results": results})
}

func (s *server) payloadFor(it item) (json.RawMessage, error) {
	name, known := s.byText[it.Text]
	if !known {
		name = "degraded"
	}
	p := make(map[string]any, len(s.payloads[name]))
	for k, v := range s.payloads[name] {
		p[k] = v
	}
	// The degraded payload carries no spans, so any text keeps it truthful.
	p["text"] = it.Text
	p["trace_id"] = it.ID
	// A real service runs one model version: every result carries the hash /health reports.
	p["artifact_hash"] = s.artifactHash
	if strings.TrimSpace(it.Text) == "" {
		return nil, fmt.Errorf("empty text")
	}
	return json.Marshal(p)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

// demoCapabilities is every category AI/decision/thresholds.yaml configures,
// in the order the panel shows them. Reported only with -demo, beside the
// seeded feed from cmd/seed; the real service reports what it can actually
// detect today.
// Each code names the module that would produce it, as the pipeline is built:
// B1-B3 are m1's routed lexicon codes (not m3's), B4 is m6's doxing detector,
// and C1-C5 come from m3's C head - m4_implicit owns their thresholds and the
// slice repair, not the scores.
var demoCapabilities = []map[string]string{
	{"code": "A1", "module": "m1_lexicon"},
	{"code": "A2", "module": "m1_lexicon"},
	{"code": "A3", "module": "m1_lexicon"},
	{"code": "A4", "module": "m1_lexicon"},
	{"code": "B1", "module": "m1_lexicon"},
	{"code": "B2", "module": "m1_lexicon"},
	{"code": "B3", "module": "m1_lexicon"},
	{"code": "B4", "module": "m6_target"},
	{"code": "B5", "module": "m3_encoder"},
	{"code": "C1", "module": "m3_encoder"},
	{"code": "C2", "module": "m3_encoder"},
	{"code": "C3", "module": "m3_encoder"},
	{"code": "C4", "module": "m3_encoder"},
	{"code": "C5", "module": "m3_encoder"},
	{"code": "D1", "module": "m5_sarcasm"},
	{"code": "binary_offensive", "module": "m3_encoder"},
}
