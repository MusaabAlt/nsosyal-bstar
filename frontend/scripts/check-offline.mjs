// Fails if the built frontend references any external host.
// The demo room has no network (design-system.md 9.2): a font, icon, script
// or stylesheet fetched from the internet breaks the screen in front of the jury.
//
//   npm run build && npm run check:offline
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// Default dist/; `node scripts/check-offline.mjs ../backend/web/dist` checks the embedded build.
const dist = process.argv[2]
  ? resolve(process.cwd(), process.argv[2])
  : resolve(dirname(fileURLToPath(import.meta.url)), '../dist')

// Strings that name a URL but are never requested by the browser. Anything
// else, including any real font, script, style or image URL, fails the check.
const ALLOWED = [
  /^https?:\/\/www\.w3\.org\//, // XML namespace identifiers (SVG, XLink)
  /^https:\/\/tailwindcss\.com$/, // Tailwind's licence comment in the CSS
  /^https:\/\/vuejs\.org\/error-reference\//, // text inside Vue's production error messages
]

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) yield* files(path)
    else yield path
  }
}

let problems = 0
let scanned = 0
try {
  statSync(dist)
} catch {
  console.error('dist/ not found: run npm run build first')
  process.exit(1)
}

for (const path of files(dist)) {
  if (!/\.(html|js|css|json|svg|webmanifest)$/.test(path)) continue
  scanned++
  const text = readFileSync(path, 'utf8')
  for (const m of text.matchAll(/(?:https?:)?\/\/[a-z0-9.-]+\.[a-z]{2,}[^\s"'`)<>]*/gi)) {
    const url = m[0].startsWith('//') ? 'https:' + m[0] : m[0]
    if (!/^https?:/i.test(url)) continue
    if (ALLOWED.some((re) => re.test(url))) continue
    problems++
    console.error(`${relative(dist, path)}: external reference ${url}`)
  }
}

if (problems > 0) {
  console.error(`\n${problems} external reference(s) found in ${scanned} files`)
  process.exit(1)
}
console.log(`offline check passed: ${scanned} files, no external hosts`)
