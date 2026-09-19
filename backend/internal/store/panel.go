package store

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

// The moderation panel's reads and the moderator actions. Every number the
// panel shows is counted here, from what was actually stored; nothing is
// estimated.

// BinaryOffensive is the decision layer's channel-level offensive score. It is
// not a content code, so it lives only inside the stored result.
const BinaryOffensive = "binary_offensive"

// detectedSQL is true when the decision layer fired at least one signal for
// the comment: a content code or the binary offensive score. The verdict
// alone is not used: while modules are stubs every verdict is "review",
// including clean sentences.
const detectedSQL = `(cardinality(d.fired_types) > 0 OR coalesce(c.result #>> '{signals,decision,binary_offensive,fired}' = 'true', false))`

// Moderator actions (migration 00002).
const (
	ActionApprove       = "approve"
	ActionHide          = "hide"
	ActionRemove        = "remove"
	ActionQueue         = "queue"
	ActionFalsePositive = "false_positive"
)

func ValidModeratorAction(a string) bool {
	switch a {
	case ActionApprove, ActionHide, ActionRemove, ActionQueue, ActionFalsePositive:
		return true
	}
	return false
}

// Queue statuses.
const (
	StatusPending  = "pending"  // the decision asks for a person, or a moderator queued it
	StatusReviewed = "reviewed" // a moderator approved, hid or removed it
	StatusAuto     = "auto"     // the decision layer acted by itself (block, nudge)
)

const statusSQL = `
CASE
  WHEN la.action IN ('approve', 'hide', 'remove') THEN 'reviewed'
  WHEN la.action IN ('queue', 'false_positive') THEN 'pending'
  WHEN d.final_action IS NULL OR d.final_action IN ('review', 'escalate') THEN 'pending'
  WHEN d.final_action IN ('block', 'nudge') THEN 'auto'
  ELSE 'none'
END`

const latestActionJoin = `
LEFT JOIN LATERAL (
  SELECT a.action, a.created_at FROM moderator_actions a
  WHERE a.comment_id = c.id ORDER BY a.created_at DESC, a.id DESC LIMIT 1
) la ON true`

// PanelItem is one analysed comment as the panel lists it.
type PanelItem struct {
	ID           uuid.UUID       `json:"id"`
	Nickname     string          `json:"nickname"`
	Text         string          `json:"text"`
	CreatedAt    time.Time       `json:"created_at"`
	FinalAction  *string         `json:"final_action"`
	FiredTypes   []string        `json:"fired_types"`
	GuardsActive []string        `json:"guards_active"`
	Degraded     bool            `json:"degraded"`
	Explanation  string          `json:"explanation"`
	Detected     bool            `json:"detected"`
	Status       string          `json:"status"` // pending | reviewed | auto | none
	LatestAction *string         `json:"latest_action"`
	LatestAt     *time.Time      `json:"latest_action_at"`
	LatencyMS    float64         `json:"latency_ms"`
	Result       json.RawMessage `json:"result"`
}

type ItemFilter struct {
	Status       string // "" = any
	DetectedOnly bool
	Code         string // a content code or binary_offensive; "" = any
	Query        string // text or nickname contains; "" = any
	SessionID    *uuid.UUID
	Limit        int
	Cursor       string
}

type ItemPage struct {
	Items      []PanelItem `json:"items"`
	NextCursor string      `json:"next_cursor,omitempty"`
}

// likePattern escapes LIKE wildcards so a search is always a plain substring.
func likePattern(q string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return "%" + r.Replace(q) + "%"
}

const itemSelect = `
SELECT c.id, s.nickname, c.raw_text, c.created_at,
       d.final_action, d.fired_types, d.guards_active, d.degraded, d.explanation,
       ` + detectedSQL + `, ` + statusSQL + `, la.action, la.created_at, c.latency_ms, c.result
FROM comments c
JOIN sessions s ON s.id = c.session_id
JOIN moderation_decisions d ON d.comment_id = c.id
` + latestActionJoin

