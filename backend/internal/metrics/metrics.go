// Package metrics keeps live latency numbers in memory for /api/stats, so
// the dashboard never runs a percentile query against Postgres.
package metrics

import (
	"slices"
	"sync"
	"time"
)

// Window keeps the most recent samples in a fixed ring (memory is bounded)
// and computes percentiles over those still inside maxAge.
type Window struct {
	maxAge time.Duration
	now    func() time.Time

	mu     sync.Mutex
	values []float64
	times  []time.Time
	next   int
	filled bool
	total  uint64
}

func NewWindow(capacity int, maxAge time.Duration) *Window {
	return &Window{
		maxAge: maxAge,
		now:    time.Now,
		values: make([]float64, capacity),
		times:  make([]time.Time, capacity),
	}
}

func (w *Window) Observe(ms float64) {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.values[w.next] = ms
	w.times[w.next] = w.now()
	w.next = (w.next + 1) % len(w.values)
	if w.next == 0 {
		w.filled = true
	}
	w.total++
}

// Summary is a latency snapshot. Percentiles are nil when there are no samples,
// so the dashboard shows "no data" instead of a fake zero.
type Summary struct {
	Samples int      `json:"samples"`
	Total   uint64   `json:"total"`
	P50MS   *float64 `json:"p50_ms"`
	P95MS   *float64 `json:"p95_ms"`
	P99MS   *float64 `json:"p99_ms"`
	MaxMS   *float64 `json:"max_ms"`
	Window  string   `json:"window"`
}

func (w *Window) Summary() Summary {
	w.mu.Lock()
	n := w.next
	if w.filled {
		n = len(w.values)
	}
	cutoff := w.now().Add(-w.maxAge)
	recent := make([]float64, 0, n)
	for i := 0; i < n; i++ {
		if w.times[i].After(cutoff) {
			recent = append(recent, w.values[i])
		}
	}
	total := w.total
	w.mu.Unlock()

	s := Summary{Samples: len(recent), Total: total, Window: w.maxAge.String()}
	if len(recent) == 0 {
		return s
	}
	slices.Sort(recent)
	s.P50MS = ptr(percentile(recent, 0.50))
	s.P95MS = ptr(percentile(recent, 0.95))
	s.P99MS = ptr(percentile(recent, 0.99))
	s.MaxMS = ptr(recent[len(recent)-1])
	return s
}

// percentile uses the nearest-rank method on sorted values.
func percentile(sorted []float64, p float64) float64 {
	rank := int(p*float64(len(sorted))+0.999999) - 1
	rank = max(0, min(rank, len(sorted)-1))
	return sorted[rank]
}

func ptr(v float64) *float64 { return &v }

// Registry groups the windows the server records.
type Registry struct {
	Request   *Window // whole POST /api/comments, as the user feels it
	QueueWait *Window // time waiting for a batch slot
	Model     *Window // Python batch call
}

func NewRegistry() *Registry {
	const capacity, age = 4096, 5 * time.Minute
	return &Registry{
		Request:   NewWindow(capacity, age),
		QueueWait: NewWindow(capacity, age),
		Model:     NewWindow(capacity, age),
	}
}
