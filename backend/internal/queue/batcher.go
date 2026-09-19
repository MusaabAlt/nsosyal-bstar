// Package queue protects the model from overload.
//
// Requests go into a bounded queue. A fixed pool of workers takes texts from
// it, groups them into small batches (up to BatchMaxSize texts, or whatever
// arrived within BatchMaxWait) and sends each batch to the model in one call.
//
// What it guarantees:
//   - Memory is bounded: when the queue is full, Submit returns ErrQueueFull
//     at once instead of waiting or growing.
//   - At most Workers batches hit the model at the same time.
//   - A request that gave up while waiting (its context ended) is skipped and
//     never reaches the model.
//   - A panic or error in the model call fails that batch only; the worker
//     keeps running.
//   - Shutdown stops new work and finishes everything already queued.
package queue

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"sync/atomic"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

var (
	// ErrQueueFull means the system is at capacity; the API answers 503.
	ErrQueueFull = errors.New("queue full")
	// ErrClosed means the server is shutting down.
	ErrClosed = errors.New("queue closed")
	// ErrMissingResult means the model answered the batch but not this item.
	ErrMissingResult = errors.New("model returned no result for item")
	// ErrPredictorPanic means the model call panicked.
	ErrPredictorPanic = errors.New("model call panicked")
)

// Predictor sends one batch to the model. It must return one outcome per
// item it answered; a returned error fails the whole batch.
type Predictor interface {
	PredictBatch(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error)
}

type Config struct {
	Size         int
	Workers      int
	BatchMaxSize int
	BatchMaxWait time.Duration
	// BatchTimeout bounds one model call. It is not tied to any single
	// request's context, so one impatient client cannot cancel a whole batch.
	BatchTimeout time.Duration
}

// Result is what Submit returns for one text.
type Result struct {
	Outcome domain.PredictOutcome
	// QueueWait is the time from Submit to the batch being sent.
	QueueWait time.Duration
	// ModelLatency is the duration of the batch call this item was part of.
	ModelLatency time.Duration
	BatchSize    int
}

type job struct {
	ctx      context.Context
	item     domain.PredictItem
	enqueued time.Time
	// Buffered (size 1) so a worker never blocks on a caller that left.
	done chan Result
}

// Stats is a point-in-time snapshot for /api/stats and /api/health.
type Stats struct {
	QueueLen      int    `json:"queue_len"`
	QueueCapacity int    `json:"queue_capacity"`
	InFlight      int64  `json:"in_flight"`
	Workers       int    `json:"workers"`
	Submitted     uint64 `json:"submitted"`
	Rejected      uint64 `json:"rejected"`
	Expired       uint64 `json:"expired"`
	Batches       uint64 `json:"batches"`
	BatchErrors   uint64 `json:"batch_errors"`
}

type Batcher struct {
	cfg  Config
	pred Predictor
	log  *slog.Logger
	jobs chan *job

	// mu guards closed and the close of jobs, so Submit can never send on a
	// closed channel.
	mu      sync.RWMutex
	closed  bool
	started bool
	wg      sync.WaitGroup

	inFlight    atomic.Int64
	submitted   atomic.Uint64
	rejected    atomic.Uint64
	expired     atomic.Uint64
	batches     atomic.Uint64
	batchErrors atomic.Uint64
}

func New(cfg Config, pred Predictor, log *slog.Logger) (*Batcher, error) {
	if cfg.Size <= 0 || cfg.Workers <= 0 || cfg.BatchMaxSize <= 0 || cfg.BatchMaxWait <= 0 || cfg.BatchTimeout <= 0 {
		return nil, fmt.Errorf("queue: every config value must be > 0: %+v", cfg)
	}
	if pred == nil {
		return nil, errors.New("queue: predictor is required")
	}
	if log == nil {
		log = slog.Default()
	}
	return &Batcher{
		cfg:  cfg,
		pred: pred,
		log:  log.With("component", "batcher"),
		jobs: make(chan *job, cfg.Size),
	}, nil
}

// Start launches the workers. Calling it more than once has no effect.
func (b *Batcher) Start() {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.started || b.closed {
		return
	}
	b.started = true
	for i := 0; i < b.cfg.Workers; i++ {
		b.wg.Add(1)
		go b.worker(i)
	}
}

// Submit queues one text and waits for its result. It returns ErrQueueFull
// immediately when there is no room, ErrClosed during shutdown, and the
// context's error if ctx ends first.
func (b *Batcher) Submit(ctx context.Context, item domain.PredictItem) (Result, error) {
	if err := ctx.Err(); err != nil {
		return Result{}, err
	}
	j := &job{ctx: ctx, item: item, enqueued: time.Now(), done: make(chan Result, 1)}

	b.mu.RLock()
	if b.closed {
		b.mu.RUnlock()
		return Result{}, ErrClosed
	}
	select {
	case b.jobs <- j:
		b.submitted.Add(1)
	default:
		b.mu.RUnlock()
		b.rejected.Add(1)
		return Result{}, ErrQueueFull
	}
	b.mu.RUnlock()

	select {
	case r := <-j.done:
		if r.Outcome.Err != nil {
			return r, r.Outcome.Err
		}
		return r, nil
	case <-ctx.Done():
		// The worker will see the ended context and skip this job.
		return Result{}, ctx.Err()
	}
}

