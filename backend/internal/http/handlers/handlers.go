// Package handlers implements the /api endpoints.
//
//	POST /api/sessions               create an anonymous session
//	POST /api/comments               submit and analyse a comment
//	GET  /api/comments?limit&cursor  feed with decisions
//	GET  /api/moderation/flagged     non-clean comments with per-type reasons
//	GET  /api/stats                  live numbers for the dashboard
//	GET  /api/health                 Go, Python and Postgres status
//	GET  /api/categories             what the AI detects, with threshold, action and status
//	/api/panel/*                     the moderation panel (panel.go)
package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/netip"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/google/uuid"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/cache"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/categories"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/display"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/respond"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/inference"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/metrics"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/queue"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
)

// --------------------------------------------------------------- dependencies

type Store interface {
	CreateSession(ctx context.Context, nickname string, ip netip.Addr) (domain.Session, error)
	SessionExists(ctx context.Context, id uuid.UUID) (bool, error)
	Feed(ctx context.Context, limit int, cursor string, flaggedOnly bool) (store.Page, error)
	DashboardCounts(ctx context.Context) (store.DashboardCounts, error)
	Ping(ctx context.Context) error
}

type Writer interface {
	EnqueueAnalysis(domain.AnalysisRecord) bool
	Stats() store.WriterStats
}

type Analyzer interface {
	Submit(ctx context.Context, item domain.PredictItem) (queue.Result, error)
	Stats() queue.Stats
}

type Inference interface {
	ArtifactHash() string
	Health() inference.Health
}

type Categories interface {
	List(capabilities []domain.Capability, degraded []string, pythonKnown bool) (categories.List, error)
}

// CachedAnalysis is what the cache keeps for one text: the result and m2's
// optional normalization, which always travel together.
type CachedAnalysis struct {
	Result        json.RawMessage
	Normalization json.RawMessage
}

type Deps struct {
	Store      Store
	Writer     Writer
	Analyzer   Analyzer
	Inference  Inference
	Categories Categories
	// Panel serves /api/panel/*; nil leaves those routes unregistered.
	Panel        PanelStore
	Cache        *cache.LRU[CachedAnalysis]
	Metrics      *metrics.Registry
	Log          *slog.Logger
	MaxBodyBytes int64
	MaxTextChars int
	StartedAt    time.Time
}

type API struct {
	Deps
	sessions *cache.LRU[bool] // known session ids, so most requests skip the DB check
	stats    statsCache
	overview overviewCache
}

func New(d Deps) *API {
	if d.Log == nil {
		d.Log = slog.Default()
	}
	return &API{Deps: d, sessions: cache.New[bool](20000, time.Hour)}
}

// Register adds every /api route to mux.
func (a *API) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /api/sessions", a.createSession)
	mux.HandleFunc("POST /api/comments", a.createComment)
	mux.HandleFunc("GET /api/comments", a.listComments)
	mux.HandleFunc("GET /api/moderation/flagged", a.listFlagged)
	mux.HandleFunc("GET /api/stats", a.getStats)
	mux.HandleFunc("GET /api/health", a.getHealth)
	mux.HandleFunc("GET /api/categories", a.getCategories)
	if a.Panel != nil {
		a.registerPanel(mux)
	}
	mux.HandleFunc("/api/", func(w http.ResponseWriter, r *http.Request) {
		respond.Error(w, http.StatusNotFound, respond.CodeNotFound, "no such endpoint", 0)
	})
}

// ------------------------------------------------------------------ helpers

// decode reads a bounded JSON body into v, answering the error itself.
func (a *API) decode(w http.ResponseWriter, r *http.Request, v any) bool {
	body := http.MaxBytesReader(w, r.Body, a.MaxBodyBytes)
	dec := json.NewDecoder(body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		var tooBig *http.MaxBytesError
		if errors.As(err, &tooBig) {
			respond.Error(w, http.StatusRequestEntityTooLarge, respond.CodeBodyTooLarge, "request body too large", 0)
		} else {
			respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "body must be a JSON object with the documented fields", 0)
		}
		return false
	}
	if _, err := dec.Token(); err != io.EOF {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "body must contain exactly one JSON object", 0)
		return false
	}
	return true
}

func clientAddr(r *http.Request) netip.Addr {
	if ap, err := netip.ParseAddrPort(r.RemoteAddr); err == nil {
		return ap.Addr().Unmap()
	}
	if addr, err := netip.ParseAddr(r.RemoteAddr); err == nil {
		return addr
	}
	return netip.IPv4Unspecified()
}

func ms(d time.Duration) float64 { return float64(d.Microseconds()) / 1000 }

// ----------------------------------------------------------------- sessions

type createSessionRequest struct {
	Nickname string `json:"nickname"`
}

