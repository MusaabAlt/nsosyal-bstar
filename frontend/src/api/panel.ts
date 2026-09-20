import type { Action, AnalysisResult } from '@/contract/types'
import { ensureSession } from './httpSource'
import { setRepresentative } from './representative'

/*
 * The moderation panel's reads and actions: /api/panel/* on the Go backend
 * (backend/internal/http/handlers/panel.go). Every number arrives computed;
 * the screens only format it.
 */

export type Fetched<T> = { ok: true; data: T } | { ok: false; status: number | null; code?: string }

async function request<T>(url: string, init?: RequestInit): Promise<Fetched<T>> {
  try {
    const response = await fetch(url, init)
    if (!response.ok) {
      let code: string | undefined
      try {
        code = ((await response.json()) as { error?: { code?: string } }).error?.code
      } catch {
        /* not our JSON shape */
      }
      return { ok: false, status: response.status, code }
    }
    return { ok: true, data: (await response.json()) as T }
  } catch {
    return { ok: false, status: null }
  }
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '' || value === false) continue
    q.set(key, String(value))
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

// ------------------------------------------------------------------ types

export type CategoryStatus = 'live' | 'stub' | 'unknown'

export interface Category {
  /** A content code or "binary_offensive". */
  code: string
  family: string
  threshold: number | null
  action: Action | null
  /** false while the threshold is still a placeholder in thresholds.yaml. */
  derived: boolean
  status: CategoryStatus
  module: string
}

export interface CategoryList {
  source: string
  categories: Category[]
  representative?: boolean
}

export type RangeName = 'live' | 'today' | 'week'

export interface Kpi {
  value: number
  previous?: number
  change_pct: number | null
  share_pct?: number | null
}

export interface QueueCounts {
  pending: number
  pending_detected: number
  reviewed: number
  auto: number
}

export interface OverviewCategory extends Category {
  total: number
  buckets: number[]
}

/** How many comments in the window ended on each verdict; counted by the server. */
export interface VerdictCounts {
  block: number
  escalate: number
  review: number
  nudge: number
  clean: number
  undecided: number
}

export interface Overview {
  range: RangeName
  start: string
  now: string
  bucket_seconds: number
  bucket_starts: string[]
  analysed: Kpi
  detected: Kpi
  automatic: Kpi
  /** review + escalate, with its share of `analysed` already computed by Go. */
  human_review: Kpi
  verdicts: VerdictCounts
  queue: QueueCounts
  categories: OverviewCategory[]
  categories_error?: string
  patterns: Array<{ code: string; count: number }>
  system: {
    artifact_hash: string
    python_status: string
    latency_p95_ms: number | null
    latency_window: string
    active_devices: number | null
    active_devices_window: string
    live_categories: number
    total_categories: number
  }
  representative: boolean
}

export type ModeratorAction = 'approve' | 'hide' | 'remove' | 'queue' | 'false_positive'
export type ItemStatus = 'pending' | 'reviewed' | 'auto' | 'none'

export interface PanelItem {
  id: string
  nickname: string
  text: string
  created_at: string
  final_action: Action | null
  fired_types: string[]
  guards_active: string[]
  degraded: boolean
  explanation: string
  detected: boolean
  status: ItemStatus
  latest_action: ModeratorAction | null
  latest_action_at: string | null
  latency_ms: number
  result: AnalysisResult
}

export interface Page<T> {
  items: T[]
  next_cursor?: string
}

export interface ItemDetail {
  item: PanelItem
  actions: Array<{ action: ModeratorAction; nickname: string | null; created_at: string }>
  previous: PanelItem[]
}

export interface PanelEvent {
  kind: 'moderator' | 'system'
  key: string
  created_at: string
  action: string | null
  actor: string | null
  comment_id: string
  author: string
  text: string
  fired_types: string[]
  detected: boolean
  degraded: boolean
  explanation: string
}

export interface MetricBucket {
  start: string
  requests: number
  errors: number
  p50_ms: number | null
  p95_ms: number | null
}

