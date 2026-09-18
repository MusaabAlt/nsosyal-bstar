package handlers

import (
	"context"
	"errors"
	"math"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/categories"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/respond"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
)

// The moderation panel (ATI-SOSYAL Paneli):
//
//	GET  /api/panel/overview?range=live|today|week   dashboard numbers, per-category series
//	GET  /api/panel/items?status&detected&code&q&limit&cursor
//	GET  /api/panel/items/{id}                       one comment with actions and context
//	GET  /api/panel/queue-counts                     queue tab counts (sidebar badge)
//	POST /api/panel/actions                          record moderator actions
//	GET  /api/panel/events?kind&q&limit&cursor       history timeline
//	GET  /api/panel/metrics                          request series for Sistem Sağlığı
//
// Every number is counted from stored data. Percentages and changes are
// computed here, so the UI computes nothing; a value that cannot be computed
// (nothing to compare with) is null, never 0.

type PanelStore interface {
	Items(ctx context.Context, f store.ItemFilter) (store.ItemPage, error)
	Item(ctx context.Context, id uuid.UUID) (store.ItemDetail, error)
	QueueCounts(ctx context.Context) (store.QueueCounts, error)
	AddActions(ctx context.Context, ids []uuid.UUID, action string, sessionID *uuid.UUID) ([]uuid.UUID, error)
	Events(ctx context.Context, f store.EventFilter) (store.EventPage, error)
	Overview(ctx context.Context, r store.Range, codes []string) (store.OverviewCounts, error)
	ActiveDevices(ctx context.Context, window time.Duration) (int64, error)
	RequestSeries(ctx context.Context, start time.Time, width time.Duration, buckets int) (store.MetricSeries, error)
}

const (
	// activeDevicesWindow is how recently a device must have sent a comment to count as active.
	activeDevicesWindow = 5 * time.Minute
	// slowP95MS marks the analysis latency as slow on Sistem Sağlığı.
	slowP95MS = 200.0
	// maxActionIDs bounds one bulk action.
	maxActionIDs = 100
)

func (a *API) registerPanel(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/panel/overview", a.panelOverview)
	mux.HandleFunc("GET /api/panel/items", a.panelItems)
	mux.HandleFunc("GET /api/panel/items/{id}", a.panelItem)
	mux.HandleFunc("GET /api/panel/queue-counts", a.panelQueueCounts)
	mux.HandleFunc("POST /api/panel/actions", a.panelActions)
	mux.HandleFunc("GET /api/panel/events", a.panelEvents)
	mux.HandleFunc("GET /api/panel/metrics", a.panelMetrics)
}

func (a *API) dbUnavailable(w http.ResponseWriter, what string, err error) {
	a.Log.Error("panel query", "query", what, "error", err)
	respond.Error(w, http.StatusServiceUnavailable, respond.CodeDatabase, "database unavailable, retry shortly", 1000)
}

// ----------------------------------------------------------------- overview

// rangeFor splits the chosen window into buckets. "today" and "week" follow
// the server's local calendar, which is the demo room's.
func rangeFor(name string, now time.Time) (store.Range, bool) {
	switch name {
	case "", "live":
		end := now.Truncate(5 * time.Minute).Add(5 * time.Minute)
		return store.Range{Start: end.Add(-time.Hour), Now: now, Bucket: 5 * time.Minute, Buckets: 12}, true
	case "today":
		y, m, d := now.Date()
		return store.Range{Start: time.Date(y, m, d, 0, 0, 0, 0, now.Location()), Now: now, Bucket: time.Hour, Buckets: 24}, true
	case "week":
		y, m, d := now.Date()
		start := time.Date(y, m, d-6, 0, 0, 0, 0, now.Location())
		return store.Range{Start: start, Now: now, Bucket: 24 * time.Hour, Buckets: 7}, true
	}
	return store.Range{}, false
}

// changePct is the change from previous to current in percent, one decimal;
// null when there is nothing to compare with.
func changePct(p store.Pair) *float64 {
	if p.Previous == 0 {
		return nil
	}
	v := math.Round(float64(p.Current-p.Previous)/float64(p.Previous)*1000) / 10
	return &v
}

func sharePct(part, whole int64) *float64 {
	if whole == 0 {
		return nil
	}
	v := math.Round(float64(part)/float64(whole)*1000) / 10
	return &v
}

