// Package inference talks to the Python inference service over localhost.
//
// Contract (agreed in the backend plan):
//
//	POST /predict_batch  {"items": [{"id", "text"}]}
//	  200 {"artifact_hash": "...", "results": [{"id", "ok": true, "result": {AnalysisResult}}
//	                                          | {"id", "ok": false, "error": "..."}]}
//	  503 while models are loading
//	GET  /health         {"status": "ok" | "loading" | "error", "artifact_hash": "...", "degraded_modules": [...]}
package inference

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

var (
	// ErrUnavailable means Python is down, restarting or failing: the API
	// answers 503 "model restarting" at once.
	ErrUnavailable = errors.New("inference service unavailable")
	// ErrLoading means Python is up but still loading its models.
	ErrLoading = errors.New("inference service is loading models")
)

// maxResponseBytes caps a batch response: 16 results of a bounded contract
// are far below this, and a broken service must not exhaust memory.
const maxResponseBytes = 32 << 20

type Config struct {
	URL             string
	HealthTimeout   time.Duration
	BreakerFailures int
	BreakerOpenFor  time.Duration
}

// Health is the last known state of the Python service.
type Health struct {
	Status          string       `json:"status"` // ok | loading | error | unreachable
	ArtifactHash    string       `json:"artifact_hash,omitempty"`
	DegradedModules []string     `json:"degraded_modules,omitempty"`
	Breaker         BreakerState `json:"breaker"`
	CheckedAt       time.Time    `json:"checked_at"`
	Error           string       `json:"error,omitempty"`
}

type Client struct {
	baseURL string
	cfg     Config
	http    *http.Client
	breaker *Breaker

	mu           sync.RWMutex
	artifactHash string
	health       Health
}

func New(cfg Config) *Client {
	transport := &http.Transport{
		// One local service: keep enough idle connections for every worker so
		// batches never pay a new TCP handshake.
		MaxIdleConns:        32,
		MaxIdleConnsPerHost: 32,
		IdleConnTimeout:     90 * time.Second,
		DialContext:         (&net.Dialer{Timeout: 2 * time.Second}).DialContext,
		DisableCompression:  true, // localhost: compression only costs CPU
	}
	return &Client{
		baseURL: strings.TrimRight(cfg.URL, "/"),
		cfg:     cfg,
		// No client-wide timeout: every call carries its own context deadline.
		http:    &http.Client{Transport: transport},
		breaker: NewBreaker(cfg.BreakerFailures, cfg.BreakerOpenFor),
		health:  Health{Status: "unknown", Breaker: BreakerClosed},
	}
}

type batchRequest struct {
	Items []domain.PredictItem `json:"items"`
}

type batchResult struct {
	ID     string          `json:"id"`
	OK     bool            `json:"ok"`
	Result json.RawMessage `json:"result"`
	Error  string          `json:"error"`
}

type batchResponse struct {
	ArtifactHash string        `json:"artifact_hash"`
	Results      []batchResult `json:"results"`
}

// ItemError is a failure Python reported for one item; the rest of the batch
// is unaffected.
type ItemError struct{ Message string }

func (e *ItemError) Error() string { return "model failed on item: " + e.Message }

// PredictBatch implements queue.Predictor.
func (c *Client) PredictBatch(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
	if !c.breaker.Allow() {
		if c.Health().Status == "loading" {
			return nil, ErrLoading
		}
		return nil, ErrUnavailable
	}

	outcomes, err := c.predict(ctx, items)
	switch {
	case err == nil:
		c.breaker.Success()
	case errors.Is(err, ErrLoading):
		// Loading is expected after a restart; it is not a failure to count,
		// but nothing should be sent until health says ok.
		c.breaker.Trip()
	default:
		c.breaker.Failure()
	}
	return outcomes, err
}

