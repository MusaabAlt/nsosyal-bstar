// vite --emptyOutDir removes backend/web/dist/.keep; put it back so the Go
// embed pattern (all:dist) always has a file to match, even after a clean.
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const target = resolve(dirname(fileURLToPath(import.meta.url)), '../../backend/web/dist/.keep')
writeFileSync(target, '')
console.log('kept', target)
