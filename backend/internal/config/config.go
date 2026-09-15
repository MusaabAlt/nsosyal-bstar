// Package config loads the server configuration.
//
// Order of precedence, lowest to highest: built-in defaults, config.yaml,
// the .env file next to config.yaml, real environment variables. Every limit that protects the system (queue size,
// batch size, timeouts, pool size, ...) lives here so it can be tuned on the
// demo laptop without a rebuild.
//
// Environment variable names are derived from the YAML path:
// queue.batch_max_wait -> NSOSYAL_QUEUE_BATCH_MAX_WAIT.
package config

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"time"

	"go.yaml.in/yaml/v3"
)

const EnvPrefix = "NSOSYAL"

type Config struct {
	Server    Server    `yaml:"server"`
	Queue     Queue     `yaml:"queue"`
	Inference Inference `yaml:"inference"`
	Python    Python    `yaml:"python"`
	RateLimit RateLimit `yaml:"rate_limit"`
	Cache     Cache     `yaml:"cache"`
	Database  Database  `yaml:"database"`
	Writer    Writer    `yaml:"writer"`
	Log       Log       `yaml:"log"`
}

type Server struct {
	Addr              string        `yaml:"addr"`
	ReadHeaderTimeout time.Duration `yaml:"read_header_timeout"`
	ReadTimeout       time.Duration `yaml:"read_timeout"`
	WriteTimeout      time.Duration `yaml:"write_timeout"`
	IdleTimeout       time.Duration `yaml:"idle_timeout"`
	// RequestTimeout bounds one API request end to end, including queue wait.
	RequestTimeout  time.Duration `yaml:"request_timeout"`
	ShutdownTimeout time.Duration `yaml:"shutdown_timeout"`
	MaxBodyBytes    int64         `yaml:"max_body_bytes"`
	MaxTextChars    int           `yaml:"max_text_chars"`
	// CORSOrigins is for local frontend development only; in the demo the Vue
	// build is served from the same origin and this stays empty.
	CORSOrigins []string `yaml:"cors_origins"`
}

type Queue struct {
	// Size is the number of texts waiting for the model. When full, the API
	// answers 503 instead of growing memory.
	Size         int           `yaml:"size"`
	Workers      int           `yaml:"workers"`
	BatchMaxSize int           `yaml:"batch_max_size"`
	BatchMaxWait time.Duration `yaml:"batch_max_wait"`
}

type Inference struct {
	URL           string        `yaml:"url"`
	BatchTimeout  time.Duration `yaml:"batch_timeout"`
	HealthTimeout time.Duration `yaml:"health_timeout"`
	// Circuit breaker: after BreakerFailures consecutive failures, calls fail
	// fast for BreakerOpenFor, then one trial call is let through.
	BreakerFailures int           `yaml:"breaker_failures"`
	BreakerOpenFor  time.Duration `yaml:"breaker_open_for"`
}

type Python struct {
	// Enabled=false means the inference service is started by hand (or the
	// mock is used) and Go only talks to it.
	Enabled           bool          `yaml:"enabled"`
	Command           string        `yaml:"command"`
	Args              []string      `yaml:"args"`
	WorkDir           string        `yaml:"workdir"`
	HealthInterval    time.Duration `yaml:"health_interval"`
	StartupGrace      time.Duration `yaml:"startup_grace"`
	RestartBackoffMin time.Duration `yaml:"restart_backoff_min"`
	RestartBackoffMax time.Duration `yaml:"restart_backoff_max"`
}

type RateLimit struct {
	// Per client IP, token bucket. Analyze is the expensive endpoint and has
	// its own, stricter limit.
	AnalyzePerSecond float64       `yaml:"analyze_per_second"`
	AnalyzeBurst     int           `yaml:"analyze_burst"`
	ReadPerSecond    float64       `yaml:"read_per_second"`
	ReadBurst        int           `yaml:"read_burst"`
	IdleEviction     time.Duration `yaml:"idle_eviction"`
}

type Cache struct {
	Size int           `yaml:"size"`
	TTL  time.Duration `yaml:"ttl"`
}

