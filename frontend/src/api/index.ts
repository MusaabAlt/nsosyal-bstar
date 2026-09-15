import type { AnalysisSource } from './source'
import { httpSource } from './httpSource'
import { mockSource } from './mockSource'

/**
 * The one place that decides where results come from. The Go API is the
 * default; `npm run dev:mock` (VITE_DATA_SOURCE=mock) renders the sample
 * payloads with the Temsili veri marker instead.
 */
export const analysisSource: AnalysisSource = import.meta.env.VITE_DATA_SOURCE === 'mock' ? mockSource : httpSource

export type { AnalysisSource, AnalyzeOutcome, AnalyzeError, Preset } from './source'
