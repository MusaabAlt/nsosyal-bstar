package metrics

import (
	"testing"
	"time"
)

func TestEmptyWindowHasNoPercentiles(t *testing.T) {
	s := NewWindow(10, time.Minute).Summary()
	if s.Samples != 0 || s.P50MS != nil || s.P95MS != nil {
		t.Fatalf("empty window must report no data, got %+v", s)
	}
}

func TestPercentiles(t *testing.T) {
	w := NewWindow(1000, time.Minute)
	for i := 1; i <= 100; i++ {
		w.Observe(float64(i))
	}
	s := w.Summary()
	if s.Samples != 100 || *s.P50MS != 50 || *s.P95MS != 95 || *s.P99MS != 99 || *s.MaxMS != 100 {
		t.Fatalf("summary = samples %d p50 %v p95 %v p99 %v max %v", s.Samples, *s.P50MS, *s.P95MS, *s.P99MS, *s.MaxMS)
	}
}

func TestRingIsBounded(t *testing.T) {
	w := NewWindow(10, time.Minute)
	for i := range 1000 {
		w.Observe(float64(i))
	}
	s := w.Summary()
	if s.Samples != 10 || s.Total != 1000 {
		t.Fatalf("samples %d total %d", s.Samples, s.Total)
	}
	if *s.P50MS < 990 {
		t.Fatalf("old samples kept: p50 %v", *s.P50MS)
	}
}

func TestOldSamplesAgeOut(t *testing.T) {
	now := time.Unix(0, 0)
	w := NewWindow(10, time.Minute)
	w.now = func() time.Time { return now }
	w.Observe(1000)
	now = now.Add(2 * time.Minute)
	w.Observe(5)
	s := w.Summary()
	if s.Samples != 1 || *s.MaxMS != 5 {
		t.Fatalf("aged sample still counted: %+v", s)
	}
}
