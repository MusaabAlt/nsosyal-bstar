package queue

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

// fakePredictor answers every item with {"text": <text>} after an optional
// delay or gate, and records the batch sizes it saw.
type fakePredictor struct {
	delay time.Duration
	// gate, when set, blocks each call until a value is received.
	gate    chan struct{}
	started chan int // receives the batch size when a call begins, if set
	fail    error
	panics  atomic.Bool
	skipIDs map[string]bool

	mu    sync.Mutex
	sizes []int
	seen  []string
	calls atomic.Int32
}

func (f *fakePredictor) PredictBatch(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
	f.calls.Add(1)
	f.mu.Lock()
	f.sizes = append(f.sizes, len(items))
	for _, it := range items {
		f.seen = append(f.seen, it.ID)
	}
	f.mu.Unlock()
	if f.started != nil {
		f.started <- len(items)
	}
	if f.gate != nil {
		select {
		case <-f.gate:
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	if f.delay > 0 {
		select {
		case <-time.After(f.delay):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	if f.panics.Load() {
		panic("boom")
	}
	if f.fail != nil {
		return nil, f.fail
	}
	out := make([]domain.PredictOutcome, 0, len(items))
	for _, it := range items {
		if f.skipIDs[it.ID] {
			continue
		}
		raw, _ := json.Marshal(map[string]string{"text": it.Text})
		out = append(out, domain.PredictOutcome{ID: it.ID, Result: raw})
	}
	return out, nil
}

func (f *fakePredictor) batchSizes() []int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]int(nil), f.sizes...)
}

func quietLog() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func newBatcher(t *testing.T, cfg Config, pred Predictor) *Batcher {
	t.Helper()
	if cfg.BatchTimeout == 0 {
		cfg.BatchTimeout = 5 * time.Second
	}
	b, err := New(cfg, pred, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	b.Start()
	t.Cleanup(func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = b.Shutdown(ctx)
	})
	return b
}

func item(i int) domain.PredictItem {
	return domain.PredictItem{ID: fmt.Sprintf("id-%d", i), Text: fmt.Sprintf("text %d", i)}
}

func TestNewRejectsBadConfig(t *testing.T) {
	good := Config{Size: 1, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond, BatchTimeout: time.Second}
	if _, err := New(good, &fakePredictor{}, nil); err != nil {
		t.Fatalf("good config rejected: %v", err)
	}
	bad := good
	bad.Size = 0
	if _, err := New(bad, &fakePredictor{}, nil); err == nil {
		t.Error("zero size accepted")
	}
	if _, err := New(good, nil, nil); err == nil {
		t.Error("nil predictor accepted")
	}
}

func TestSubmitReturnsItsOwnResult(t *testing.T) {
	b := newBatcher(t, Config{Size: 64, Workers: 2, BatchMaxSize: 8, BatchMaxWait: 5 * time.Millisecond}, &fakePredictor{})

	var wg sync.WaitGroup
	for i := range 40 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			it := item(i)
			r, err := b.Submit(context.Background(), it)
			if err != nil {
				t.Errorf("item %d: %v", i, err)
				return
			}
			var got map[string]string
			if err := json.Unmarshal(r.Outcome.Result, &got); err != nil {
				t.Errorf("item %d: bad json: %v", i, err)
				return
			}
			// Each caller must get the answer for its own text, never a neighbour's.
			if got["text"] != it.Text || r.Outcome.ID != it.ID {
				t.Errorf("item %d got %q (id %s)", i, got["text"], r.Outcome.ID)
			}
			if r.BatchSize < 1 || r.BatchSize > 8 {
				t.Errorf("batch size %d out of range", r.BatchSize)
			}
		}()
	}
	wg.Wait()
}

func TestBatchFlushesWhenFullWithoutWaiting(t *testing.T) {
	pred := &fakePredictor{}
	// One worker and a very long wait: only "batch is full" can flush quickly.
	b := newBatcher(t, Config{Size: 64, Workers: 1, BatchMaxSize: 16, BatchMaxWait: 2 * time.Second}, pred)

	start := time.Now()
	var wg sync.WaitGroup
	for i := range 16 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := b.Submit(context.Background(), item(i)); err != nil {
				t.Error(err)
			}
		}()
	}
	wg.Wait()
	if took := time.Since(start); took > time.Second {
		t.Fatalf("full batch waited %s; should flush as soon as it has 16 items", took)
	}
	if sizes := pred.batchSizes(); len(sizes) != 1 || sizes[0] != 16 {
		t.Fatalf("batch sizes = %v, want [16]", sizes)
	}
}

