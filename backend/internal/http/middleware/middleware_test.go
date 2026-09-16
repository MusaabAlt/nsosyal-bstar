package middleware

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func quiet() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func TestRecoverTurnsPanicInto500JSON(t *testing.T) {
	h := Recover(quiet())(http.HandlerFunc(func(http.ResponseWriter, *http.Request) { panic("boom") }))
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest(http.MethodGet, "/api/x", nil))
	if rr.Code != http.StatusInternalServerError {
		t.Fatalf("status %d", rr.Code)
	}
	var body struct {
		Error struct{ Code string } `json:"error"`
	}
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil || body.Error.Code != "internal_error" {
		t.Fatalf("body %s", rr.Body)
	}
}

func TestRecoverKeepsServerAlive(t *testing.T) {
	srv := httptest.NewServer(Recover(quiet())(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/panic" {
			panic("boom")
		}
		w.WriteHeader(http.StatusOK)
	})))
	defer srv.Close()
	for range 3 {
		resp, err := http.Get(srv.URL + "/panic")
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
	}
	resp, err := http.Get(srv.URL + "/ok")
	if err != nil || resp.StatusCode != http.StatusOK {
		t.Fatalf("server dead after panics: %v %v", resp, err)
	}
	resp.Body.Close()
}

func TestLimiterTokenBucket(t *testing.T) {
	now := time.Unix(0, 0)
	l := NewLimiter(1, 3, time.Minute)
	l.now = func() time.Time { return now }

	for i := range 3 {
		if ok, _ := l.Allow("a"); !ok {
			t.Fatalf("burst request %d refused", i)
		}
	}
	ok, wait := l.Allow("a")
	if ok || wait <= 0 || wait > time.Second {
		t.Fatalf("4th request: ok=%v wait=%s", ok, wait)
	}
	if ok, _ := l.Allow("b"); !ok {
		t.Fatal("another IP must have its own bucket")
	}
	now = now.Add(time.Second)
	if ok, _ := l.Allow("a"); !ok {
		t.Fatal("token not refilled after 1s")
	}
}

func TestLimiterEvictsIdleIPs(t *testing.T) {
	now := time.Unix(0, 0)
	l := NewLimiter(1, 1, time.Minute)
	l.now = func() time.Time { return now }
	l.Allow("a")
	now = now.Add(30 * time.Second)
	l.Allow("b")
	now = now.Add(45 * time.Second)
	if n := l.Evict(); n != 1 || l.Size() != 1 {
		t.Fatalf("evicted %d, size %d", n, l.Size())
	}
}

func TestRateLimitMiddleware(t *testing.T) {
	analyze := NewLimiter(0.001, 1, time.Minute)
	read := NewLimiter(0.001, 2, time.Minute)
	h := RateLimit(analyze, read)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusOK) }))

	do := func(method, path string) *httptest.ResponseRecorder {
		req := httptest.NewRequest(method, path, nil)
		req.RemoteAddr = "192.168.1.50:5000"
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, req)
		return rr
	}
	if do(http.MethodPost, "/api/comments").Code != http.StatusOK {
		t.Fatal("first POST refused")
	}
	rr := do(http.MethodPost, "/api/comments")
	if rr.Code != http.StatusTooManyRequests || rr.Header().Get("Retry-After") == "" {
		t.Fatalf("second POST: %d, Retry-After %q", rr.Code, rr.Header().Get("Retry-After"))
	}
	// Reads have their own budget, and static files are never limited.
	if do(http.MethodGet, "/api/stats").Code != http.StatusOK {
		t.Fatal("GET refused because POST budget is spent")
	}
	for range 10 {
		if do(http.MethodGet, "/assets/app.js").Code != http.StatusOK {
			t.Fatal("static file rate limited")
		}
	}
}

func TestClientIPIgnoresForwardedHeader(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.RemoteAddr = "10.0.0.7:1234"
	req.Header.Set("X-Forwarded-For", "1.2.3.4")
	if ip := ClientIP(req); ip != "10.0.0.7" {
		t.Fatalf("ip = %s", ip)
	}
}

func TestTimeoutSetsDeadline(t *testing.T) {
	var deadline time.Time
	h := Timeout(time.Second)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		deadline, _ = r.Context().Deadline()
	}))
	h.ServeHTTP(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, "/", nil))
	if until := time.Until(deadline); until <= 0 || until > time.Second {
		t.Fatalf("deadline in %s", until)
	}
}

func TestCORSOnlyForListedOrigins(t *testing.T) {
	h := CORS([]string{"http://localhost:5173"})(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusOK) }))

	req := httptest.NewRequest(http.MethodOptions, "/api/comments", nil)
	req.Header.Set("Origin", "http://localhost:5173")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusNoContent || rr.Header().Get("Access-Control-Allow-Origin") != "http://localhost:5173" {
		t.Fatalf("preflight: %d %v", rr.Code, rr.Header())
	}

	req = httptest.NewRequest(http.MethodGet, "/api/stats", nil)
	req.Header.Set("Origin", "http://evil.example")
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Fatal("unlisted origin allowed")
	}
}
