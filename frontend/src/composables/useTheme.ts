import { ref } from 'vue'

/* Dark is the default; the choice is remembered per browser (index.html applies it before the first paint). */
const KEY = 'nsosyal.theme'

function readDark(): boolean {
  try {
    return localStorage.getItem(KEY) !== 'light'
  } catch {
    return true
  }
}

const dark = ref(typeof document === 'undefined' ? true : !document.documentElement.classList.contains('light') && readDark())

export function useTheme() {
  function setDark(value: boolean) {
    dark.value = value
    document.documentElement.classList.toggle('light', !value)
    try {
      localStorage.setItem(KEY, value ? 'dark' : 'light')
    } catch {
      /* storage blocked: the choice lasts for this page only */
    }
  }
  return { dark, setDark, toggle: () => setDark(!dark.value) }
}
