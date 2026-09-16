import type { AnalysisSource } from './source'
import { httpSource } from './httpSource'

/**
 * Every screen reads the Go API. The sample payloads in src/api/mocks remain
 * as test fixtures only.
 */
export const analysisSource: AnalysisSource = httpSource

export type { AnalysisSource, AnalyzeOutcome, AnalyzeError, Extras, Display, Normalization, Preset } from './source'
