import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
// @ts-expect-error: plain ES module script without type declarations
import { CODES_PY, OUTPUT, parseCodes, render } from '../../scripts/gen-labels.mjs'
import { CONTENT_CODES, contentLabel, familyLabel, formLabel, guardLabel, targetLabel } from './labels'

describe('Turkish labels', () => {
  it('match AI/contracts/codes.py exactly (run node scripts/gen-labels.mjs if this fails)', () => {
    const fresh = render(parseCodes(readFileSync(CODES_PY, 'utf8')))
    expect(readFileSync(OUTPUT, 'utf8')).toBe(fresh)
  })

  it('cover the sixteen content categories', () => {
    expect(CONTENT_CODES).toHaveLength(16)
    expect(contentLabel('B2')).toBe('Tehdit')
    expect(contentLabel('CLEAN')).toBe('Temiz')
    expect(familyLabel('C')).toBe('Örtük saldırganlık')
    expect(formLabel('LEET')).toBe('Rakam/sembol ikamesi')
    expect(guardLabel('SUBSTRING_COLLISION')).toBe('Alt dizi çakışması')
    expect(targetLabel('non_human')).toBe('İnsan dışı')
  })

  it('shows an unknown code as itself instead of hiding it', () => {
    expect(contentLabel('Z9')).toBe('Z9')
  })
})
