import type { AnalysisResult } from '@/contract/types'
import { CONTENT_CODES, FAMILIES, contentLabel, familyLabel, familyOf } from '@/contract/labels'
import { copy } from '@/copy'
import type { IconName } from '@/components/icons'

/*
 * How a category looks on the panel. The colour follows the family, so a
 * category keeps its colour on every screen: A red, B pink, C orange, D blue,
 * and the model's general offensive score purple.
 */

export const BINARY_OFFENSIVE = 'binary_offensive'

/**
 * The content-code families the moderation classes are drawn from, in code
 * order. CLEAN is not a moderation class: it is the absence of one.
 */
export const CONTENT_FAMILIES = FAMILIES.filter((f) => f !== 'CLEAN')

/** Every content code the contract puts in this family, in code order. */
export function codesOfFamily(family: string): string[] {
  return CONTENT_CODES.filter((code) => code !== 'CLEAN' && familyOf(code) === family)
}

export type Tone = 'direct' | 'bully' | 'veiled' | 'sarcasm' | 'obf' | 'clean'

const TONE_BY_FAMILY: Record<string, Tone> = { A: 'direct', B: 'bully', C: 'veiled', D: 'sarcasm' }
const ICON_BY_FAMILY: Record<string, IconName> = { A: 'alertDiamond', B: 'userBlock', C: 'viewOff', D: 'sad' }

export interface CategoryMeta {
  code: string
  label: string
  family: string
  tone: Tone
  icon: IconName
  /** CSS colour variables for this category. */
  color: string
  ink: string
  tint: string
}

function familyOfCode(code: string): string {
  return code === BINARY_OFFENSIVE ? '' : code === 'CLEAN' ? 'CLEAN' : code.slice(0, 1)
}

export function categoryMeta(code: string): CategoryMeta {
  const family = familyOfCode(code)
  const tone: Tone = code === BINARY_OFFENSIVE ? 'obf' : (TONE_BY_FAMILY[family] ?? 'clean')
  return {
    code,
    label: code === BINARY_OFFENSIVE ? copy.stages.binaryOffensive : contentLabel(code),
    family: family === '' ? copy.panel.generalFamily : familyLabel(family),
    tone,
    icon: code === BINARY_OFFENSIVE ? 'brain' : (ICON_BY_FAMILY[family] ?? 'check'),
    color: `var(--cat-${tone})`,
    ink: `var(--cat-${tone}-ink)`,
    tint: `var(--cat-${tone}-bg)`,
  }
}

export interface FamilyMeta {
  family: string
  label: string
  tone: Tone
  icon: IconName
  color: string
  ink: string
  tint: string
}

/** How a whole moderation class looks: the family's colour, icon and Turkish name. */
export function familyMeta(family: string): FamilyMeta {
  const tone: Tone = TONE_BY_FAMILY[family] ?? 'clean'
  return {
    family,
    label: familyLabel(family),
    tone,
    icon: ICON_BY_FAMILY[family] ?? 'check',
    color: `var(--cat-${tone})`,
    ink: `var(--cat-${tone}-ink)`,
    tint: `var(--cat-${tone}-bg)`,
  }
}

export interface FiredCategory {
  code: string
  score: number
  threshold: number | null
}

/**
 * The categories the decision layer fired for a result, content codes first
 * (by score, highest first), then the general offensive score. Only reads
 * `fired`; never compares a score with a threshold.
 */
export function firedCategories(result: AnalysisResult | null | undefined): FiredCategory[] {
  if (!result) return []
  const content = (result.content ?? [])
    .filter((c) => c.fired === true)
    .map((c) => ({ code: c.code as string, score: c.score, threshold: c.threshold }))
    .sort((a, b) => b.score - a.score)
  const bo = result.signals?.decision?.binary_offensive
  if (bo?.fired === true) {
    const reading = [bo.channels?.raw, bo.channels?.normalized].find((c) => c?.fired === true && typeof c.score === 'number')
    if (reading && typeof reading.score === 'number') {
      content.push({ code: BINARY_OFFENSIVE, score: reading.score, threshold: bo.threshold })
    }
  }
  return content
}
