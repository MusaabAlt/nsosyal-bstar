package handlers

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/netip"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/google/uuid"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/cache"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/categories"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/inference"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/metrics"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/queue"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
)

// ------------------------------------------------------------------ fakes

type fakeStore struct {
	mu       sync.Mutex
	sessions map[uuid.UUID]bool
	checks   int
	fail     error
	page     store.Page
	counts   store.DashboardCounts
	countsN  int
}

func (f *fakeStore) CreateSession(_ context.Context, nickname string, _ netip.Addr) (domain.Session, error) {
	if f.fail != nil {
		return domain.Session{}, f.fail
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	s := domain.Session{ID: uuid.Must(uuid.NewV7()), Nickname: nickname, CreatedAt: time.Now()}
	f.sessions[s.ID] = true
	return s, nil
}

func (f *fakeStore) SessionExists(_ context.Context, id uuid.UUID) (bool, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.checks++
	return f.sessions[id], f.fail
}

func (f *fakeStore) Feed(_ context.Context, limit int, cursor string, flagged bool) (store.Page, error) {
	if cursor == "bad" {
		return store.Page{}, store.ErrBadCursor
	}
	return f.page, f.fail
}

func (f *fakeStore) DashboardCounts(context.Context) (store.DashboardCounts, error) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.countsN++
	return f.counts, f.fail
}

func (f *fakeStore) Ping(context.Context) error { return f.fail }

type fakeWriter struct {
	mu      sync.Mutex
	records []domain.AnalysisRecord
}

func (w *fakeWriter) EnqueueAnalysis(r domain.AnalysisRecord) bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.records = append(w.records, r)
	return true
}
func (w *fakeWriter) Stats() store.WriterStats { return store.WriterStats{} }

type fakeAnalyzer struct {
	result json.RawMessage
	norm   json.RawMessage
	err    error
	calls  atomic.Int32
}

func (a *fakeAnalyzer) Submit(_ context.Context, item domain.PredictItem) (queue.Result, error) {
	a.calls.Add(1)
	if a.err != nil {
		return queue.Result{}, a.err
	}
	return queue.Result{Outcome: domain.PredictOutcome{ID: item.ID, Result: a.result, Normalization: a.norm}, QueueWait: 3 * time.Millisecond, ModelLatency: 40 * time.Millisecond, BatchSize: 4}, nil
}
func (a *fakeAnalyzer) Stats() queue.Stats { return queue.Stats{QueueCapacity: 256} }

type fakeInference struct {
	hash           string
	degraded       []string
	representative bool
}

func (f fakeInference) ArtifactHash() string { return f.hash }
func (f fakeInference) Health() inference.Health {
	return inference.Health{Status: "ok", ArtifactHash: f.hash, Breaker: inference.BreakerClosed, DegradedModules: f.degraded, Representative: f.representative}
}

func mock(t *testing.T, name string) json.RawMessage {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "frontend", "src", "api", "mocks", name+".json"))
	if err != nil {
		t.Fatal(err)
	}
	return data
}

type env struct {
	api      *API
	store    *fakeStore
	writer   *fakeWriter
	analyzer *fakeAnalyzer
	mux      *http.ServeMux
}

func newEnv(t *testing.T) *env {
	t.Helper()
	e := &env{
		store:    &fakeStore{sessions: map[uuid.UUID]bool{}},
		writer:   &fakeWriter{},
		analyzer: &fakeAnalyzer{result: mock(t, "flagged")},
	}
	e.api = New(Deps{
		Store: e.store, Writer: e.writer, Analyzer: e.analyzer,
		Inference:    fakeInference{hash: "57466e1738c99c48ae87ba537df93c268d446b3cf4a258669ff3611f5bf6fe63"},
		Categories:   categories.NewStore("../../../../AI/decision/thresholds.yaml"),
		Cache:        cache.New[CachedAnalysis](100, time.Minute),
		Metrics:      metrics.NewRegistry(),
		Log:          slog.New(slog.NewTextHandler(io.Discard, nil)),
		MaxBodyBytes: 64 << 10, MaxTextChars: 5000, StartedAt: time.Now(),
	})
	e.mux = http.NewServeMux()
	e.api.Register(e.mux)
	return e
}