func scanItem(row pgx.CollectableRow) (PanelItem, error) {
	var it PanelItem
	err := row.Scan(&it.ID, &it.Nickname, &it.Text, &it.CreatedAt,
		&it.FinalAction, &it.FiredTypes, &it.GuardsActive, &it.Degraded, &it.Explanation,
		&it.Detected, &it.Status, &it.LatestAction, &it.LatestAt, &it.LatencyMS, &it.Result)
	return it, err
}

// filterSQL is shared by the list and the counts, so a tab's count always
// matches what the tab lists.
const filterSQL = `
  AND ($1::text = '' OR ` + statusSQL + ` = $1)
  AND ($2::boolean = false OR ` + detectedSQL + `)
  AND ($3::text = '' OR $3 = ANY(d.fired_types)
       OR ($3 = 'binary_offensive' AND c.result #>> '{signals,decision,binary_offensive,fired}' = 'true'))
  AND ($4::text = '' OR c.raw_text ILIKE $4 OR s.nickname ILIKE $4)
  AND ($5::uuid IS NULL OR c.session_id = $5)`

// Items lists analysed comments newest first.
func (q *Queries) Items(ctx context.Context, f ItemFilter) (ItemPage, error) {
	var (
		afterTime *time.Time
		afterID   uuid.UUID
	)
	if f.Cursor != "" {
		t, id, err := decodeCursor(f.Cursor)
		if err != nil {
			return ItemPage{}, err
		}
		afterTime, afterID = &t, id
	}
	like := ""
	if f.Query != "" {
		like = likePattern(f.Query)
	}

	ctx, cancel := q.ctx(ctx)
	defer cancel()
	rows, err := q.pool.Query(ctx, itemSelect+`
WHERE ($6::timestamptz IS NULL OR (c.created_at, c.id) < ($6, $7))`+filterSQL+`
ORDER BY c.created_at DESC, c.id DESC
LIMIT $8`, f.Status, f.DetectedOnly, f.Code, like, f.SessionID, afterTime, afterID, f.Limit+1)
	if err != nil {
		return ItemPage{}, err
	}
	items, err := pgx.CollectRows(rows, scanItem)
	if err != nil {
		return ItemPage{}, err
	}
	page := ItemPage{Items: items}
	if len(items) > f.Limit {
		page.Items = items[:f.Limit]
		last := page.Items[f.Limit-1]
		page.NextCursor = encodeCursor(last.CreatedAt, last.ID)
	}
	if page.Items == nil {
		page.Items = []PanelItem{}
	}
	return page, nil
}

// QueueCounts are the queue tab counts.
type QueueCounts struct {
	Pending         int64 `json:"pending"`
	PendingDetected int64 `json:"pending_detected"`
	Reviewed        int64 `json:"reviewed"`
	Auto            int64 `json:"auto"`
}

func (q *Queries) QueueCounts(ctx context.Context) (QueueCounts, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	var out QueueCounts
	err := q.pool.QueryRow(ctx, `
SELECT count(*) FILTER (WHERE st = 'pending'),
       count(*) FILTER (WHERE st = 'pending' AND detected),
       count(*) FILTER (WHERE st = 'reviewed'),
       count(*) FILTER (WHERE st = 'auto')
FROM (
  SELECT `+statusSQL+` AS st, `+detectedSQL+` AS detected
  FROM comments c
  JOIN moderation_decisions d ON d.comment_id = c.id
  `+latestActionJoin+`
) t`).Scan(&out.Pending, &out.PendingDetected, &out.Reviewed, &out.Auto)
	return out, err
}

// ErrNotFound means the comment is not (or not yet) stored.
var ErrNotFound = errors.New("not found")

type ActionRecord struct {
	Action    string    `json:"action"`
	Nickname  *string   `json:"nickname"`
	CreatedAt time.Time `json:"created_at"`
}

type ItemDetail struct {
	Item    PanelItem      `json:"item"`
	Actions []ActionRecord `json:"actions"`
	// The sender's previous comments, newest first (thread context).
	Previous []PanelItem `json:"previous"`
}

