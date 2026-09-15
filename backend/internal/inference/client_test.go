package inference

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

const validResult = `{"text":"x","verdict":"review","content":[],"guards":[],"explanation":"e","latency_ms":1,"trace_id":"t","artifact_hash":"h1","signals":{"pipeline":{"degraded":[]}}}`

func newClient(url string) *Client {
	return New(Config{URL: url, HealthTimeout: time.Second, BreakerFailures: 3, BreakerOpenFor: time.Hour})
}

func items(ids ...string) []domain.PredictItem {
	out := make([]domain.PredictItem, len(ids))
	for i, id := range ids {
		out[i] = domain.PredictItem{ID: id, Text: "text " + id}
	}
	return out
}

func TestPredictBatchParsesPerItemResults(t *testing.T) {
	var got batchRequest
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/predict_batch" || r.Method != http.MethodPost {
			t.Errorf("unexpected %s %s", r.Method, r.URL.Path)
		}
		_ = json.NewDecoder(r.Body).Decode(&got)
		_, _ = w.Write([]byte(`{"artifact_hash":"h1","results":[
			{"id":"a","ok":true,"result":` + validResult + `},
			{"id":"b","ok":false,"error":"boom"},
			{"id":"c","ok":true,"result":{"verdict":"hide"}}]}`))
	}))
	defer srv.Close()

	c := newClient(srv.URL)
	out, err := c.PredictBatch(context.Background(), items("a", "b", "c"))
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Items) != 3 || got.Items[1].ID != "b" {
		t.Fatalf("request items = %+v", got.Items)
	}
	if len(out) != 3 {
		t.Fatalf("%d outcomes", len(out))
	}
	if out[0].Err != nil || len(out[0].Result) == 0 {
		t.Errorf("a: %+v", out[0])
	}
	var itemErr *ItemError
	if !errors.As(out[1].Err, &itemErr) {
		t.Errorf("b: want ItemError, got %v", out[1].Err)
	}
	if !errors.As(out[2].Err, &itemErr) {
		t.Errorf("c: invalid verdict must be an item error, got %v", out[2].Err)
	}
	if c.ArtifactHash() != "h1" {
		t.Errorf("artifact hash = %q", c.ArtifactHash())
	}
}

