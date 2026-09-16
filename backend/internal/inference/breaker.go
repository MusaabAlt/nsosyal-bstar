package inference

import (
	"sync"
	"time"
)

// BreakerState is the circuit breaker's position.
type BreakerState string

const (
	// Closed: calls go through normally.
	BreakerClosed BreakerState = "closed"
	// Open: calls fail fast without touching Python.
	BreakerOpen BreakerState = "open"
	// HalfOpen: one trial call is let through to see if Python is back.
	BreakerHalfOpen BreakerState = "half_open"
)

// Breaker stops sending work to a Python service that keeps failing, so
// requests get a fast "model restarting" answer instead of each waiting for
// its own timeout. After `failures` consecutive failures it opens for
// `openFor`; then it lets exactly one trial call through.
type Breaker struct {
	failures int
	openFor  time.Duration
	now      func() time.Time

	mu          sync.Mutex
	state       BreakerState
	consecutive int
	openedAt    time.Time
	trialActive bool
}

func NewBreaker(failures int, openFor time.Duration) *Breaker {
	return &Breaker{failures: failures, openFor: openFor, now: time.Now, state: BreakerClosed}
}

// Allow reports whether a call may proceed. A true result must be followed
// by exactly one Success or Failure.
func (b *Breaker) Allow() bool {
	b.mu.Lock()
	defer b.mu.Unlock()
	switch b.state {
	case BreakerClosed:
		return true
	case BreakerOpen:
		if b.now().Sub(b.openedAt) < b.openFor {
			return false
		}
		b.state = BreakerHalfOpen
		b.trialActive = true
		return true
	default: // half-open: only the one trial call
		if b.trialActive {
			return false
		}
		b.trialActive = true
		return true
	}
}

func (b *Breaker) Success() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.state = BreakerClosed
	b.consecutive = 0
	b.trialActive = false
}

func (b *Breaker) Failure() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.trialActive = false
	if b.state == BreakerHalfOpen {
		b.open()
		return
	}
	b.consecutive++
	if b.consecutive >= b.failures {
		b.open()
	}
}

// Trip opens the breaker at once, e.g. when the supervisor knows Python died.
func (b *Breaker) Trip() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.trialActive = false
	b.open()
}

func (b *Breaker) open() {
	b.state = BreakerOpen
	b.openedAt = b.now()
	b.consecutive = 0
}

func (b *Breaker) State() BreakerState {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.state == BreakerOpen && b.now().Sub(b.openedAt) >= b.openFor {
		return BreakerHalfOpen
	}
	return b.state
}