export interface Metrics {
  bucket_seconds: number
  analyses: MetricBucket[]
  all_requests: MetricBucket[]
  now: string
  requests_per_second: number | null
  error_rate_pct: number | null
  active_devices: number | null
  active_devices_window: string
  latency: { samples: number; p50_ms: number | null; p95_ms: number | null; window: string }
  slow_p95_ms: number
  slow: boolean
}

export interface LatencySummary {
  samples: number
  total: number
  p50_ms: number | null
  p95_ms: number | null
  p99_ms: number | null
  max_ms: number | null
  window: string
}

export interface Health {
  status: 'ok' | 'degraded'
  go: { status: string; uptime_seconds: number; goroutines: number }
  python: {
    status: string
    artifact_hash?: string
    degraded_modules?: string[]
    capabilities?: Array<{ code: string; module: string }>
    representative: boolean
    breaker: string
    checked_at: string
    error?: string
  }
  postgres: { status: string; latency_ms?: number; error?: string }
  queue: {
    queue_len: number
    queue_capacity: number
    in_flight: number
    workers: number
    submitted: number
    rejected: number
    expired: number
    batches: number
    batch_errors: number
  }
  writer: {
    analyses_queued: number
    analyses_written: number
    analyses_dropped: number
    metrics_queued: number
    metrics_written: number
    metrics_dropped: number
  }
}

export interface Stats {
  latency: Record<'request' | 'queue_wait' | 'model', LatencySummary>
  cache: { entries: number; capacity: number; hits: number; misses: number }
  uptime_seconds: number
}

// ---------------------------------------------------------------- fetchers

export async function fetchOverview(range: RangeName): Promise<Fetched<Overview>> {
  const out = await request<Overview>(`/api/panel/overview${query({ range })}`)
  if (out.ok) setRepresentative(out.data.representative)
  return out
}

export function fetchItems(params: {
  status?: ItemStatus | ''
  detected?: boolean
  code?: string
  q?: string
  limit?: number
  cursor?: string
}): Promise<Fetched<Page<PanelItem>>> {
  return request(`/api/panel/items${query(params)}`)
}

export function fetchItem(id: string): Promise<Fetched<ItemDetail>> {
  return request(`/api/panel/items/${encodeURIComponent(id)}`)
}

export function fetchQueueCounts(): Promise<Fetched<QueueCounts>> {
  return request('/api/panel/queue-counts')
}

export function fetchEvents(params: { kind?: string; q?: string; limit?: number; cursor?: string }): Promise<Fetched<Page<PanelEvent>>> {
  return request(`/api/panel/events${query(params)}`)
}

export function fetchMetrics(): Promise<Fetched<Metrics>> {
  return request('/api/panel/metrics')
}

export function fetchHealth(): Promise<Fetched<Health>> {
  return request('/api/health')
}

export function fetchStats(): Promise<Fetched<Stats>> {
  return request('/api/stats')
}

export async function fetchCategories(): Promise<Fetched<CategoryList>> {
  const out = await request<CategoryList>('/api/categories')
  if (out.ok) setRepresentative(out.data.representative)
  return out
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Records a moderator action. A comment analysed a moment ago may not be
 * stored yet (the server writes in the background), so a "not found" is
 * retried a few times before it is reported.
 */
export async function recordAction(
  commentIds: string[],
  action: ModeratorAction,
): Promise<Fetched<{ recorded: number; missing: string[] }>> {
  const session = await ensureSession().catch(() => null)
  const body = JSON.stringify({
    comment_ids: commentIds,
    action,
    session_id: typeof session === 'string' ? session : '',
  })
  let out: Fetched<{ recorded: number; missing: string[] }> = { ok: false, status: null }
  for (const wait of [0, 400, 800, 1600]) {
    if (wait) await sleep(wait)
    out = await request('/api/panel/actions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
    if (out.ok || out.status !== 404) return out
  }
  return out
}