func validNickname(s string) (string, bool) {
	s = strings.TrimSpace(s)
	n := utf8.RuneCountInString(s)
	if !utf8.ValidString(s) || n < 1 || n > 32 {
		return "", false
	}
	for _, r := range s {
		if unicode.IsControl(r) {
			return "", false
		}
	}
	return s, true
}

func (a *API) createSession(w http.ResponseWriter, r *http.Request) {
	var req createSessionRequest
	if !a.decode(w, r, &req) {
		return
	}
	nickname, ok := validNickname(req.Nickname)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeInvalidNickname, "nickname must be 1 to 32 characters", 0)
		return
	}
	s, err := a.Store.CreateSession(r.Context(), nickname, clientAddr(r))
	if err != nil {
		a.Log.Error("create session", "error", err)
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeDatabase, "could not create session, retry shortly", 1000)
		return
	}
	a.sessions.Put(s.ID.String(), true)
	respond.JSON(w, http.StatusCreated, s)
}

// ----------------------------------------------------------------- comments

type createCommentRequest struct {
	SessionID string `json:"session_id"`
	Text      string `json:"text"`
}

type commentInfo struct {
	ID        uuid.UUID `json:"id"`
	SessionID uuid.UUID `json:"session_id"`
	CreatedAt time.Time `json:"created_at"`
}

type timing struct {
	TotalMS     float64  `json:"total_ms"`
	QueueWaitMS *float64 `json:"queue_wait_ms"`
	ModelMS     *float64 `json:"model_ms"`
	BatchSize   *int     `json:"batch_size"`
	CacheHit    bool     `json:"cache_hit"`
}

type createCommentResponse struct {
	Comment commentInfo     `json:"comment"`
	Result  json.RawMessage `json:"result"`
	// Optional m2 output beside the frozen result (null until m2 provides it).
	Normalization json.RawMessage `json:"normalization"`
	// Numbers docs/UI shows that the result does not carry (package display).
	Display display.Display `json:"display"`
	// true while the model service returns sample data (Temsili veri, design-system 4.19).
	Representative bool   `json:"representative"`
	Timing         timing `json:"timing"`
}

// validText accepts what the model can be given: valid UTF-8, not blank, at
// most MaxTextChars characters. The text itself is never altered.
func (a *API) validText(s string) (string, bool) {
	if !utf8.ValidString(s) || strings.TrimSpace(s) == "" {
		return "", false
	}
	if utf8.RuneCountInString(s) > a.MaxTextChars {
		return "", false
	}
	return s, true
}

func (a *API) knownSession(ctx context.Context, id uuid.UUID) (bool, error) {
	if _, ok := a.sessions.Get(id.String()); ok {
		return true, nil
	}
	exists, err := a.Store.SessionExists(ctx, id)
	if err == nil && exists {
		a.sessions.Put(id.String(), true)
	}
	return exists, err
}

