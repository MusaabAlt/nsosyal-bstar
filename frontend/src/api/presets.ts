import type { Preset } from './source'
import flagged from './mocks/flagged.json'
import guard from './mocks/guard.json'
import clean from './mocks/clean.json'

/*
 * Preset demo strings (pages-spec 2.1): at least one per demo moment. Labels
 * say what the preset demonstrates. The obfuscated, guard and clean texts
 * are the sample payload texts, which the mock services recognise; the
 * Kalıp yargı text is the example quoted in docs/PROJE_ACIKLAMASI.md.
 */
export const presets: Preset[] = [
  { label: 'Gizlenmiş hakaret', text: flagged.text },
  { label: 'Zararsız benzerlik', text: guard.text },
  { label: 'Kalıp yargı', text: 'Senin gibilerin oyu yüzünden bu haldeyiz' },
  { label: 'Temiz cümle', text: clean.text },
]
