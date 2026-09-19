import { describe, expect, it } from 'vitest'
import type { AnalysisResult } from '@/contract/types'
import degradedJson from '@/api/mocks/degraded.json'
import cleanJson from '@/api/mocks/clean.json'
import flaggedJson from '@/api/mocks/flagged.json'
import guardJson from '@/api/mocks/guard.json'
import { buildStages, consequenceView, isDecisionFailure, moduleState, verdictView, type Stage } from './model'

const load = (json: unknown) => JSON.parse(JSON.stringify(json)) as AnalysisResult
const stage = <K extends Stage['kind']>(stages: Stage[], kind: K) =>
  // Intersection, not Extract: PatternStage's kind is the union 'charsafe' | 'obfuscation'.
  stages.find((s) => s.kind === kind) as Stage & { kind: K }

describe('verdict', () => {
  it('degraded is the incomplete block, never green, and names every module that did not run', () => {
    const r = load(degradedJson)
    const v = verdictView(r)
    expect(v.tone).toBe('incomplete')
    expect(v.word).toBe('Değerlendirme tamamlanmadı')
    expect(v.word).not.toBe('Temiz')
    // m5_sarcasm is the one module still a stub; one is enough to block a clean verdict.
    expect(v.notRun.map((d) => d.module)).toEqual(['m5_sarcasm'])
    expect(v.explanation).toBe(r.explanation) // verbatim
  })

  it('a clean verdict is Temiz only when nothing is degraded', () => {
    expect(verdictView(load(cleanJson))).toMatchObject({ word: 'Temiz', tone: 'clean' })

    const cleanButDegraded = load(cleanJson)
    cleanButDegraded.signals.pipeline!.degraded = [{ module: 'm3_encoder', kinds: ['stub'], reasons: [] }]
    expect(verdictView(cleanButDegraded).tone).toBe('incomplete')
  })

  it('fails closed when the response does not say which modules ran', () => {
    const r = load(cleanJson)
    delete r.signals.pipeline
    const v = verdictView(r)
    expect(v.tone).toBe('incomplete')
    expect(v.moduleStatusKnown).toBe(false)
  })

  it('maps actions to the design-system words', () => {
    const r = load(cleanJson)
    const word = (verdict: AnalysisResult['verdict']) => verdictView({ ...r, verdict }).word
    expect(word('block')).toBe('Engelle')
    expect(word('escalate')).toBe('İncele')
    expect(word('review')).toBe('İncele')
    expect(word('nudge')).toBe('Hassas içerik')
    expect(word('clean')).toBe('Temiz')
  })

  it('verdict null is a decision failure, never a pass', () => {
    const r = { ...load(cleanJson), verdict: null }
    expect(isDecisionFailure(r)).toBe(true)
    expect(verdictView(r).tone).not.toBe('clean')
  })
})

