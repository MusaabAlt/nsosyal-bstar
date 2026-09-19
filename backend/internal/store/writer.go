package store

import (
	"context"
	"errors"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

type WriterConfig struct {
	CommentBuffer int
	MetricsBuffer int
	BatchSize     int
	FlushInterval time.Duration
	WriteTimeout  time.Duration
}

// Writer stores results in the background so the database never slows down
// or blocks a user's response.
//
//   - Enqueue never blocks. When a buffer is full the record is dropped,
//     counted and logged: the API keeps answering.
//   - Records are written in batches with COPY, inside one transaction per batch.
//   - A batch that fails because of its data is retried row by row, so one
//     bad row does not lose the others. A batch that fails because Postgres
//     is unreachable is retried a few times with backoff, then dropped.
//   - Close drains both buffers and flushes before returning.
type Writer struct {
	pool *pgxpool.Pool
	cfg  WriterConfig
	log  *slog.Logger

	analyses chan domain.AnalysisRecord
	metrics  chan domain.RequestMetric

	mu     sync.RWMutex
	closed bool
	done   chan struct{}

	analysesWritten atomic.Uint64
	analysesDropped atomic.Uint64
	metricsWritten  atomic.Uint64
	metricsDropped  atomic.Uint64
	lastError       atomic.Pointer[string]
	lastDropLog     atomic.Int64 // unix seconds of the last "buffer full" warning
}

func NewWriter(pool *pgxpool.Pool, cfg WriterConfig, log *slog.Logger) *Writer {
	if log == nil {
		log = slog.Default()
	}
	return &Writer{
		pool:     pool,
		cfg:      cfg,
		log:      log.With("component", "db-writer"),
		analyses: make(chan domain.AnalysisRecord, cfg.CommentBuffer),
		metrics:  make(chan domain.RequestMetric, cfg.MetricsBuffer),
		done:     make(chan struct{}),
	}
}

// EnqueueAnalysis hands a result to the writer. It returns false (and drops
// the record) when the buffer is full or the writer is closed.
func (w *Writer) EnqueueAnalysis(rec domain.AnalysisRecord) bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	if w.closed {
		w.analysesDropped.Add(1)
		return false
	}
	select {
	case w.analyses <- rec:
		return true
	default:
		dropped := w.analysesDropped.Add(1)
		// At most one warning per second: under pressure, logging every drop
		// would itself become the overload.
		now := time.Now().Unix()
		if last := w.lastDropLog.Load(); now > last && w.lastDropLog.CompareAndSwap(last, now) {
			w.log.Warn("analysis buffer full, dropping records", "dropped_total", dropped)
		}
		return false
	}
}

// EnqueueMetric is like EnqueueAnalysis for request metrics, which are the
// first thing to go under pressure (smaller priority, no log per drop).
func (w *Writer) EnqueueMetric(m domain.RequestMetric) bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	if w.closed {
		w.metricsDropped.Add(1)
		return false
	}
	select {
	case w.metrics <- m:
		return true
	default:
		w.metricsDropped.Add(1)
		return false
	}
}

// Run writes until Close; call it in its own goroutine.
func (w *Writer) Run() {
	defer close(w.done)
	ticker := time.NewTicker(w.cfg.FlushInterval)
	defer ticker.Stop()

	analyses := make([]domain.AnalysisRecord, 0, w.cfg.BatchSize)
	metrics := make([]domain.RequestMetric, 0, w.cfg.BatchSize)
	// Local copies: a closed channel is set to nil here (a nil channel is
	// never selected), without touching the fields Stats reads.
	analysisCh, metricsCh := w.analyses, w.metrics

	flush := func() {
		if len(analyses) > 0 {
			w.writeAnalyses(analyses)
			analyses = analyses[:0]
		}
		if len(metrics) > 0 {
			w.writeMetrics(metrics)
			metrics = metrics[:0]
		}
	}
	addAnalysis := func(rec domain.AnalysisRecord) {
		analyses = append(analyses, rec)
		if len(analyses) >= w.cfg.BatchSize {
			w.writeAnalyses(analyses)
			analyses = analyses[:0]
		}
	}

	for analysisCh != nil || metricsCh != nil {
		// Comments and decisions first: they are what users see in the feed.
		select {
		case rec, ok := <-analysisCh:
			if !ok {
				analysisCh = nil
			} else {
				addAnalysis(rec)
			}
			continue
		default:
		}

		select {
		case rec, ok := <-analysisCh:
			if !ok {
				analysisCh = nil
				continue
			}
			addAnalysis(rec)
		case m, ok := <-metricsCh:
			if !ok {
				metricsCh = nil
				continue
			}
			metrics = append(metrics, m)
			if len(metrics) >= w.cfg.BatchSize {
				w.writeMetrics(metrics)
				metrics = metrics[:0]
			}
		case <-ticker.C:
			flush()
		}
	}
	flush()
}

