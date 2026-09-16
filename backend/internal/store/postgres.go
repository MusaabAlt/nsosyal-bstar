// Package store owns everything that talks to PostgreSQL: the connection
// pool, migrations, queries and the async writer.
package store

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/config"
)

// NewPool opens one shared pool for the whole process. No request ever opens
// its own connection; MaxConns caps how hard the API can push Postgres.
func NewPool(ctx context.Context, cfg config.Database) (*pgxpool.Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.URL)
	if err != nil {
		// The URL contains the password; never echo it back.
		return nil, fmt.Errorf("parse database.url: invalid connection string")
	}
	poolCfg.MaxConns = cfg.MaxConns
	poolCfg.MinConns = cfg.MinConns
	poolCfg.ConnConfig.ConnectTimeout = cfg.ConnectTimeout
	poolCfg.HealthCheckPeriod = 30 * time.Second
	poolCfg.MaxConnIdleTime = 5 * time.Minute
	poolCfg.ConnConfig.RuntimeParams["application_name"] = "nsosyal-backend"
	// A runaway query must not hold a connection forever; per-call contexts
	// are the first line, this is the backstop.
	poolCfg.ConnConfig.RuntimeParams["statement_timeout"] = fmt.Sprint(cfg.QueryTimeout.Milliseconds() * 4)

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("create pool: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, cfg.ConnectTimeout)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("connect to postgres at %s:%d: %w", poolCfg.ConnConfig.Host, poolCfg.ConnConfig.Port, err)
	}
	return pool, nil
}

// Ping reports whether Postgres answers within timeout (used by /api/health).
func Ping(ctx context.Context, pool *pgxpool.Pool, timeout time.Duration) error {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	return pool.Ping(ctx)
}
