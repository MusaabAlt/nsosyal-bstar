// Command seed fills the database with a demo feed for the moderation panel.
//
//	go run ./cmd/seed [-config config.yaml] [-days 14] [-comments 40000] [-reset]
//
// Every post, comment and nickname it writes is invented (see samples.go): no
// real NSosyal user and no real message ever goes through this command. It
// exists so the panel can be shown on a projector without the model, the
// inference service or a live audience behind it.
//
// The rows it writes have exactly the shape the running system writes, so the
// panel's numbers are still counted from stored data by the same queries -
// nothing on the screen is a placeholder.
//
// -reset deletes every comment, session, decision, moderator action and
// request metric in the database first. It refuses to run without -reset when
// the database already holds comments.
package main

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand/v2"
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/config"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
)

// defaultArtifactHash is the artifact the demo rows claim to come from. Pass
// -artifact with the hash the running inference service reports (GET /health)
// so the panel's "Model sürümü" agrees with the seeded rows.
const defaultArtifactHash = "57466e1738c99c48ae87ba537df93c268d446b3cf4a258669ff3611f5bf6fe63"

// artifactHash is what this run stamps on every row it writes.
var artifactHash = defaultArtifactHash

// How the generated stream is made up. Clean dominates, as a real feed does.
//
// shareBorderline is deliberately small. A borderline message clears the
// general offensive threshold without reaching any category threshold, so the
// decision layer can only ask for a person: every one of them lands in the
// human review queue. A feed where one message in sixteen is that ambiguous
// would bury the moderators, and it is not what a real feed looks like.
const (
	shareClean      = 0.825
	shareGuarded    = 0.04
	shareBorderline = 0.015
	// the rest is shareDetected
)

// copyChunk is how many rows go to Postgres in one CopyFrom.
const copyChunk = 5000

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "seed:", err)
		os.Exit(1)
	}
}

