// Generates src/contract/labels.generated.json from AI/contracts/codes.py.
//
// The API sends codes, not Turkish text. The labels live only in codes.py,
// so the UI copies them from there instead of retyping them. A unit test
// (src/contract/labels.test.ts) fails when this file is out of date.
//
//   node scripts/gen-labels.mjs          write the file
//   node scripts/gen-labels.mjs --check  exit 1 if the file is stale
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
export const CODES_PY = resolve(here, '../../AI/contracts/codes.py')
export const OUTPUT = resolve(here, '../src/contract/labels.generated.json')

const ENUMS = ['ContentCode', 'FormCode', 'GuardCode', 'TargetType', 'Action', 'Family', 'ModuleName']

export function parseCodes(source) {
  const values = {}
  for (const name of ENUMS) {
    const body = source.match(new RegExp(`class ${name}\\(str, Enum\\):([\\s\\S]*?)(?=\\n\\S)`))
    if (!body) throw new Error(`enum ${name} not found in codes.py`)
    values[name] = {}
    for (const m of body[1].matchAll(/^\s+([A-Z0-9_]+)\s*=\s*"([^"]+)"/gm)) {
      values[name][m[1]] = m[2]
    }
    if (Object.keys(values[name]).length === 0) throw new Error(`enum ${name} has no members`)
  }

  const labels = {}
  // Anchor on the assignment: the name also appears in docstrings above it.
  const block = source.match(/^TR_LABELS\b[^=\n]*=\s*EnumLabels\(\[([\s\S]*?)\n\]\)/m)
  if (!block) throw new Error('TR_LABELS not found in codes.py')
  for (const m of block[1].matchAll(/\((\w+)\.(\w+),\s*"([^"]*)"\)/g)) {
    const [, enumName, member, label] = m
    const value = values[enumName]?.[member]
    if (value === undefined) throw new Error(`TR_LABELS references unknown ${enumName}.${member}`)
    labels[enumName] ??= {}
    labels[enumName][value] = label
  }
  // codes.py requires a label for every member; hold the copy to the same rule.
  for (const name of ENUMS.filter((n) => n !== 'ModuleName')) {
    for (const value of Object.values(values[name])) {
      if (labels[name]?.[value] === undefined) throw new Error(`no Turkish label for ${name}.${value}`)
    }
  }
  return { source: 'AI/contracts/codes.py', enums: values, labels }
}

export function render(parsed) {
  return JSON.stringify(parsed, null, 2) + '\n'
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const fresh = render(parseCodes(readFileSync(CODES_PY, 'utf8')))
  if (process.argv.includes('--check')) {
    let current = ''
    try {
      current = readFileSync(OUTPUT, 'utf8')
    } catch {
      /* missing counts as stale */
    }
    if (current !== fresh) {
      console.error('labels.generated.json is out of date: run node scripts/gen-labels.mjs')
      process.exit(1)
    }
    console.log('labels up to date')
  } else {
    writeFileSync(OUTPUT, fresh)
    console.log('wrote', OUTPUT)
  }
}