type kpi struct {
	Value int64 `json:"value"`
	// Previous is the count for the same stretch of the window before.
	Previous  *int64   `json:"previous,omitempty"`
	ChangePct *float64 `json:"change_pct"`
	SharePct  *float64 `json:"share_pct,omitempty"`
}

type overviewCategory struct {
	categories.Category
	Total   int64   `json:"total"`
	Buckets []int64 `json:"buckets"`
}

type overviewSystem struct {
	ArtifactHash    string   `json:"artifact_hash"`
	PythonStatus    string   `json:"python_status"`
	LatencyP95MS    *float64 `json:"latency_p95_ms"`
	LatencyWindow   string   `json:"latency_window"`
	ActiveDevices   *int64   `json:"active_devices"`
	DevicesWindow   string   `json:"active_devices_window"`
	LiveCategories  int      `json:"live_categories"`
	TotalCategories int      `json:"total_categories"`
}

type overviewResponse struct {
	Range          string               `json:"range"`
	Start          time.Time            `json:"start"`
	Now            time.Time            `json:"now"`
	BucketSeconds  int                  `json:"bucket_seconds"`
	BucketStarts   []time.Time          `json:"bucket_starts"`
	Analysed       kpi                  `json:"analysed"`
	Detected       kpi                  `json:"detected"`
	Automatic      kpi                  `json:"automatic"`
	Verdicts       store.VerdictCounts  `json:"verdicts"`
	Pending        store.QueueCounts    `json:"queue"`
	Categories     []overviewCategory   `json:"categories"`
	CategoriesErr  string               `json:"categories_error,omitempty"`
	Patterns       []store.PatternCount `json:"patterns"`
	System         overviewSystem       `json:"system"`
	Representative bool                 `json:"representative"`
}

// overviewCache answers repeated polls of the same range from memory for a
// second: many open dashboards cost one set of queries per second.
type overviewCache struct {
	mu      sync.Mutex
	entries map[string]overviewCacheEntry
}

type overviewCacheEntry struct {
	at   time.Time
	resp overviewResponse
}

func (a *API) panelOverview(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("range")
	if name == "" {
		name = "live"
	}
	now := time.Now()
	rng, ok := rangeFor(name, now)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "range must be live, today or week", 0)
		return
	}

	a.overview.mu.Lock()
	defer a.overview.mu.Unlock()
	if e, hit := a.overview.entries[name]; hit && now.Sub(e.at) < time.Second {
		respond.JSON(w, http.StatusOK, e.resp)
		return
	}

	h := a.Inference.Health()
	resp := overviewResponse{
		Range: name, Start: rng.Start, Now: now, BucketSeconds: int(rng.Bucket.Seconds()),
		Categories: []overviewCategory{}, Patterns: []store.PatternCount{},
		Representative: h.Representative,
	}
	for i := range rng.Buckets {
		resp.BucketStarts = append(resp.BucketStarts, rng.Start.Add(rng.Bucket*time.Duration(i)))
	}

	list, err := a.Categories.List(h.Capabilities, h.DegradedModules, h.Status == "ok")
	if err != nil {
		a.Log.Error("categories", "error", err)
		resp.CategoriesErr = "category configuration could not be read"
	}
	codes := make([]string, 0, len(list.Categories))
	for _, c := range list.Categories {
		codes = append(codes, c.Code)
	}

	counts, err := a.Panel.Overview(r.Context(), rng, codes)
	if err != nil {
		a.dbUnavailable(w, "overview", err)
		return
	}
	queue, err := a.Panel.QueueCounts(r.Context())
	if err != nil {
		a.dbUnavailable(w, "queue counts", err)
		return
	}
	resp.Pending = queue
	resp.Analysed = kpi{Value: counts.Analysed.Current, Previous: &counts.Analysed.Previous, ChangePct: changePct(counts.Analysed)}
	resp.Detected = kpi{
		Value: counts.Detected.Current, Previous: &counts.Detected.Previous, ChangePct: changePct(counts.Detected),
		SharePct: sharePct(counts.Detected.Current, counts.Analysed.Current),
	}
	resp.Automatic = kpi{Value: counts.Automatic.Current, Previous: &counts.Automatic.Previous, ChangePct: changePct(counts.Automatic)}
	resp.Verdicts = counts.Verdicts
	resp.Patterns = counts.Patterns

	live := 0
	for i, c := range list.Categories {
		if c.Status == "live" {
			live++
		}
		resp.Categories = append(resp.Categories, overviewCategory{
			Category: c, Total: counts.Series[i].Total, Buckets: counts.Series[i].Buckets,
		})
	}

	sys := overviewSystem{
		ArtifactHash: h.ArtifactHash, PythonStatus: h.Status,
		LatencyP95MS:   a.Metrics.Request.Summary().P95MS,
		LatencyWindow:  a.Metrics.Request.Summary().Window,
		DevicesWindow:  activeDevicesWindow.String(),
		LiveCategories: live, TotalCategories: len(list.Categories),
	}
	if n, err := a.Panel.ActiveDevices(r.Context(), activeDevicesWindow); err == nil {
		sys.ActiveDevices = &n
	} else {
		a.Log.Warn("active devices", "error", err)
	}
	resp.System = sys

	if a.overview.entries == nil {
		a.overview.entries = map[string]overviewCacheEntry{}
	}
	a.overview.entries[name] = overviewCacheEntry{at: now, resp: resp}
	respond.JSON(w, http.StatusOK, resp)
}

