package supervisor

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/inference"
)

// TestHelperProcess is not a real test: the supervisor tests start this test
// binary as the "Python" child. It serves /health on HELPER_ADDR and exits
// after HELPER_EXIT_AFTER if set.
func TestHelperProcess(t *testing.T) {
	addr := os.Getenv("SUPERVISOR_HELPER_ADDR")
	if addr == "" {
		return
	}
	if d, err := time.ParseDuration(os.Getenv("SUPERVISOR_HELPER_EXIT_AFTER")); err == nil {
		time.AfterFunc(d, func() { os.Exit(3) })
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"status":"ok","artifact_hash":"helper"}`))
	})
	fmt.Println("helper listening on", addr)
	_ = http.ListenAndServe(addr, mux)
	os.Exit(0)
}

func freeAddr(t *testing.T) string {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := l.Addr().String()
	l.Close()
	return addr
}

func helperSupervisor(t *testing.T, addr, exitAfter string) (*Supervisor, *inference.Client) {
	t.Helper()
	t.Setenv("SUPERVISOR_HELPER_ADDR", addr)
	t.Setenv("SUPERVISOR_HELPER_EXIT_AFTER", exitAfter)
	client := inference.New(inference.Config{URL: "http://" + addr, HealthTimeout: 500 * time.Millisecond, BreakerFailures: 3, BreakerOpenFor: time.Second})
	cfg := Config{
		Manage:            true,
		Command:           os.Args[0],
		Args:              []string{"-test.run=^TestHelperProcess$"},
		HealthInterval:    100 * time.Millisecond,
		StartupGrace:      5 * time.Second,
		RestartBackoffMin: 50 * time.Millisecond,
		RestartBackoffMax: 200 * time.Millisecond,
	}
	log := slog.New(slog.NewTextHandler(io.Discard, nil))
	return New(cfg, "http://"+addr, client, log), client
}

func waitUntil(t *testing.T, what string, timeout time.Duration, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatalf("timed out waiting for %s", what)
		}
		time.Sleep(20 * time.Millisecond)
	}
}

func TestStartsProcessAndReportsHealthy(t *testing.T) {
	addr := freeAddr(t)
	s, client := helperSupervisor(t, addr, "")
	s.Start()
	waitUntil(t, "healthy", 10*time.Second, func() bool { return client.Health().Status == "ok" })

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := s.Stop(ctx); err != nil {
		t.Fatal(err)
	}
	// The process tree is gone: nothing answers on the port any more.
	waitUntil(t, "port freed", 5*time.Second, func() bool {
		conn, err := net.DialTimeout("tcp", addr, 100*time.Millisecond)
		if err != nil {
			return true
		}
		conn.Close()
		return false
	})
}

func TestRestartsAfterCrash(t *testing.T) {
	addr := freeAddr(t)
	s, client := helperSupervisor(t, addr, "700ms")
	s.Start()
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = s.Stop(ctx)
	}()

	waitUntil(t, "first healthy", 10*time.Second, func() bool { return client.Health().Status == "ok" })
	waitUntil(t, "a restart after the crash", 10*time.Second, func() bool { return s.Restarts() >= 1 })
	waitUntil(t, "healthy again", 10*time.Second, func() bool { return client.Health().Status == "ok" })
}

func TestMonitorOnlyDoesNotStartAnything(t *testing.T) {
	addr := freeAddr(t)
	s, client := helperSupervisor(t, addr, "")
	s.cfg.Manage = false
	s.Start()
	defer func() { _ = s.Stop(context.Background()) }()

	waitUntil(t, "first check", 5*time.Second, func() bool { return client.Health().Status != "unknown" })
	if st := client.Health().Status; st != "unreachable" {
		t.Fatalf("status = %s; nothing should have been started", st)
	}
	if client.Health().Breaker != inference.BreakerOpen {
		t.Fatal("breaker must be open while python is unreachable")
	}
}

func TestDoesNotStartSecondServiceOnBusyPort(t *testing.T) {
	addr := freeAddr(t)
	l, err := net.Listen("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	srv := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"status":"ok","artifact_hash":"manual"}`))
	})}
	go srv.Serve(l)
	defer srv.Close()

	s, client := helperSupervisor(t, addr, "")
	s.Start()
	defer func() { _ = s.Stop(context.Background()) }()
	waitUntil(t, "healthy", 5*time.Second, func() bool { return client.Health().ArtifactHash == "manual" })
	if s.running() {
		t.Fatal("started a second service while the port was taken")
	}
}
