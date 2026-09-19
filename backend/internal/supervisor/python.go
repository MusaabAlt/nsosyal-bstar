// Package supervisor starts the Python inference service, watches it with
// health checks and restarts it when it dies or hangs.
//
// Rules it follows:
//   - Model loading takes a while: during StartupGrace a service that is not
//     healthy yet is left alone.
//   - After the grace period, a service that stays unreachable for
//     hungAfter consecutive checks is killed and restarted.
//   - Restarts back off exponentially (RestartBackoffMin to Max) so a
//     service that crashes at once cannot spin the CPU. The backoff resets
//     after the service has been healthy for a while.
//   - The whole process tree is killed (uvicorn starts workers), so no
//     orphan keeps port 8001 busy.
//   - If something already answers on the port when Go starts (a service
//     started by hand, or a leftover), it is monitored, not started twice.
//   - With Manage=false it only monitors (python.enabled: false).
package supervisor

import (
	"bufio"
	"context"
	"errors"
	"io"
	"log/slog"
	"net"
	"net/url"
	"os/exec"
	"sync"
	"time"

	"github.com/MusaabAlt/nsosyal-bstar/backend/internal/inference"
)

const hungAfter = 3

type Config struct {
	Manage            bool
	Command           string
	Args              []string
	WorkDir           string
	HealthInterval    time.Duration
	StartupGrace      time.Duration
	RestartBackoffMin time.Duration
	RestartBackoffMax time.Duration
}

// HealthChecker is the part of the inference client the supervisor uses.
type HealthChecker interface {
	CheckHealth(ctx context.Context) inference.Health
	MarkDown(reason string)
}

type Supervisor struct {
	cfg    Config
	client HealthChecker
	addr   string // host:port of the service, for the port-in-use check
	log    *slog.Logger

	mu       sync.Mutex
	cmd      *exec.Cmd
	exited   chan struct{}
	restarts int

	stop chan struct{}
	done chan struct{}
}

func New(cfg Config, serviceURL string, client HealthChecker, log *slog.Logger) *Supervisor {
	addr := ""
	if u, err := url.Parse(serviceURL); err == nil {
		addr = u.Host
	}
	if log == nil {
		log = slog.Default()
	}
	return &Supervisor{
		cfg: cfg, client: client, addr: addr,
		log:  log.With("component", "python-supervisor"),
		stop: make(chan struct{}), done: make(chan struct{}),
	}
}

// Start begins supervision in the background.
func (s *Supervisor) Start() { go s.loop() }

// Restarts is how many times the service was (re)started after the first start.
func (s *Supervisor) Restarts() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.restarts
}

