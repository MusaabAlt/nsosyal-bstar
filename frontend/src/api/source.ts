import type { AnalysisResult } from '@/contract/types'

export type AnalyzeErrorKind = 'network' | 'http'

export interface AnalyzeError {
  kind: AnalyzeErrorKind
  /** HTTP status for kind "http". */
  status?: number
  /** The backend's error code, e.g. "queue_full" (backend internal/http/respond). */
  code?: string
  /** The server's own error text, for logs only; the screen shows copy.errors. */
  detail?: string
}

export type AnalyzeOutcome = { ok: true; result: AnalysisResult } | { ok: false; error: AnalyzeError }

export interface Preset {
  /** What the preset demonstrates, not its content (pages-spec 2.1). */
  label: string
  text: string
}

/**
 * Where analysis results come from. The screen depends only on this
 * interface, so switching from the sample payloads to the Go API changes
 * one line in src/api/index.ts.
 */
export interface AnalysisSource {
  /** true while sample data is rendered: shows the Temsili veri marker (4.19). */
  readonly representative: boolean
  readonly presets: Preset[]
  analyze(text: string, signal?: AbortSignal): Promise<AnalyzeOutcome>
}
