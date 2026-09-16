/*
 * Number and time formatting. Every function returns null for a value the
 * response did not contain, so the caller renders it as unavailable: a
 * missing value must never become "0".
 */

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

const integer = new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 0 })
const oneDecimal = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** Scores and thresholds: two decimals, as the model reports them. */
export function formatScore(value: unknown): string | null {
  return isNumber(value) ? value.toFixed(2) : null
}

/** Latency and durations: one decimal; the unit is rendered separately. */
export function formatMs(value: unknown): string | null {
  return isNumber(value) ? value.toFixed(1) : null
}

/** Counts with Turkish digit grouping: 12.480. */
export function formatCount(value: unknown): string | null {
  return isNumber(value) ? integer.format(value) : null
}

/** A percentage the server computed: %9,0. */
export function formatPercent(value: unknown): string | null {
  return isNumber(value) ? `%${oneDecimal.format(value)}` : null
}

/** A signed change the server computed: +%12,0 or −%5,0. */
export function formatChange(value: unknown): string | null {
  if (!isNumber(value)) return null
  const sign = value > 0 ? '+' : value < 0 ? '−' : ''
  return `${sign}%${oneDecimal.format(Math.abs(value))}`
}

/** "şimdi", "6 dk", "3 sa", "2 g" before now. */
export function formatAgo(iso: string, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000))
  if (seconds < 45) return 'şimdi'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} dk`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} sa`
  return `${Math.round(hours / 24)} g`
}

const clock = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit' })
const clockSeconds = new Intl.DateTimeFormat('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
const dayMonth = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short' })
const longDay = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', year: 'numeric', weekday: 'long' })

export function formatClock(iso: string, seconds = false): string {
  return (seconds ? clockSeconds : clock).format(new Date(iso))
}

export function formatDayMonth(iso: string): string {
  return dayMonth.format(new Date(iso))
}

/** A day heading for the history: Bugün, Dün, or the full date. */
export function formatDayHeading(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const diff = Math.round((startOf(now) - startOf(d)) / 86_400_000)
  if (diff === 0) return 'Bugün'
  if (diff === 1) return 'Dün'
  return longDay.format(d)
}

export function dayKey(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}

/** Two letters for an avatar. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? (parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '') : name.trim().slice(0, 2)
  return letters.toLocaleUpperCase('tr-TR') || '?'
}

/** A value's position on a 0-1 bar as a CSS length. Drawing only; never shown as a number. */
export function barPosition(value: number): string {
  return `${Math.min(Math.max(value, 0), 1) * 100}%`
}