type Database struct {
	URL            string        `yaml:"url"`
	MaxConns       int32         `yaml:"max_conns"`
	MinConns       int32         `yaml:"min_conns"`
	ConnectTimeout time.Duration `yaml:"connect_timeout"`
	QueryTimeout   time.Duration `yaml:"query_timeout"`
	MigrateOnStart bool          `yaml:"migrate_on_start"`
}

type Writer struct {
	// Comments and decisions are never dropped while there is room; metrics
	// rows are dropped first when the database falls behind.
	CommentBuffer int           `yaml:"comment_buffer"`
	MetricsBuffer int           `yaml:"metrics_buffer"`
	BatchSize     int           `yaml:"batch_size"`
	FlushInterval time.Duration `yaml:"flush_interval"`
	WriteTimeout  time.Duration `yaml:"write_timeout"`
}

type Log struct {
	Level  string `yaml:"level"`  // debug | info | warn | error
	Format string `yaml:"format"` // json | text
}

// Default returns a configuration that runs on a developer laptop.
func Default() Config {
	return Config{
		Server: Server{
			Addr:              "0.0.0.0:8080",
			ReadHeaderTimeout: 5 * time.Second,
			ReadTimeout:       10 * time.Second,
			WriteTimeout:      30 * time.Second,
			IdleTimeout:       60 * time.Second,
			RequestTimeout:    15 * time.Second,
			ShutdownTimeout:   20 * time.Second,
			MaxBodyBytes:      64 << 10,
			MaxTextChars:      5000,
		},
		Queue: Queue{
			Size:         256,
			Workers:      2,
			BatchMaxSize: 16,
			BatchMaxWait: 20 * time.Millisecond,
		},
		Inference: Inference{
			URL:             "http://127.0.0.1:8001",
			BatchTimeout:    10 * time.Second,
			HealthTimeout:   2 * time.Second,
			BreakerFailures: 5,
			BreakerOpenFor:  5 * time.Second,
		},
		Python: Python{
			Enabled:           false,
			Command:           "python",
			Args:              []string{"-m", "uvicorn", "serving.app:app", "--host", "127.0.0.1", "--port", "8001"},
			WorkDir:           "../AI",
			HealthInterval:    2 * time.Second,
			StartupGrace:      120 * time.Second,
			RestartBackoffMin: 1 * time.Second,
			RestartBackoffMax: 30 * time.Second,
		},
		RateLimit: RateLimit{
			AnalyzePerSecond: 1,
			AnalyzeBurst:     5,
			ReadPerSecond:    10,
			ReadBurst:        30,
			IdleEviction:     10 * time.Minute,
		},
		Cache: Cache{
			Size: 10000,
			TTL:  10 * time.Minute,
		},
		Database: Database{
			URL:            "postgres://nsosyal:nsosyal_dev@127.0.0.1:5432/nsosyal?sslmode=disable",
			MaxConns:       15,
			MinConns:       2,
			ConnectTimeout: 5 * time.Second,
			QueryTimeout:   3 * time.Second,
			MigrateOnStart: true,
		},
		Writer: Writer{
			CommentBuffer: 4096,
			MetricsBuffer: 8192,
			BatchSize:     200,
			FlushInterval: 250 * time.Millisecond,
			WriteTimeout:  5 * time.Second,
		},
		Log: Log{
			Level:  "info",
			Format: "json",
		},
	}
}

