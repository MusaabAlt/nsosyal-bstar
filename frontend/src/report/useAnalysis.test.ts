import { describe, expect, it, vi } from 'vitest'
import type { AnalysisSource, AnalyzeOutcome } from '@/api'
import { resolveMock } from '@/api/mockSource'
import { MIN_REVEAL_MS, errorLine, useAnalysis } from './useAnalysis'

function sourceReturning(outcome: AnalyzeOutcome): AnalysisSource {
  return { presets: [], analyze: async () => outcome }
}

describe('analysis flow', () => {
  it('holds the analysing state for at least 400ms, then reveals the report', async () => {
    const wait = vi.fn(async () => {})
    const { phase, result, analyze } = useAnalysis(sourceReturning(resolveMock('Bu bir test cumlesi', null)), wait)
    const running = analyze('Bu bir test cumlesi')
    expect(phase.value).toBe('analysing')
    await running
    expect(wait).toHaveBeenCalledOnce()
    const [held] = wait.mock.calls[0] as unknown as [number]
    expect(held).toBeGreaterThan(0)
    expect(held).toBeLessThanOrEqual(MIN_REVEAL_MS)
    expect(phase.value).toBe('report')
    // The latency shown is the payload's measured value, untouched by the hold.
    expect(result.value?.latency_ms).toBe(0.26349996915087104)
  })

  it('does nothing for empty input', async () => {
    const analyzeSpy = vi.fn()
    const { phase, analyze } = useAnalysis({ presets: [], analyze: analyzeSpy }, async () => {})
    await analyze('   ')
    expect(analyzeSpy).not.toHaveBeenCalled()
    expect(phase.value).toBe('idle')
  })

  it.each([
    ['network', 'Analiz servisi yanıt vermedi.'],
    ['400', 'Analiz servisi isteği kabul etmedi.'],
    ['404', 'Analiz servisi isteği kabul etmedi.'],
    ['413', 'Metin, analiz servisinin kabul ettiği boyutu aşıyor.'],
    ['500', 'Analiz servisi yanıt vermedi.'],
  ])('error %s gives a readable line, never a blank screen', async (forced, line) => {
    const { phase, errorText, analyze } = useAnalysis(sourceReturning(resolveMock('x', forced)), async () => {})
    await analyze('x')
    expect(phase.value).toBe('error')
    expect(errorText.value).toBe(line)
  })

  it('verdict null shows the error state with the decision layer sentence', async () => {
    const { phase, errorText, result, analyze } = useAnalysis(
      sourceReturning(resolveMock('x', 'decision-null')),
      async () => {},
    )
    await analyze('x')
    expect(phase.value).toBe('error')
    expect(errorText.value.startsWith('Karar verilemedi: karar katmanında')).toBe(true)
    expect(result.value).toBeNull()
  })

  it('a source that throws becomes the network error state', async () => {
    const throwing: AnalysisSource = {
      presets: [],
      analyze: async () => {
        throw new TypeError('Failed to fetch')
      },
    }
    const { phase, errorText, analyze } = useAnalysis(throwing, async () => {})
    await analyze('x')
    expect(phase.value).toBe('error')
    expect(errorText.value).toBe(errorLine({ kind: 'network' }))
  })
})

describe('mock source', () => {
  it('maps the preset texts to their payloads and anything else to degraded', () => {
    const verdictOf = (text: string) => {
      const o = resolveMock(text, null)
      return o.ok ? o.result.verdict : null
    }
    expect(verdictOf('Seni b1tireceğim')).toBe('escalate')
    expect(verdictOf('amcam geldi')).toBe('clean')
    expect(verdictOf('Bu bir test cumlesi')).toBe('clean')
    const other = resolveMock('başka bir cümle 😀', null)
    expect(other.ok && other.result.text).toBe('başka bir cümle 😀')
    expect(other.ok && other.result.signals.pipeline?.degraded?.length).toBe(1)
  })

  it('returns copies, so a screen cannot corrupt the sample data', () => {
    const a = resolveMock('Seni b1tireceğim', null)
    if (a.ok) a.result.content.length = 0
    const b = resolveMock('Seni b1tireceğim', null)
    expect(b.ok && b.result.content.length).toBe(2)
  })
})