func (q *Queries) Item(ctx context.Context, id uuid.UUID) (ItemDetail, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	rows, err := q.pool.Query(ctx, itemSelect+` WHERE c.id = $1`, id)
	if err != nil {
		return ItemDetail{}, err
	}
	items, err := pgx.CollectRows(rows, scanItem)
	if err != nil {
		return ItemDetail{}, err
	}
	if len(items) == 0 {
		return ItemDetail{}, ErrNotFound
	}
	out := ItemDetail{Item: items[0], Actions: []ActionRecord{}, Previous: []PanelItem{}}

	rows, err = q.pool.Query(ctx, `
SELECT a.action, s.nickname, a.created_at
FROM moderator_actions a LEFT JOIN sessions s ON s.id = a.session_id
WHERE a.comment_id = $1 ORDER BY a.created_at DESC, a.id DESC`, id)
	if err != nil {
		return ItemDetail{}, err
	}
	actions, err := pgx.CollectRows(rows, func(row pgx.CollectableRow) (ActionRecord, error) {
		var r ActionRecord
		return r, row.Scan(&r.Action, &r.Nickname, &r.CreatedAt)
	})
	if err != nil {
		return ItemDetail{}, err
	}
	if actions != nil {
		out.Actions = actions
	}

	rows, err = q.pool.Query(ctx, itemSelect+`
WHERE c.session_id = (SELECT session_id FROM comments WHERE id = $1)
  AND (c.created_at, c.id) < ($2, $1)
ORDER BY c.created_at DESC, c.id DESC LIMIT 3`, id, out.Item.CreatedAt)
	if err != nil {
		return ItemDetail{}, err
	}
	previous, err := pgx.CollectRows(rows, scanItem)
	if err != nil {
		return ItemDetail{}, err
	}
	if previous != nil {
		out.Previous = previous
	}
	return out, nil
}

// AddActions records one moderator action for each comment. It returns the
// ids that are not stored (yet): the writer stores comments a moment after
// they are analysed.
func (q *Queries) AddActions(ctx context.Context, ids []uuid.UUID, action string, sessionID *uuid.UUID) (missing []uuid.UUID, err error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	rows, err := q.pool.Query(ctx, `
INSERT INTO moderator_actions (comment_id, action, session_id)
SELECT c.id, $2, (SELECT s.id FROM sessions s WHERE s.id = $3)
FROM comments c WHERE c.id = ANY($1)
RETURNING comment_id`, ids, action, sessionID)
	if err != nil {
		return nil, err
	}
	done, err := pgx.CollectRows(rows, pgx.RowTo[uuid.UUID])
	if err != nil {
		return nil, err
	}
	stored := make(map[uuid.UUID]bool, len(done))
	for _, id := range done {
		stored[id] = true
	}
	for _, id := range ids {
		if !stored[id] {
			missing = append(missing, id)
		}
	}
	return missing, nil
}

// ------------------------------------------------------------------ events

// Event is one line of the history: a moderator action, or a decision the
// system made by itself for a comment where it detected something.
type Event struct {
	Kind        string    `json:"kind"` // moderator | system
	Key         string    `json:"key"`
	CreatedAt   time.Time `json:"created_at"`
	Action      *string   `json:"action"` // moderator action, or the final_action for system events
	Actor       *string   `json:"actor"`  // moderator nickname; null for system events
	CommentID   uuid.UUID `json:"comment_id"`
	Author      string    `json:"author"`
	Text        string    `json:"text"`
	FiredTypes  []string  `json:"fired_types"`
	Detected    bool      `json:"detected"`
	Degraded    bool      `json:"degraded"`
	Explanation string    `json:"explanation"`
}

type EventFilter struct {
	Kind   string // "" | moderator | system
	Query  string
	Limit  int
	Cursor string
}

type EventPage struct {
	Items      []Event `json:"items"`
	NextCursor string  `json:"next_cursor,omitempty"`
}

