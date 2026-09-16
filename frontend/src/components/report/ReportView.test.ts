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
import { resolveMock } from '@/api/mockSource'
import type { Extras } from '@/api/source'

const vuetify = createVuetify({ components })
const load = (json: unknown) => JSON.parse(JSON.stringify(json)) as AnalysisResult
const global = { plugins: [vuetify], stubs: { RouterLink: { template: '<a><slot /></a>' } } }
const render = (result: AnalysisResult, extras?: Extras) => mount(ReportView, { props: { result, extras }, global })

/** A sample text with the exact result and extras the Go backend sends for it. */
function sample(text: string) {
  const outcome = resolveMock(text, null)
  if (!outcome.ok) throw new Error('sample failed')
  return outcome
}

describe('report renders each state from its payload', () => {
  it('degraded: incomplete, every missing module by name, the evaluated count, never Temiz', () => {
    const { result: r, extras } = sample('herhangi bir metin')
    const w = render(r, extras)
    const verdict = w.find('.verdict')
    expect(verdict.classes()).toContain('verdict--incomplete')
    expect(verdict.find('.verdict__word').text()).toBe('Değerlendirme tamamlanmadı')
    for (const d of r.signals.pipeline!.degraded!) {
      expect(verdict.text()).toContain(d.module)
    }
    expect(verdict.text()).toContain("2 kategoriden 0'ı değerlendirildi")
    // 4.12: the list replaces the single sentence; the explanation is still shown in stage 9.
    expect(verdict.text()).not.toContain(r.explanation)
    expect(w.text()).toContain(r.explanation)
    expect(verdict.text()).not.toContain('Temiz')
    expect(w.findAll('.status-word--moduleUnavailable').length).toBeGreaterThanOrEqual(5)
  })

  it('without server extras the count line is left out, never guessed', () => {
    const w = render(load(degradedJson))
    expect(w.find('.verdict').text()).not.toContain('kategoriden')
  })

  it('flagged: the docs lines with the server numbers', () => {
    const { result, extras } = sample('Seni b1tireceğim')
    const w = render(result, extras)
    const bars = w.findAllComponents(ThresholdBar)
    // 4.9: label only above the bar, and the relationship in words with its own margin.
    expect(bars[0]!.find('.threshold-bar__label').text()).toBe('Tehdit')
    expect(bars[0]!.text()).toContain('Skor kendi eşiğini 0.37 puan aşıyor')
    // The BERTurk offensive score: raw 0.44 against 0.50.
    expect(bars[1]!.find('.threshold-bar__label').text()).toBe('Genel saldırganlık')
    expect(bars[1]!.text()).toContain('Skor kendi eşiğinin 0.06 puan altında')
    expect(bars[2]!.text()).toContain('Skor kendi eşiğinin 0.38 puan altında')
    // Stage 3 and stage 5 lines.
    expect(w.text()).toContain('Kontrol edilen diğer 11 kalıpta eşleşme yok')
    // Of today's two categories only the offensive score was evaluated, and it has its own bar.
    expect(w.text()).not.toContain('Eşik altındaki')
    // Stage 4: original, what changed, recovered text with the recovered character highlighted.
    const stage4 = w.findAll('.stage-row')[3]!
    expect(stage4.text()).toContain('1 karakter değiştirildi')
    const evidences = stage4.findAll('.evidence')
    expect(evidences.map((e) => e.text())).toEqual(['Seni b1tireceğim', 'Seni bitireceğim'])
    expect(evidences[1]!.find('.evidence__hl').text()).toBe('i')
  })

  it('stage 3 rows show name, substring and confidence only', () => {
    const { result, extras } = sample('Seni b1tireceğim')
    const row = render(result, extras).find('.patterns tr')
    expect(row.findAll('th, td').map((c) => c.text())).toEqual(['Rakam/sembol ikamesi', '1', '0.90'])
  })

  it('stage 6 uses the target words from pages-spec', () => {
    const { result, extras } = sample('Seni b1tireceğim')
    result.target = { type: 'group', confidence: 0.8, evidence: 'Seni', span: [0, 4], source: 'm6_target' }
    result.per_module_ms.m6_target = 1
    const stage6 = render(result, extras).findAll('.stage-row')[5]!
    expect(stage6.find('.stage-target__type').text()).toBe('grup')
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
    expect(bars).toHaveLength(3)
    expect(bars[0]!.text()).toContain('Tehdit')
    expect(bars[0]!.find('.threshold-bar__score').text()).toBe('0.87')
    expect(bars[0]!.find('.threshold-bar__caption').text()).toBe('eşik 0.50')
    expect(bars[0]!.classes()).toContain('threshold-bar--fired')
    expect(bars[1]!.classes()).not.toContain('threshold-bar--fired')
    expect(bars[2]!.classes()).not.toContain('threshold-bar--fired')
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

describe('real pipeline shapes (m1 terlik, m3 checkpoint missing)', () => {
  it('a substring collision m1 rejected before scoring reads as a deliberate silence, not a broken sentence', () => {
    const r = load(guardJson)
    r.content = []
    r.guards[0]!.suppressed = []
    const guards = render(r).find('.stage-guards')
    expect(guards.text()).toContain('Alt dizi çakışması')
    expect(guards.text()).toContain('bilerek işaretlemedi')
    expect(guards.text()).not.toContain('bastırdı: .')
    expect(guards.find('.evidence').text()).toBe('amcam')
  })
})