func (e *env) do(method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.RemoteAddr = "192.168.1.40:51000"
	rr := httptest.NewRecorder()
	e.mux.ServeHTTP(rr, req)
	return rr
}

func (e *env) session(t *testing.T) string {
	t.Helper()
	rr := e.do(http.MethodPost, "/api/sessions", `{"nickname":"Emin"}`)
	if rr.Code != http.StatusCreated {
		t.Fatalf("create session: %d %s", rr.Code, rr.Body)
	}
	var s domain.Session
	_ = json.Unmarshal(rr.Body.Bytes(), &s)
	return s.ID.String()
}

func errorCode(t *testing.T, rr *httptest.ResponseRecorder) string {
	t.Helper()
	var body struct {
		Error struct {
			Code    string `json:"code"`
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("error body is not the standard shape: %s", rr.Body)
	}
	return body.Error.Code
}

// ------------------------------------------------------------------ tests

func TestCreateSession(t *testing.T) {
	e := newEnv(t)
	rr := e.do(http.MethodPost, "/api/sessions", `{"nickname":"  Ayşe  "}`)
	if rr.Code != http.StatusCreated {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
	var s domain.Session
	if err := json.Unmarshal(rr.Body.Bytes(), &s); err != nil || s.Nickname != "Ayşe" || s.ID == uuid.Nil {
		t.Fatalf("session = %+v, %v", s, err)
	}

	for name, body := range map[string]string{
		"empty":         `{"nickname":"   "}`,
		"too long":      `{"nickname":"` + strings.Repeat("ş", 33) + `"}`,
		"control char":  `{"nickname":"a\u0007b"}`,
		"unknown field": `{"nickname":"a","admin":true}`,
		"not json":      `nickname=a`,
		"two objects":   `{"nickname":"a"}{"nickname":"b"}`,
	} {
		t.Run(name, func(t *testing.T) {
			if rr := e.do(http.MethodPost, "/api/sessions", body); rr.Code != http.StatusBadRequest {
				t.Fatalf("%d %s", rr.Code, rr.Body)
			}
		})
	}
}

func TestCreateCommentReturnsResultUnchanged(t *testing.T) {
	e := newEnv(t)
	sid := e.session(t)
	rr := e.do(http.MethodPost, "/api/comments", fmt.Sprintf(`{"session_id":%q,"text":"Seni b1tireceğim"}`, sid))
	if rr.Code != http.StatusCreated {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
	var resp struct {
		Comment struct {
			ID uuid.UUID `json:"id"`
		} `json:"comment"`
		Result json.RawMessage `json:"result"`
		Timing timing          `json:"timing"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	var want, got any
	_ = json.Unmarshal(mock(t, "flagged"), &want)
	_ = json.Unmarshal(resp.Result, &got)
	if fmt.Sprint(want) != fmt.Sprint(got) {
		t.Fatal("result differs from what the model returned")
	}
	if resp.Timing.CacheHit || resp.Timing.BatchSize == nil || *resp.Timing.BatchSize != 4 || *resp.Timing.ModelMS != 40 {
		t.Fatalf("timing = %+v", resp.Timing)
	}

	// The record handed to the async writer carries the decision as Python made it.
	if len(e.writer.records) != 1 {
		t.Fatalf("%d records enqueued", len(e.writer.records))
	}
	rec := e.writer.records[0]
	if rec.CommentID != resp.Comment.ID || *rec.Summary.Verdict != "escalate" || rec.IP != "192.168.1.40" || len(rec.TextSHA256) != 32 {
		t.Fatalf("record = %+v", rec)
	}
}

func TestRepeatedTextIsServedFromCache(t *testing.T) {
	e := newEnv(t)
	sid := e.session(t)
	body := fmt.Sprintf(`{"session_id":%q,"text":"Seni b1tireceğim"}`, sid)
	e.do(http.MethodPost, "/api/comments", body)
	rr := e.do(http.MethodPost, "/api/comments", body)
	if rr.Code != http.StatusCreated {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
	if e.analyzer.calls.Load() != 1 {
		t.Fatalf("model called %d times for the same text", e.analyzer.calls.Load())
	}
	if !strings.Contains(rr.Body.String(), `"cache_hit":true`) {
		t.Fatalf("second response not marked as cache hit: %s", rr.Body)
	}
	// A different spelling is a different question.
	e.do(http.MethodPost, "/api/comments", fmt.Sprintf(`{"session_id":%q,"text":"Seni bitireceğim"}`, sid))
	if e.analyzer.calls.Load() != 2 {
		t.Fatal("a different spelling was served from cache")
	}
	if !e.writer.records[1].FromCache {
		t.Fatal("cached analysis not recorded as from_cache")
	}
}

// Regression: the lookup used the version from /health while the save used the
// version inside the result; when they differed, identical texts never hit.
func TestCacheHitsWhenResultVersionDiffersFromHealth(t *testing.T) {
	e := newEnv(t)
	e.api.Inference = fakeInference{hash: "version-from-health"}
	sid := e.session(t)
	body := fmt.Sprintf(`{"session_id":%q,"text":"aynı metin"}`, sid)
	e.do(http.MethodPost, "/api/comments", body)
	rr := e.do(http.MethodPost, "/api/comments", body)
	if e.analyzer.calls.Load() != 1 || !strings.Contains(rr.Body.String(), `"cache_hit":true`) {
		t.Fatalf("model calls %d, second response %s", e.analyzer.calls.Load(), rr.Body)
	}
}

func TestFailedDecisionIsNotCached(t *testing.T) {
	e := newEnv(t)
	e.analyzer.result = json.RawMessage(`{"text":"x","verdict":null,"explanation":"Karar verilemedi: karar katmanında","artifact_hash":"h","signals":{"pipeline":{"degraded":[]}}}`)
	sid := e.session(t)
	body := fmt.Sprintf(`{"session_id":%q,"text":"x"}`, sid)
	e.do(http.MethodPost, "/api/comments", body)
	e.do(http.MethodPost, "/api/comments", body)
	if e.analyzer.calls.Load() != 2 {
		t.Fatal("verdict null was cached")
	}
}

func TestSessionIsCheckedOnceThenRemembered(t *testing.T) {
	e := newEnv(t)
	id := uuid.Must(uuid.NewV7())
	e.store.sessions[id] = true // created by another server instance, not in memory
	body := fmt.Sprintf(`{"session_id":%q,"text":"a"}`, id)
	for range 3 {
		if rr := e.do(http.MethodPost, "/api/comments", body); rr.Code != http.StatusCreated {
			t.Fatalf("%d %s", rr.Code, rr.Body)
		}
	}
	if e.store.checks != 1 {
		t.Fatalf("session checked %d times in the database", e.store.checks)
	}
}

func TestCommentValidation(t *testing.T) {
	e := newEnv(t)
	sid := e.session(t)
	cases := []struct {
		name, body, code string
		status           int
	}{
		{"unknown session", fmt.Sprintf(`{"session_id":%q,"text":"a"}`, uuid.Must(uuid.NewV7())), "unknown_session", 400},
		{"bad session id", `{"session_id":"nope","text":"a"}`, "unknown_session", 400},
		{"blank text", fmt.Sprintf(`{"session_id":%q,"text":"   "}`, sid), "invalid_text", 400},
		{"5001 chars", fmt.Sprintf(`{"session_id":%q,"text":%q}`, sid, strings.Repeat("ş", 5001)), "invalid_text", 400},
		{"body too large", fmt.Sprintf(`{"session_id":%q,"text":%q}`, sid, strings.Repeat("a", 70000)), "body_too_large", 413},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rr := e.do(http.MethodPost, "/api/comments", c.body)
			if rr.Code != c.status || errorCode(t, rr) != c.code {
				t.Fatalf("%d %s", rr.Code, rr.Body)
			}
		})
	}
	// 5000 multibyte characters are accepted.
	rr := e.do(http.MethodPost, "/api/comments", fmt.Sprintf(`{"session_id":%q,"text":%q}`, sid, strings.Repeat("ş", 5000)))
	if rr.Code != http.StatusCreated {
		t.Fatalf("5000 chars: %d %s", rr.Code, rr.Body)
	}
	if e.analyzer.calls.Load() != 1 {
		t.Fatalf("invalid requests reached the model: %d calls", e.analyzer.calls.Load())
	}
}

func TestAnalysisErrorsAreFastAndClear(t *testing.T) {
	cases := []struct {
		name       string
		err        error
		status     int
		code       string
		retryAfter bool
	}{
		{"queue full", queue.ErrQueueFull, 503, "queue_full", true},
		{"shutting down", queue.ErrClosed, 503, "shutting_down", true},
		{"model loading", inference.ErrLoading, 503, "model_loading", true},
		{"python down", fmt.Errorf("%w: connection refused", inference.ErrUnavailable), 503, "model_unavailable", true},
		{"item error", &inference.ItemError{Message: "x"}, 502, "model_error", false},
		{"worker panic", queue.ErrPredictorPanic, 502, "model_error", false},
		{"unexpected", errors.New("???"), 500, "internal_error", false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			e := newEnv(t)
			sid := e.session(t)
			e.analyzer.err = c.err
			rr := e.do(http.MethodPost, "/api/comments", fmt.Sprintf(`{"session_id":%q,"text":"a"}`, sid))
			if rr.Code != c.status || errorCode(t, rr) != c.code {
				t.Fatalf("%d %s", rr.Code, rr.Body)
			}
			if c.retryAfter && rr.Header().Get("Retry-After") == "" {
				t.Fatal("missing Retry-After")
			}
			if len(e.writer.records) != 0 {
				t.Fatal("a failed analysis was stored")
			}
		})
	}
}

func TestFeedEndpoints(t *testing.T) {
	e := newEnv(t)
	e.store.page = store.Page{Items: []store.FeedItem{{Text: "a"}}, NextCursor: "c1"}
	for _, path := range []string{"/api/comments?limit=10", "/api/moderation/flagged"} {
		rr := e.do(http.MethodGet, path, "")
		if rr.Code != 200 || !strings.Contains(rr.Body.String(), `"next_cursor":"c1"`) {
			t.Fatalf("%s: %d %s", path, rr.Code, rr.Body)
		}
	}
	if rr := e.do(http.MethodGet, "/api/comments?limit=500", ""); rr.Code != 400 {
		t.Fatalf("limit 500: %d", rr.Code)
	}
	if rr := e.do(http.MethodGet, "/api/comments?cursor=bad", ""); rr.Code != 400 {
		t.Fatalf("bad cursor: %d", rr.Code)
	}
	e.store.page = store.Page{}
	if rr := e.do(http.MethodGet, "/api/comments", ""); !strings.Contains(rr.Body.String(), `"items":[]`) {
		t.Fatalf("empty feed must be [] not null: %s", rr.Body)
	}
	e.store.fail = errors.New("db down")
	if rr := e.do(http.MethodGet, "/api/comments", ""); rr.Code != 503 || errorCode(t, rr) != "database_unavailable" {
		t.Fatalf("db down: %d %s", rr.Code, rr.Body)
	}
}

func TestStatsQueryIsCachedForOneSecond(t *testing.T) {
	e := newEnv(t)
	e.store.counts = store.DashboardCounts{Comments: 7}
	for range 20 {
		if rr := e.do(http.MethodGet, "/api/stats", ""); rr.Code != 200 {
			t.Fatalf("%d %s", rr.Code, rr.Body)
		}
	}
	if e.store.countsN != 1 {
		t.Fatalf("dashboard query ran %d times for 20 polls", e.store.countsN)
	}
	rr := e.do(http.MethodGet, "/api/stats", "")
	var body statsResponse
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil || body.Database.Comments != 7 || body.Queue.QueueCapacity != 256 {
		t.Fatalf("stats = %s", rr.Body)
	}
	if _, ok := body.Latency["request"]; !ok {
		t.Fatal("latency summary missing")
	}
}

func TestHealthReportsEachComponent(t *testing.T) {
	e := newEnv(t)
	rr := e.do(http.MethodGet, "/api/health", "")
	var body healthResponse
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if rr.Code != 200 || body.Status != "ok" || body.Postgres.Status != "ok" || body.Python.Status != "ok" {
		t.Fatalf("health = %s", rr.Body)
	}
	e.store.fail = errors.New("down")
	rr = e.do(http.MethodGet, "/api/health", "")
	_ = json.Unmarshal(rr.Body.Bytes(), &body)
	if rr.Code != 200 || body.Status != "degraded" || body.Postgres.Status != "down" {
		t.Fatalf("health with db down = %s", rr.Body)
	}
}

func TestUnknownAPIPathIsJSON404(t *testing.T) {
	e := newEnv(t)
	rr := e.do(http.MethodGet, "/api/nope", "")
	if rr.Code != 404 || errorCode(t, rr) != "not_found" {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
}

func TestConcurrentRequestsAreSafe(t *testing.T) {
	e := newEnv(t)
	sid := e.session(t)
	var wg sync.WaitGroup
	for i := range 50 {
		wg.Go(func() {
			req := httptest.NewRequest(http.MethodPost, "/api/comments",
				bytes.NewReader([]byte(fmt.Sprintf(`{"session_id":%q,"text":"metin %d"}`, sid, i%5))))
			rr := httptest.NewRecorder()
			e.mux.ServeHTTP(rr, req)
			if rr.Code != http.StatusCreated {
				t.Errorf("%d %s", rr.Code, rr.Body)
			}
		})
	}
	wg.Wait()
}

func TestCommentResponseCarriesDisplayNormalizationAndMarker(t *testing.T) {
	e := newEnv(t)
	e.api.Inference = fakeInference{hash: "h", representative: true}
	e.analyzer.norm = json.RawMessage(`{"text":"Seni bitireceğim","changes":[{"code":"LEET","from_span":[6,7],"to_span":[6,7],"from":"1","to":"i"}]}`)
	sid := e.session(t)
	body := fmt.Sprintf(`{"session_id":%q,"text":"Seni b1tireceğim"}`, sid)
	rr := e.do(http.MethodPost, "/api/comments", body)
	var resp struct {
		Normalization  *struct{ Text string } `json:"normalization"`
		Representative bool                   `json:"representative"`
		Display        struct {
			CategoriesTotal      int                     `json:"categories_total"`
			CategoriesEvaluated  int                     `json:"categories_evaluated"`
			CategoriesHidden     int                     `json:"categories_hidden"`
			PatternsCheckedOther *int                    `json:"patterns_checked_other"`
			ContentMargins       []*float64              `json:"content_margins"`
			Normalization        *struct{ Replaced int } `json:"normalization"`
		} `json:"display"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	d := resp.Display
	if !resp.Representative || resp.Normalization == nil || resp.Normalization.Text != "Seni bitireceğim" {
		t.Fatalf("response = %s", rr.Body)
	}
	if d.CategoriesTotal != 16 || d.CategoriesEvaluated != 5 || d.CategoriesHidden != 4 || d.PatternsCheckedOther == nil || *d.PatternsCheckedOther != 11 ||
		len(d.ContentMargins) != 2 || d.Normalization == nil || d.Normalization.Replaced != 1 {
		t.Fatalf("display = %s", rr.Body)
	}

	// A cache hit returns the same normalization.
	rr = e.do(http.MethodPost, "/api/comments", body)
	if !strings.Contains(rr.Body.String(), `"cache_hit":true`) || !strings.Contains(rr.Body.String(), "Seni bitireceğim") {
		t.Fatalf("cached response lost normalization: %s", rr.Body)
	}
}

func TestNoNormalizationIsNull(t *testing.T) {
	e := newEnv(t)
	sid := e.session(t)
	rr := e.do(http.MethodPost, "/api/comments", fmt.Sprintf(`{"session_id":%q,"text":"x"}`, sid))
	if !strings.Contains(rr.Body.String(), `"normalization":null`) {
		t.Fatalf("want normalization null: %s", rr.Body)
	}
}

func TestCategoriesEndpoint(t *testing.T) {
	e := newEnv(t)
	e.api.Inference = fakeInference{hash: "h", degraded: []string{"m2_deobf", "m6_target", "m1_lexicon", "m3_encoder", "m5_sarcasm"}, representative: true}
	rr := e.do(http.MethodGet, "/api/categories", "")
	if rr.Code != 200 {
		t.Fatalf("%d %s", rr.Code, rr.Body)
	}
	var body struct {
		Placeholder    bool                  `json:"placeholder"`
		Representative bool                  `json:"representative"`
		Categories     []categories.Category `json:"categories"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	if len(body.Categories) != 16 || !body.Placeholder || !body.Representative || body.Categories[0].Status != "stub" {
		t.Fatalf("categories = %s", rr.Body)
	}
}