func (q *Queries) Events(ctx context.Context, f EventFilter) (EventPage, error) {
	var (
		afterTime *time.Time
		afterKey  string
	)
	if f.Cursor != "" {
		t, key, err := decodeCursorKey(f.Cursor)
		if err != nil {
			return EventPage{}, err
		}
		afterTime, afterKey = &t, key
	}
	like := ""
	if f.Query != "" {
		like = likePattern(f.Query)
	}
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	// Keys sort within one timestamp: "m" + zero-padded id, "s" + comment id.
	rows, err := q.pool.Query(ctx, `
SELECT kind, key, created_at, action, actor, comment_id, author, raw_text, fired_types, detected, degraded, explanation
FROM (
  SELECT 'moderator' AS kind, 'm' || lpad(a.id::text, 19, '0') AS key, a.created_at, a.action, ms.nickname AS actor,
         c.id AS comment_id, s.nickname AS author, c.raw_text, d.fired_types, `+detectedSQL+` AS detected, d.degraded, d.explanation
  FROM moderator_actions a
  JOIN comments c ON c.id = a.comment_id
  JOIN sessions s ON s.id = c.session_id
  JOIN moderation_decisions d ON d.comment_id = c.id
  LEFT JOIN sessions ms ON ms.id = a.session_id
  WHERE $1::text IN ('', 'moderator')
  UNION ALL
  SELECT 'system', 's' || c.id::text, c.created_at, d.final_action, NULL,
         c.id, s.nickname, c.raw_text, d.fired_types, true, d.degraded, d.explanation
  FROM comments c
  JOIN sessions s ON s.id = c.session_id
  JOIN moderation_decisions d ON d.comment_id = c.id
  WHERE $1::text IN ('', 'system') AND `+detectedSQL+`
) e
WHERE ($2::timestamptz IS NULL OR (created_at, key) < ($2, $3))
  AND ($4::text = '' OR raw_text ILIKE $4 OR author ILIKE $4 OR actor ILIKE $4)
ORDER BY created_at DESC, key DESC
LIMIT $5`, f.Kind, afterTime, afterKey, like, f.Limit+1)
	if err != nil {
		return EventPage{}, err
	}
	events, err := pgx.CollectRows(rows, func(row pgx.CollectableRow) (Event, error) {
		var e Event
		err := row.Scan(&e.Kind, &e.Key, &e.CreatedAt, &e.Action, &e.Actor, &e.CommentID, &e.Author, &e.Text,
			&e.FiredTypes, &e.Detected, &e.Degraded, &e.Explanation)
		return e, err
	})
	if err != nil {
		return EventPage{}, err
	}
	page := EventPage{Items: events}
	if len(events) > f.Limit {
		page.Items = events[:f.Limit]
		last := page.Items[f.Limit-1]
		page.NextCursor = encodeCursorKey(last.CreatedAt, last.Key)
	}
	if page.Items == nil {
		page.Items = []Event{}
	}
	return page, nil
}

// ---------------------------------------------------------------- overview

// Range is a time window split into equal buckets. Now lies inside it; the
// buckets after Now are in the future and have no data yet.
type Range struct {
	Start   time.Time
	Now     time.Time
	Bucket  time.Duration
	Buckets int
}

func (r Range) End() time.Time { return r.Start.Add(r.Bucket * time.Duration(r.Buckets)) }

// Pair is a count in the window so far and in the same stretch of the window before it.
type Pair struct {
	Current  int64 `json:"current"`
	Previous int64 `json:"previous"`
}

type Series struct {
	Code    string  `json:"code"`
	Total   int64   `json:"total"`
	Buckets []int64 `json:"buckets"`
}

type PatternCount struct {
	Code  string `json:"code"`
	Count int64  `json:"count"`
}

// VerdictCounts is how many comments in the window ended on each verdict the
// decision layer can produce. Undecided are the ones whose evaluation did not
// complete (final_action NULL), never folded into another bucket.
type VerdictCounts struct {
	Block     int64 `json:"block"`
	Escalate  int64 `json:"escalate"`
	Review    int64 `json:"review"`
	Nudge     int64 `json:"nudge"`
	Clean     int64 `json:"clean"`
	Undecided int64 `json:"undecided"`
}

