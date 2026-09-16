// Command server runs the NSosyal backend: the REST API under /api and the
// embedded Vue frontend, on one port, for the live demo.
//
//	go run ./cmd/server [-config config.yaml]
//
// Shutdown order (Ctrl+C or SIGTERM):
//  1. stop accepting HTTP requests, let in-flight ones finish
//  2. drain the analysis queue
//  3. flush the database writer
//  4. stop the Python process
//  5. close the database pool
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/cache"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/categories"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/config"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/domain"
	httpapi "github.com/MusaabAlt/nsosyal-bstar/backend/internal/http"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/handlers"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/http/middleware"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/inference"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/metrics"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/queue"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/store"
	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/supervisor"
	"github.com/MusaabAlt/nsosyal-bstar/backend/web"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "server:", err)
		os.Exit(1)
	}
}

func run() error {
	configPath := flag.String("config", "", "path to config.yaml (default: found in the current folder or backend/)")
	flag.Parse()
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
	log := newLogger(cfg.Log)
	slog.SetDefault(log)
	log.Info("config loaded", "path", path)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	startedAt := time.Now()

	// Claim the port first: if it is taken, fail before Postgres, Python or
	// any goroutine has been started, so nothing is left behind.
	listener, err := net.Listen(listenNetwork(cfg.Server.Addr), cfg.Server.Addr)
	if err != nil {
		return fmt.Errorf("listen on %s: %w (another program uses this port: stop it or change server.addr / NSOSYAL_SERVER_ADDR)", cfg.Server.Addr, err)
	}
	defer listener.Close()

	// --- Postgres
	pool, err := store.NewPool(ctx, cfg.Database)
	if err != nil {
		return fmt.Errorf("%w (is PostgreSQL running? check database.url / NSOSYAL_DATABASE_URL)", err)
	}
	defer pool.Close()
	if cfg.Database.MigrateOnStart {
		if err := migrate(ctx, pool, log); err != nil {
			return err
		}
	}
	queries := store.NewQueries(pool, cfg.Database.QueryTimeout)
	writer := store.NewWriter(pool, store.WriterConfig{
		CommentBuffer: cfg.Writer.CommentBuffer,
		MetricsBuffer: cfg.Writer.MetricsBuffer,
		BatchSize:     cfg.Writer.BatchSize,
		FlushInterval: cfg.Writer.FlushInterval,
		WriteTimeout:  cfg.Writer.WriteTimeout,
	}, log)
	go writer.Run()

	// --- Python
	client := inference.New(inference.Config{
		URL:             cfg.Inference.URL,
		HealthTimeout:   cfg.Inference.HealthTimeout,
		BreakerFailures: cfg.Inference.BreakerFailures,
		BreakerOpenFor:  cfg.Inference.BreakerOpenFor,
	})
	sup := supervisor.New(supervisor.Config{
		Manage:            cfg.Python.Enabled,
		Command:           resolveCommand(path, cfg.Python.Command),
		Args:              cfg.Python.Args,
		WorkDir:           resolveFrom(path, cfg.Python.WorkDir),
		HealthInterval:    cfg.Python.HealthInterval,
		StartupGrace:      cfg.Python.StartupGrace,
		RestartBackoffMin: cfg.Python.RestartBackoffMin,
		RestartBackoffMax: cfg.Python.RestartBackoffMax,
	}, cfg.Inference.URL, client, log)
	sup.Start()

	// --- Queue and batching
	batcher, err := queue.New(queue.Config{
		Size:         cfg.Queue.Size,
		Workers:      cfg.Queue.Workers,
		BatchMaxSize: cfg.Queue.BatchMaxSize,
		BatchMaxWait: cfg.Queue.BatchMaxWait,
		BatchTimeout: cfg.Inference.BatchTimeout,
	}, client, log)
	if err != nil {
		return err
	}
	batcher.Start()

	// --- HTTP
	reg := metrics.NewRegistry()
	api := handlers.New(handlers.Deps{
		Store:        queries,
		Writer:       writer,
		Analyzer:     batcher,
		Inference:    client,
		Categories:   categories.NewStore(resolveFrom(path, cfg.Decision.ThresholdsFile)),
		Cache:        cache.New[handlers.CachedAnalysis](cfg.Cache.Size, cfg.Cache.TTL),
		Metrics:      reg,
		Log:          log,
		MaxBodyBytes: cfg.Server.MaxBodyBytes,
		MaxTextChars: cfg.Server.MaxTextChars,
		StartedAt:    startedAt,
	})
	analyzeLimiter := middleware.NewLimiter(cfg.RateLimit.AnalyzePerSecond, cfg.RateLimit.AnalyzeBurst, cfg.RateLimit.IdleEviction)
	readLimiter := middleware.NewLimiter(cfg.RateLimit.ReadPerSecond, cfg.RateLimit.ReadBurst, cfg.RateLimit.IdleEviction)
	evictCtx, stopEviction := context.WithCancel(context.Background())
	defer stopEviction()
	go analyzeLimiter.RunEviction(evictCtx)
	go readLimiter.RunEviction(evictCtx)

	router := httpapi.NewRouter(api, web.Handler(), httpapi.RouterConfig{
		RequestTimeout: cfg.Server.RequestTimeout,
		CORSOrigins:    cfg.Server.CORSOrigins,
		Analyze:        analyzeLimiter,
		Read:           readLimiter,
		Log:            log,
		OnRequest: func(info middleware.RequestInfo) {
			writer.EnqueueMetric(domain.RequestMetric{
				Endpoint: info.Path, Method: info.Method, StatusCode: info.Status,
				LatencyMS: float64(info.Duration.Microseconds()) / 1000, CreatedAt: time.Now(),
			})
		},
	})

	srv := &http.Server{
		Addr:              cfg.Server.Addr,
		Handler:           router,
		ReadHeaderTimeout: cfg.Server.ReadHeaderTimeout,
		ReadTimeout:       cfg.Server.ReadTimeout,
		WriteTimeout:      cfg.Server.WriteTimeout,
		IdleTimeout:       cfg.Server.IdleTimeout,
		MaxHeaderBytes:    32 << 10,
		ErrorLog:          slog.NewLogLogger(log.Handler(), slog.LevelWarn),
	}
	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(listener) }()
	announce(log, cfg.Server.Addr)

	select {
	case <-ctx.Done():
		log.Info("shutdown requested")
	case err := <-serveErr:
		if !errors.Is(err, http.ErrServerClosed) {
			log.Error("http server stopped", "error", err)
		}
	}
	stop() // a second Ctrl+C now kills the process immediately

	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.Server.ShutdownTimeout)
	defer cancel()
	step := func(name string, fn func(context.Context) error) {
		start := time.Now()
		if err := fn(shutdownCtx); err != nil {
			log.Error("shutdown step failed", "step", name, "error", err)
			return
		}
		log.Info("shutdown step done", "step", name, "duration_ms", time.Since(start).Milliseconds())
	}
	step("http", srv.Shutdown)
	step("queue", batcher.Shutdown)
	step("db-writer", writer.Close)
	step("python", sup.Stop)
	log.Info("shutdown complete")
	return nil
}