func run() error {
	configPath := flag.String("config", "", "path to config.yaml (default: found in the current folder or backend/)")
	// Two weeks by default: the panel's "7 Gün" range compares with the week
	// before it, and a window with nothing behind it shows an absurd change.
	days := flag.Int("days", 14, "how many days back the demo feed starts")
	total := flag.Int("comments", 40000, "how many comments to generate")
	reset := flag.Bool("reset", false, "delete all existing comments, sessions and metrics first")
	seed := flag.Uint64("seed", 20260918, "random seed; the same seed produces the same feed")
	degradedPct := flag.Float64("degraded-pct", 1.0, "percent of comments whose evaluation did not complete")
	artifact := flag.String("artifact", defaultArtifactHash, "artifact hash to stamp on the demo rows (match the inference service's /health)")
	flag.Parse()
	artifactHash = *artifact

	if *days < 1 || *total < 1 {
		return fmt.Errorf("-days and -comments must be at least 1")
	}

	path := *configPath
	if path == "" {
		found, err := config.Find()
		if err != nil {
			return err
		}
		path = found
	}
	cfg, err := config.Load(path)
	if err != nil {
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	pool, err := store.NewPool(ctx, cfg.Database)
	if err != nil {
		return err
	}
	defer pool.Close()

	var existing int64
	if err := pool.QueryRow(ctx, `SELECT count(*) FROM comments`).Scan(&existing); err != nil {
		return fmt.Errorf("count comments: %w (run ./cmd/migrate first)", err)
	}
	if existing > 0 && !*reset {
		return fmt.Errorf("database already holds %d comments; re-run with -reset to replace them", existing)
	}
	if *reset {
		fmt.Printf("deleting %d existing comments and everything attached to them\n", existing)
		if err := clear(ctx, pool); err != nil {
			return err
		}
	}

	fmt.Printf("generating %d comments over the last %d day(s)\n", *total, *days)
	rng := rand.New(rand.NewPCG(*seed, *seed>>7))
	feed := generate(rng, *total, *days, *degradedPct/100)

	if err := write(ctx, pool, feed); err != nil {
		return err
	}
	feed.report()
	return nil
}

func clear(ctx context.Context, pool *pgxpool.Pool) error {
	// One statement: moderator_actions, analysis_results and
	// moderation_decisions all cascade from comments.
	for _, stmt := range []string{
		`TRUNCATE moderator_actions, analysis_results, moderation_decisions, comments, sessions RESTART IDENTITY CASCADE`,
		`TRUNCATE request_metrics RESTART IDENTITY`,
	} {
		if _, err := pool.Exec(ctx, stmt); err != nil {
			return fmt.Errorf("clear: %w", err)
		}
	}
	return nil
}

// ------------------------------------------------------------------ feed

type commentRow struct {
	ID        uuid.UUID
	SessionID uuid.UUID
	Text      string
	SHA       []byte
	Result    []byte
	Latency   float64
	QueueWait float64
	FromCache bool
	CreatedAt time.Time
}

type resultRow struct {
	CommentID uuid.UUID
	Code      string
	Score     float64
	Threshold *float64
	Fired     *bool
	Source    string
	CreatedAt time.Time
}

type decisionRow struct {
	CommentID   uuid.UUID
	Verdict     *string
	FiredTypes  []string
	Guards      []string
	Degraded    bool
	Explanation string
	CreatedAt   time.Time
}

type actionRow struct {
	CommentID uuid.UUID
	Action    string
	SessionID uuid.UUID
	CreatedAt time.Time
}

type metricRow struct {
	Endpoint  string
	Method    string
	Status    int16
	Latency   float64
	QueueWait *float64
	CacheHit  bool
	CreatedAt time.Time
}

type feed struct {
	sessions  []sessionRow
	comments  []commentRow
	results   []resultRow
	decisions []decisionRow
	actions   []actionRow
	metrics   []metricRow

	detected  int
	pending   int
	reviewed  int
	auto      int
	byCode    map[string]int
	offensive int
}

type sessionRow struct {
	ID       uuid.UUID
	Nickname string
	IP       string
}

// weighted picks one sample from a list, by Weight.
func weighted(rng *rand.Rand, list []sample) sample {
	sum := 0
	for _, s := range list {
		sum += s.Weight
	}
	n := rng.IntN(sum)
	for _, s := range list {
		n -= s.Weight
		if n < 0 {
			return s
		}
	}
	return list[len(list)-1]
}

// hourWeight is how busy the feed is at a given local hour: quiet at night,
// busy at lunchtime and in the evening.
func hourWeight(hour int) float64 {
	weights := [24]float64{
		0.35, 0.22, 0.14, 0.10, 0.10, 0.14, // 00-05
		0.30, 0.55, 0.80, 0.90, 0.95, 1.00, // 06-11
		1.20, 1.15, 1.00, 0.95, 1.05, 1.20, // 12-17
		1.35, 1.45, 1.55, 1.40, 1.05, 0.65, // 18-23
	}
	return weights[hour]
}

// pickTime draws a moment in the window, following the daily curve, with a
// slow upward trend across the fortnight. The curve alone keeps the "Canlı"
// hour busy; nothing is injected into it, so the panel's change against the
// previous hour stays a believable number instead of a spike.
func pickTime(rng *rand.Rand, start, now time.Time, days int) time.Time {
	for range 40 {
		offset := time.Duration(rng.Float64() * float64(now.Sub(start)))
		t := start.Add(offset)
		// Later days carry a little more traffic than the first ones.
		dayIndex := int(t.Sub(start).Hours() / 24)
		trend := 0.88 + 0.12*float64(dayIndex)/math.Max(1, float64(days-1))
		if rng.Float64() < hourWeight(t.Hour())/1.55*trend {
			return t
		}
	}
	return start.Add(time.Duration(rng.Float64() * float64(now.Sub(start))))
}

// uuidV7At builds a time-ordered UUIDv7 stamped with t, so the panel's
// (created_at, id) cursor walks the demo feed in the right order.
func uuidV7At(t time.Time, rng *rand.Rand) uuid.UUID {
	var id uuid.UUID
	ms := uint64(t.UnixMilli())
	binary.BigEndian.PutUint16(id[0:2], uint16(ms>>32))
	binary.BigEndian.PutUint32(id[2:6], uint32(ms))
	binary.BigEndian.PutUint64(id[8:16], rng.Uint64())
	binary.BigEndian.PutUint16(id[6:8], uint16(rng.Uint32()))
	id[6] = (id[6] & 0x0f) | 0x70 // version 7
	id[8] = (id[8] & 0x3f) | 0x80 // variant 10
	return id
}

func generate(rng *rand.Rand, total, days int, degradedRate float64) *feed {
	now := time.Now()
	start := now.Add(-time.Duration(days) * 24 * time.Hour)

	f := &feed{byCode: map[string]int{}}
	for i, nick := range nicknames {
		f.sessions = append(f.sessions, sessionRow{
			ID:       uuidV7At(start.Add(time.Duration(i)*time.Minute), rng),
			Nickname: nick,
			IP:       fmt.Sprintf("192.168.1.%d", 20+i),
		})
	}

	for range total {
		created := pickTime(rng, start, now, days)
		session := f.sessions[rng.IntN(len(f.sessions))]

		var s sample
		switch draw := rng.Float64(); {
		case draw < shareClean:
			s = weighted(rng, cleanSamples)
		case draw < shareClean+shareGuarded:
			s = weighted(rng, guardedSamples)
		case draw < shareClean+shareGuarded+shareBorderline:
			s = weighted(rng, borderlineSamples)
		default:
			s = weighted(rng, detectedSamples)
		}

		id := uuidV7At(created, rng)
		a := analyse(s, rng, rng.Float64() < degradedRate)
		a.Result["trace_id"] = id.String()
		a.Result["artifact_hash"] = artifactHash
		payload, err := json.Marshal(a.Result)
		if err != nil {
			panic(err) // the map is built here; a failure is a bug, not input
		}
		sum := sha256.Sum256([]byte(s.Text))

		f.comments = append(f.comments, commentRow{
			ID: id, SessionID: session.ID, Text: s.Text, SHA: sum[:], Result: payload,
			Latency: a.LatencyMS, QueueWait: a.QueueWaitMS,
			FromCache: rng.Float64() < 0.18, CreatedAt: created,
		})
		for _, c := range a.Content {
			f.results = append(f.results, resultRow{
				CommentID: id, Code: c.Code, Score: c.Score, Threshold: c.Threshold,
				Fired: c.Fired, Source: c.Source, CreatedAt: created,
			})
		}
		f.decisions = append(f.decisions, decisionRow{
			CommentID: id, Verdict: a.Verdict, FiredTypes: a.FiredTypes, Guards: a.GuardsActive,
			Degraded: a.Degraded, Explanation: a.Explanation, CreatedAt: created,
		})
		f.metrics = append(f.metrics, metricRow{
			Endpoint: "/api/analyze", Method: "POST", Status: 200,
			Latency:   a.LatencyMS + a.QueueWaitMS + 2 + rng.Float64()*8,
			QueueWait: &a.QueueWaitMS, CacheHit: false, CreatedAt: created,
		})

		f.tally(a)
		f.maybeAct(rng, id, a, created, now)
	}
	return f
}

// tally counts what the dashboard will show, so the seeder can report it.
func (f *feed) tally(a analysed) {
	if a.Detected {
		f.detected++
	}
	for _, code := range a.FiredTypes {
		f.byCode[code]++
	}
	if len(a.FiredTypes) == 0 && a.Detected {
		f.offensive++
	}
}

// maybeAct records a moderator's decision on some of the comments that asked
// for a person, and leaves the rest in the queue: those are the Human Review
// number on the dashboard.
func (f *feed) maybeAct(rng *rand.Rand, id uuid.UUID, a analysed, created, now time.Time) {
	needsPerson := a.Verdict != nil && (*a.Verdict == "review" || *a.Verdict == "escalate")
	switch {
	case needsPerson:
		f.pending++
	case a.Verdict != nil && (*a.Verdict == "block" || *a.Verdict == "nudge"):
		f.auto++
		return
	default:
		return
	}
	// A moderation queue is a working queue, not an archive: yesterday's items
	// have almost all been dealt with, and what is still waiting is recent.
	age := now.Sub(created)
	handled := 0.35
	if age > 2*time.Hour {
		handled = 0.80
	}
	if age > 24*time.Hour {
		handled = 0.985
	}
	if rng.Float64() >= handled {
		return
	}

	// What a moderator did, weighted by how severe the verdict was.
	var action string
	switch draw := rng.Float64(); {
	case draw < 0.34:
		action = store.ActionApprove
	case draw < 0.62:
		action = store.ActionHide
	case draw < 0.84:
		action = store.ActionRemove
	case draw < 0.94:
		action = store.ActionFalsePositive
	default:
		action = store.ActionQueue
	}

	// A person answered somewhere between a minute and six hours later.
	delay := time.Duration(60+rng.IntN(6*3600)) * time.Second
	at := created.Add(delay)
	if at.After(now) {
		at = now.Add(-time.Duration(rng.IntN(120)) * time.Second)
	}
	f.actions = append(f.actions, actionRow{
		CommentID: id, Action: action,
		SessionID: f.sessions[rng.IntN(len(f.sessions))].ID, CreatedAt: at,
	})
	if action == store.ActionApprove || action == store.ActionHide || action == store.ActionRemove {
		f.pending--
		f.reviewed++
	}
}

func (f *feed) report() {
	fmt.Println()
	fmt.Printf("  sessions            %d\n", len(f.sessions))
	fmt.Printf("  comments analysed   %d\n", len(f.comments))
	fmt.Printf("  detected            %d (%.1f%%)\n", f.detected, 100*float64(f.detected)/float64(len(f.comments)))
	fmt.Printf("  human review left   %d\n", f.pending)
	fmt.Printf("  handled by a person %d\n", f.reviewed)
	fmt.Printf("  automatic action    %d\n", f.auto)
	fmt.Printf("  offensive score only %d\n", f.offensive)
	fmt.Println("  per category:")
	for _, code := range []string{"A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4", "C5", "D1"} {
		if n := f.byCode[code]; n > 0 {
			fmt.Printf("    %-3s %d\n", code, n)
		}
	}
}

// ----------------------------------------------------------------- writing

func write(ctx context.Context, pool *pgxpool.Pool, f *feed) error {
	sessions := make([][]any, len(f.sessions))
	for i, s := range f.sessions {
		sessions[i] = []any{s.ID, s.Nickname, s.IP}
	}
	if err := copyRows(ctx, pool, "sessions", []string{"id", "nickname", "ip"}, sessions); err != nil {
		return err
	}

	comments := make([][]any, len(f.comments))
	for i, c := range f.comments {
		comments[i] = []any{
			c.ID, c.SessionID, c.Text, c.SHA, artifactHash, c.Result,
			c.Latency, c.QueueWait, c.FromCache, c.CreatedAt,
		}
	}
	if err := copyRows(ctx, pool, "comments",
		[]string{"id", "session_id", "raw_text", "text_sha256", "artifact_hash", "result", "latency_ms", "queue_wait_ms", "from_cache", "created_at"},
		comments); err != nil {
		return err
	}

	results := make([][]any, len(f.results))
	for i, r := range f.results {
		results[i] = []any{
			r.CommentID, r.Code, r.Score, r.Threshold, r.Fired,
			"model", r.Source, artifactHash, r.CreatedAt,
		}
	}
	if err := copyRows(ctx, pool, "analysis_results",
		[]string{"comment_id", "offense_type", "score", "threshold", "fired", "engine", "source", "model_version", "created_at"},
		results); err != nil {
		return err
	}

	decisions := make([][]any, len(f.decisions))
	for i, d := range f.decisions {
		decisions[i] = []any{d.CommentID, d.Verdict, d.FiredTypes, d.Guards, d.Degraded, d.Explanation, d.CreatedAt}
	}
	if err := copyRows(ctx, pool, "moderation_decisions",
		[]string{"comment_id", "final_action", "fired_types", "guards_active", "degraded", "explanation", "created_at"},
		decisions); err != nil {
		return err
	}

	actions := make([][]any, len(f.actions))
	for i, a := range f.actions {
		actions[i] = []any{a.CommentID, a.Action, a.SessionID, a.CreatedAt}
	}
	if err := copyRows(ctx, pool, "moderator_actions",
		[]string{"comment_id", "action", "session_id", "created_at"}, actions); err != nil {
		return err
	}

	metrics := make([][]any, len(f.metrics))
	for i, m := range f.metrics {
		metrics[i] = []any{m.Endpoint, m.Method, m.Status, m.Latency, m.QueueWait, nil, m.CacheHit, m.CreatedAt}
	}
	return copyRows(ctx, pool, "request_metrics",
		[]string{"endpoint", "method", "status_code", "latency_ms", "queue_wait_ms", "batch_size", "cache_hit", "created_at"},
		metrics)
}

func copyRows(ctx context.Context, pool *pgxpool.Pool, table string, columns []string, rows [][]any) error {
	if len(rows) == 0 {
		return nil
	}
	for start := 0; start < len(rows); start += copyChunk {
		end := min(start+copyChunk, len(rows))
		if _, err := pool.CopyFrom(ctx, pgx.Identifier{table}, columns, pgx.CopyFromRows(rows[start:end])); err != nil {
			return fmt.Errorf("copy into %s: %w", table, err)
		}
	}
	fmt.Printf("  wrote %6d rows into %s\n", len(rows), table)
	return nil
}
