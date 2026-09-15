import type { Span } from '@/contract/types'

/*
 * Spans in the contract are [start, end) offsets in Python string indices,
 * which count Unicode code points. JavaScript string indices count UTF-16
 * code units, so text.slice(start, end) highlights the wrong characters as
 * soon as the text contains an emoji or any other character outside the
 * Basic Multilingual Plane (AMIN_BRIEF 1.2). Everything here works on
 * Array.from(text), which splits by code point.
 */

export function codePoints(text: string): string[] {
  return Array.from(text)
}

/** Number of code points: the length Python reports for the same string. */
export function codePointLength(text: string): number {
  return codePoints(text).length
}

/** A span is usable only if it lies inside the text; anything else is ignored, never guessed. */
export function isValidSpan(span: Span | null | undefined, length: number): span is Span {
  return (
    Array.isArray(span) &&
    span.length === 2 &&
    Number.isInteger(span[0]) &&
    Number.isInteger(span[1]) &&
    span[0] >= 0 &&
    span[0] < span[1] &&
    span[1] <= length
  )
}

export function sliceSpan(text: string, span: Span): string {
  return codePoints(text).slice(span[0], span[1]).join('')
}

export type MarkKind = 'highlight' | 'underline'

export interface Mark {
  span: Span
  kind: MarkKind
}

export interface Segment {
  text: string
  highlight: boolean
  underline: boolean
}

/**
 * Splits text into runs that share the same marks, so a renderer can wrap
 * each run once. Overlapping marks combine; invalid spans are skipped.
 */
export function segment(text: string, marks: Mark[]): Segment[] {
  const chars = codePoints(text)
  const highlight = new Array<boolean>(chars.length).fill(false)
  const underline = new Array<boolean>(chars.length).fill(false)
  for (const mark of marks) {
    if (!isValidSpan(mark.span, chars.length)) continue
    const target = mark.kind === 'highlight' ? highlight : underline
    for (let i = mark.span[0]; i < mark.span[1]; i++) target[i] = true
  }

  const out: Segment[] = []
  for (let i = 0; i < chars.length; i++) {
    const last = out[out.length - 1]
    if (last && last.highlight === highlight[i] && last.underline === underline[i]) {
      last.text += chars[i]
    } else {
      out.push({ text: chars[i] ?? '', highlight: highlight[i] ?? false, underline: underline[i] ?? false })
    }
  }
  return out
}
