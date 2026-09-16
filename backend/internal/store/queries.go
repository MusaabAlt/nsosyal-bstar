package store

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/netip"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
)

// ErrBadCursor means the pagination cursor was not produced by this server.
var ErrBadCursor = errors.New("invalid cursor")

// Queries holds the read and session queries. Every call carries its own
// timeout, so a slow database never holds a request past query_timeout.
type Queries struct {
	pool    *pgxpool.Pool
	timeout time.Duration
}

func NewQueries(pool *pgxpool.Pool, timeout time.Duration) *Queries {
	return &Queries{pool: pool, timeout: timeout}
}

func (q *Queries) ctx(parent context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(parent, q.timeout)
}

// Ping reports whether Postgres answers (used by /api/health).
func (q *Queries) Ping(ctx context.Context) error {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	return q.pool.Ping(ctx)
}

// CreateSession stores an anonymous session. It is written synchronously so
// the comments that reference it can never violate the foreign key.
func (q *Queries) CreateSession(ctx context.Context, nickname string, ip netip.Addr) (domain.Session, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	s := domain.Session{ID: uuid.Must(uuid.NewV7()), Nickname: nickname}
	err := q.pool.QueryRow(ctx,
		`INSERT INTO sessions (id, nickname, ip) VALUES ($1, $2, $3) RETURNING created_at`,
		s.ID, nickname, ip).Scan(&s.CreatedAt)
	return s, err
}

func (q *Queries) SessionExists(ctx context.Context, id uuid.UUID) (bool, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	var exists bool
	err := q.pool.QueryRow(ctx, `SELECT EXISTS (SELECT 1 FROM sessions WHERE id = $1)`, id).Scan(&exists)
	return exists, err
}

// FeedItem is one comment with the decision Python made for it.
type FeedItem struct {
	ID           uuid.UUID       `json:"id"`
	Nickname     string          `json:"nickname"`
	Text         string          `json:"text"`
	CreatedAt    time.Time       `json:"created_at"`
	FinalAction  *string         `json:"final_action"`
	FiredTypes   []string        `json:"fired_types"`
	GuardsActive []string        `json:"guards_active"`
	Degraded     bool            `json:"degraded"`
	Explanation  string          `json:"explanation"`
	Reasons      []Reason        `json:"reasons,omitempty"`
	Result       json.RawMessage `json:"result,omitempty"`
}

// Reason is one fired offense type with its own score and threshold.
type Reason struct {
	Type      string   `json:"type"`
	Score     float64  `json:"score"`
	Threshold *float64 `json:"threshold"`
	Engine    string   `json:"engine"`
	Source    string   `json:"source"`
}

type Page struct {
	Items      []FeedItem `json:"items"`
	NextCursor string     `json:"next_cursor,omitempty"`
}

// Cursors are opaque to clients: base64 of "created_at|id".
func encodeCursor(t time.Time, id uuid.UUID) string {
	return base64.RawURLEncoding.EncodeToString([]byte(t.UTC().Format(time.RFC3339Nano) + "|" + id.String()))
}

func decodeCursor(s string) (time.Time, uuid.UUID, error) {
	raw, err := base64.RawURLEncoding.DecodeString(s)
	if err != nil {
		return time.Time{}, uuid.Nil, ErrBadCursor
	}
	ts, idStr, ok := strings.Cut(string(raw), "|")
	if !ok {
		return time.Time{}, uuid.Nil, ErrBadCursor
	}
	t, err := time.Parse(time.RFC3339Nano, ts)
	if err != nil {
		return time.Time{}, uuid.Nil, ErrBadCursor
	}
	id, err := uuid.Parse(idStr)
	if err != nil {
		return time.Time{}, uuid.Nil, ErrBadCursor
	}
	return t, id, nil
}

const feedSelect = `
SELECT c.id, s.nickname, c.raw_text, c.created_at,
       d.final_action, d.fired_types, d.guards_active, d.degraded, d.explanation
FROM comments c
JOIN sessions s ON s.id = c.session_id
JOIN moderation_decisions d ON d.comment_id = c.id
WHERE ($1::timestamptz IS NULL OR (c.created_at, c.id) < ($1, $2))
  AND ($3::boolean = false OR d.final_action IS DISTINCT FROM 'clean')
ORDER BY c.created_at DESC, c.id DESC
LIMIT $4`

