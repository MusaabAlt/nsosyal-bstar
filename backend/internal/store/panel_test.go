package store

import (
	"context"
	"net/netip"
	"testing"
	"time"

	"github.com/google/uuid"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

// Stores degraded (review, nothing fired), clean, flagged (escalate: B2 and
// the binary offensive score fired, LEET active) and guard (clean) comments.
func seedPanel(t *testing.T) (*Queries, map[string]uuid.UUID, uuid.UUID) {
	t.Helper()
	pool := testPool(t)
	ctx := context.Background()
	freshSchema(t, pool)
	q := NewQueries(pool, 3*time.Second)
	session, err := q.CreateSession(ctx, "ayşe", netip.MustParseAddr("192.168.1.21"))
	if err != nil {
		t.Fatal(err)
	}
	w := NewWriter(pool, testWriterConfig(), nil)
	go w.Run()
	ids := map[string]uuid.UUID{}
	base := time.Now().Add(-2 * time.Minute)
	for i, name := range []string{"degraded", "clean", "flagged", "guard"} {
		r := record(t, session.ID, name, base.Add(time.Duration(i)*time.Second))
		ids[name] = r.CommentID
		w.EnqueueAnalysis(r)
	}
	w.EnqueueMetric(domain.RequestMetric{Endpoint: "/api/comments", Method: "POST", StatusCode: 201, LatencyMS: 40, CreatedAt: time.Now()})
	w.EnqueueMetric(domain.RequestMetric{Endpoint: "/api/comments", Method: "POST", StatusCode: 503, LatencyMS: 2, CreatedAt: time.Now()})
	w.EnqueueMetric(domain.RequestMetric{Endpoint: "/api/stats", Method: "GET", StatusCode: 200, LatencyMS: 1, CreatedAt: time.Now()})
	if err := w.Close(ctx); err != nil {
		t.Fatal(err)
	}
	return q, ids, session.ID
}

func itemIDs(items []PanelItem) []uuid.UUID {
	out := []uuid.UUID{}
	for _, it := range items {
		out = append(out, it.ID)
	}
	return out
}

func TestPanelQueueAndActions(t *testing.T) {
	q, ids, session := seedPanel(t)
	ctx := context.Background()

	counts, err := q.QueueCounts(ctx)
	if err != nil {
		t.Fatal(err)
	}
	// degraded (review) and flagged (escalate) ask for a person; only flagged detected anything.
	if counts != (QueueCounts{Pending: 2, PendingDetected: 1, Reviewed: 0, Auto: 0}) {
		t.Fatalf("counts = %+v", counts)
	}

	detected, err := q.Items(ctx, ItemFilter{DetectedOnly: true, Limit: 10})
	if err != nil {
		t.Fatal(err)
	}
	if len(detected.Items) != 1 || detected.Items[0].ID != ids["flagged"] || !detected.Items[0].Detected || len(detected.Items[0].Result) == 0 {
		t.Fatalf("detected = %+v", itemIDs(detected.Items))
	}
	byCode, err := q.Items(ctx, ItemFilter{Code: BinaryOffensive, Limit: 10})
	if err != nil || len(byCode.Items) != 1 {
		t.Fatalf("binary_offensive filter = %v %v", itemIDs(byCode.Items), err)
	}

	missing, err := q.AddActions(ctx, []uuid.UUID{ids["flagged"], uuid.Must(uuid.NewV7())}, ActionHide, &session)
	if err != nil {
		t.Fatal(err)
	}
	if len(missing) != 1 {
		t.Fatalf("missing = %v", missing)
	}
	// A moderator queues a clean comment: it becomes pending.
	if _, err := q.AddActions(ctx, []uuid.UUID{ids["clean"]}, ActionQueue, nil); err != nil {
		t.Fatal(err)
	}
	counts, _ = q.QueueCounts(ctx)
	if counts != (QueueCounts{Pending: 2, PendingDetected: 0, Reviewed: 1, Auto: 0}) {
		t.Fatalf("counts after actions = %+v", counts)
	}
	reviewed, err := q.Items(ctx, ItemFilter{Status: StatusReviewed, Limit: 10})
	if err != nil || len(reviewed.Items) != 1 || *reviewed.Items[0].LatestAction != ActionHide {
		t.Fatalf("reviewed = %+v %v", reviewed.Items, err)
	}

	search, err := q.Items(ctx, ItemFilter{Query: "b1tir", Limit: 10})
	if err != nil || len(search.Items) != 1 {
		t.Fatalf("search = %v %v", itemIDs(search.Items), err)
	}
	if none, err := q.Items(ctx, ItemFilter{Query: "%", Limit: 10}); err != nil || len(none.Items) != 0 {
		t.Fatalf("a %% search must be literal: %v %v", itemIDs(none.Items), err)
	}

	detail, err := q.Item(ctx, ids["flagged"])
	if err != nil {
		t.Fatal(err)
	}
	if len(detail.Actions) != 1 || detail.Actions[0].Nickname == nil || *detail.Actions[0].Nickname != "ayşe" {
		t.Fatalf("actions = %+v", detail.Actions)
	}
	if len(detail.Previous) != 2 || detail.Previous[0].ID != ids["clean"] {
		t.Fatalf("previous = %v", itemIDs(detail.Previous))
	}
	if _, err := q.Item(ctx, uuid.Must(uuid.NewV7())); err != ErrNotFound {
		t.Fatalf("unknown id: %v", err)
	}

	// Events: two moderator actions plus one system detection, paginated.
	var got []Event
	cursor := ""
	for {
		page, err := q.Events(ctx, EventFilter{Limit: 2, Cursor: cursor})
		if err != nil {
			t.Fatal(err)
		}
		got = append(got, page.Items...)
		if page.NextCursor == "" {
			break
		}
		cursor = page.NextCursor
	}
	if len(got) != 3 {
		t.Fatalf("events = %+v", got)
	}
	if got[0].Kind != "moderator" || got[2].Kind != "system" || got[2].CommentID != ids["flagged"] {
		t.Fatalf("event order = %+v", got)
	}
	if mods, _ := q.Events(ctx, EventFilter{Kind: "moderator", Limit: 10}); len(mods.Items) != 2 {
		t.Fatalf("moderator events = %d", len(mods.Items))
	}
}

func TestPanelOverviewAndMetrics(t *testing.T) {
	q, _, _ := seedPanel(t)
	ctx := context.Background()
	now := time.Now()
	r := Range{Start: now.Add(-58 * time.Minute), Now: now, Bucket: 5 * time.Minute, Buckets: 12}

	counts, err := q.Overview(ctx, r, []string{"A1", "B2", BinaryOffensive})
	if err != nil {
		t.Fatal(err)
	}
	if counts.Analysed != (Pair{Current: 4}) || counts.Detected != (Pair{Current: 1}) || counts.Automatic != (Pair{}) {
		t.Fatalf("totals = %+v", counts)
	}
	// degraded -> review with nothing fired, flagged -> escalate and detected.
	if counts.Verdicts != (VerdictCounts{Review: 1, Escalate: 1, Clean: 2}) {
		t.Fatalf("verdicts = %+v", counts.Verdicts)
	}
	// The dashboard divides "İnsan incelemesi" (review + escalate) by Analysed,
	// which is only sound because the six buckets partition the analysed rows.
	// Assert the partition itself, not the quotient: the card read 200% on this
	// very fixture while it divided by Detected (2 asking for a person, 1
	// detected), because the fail-closed rule sends undetected comments to a
	// person too.
	v := counts.Verdicts
	if sum := v.Block + v.Escalate + v.Review + v.Nudge + v.Clean + v.Undecided; sum != counts.Analysed.Current {
		t.Fatalf("verdicts sum to %d, analysed is %d: they must partition the same rows", sum, counts.Analysed.Current)
	}
	if v.Review+v.Escalate > counts.Analysed.Current {
		t.Fatalf("human review %d exceeds analysed %d", v.Review+v.Escalate, counts.Analysed.Current)
	}
	want := map[string]int64{"A1": 0, "B2": 1, BinaryOffensive: 1}
	for _, s := range counts.Series {
		if s.Total != want[s.Code] || len(s.Buckets) != 12 || s.Buckets[11] != want[s.Code] {
			t.Errorf("series %s = %+v", s.Code, s)
		}
	}
	if len(counts.Patterns) != 1 || counts.Patterns[0] != (PatternCount{Code: "LEET", Count: 1}) {
		t.Fatalf("patterns = %+v", counts.Patterns)
	}

	if n, err := q.ActiveDevices(ctx, 5*time.Minute); err != nil || n != 1 {
		t.Fatalf("active devices = %d %v", n, err)
	}

	series, err := q.RequestSeries(ctx, now.Truncate(time.Minute).Add(-29*time.Minute), time.Minute, 30)
	if err != nil {
		t.Fatal(err)
	}
	last := len(series.Analyses) - 1
	if series.Analyses[last].Requests != 2 || series.Analyses[last].Errors != 1 || series.AllRequests[last].Requests != 3 {
		t.Fatalf("metric series = %+v / %+v", series.Analyses[last], series.AllRequests[last])
	}
	if series.Analyses[0].P95MS != nil {
		t.Fatal("an empty minute must have no latency, not 0")
	}
}
