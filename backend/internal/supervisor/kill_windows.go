//go:build windows

package supervisor

import (
	"os/exec"
	"strconv"
	"syscall"
)

// createNewProcessGroup keeps Ctrl+C in the Go console from reaching Python
// directly; Go decides when and how Python stops.
const createNewProcessGroup = 0x00000200

func prepareCommand(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: createNewProcessGroup}
}

// killTree kills the process and every child it started. Killing only the
// parent would leave uvicorn's worker holding port 8001.
func killTree(cmd *exec.Cmd) error {
	kill := exec.Command("taskkill", "/T", "/F", "/PID", strconv.Itoa(cmd.Process.Pid))
	if err := kill.Run(); err != nil {
		return cmd.Process.Kill()
	}
	return nil
}