func TestBatchFlushesAfterMaxWait(t *testing.T) {
	pred := &fakePredictor{}
	wait := 40 * time.Millisecond
	b := newBatcher(t, Config{Size: 64, Workers: 1, BatchMaxSize: 16, BatchMaxWait: wait}, pred)

	start := time.Now()
	var wg sync.WaitGroup
	for i := range 3 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := b.Submit(context.Background(), item(i)); err != nil {
				t.Error(err)
			}
		}()
	}
	wg.Wait()
	took := time.Since(start)
	if took < wait/2 {
		t.Errorf("returned after %s; a partial batch should wait about %s for more items", took, wait)
	}
	if took > time.Second {
		t.Errorf("partial batch took %s; max wait is %s", took, wait)
	}
	total := 0
	for _, s := range pred.batchSizes() {
		total += s
	}
	if total != 3 {
		t.Errorf("model saw %d items, want 3", total)
	}
}

func TestBatchNeverExceedsMaxSize(t *testing.T) {
	pred := &fakePredictor{delay: 2 * time.Millisecond}
	b := newBatcher(t, Config{Size: 500, Workers: 3, BatchMaxSize: 5, BatchMaxWait: 10 * time.Millisecond}, pred)

	var wg sync.WaitGroup
	for i := range 200 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := b.Submit(context.Background(), item(i)); err != nil {
				t.Error(err)
			}
		}()
	}
	wg.Wait()
	total := 0
	for _, s := range pred.batchSizes() {
		if s > 5 {
			t.Fatalf("batch of %d exceeds max 5", s)
		}
		total += s
	}
	if total != 200 {
		t.Fatalf("model saw %d items, want 200", total)
	}
}

func TestWorkersBoundModelConcurrency(t *testing.T) {
	var current, peak atomic.Int32
	pred := predictorFunc(func(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
		n := current.Add(1)
		for {
			p := peak.Load()
			if n <= p || peak.CompareAndSwap(p, n) {
				break
			}
		}
		time.Sleep(5 * time.Millisecond)
		current.Add(-1)
		return echo(items), nil
	})
	b := newBatcher(t, Config{Size: 500, Workers: 2, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)

	var wg sync.WaitGroup
	for i := range 60 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, _ = b.Submit(context.Background(), item(i))
		}()
	}
	wg.Wait()
	if p := peak.Load(); p > 2 {
		t.Fatalf("%d concurrent model calls, workers = 2", p)
	}
}

func TestQueueFullReturnsImmediately(t *testing.T) {
	pred := &fakePredictor{gate: make(chan struct{}), started: make(chan int, 10)}
	b := newBatcher(t, Config{Size: 2, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)

	results := make(chan error, 3)
	submit := func(i int) {
		_, err := b.Submit(context.Background(), item(i))
		results <- err
	}

	// Item 0 is taken by the only worker, which then blocks on the gate.
	go submit(0)
	<-pred.started
	// Items 1 and 2 fill the queue (size 2).
	go submit(1)
	go submit(2)
	waitFor(t, func() bool { return b.Stats().QueueLen == 2 })

	start := time.Now()
	_, err := b.Submit(context.Background(), item(3))
	if !errors.Is(err, ErrQueueFull) {
		t.Fatalf("want ErrQueueFull, got %v", err)
	}
	if took := time.Since(start); took > 50*time.Millisecond {
		t.Fatalf("rejection took %s; must not wait", took)
	}
	if s := b.Stats(); s.Rejected != 1 {
		t.Fatalf("rejected = %d, want 1", s.Rejected)
	}

	// Release the model: the three accepted items all complete.
	for range 3 {
		pred.gate <- struct{}{}
	}
	for range 3 {
		if err := <-results; err != nil {
			t.Errorf("accepted item failed: %v", err)
		}
	}
}

func TestCancelledWhileQueuedNeverReachesModel(t *testing.T) {
	pred := &fakePredictor{gate: make(chan struct{}), started: make(chan int, 10)}
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)

	// Occupy the worker.
	go func() { _, _ = b.Submit(context.Background(), item(0)) }()
	<-pred.started

	ctx, cancel := context.WithCancel(context.Background())
	errc := make(chan error, 1)
	go func() {
		_, err := b.Submit(ctx, domain.PredictItem{ID: "gave-up", Text: "x"})
		errc <- err
	}()
	waitFor(t, func() bool { return b.Stats().QueueLen == 1 })
	cancel()
	if err := <-errc; !errors.Is(err, context.Canceled) {
		t.Fatalf("want context.Canceled, got %v", err)
	}

	pred.gate <- struct{}{} // finish item 0; the worker then meets the cancelled job
	waitFor(t, func() bool { return b.Stats().Expired == 1 })

	pred.mu.Lock()
	defer pred.mu.Unlock()
	for _, id := range pred.seen {
		if id == "gave-up" {
			t.Fatal("cancelled item was sent to the model")
		}
	}
}

