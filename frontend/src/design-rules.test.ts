import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

/*
 * Rules that can be checked in source. The look follows the ATI-SOSYAL
 * Paneli design (tokens in styles/tokens.css); the hard rules are that the
 * panel works offline and never makes a decision the model owns.
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

describe('design tokens', () => {
  it('no raw hex colours inside components: colours come from tokens.css', () => {
    expect(offenders(/#[0-9a-fA-F]{3,8}\b/, (p) => p.endsWith('.vue'))).toEqual([])
  })

  it('no emoji in the interface', () => {
    expect(offenders(/\p{Extended_Pictographic}/u, (p) => p.endsWith('.vue') || p === 'copy.ts')).toEqual([])
  })

  it('no remote resources: the demo room is offline', () => {
    expect(offenders(/https?:\/\/(?!www\.w3\.org)/, (p) => !p.startsWith('api/mocks/'))).toEqual([])
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
    expect(offenders(/\.reduce\(|Math\.(max|min)\([^)]*score|average|mean\(/i)).toEqual([])
  })
})
