package store

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/netip"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/google/uuid"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

func mockResult(t *testing.T, name string) (json.RawMessage, domain.ResultSummary) {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("..", "..", "..", "frontend", "src", "api", "mocks", name+".json"))
	if err != nil {
		t.Fatal(err)
	}
	s, err := domain.ParseResult(raw)
	if err != nil {
		t.Fatal(err)
	}
	return raw, s
}

func testWriterConfig() WriterConfig {
	return WriterConfig{CommentBuffer: 100, MetricsBuffer: 100, BatchSize: 50, FlushInterval: 20 * time.Millisecond, WriteTimeout: 5 * time.Second}
}

func record(t *testing.T, sessionID uuid.UUID, name string, at time.Time) domain.AnalysisRecord {
	raw, s := mockResult(t, name)
	sum := sha256.Sum256([]byte(s.Text))
	wait := 3.5
	return domain.AnalysisRecord{
		CommentID: uuid.Must(uuid.NewV7()), SessionID: sessionID, Text: s.Text, TextSHA256: sum[:],
		Result: raw, Summary: s, QueueWaitMS: &wait, CreatedAt: at,
	}
}

func TestWriterStoresAndQueriesReadBack(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()
	freshSchema(t, pool)
	q := NewQueries(pool, 3*time.Second)

	session, err := q.CreateSession(ctx, "emin", netip.MustParseAddr("192.168.1.20"))
	if err != nil {
		t.Fatal(err)
	}
	if ok, err := q.SessionExists(ctx, session.ID); err != nil || !ok {
		t.Fatalf("session not found: %v %v", ok, err)
	}

	w := NewWriter(pool, testWriterConfig(), nil)
	go w.Run()

	base := time.Now().Add(-time.Minute)
	names := []string{"degraded", "clean", "flagged", "guard", "flagged"}
	for i, name := range names {
		if !w.EnqueueAnalysis(record(t, session.ID, name, base.Add(time.Duration(i)*time.Second))) {
			t.Fatal("enqueue refused")
		}
	}
	for range 10 {
		code := 200
		w.EnqueueMetric(domain.RequestMetric{Endpoint: "/api/comments", Method: "POST", StatusCode: code, LatencyMS: 12.5, CreatedAt: time.Now()})
	}
	if err := w.Close(ctx); err != nil {
		t.Fatal(err)
	}
	if s := w.Stats(); s.AnalysesWritten != 5 || s.MetricsWritten != 10 || s.AnalysesDropped != 0 {
		t.Fatalf("writer stats = %+v", s)
	}

	// Feed: newest first, paginated.
	page, err := q.Feed(ctx, 2, "", false)
	if err != nil {
		t.Fatal(err)
	}
	if len(page.Items) != 2 || page.NextCursor == "" {
		t.Fatalf("page 1 = %d items, cursor %q", len(page.Items), page.NextCursor)
	}
	if page.Items[0].Nickname != "emin" || !page.Items[0].CreatedAt.After(page.Items[1].CreatedAt) {
		t.Fatalf("page 1 order/nickname wrong: %+v", page.Items)
	}
	seen := map[uuid.UUID]bool{}
	cursor := ""
	for {
		p, err := q.Feed(ctx, 2, cursor, false)
		if err != nil {
			t.Fatal(err)
		}
		for _, it := range p.Items {
			if seen[it.ID] {
				t.Fatalf("duplicate %s across pages", it.ID)
			}
			seen[it.ID] = true
		}
		if p.NextCursor == "" {
			break
		}
		cursor = p.NextCursor
	}
	if len(seen) != 5 {
		t.Fatalf("paged through %d items, want 5", len(seen))
	}

	// Flagged: everything not clean, with its own score and threshold per type.
	flagged, err := q.Feed(ctx, 10, "", true)
	if err != nil {
		t.Fatal(err)
	}
	if len(flagged.Items) != 3 { // degraded (review) + 2 flagged (escalate)
		t.Fatalf("flagged = %d items, want 3", len(flagged.Items))
	}
	var withReason int
	for _, it := range flagged.Items {
		if it.FinalAction == nil || *it.FinalAction == "clean" {
			t.Fatalf("clean item in flagged list: %+v", it)
		}
		if len(it.Reasons) > 0 {
			withReason++
			r := it.Reasons[0]
			if r.Type != "B2" || r.Score != 0.87 || r.Threshold == nil || *r.Threshold != 0.5 || r.Engine != "model" {
				t.Fatalf("reason = %+v", r)
			}
		}
	}
	if withReason != 2 {
		t.Fatalf("%d flagged items with reasons, want 2", withReason)
	}

	counts, err := q.DashboardCounts(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if counts.Comments != 5 || counts.Sessions != 1 || counts.Degraded != 1 ||
		counts.PerType["B2"] != 2 || counts.PerAction["escalate"] != 2 || counts.PerAction["clean"] != 2 || counts.PerAction["review"] != 1 {
		t.Fatalf("counts = %+v", counts)
	}

	// The stored result is the exact JSON Python sent.
	var stored json.RawMessage
	if err := pool.QueryRow(ctx, `SELECT result FROM comments WHERE raw_text = 'amcam geldi'`).Scan(&stored); err != nil {
		t.Fatal(err)
	}
	s, err := domain.ParseResult(stored)
	if err != nil || len(s.ActiveGuards()) != 1 {
		t.Fatalf("stored result unreadable: %v %+v", err, s)
	}
}

func TestBadCursorIsRejected(t *testing.T) {
	pool := testPool(t)
	freshSchema(t, pool)
	q := NewQueries(pool, time.Second)
	for _, c := range []string{"!!!", "bm9waXBl", encodeCursorRaw("2026-01-01T00:00:00Z|not-a-uuid")} {
		if _, err := q.Feed(context.Background(), 10, c, false); err != ErrBadCursor {
			t.Errorf("cursor %q: want ErrBadCursor, got %v", c, err)
		}
	}
}

func encodeCursorRaw(s string) string {
	return base64.RawURLEncoding.EncodeToString([]byte(s))
}

func TestOneBadRowDoesNotLoseTheBatch(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()
	freshSchema(t, pool)
	q := NewQueries(pool, 3*time.Second)
	session, err := q.CreateSession(ctx, "x", netip.MustParseAddr("10.0.0.1"))
	if err != nil {
		t.Fatal(err)
	}

	w := NewWriter(pool, testWriterConfig(), nil)
	go w.Run()
	good1 := record(t, session.ID, "clean", time.Now())
	bad := record(t, uuid.Must(uuid.NewV7()), "clean", time.Now()) // unknown session: FK violation
	good2 := record(t, session.ID, "flagged", time.Now())
	for _, r := range []domain.AnalysisRecord{good1, bad, good2} {
		w.EnqueueAnalysis(r)
	}
	if err := w.Close(ctx); err != nil {
		t.Fatal(err)
	}
	s := w.Stats()
	if s.AnalysesWritten != 2 || s.AnalysesDropped != 1 || s.LastError == "" {
		t.Fatalf("stats = %+v", s)
	}
}

func TestEnqueueNeverBlocksWhenFull(t *testing.T) {
	cfg := testWriterConfig()
	cfg.CommentBuffer, cfg.MetricsBuffer = 1, 1
	w := NewWriter(nil, cfg, nil) // not running: nothing drains the buffers
	start := time.Now()
	for range 1000 {
		w.EnqueueAnalysis(domain.AnalysisRecord{})
		w.EnqueueMetric(domain.RequestMetric{})
	}
	if time.Since(start) > 100*time.Millisecond {
		t.Fatal("enqueue blocked on a full buffer")
	}
	if s := w.Stats(); s.AnalysesDropped != 999 || s.MetricsDropped != 999 {
		t.Fatalf("stats = %+v", s)
	}
}
