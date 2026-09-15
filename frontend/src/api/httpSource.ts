import type { AnalysisResult } from '@/contract/types'
import type { AnalysisSource, AnalyzeError, AnalyzeOutcome } from './source'
import { presets } from './presets'

/*
 * Real data source: the Go backend.
 *
 *   POST /api/sessions {nickname}          -> {id}
 *   POST /api/comments {session_id, text}  -> {comment, result: AnalysisResult, timing}
 *
 * The console has no accounts (pages-spec 1), so an anonymous session is
 * created once, silently, and kept for the browser tab. If the server no
 * longer knows it (database reset), a new one is created and the request is
 * sent again once.
 */

const SESSION_KEY = 'nsosyal.session'
const OPERATOR_NICKNAME = 'Operatör'

interface ErrorBody {
  error?: { code?: string; message?: string }
}

function readSession(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY)
  } catch {
    return null // storage blocked: keep working with an in-memory session
  }
}

let memorySession: string | null = null

function storeSession(id: string | null) {
  memorySession = id
  try {
    if (id) sessionStorage.setItem(SESSION_KEY, id)
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    /* in-memory only */
  }
}

async function errorFrom(response: Response): Promise<AnalyzeError> {
  let body: ErrorBody = {}
  try {
    body = (await response.json()) as ErrorBody
  } catch {
    /* not our JSON shape (e.g. a proxy error page) */
  }
  return { kind: 'http', status: response.status, code: body.error?.code, detail: body.error?.message }
}

async function postJSON(url: string, payload: unknown, signal?: AbortSignal): Promise<Response> {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
}

async function ensureSession(signal?: AbortSignal): Promise<string | AnalyzeError> {
  // Storage first; memory only when storage is blocked.
  const existing = readSession() ?? memorySession
  if (existing) return existing
  const response = await postJSON('/api/sessions', { nickname: OPERATOR_NICKNAME }, signal)
  if (!response.ok) return errorFrom(response)
  const session = (await response.json()) as { id: string }
  storeSession(session.id)
  return session.id
}

async function analyzeOnce(text: string, signal?: AbortSignal): Promise<AnalyzeOutcome & { staleSession?: boolean }> {
  const session = await ensureSession(signal)
  if (typeof session !== 'string') return { ok: false, error: session }

  const response = await postJSON('/api/comments', { session_id: session, text }, signal)
  if (!response.ok) {
    const error = await errorFrom(response)
    return { ok: false, error, staleSession: error.code === 'unknown_session' }
  }
  const body = (await response.json()) as { result: AnalysisResult }
  return { ok: true, result: body.result }
}

export const httpSource: AnalysisSource = {
  representative: false,
  presets,
  async analyze(text, signal) {
    try {
      let outcome = await analyzeOnce(text, signal)
      if (!outcome.ok && outcome.staleSession) {
        storeSession(null)
        outcome = await analyzeOnce(text, signal)
      }
      if (outcome.ok) return { ok: true, result: outcome.result }
      return { ok: false, error: outcome.error }
    } catch {
      // fetch throws only when the server could not be reached at all.
      return { ok: false, error: { kind: 'network' } }
    }
  },
}