// -------------------------------------------------------------------- items

func (a *API) panelItems(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	limit, ok := parseLimit(r)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "limit must be between 1 and 100", 0)
		return
	}
	f := store.ItemFilter{
		Status:       query.Get("status"),
		DetectedOnly: query.Get("detected") == "true",
		Code:         query.Get("code"),
		Query:        strings.TrimSpace(query.Get("q")),
		Limit:        limit,
		Cursor:       query.Get("cursor"),
	}
	switch f.Status {
	case "", store.StatusPending, store.StatusReviewed, store.StatusAuto:
	default:
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "status must be pending, reviewed or auto", 0)
		return
	}
	if len([]rune(f.Query)) > 200 {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "q must be at most 200 characters", 0)
		return
	}
	page, err := a.Panel.Items(r.Context(), f)
	switch {
	case errors.Is(err, store.ErrBadCursor):
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "invalid cursor", 0)
	case err != nil:
		a.dbUnavailable(w, "items", err)
	default:
		respond.JSON(w, http.StatusOK, page)
	}
}

func (a *API) panelItem(w http.ResponseWriter, r *http.Request) {
	id, err := uuid.Parse(r.PathValue("id"))
	if err != nil {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "id must be a comment id", 0)
		return
	}
	detail, err := a.Panel.Item(r.Context(), id)
	switch {
	case errors.Is(err, store.ErrNotFound):
		respond.Error(w, http.StatusNotFound, respond.CodeNotFound, "comment not found", 0)
	case err != nil:
		a.dbUnavailable(w, "item", err)
	default:
		respond.JSON(w, http.StatusOK, detail)
	}
}

func (a *API) panelQueueCounts(w http.ResponseWriter, r *http.Request) {
	counts, err := a.Panel.QueueCounts(r.Context())
	if err != nil {
		a.dbUnavailable(w, "queue counts", err)
		return
	}
	respond.JSON(w, http.StatusOK, counts)
}

// ------------------------------------------------------------------ actions

type actionRequest struct {
	CommentIDs []string `json:"comment_ids"`
	Action     string   `json:"action"`
	SessionID  string   `json:"session_id"`
}

type actionResponse struct {
	Recorded int         `json:"recorded"`
	Missing  []uuid.UUID `json:"missing"`
}

func (a *API) panelActions(w http.ResponseWriter, r *http.Request) {
	var req actionRequest
	if !a.decode(w, r, &req) {
		return
	}
	if !store.ValidModeratorAction(req.Action) {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "action must be approve, hide, remove, queue or false_positive", 0)
		return
	}
	if len(req.CommentIDs) == 0 || len(req.CommentIDs) > maxActionIDs {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "comment_ids must list 1 to "+strconv.Itoa(maxActionIDs)+" ids", 0)
		return
	}
	seen := map[uuid.UUID]bool{}
	ids := make([]uuid.UUID, 0, len(req.CommentIDs))
	for _, raw := range req.CommentIDs {
		id, err := uuid.Parse(raw)
		if err != nil {
			respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "comment_ids must be comment ids", 0)
			return
		}
		if !seen[id] {
			seen[id] = true
			ids = append(ids, id)
		}
	}
	var session *uuid.UUID
	if req.SessionID != "" {
		id, err := uuid.Parse(req.SessionID)
		if err != nil {
			respond.Error(w, http.StatusBadRequest, respond.CodeUnknownSession, "session_id is not a valid session", 0)
			return
		}
		session = &id
	}

	missing, err := a.Panel.AddActions(r.Context(), ids, req.Action, session)
	if err != nil {
		a.dbUnavailable(w, "add actions", err)
		return
	}
	if len(missing) == len(ids) {
		// Comments are stored a moment after analysis; a retry usually succeeds.
		respond.Error(w, http.StatusNotFound, respond.CodeNotFound, "comment not stored yet, retry shortly", 500)
		return
	}
	a.overview.mu.Lock()
	a.overview.entries = nil // queue counts changed
	a.overview.mu.Unlock()
	if missing == nil {
		missing = []uuid.UUID{}
	}
	respond.JSON(w, http.StatusOK, actionResponse{Recorded: len(ids) - len(missing), Missing: missing})
}