// Load reads defaults, then the YAML file at path (skipped when path is
// empty), then the .env file in the same folder, then real environment
// variables, and validates the result.
func Load(path string) (Config, error) {
	cfg := Default()
	envFile := EnvFileName
	if path != "" {
		envFile = filepath.Join(filepath.Dir(path), EnvFileName)
		data, err := os.ReadFile(path)
		if err != nil {
			return Config{}, fmt.Errorf("read config: %w", err)
		}
		dec := yaml.NewDecoder(bytes.NewReader(data))
		// A misspelled key would otherwise be silently ignored and the
		// default used, which is exactly the kind of mistake found on stage.
		dec.KnownFields(true)
		// io.EOF: an empty file means "use defaults".
		if err := dec.Decode(&cfg); err != nil && !errors.Is(err, io.EOF) {
			return Config{}, fmt.Errorf("parse %s: %w", path, err)
		}
	}
	dotenv, err := readDotEnv(envFile)
	if err != nil {
		return Config{}, err
	}
	// A variable set in the real environment wins over the .env file, so a
	// one-off override on the command line always works.
	lookup := func(key string) (string, bool) {
		if v, ok := os.LookupEnv(key); ok {
			return v, true
		}
		v, ok := dotenv[key]
		return v, ok
	}
	if err := applyEnv(&cfg, lookup); err != nil {
		return Config{}, err
	}
	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

// Validate rejects values that would make the server unsafe or unable to run.
func (c Config) Validate() error {
	var errs []error
	check := func(ok bool, format string, args ...any) {
		if !ok {
			errs = append(errs, fmt.Errorf(format, args...))
		}
	}

	check(c.Server.Addr != "", "server.addr is required")
	check(c.Server.ReadHeaderTimeout > 0, "server.read_header_timeout must be > 0")
	check(c.Server.ReadTimeout > 0, "server.read_timeout must be > 0")
	check(c.Server.WriteTimeout > 0, "server.write_timeout must be > 0")
	check(c.Server.RequestTimeout > 0, "server.request_timeout must be > 0")
	check(c.Server.WriteTimeout > c.Server.RequestTimeout,
		"server.write_timeout (%s) must be greater than server.request_timeout (%s)", c.Server.WriteTimeout, c.Server.RequestTimeout)
	check(c.Server.ShutdownTimeout > 0, "server.shutdown_timeout must be > 0")
	check(c.Server.MaxBodyBytes > 0, "server.max_body_bytes must be > 0")
	check(c.Server.MaxTextChars > 0, "server.max_text_chars must be > 0")

	check(c.Queue.Size > 0, "queue.size must be > 0")
	check(c.Queue.Workers > 0, "queue.workers must be > 0")
	check(c.Queue.BatchMaxSize > 0, "queue.batch_max_size must be > 0")
	check(c.Queue.BatchMaxWait > 0, "queue.batch_max_wait must be > 0")

	check(c.Inference.URL != "", "inference.url is required")
	check(c.Inference.BatchTimeout > 0, "inference.batch_timeout must be > 0")
	check(c.Inference.BatchTimeout < c.Server.RequestTimeout,
		"inference.batch_timeout (%s) must be less than server.request_timeout (%s)", c.Inference.BatchTimeout, c.Server.RequestTimeout)
	check(c.Inference.HealthTimeout > 0, "inference.health_timeout must be > 0")
	check(c.Inference.BreakerFailures > 0, "inference.breaker_failures must be > 0")
	check(c.Inference.BreakerOpenFor > 0, "inference.breaker_open_for must be > 0")

	if c.Python.Enabled {
		check(c.Python.Command != "", "python.command is required when python.enabled")
		check(c.Python.HealthInterval > 0, "python.health_interval must be > 0")
		check(c.Python.StartupGrace > 0, "python.startup_grace must be > 0")
		check(c.Python.RestartBackoffMin > 0, "python.restart_backoff_min must be > 0")
		check(c.Python.RestartBackoffMax >= c.Python.RestartBackoffMin,
			"python.restart_backoff_max must be >= python.restart_backoff_min")
	}

	check(c.RateLimit.AnalyzePerSecond > 0, "rate_limit.analyze_per_second must be > 0")
	check(c.RateLimit.AnalyzeBurst > 0, "rate_limit.analyze_burst must be > 0")
	check(c.RateLimit.ReadPerSecond > 0, "rate_limit.read_per_second must be > 0")
	check(c.RateLimit.ReadBurst > 0, "rate_limit.read_burst must be > 0")
	check(c.RateLimit.IdleEviction > 0, "rate_limit.idle_eviction must be > 0")

	check(c.Cache.Size > 0, "cache.size must be > 0")
	check(c.Cache.TTL > 0, "cache.ttl must be > 0")

	check(c.Database.URL != "", "database.url is required")
	check(c.Database.MaxConns > 0, "database.max_conns must be > 0")
	check(c.Database.MinConns >= 0 && c.Database.MinConns <= c.Database.MaxConns,
		"database.min_conns must be between 0 and database.max_conns")
	check(c.Database.ConnectTimeout > 0, "database.connect_timeout must be > 0")
	check(c.Database.QueryTimeout > 0, "database.query_timeout must be > 0")

	check(c.Writer.CommentBuffer > 0, "writer.comment_buffer must be > 0")
	check(c.Writer.MetricsBuffer > 0, "writer.metrics_buffer must be > 0")
	check(c.Writer.BatchSize > 0, "writer.batch_size must be > 0")
	check(c.Writer.FlushInterval > 0, "writer.flush_interval must be > 0")
	check(c.Writer.WriteTimeout > 0, "writer.write_timeout must be > 0")

	switch c.Log.Level {
	case "debug", "info", "warn", "error":
	default:
		errs = append(errs, fmt.Errorf("log.level must be debug, info, warn or error, got %q", c.Log.Level))
	}
	switch c.Log.Format {
	case "json", "text":
	default:
		errs = append(errs, fmt.Errorf("log.format must be json or text, got %q", c.Log.Format))
	}

	if len(errs) > 0 {
		return fmt.Errorf("invalid config: %w", errors.Join(errs...))
	}
	return nil
}

// Find looks for config.yaml in the current folder, then in backend/, walking
// up a few parents. IDEs often start a process from the repo root or from
// the command's own folder.
func Find() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	start := dir
	for range 4 {
		for _, candidate := range []string{
			filepath.Join(dir, "config.yaml"),
			filepath.Join(dir, "backend", "config.yaml"),
		} {
			if info, err := os.Stat(candidate); err == nil && !info.IsDir() {
				return candidate, nil
			}
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("config.yaml not found from %s; pass -config", start)
}

var durationType = reflect.TypeFor[time.Duration]()

// applyEnv walks the struct by its yaml tags and overrides every field whose
// environment variable is set. lookup is injected so tests do not touch the
// real environment.
func applyEnv(cfg *Config, lookup func(string) (string, bool)) error {
	return walkEnv(reflect.ValueOf(cfg).Elem(), EnvPrefix, lookup)
}

func walkEnv(v reflect.Value, prefix string, lookup func(string) (string, bool)) error {
	t := v.Type()
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		tag := strings.Split(field.Tag.Get("yaml"), ",")[0]
		if tag == "" || tag == "-" {
			continue
		}
		name := prefix + "_" + strings.ToUpper(tag)
		fv := v.Field(i)
		if fv.Kind() == reflect.Struct {
			if err := walkEnv(fv, name, lookup); err != nil {
				return err
			}
			continue
		}
		raw, ok := lookup(name)
		if !ok {
			continue
		}
		if err := setField(fv, raw); err != nil {
			return fmt.Errorf("env %s=%q: %w", name, raw, err)
		}
	}
	return nil
}

func setField(fv reflect.Value, raw string) error {
	raw = strings.TrimSpace(raw)
	if fv.Type() == durationType {
		d, err := time.ParseDuration(raw)
		if err != nil {
			return err
		}
		fv.SetInt(int64(d))
		return nil
	}
	switch fv.Kind() {
	case reflect.String:
		fv.SetString(raw)
	case reflect.Bool:
		b, err := strconv.ParseBool(raw)
		if err != nil {
			return err
		}
		fv.SetBool(b)
	case reflect.Int, reflect.Int32, reflect.Int64:
		n, err := strconv.ParseInt(raw, 10, fv.Type().Bits())
		if err != nil {
			return err
		}
		fv.SetInt(n)
	case reflect.Float64:
		f, err := strconv.ParseFloat(raw, 64)
		if err != nil {
			return err
		}
		fv.SetFloat(f)
	case reflect.Slice:
		if fv.Type().Elem().Kind() != reflect.String {
			return fmt.Errorf("unsupported slice type %s", fv.Type())
		}
		var parts []string
		for p := range strings.SplitSeq(raw, ",") {
			if p = strings.TrimSpace(p); p != "" {
				parts = append(parts, p)
			}
		}
		fv.Set(reflect.ValueOf(parts))
	default:
		return fmt.Errorf("unsupported field type %s", fv.Type())
	}
	return nil
}
