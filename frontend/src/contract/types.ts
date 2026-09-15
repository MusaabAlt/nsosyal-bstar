/*
 * The AnalysisResult contract as the API sends it (AI/contracts/schema.py,
 * AnalysisResult.to_dict()). Enums arrive as their string value; spans as
 * [start, end) code-point offsets into the ORIGINAL text.
 *
 * The UI only reads these fields. It never derives verdict, fired, active or
 * suppressed, and never compares a score with a threshold (AMIN_BRIEF 6).
 */

export type ContentCode =
  | 'A1' | 'A2' | 'A3' | 'A4'
  | 'B1' | 'B2' | 'B3' | 'B4' | 'B5'
  | 'C1' | 'C2' | 'C3' | 'C4' | 'C5'
  | 'D1' | 'CLEAN'

export type FormCode =
  | 'LEET' | 'SPACED' | 'PUNCT_SPLIT' | 'REPEAT' | 'CHAR_DROP' | 'WORD_MERGE'
  | 'ABBREV' | 'DEASCII' | 'DOTLESS_I' | 'VOWEL_DROP' | 'SUFFIX_ON_MASKED'
  | 'DIALECT' | 'HOMOGLYPH' | 'ZERO_WIDTH' | 'EMOJI_SUB' | 'PHONETIC'

export type GuardCode =
  | 'SUBSTRING_COLLISION' | 'NEGATION' | 'QUOTE_COUNTERSPEECH' | 'METADISCUSSION'
  | 'SELF_DIRECTED' | 'FRIENDLY_BANTER' | 'DUAL_REGISTER' | 'HOMONYM' | 'NON_HUMAN_TARGET'

export type TargetType = 'individual' | 'group' | 'non_human' | 'none'

export type Action = 'block' | 'escalate' | 'review' | 'nudge' | 'clean'

export type Family = 'A' | 'B' | 'C' | 'D' | 'CLEAN'

export type ModuleName =
  | 'm0_charsafe' | 'm1_lexicon' | 'm2_deobf' | 'm3_encoder'
  | 'm4_implicit' | 'm5_sarcasm' | 'm6_target'

/** [start, end) in Python string indices (Unicode code points). */
export type Span = [number, number]

export interface FormPattern {
  code: FormCode
  confidence: number
  evidence: string
  span: Span | null
  source: string
}

export interface FormResult {
  patterns: FormPattern[]
  /** Decision layer: codes whose confidence reached form.min_confidence. */
  active: FormCode[]
}

export interface ContentScore {
  code: ContentCode
  score: number
  /** "<module>@raw" or "<module>@normalized" */
  source: string
  span: Span | null
  /** Decision layer only. */
  threshold: number | null
  /** Decision layer only; null = not decided. */
  fired: boolean | null
}

export interface TargetResult {
  type: TargetType
  confidence: number
  evidence: string
  span: Span | null
  source: string
}

export interface GuardResult {
  code: GuardCode
  score: number
  source: string
  evidence: string
  span: Span | null
  threshold: number | null
  active: boolean | null
  suppressed: ContentCode[]
}

export interface ThreadSignal {
  thread_id: string | null
  repeat_count: number
  window_posts: number
  same_target: boolean | null
  source: string
  threshold: number | null
  fired: boolean | null
}

export type DegradedKind = 'stub' | 'failed' | 'invalid_output'

export interface DegradedModule {
  module: ModuleName | string
  kinds: DegradedKind[]
  reasons: string[]
}

export interface ChannelReading {
  score: number | null
  fired: boolean | null
}

export interface BinaryOffensive {
  threshold: number | null
  branch: string
  signal: string | null
  signal_value: unknown
  channels: { raw: ChannelReading; normalized: ChannelReading }
  fired: boolean | null
  action: Action | null
}

/**
 * signals is dict[str, Any] in the contract and NOT frozen: every key is
 * optional here and every read must tolerate its absence.
 */
export interface Signals {
  pipeline?: {
    degraded?: DegradedModule[]
    emits_spans?: Record<string, boolean>
  }
  decision?: {
    family_a?: Record<string, unknown> | null
    threshold_branches?: Array<Record<string, unknown>>
    binary_offensive?: BinaryOffensive
    channel_scores?: ContentScore[]
    post_offensive?: boolean
  }
  [module: string]: unknown
}

export interface AnalysisResult {
  text: string
  /** null only when the decision layer itself failed. */
  verdict: Action | null
  form: FormResult
  content: ContentScore[]
  target: TargetResult | null
  guards: GuardResult[]
  thread: ThreadSignal | null
  signals: Signals
  /** Exactly one Turkish sentence; shown verbatim. */
  explanation: string
  latency_ms: number
  per_module_ms: Record<string, number>
  fast_path: boolean
  trace_id: string
  artifact_hash: string
  /** English diagnostics. Not screen text. */
  notes: string[]
}
