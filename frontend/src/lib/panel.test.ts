import { describe, expect, it } from 'vitest'
import type { AnalysisResult } from '@/contract/types'
import flaggedJson from '@/api/mocks/flagged.json'
import degradedJson from '@/api/mocks/degraded.json'
import { segmentByKey } from './spans'
import { BINARY_OFFENSIVE, categoryMeta, firedCategories } from './categories'
import { formatChange, formatCount, formatPercent } from './format'
import { accusative, percentSuffix } from '@/copy'

const load = (json: unknown) => JSON.parse(JSON.stringify(json)) as AnalysisResult

describe('segmentByKey', () => {
  it('colours runs by the first mark and counts code points, not UTF-16 units', () => {
    const segs = segmentByKey('a😀 salak b', [
      { span: [3, 8], key: 'A1' },
      { span: [4, 6], key: 'B1' },
      { span: [20, 30], key: 'X' }, // out of range: skipped
    ])
    expect(segs).toEqual([
      { text: 'a😀 ', key: null },
      { text: 'salak', key: 'A1' },
      { text: ' b', key: null },
    ])
  })
})

describe('firedCategories', () => {
  it('lists fired content codes first, then the offensive score, reading fired only', () => {
    const fired = firedCategories(load(flaggedJson))
    expect(fired.map((f) => f.code)).toEqual(['B2', BINARY_OFFENSIVE])
    // The offensive score shown is the channel that fired (normalized), not the raw one.
    expect(fired[1]!.score).toBe(0.81)
  })

  it('is empty when nothing fired', () => {
    expect(firedCategories(load(degradedJson))).toEqual([])
    expect(firedCategories(null)).toEqual([])
  })

  it('gives every family its own colour and the offensive score its own label', () => {
    expect(categoryMeta('A1').tone).toBe('direct')
    expect(categoryMeta('B2').tone).toBe('bully')
    expect(categoryMeta(BINARY_OFFENSIVE)).toMatchObject({ tone: 'obf', label: 'Genel saldırganlık' })
  })
})

describe('formatting', () => {
  it('never turns a missing number into zero', () => {
    expect(formatCount(null)).toBeNull()
    expect(formatPercent(undefined)).toBeNull()
    expect(formatChange(null)).toBeNull()
  })

  it('uses Turkish grouping and signs', () => {
    expect(formatCount(12480)).toBe('12.480')
    expect(formatPercent(9)).toBe('%9,0')
    expect(formatChange(12)).toBe('+%12,0')
    expect(formatChange(-5)).toBe('−%5,0')
  })
})

describe('Turkish suffixes', () => {
  it('reads a number the way it is spoken', () => {
    // "2 kategoriden 1'i", "... 4'ü", "... 6'sı", "10'u", "0'ı".
    expect(accusative(1)).toBe("'i")
    expect(accusative(4)).toBe("'ü")
    expect(accusative(6)).toBe("'sı")
    expect(accusative(10)).toBe("'u")
    expect(accusative(0)).toBe("'ı")
  })

  it('suffixes a percent from its decimal digit, not with a fixed i', () => {
    // A percent is spoken ending in its decimal: "%100,0" is "yüzde yüz virgül
    // sıfır", so it takes 'ı. A hardcoded "'i" was wrong for seven digits.
    expect(percentSuffix(formatPercent(100)!)).toBe("'ı")
    expect(percentSuffix(formatPercent(12.5)!)).toBe("'i")
    expect(percentSuffix(formatPercent(33.4)!)).toBe("'ü")
    expect(percentSuffix(formatPercent(0)!)).toBe("'ı")
  })

  it('leaves a percent it cannot read alone rather than guessing', () => {
    expect(percentSuffix('%—')).toBe("'i")
  })
})
