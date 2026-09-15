import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

/*
 * design-system.md section 7 lists prohibitions that are build failures, not
 * style disagreements. This test enforces the ones that can be checked in
 * source, plus the hard rule that the UI never compares a score with a
 * threshold (AMIN_BRIEF 6).
 */

const SRC = join(__dirname)

function* walk(dir: string): Generator<string> {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) yield* walk(path)
    else yield path
  }
}

const sources = [...walk(SRC)]
  .filter((p) => /\.(vue|ts|css)$/.test(p) && !/\.test\.ts$/.test(p))
  .map((p) => ({ path: relative(SRC, p).replaceAll('\\', '/'), text: readFileSync(p, 'utf8') }))

/** Strip comments so documentation that names a prohibited thing does not trip the check. */
function code(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '').replace(/(^|[^:])\/\/.*$/gm, '$1')
}

function offenders(pattern: RegExp, filter: (path: string) => boolean = () => true): string[] {
  return sources.filter((s) => filter(s.path) && pattern.test(code(s.text))).map((s) => s.path)
}

describe('design-system prohibitions', () => {
  it('no raw hex colours inside components (12): tokens.css and the Vuetify theme mirror only', () => {
    expect(offenders(/#[0-9a-fA-F]{3,8}\b/, (p) => p.endsWith('.vue'))).toEqual([])
  })

  it('no box-shadow anywhere (5)', () => {
    expect(offenders(/box-shadow\s*:(?!\s*none\s*[;}])/)).toEqual([])
  })

  it('no gradient outside the progress token (4)', () => {
    expect(offenders(/gradient\(/, (p) => p !== 'styles/tokens.css')).toEqual([])
  })

  it('no uppercase labels (1)', () => {
    expect(offenders(/text-transform\s*:\s*uppercase|\buppercase\b/)).toEqual([])
  })

  it('no monospace outside evidence text (3)', () => {
    expect(
      offenders(/font-family-mono|monospace|\bfont-mono\b/, (p) => !['components/ui/EvidenceText.vue', 'styles/tokens.css', 'styles/main.css'].includes(p)),
    ).toEqual([])
  })

  it('no emoji in the interface (10)', () => {
    expect(offenders(/\p{Extended_Pictographic}/u, (p) => p.endsWith('.vue') || p === 'copy.ts')).toEqual([])
  })

  it('no remote resources (9.2)', () => {
    expect(offenders(/https?:\/\/(?!www\.w3\.org)/, (p) => !p.startsWith('api/mocks/'))).toEqual([])
  })

  it('no radius other than the two tokens (2.4)', () => {
    const bad = sources
      .filter((s) => s.path.endsWith('.vue'))
      .flatMap((s) =>
        [...code(s.text).matchAll(/border-radius\s*:\s*([^;]+);/g)]
          .map((m) => m[1]!.trim())
          .filter((v) => !['var(--radius-control)', '0', '50%'].includes(v))
          .map((v) => `${s.path}: ${v}`),
      )
    // 50% is allowed only for the round avatar and the 6px status dot, which the documents specify as round.
    expect(bad).toEqual([])
  })
})

describe('the UI makes no decisions', () => {
  it('never compares a score with a threshold', () => {
    const comparison = /(score|confidence)[\w.?!\]]*\s*[<>]=?\s*[\w.?!]*threshold|threshold[\w.?!\]]*\s*[<>]=?\s*[\w.?!]*(score|confidence)/i
    expect(offenders(comparison)).toEqual([])
  })

  it('never assigns decision-owned fields', () => {
    const assignment = /\.(fired|active|suppressed|verdict)\s*=(?!=)/
    expect(offenders(assignment, (p) => p !== 'api/mockSource.ts')).toEqual([])
  })

  it('never averages or sums scores', () => {
    expect(offenders(/\.reduce\(|Math\.(max|min)\([^)]*score|average|mean\(/i, (p) => !p.startsWith('components/ui/ThresholdBar'))).toEqual([])
  })
})