func (c *Client) predict(ctx context.Context, items []domain.PredictItem) ([]domain.PredictOutcome, error) {
	body, err := json.Marshal(batchRequest{Items: items})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/predict_batch", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		if ctxErr := ctx.Err(); ctxErr != nil {
			return nil, fmt.Errorf("%w: %w", ErrUnavailable, ctxErr)
		}
		return nil, fmt.Errorf("%w: %v", ErrUnavailable, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return nil, fmt.Errorf("%w: read response: %v", ErrUnavailable, err)
	}

	switch {
	case resp.StatusCode == http.StatusServiceUnavailable:
		return nil, ErrLoading
	case resp.StatusCode != http.StatusOK:
		return nil, fmt.Errorf("%w: status %d: %s", ErrUnavailable, resp.StatusCode, snippet(data))
	}

	var parsed batchResponse
	if err := json.Unmarshal(data, &parsed); err != nil {
		return nil, fmt.Errorf("%w: invalid response JSON: %v", ErrUnavailable, err)
	}
	if parsed.ArtifactHash != "" {
		c.setArtifactHash(parsed.ArtifactHash)
	}

	outcomes := make([]domain.PredictOutcome, 0, len(parsed.Results))
	for _, r := range parsed.Results {
		o := domain.PredictOutcome{ID: r.ID}
		switch {
		case !r.OK:
			o.Err = &ItemError{Message: r.Error}
		case len(r.Result) == 0 || string(r.Result) == "null":
			o.Err = &ItemError{Message: "empty result"}
		default:
			if _, err := domain.ParseResult(r.Result); err != nil {
				o.Err = &ItemError{Message: err.Error()}
			} else {
				o.Result = r.Result
			}
		}
		outcomes = append(outcomes, o)
	}
	return outcomes, nil
}

type healthResponse struct {
	Status          string   `json:"status"`
	ArtifactHash    string   `json:"artifact_hash"`
	DegradedModules []string `json:"degraded_modules"`
}

// CheckHealth calls GET /health, records the result and returns it. The
// supervisor calls it on an interval.
func (c *Client) CheckHealth(ctx context.Context) Health {
	ctx, cancel := context.WithTimeout(ctx, c.cfg.HealthTimeout)
	defer cancel()

	h := Health{CheckedAt: time.Now()}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/health", nil)
	if err == nil {
		var resp *http.Response
		resp, err = c.http.Do(req)
		if err == nil {
			data, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			resp.Body.Close()
			var parsed healthResponse
			if jsonErr := json.Unmarshal(data, &parsed); jsonErr != nil || parsed.Status == "" {
				h.Status = "error"
				h.Error = fmt.Sprintf("status %d, unreadable health body", resp.StatusCode)
			} else {
				h.Status = parsed.Status
				h.ArtifactHash = parsed.ArtifactHash
				h.DegradedModules = parsed.DegradedModules
			}
		}
	}
	if err != nil {
		h.Status = "unreachable"
		h.Error = err.Error()
	}

	switch h.Status {
	case "ok":
		if h.ArtifactHash != "" {
			c.setArtifactHash(h.ArtifactHash)
		}
		// Python answers: let the next call through instead of waiting out the open period.
		if c.breaker.State() != BreakerClosed {
			c.breaker.Success()
		}
	default:
		c.breaker.Trip()
	}
	h.Breaker = c.breaker.State()

	c.mu.Lock()
	c.health = h
	c.mu.Unlock()
	return h
}

// Health returns the last recorded health, with the breaker's current state.
func (c *Client) Health() Health {
	c.mu.RLock()
	h := c.health
	c.mu.RUnlock()
	h.Breaker = c.breaker.State()
	return h
}

// ArtifactHash is the model+threshold version Python last reported, or "".
// The cache keys on it so a new model never serves old answers.
func (c *Client) ArtifactHash() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.artifactHash
}

// MarkDown is called by the supervisor when the Python process exits.
func (c *Client) MarkDown(reason string) {
	c.breaker.Trip()
	c.mu.Lock()
	c.health = Health{Status: "unreachable", Error: reason, CheckedAt: time.Now()}
	c.mu.Unlock()
}

func (c *Client) setArtifactHash(hash string) {
	c.mu.Lock()
	c.artifactHash = hash
	c.mu.Unlock()
}

func snippet(b []byte) string {
	const max = 200
	s := strings.TrimSpace(string(b))
	if len(s) > max {
		return s[:max] + "..."
	}
	return s
}
