// Package domain holds the types shared between packages.
package domain

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
)

// PredictItem is one text sent to the Python /predict_batch endpoint.
// ID is the comment id; Python uses it as the pipeline trace_id.
type PredictItem struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

// PredictOutcome is the model's answer for one item. Exactly one of Result
// and Err is set. Result is the AnalysisResult JSON exactly as Python sent it
// (AI/contracts/schema.py); Go passes it through and never rewrites it.
type PredictOutcome struct {
	ID     string
	Result json.RawMessage
	// Normalization is m2's optional de-obfuscated text and changes, sent
	// beside the result (it is not part of the frozen AnalysisResult).
	Normalization json.RawMessage
	Err           error
}

// Actions, most severe first (AI/contracts/codes.py ACTION_PRECEDENCE).
const (
	ActionBlock    = "block"
	ActionEscalate = "escalate"
	ActionReview   = "review"
	ActionNudge    = "nudge"
	ActionClean    = "clean"
)

// ContentScore, GuardResult and DegradedModule mirror the fields of the
// contract that Go needs for storage and the dashboard. Everything else in
// the result is kept as raw JSON.
type ContentScore struct {
	Code      string   `json:"code"`
	Score     float64  `json:"score"`
	Source    string   `json:"source"`
	Threshold *float64 `json:"threshold"`
	Fired     *bool    `json:"fired"`
}

type GuardResult struct {
	Code       string   `json:"code"`
	Active     *bool    `json:"active"`
	Suppressed []string `json:"suppressed"`
}

type DegradedModule struct {
	Module string   `json:"module"`
	Kinds  []string `json:"kinds"`
}

// ResultSummary is the part of an AnalysisResult Go reads. Go never decides
// anything from it: verdict, fired and active are copied as Python set them.
type ResultSummary struct {
	Text         string         `json:"text"`
	Verdict      *string        `json:"verdict"`
	Content      []ContentScore `json:"content"`
	Guards       []GuardResult  `json:"guards"`
	Explanation  string         `json:"explanation"`
	LatencyMS    float64        `json:"latency_ms"`
	TraceID      string         `json:"trace_id"`
	ArtifactHash string         `json:"artifact_hash"`
	Signals      struct {
		Pipeline *struct {
			Degraded []DegradedModule `json:"degraded"`
		} `json:"pipeline"`
	} `json:"signals"`
}

// ParseResult reads the fields Go needs and checks the shape is usable.
func ParseResult(raw json.RawMessage) (ResultSummary, error) {
	var s ResultSummary
	if err := json.Unmarshal(raw, &s); err != nil {
		return ResultSummary{}, fmt.Errorf("analysis result is not valid JSON: %w", err)
	}
	if s.Verdict != nil {
		switch *s.Verdict {
		case ActionBlock, ActionEscalate, ActionReview, ActionNudge, ActionClean:
		default:
			return ResultSummary{}, fmt.Errorf("analysis result has unknown verdict %q", *s.Verdict)
		}
	}
	return s, nil
}

// Degraded reports whether any module did not run properly. A result that
// does not say is treated as degraded: fail closed, like the frontend.
func (s ResultSummary) Degraded() bool {
	return s.Signals.Pipeline == nil || len(s.Signals.Pipeline.Degraded) > 0
}

// FiredTypes lists content codes the decision layer marked fired.
func (s ResultSummary) FiredTypes() []string {
	out := []string{}
	for _, c := range s.Content {
		if c.Fired != nil && *c.Fired {
			out = append(out, c.Code)
		}
	}
	return out
}

// ActiveGuards lists guard codes the decision layer marked active.
func (s ResultSummary) ActiveGuards() []string {
	out := []string{}
	for _, g := range s.Guards {
		if g.Active != nil && *g.Active {
			out = append(out, g.Code)
		}
	}
	return out
}

// EngineFor maps a score's source ("m3_encoder@raw") to the engine column.
func EngineFor(source string) string {
	module, _, _ := strings.Cut(source, "@")
	switch module {
	case "m1_lexicon":
		return "lexicon"
	case "m0_charsafe", "m2_deobf", "m6_target":
		return "rule"
	default:
		return "model"
	}
}

// Session is an anonymous demo user.
type Session struct {
	ID        uuid.UUID `json:"id"`
	Nickname  string    `json:"nickname"`
	CreatedAt time.Time `json:"created_at"`
}

// AnalysisRecord is everything the async writer stores for one analysed comment.
type AnalysisRecord struct {
	CommentID   uuid.UUID
	SessionID   uuid.UUID
	IP          string
	Text        string
	TextSHA256  []byte
	Result      json.RawMessage
	Summary     ResultSummary
	QueueWaitMS *float64
	FromCache   bool
	CreatedAt   time.Time
}

// RequestMetric is one row of request_metrics.
type RequestMetric struct {
	Endpoint    string
	Method      string
	StatusCode  int
	LatencyMS   float64
	QueueWaitMS *float64
	BatchSize   *int
	CacheHit    *bool
	CreatedAt   time.Time
}
