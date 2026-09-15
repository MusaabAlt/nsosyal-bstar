package store

import (
	"context"
	"database/sql"
	"embed"
	"fmt"
	"io/fs"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
)

// The SQL files are compiled into the binary, so the demo laptop needs no
// migration tool and no files next to the executable.
//
//go:embed migrations/*.sql
var migrationFiles embed.FS

// Migrator runs the embedded migrations over the existing pool.
type Migrator struct {
	db       *sql.DB
	provider *goose.Provider
}

func NewMigrator(pool *pgxpool.Pool) (*Migrator, error) {
	fsys, err := fs.Sub(migrationFiles, "migrations")
	if err != nil {
		return nil, err
	}
	db := stdlib.OpenDBFromPool(pool)
	provider, err := goose.NewProvider(goose.DialectPostgres, db, fsys)
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("load migrations: %w", err)
	}
	return &Migrator{db: db, provider: provider}, nil
}

// Close releases the database/sql wrapper. The pool itself stays open.
func (m *Migrator) Close() error { return m.db.Close() }

// Up applies every pending migration.
func (m *Migrator) Up(ctx context.Context) ([]*goose.MigrationResult, error) {
	return m.provider.Up(ctx)
}

// DownTo rolls back to version (0 = empty schema).
func (m *Migrator) DownTo(ctx context.Context, version int64) ([]*goose.MigrationResult, error) {
	return m.provider.DownTo(ctx, version)
}

// Status lists every migration and whether it is applied.
func (m *Migrator) Status(ctx context.Context) ([]*goose.MigrationStatus, error) {
	return m.provider.Status(ctx)
}

// Version is the highest applied migration.
func (m *Migrator) Version(ctx context.Context) (int64, error) {
	return m.provider.GetDBVersion(ctx)
}
