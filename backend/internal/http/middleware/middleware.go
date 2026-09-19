// Package middleware wraps every request with the protections the server
// needs to stay up under a live demo: panic recovery, per-IP rate limits,
// a request deadline, structured logging and (dev-only) CORS.
package middleware

import (
	"context"
	"log/slog"
	"net"
	"net/http"
	"runtime/debug"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/respond"
)

// Chain applies middlewares so the first one listed runs first (outermost).
func Chain(h http.Handler, mws ...func(http.Handler) http.Handler) http.Handler {
	for i := len(mws) - 1; i >= 0; i-- {
		h = mws[i](h)
	}
	return h
}

// statusRecorder remembers the status code and whether headers were sent.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
	bytes       int
}

func (r *statusRecorder) WriteHeader(code int) {
	if !r.wroteHeader {
		r.status = code
		r.wroteHeader = true
	}
	r.ResponseWriter.WriteHeader(code)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.WriteHeader(http.StatusOK)
	}
	n, err := r.ResponseWriter.Write(b)
	r.bytes += n
	return n, err
}

func (r *statusRecorder) Unwrap() http.ResponseWriter { return r.ResponseWriter }

func recorder(w http.ResponseWriter) *statusRecorder {
	if rec, ok := w.(*statusRecorder); ok {
		return rec
	}
	return &statusRecorder{ResponseWriter: w, status: http.StatusOK}
}

// Recover turns a panic in any handler into a 500 JSON response and a log
// line with the stack, so one bad request never kills the server.
func Recover(log *slog.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			rec := recorder(w)
			defer func() {
				v := recover()
				if v == nil {
					return
				}
				if v == http.ErrAbortHandler { // the server's own "stop this response" signal
					panic(v)
				}
				log.Error("panic in handler", "method", r.Method, "path", r.URL.Path, "panic", v, "stack", string(debug.Stack()))
				if !rec.wroteHeader {
					respond.Error(rec, http.StatusInternalServerError, respond.CodeInternal, "internal error", 0)
				}
			}()
			next.ServeHTTP(rec, r)
		})
	}
}

// RequestInfo is passed to the logging hook for every finished request.
type RequestInfo struct {
	Method   string
	Path     string
	Status   int
	Duration time.Duration
	IP       string
}

// Logging writes one structured line per API request and calls onDone (for
// request metrics). Static files are logged at debug level only.
func Logging(log *slog.Logger, onDone func(RequestInfo)) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rec := recorder(w)
			next.ServeHTTP(rec, r)
			info := RequestInfo{Method: r.Method, Path: r.URL.Path, Status: rec.status, Duration: time.Since(start), IP: ClientIP(r)}

			level := slog.LevelInfo
			switch {
			case !strings.HasPrefix(r.URL.Path, "/api/"):
				level = slog.LevelDebug
			case rec.status >= 500:
				level = slog.LevelError
			case rec.status >= 400:
				level = slog.LevelWarn
			}
			log.Log(r.Context(), level, "request",
				"method", info.Method, "path", info.Path, "status", info.Status,
				"duration_ms", float64(info.Duration.Microseconds())/1000, "ip", info.IP, "bytes", rec.bytes)
			if onDone != nil && strings.HasPrefix(r.URL.Path, "/api/") {
				onDone(info)
			}
		})
	}
}

// ClientIP is the TCP peer address. X-Forwarded-For is deliberately ignored:
// clients connect directly over the LAN, and a forgeable header would let
// one phone dodge its rate limit.
func ClientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

// Timeout gives every request a deadline. Handlers and everything they call
// (queue, Python, Postgres) use the request context, so nothing outlives it.
func Timeout(d time.Duration) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			ctx, cancel := context.WithTimeout(r.Context(), d)
			defer cancel()
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// CORS allows only the listed origins. In the demo the UI is served by this
// server (same origin) and the list is empty; it exists for `npm run dev`.
func CORS(origins []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		if len(origins) == 0 {
			return next
		}
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && slices.Contains(origins, origin) {
				h := w.Header()
				h.Set("Access-Control-Allow-Origin", origin)
				h.Set("Vary", "Origin")
				h.Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
				h.Set("Access-Control-Allow-Headers", "Content-Type")
				h.Set("Access-Control-Max-Age", "600")
				if r.Method == http.MethodOptions {
					w.WriteHeader(http.StatusNoContent)
					return
				}
			}
			next.ServeHTTP(w, r)
		})
	}
}

// ------------------------------------------------------------ rate limiting

// bucket is a token bucket: `rate` tokens per second, up to `burst`.
type bucket struct {
	tokens   float64
	last     time.Time
	lastSeen time.Time
}

// Limiter enforces a per-IP token bucket. Idle IPs are evicted so the map
// cannot grow without bound.
type Limiter struct {
	rate  float64
	burst float64
	idle  time.Duration
	now   func() time.Time

	mu      sync.Mutex
	buckets map[string]*bucket
}

func NewLimiter(perSecond float64, burst int, idle time.Duration) *Limiter {
	return &Limiter{rate: perSecond, burst: float64(burst), idle: idle, now: time.Now, buckets: map[string]*bucket{}}
}

// Allow takes one token for key. When refused, it returns how long until a
// token is available.
func (l *Limiter) Allow(key string) (bool, time.Duration) {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	b, ok := l.buckets[key]
	if !ok {
		b = &bucket{tokens: l.burst, last: now}
		l.buckets[key] = b
	}
	b.tokens = min(l.burst, b.tokens+now.Sub(b.last).Seconds()*l.rate)
	b.last, b.lastSeen = now, now
	if b.tokens >= 1 {
		b.tokens--
		return true, 0
	}
	wait := time.Duration((1 - b.tokens) / l.rate * float64(time.Second))
	return false, wait
}

// Evict removes IPs not seen for the idle period.
func (l *Limiter) Evict() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	cutoff := l.now().Add(-l.idle)
	n := 0
	for k, b := range l.buckets {
		if b.lastSeen.Before(cutoff) {
			delete(l.buckets, k)
			n++
		}
	}
	return n
}

// Size is the number of tracked IPs.
func (l *Limiter) Size() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return len(l.buckets)
}

// RunEviction evicts idle IPs until ctx ends.
func (l *Limiter) RunEviction(ctx context.Context) {
	t := time.NewTicker(l.idle / 2)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			l.Evict()
		}
	}
}

// RateLimit applies `analyze` to POST requests (the ones that reach the
// model or the database) and `read` to everything else under /api/.
// Static files are not limited.
func RateLimit(analyze, read *Limiter) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !strings.HasPrefix(r.URL.Path, "/api/") || r.Method == http.MethodOptions {
				next.ServeHTTP(w, r)
				return
			}
			l := read
			if r.Method == http.MethodPost {
				l = analyze
			}
			if ok, wait := l.Allow(ClientIP(r)); !ok {
				ms := max(int(wait.Milliseconds()), 100)
				respond.Error(w, http.StatusTooManyRequests, respond.CodeRateLimited, "too many requests, retry shortly", ms)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}
