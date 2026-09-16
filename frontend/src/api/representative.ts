import { ref } from 'vue'

/**
 * True while sample data is on screen (design-system 4.19: the Temsili veri
 * marker). Set by the sample source, and by the Go API from the model
 * service's own "representative" flag, so the marker disappears by itself
 * the moment the real model replaces the mock.
 */
export const representative = ref(false)

export function setRepresentative(value: unknown) {
  representative.value = value === true
}
