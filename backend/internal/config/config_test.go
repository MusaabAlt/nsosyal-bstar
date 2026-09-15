package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func writeFile(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func envMap(m map[string]string) func(string) (string, bool) {
	return func(k string) (string, bool) {
		v, ok := m[k]
		return v, ok
	}
}

func TestDefaultIsValid(t *testing.T) {
	if err := Default().Validate(); err != nil {
		t.Fatalf("default config invalid: %v", err)
	}
}

// The shipped config.yaml must always load; a typo there breaks the demo.
func TestShippedConfigLoads(t *testing.T) {
	cfg, err := Load(filepath.Join("..", "..", "config.yaml"))
	if err != nil {
		t.Fatalf("config.yaml: %v", err)
	}
	if cfg.Queue.BatchMaxWait != 20*time.Millisecond {
		t.Errorf("batch_max_wait = %s, want 20ms", cfg.Queue.BatchMaxWait)
	}
}

func TestLoadYAMLOverridesDefaults(t *testing.T) {
	path := writeFile(t, `
queue:
  size: 64
  batch_max_wait: 35ms
python:
  args: ["a", "b"]
`)
	cfg, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Queue.Size != 64 {
		t.Errorf("queue.size = %d, want 64", cfg.Queue.Size)
	}
	if cfg.Queue.BatchMaxWait != 35*time.Millisecond {
		t.Errorf("queue.batch_max_wait = %s, want 35ms", cfg.Queue.BatchMaxWait)
	}
	if got := strings.Join(cfg.Python.Args, " "); got != "a b" {
		t.Errorf("python.args = %q", got)
	}
	// Untouched values keep their defaults.
	if cfg.Queue.Workers != Default().Queue.Workers {
		t.Errorf("queue.workers = %d, want default", cfg.Queue.Workers)
	}
}

func TestEmptyFileMeansDefaults(t *testing.T) {
	cfg, err := Load(writeFile(t, ""))
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Queue.Size != Default().Queue.Size {
		t.Errorf("queue.size = %d, want default", cfg.Queue.Size)
	}
}

func TestUnknownKeyIsRejected(t *testing.T) {
	_, err := Load(writeFile(t, "queue:\n  sise: 10\n"))
	if err == nil || !strings.Contains(err.Error(), "sise") {
		t.Fatalf("want error naming the unknown key, got %v", err)
	}
}

func TestMissingFileIsAnError(t *testing.T) {
	if _, err := Load(filepath.Join(t.TempDir(), "nope.yaml")); err == nil {
		t.Fatal("want error for missing file")
	}
}

func TestEnvOverridesEveryKind(t *testing.T) {
	cfg := Default()
	err := applyEnv(&cfg, envMap(map[string]string{
		"NSOSYAL_SERVER_ADDR":                   "127.0.0.1:9090",
		"NSOSYAL_QUEUE_SIZE":                    "1024",
		"NSOSYAL_QUEUE_BATCH_MAX_WAIT":          "50ms",
		"NSOSYAL_PYTHON_ENABLED":                "true",
		"NSOSYAL_RATE_LIMIT_ANALYZE_PER_SECOND": "2.5",
		"NSOSYAL_DATABASE_MAX_CONNS":            "20",
		"NSOSYAL_SERVER_MAX_BODY_BYTES":         "1000",
		"NSOSYAL_SERVER_CORS_ORIGINS":           "http://a, http://b",
	}))
	if err != nil {
		t.Fatal(err)
	}
	checks := []struct {
		name string
		ok   bool
	}{
		{"server.addr", cfg.Server.Addr == "127.0.0.1:9090"},
		{"queue.size", cfg.Queue.Size == 1024},
		{"queue.batch_max_wait", cfg.Queue.BatchMaxWait == 50*time.Millisecond},
		{"python.enabled", cfg.Python.Enabled},
		{"rate_limit.analyze_per_second", cfg.RateLimit.AnalyzePerSecond == 2.5},
		{"database.max_conns", cfg.Database.MaxConns == 20},
		{"server.max_body_bytes", cfg.Server.MaxBodyBytes == 1000},
		{"server.cors_origins", strings.Join(cfg.Server.CORSOrigins, "|") == "http://a|http://b"},
	}
	for _, c := range checks {
		if !c.ok {
			t.Errorf("%s not overridden: %+v", c.name, cfg)
		}
	}
}

func TestEnvBeatsYAML(t *testing.T) {
	path := writeFile(t, "queue:\n  size: 64\n")
	t.Setenv("NSOSYAL_QUEUE_SIZE", "128")
	cfg, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Queue.Size != 128 {
		t.Errorf("queue.size = %d, want 128 from env", cfg.Queue.Size)
	}
}

func TestBadEnvValueNamesTheVariable(t *testing.T) {
	cfg := Default()
	err := applyEnv(&cfg, envMap(map[string]string{"NSOSYAL_QUEUE_SIZE": "lots"}))
	if err == nil || !strings.Contains(err.Error(), "NSOSYAL_QUEUE_SIZE") {
		t.Fatalf("want error naming the variable, got %v", err)
	}
}

func TestValidateRejectsUnsafeValues(t *testing.T) {
	cases := map[string]func(*Config){
		"zero queue":                 func(c *Config) { c.Queue.Size = 0 },
		"zero workers":               func(c *Config) { c.Queue.Workers = 0 },
		"zero batch":                 func(c *Config) { c.Queue.BatchMaxSize = 0 },
		"batch timeout >= request":   func(c *Config) { c.Inference.BatchTimeout = c.Server.RequestTimeout },
		"write timeout <= request":   func(c *Config) { c.Server.WriteTimeout = c.Server.RequestTimeout },
		"min conns > max conns":      func(c *Config) { c.Database.MinConns = c.Database.MaxConns + 1 },
		"bad log level":              func(c *Config) { c.Log.Level = "loud" },
		"python enabled without cmd": func(c *Config) { c.Python.Enabled = true; c.Python.Command = "" },
		"backoff max below min":      func(c *Config) { c.Python.Enabled = true; c.Python.RestartBackoffMax = time.Millisecond },
		"zero rate limit":            func(c *Config) { c.RateLimit.AnalyzePerSecond = 0 },
		"empty database url":         func(c *Config) { c.Database.URL = "" },
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			cfg := Default()
			mutate(&cfg)
			if err := cfg.Validate(); err == nil {
				t.Fatal("want validation error")
			}
		})
	}
}
