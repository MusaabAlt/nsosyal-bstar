/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "mock" (default) renders the sample payloads with the Temsili veri marker. */
  readonly VITE_DATA_SOURCE?: 'mock' | 'api'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}
