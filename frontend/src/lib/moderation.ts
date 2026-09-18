import type { Action } from '@/contract/types'
import { copy } from '@/copy'

/*
 * How a finished decision reads on the dashboard. The decision layer owns
 * final_action; this only gives it a word and a colour, exactly as
 * categoryMeta does for a content code. Nothing here decides anything: an
 * action the response did not carry becomes "Tamamlanmadı", never "Temiz".
 */

export type ModerationTone = 'clean' | 'warning' | 'review' | 'blocked' | 'incomplete'

export interface ModerationStatus {
  tone: ModerationTone
  label: string
  /** CSS colour variables, so light and dark both follow tokens.css. */
  ink: string
  tint: string
}

const STATUS: Record<ModerationTone, ModerationStatus> = {
  clean: { tone: 'clean', label: copy.moderation.clean, ink: 'var(--cat-clean-ink)', tint: 'var(--cat-clean-bg)' },
  warning: { tone: 'warning', label: copy.moderation.warning, ink: 'var(--warning)', tint: 'var(--warning-subtle)' },
  review: { tone: 'review', label: copy.moderation.review, ink: 'var(--cat-veiled-ink)', tint: 'var(--cat-veiled-bg)' },
  blocked: { tone: 'blocked', label: copy.moderation.blocked, ink: 'var(--cat-direct-ink)', tint: 'var(--cat-direct-bg)' },
  incomplete: { tone: 'incomplete', label: copy.moderation.incomplete, ink: 'var(--text-muted)', tint: 'var(--bg-subtle)' },
}

/**
 * The dashboard word for a final action:
 *   clean            -> Temiz
 *   nudge            -> Uyarı      (the user was warned, the post stayed up)
 *   review, escalate -> İnceleme   (a person has to look at it)
 *   block            -> Engellendi
 *   null             -> Tamamlanmadı (the decision layer produced no verdict)
 */
export function moderationStatus(action: Action | string | null | undefined): ModerationStatus {
  switch (action) {
    case 'clean':
      return STATUS.clean
    case 'nudge':
      return STATUS.warning
    case 'review':
    case 'escalate':
      return STATUS.review
    case 'block':
      return STATUS.blocked
    default:
      return STATUS.incomplete
  }
}

/** The four buckets the status card lists, in order of severity. */
export const STATUS_ORDER: ModerationTone[] = ['clean', 'warning', 'review', 'blocked', 'incomplete']

export function statusMeta(tone: ModerationTone): ModerationStatus {
  return STATUS[tone]
}