func (a *API) createComment(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	var req createCommentRequest
	if !a.decode(w, r, &req) {
		return
	}
	sessionID, err := uuid.Parse(req.SessionID)
	if err != nil {
		respond.Error(w, http.StatusBadRequest, respond.CodeUnknownSession, "session_id is not a valid session", 0)
		return
	}
	text, ok := a.validText(req.Text)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeInvalidText, "text must be 1 to "+strconv.Itoa(a.MaxTextChars)+" characters of valid UTF-8", 0)
		return
	}
	known, err := a.knownSession(r.Context(), sessionID)
	if err != nil {
		a.Log.Error("check session", "error", err)
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeDatabase, "database unavailable, retry shortly", 1000)
		return
	}
	if !known {
		respond.Error(w, http.StatusBadRequest, respond.CodeUnknownSession, "session not found; create one with POST /api/sessions", 0)
		return
	}

	commentID := uuid.Must(uuid.NewV7())
	createdAt := time.Now().UTC()
	var (
		result        json.RawMessage
		normalization json.RawMessage
		tm            timing
		fromHash      = a.Inference.ArtifactHash()
		key           string
	)

	if fromHash != "" {
		key = cache.Key(text, fromHash)
		if cached, hit := a.Cache.Get(key); hit {
			result, normalization, tm.CacheHit = cached.Result, cached.Normalization, true
		}
	}

	if !tm.CacheHit {
		res, err := a.Analyzer.Submit(r.Context(), domain.PredictItem{ID: commentID.String(), Text: text})
		if err != nil {
			a.analysisError(w, r, err)
			return
		}
		result = res.Outcome.Result
		normalization = res.Outcome.Normalization
		qw, mm, bs := ms(res.QueueWait), ms(res.ModelLatency), res.BatchSize
		tm.QueueWaitMS, tm.ModelMS, tm.BatchSize = &qw, &mm, &bs
		a.Metrics.QueueWait.Observe(qw)
		a.Metrics.Model.Observe(mm)
	}

	summary, err := domain.ParseResult(result)
	if err != nil {
		a.Log.Error("unreadable analysis result", "comment_id", commentID, "error", err)
		respond.Error(w, http.StatusBadGateway, respond.CodeModelError, "the model returned an unreadable result", 0)
		return
	}
	if !tm.CacheHit && summary.Verdict != nil {
		// A failed decision (verdict null) may be transient: never cache it.
		// Store under the same key the lookup used, so the next identical text
		// hits; fall back to the result's own version when none was known yet.
		if key == "" && summary.ArtifactHash != "" {
			key = cache.Key(text, summary.ArtifactHash)
		}
		if key != "" {
			a.Cache.Put(key, CachedAnalysis{Result: result, Normalization: normalization})
		}
	}

	sum := sha256Sum(text)
	a.Writer.EnqueueAnalysis(domain.AnalysisRecord{
		CommentID: commentID, SessionID: sessionID, IP: clientAddr(r).String(), Text: text, TextSHA256: sum,
		Result: result, Summary: summary, QueueWaitMS: tm.QueueWaitMS, FromCache: tm.CacheHit, CreatedAt: createdAt,
	})

	health := a.Inference.Health()
	disp, err := display.Build(result, normalization, health.Capabilities)
	if err != nil {
		// The result itself parsed; only the extras are unreadable. Answer
		// without them rather than failing the analysis.
		a.Log.Warn("display numbers", "comment_id", commentID, "error", err)
		normalization = nil
		disp, _ = display.Build(result, nil, health.Capabilities)
	}
	if normalization == nil {
		normalization = json.RawMessage("null")
	}

	tm.TotalMS = ms(time.Since(start))
	a.Metrics.Request.Observe(tm.TotalMS)
	respond.JSON(w, http.StatusCreated, createCommentResponse{
		Comment:        commentInfo{ID: commentID, SessionID: sessionID, CreatedAt: createdAt},
		Result:         result,
		Normalization:  normalization,
		Display:        disp,
		Representative: health.Representative,
		Timing:         tm,
	})
}

// analysisError maps queue and model failures to clear, fast answers.
func (a *API) analysisError(w http.ResponseWriter, r *http.Request, err error) {
	var itemErr *inference.ItemError
	switch {
	case errors.Is(err, queue.ErrQueueFull):
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeQueueFull, "the system is busy, retry in a moment", 2000)
	case errors.Is(err, queue.ErrClosed):
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeShuttingDown, "the server is restarting", 5000)
	case errors.Is(err, inference.ErrLoading):
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeModelLoading, "the model is loading, retry shortly", 5000)
	case errors.Is(err, context.DeadlineExceeded) && r.Context().Err() != nil:
		respond.Error(w, http.StatusGatewayTimeout, respond.CodeTimeout, "analysis took too long, retry", 2000)
	case errors.Is(err, context.Canceled):
		// The client went away; nobody reads this response.
		respond.Error(w, 499, respond.CodeTimeout, "request cancelled", 0)
	case errors.As(err, &itemErr), errors.Is(err, queue.ErrMissingResult), errors.Is(err, queue.ErrPredictorPanic):
		a.Log.Warn("model failed on item", "error", err)
		respond.Error(w, http.StatusBadGateway, respond.CodeModelError, "the model could not analyse this text", 0)
	case errors.Is(err, inference.ErrUnavailable), errors.Is(err, context.DeadlineExceeded):
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeModelUnavailable, "the model is restarting, retry shortly", 3000)
	default:
		a.Log.Error("analysis failed", "error", err)
		respond.Error(w, http.StatusInternalServerError, respond.CodeInternal, "analysis failed", 0)
	}
}

func parseLimit(r *http.Request) (int, bool) {
	raw := r.URL.Query().Get("limit")
	if raw == "" {
		return 20, true
	}
	n, err := strconv.Atoi(raw)
	if err != nil || n < 1 || n > 100 {
		return 0, false
	}
	return n, true
}

func (a *API) listComments(w http.ResponseWriter, r *http.Request) { a.feed(w, r, false) }
func (a *API) listFlagged(w http.ResponseWriter, r *http.Request)  { a.feed(w, r, true) }

func (a *API) feed(w http.ResponseWriter, r *http.Request, flagged bool) {
	limit, ok := parseLimit(r)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "limit must be between 1 and 100", 0)
		return
	}
	page, err := a.Store.Feed(r.Context(), limit, r.URL.Query().Get("cursor"), flagged)
	switch {
	case errors.Is(err, store.ErrBadCursor):
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "invalid cursor", 0)
	case err != nil:
		a.Log.Error("feed query", "flagged", flagged, "error", err)
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeDatabase, "database unavailable, retry shortly", 1000)
	default:
		if page.Items == nil {
			page.Items = []store.FeedItem{}
		}
		respond.JSON(w, http.StatusOK, page)
	}
}

