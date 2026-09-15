import type { Preset } from './source'
import flagged from './mocks/flagged.json'
import guard from './mocks/guard.json'
import clean from './mocks/clean.json'

/*
 * Preset demo strings (pages-spec 2.1). The final demo strings are [OPEN];
 * until they are chosen, the presets are the texts of the sample payloads,
 * which both the frontend mock and the Go mock inference service recognise.
 */
export const presets: Preset[] = [
  { label: 'Gizlenmiş hakaret', text: flagged.text }, // pages-spec 2.1 label
  { label: 'Zararsız benzerlik', text: guard.text }, // pages-spec 2.1 label
  { label: 'Temiz cümle', text: clean.text }, // ours: the spec requires a clean preset but names none
]
