package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseDotEnv(t *testing.T) {
	input := "\xef\xbb\xbf" + `# local secrets
NSOSYAL_DATABASE_URL=postgres://u:p@h:5432/db?sslmode=disable

export NSOSYAL_QUEUE_SIZE = 64
NSOSYAL_LOG_LEVEL="debug"
SINGLE='a b'
LITERAL=pa$$w\rd#1
EMPTY=
`
	got, err := parseDotEnv([]byte(input), ".env")
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]string{
		"NSOSYAL_DATABASE_URL": "postgres://u:p@h:5432/db?sslmode=disable",
		"NSOSYAL_QUEUE_SIZE":   "64",
		"NSOSYAL_LOG_LEVEL":    "debug",
		"SINGLE":               "a b",
		"LITERAL":              `pa$$w\rd#1`, // no expansion, no escapes, # inside a value is kept
		"EMPTY":                "",
	}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("%s = %q, want %q", k, got[k], v)
		}
	}
	if len(got) != len(want) {
		t.Errorf("got %d keys, want %d: %v", len(got), len(want), got)
	}
}

func TestParseDotEnvWindowsLineEndings(t *testing.T) {
	got, err := parseDotEnv([]byte("A=1\r\nB=2\r\n"), ".env")
	if err != nil {
		t.Fatal(err)
	}
	if got["A"] != "1" || got["B"] != "2" {
		t.Fatalf("got %v", got)
	}
}

func TestParseDotEnvErrorsNeverShowValues(t *testing.T) {
	cases := map[string]string{
		"no equals":      "NSOSYAL_DATABASE_URL secretpassword",
		"unclosed quote": `NSOSYAL_DATABASE_URL="secretpassword`,
		"space in key":   "BAD KEY=secretpassword",
	}
	for name, input := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := parseDotEnv([]byte("# ok\n"+input), ".env")
			if err == nil {
				t.Fatal("want error")
			}
			if !strings.Contains(err.Error(), "line 2") {
				t.Errorf("error should name line 2: %v", err)
			}
			if strings.Contains(err.Error(), "secretpassword") {
				t.Errorf("error leaks the value: %v", err)
			}
		})
	}
}

func TestMissingDotEnvIsFine(t *testing.T) {
	got, err := readDotEnv(filepath.Join(t.TempDir(), ".env"))
	if err != nil || len(got) != 0 {
		t.Fatalf("got %v, %v", got, err)
	}
}

// Precedence: defaults < config.yaml < .env < real environment.
func TestLoadReadsDotEnvNextToConfig(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "config.yaml")
	write := func(name, content string) {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	write("config.yaml", "queue:\n  size: 64\n  workers: 3\ndatabase:\n  url: postgres://yaml\n")
	write(EnvFileName, "NSOSYAL_DATABASE_URL=postgres://from-dotenv\nNSOSYAL_QUEUE_SIZE=128\n")
	t.Setenv("NSOSYAL_QUEUE_SIZE", "512")

	cfg, err := Load(cfgPath)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Database.URL != "postgres://from-dotenv" {
		t.Errorf(".env did not override config.yaml: url = %q", cfg.Database.URL)
	}
	if cfg.Queue.Size != 512 {
		t.Errorf("real env did not override .env: queue.size = %d", cfg.Queue.Size)
	}
	if cfg.Queue.Workers != 3 {
		t.Errorf("config.yaml value lost: queue.workers = %d", cfg.Queue.Workers)
	}
}

func TestLoadRejectsBrokenDotEnv(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "config.yaml"), nil, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, EnvFileName), []byte("not a valid line"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(filepath.Join(dir, "config.yaml")); err == nil {
		t.Fatal("want error for a broken .env")
	}
}
