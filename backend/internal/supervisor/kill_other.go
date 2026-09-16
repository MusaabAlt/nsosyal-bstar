//go:build !windows

package supervisor

import (
	"os/exec"
	"syscall"
)

// prepareCommand puts Python in its own process group so the whole tree can
// be signalled at once.
func prepareCommand(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
}

func killTree(cmd *exec.Cmd) error {
	// Negative pid: the whole process group.
	if err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL); err != nil {
		return cmd.Process.Kill()
	}
	return nil
}