// ------------------------------------------------------------------- events

func (a *API) panelEvents(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	limit, ok := parseLimit(r)
	if !ok {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "limit must be between 1 and 100", 0)
		return
	}
	f := store.EventFilter{Kind: query.Get("kind"), Query: strings.TrimSpace(query.Get("q")), Limit: limit, Cursor: query.Get("cursor")}
	switch f.Kind {
	case "", "moderator", "system":
	default:
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "kind must be moderator or system", 0)
		return
	}
	if len([]rune(f.Query)) > 200 {
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "q must be at most 200 characters", 0)
		return
	}
	page, err := a.Panel.Events(r.Context(), f)
	switch {
	case errors.Is(err, store.ErrBadCursor):
		respond.Error(w, http.StatusBadRequest, respond.CodeBadRequest, "invalid cursor", 0)
	case err != nil:
		a.dbUnavailable(w, "events", err)
	default:
		respond.JSON(w, http.StatusOK, page)
	}
}

// ------------------------------------------------------------------ metrics

type metricsResponse struct {
	store.MetricSeries
	Now time.Time `json:"now"`
	// Requests per second over the last complete minute; null without a complete minute of data.
	RequestsPerSecond *float64 `json:"requests_per_second"`
	// 5xx share of all API requests in the series, percent; null without requests.
	ErrorRatePct  *float64 `json:"error_rate_pct"`
	ActiveDevices *int64   `json:"active_devices"`
	DevicesWindow string   `json:"active_devices_window"`
	// Latency of POST /api/comments from memory (last few minutes).
	Latency   latencySummary `json:"latency"`
	SlowP95MS float64        `json:"slow_p95_ms"`
	// Slow is true when the recent analysis p95 is above SlowP95MS.
	Slow bool `json:"slow"`
}

type latencySummary struct {
	Samples int      `json:"samples"`
	P50MS   *float64 `json:"p50_ms"`
	P95MS   *float64 `json:"p95_ms"`
	Window  string   `json:"window"`
}

func (a *API) panelMetrics(w http.ResponseWriter, r *http.Request) {
	const buckets = 30
	now := time.Now()
	start := now.Truncate(time.Minute).Add(-(buckets - 1) * time.Minute)
	series, err := a.Panel.RequestSeries(r.Context(), start, time.Minute, buckets)
	if err != nil {
		a.dbUnavailable(w, "request series", err)
		return
	}
	resp := metricsResponse{MetricSeries: series, Now: now, DevicesWindow: activeDevicesWindow.String(), SlowP95MS: slowP95MS}

	// The last bucket is the running minute; the one before it is complete.
	if len(series.AllRequests) >= 2 {
		v := math.Round(float64(series.AllRequests[len(series.AllRequests)-2].Requests)/60*10) / 10
		resp.RequestsPerSecond = &v
	}
	var total, errs int64
	for _, b := range series.AllRequests {
		total += b.Requests
		errs += b.Errors
	}
	if total > 0 {
		v := math.Round(float64(errs)/float64(total)*10000) / 100
		resp.ErrorRatePct = &v
	}

	if n, err := a.Panel.ActiveDevices(r.Context(), activeDevicesWindow); err == nil {
		resp.ActiveDevices = &n
	} else {
		a.Log.Warn("active devices", "error", err)
	}
	s := a.Metrics.Request.Summary()
	resp.Latency = latencySummary{Samples: s.Samples, P50MS: s.P50MS, P95MS: s.P95MS, Window: s.Window}
	resp.Slow = s.P95MS != nil && *s.P95MS > slowP95MS
	respond.JSON(w, http.StatusOK, resp)
}
