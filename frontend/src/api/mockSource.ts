import type { AnalysisResult } from '@/contract/types'
import type { AnalysisSource, AnalyzeOutcome } from './source'
import { presets } from './presets'
import degraded from './mocks/degraded.json'
import clean from './mocks/clean.json'
import flagged from './mocks/flagged.json'
import guard from './mocks/guard.json'

/*
 * Sample data source: the five payloads in docs/team/AMIN_BRIEF.md section 7,
 * generated from the real pipeline at commit 6583e5c. The flagged and guard
 * scores are TEST-DOUBLE values: this source always sets representative, so
 * the Temsili veri marker is on screen whenever they are shown.
 *
 * Mapping:
 *   "Seni b1tireceğim"     -> flagged  (obfuscated threat, test-double scores)
 *   "amcam geldi"          -> guard    (substring collision suppressed, test-double)
 *   "Bu bir test cumlesi"  -> clean    (real pipeline with only m0)
 *   any other text         -> degraded (the real default pipeline today)
 *
 * Error states can be previewed in development with ?mock=network, ?mock=400,
 * ?mock=404, ?mock=413, ?mock=500 or ?mock=decision-null.
 */

const payloads = {
  degraded: degraded as unknown as AnalysisResult,
  clean: clean as unknown as AnalysisResult,
  flagged: flagged as unknown as AnalysisResult,
  guard: guard as unknown as AnalysisResult,
}

const byText = new Map<string, AnalysisResult>([
  [payloads.flagged.text, payloads.flagged],
  [payloads.guard.text, payloads.guard],
  [payloads.clean.text, payloads.clean],
])


function forcedState(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get('mock')
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

export function resolveMock(text: string, forced: string | null): AnalyzeOutcome {
  switch (forced) {
    case 'network':
      return { ok: false, error: { kind: 'network' } }
    case '400':
      return { ok: false, error: { kind: 'http', status: 400, detail: 'text must be a string' } }
    case '404':
      return { ok: false, error: { kind: 'http', status: 404, detail: 'not found' } }
    case '413':
      return { ok: false, error: { kind: 'http', status: 413, detail: 'body too large' } }
    case '500':
      return { ok: false, error: { kind: 'http', status: 500, detail: 'internal error: RuntimeError' } }
    case 'decision-null': {
      // verdict null: the decision layer failed (AMIN_BRIEF 5, state 2).
      const result = clone(payloads.degraded)
      result.text = text
      result.verdict = null
      result.explanation = 'Karar verilemedi: karar katmanında RuntimeError oluştu.'
      return { ok: true, result }
    }
  }

  const known = byText.get(text)
  if (known) return { ok: true, result: clone(known) }

  // The degraded payload carries no spans, so it stays truthful for any text.
  const result = clone(payloads.degraded)
  result.text = text
  return { ok: true, result }
}

export const mockSource: AnalysisSource = {
  representative: true,
  presets,
  async analyze(text) {
    return resolveMock(text, forcedState())
  },
}
