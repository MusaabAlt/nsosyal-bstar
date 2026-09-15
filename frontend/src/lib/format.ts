/*
 * Number formatting (design-system 5 and 6). Every function returns null for
 * a value the response did not contain, so the caller renders it as
 * unavailable. A missing value must never become "0.00": a zero and a missing
 * value look the same to a juror and one of them is untrue.
 */

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

/** Scores and thresholds: two decimals. */
export function formatScore(value: unknown): string | null {
  return isNumber(value) ? value.toFixed(2) : null
}

/** Latency and durations: one decimal; the unit is rendered separately. */
export function formatMs(value: unknown): string | null {
  return isNumber(value) ? value.toFixed(1) : null
}
