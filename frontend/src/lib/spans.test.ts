import { describe, expect, it } from 'vitest'
import { codePointLength, isValidSpan, segment, sliceSpan } from './spans'

describe('spans use code points, like Python', () => {
  it('counts an emoji as one character', () => {
    // Python: len("a😀b") == 3; JavaScript "a😀b".length == 4
    expect(codePointLength('a😀b')).toBe(3)
  })

  it('slices the right characters after an emoji', () => {
    const text = '😀 s4l4k'
    // Python: text[2:7] == "s4l4k"
    expect(sliceSpan(text, [2, 7])).toBe('s4l4k')
    // The naive JavaScript slice is off by one: this is the bug being avoided.
    expect(text.slice(2, 7)).not.toBe('s4l4k')
  })

  it('handles Turkish dotted and dotless i as single characters', () => {
    expect(sliceSpan('İstanbul ığdır', [9, 14])).toBe('ığdır')
  })

  it('highlights exactly the span, with emoji before it', () => {
    const parts = segment('🙂🙂 amcam geldi', [{ span: [3, 8], kind: 'highlight' }])
    expect(parts).toEqual([
      { text: '🙂🙂 ', highlight: false, underline: false },
      { text: 'amcam', highlight: true, underline: false },
      { text: ' geldi', highlight: false, underline: false },
    ])
  })

  it('combines overlapping highlight and underline', () => {
    const parts = segment('amcam', [
      { span: [0, 5], kind: 'highlight' },
      { span: [0, 2], kind: 'underline' },
    ])
    expect(parts).toEqual([
      { text: 'am', highlight: true, underline: true },
      { text: 'cam', highlight: true, underline: false },
    ])
  })

  it('ignores spans outside the text instead of guessing', () => {
    expect(isValidSpan([3, 9], 5)).toBe(false)
    expect(isValidSpan([2, 2], 5)).toBe(false)
    expect(isValidSpan([-1, 2], 5)).toBe(false)
    expect(isValidSpan(null, 5)).toBe(false)
    expect(segment('abc', [{ span: [1, 99], kind: 'highlight' }])).toEqual([
      { text: 'abc', highlight: false, underline: false },
    ])
  })
})