func TestAlreadyCancelledContextIsNotQueued(t *testing.T) {
	b := newBatcher(t, Config{Size: 1, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, &fakePredictor{})
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := b.Submit(ctx, item(0)); !errors.Is(err, context.Canceled) {
		t.Fatalf("want context.Canceled, got %v", err)
	}
	if s := b.Stats(); s.Submitted != 0 {
		t.Fatalf("submitted = %d, want 0", s.Submitted)
	}
}

func TestPredictorErrorFailsWholeBatch(t *testing.T) {
	boom := errors.New("python down")
	pred := &fakePredictor{fail: boom}
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 4, BatchMaxWait: 20 * time.Millisecond}, pred)

	var wg sync.WaitGroup
	for i := range 4 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := b.Submit(context.Background(), item(i)); !errors.Is(err, boom) {
				t.Errorf("item %d: want %v, got %v", i, boom, err)
			}
		}()
	}
	wg.Wait()
	if s := b.Stats(); s.BatchErrors == 0 {
		t.Error("batch error not counted")
	}
}

func TestPredictorPanicDoesNotKillWorker(t *testing.T) {
	pred := &fakePredictor{}
	pred.panics.Store(true)
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)

	if _, err := b.Submit(context.Background(), item(0)); !errors.Is(err, ErrPredictorPanic) {
		t.Fatalf("want ErrPredictorPanic, got %v", err)
	}
	// The same single worker must still serve the next request.
	pred.panics.Store(false)
	if _, err := b.Submit(context.Background(), item(1)); err != nil {
		t.Fatalf("worker dead after panic: %v", err)
	}
}

func TestMissingItemGetsErrorOthersSucceed(t *testing.T) {
	pred := &fakePredictor{skipIDs: map[string]bool{"id-1": true}}
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 3, BatchMaxWait: 30 * time.Millisecond}, pred)

	errs := make([]error, 3)
	var wg sync.WaitGroup
	for i := range 3 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, errs[i] = b.Submit(context.Background(), item(i))
		}()
	}
	wg.Wait()
	if !errors.Is(errs[1], ErrMissingResult) {
		t.Errorf("item 1: want ErrMissingResult, got %v", errs[1])
	}
	if errs[0] != nil || errs[2] != nil {
		t.Errorf("other items failed: %v, %v", errs[0], errs[2])
	}
}

func TestPerItemErrorIsReturned(t *testing.T) {
	itemErr := errors.New("text too strange")
	pred := predictorFunc(func(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
		out := echo(items)
		out[0].Result, out[0].Err = nil, itemErr
		return out, nil
	})
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)
	if _, err := b.Submit(context.Background(), item(0)); !errors.Is(err, itemErr) {
		t.Fatalf("want item error, got %v", err)
	}
}

func TestBatchTimeoutBoundsModelCall(t *testing.T) {
	pred := &fakePredictor{gate: make(chan struct{})} // never released
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond, BatchTimeout: 50 * time.Millisecond}, pred)

	start := time.Now()
	_, err := b.Submit(context.Background(), item(0))
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("want deadline exceeded, got %v", err)
	}
	if took := time.Since(start); took > time.Second {
		t.Fatalf("hung model call took %s; batch timeout is 50ms", took)
	}
}