describe('stages read decisions, they do not make them', () => {
  // The sample the real pipeline produces today for a clean sentence: every
  // module runs except m5, so the stages report findings instead of absence.
  it('degraded: the modules that ran say they found nothing; only m5 is unavailable', () => {
    const stages = buildStages(load(degradedJson))
    expect(stages).toHaveLength(9)
    expect(stages.map((s) => s.number)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9])
    expect(stage(stages, 'charsafe')).toMatchObject({ status: 'passed', line: 'Şüpheli karakter bulunamadı' })
    expect(stage(stages, 'obfuscation')).toMatchObject({ status: 'passed', line: 'Gizleme kalıbı bulunamadı' })
    expect(stage(stages, 'normalization').status).toBe('passed')
    // m3 scored the text below its threshold, so the offensive row is present but below.
    expect(stage(stages, 'content').status).toBe('below')
    // m6 ran and resolved no target: no data to show, not an unavailable module.
    expect(stage(stages, 'target')).toMatchObject({ status: 'noData', target: null })
    expect(stage(stages, 'guards')).toMatchObject({ status: 'passed', active: [] })
    expect(stage(stages, 'thread')).toMatchObject({ status: 'notApplied' })
    expect(stage(stages, 'reason').status).toBeNull()
    // The verdict is still incomplete: m5 did not run (fail closed).
    expect(verdictView(load(degradedJson)).tone).toBe('incomplete')
  })

  it('every stage that has no findings still says something (4.8)', () => {
    for (const json of [degradedJson, cleanJson, flaggedJson, guardJson]) {
      for (const s of buildStages(load(json))) {
        const hasContent =
          s.line !== null ||
          s.kind === 'input' ||
          s.kind === 'reason' ||
          ('patterns' in s && s.patterns.length > 0) ||
          ('rows' in s && s.rows.length > 0) ||
          ('active' in s && s.active.length > 0) ||
          ('scorePair' in s && s.scorePair !== null) ||
          ('target' in s && s.target !== null) ||
          ('thread' in s && s.thread !== null)
        expect(hasContent, `stage ${s.number} (${s.kind}) renders nothing`).toBe(true)
      }
    }
  })

  it('flagged: the obfuscation pattern is active, B2 fired first, score pair from the payload', () => {
    const stages = buildStages(load(flaggedJson))
    const obfuscation = stage(stages, 'obfuscation')
    expect(obfuscation.status).toBe('triggered')
    expect(obfuscation.patterns).toMatchObject([{ code: 'LEET', evidence: '1', active: true }])

    const content = stage(stages, 'content')
    expect(content.status).toBe('triggered')
    // Fired first, then by score; the BERTurk offensive score (raw channel) has its own row.
    expect(content.rows.map((r) => [r.key, r.label, r.score, r.threshold, r.fired])).toEqual([
      ['B2', 'Tehdit', 0.87, 0.5, true],
      ['binary_offensive', 'Genel saldırganlık', 0.44, 0.5, false],
      ['C4', 'Kışkırtma', 0.12, 0.5, false],
    ])

    expect(stage(stages, 'normalization')).toMatchObject({
      status: 'triggered',
      scorePair: { raw: { score: 0.44, fired: false }, normalized: { score: 0.81, fired: true } },
    })
    // m6 resolves "Seni" as an individual, so Hedef triggers too.
    expect(stage(stages, 'target')).toMatchObject({ status: 'triggered', target: { type: 'individual', evidence: 'Seni' } })
    expect(stage(stages, 'reason').triggeredStages).toEqual([
      'Gizleme tespiti', 'Normalleştirme', 'İçerik sınıflandırma', 'Hedef',
    ])
  })

  it('follows fired from the payload even when it disagrees with the numbers', () => {
    // A score above its threshold that the decision layer did NOT fire must
    // render as not fired: the UI never compares score and threshold.
    const r = load(flaggedJson)
    r.content[1] = { ...r.content[1]!, score: 0.9, threshold: 0.1, fired: false }
    const content = stage(buildStages(r), 'content')
    const c4 = content.rows.find((row) => row.key === 'C4')!
    expect(c4.fired).toBe(false)
    expect(content.rows[0]!.key).toBe('B2') // fired first, regardless of score
  })

  it('guard: the suppression is shown as deliberate, with the suppressed entry for the underline', () => {
    const stages = buildStages(load(guardJson))
    const guards = stage(stages, 'guards')
    expect(guards.status).toBe('triggered')
    expect(guards.active).toHaveLength(1)
    expect(guards.active[0]!.guard).toMatchObject({ code: 'SUBSTRING_COLLISION', evidence: 'amcam', span: [0, 5] })
    expect(guards.active[0]!.suppressedEntries.map((e) => [e.code, e.span])).toEqual([['A1', [0, 2]]])

    const content = stage(stages, 'content')
    expect(content.rows[0]!.suppressedBy?.code).toBe('SUBSTRING_COLLISION')
    expect(content.status).toBe('below')
  })

  it('absent optional sections render as "veri yok", never as zero', () => {
    const r = load(cleanJson)
    r.per_module_ms = {}
    const stages = buildStages(r)
    expect(stage(stages, 'charsafe').status).toBe('noData')
    expect(stage(stages, 'charsafe').durationMs).toBeNull()
  })
})

describe('modules and consequence', () => {
  it('reads module state from the degraded list and per_module_ms', () => {
    const r = load(degradedJson)
    expect(moduleState(r, 'm0_charsafe')).toBe('ran')
    expect(moduleState(r, 'm3_encoder')).toBe('ran')
    expect(moduleState(r, 'm4_implicit')).toBe('ran')
    expect(moduleState(r, 'm5_sarcasm')).toBe('stub')
    r.signals.pipeline!.degraded![0]!.kinds = ['failed']
    expect(moduleState(r, 'm5_sarcasm')).toBe('failed')
  })

  it('never implies a degraded post was cleared', () => {
    expect(consequenceView(load(degradedJson))).toEqual({ mode: 'normal', incomplete: true })
    expect(consequenceView(load(cleanJson))).toEqual({ mode: 'normal', incomplete: false })
    expect(consequenceView(load(flaggedJson))).toEqual({ mode: 'queued', incomplete: false })
    expect(consequenceView({ ...load(cleanJson), verdict: 'block' }).mode).toBe('withheld')
    expect(consequenceView({ ...load(cleanJson), verdict: 'nudge' }).mode).toBe('sensitive')
  })
})

describe('binary offensive score (m3 BERTurk)', () => {
  it('is its own row on the raw channel, with the server margin, when m3 scored the text', () => {
    const r = load(guardJson)
    r.signals.decision!.binary_offensive = {
      threshold: 0.320188, branch: 'scalar', signal: null, signal_value: null,
      channels: { raw: { score: 0.91, fired: true } }, fired: true, action: 'review',
    }
    const extras = { display: { categories_total: 2, categories_evaluated: 2, categories_hidden: 0, patterns_checked_other: null, content_margins: [0.22], binary_offensive_margin: 0.589812, normalization: null }, normalization: null, commentId: null }
    const content = stage(buildStages(r, extras), 'content')
    const row = content.rows.find((x) => x.key === 'binary_offensive')!
    expect(row).toMatchObject({ label: 'Genel saldırganlık', score: 0.91, threshold: 0.320188, fired: true, margin: 0.589812 })
    expect(content.rows[0]!.key).toBe('binary_offensive') // fired first
    expect(content.status).toBe('triggered')
    expect(verdictView(r, extras).evaluated).toEqual({ total: 2, n: 2 })
  })

  it('has no row when m3 did not score (checkpoint missing: score null)', () => {
    const r = load(degradedJson)
    r.signals.decision!.binary_offensive = {
      threshold: 0.320188, branch: 'scalar', signal: null, signal_value: null,
      channels: { raw: { score: null, fired: null } }, fired: null, action: null,
    }
    expect(stage(buildStages(r), 'content').rows).toEqual([])
  })
})
