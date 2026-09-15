import { ref, shallowRef } from 'vue'
import type { AnalysisSource, AnalyzeError, Extras } from '@/api'
import { NO_EXTRAS } from '@/api/source'
import type { AnalysisResult } from '@/contract/types'
import { isDecisionFailure } from './model'
import { copy } from '@/copy'

/*
 * The Analiz page flow: idle -> analysing -> report | error. One state at a
 * time (pages-spec 2).
 *
 * The backend answers faster than perception, so the analysing state is held
 * for at least MIN_REVEAL_MS before revealing (pages-spec 2.2). Only the
 * moment of reveal is delayed: the latency shown is always the measured
 * latency_ms from the payload.
 */
export const MIN_REVEAL_MS = 400

export type Phase = 'idle' | 'analysing' | 'report' | 'error'

const LINE_BY_CODE: Record<string, string> = {
  queue_full: copy.errors.busy,
  model_loading: copy.errors.modelLoading,
  model_unavailable: copy.errors.modelRestarting,
  shutting_down: copy.errors.modelRestarting,
  model_error: copy.errors.modelError,
  rate_limited: copy.errors.rateLimited,
  timeout: copy.errors.timeout,
  database_unavailable: copy.errors.database,
  body_too_large: copy.errors.tooLarge,
}

/** One plain line for each failure (design-system 4.18): what failed, no codes. */
export function errorLine(error: AnalyzeError): string {
  if (error.kind === 'network') return copy.errors.network
  const byCode = error.code ? LINE_BY_CODE[error.code] : undefined
  if (byCode) return byCode
  if (error.status === 413) return copy.errors.tooLarge
  if (error.status === 429) return copy.errors.rateLimited
  if (error.status === 503) return copy.errors.busy
  if (error.status === 504) return copy.errors.timeout
  if (error.status !== undefined && error.status >= 400 && error.status < 500) return copy.errors.rejected
  return copy.errors.network
}

export function useAnalysis(source: AnalysisSource, wait = (ms: number) => new Promise((r) => setTimeout(r, ms))) {
  const phase = ref<Phase>('idle')
  const result = shallowRef<AnalysisResult | null>(null)
  const extras = shallowRef<Extras>(NO_EXTRAS)
  const errorText = ref('')
  let controller: AbortController | null = null
  let runId = 0

  async function analyze(text: string) {
    if (text.trim() === '') return
    controller?.abort()
    controller = new AbortController()
    const id = ++runId

    phase.value = 'analysing'
    const started = performance.now()
    let outcome
    try {
      outcome = await source.analyze(text, controller.signal)
    } catch {
      outcome = { ok: false as const, error: { kind: 'network' as const } }
    }
    const elapsed = performance.now() - started
    if (elapsed < MIN_REVEAL_MS) await wait(MIN_REVEAL_MS - elapsed)
    if (id !== runId) return // a newer analysis replaced this one

    if (!outcome.ok) {
      result.value = null
      errorText.value = errorLine(outcome.error)
      phase.value = 'error'
      return
    }
    if (isDecisionFailure(outcome.result)) {
      // verdict null: no judgement was made. The decision layer's own sentence says why.
      result.value = null
      errorText.value = outcome.result.explanation || copy.errors.network
      phase.value = 'error'
      return
    }
    result.value = outcome.result
    extras.value = outcome.extras
    phase.value = 'report'
  }

  return { phase, result, extras, errorText, analyze }
}
