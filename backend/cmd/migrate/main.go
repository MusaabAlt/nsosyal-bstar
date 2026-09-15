// Command migrate applies or rolls back the database schema by hand.
// The server also migrates on start when database.migrate_on_start is true.
//
//	go run ./cmd/migrate [-config config.yaml] [up|down|reset|status]   (default: up)
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/config"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "migrate:", err)
		os.Exit(1)
	}
}

func run() error {
	configPath := flag.String("config", "", "path to config.yaml (default: found in the current folder or backend/)")
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, "usage: migrate [-config config.yaml] [up|down|reset|status]   (default: up)")
		flag.PrintDefaults()
	}
	flag.Parse()
	if flag.NArg() > 1 {
		flag.Usage()
		return fmt.Errorf("expected at most one command, got %d", flag.NArg())
	}
	// No command means "up", so a plain run from the IDE does the useful thing.
	cmd := "up"
	if flag.NArg() == 1 {
		cmd = flag.Arg(0)
	}

	path := *configPath
	if path == "" {
		found, err := config.Find()
		if err != nil {
			return err
		}
		path = found
	}
	fmt.Println("config:", path)
	envFile := filepath.Join(filepath.Dir(path), config.EnvFileName)
	if _, err := os.Stat(envFile); err == nil {
		fmt.Println("env file:", envFile)
	} else {
		fmt.Println("env file: none (using config.yaml and environment only)")
	}

	cfg, err := config.Load(path)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	pool, err := store.NewPool(ctx, cfg.Database)
	if err != nil {
		return err
	}
	defer pool.Close()
	m, err := store.NewMigrator(pool)
	if err != nil {
		return err
	}
	defer m.Close()

	switch cmd {
	case "up":
		results, err := m.Up(ctx)
		for _, r := range results {
			fmt.Println("applied", r.Source.Path)
		}
		if err != nil {
			return err
		}
		if len(results) == 0 {
			fmt.Println("schema already up to date")
		}
	case "down":
		version, err := m.Version(ctx)
		if err != nil {
			return err
		}
		if version == 0 {
			fmt.Println("nothing to roll back")
			return nil
		}
		results, err := m.DownTo(ctx, version-1)
		for _, r := range results {
			fmt.Println("rolled back", r.Source.Path)
		}
		return err
	case "reset":
		results, err := m.DownTo(ctx, 0)
		for _, r := range results {
			fmt.Println("rolled back", r.Source.Path)
		}
		return err
	case "status":
		statuses, err := m.Status(ctx)
		if err != nil {
			return err
		}
		for _, s := range statuses {
			fmt.Printf("%-10s %s\n", s.State, s.Source.Path)
		}
	default:
		flag.Usage()
		return fmt.Errorf("unknown command %q", cmd)
	}
	return nil
}