// Feed lists comments newest first. flaggedOnly keeps everything whose
// decision is not clean (including failed decisions), with per-type reasons.
func (q *Queries) Feed(ctx context.Context, limit int, cursor string, flaggedOnly bool) (Page, error) {
	var (
		afterTime *time.Time
		afterID   uuid.UUID
	)
	if cursor != "" {
		t, id, err := decodeCursor(cursor)
		if err != nil {
			return Page{}, err
		}
		afterTime, afterID = &t, id
	}

	ctx, cancel := q.ctx(ctx)
	defer cancel()
	// One extra row tells whether there is a next page.
	rows, err := q.pool.Query(ctx, feedSelect, afterTime, afterID, flaggedOnly, limit+1)
	if err != nil {
		return Page{}, err
	}
	items, err := pgx.CollectRows(rows, func(row pgx.CollectableRow) (FeedItem, error) {
		var it FeedItem
		err := row.Scan(&it.ID, &it.Nickname, &it.Text, &it.CreatedAt,
			&it.FinalAction, &it.FiredTypes, &it.GuardsActive, &it.Degraded, &it.Explanation)
		return it, err
	})
	if err != nil {
		return Page{}, err
	}

	page := Page{Items: items}
	if len(items) > limit {
		page.Items = items[:limit]
		last := page.Items[limit-1]
		page.NextCursor = encodeCursor(last.CreatedAt, last.ID)
	}
	if flaggedOnly && len(page.Items) > 0 {
		if err := q.attachReasons(ctx, page.Items); err != nil {
			return Page{}, err
		}
	}
	return page, nil
}

func (q *Queries) attachReasons(ctx context.Context, items []FeedItem) error {
	ids := make([]uuid.UUID, len(items))
	index := make(map[uuid.UUID]int, len(items))
	for i, it := range items {
		ids[i] = it.ID
		index[it.ID] = i
	}
	rows, err := q.pool.Query(ctx, `
		SELECT comment_id, offense_type, score, threshold, engine, source
		FROM analysis_results
		WHERE comment_id = ANY($1) AND fired
		ORDER BY score DESC`, ids)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var (
			id uuid.UUID
			r  Reason
		)
		if err := rows.Scan(&id, &r.Type, &r.Score, &r.Threshold, &r.Engine, &r.Source); err != nil {
			return err
		}
		if i, ok := index[id]; ok {
			items[i].Reasons = append(items[i].Reasons, r)
		}
	}
	return rows.Err()
}

// DashboardCounts are the database half of /api/stats.
type DashboardCounts struct {
	Comments    int64            `json:"comments"`
	Sessions    int64            `json:"sessions"`
	Degraded    int64            `json:"degraded"`
	PerType     map[string]int64 `json:"fired_per_type"`
	PerAction   map[string]int64 `json:"per_action"`
	FromCache   int64            `json:"from_cache"`
	GeneratedAt time.Time        `json:"generated_at"`
}

func (q *Queries) DashboardCounts(ctx context.Context) (DashboardCounts, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	out := DashboardCounts{PerType: map[string]int64{}, PerAction: map[string]int64{}, GeneratedAt: time.Now()}

	err := q.pool.QueryRow(ctx, `
		SELECT (SELECT count(*) FROM comments),
		       (SELECT count(*) FROM sessions),
		       (SELECT count(*) FROM moderation_decisions WHERE degraded),
		       (SELECT count(*) FROM comments WHERE from_cache)`).
		Scan(&out.Comments, &out.Sessions, &out.Degraded, &out.FromCache)
	if err != nil {
		return out, fmt.Errorf("totals: %w", err)
	}

	if err := q.countInto(ctx, out.PerType,
		`SELECT offense_type, count(*) FROM analysis_results WHERE fired GROUP BY offense_type`); err != nil {
		return out, fmt.Errorf("per type: %w", err)
	}
	if err := q.countInto(ctx, out.PerAction,
		`SELECT coalesce(final_action, 'decision_failed'), count(*) FROM moderation_decisions GROUP BY 1`); err != nil {
		return out, fmt.Errorf("per action: %w", err)
	}
	return out, nil
}

func (q *Queries) countInto(ctx context.Context, into map[string]int64, sql string) error {
	rows, err := q.pool.Query(ctx, sql)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var (
			key string
			n   int64
		)
		if err := rows.Scan(&key, &n); err != nil {
			return err
		}
		into[key] = n
	}
	return rows.Err()
}

// encodeCursorKey is encodeCursor for rows keyed by text instead of a uuid.
func encodeCursorKey(t time.Time, key string) string {
	return base64.RawURLEncoding.EncodeToString([]byte(t.UTC().Format(time.RFC3339Nano) + "|" + key))
}

func decodeCursorKey(s string) (time.Time, string, error) {
	raw, err := base64.RawURLEncoding.DecodeString(s)
	if err != nil {
		return time.Time{}, "", ErrBadCursor
	}
	ts, key, ok := strings.Cut(string(raw), "|")
	if !ok || key == "" {
		return time.Time{}, "", ErrBadCursor
	}
	t, err := time.Parse(time.RFC3339Nano, ts)
	if err != nil {
		return time.Time{}, "", ErrBadCursor
	}
	return t, key, nil
}