// Shutdown stops accepting work, lets the workers finish everything already
// queued, and returns when they are done or ctx ends.
func (b *Batcher) Shutdown(ctx context.Context) error {
	b.mu.Lock()
	if !b.closed {
		b.closed = true
		close(b.jobs)
	}
	started := b.started
	b.mu.Unlock()

	if !started {
		// No workers will ever drain the queue; fail anything left in it.
		for j := range b.jobs {
			j.done <- Result{Outcome: domain.PredictOutcome{ID: j.item.ID, Err: ErrClosed}}
		}
		return nil
	}

	finished := make(chan struct{})
	go func() {
		b.wg.Wait()
		close(finished)
	}()
	select {
	case <-finished:
		return nil
	case <-ctx.Done():
		return fmt.Errorf("queue drain: %w", ctx.Err())
	}
}

func (b *Batcher) Stats() Stats {
	return Stats{
		QueueLen:      len(b.jobs),
		QueueCapacity: cap(b.jobs),
		InFlight:      b.inFlight.Load(),
		Workers:       b.cfg.Workers,
		Submitted:     b.submitted.Load(),
		Rejected:      b.rejected.Load(),
		Expired:       b.expired.Load(),
		Batches:       b.batches.Load(),
		BatchErrors:   b.batchErrors.Load(),
	}
}

func (b *Batcher) worker(id int) {
	defer b.wg.Done()
	batch := make([]*job, 0, b.cfg.BatchMaxSize)
	timer := time.NewTimer(time.Hour)
	timer.Stop()

	for {
		// Block until there is work. A closed and drained channel ends the worker.
		first, ok := <-b.jobs
		if !ok {
			return
		}
		batch = append(batch[:0], first)

		// Collect more until the batch is full or the wait is over.
		timer.Reset(b.cfg.BatchMaxWait)
	collect:
		for len(batch) < b.cfg.BatchMaxSize {
			select {
			case j, ok := <-b.jobs:
				if !ok {
					break collect
				}
				batch = append(batch, j)
			case <-timer.C:
				break collect
			}
		}
		timer.Stop()

		b.runBatch(id, batch)
		clear(batch) // drop references so finished jobs can be collected
	}
}

func (b *Batcher) runBatch(workerID int, batch []*job) {
	// Skip requests whose callers already gave up: the model is the scarce
	// resource and must not spend time on answers nobody will read.
	live := make([]*job, 0, len(batch))
	for _, j := range batch {
		if err := j.ctx.Err(); err != nil {
			b.expired.Add(1)
			j.done <- Result{Outcome: domain.PredictOutcome{ID: j.item.ID, Err: err}}
			continue
		}
		live = append(live, j)
	}
	if len(live) == 0 {
		return
	}

	dispatched := time.Now()
	items := make([]domain.PredictItem, len(live))
	for i, j := range live {
		items[i] = j.item
	}

	b.inFlight.Add(int64(len(live)))
	defer b.inFlight.Add(-int64(len(live)))
	b.batches.Add(1)

	outcomes, err := b.callPredictor(items)
	modelLatency := time.Since(dispatched)

	finish := func(j *job, outcome domain.PredictOutcome) {
		j.done <- Result{
			Outcome:      outcome,
			QueueWait:    dispatched.Sub(j.enqueued),
			ModelLatency: modelLatency,
			BatchSize:    len(live),
		}
	}

	if err != nil {
		b.batchErrors.Add(1)
		b.log.Warn("batch failed", "worker", workerID, "size", len(live), "latency_ms", modelLatency.Milliseconds(), "error", err)
		for _, j := range live {
			finish(j, domain.PredictOutcome{ID: j.item.ID, Err: err})
		}
		return
	}

	// Match by id, not by position. Ids are normally unique; a list per id
	// keeps duplicates from being silently dropped.
	byID := make(map[string][]domain.PredictOutcome, len(outcomes))
	for _, o := range outcomes {
		byID[o.ID] = append(byID[o.ID], o)
	}
	for _, j := range live {
		list := byID[j.item.ID]
		if len(list) == 0 {
			finish(j, domain.PredictOutcome{ID: j.item.ID, Err: ErrMissingResult})
			continue
		}
		byID[j.item.ID] = list[1:]
		finish(j, list[0])
	}
}

// callPredictor turns a panic inside the model client into an error for this
// batch. Without it, one panic in a worker goroutine would kill the process;
// the HTTP recover middleware does not cover goroutines it did not start.
func (b *Batcher) callPredictor(items []domain.PredictItem) (outcomes []domain.PredictOutcome, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), b.cfg.BatchTimeout)
	defer cancel()
	defer func() {
		if r := recover(); r != nil {
			b.log.Error("predictor panic", "panic", r, "size", len(items))
			outcomes, err = nil, fmt.Errorf("%w: %v", ErrPredictorPanic, r)
		}
	}()
	return b.pred.PredictBatch(ctx, items)
}