// -------------------------------------------------------------------- stats

// statsCache holds the database counts for one second: many dashboards
// polling at once cost one query per second, not one per poll.
type statsCache struct {
	mu      sync.Mutex
	at      time.Time
	counts  *store.DashboardCounts
	lastErr string
}

type statsResponse struct {
	Database      *store.DashboardCounts     `json:"database"`
	DatabaseError string                     `json:"database_error,omitempty"`
	Latency       map[string]metrics.Summary `json:"latency"`
	Queue         queue.Stats                `json:"queue"`
	Cache         cache.Stats                `json:"cache"`
	Writer        store.WriterStats          `json:"writer"`
	UptimeSeconds int64                      `json:"uptime_seconds"`
}

func (a *API) dashboardCounts(ctx context.Context) (*store.DashboardCounts, string) {
	a.stats.mu.Lock()
	defer a.stats.mu.Unlock()
	if time.Since(a.stats.at) < time.Second {
		return a.stats.counts, a.stats.lastErr
	}
	counts, err := a.Store.DashboardCounts(ctx)
	a.stats.at = time.Now()
	if err != nil {
		a.Log.Warn("dashboard counts", "error", err)
		a.stats.lastErr = "database unavailable"
		// Keep the last good numbers visible, marked with the error.
		return a.stats.counts, a.stats.lastErr
	}
	a.stats.counts, a.stats.lastErr = &counts, ""
	return a.stats.counts, ""
}

func (a *API) getStats(w http.ResponseWriter, r *http.Request) {
	counts, dbErr := a.dashboardCounts(r.Context())
	respond.JSON(w, http.StatusOK, statsResponse{
		Database:      counts,
		DatabaseError: dbErr,
		Latency: map[string]metrics.Summary{
			"request":    a.Metrics.Request.Summary(),
			"queue_wait": a.Metrics.QueueWait.Summary(),
			"model":      a.Metrics.Model.Summary(),
		},
		Queue:         a.Analyzer.Stats(),
		Cache:         a.Cache.Stats(),
		Writer:        a.Writer.Stats(),
		UptimeSeconds: int64(time.Since(a.StartedAt).Seconds()),
	})
}

// ------------------------------------------------------------------- health

type componentHealth struct {
	Status    string   `json:"status"`
	LatencyMS *float64 `json:"latency_ms,omitempty"`
	Error     string   `json:"error,omitempty"`
}

type healthResponse struct {
	Status   string            `json:"status"` // ok | degraded
	Go       map[string]any    `json:"go"`
	Python   inference.Health  `json:"python"`
	Postgres componentHealth   `json:"postgres"`
	Queue    queue.Stats       `json:"queue"`
	Writer   store.WriterStats `json:"writer"`
}

// getHealth always answers 200 while Go is up: the body says which part is
// not ok, so the UI and operators can show exactly what is wrong.
func (a *API) getHealth(w http.ResponseWriter, r *http.Request) {
	pg := componentHealth{Status: "ok"}
	start := time.Now()
	ctx, cancel := context.WithTimeout(r.Context(), time.Second)
	err := a.Store.Ping(ctx)
	cancel()
	if err != nil {
		pg = componentHealth{Status: "down", Error: "postgres did not answer"}
	} else {
		l := ms(time.Since(start))
		pg.LatencyMS = &l
	}

	py := a.Inference.Health()
	status := "ok"
	if pg.Status != "ok" || py.Status != "ok" {
		status = "degraded"
	}
	respond.JSON(w, http.StatusOK, healthResponse{
		Status: status,
		Go: map[string]any{
			"status":         "ok",
			"uptime_seconds": int64(time.Since(a.StartedAt).Seconds()),
			"goroutines":     runtime.NumGoroutine(),
		},
		Python:   py,
		Postgres: pg,
		Queue:    a.Analyzer.Stats(),
		Writer:   a.Writer.Stats(),
	})
}

// --------------------------------------------------------------- categories

type categoriesResponse struct {
	categories.List
	Representative bool `json:"representative"`
}

// getCategories serves the Kategoriler page (pages-spec 3).
func (a *API) getCategories(w http.ResponseWriter, r *http.Request) {
	h := a.Inference.Health()
	known := h.Status == "ok"
	list, err := a.Categories.List(h.Capabilities, h.DegradedModules, known)
	if err != nil {
		a.Log.Error("categories", "error", err)
		respond.Error(w, http.StatusServiceUnavailable, respond.CodeInternal, "category configuration could not be read", 0)
		return
	}
	respond.JSON(w, http.StatusOK, categoriesResponse{List: list, Representative: h.Representative})
}