// Stop ends supervision and kills the managed process tree.
func (s *Supervisor) Stop(ctx context.Context) error {
	select {
	case <-s.stop:
	default:
		close(s.stop)
	}
	select {
	case <-s.done:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

func (s *Supervisor) loop() {
	defer close(s.done)
	defer s.killProcess()

	ticker := time.NewTicker(s.cfg.HealthInterval)
	defer ticker.Stop()

	var (
		startedAt    time.Time
		unreachable  int
		backoff      = s.cfg.RestartBackoffMin
		healthySince time.Time
		first        = true
	)

	start := func() {
		if !s.cfg.Manage {
			return
		}
		if s.portInUse() {
			s.log.Warn("something already listens on the inference port; monitoring it instead of starting a second service", "addr", s.addr)
			return
		}
		if err := s.startProcess(); err != nil {
			s.log.Error("could not start python", "error", err)
			s.client.MarkDown("start failed: " + err.Error())
			return
		}
		if !first {
			s.mu.Lock()
			s.restarts++
			s.mu.Unlock()
		}
		first = false
		startedAt = time.Now()
		unreachable = 0
	}

	restart := func(reason string) bool {
		s.client.MarkDown(reason)
		s.killProcess()
		s.log.Warn("restarting python", "reason", reason, "backoff", backoff)
		select {
		case <-time.After(backoff):
		case <-s.stop:
			return false
		}
		backoff = min(backoff*2, s.cfg.RestartBackoffMax)
		start()
		return true
	}

	start()
	s.check(&unreachable, &healthySince)

	for {
		select {
		case <-s.stop:
			return
		case <-s.exitedChan():
			code := s.exitCode()
			if !restart("python process exited with code " + code) {
				return
			}
		case <-ticker.C:
			healthy := s.check(&unreachable, &healthySince)
			if healthy && !healthySince.IsZero() && time.Since(healthySince) > time.Minute {
				backoff = s.cfg.RestartBackoffMin // stable again: forget old crashes
			}
			if !s.cfg.Manage || !s.running() {
				continue
			}
			inGrace := time.Since(startedAt) < s.cfg.StartupGrace
			if !healthy && !inGrace && unreachable >= hungAfter {
				if !restart("python unreachable after startup grace (hung)") {
					return
				}
			}
		}
	}
}

// check runs one health check and updates the counters. It returns true when healthy.
func (s *Supervisor) check(unreachable *int, healthySince *time.Time) bool {
	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		select {
		case <-s.stop:
			cancel()
		case <-ctx.Done():
		}
	}()
	h := s.client.CheckHealth(ctx)
	cancel()

	switch h.Status {
	case "ok":
		*unreachable = 0
		if healthySince.IsZero() {
			*healthySince = time.Now()
			s.log.Info("python healthy", "artifact_hash", h.ArtifactHash)
		}
		return true
	case "loading":
		*unreachable = 0
	default:
		*unreachable++
	}
	if !healthySince.IsZero() {
		s.log.Warn("python not healthy", "status", h.Status, "error", h.Error)
	}
	*healthySince = time.Time{}
	return false
}

func (s *Supervisor) startProcess() error {
	cmd := exec.Command(s.cfg.Command, s.cfg.Args...)
	cmd.Dir = s.cfg.WorkDir
	prepareCommand(cmd)

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return err
	}
	if err := cmd.Start(); err != nil {
		return err
	}

	exited := make(chan struct{})
	s.mu.Lock()
	s.cmd, s.exited = cmd, exited
	s.mu.Unlock()

	var pipes sync.WaitGroup
	pipes.Add(2)
	go s.forward(stdout, "stdout", &pipes)
	go s.forward(stderr, "stderr", &pipes)
	go func() {
		pipes.Wait() // read all output before Wait closes the pipes
		_ = cmd.Wait()
		close(exited)
	}()

	s.log.Info("python started", "pid", cmd.Process.Pid, "command", s.cfg.Command, "args", s.cfg.Args, "dir", s.cfg.WorkDir)
	return nil
}

// forward copies the service's output into our structured log.
func (s *Supervisor) forward(r io.Reader, stream string, wg *sync.WaitGroup) {
	defer wg.Done()
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 64*1024), 1024*1024)
	for sc.Scan() {
		s.log.Info("python", "stream", stream, "line", sc.Text())
	}
}

func (s *Supervisor) exitedChan() <-chan struct{} {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.exited == nil {
		return nil // nothing running: never fires
	}
	return s.exited
}

func (s *Supervisor) running() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.exited == nil {
		return false
	}
	select {
	case <-s.exited:
		return false
	default:
		return true
	}
}

func (s *Supervisor) exitCode() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cmd == nil || s.cmd.ProcessState == nil {
		return "unknown"
	}
	return s.cmd.ProcessState.String()
}

func (s *Supervisor) killProcess() {
	s.mu.Lock()
	cmd, exited := s.cmd, s.exited
	s.cmd, s.exited = nil, nil
	s.mu.Unlock()
	if cmd == nil || cmd.Process == nil {
		return
	}
	select {
	case <-exited:
		return // already gone
	default:
	}
	if err := killTree(cmd); err != nil && !errors.Is(err, context.Canceled) {
		s.log.Warn("kill python", "pid", cmd.Process.Pid, "error", err)
	}
	select {
	case <-exited:
		s.log.Info("python stopped", "pid", cmd.Process.Pid)
	case <-time.After(5 * time.Second):
		s.log.Error("python did not exit after kill", "pid", cmd.Process.Pid)
	}
}

func (s *Supervisor) portInUse() bool {
	if s.addr == "" {
		return false
	}
	conn, err := net.DialTimeout("tcp", s.addr, 300*time.Millisecond)
	if err != nil {
		return false
	}
	_ = conn.Close()
	return true
}
