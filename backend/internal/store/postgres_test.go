package store

import (
	"context"
	"crypto/sha256"
	"errors"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/config"
)

// Integration tests run against a real, disposable database:
//
//	NSOSYAL_TEST_DATABASE_URL=postgres://nsosyal:nsosyal_dev@127.0.0.1:5432/nsosyal_test?sslmode=disable
//
// They are skipped when the variable is unset. They DROP every table.
const testDBEnv = "NSOSYAL_TEST_DATABASE_URL"

func testPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv(testDBEnv)
	if url == "" {
		t.Skipf("%s not set; skipping Postgres integration test", testDBEnv)
	}
	if !strings.Contains(url, "test") {
		t.Fatalf("%s must point at a test database (its name should contain \"test\"): these tests drop tables", testDBEnv)
	}
	cfg := config.Default().Database
	cfg.URL = url
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	pool, err := NewPool(ctx, cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	return pool
}

// freshSchema resets the test database to an empty schema, then migrates up.
func freshSchema(t *testing.T, pool *pgxpool.Pool) *Migrator {
	t.Helper()
	ctx := context.Background()
	m, err := NewMigrator(pool)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = m.Close() })
	if _, err := m.DownTo(ctx, 0); err != nil {
		t.Fatalf("reset: %v", err)
	}
	if _, err := m.Up(ctx); err != nil {
		t.Fatalf("up: %v", err)
	}
	return m
}

func TestNewPoolRejectsBadURLWithoutLeakingPassword(t *testing.T) {
	cfg := config.Default().Database
	cfg.URL = "postgres://user:s3cret@host:notaport/db"
	_, err := NewPool(context.Background(), cfg)
	if err == nil {
		t.Fatal("want error")
	}
	if strings.Contains(err.Error(), "s3cret") {
		t.Fatalf("error leaks the password: %v", err)
	}
}

func TestNewPoolFailsFastWhenPostgresIsDown(t *testing.T) {
	cfg := config.Default().Database
	cfg.URL = "postgres://u:p@127.0.0.1:1/db?sslmode=disable" // nothing listens on port 1
	cfg.ConnectTimeout = 500 * time.Millisecond
	start := time.Now()
	if _, err := NewPool(context.Background(), cfg); err == nil {
		t.Fatal("want connection error")
	}
	if took := time.Since(start); took > 5*time.Second {
		t.Fatalf("took %s; must fail fast", took)
	}
}