type OverviewCounts struct {
	Analysed  Pair           `json:"analysed"`
	Detected  Pair           `json:"detected"`
	Automatic Pair           `json:"automatic"`
	Verdicts  VerdictCounts  `json:"verdicts"`
	Series    []Series       `json:"series"`
	Patterns  []PatternCount `json:"patterns"`
}

func bucketIndexSQL(col string) string {
	return `floor(extract(epoch FROM (` + col + ` - $1)) / $2)::int`
}

// Overview counts the window for the dashboard. codes are the categories the
// AI detects today; each gets a series, zero-filled where nothing fired.
func (q *Queries) Overview(ctx context.Context, r Range, codes []string) (OverviewCounts, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	// The previous stretch is as long as the part of this window that has passed.
	prevStart := r.Start.Add(-r.Now.Sub(r.Start))

	var out OverviewCounts
	err := q.pool.QueryRow(ctx, `
SELECT count(*) FILTER (WHERE c.created_at >= $1),
       count(*) FILTER (WHERE c.created_at < $1),
       count(*) FILTER (WHERE c.created_at >= $1 AND `+detectedSQL+`),
       count(*) FILTER (WHERE c.created_at < $1 AND `+detectedSQL+`),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action IN ('block', 'nudge')),
       count(*) FILTER (WHERE c.created_at < $1 AND d.final_action IN ('block', 'nudge')),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action = 'block'),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action = 'escalate'),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action = 'review'),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action = 'nudge'),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action = 'clean'),
       count(*) FILTER (WHERE c.created_at >= $1 AND d.final_action IS NULL)
FROM comments c JOIN moderation_decisions d ON d.comment_id = c.id
WHERE c.created_at >= $2 AND c.created_at < $3`,
		r.Start, prevStart, r.Now).Scan(
		&out.Analysed.Current, &out.Analysed.Previous,
		&out.Detected.Current, &out.Detected.Previous,
		&out.Automatic.Current, &out.Automatic.Previous,
		&out.Verdicts.Block, &out.Verdicts.Escalate, &out.Verdicts.Review,
		&out.Verdicts.Nudge, &out.Verdicts.Clean, &out.Verdicts.Undecided)
	if err != nil {
		return out, fmt.Errorf("overview totals: %w", err)
	}

	width := r.Bucket.Seconds()
	byCode := map[string]*Series{}
	for _, code := range codes {
		byCode[code] = &Series{Code: code, Buckets: make([]int64, r.Buckets)}
	}
	add := func(code string, b int, n int64) {
		s, ok := byCode[code]
		if !ok || b < 0 || b >= r.Buckets {
			return
		}
		s.Buckets[b] += n
		s.Total += n
	}

	rows, err := q.pool.Query(ctx, `
SELECT r.offense_type, `+bucketIndexSQL("c.created_at")+`, count(DISTINCT c.id)
FROM analysis_results r JOIN comments c ON c.id = r.comment_id
WHERE r.fired AND c.created_at >= $1 AND c.created_at < $3
GROUP BY 1, 2`, r.Start, width, r.End())
	if err != nil {
		return out, fmt.Errorf("overview series: %w", err)
	}
	for rows.Next() {
		var (
			code string
			b    int
			n    int64
		)
		if err := rows.Scan(&code, &b, &n); err != nil {
			rows.Close()
			return out, err
		}
		add(code, b, n)
	}
	rows.Close()
	if err := rows.Err(); err != nil {
		return out, err
	}

	if _, ok := byCode[BinaryOffensive]; ok {
		rows, err := q.pool.Query(ctx, `
SELECT `+bucketIndexSQL("c.created_at")+`, count(*)
FROM comments c
WHERE c.created_at >= $1 AND c.created_at < $3
  AND c.result #>> '{signals,decision,binary_offensive,fired}' = 'true'
GROUP BY 1`, r.Start, width, r.End())
		if err != nil {
			return out, fmt.Errorf("overview offensive series: %w", err)
		}
		for rows.Next() {
			var (
				b int
				n int64
			)
			if err := rows.Scan(&b, &n); err != nil {
				rows.Close()
				return out, err
			}
			add(BinaryOffensive, b, n)
		}
		rows.Close()
		if err := rows.Err(); err != nil {
			return out, err
		}
	}
	out.Series = make([]Series, 0, len(codes))
	for _, code := range codes {
		out.Series = append(out.Series, *byCode[code])
	}

	rows, err = q.pool.Query(ctx, `
SELECT p.code, count(*)
FROM comments c, jsonb_array_elements_text(coalesce(c.result #> '{form,active}', '[]'::jsonb)) AS p(code)
WHERE c.created_at >= $1 AND c.created_at < $2
GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 5`, r.Start, r.End())
	if err != nil {
		return out, fmt.Errorf("overview patterns: %w", err)
	}
	out.Patterns, err = pgx.CollectRows(rows, func(row pgx.CollectableRow) (PatternCount, error) {
		var p PatternCount
		return p, row.Scan(&p.Code, &p.Count)
	})
	if err != nil {
		return out, err
	}
	if out.Patterns == nil {
		out.Patterns = []PatternCount{}
	}
	return out, nil
}

