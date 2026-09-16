import type { AnalysisResult, Span } from '@/contract/types'

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

/**
 * Numbers docs/UI shows that the AnalysisResult does not carry. The Go
 * backend computes them (backend/internal/display) so the screen computes
 * nothing (design-system 6).
 */
export interface Display {
  /** Categories the AI detects today (AI/serving/capabilities.py); null when not reported. */
  categories_total: number | null
  categories_evaluated: number | null
  categories_hidden: number | null
  /** null when m2 did not run: no pattern was checked. */
  patterns_checked_other: number | null
  /** Same order as result.content; null where the threshold is null. */
  content_margins: Array<number | null>
  /** Score minus threshold of signals.decision.binary_offensive; null without both. */
  binary_offensive_margin: number | null
  normalization: { removed: number; replaced: number } | null
}

/** m2's optional de-obfuscated text, beside the frozen result (backend/docs/inference-contract.md). */
export interface Normalization {
  text: string
  changes: Array<{
    code: string
    /** In the original text, code points. */
    from_span: Span
    /** In normalization.text, code points; null when characters were removed. */
    to_span: Span | null
    from: string
    to: string
  }>
}

/** Everything the server sends beside the result. Missing pieces render as unavailable. */
export interface Extras {
  display: Display | null
  normalization: Normalization | null
  /** The stored comment's id, for moderator actions; null when the source has none. */
  commentId: string | null
}

export const NO_EXTRAS: Extras = { display: null, normalization: null, commentId: null }

export type AnalyzeOutcome = { ok: true; result: AnalysisResult; extras: Extras } | { ok: false; error: AnalyzeError }

export interface Preset {
  /** What the preset demonstrates, not its content (pages-spec 2.1). */
  label: string
  text: string
}

/**
 * Where analysis results come from. The screen depends only on this
 * interface; src/api/index.ts picks the implementation.
 */
export interface AnalysisSource {
  readonly presets: Preset[]
  analyze(text: string, signal?: AbortSignal): Promise<AnalyzeOutcome>
}