func TestMigrationsUpDownUp(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()
	m := freshSchema(t, pool)

	version, err := m.Version(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if version < 1 {
		t.Fatalf("version = %d after up", version)
	}
	for _, table := range []string{"sessions", "comments", "analysis_results", "moderation_decisions", "request_metrics"} {
		var exists bool
		if err := pool.QueryRow(ctx, `SELECT to_regclass('public.' || $1) IS NOT NULL`, table).Scan(&exists); err != nil {
			t.Fatal(err)
		}
		if !exists {
			t.Errorf("table %s missing after up", table)
		}
	}

	// Down must fully undo up, or a later re-run on the demo laptop fails.
	if _, err := m.DownTo(ctx, 0); err != nil {
		t.Fatalf("down: %v", err)
	}
	var exists bool
	if err := pool.QueryRow(ctx, `SELECT to_regclass('public.comments') IS NOT NULL`).Scan(&exists); err != nil {
		t.Fatal(err)
	}
	if exists {
		t.Fatal("comments still exists after down")
	}
	if _, err := m.Up(ctx); err != nil {
		t.Fatalf("second up: %v", err)
	}

	// Up on an up-to-date schema is a no-op, which is what migrate_on_start relies on.
	results, err := m.Up(ctx)
	if err != nil {
		t.Fatalf("idempotent up: %v", err)
	}
	if len(results) != 0 {
		t.Fatalf("up on current schema applied %d migrations", len(results))
	}
}

func TestMigratorCloseKeepsPoolOpen(t *testing.T) {
	pool := testPool(t)
	m, err := NewMigrator(pool)
	if err != nil {
		t.Fatal(err)
	}
	if err := m.Close(); err != nil {
		t.Fatal(err)
	}
	if err := Ping(context.Background(), pool, time.Second); err != nil {
		t.Fatalf("pool unusable after migrator close: %v", err)
	}
}

func insertComment(ctx context.Context, pool *pgxpool.Pool, sessionID uuid.UUID, text string) (uuid.UUID, error) {
	id := uuid.Must(uuid.NewV7())
	sum := sha256.Sum256([]byte(text))
	_, err := pool.Exec(ctx, `
		INSERT INTO comments (id, session_id, raw_text, text_sha256, artifact_hash, result, latency_ms, from_cache)
		VALUES ($1, $2, $3, $4, 'hash', '{}'::jsonb, 1.5, false)`,
		id, sessionID, text, sum[:])
	return id, err
}

func wantCheckViolation(t *testing.T, err error, what string) {
	t.Helper()
	var pgErr *pgconn.PgError
	if !errors.As(err, &pgErr) || pgErr.Code != "23514" {
		t.Fatalf("%s: want check violation (23514), got %v", what, err)
	}
}

// The constraints are the last guard against bad data reaching the dashboard.
func TestSchemaConstraints(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()
	freshSchema(t, pool)

	sessionID := uuid.Must(uuid.NewV7())
	if _, err := pool.Exec(ctx, `INSERT INTO sessions (id, nickname, ip) VALUES ($1, 'emin', '192.168.1.20')`, sessionID); err != nil {
		t.Fatal(err)
	}

	t.Run("nickname length", func(t *testing.T) {
		_, err := pool.Exec(ctx, `INSERT INTO sessions (id, nickname, ip) VALUES ($1, '', '10.0.0.1')`, uuid.Must(uuid.NewV7()))
		wantCheckViolation(t, err, "empty nickname")
	})

	t.Run("text up to 5000 chars incl. multibyte", func(t *testing.T) {
		// 5000 Turkish characters is 10000 bytes; the limit is on characters.
		if _, err := insertComment(ctx, pool, sessionID, strings.Repeat("ş", 5000)); err != nil {
			t.Fatalf("5000 chars rejected: %v", err)
		}
		_, err := insertComment(ctx, pool, sessionID, strings.Repeat("ş", 5001))
		wantCheckViolation(t, err, "5001 chars")
	})

	commentID, err := insertComment(ctx, pool, sessionID, "Seni b1tireceğim")
	if err != nil {
		t.Fatal(err)
	}

	t.Run("final_action values", func(t *testing.T) {
		for _, action := range []string{"block", "escalate", "review", "nudge", "clean"} {
			id, err := insertComment(ctx, pool, sessionID, "x "+action)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := pool.Exec(ctx, `INSERT INTO moderation_decisions (comment_id, final_action, degraded, explanation) VALUES ($1, $2, false, 'e')`, id, action); err != nil {
				t.Errorf("action %s rejected: %v", action, err)
			}
		}
		_, err := pool.Exec(ctx, `INSERT INTO moderation_decisions (comment_id, final_action, degraded, explanation) VALUES ($1, 'hide', false, 'e')`, commentID)
		wantCheckViolation(t, err, "action hide")
	})

	t.Run("null final_action means decision failed", func(t *testing.T) {
		if _, err := pool.Exec(ctx, `INSERT INTO moderation_decisions (comment_id, final_action, degraded, explanation) VALUES ($1, NULL, true, 'Karar verilemedi')`, commentID); err != nil {
			t.Fatalf("null action rejected: %v", err)
		}
	})

	t.Run("offense type and score range", func(t *testing.T) {
		insert := `INSERT INTO analysis_results (comment_id, offense_type, score, engine, source, model_version) VALUES ($1, $2, $3, 'model', 'm3_encoder@raw', 'v')`
		if _, err := pool.Exec(ctx, insert, commentID, "B2", 0.87); err != nil {
			t.Fatalf("valid row rejected: %v", err)
		}
		_, err := pool.Exec(ctx, insert, commentID, "Z9", 0.5)
		wantCheckViolation(t, err, "offense type Z9")
		_, err = pool.Exec(ctx, insert, commentID, "B2", 1.2)
		wantCheckViolation(t, err, "score 1.2")
	})

	t.Run("deleting a comment cascades", func(t *testing.T) {
		if _, err := pool.Exec(ctx, `DELETE FROM comments WHERE id = $1`, commentID); err != nil {
			t.Fatal(err)
		}
		var n int
		if err := pool.QueryRow(ctx, `SELECT count(*) FROM analysis_results WHERE comment_id = $1`, commentID).Scan(&n); err != nil {
			t.Fatal(err)
		}
		if n != 0 {
			t.Fatalf("%d orphan analysis_results", n)
		}
	})
}

// The dashboard queries must use the indexes, not scan whole tables.
func TestDashboardIndexesExist(t *testing.T) {
	pool := testPool(t)
	ctx := context.Background()
	freshSchema(t, pool)
	for _, idx := range []string{
		"comments_feed_idx", "comments_session_idx", "analysis_results_type_idx",
		"analysis_results_comment_idx", "moderation_decisions_action_idx",
		"moderation_decisions_flagged_idx", "request_metrics_created_brin",
	} {
		var exists bool
		if err := pool.QueryRow(ctx, `SELECT to_regclass('public.' || $1) IS NOT NULL`, idx).Scan(&exists); err != nil {
			t.Fatal(err)
		}
		if !exists {
			t.Errorf("index %s missing", idx)
		}
	}
}