func TestResultIsPassedThroughUnchanged(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"results":[{"id":"a","ok":true,"result":` + validResult + `}]}`))
	}))
	defer srv.Close()
	out, err := newClient(srv.URL).PredictBatch(context.Background(), items("a"))
	if err != nil {
		t.Fatal(err)
	}
	if string(out[0].Result) != validResult {
		t.Fatalf("result was rewritten:\n%s", out[0].Result)
	}
}

func TestLoading503FailsFastAfterwards(t *testing.T) {
	var calls atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()
	c := newClient(srv.URL)

	if _, err := c.PredictBatch(context.Background(), items("a")); !errors.Is(err, ErrLoading) {
		t.Fatalf("want ErrLoading, got %v", err)
	}
	// Breaker is open now: no second request reaches Python.
	if _, err := c.PredictBatch(context.Background(), items("b")); err == nil {
		t.Fatal("want fast failure while loading")
	}
	if n := calls.Load(); n != 1 {
		t.Fatalf("python called %d times, want 1", n)
	}
}

func TestBreakerOpensAfterConsecutiveFailures(t *testing.T) {
	var calls atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls.Add(1)
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()
	c := newClient(srv.URL)

	for range 3 {
		if _, err := c.PredictBatch(context.Background(), items("a")); !errors.Is(err, ErrUnavailable) {
			t.Fatalf("want ErrUnavailable, got %v", err)
		}
	}
	start := time.Now()
	_, err := c.PredictBatch(context.Background(), items("a"))
	if !errors.Is(err, ErrUnavailable) {
		t.Fatalf("want ErrUnavailable, got %v", err)
	}
	if time.Since(start) > 20*time.Millisecond {
		t.Fatal("open breaker must fail fast")
	}
	if n := calls.Load(); n != 3 {
		t.Fatalf("python called %d times, want 3", n)
	}
	if c.Health().Breaker != BreakerOpen {
		t.Fatalf("breaker = %s", c.Health().Breaker)
	}
}

func TestDownServiceIsUnavailableNotHanging(t *testing.T) {
	srv := httptest.NewServer(http.NotFoundHandler())
	url := srv.URL
	srv.Close() // nothing listens any more

	c := newClient(url)
	start := time.Now()
	if _, err := c.PredictBatch(context.Background(), items("a")); !errors.Is(err, ErrUnavailable) {
		t.Fatalf("want ErrUnavailable, got %v", err)
	}
	if time.Since(start) > 3*time.Second {
		t.Fatal("connection refused must fail quickly")
	}
}

func TestContextDeadlineBoundsTheCall(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Read the body so the server can notice the client hanging up, and
		// never wait forever: srv.Close waits for this handler to return.
		_, _ = io.Copy(io.Discard, r.Body)
		select {
		case <-r.Context().Done():
		case <-time.After(2 * time.Second):
		}
	}))
	defer srv.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	start := time.Now()
	_, err := newClient(srv.URL).PredictBatch(ctx, items("a"))
	if !errors.Is(err, context.DeadlineExceeded) || !errors.Is(err, ErrUnavailable) {
		t.Fatalf("want deadline + unavailable, got %v", err)
	}
	if time.Since(start) > time.Second {
		t.Fatal("hung Python must be cut off by the context")
	}
}

func TestHealthOKClosesBreakerAndRecordsHash(t *testing.T) {
	var healthy atomic.Bool
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/health" {
			if healthy.Load() {
				_, _ = w.Write([]byte(`{"status":"ok","artifact_hash":"h2","degraded_modules":["m3_encoder"]}`))
			} else {
				_, _ = w.Write([]byte(`{"status":"loading"}`))
			}
			return
		}
		_, _ = w.Write([]byte(`{"results":[{"id":"a","ok":true,"result":` + validResult + `}]}`))
	}))
	defer srv.Close()
	c := newClient(srv.URL)

	h := c.CheckHealth(context.Background())
	if h.Status != "loading" || h.Breaker != BreakerOpen {
		t.Fatalf("loading health = %+v", h)
	}
	if _, err := c.PredictBatch(context.Background(), items("a")); !errors.Is(err, ErrLoading) {
		t.Fatalf("while loading: want ErrLoading, got %v", err)
	}

	healthy.Store(true)
	h = c.CheckHealth(context.Background())
	if h.Status != "ok" || h.Breaker != BreakerClosed || h.ArtifactHash != "h2" || len(h.DegradedModules) != 1 {
		t.Fatalf("ok health = %+v", h)
	}
	if _, err := c.PredictBatch(context.Background(), items("a")); err != nil {
		t.Fatalf("after recovery: %v", err)
	}
}

func TestHealthUnreachable(t *testing.T) {
	c := newClient("http://127.0.0.1:1")
	h := c.CheckHealth(context.Background())
	if h.Status != "unreachable" || h.Breaker != BreakerOpen {
		t.Fatalf("health = %+v", h)
	}
}

func TestBreakerHalfOpenAllowsOneTrial(t *testing.T) {
	now := time.Unix(0, 0)
	b := NewBreaker(1, time.Second)
	b.now = func() time.Time { return now }

	b.Failure()
	if b.Allow() {
		t.Fatal("open breaker allowed a call")
	}
	now = now.Add(time.Second)
	if !b.Allow() {
		t.Fatal("half-open breaker refused the trial call")
	}
	if b.Allow() {
		t.Fatal("half-open breaker allowed a second concurrent trial")
	}
	b.Failure() // trial failed: open again
	if b.Allow() {
		t.Fatal("breaker should re-open after a failed trial")
	}
	now = now.Add(time.Second)
	if !b.Allow() {
		t.Fatal("no trial after second open period")
	}
	b.Success()
	if b.State() != BreakerClosed || !b.Allow() {
		t.Fatal("successful trial must close the breaker")
	}
}