// Close stops accepting records and waits until everything buffered is written.
func (w *Writer) Close(ctx context.Context) error {
	w.mu.Lock()
	if !w.closed {
		w.closed = true
		close(w.analyses)
		close(w.metrics)
	}
	w.mu.Unlock()
	select {
	case <-w.done:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

type WriterStats struct {
	AnalysesQueued  int    `json:"analyses_queued"`
	AnalysesWritten uint64 `json:"analyses_written"`
	AnalysesDropped uint64 `json:"analyses_dropped"`
	MetricsQueued   int    `json:"metrics_queued"`
	MetricsWritten  uint64 `json:"metrics_written"`
	MetricsDropped  uint64 `json:"metrics_dropped"`
	LastError       string `json:"last_error,omitempty"`
}

func (w *Writer) Stats() WriterStats {
	s := WriterStats{
		AnalysesQueued:  len(w.analyses),
		AnalysesWritten: w.analysesWritten.Load(),
		AnalysesDropped: w.analysesDropped.Load(),
		MetricsQueued:   len(w.metrics),
		MetricsWritten:  w.metricsWritten.Load(),
		MetricsDropped:  w.metricsDropped.Load(),
	}
	if e := w.lastError.Load(); e != nil {
		s.LastError = *e
	}
	return s
}

// --------------------------------------------------------------- writing

const maxAttempts = 3

// withRetry runs a batch write. Data errors (the database rejected a row)
// are returned at once so the caller can go row by row; connection errors
// are retried with backoff.
func (w *Writer) withRetry(write func(ctx context.Context) error) error {
	var err error
	backoff := 200 * time.Millisecond
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		ctx, cancel := context.WithTimeout(context.Background(), w.cfg.WriteTimeout)
		err = write(ctx)
		cancel()
		if err == nil || isDataError(err) {
			return err
		}
		if attempt < maxAttempts {
			time.Sleep(backoff)
			backoff *= 2
		}
	}
	return err
}

func isDataError(err error) bool {
	var pgErr *pgconn.PgError
	// Class 22 data exception, 23 integrity constraint violation.
	return errors.As(err, &pgErr) && (pgErr.Code[:2] == "22" || pgErr.Code[:2] == "23")
}

func (w *Writer) recordError(err error) {
	msg := err.Error()
	w.lastError.Store(&msg)
}

func (w *Writer) writeAnalyses(batch []domain.AnalysisRecord) {
	err := w.withRetry(func(ctx context.Context) error { return w.copyAnalyses(ctx, batch) })
	if err == nil {
		w.analysesWritten.Add(uint64(len(batch)))
		return
	}
	w.recordError(err)
	if !isDataError(err) {
		w.analysesDropped.Add(uint64(len(batch)))
		w.log.Error("database unavailable, dropping analysis batch", "size", len(batch), "error", err)
		return
	}
	// One bad row: save the others.
	for i := range batch {
		one := batch[i : i+1]
		if err := w.withRetry(func(ctx context.Context) error { return w.copyAnalyses(ctx, one) }); err != nil {
			w.analysesDropped.Add(1)
			w.recordError(err)
			w.log.Error("dropping analysis record", "comment_id", one[0].CommentID, "error", err)
			continue
		}
		w.analysesWritten.Add(1)
	}
}

func (w *Writer) copyAnalyses(ctx context.Context, batch []domain.AnalysisRecord) error {
	return pgx.BeginFunc(ctx, w.pool, func(tx pgx.Tx) error {
		comments := make([][]any, 0, len(batch))
		results := make([][]any, 0, len(batch)*2)
		decisions := make([][]any, 0, len(batch))
		for _, r := range batch {
			s := r.Summary
			comments = append(comments, []any{
				r.CommentID, r.SessionID, r.Text, r.TextSHA256, s.ArtifactHash,
				r.Result, s.LatencyMS, r.QueueWaitMS, r.FromCache, r.CreatedAt,
			})
			for _, c := range s.Content {
				results = append(results, []any{
					r.CommentID, c.Code, c.Score, c.Threshold, c.Fired,
					domain.EngineFor(c.Source), c.Source, s.ArtifactHash, r.CreatedAt,
				})
			}
			decisions = append(decisions, []any{
				r.CommentID, s.Verdict, s.FiredTypes(), s.ActiveGuards(), s.Degraded(), s.Explanation, r.CreatedAt,
			})
		}
		if _, err := tx.CopyFrom(ctx, pgx.Identifier{"comments"},
			[]string{"id", "session_id", "raw_text", "text_sha256", "artifact_hash", "result", "latency_ms", "queue_wait_ms", "from_cache", "created_at"},
			pgx.CopyFromRows(comments)); err != nil {
			return err
		}
		if len(results) > 0 {
			if _, err := tx.CopyFrom(ctx, pgx.Identifier{"analysis_results"},
				[]string{"comment_id", "offense_type", "score", "threshold", "fired", "engine", "source", "model_version", "created_at"},
				pgx.CopyFromRows(results)); err != nil {
				return err
			}
		}
		_, err := tx.CopyFrom(ctx, pgx.Identifier{"moderation_decisions"},
			[]string{"comment_id", "final_action", "fired_types", "guards_active", "degraded", "explanation", "created_at"},
			pgx.CopyFromRows(decisions))
		return err
	})
}

func (w *Writer) writeMetrics(batch []domain.RequestMetric) {
	rows := make([][]any, len(batch))
	for i, m := range batch {
		var batchSize *int16
		if m.BatchSize != nil {
			v := int16(*m.BatchSize)
			batchSize = &v
		}
		rows[i] = []any{m.Endpoint, m.Method, int16(m.StatusCode), m.LatencyMS, m.QueueWaitMS, batchSize, m.CacheHit, m.CreatedAt}
	}
	err := w.withRetry(func(ctx context.Context) error {
		_, err := w.pool.CopyFrom(ctx, pgx.Identifier{"request_metrics"},
			[]string{"endpoint", "method", "status_code", "latency_ms", "queue_wait_ms", "batch_size", "cache_hit", "created_at"},
			pgx.CopyFromRows(rows))
		return err
	})
	if err != nil {
		// Metrics are the lowest priority: never retried row by row.
		w.metricsDropped.Add(uint64(len(batch)))
		w.recordError(err)
		w.log.Warn("dropping metrics batch", "size", len(batch), "error", err)
		return
	}
	w.metricsWritten.Add(uint64(len(batch)))
}
