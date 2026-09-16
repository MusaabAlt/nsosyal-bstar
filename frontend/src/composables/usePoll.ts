import { getCurrentInstance, onBeforeUnmount, onMounted } from 'vue'

/**
 * Runs `task` now and then every `intervalMs` while the component is mounted.
 * A run never overlaps the previous one, and polling pauses while the tab is
 * hidden, so an idle panel does not load the server.
 */
export function usePoll(task: () => Promise<unknown>, intervalMs: number) {
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false
  let stopped = false

  async function run() {
    if (running || stopped) return
    running = true
    try {
      await task()
    } finally {
      running = false
      schedule()
    }
  }

  function schedule() {
    if (timer) clearTimeout(timer)
    if (stopped) return
    timer = setTimeout(() => {
      if (typeof document !== 'undefined' && document.hidden) schedule()
      else void run()
    }, intervalMs)
  }

  function onVisible() {
    if (!document.hidden) void run()
  }

  function start() {
    stopped = false
    document.addEventListener('visibilitychange', onVisible)
    void run()
  }

  function stop() {
    stopped = true
    if (timer) clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisible)
  }

  if (getCurrentInstance()) {
    onMounted(start)
    onBeforeUnmount(stop)
  }

  /** Runs the task now (after an action), then keeps the interval. */
  return { refresh: run, start, stop }
}
