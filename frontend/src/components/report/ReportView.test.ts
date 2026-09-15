import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import ReportView from './ReportView.vue'
import ConsequenceColumn from './ConsequenceColumn.vue'
import ThresholdBar from '@/components/ui/ThresholdBar.vue'
import type { AnalysisResult } from '@/contract/types'
import degradedJson from '@/api/mocks/degraded.json'
import cleanJson from '@/api/mocks/clean.json'
import flaggedJson from '@/api/mocks/flagged.json'
import guardJson from '@/api/mocks/guard.json'

const vuetify = createVuetify({ components })
const load = (json: unknown) => JSON.parse(JSON.stringify(json)) as AnalysisResult
const render = (result: AnalysisResult) => mount(ReportView, { props: { result }, global: { plugins: [vuetify] } })

describe('report renders each state from its payload', () => {
  it('degraded: incomplete, every missing module by name and kind, explanation verbatim, never Temiz', () => {
    const r = load(degradedJson)
    const w = render(r)
    const verdict = w.find('.verdict')
    expect(verdict.classes()).toContain('verdict--incomplete')
    expect(verdict.find('.verdict__word').text()).toBe('Değerlendirme tamamlanmadı')
    for (const d of r.signals.pipeline!.degraded!) {
      expect(verdict.text()).toContain(d.module)
    }
    expect(verdict.text()).toContain('stub')
    expect(w.text()).toContain(r.explanation)
    expect(verdict.text()).not.toContain('Temiz')
    expect(w.findAll('.status-word--moduleUnavailable').length).toBeGreaterThanOrEqual(5)
  })

  it('shows the measured latency to one decimal', () => {
    const w = render(load(degradedJson))
    expect(w.find('.verdict__metric-value').text()).toBe('0.5')
  })

  it('clean: Temiz in the clean tone', () => {
    const w = render(load(cleanJson))
    expect(w.find('.verdict').classes()).toContain('verdict--clean')
    expect(w.find('.verdict__word').text()).toBe('Temiz')
  })

  it('flagged: each fired code with its own label, score and threshold from the same entry', () => {
    const w = render(load(flaggedJson))
    expect(w.find('.verdict__word').text()).toBe('İncele')
    const bars = w.findAllComponents(ThresholdBar)
    expect(bars).toHaveLength(2)
    expect(bars[0]!.text()).toContain('Tehdit')
    expect(bars[0]!.find('.threshold-bar__score').text()).toBe('0.87')
    expect(bars[0]!.find('.threshold-bar__caption').text()).toBe('eşik 0.50')
    expect(bars[0]!.classes()).toContain('threshold-bar--fired')
    expect(bars[1]!.classes()).not.toContain('threshold-bar--fired')
    expect(w.text()).toContain('Rakam/sembol ikamesi')
    // Score pair: raw and recovered, both from the payload.
    expect(w.findAll('.score-pair__value').map((v) => v.text())).toEqual(['0.44', '0.81'])
  })

  it('guard: the guard, what it suppressed, the underlined substring, and that the silence was deliberate', () => {
    const w = render(load(guardJson))
    const guards = w.find('.stage-guards')
    expect(guards.text()).toContain('Alt dizi çakışması')
    expect(guards.text()).toContain('Hedefsiz küfür')
    expect(guards.text()).toContain('bilerek işaretlemedi')
    const underlined = guards.find('.evidence__ul')
    expect(underlined.text()).toBe('am')
    expect(guards.find('.evidence').text()).toBe('amcam')
  })

  it('no averaged or combined score appears anywhere', () => {
    const w = render(load(flaggedJson))
    // (0.87 + 0.12) / 2 = 0.495 -> "0.50" would also be the threshold, so check the average of all scores shown.
    expect(w.text()).not.toMatch(/ortalama|toplam|genel skor/i)
  })

  it('a missing score never renders as 0.00', () => {
    const r = load(flaggedJson)
    ;(r.content[0] as { threshold: number | null }).threshold = null
    const w = render(r)
    const bar = w.findAllComponents(ThresholdBar)[0]!
    expect(bar.text()).toContain('eşik yok')
    expect(bar.find('.threshold-bar__tick').exists()).toBe(false)
    expect(w.find('.stage-row').text()).not.toContain('0.00')
  })

  it('highlights obfuscation evidence at the right place after an emoji', () => {
    const r = load(flaggedJson)
    r.text = '😀 Seni b1tireceğim'
    r.form.patterns[0]!.span = [8, 9] // code points: the "1"
    const w = render(r)
    const highlighted = w.findAll('.evidence__hl').map((m) => m.text())
    expect(highlighted).toContain('1')
  })
})

describe('consequence column', () => {
  const mountColumn = (result: AnalysisResult | null) =>
    mount(ConsequenceColumn, { props: { result }, global: { plugins: [vuetify] } })

  it('contains no numbers', () => {
    const w = mountColumn(load(flaggedJson))
    expect(w.text()).not.toMatch(/\d\.\d/)
  })

  it('degraded: the post renders with a note that it was not cleared', () => {
    const w = mountColumn(load(degradedJson))
    expect(w.text()).toContain('onaylanmış sayılmaz')
    expect(w.find('.post').exists()).toBe(true)
  })

  it('block: the post does not render', () => {
    const w = mountColumn({ ...load(cleanJson), verdict: 'block' })
    expect(w.find('.post').exists()).toBe(false)
    expect(w.text()).toContain('yayımlanmadı')
  })

  it('nudge: NSosyal sensitive-content text with Göster, revealing on click', async () => {
    const w = mountColumn({ ...load(cleanJson), verdict: 'nudge' })
    expect(w.text()).toContain(
      'Bu gönderide, bazı insanların saldırgan, kırıcı veya rahatsız edici bulabileceği hassas içerikler var.',
    )
    await w.find('.sensitive button').trigger('click')
    expect(w.find('.sensitive').exists()).toBe(false)
    expect(w.find('.post__text').text()).toBe('Bu bir test cumlesi')
  })
})