// ActiveDevices counts the distinct client addresses that sent a comment in
// the last window.
func (q *Queries) ActiveDevices(ctx context.Context, window time.Duration) (int64, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	var n int64
	err := q.pool.QueryRow(ctx, `
SELECT count(DISTINCT s.ip)
FROM comments c JOIN sessions s ON s.id = c.session_id
WHERE c.created_at > now() - make_interval(secs => $1)`, window.Seconds()).Scan(&n)
	return n, err
}

// ----------------------------------------------------------------- metrics

type MetricBucket struct {
	Start    time.Time `json:"start"`
	Requests int64     `json:"requests"`
	Errors   int64     `json:"errors"`
	P50MS    *float64  `json:"p50_ms"`
	P95MS    *float64  `json:"p95_ms"`
}

type MetricSeries struct {
	BucketSeconds int            `json:"bucket_seconds"`
	Analyses      []MetricBucket `json:"analyses"` // POST /api/comments
	AllRequests   []MetricBucket `json:"all_requests"`
}

// RequestSeries buckets request_metrics from start, one bucket per width.
func (q *Queries) RequestSeries(ctx context.Context, start time.Time, width time.Duration, buckets int) (MetricSeries, error) {
	ctx, cancel := q.ctx(ctx)
	defer cancel()
	out := MetricSeries{BucketSeconds: int(width.Seconds())}
	for _, analysesOnly := range []bool{true, false} {
		series := make([]MetricBucket, buckets)
		for i := range series {
			series[i].Start = start.Add(width * time.Duration(i))
		}
		rows, err := q.pool.Query(ctx, `
SELECT `+bucketIndexSQL("created_at")+`, count(*), count(*) FILTER (WHERE status_code >= 500),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms),
       percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
FROM request_metrics
WHERE created_at >= $1 AND created_at < $3
  AND ($4::boolean = false OR (endpoint = '/api/comments' AND method = 'POST'))
GROUP BY 1`, start, width.Seconds(), start.Add(width*time.Duration(buckets)), analysesOnly)
		if err != nil {
			return out, err
		}
		for rows.Next() {
			var (
				b        int
				n, errs  int64
				p50, p95 float64
			)
			if err := rows.Scan(&b, &n, &errs, &p50, &p95); err != nil {
				rows.Close()
				return out, err
			}
			if b >= 0 && b < buckets {
				series[b].Requests, series[b].Errors = n, errs
				series[b].P50MS, series[b].P95MS = &p50, &p95
			}
		}
		rows.Close()
		if err := rows.Err(); err != nil {
			return out, err
		}
		if analysesOnly {
			out.Analyses = series
		} else {
			out.AllRequests = series
		}
	}
	return out, nil
}
