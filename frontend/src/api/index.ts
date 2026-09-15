import type { AnalysisSource } from './source'
import { httpSource } from './httpSource'
import { mockSource } from './mockSource'

/**
 * The one place that decides where data comes from. The Go API is the
 * default; `npm run dev:mock` (VITE_DATA_SOURCE=mock) uses the sample
 * payloads instead.
 */
export const dataMode: 'api' | 'mock' = import.meta.env.VITE_DATA_SOURCE === 'mock' ? 'mock' : 'api'

export const analysisSource: AnalysisSource = dataMode === 'mock' ? mockSource : httpSource

export type { AnalysisSource, AnalyzeOutcome, AnalyzeError, Extras, Display, Normalization, Preset } from './source'