func migrate(ctx context.Context, pool *pgxpool.Pool, log *slog.Logger) error {
	m, err := store.NewMigrator(pool)
	if err != nil {
		return err
	}
	defer m.Close()
	results, err := m.Up(ctx)
	if err != nil {
		return fmt.Errorf("migrate: %w", err)
	}
	for _, r := range results {
		log.Info("migration applied", "file", r.Source.Path)
	}
	return nil
}

// listenNetwork binds IPv4 addresses with "tcp4". With plain "tcp", Go turns
// 0.0.0.0 into the dual-stack wildcard: if another program (Apache, IIS, ...)
// already holds IPv4 0.0.0.0:8080, Go still starts on IPv6 only, and every
// phone on the LAN silently reaches the other program instead of this one.
func listenNetwork(addr string) string {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return "tcp"
	}
	if ip := net.ParseIP(host); ip != nil && ip.To4() != nil {
		return "tcp4"
	}
	return "tcp"
}

// resolveFrom makes a relative path relative to the config file's folder, so
// the server finds AI/decision/thresholds.yaml from any working directory.
func resolveFrom(configPath, p string) string {
	if filepath.IsAbs(p) {
		return p
	}
	return filepath.Join(filepath.Dir(configPath), p)
}

// resolveCommand resolves a command given as a path ("../.venv/Scripts/python.exe")
// from the config file's folder; a bare name ("python") is left for PATH lookup.
func resolveCommand(configPath, command string) string {
	if !strings.ContainsAny(command, `/\`) {
		return command
	}
	return resolveFrom(configPath, command)
}

func newLogger(cfg config.Log) *slog.Logger {
	var level slog.Level
	_ = level.UnmarshalText([]byte(cfg.Level))
	opts := &slog.HandlerOptions{Level: level}
	if cfg.Format == "text" {
		return slog.New(slog.NewTextHandler(os.Stdout, opts))
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, opts))
}

// announce prints the addresses phones on the LAN should open.
func announce(log *slog.Logger, addr string) {
	host, port, _ := net.SplitHostPort(addr)
	urls := []string{}
	if host == "" || host == "0.0.0.0" || host == "::" {
		ifaces, _ := net.InterfaceAddrs()
		for _, a := range ifaces {
			if ipnet, ok := a.(*net.IPNet); ok && ipnet.IP.To4() != nil && !ipnet.IP.IsLoopback() && !ipnet.IP.IsLinkLocalUnicast() {
				urls = append(urls, "http://"+ipnet.IP.String()+":"+port)
			}
		}
		urls = append(urls, "http://127.0.0.1:"+port)
	} else {
		urls = append(urls, "http://"+addr)
	}
	log.Info("server ready", "addr", addr, "open", strings.Join(urls, "  "))
}