func TestQueueWaitIsMeasured(t *testing.T) {
	pred := &fakePredictor{gate: make(chan struct{}), started: make(chan int, 10)}
	b := newBatcher(t, Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond}, pred)

	go func() { _, _ = b.Submit(context.Background(), item(0)) }()
	<-pred.started

	resc := make(chan Result, 1)
	go func() {
		r, _ := b.Submit(context.Background(), item(1))
		resc <- r
	}()
	waitFor(t, func() bool { return b.Stats().QueueLen == 1 })
	time.Sleep(60 * time.Millisecond) // item 1 waits in the queue
	pred.gate <- struct{}{}
	<-pred.started
	pred.gate <- struct{}{}

	r := <-resc
	if r.QueueWait < 50*time.Millisecond {
		t.Fatalf("queue wait = %s, want >= 50ms", r.QueueWait)
	}
}

func TestShutdownDrainsQueuedWork(t *testing.T) {
	pred := &fakePredictor{delay: 10 * time.Millisecond}
	b, err := New(Config{Size: 100, Workers: 2, BatchMaxSize: 4, BatchMaxWait: 5 * time.Millisecond, BatchTimeout: 5 * time.Second}, pred, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	b.Start()

	const n = 50
	errs := make(chan error, n)
	for i := range n {
		go func() {
			_, err := b.Submit(context.Background(), item(i))
			errs <- err
		}()
	}
	waitFor(t, func() bool { return b.Stats().Submitted == n })

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := b.Shutdown(ctx); err != nil {
		t.Fatalf("shutdown: %v", err)
	}
	for range n {
		if err := <-errs; err != nil {
			t.Errorf("queued item lost during shutdown: %v", err)
		}
	}
	if _, err := b.Submit(context.Background(), item(999)); !errors.Is(err, ErrClosed) {
		t.Fatalf("submit after shutdown: want ErrClosed, got %v", err)
	}
	// A second shutdown is harmless.
	if err := b.Shutdown(ctx); err != nil {
		t.Fatalf("second shutdown: %v", err)
	}
}

func TestShutdownRespectsDeadline(t *testing.T) {
	pred := &fakePredictor{gate: make(chan struct{}), started: make(chan int, 1)}
	b, err := New(Config{Size: 10, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond, BatchTimeout: 10 * time.Second}, pred, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	b.Start()
	go func() { _, _ = b.Submit(context.Background(), item(0)) }()
	<-pred.started

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	if err := b.Shutdown(ctx); !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("want deadline exceeded while model hangs, got %v", err)
	}
	close(pred.gate)
}

func TestShutdownWithoutStartFailsQueuedJobs(t *testing.T) {
	b, err := New(Config{Size: 5, Workers: 1, BatchMaxSize: 1, BatchMaxWait: time.Millisecond, BatchTimeout: time.Second}, &fakePredictor{}, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	errc := make(chan error, 1)
	go func() {
		_, err := b.Submit(context.Background(), item(0))
		errc <- err
	}()
	waitFor(t, func() bool { return b.Stats().QueueLen == 1 })
	if err := b.Shutdown(context.Background()); err != nil {
		t.Fatal(err)
	}
	if err := <-errc; !errors.Is(err, ErrClosed) {
		t.Fatalf("want ErrClosed, got %v", err)
	}
}

// Many goroutines submitting while shutdown closes the queue must never
// panic with "send on closed channel".
func TestConcurrentSubmitAndShutdown(t *testing.T) {
	for range 20 {
		b, err := New(Config{Size: 8, Workers: 2, BatchMaxSize: 4, BatchMaxWait: time.Millisecond, BatchTimeout: time.Second}, &fakePredictor{}, quietLog())
		if err != nil {
			t.Fatal(err)
		}
		b.Start()
		var wg sync.WaitGroup
		for i := range 50 {
			wg.Add(1)
			go func() {
				defer wg.Done()
				_, err := b.Submit(context.Background(), item(i))
				if err != nil && !errors.Is(err, ErrClosed) && !errors.Is(err, ErrQueueFull) {
					t.Errorf("unexpected error: %v", err)
				}
			}()
		}
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		if err := b.Shutdown(ctx); err != nil {
			t.Errorf("shutdown: %v", err)
		}
		cancel()
		wg.Wait()
	}
}

type predictorFunc func(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error)

func (f predictorFunc) PredictBatch(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
	return f(ctx, items)
}

func echo(items []domain.PredictItem) []domain.PredictOutcome {
	out := make([]domain.PredictOutcome, len(items))
	for i, it := range items {
		out[i] = domain.PredictOutcome{ID: it.ID, Result: json.RawMessage(`{}`)}
	}
	return out
}

func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatal("condition not reached within 3s")
		}
		time.Sleep(time.Millisecond)
	}
}
