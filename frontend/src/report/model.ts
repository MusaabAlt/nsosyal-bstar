import type {
  AnalysisResult,
  ContentScore,
  DegradedModule,
  FormPattern,
  GuardResult,
  ModuleName,
  TargetResult,
  ThreadSignal,
} from '@/contract/types'
import { copy } from '@/copy'

/*
 * Turns one AnalysisResult into what the report shows.
 *
 * Hard rule (AMIN_BRIEF 6, design-system 6): this file READS decisions, it
 * never makes them. verdict, fired, active and suppressed come from the
 * payload; no score is ever compared with a threshold, and no number is
 * computed. The only derived things are which word to show for fields that
 * are already decided, and the display order.
 */

// ---------------------------------------------------------------- statuses

export type StatusKey = 'passed' | 'triggered' | 'below' | 'notApplied' | 'moduleUnavailable' | 'noData'

export const STATUS_WORD: Record<StatusKey, string> = copy.status

// ---------------------------------------------------------------- verdict

export type VerdictTone = 'block' | 'review' | 'clean' | 'incomplete'

export interface VerdictView {
  word: string
  tone: VerdictTone
  /** Modules that did not run. Present only for the incomplete tone. */
  notRun: DegradedModule[]
  /** false when the response did not say which modules ran at all. */
  moduleStatusKnown: boolean
  /** Verbatim from the decision layer. */
  explanation: string
}

/**
 * The degraded list, or null when the response does not carry it. signals is
 * not a frozen part of the contract, so its absence must be handled.
 */
export function degradedModules(result: AnalysisResult): DegradedModule[] | null {
  const list = result.signals?.pipeline?.degraded
  return Array.isArray(list) ? list : null
}

/**
 * Verdict word mapping agreed for this build (design-system 4.11 words only):
 * block -> Engelle, escalate and review -> İncele, nudge -> Hassas içerik,
 * clean -> Temiz. Any degraded result is the incomplete block (4.12) and is
 * never green: a pass over modules that did not run is the worst failure
 * this screen can produce (prohibition 17). A response that does not say
 * which modules ran is treated the same way: fail closed.
 */
export function verdictView(result: AnalysisResult): VerdictView {
  const degraded = degradedModules(result)
  if (degraded === null || degraded.length > 0) {
    return {
      word: copy.verdict.incomplete,
      tone: 'incomplete',
      notRun: degraded ?? [],
      moduleStatusKnown: degraded !== null,
      explanation: result.explanation,
    }
  }
  const base = { notRun: [], moduleStatusKnown: true, explanation: result.explanation }
  switch (result.verdict) {
    case 'block':
      return { ...base, word: copy.verdict.block, tone: 'block' }
    case 'escalate':
    case 'review':
      return { ...base, word: copy.verdict.review, tone: 'review' }
    case 'nudge':
      return { ...base, word: copy.verdict.sensitive, tone: 'review' }
    case 'clean':
      return { ...base, word: copy.verdict.clean, tone: 'clean' }
    default:
      // verdict null is the decision-layer failure; the view shows the error
      // state for it. Never fall through to a pass.
      return { ...base, word: copy.verdict.incomplete, tone: 'incomplete' }
  }
}

/** verdict: null means the decision layer itself failed (AMIN_BRIEF 5, state 2). */
export function isDecisionFailure(result: AnalysisResult): boolean {
  return result.verdict === null
}

// ---------------------------------------------------------------- consequence

export type ConsequenceMode = 'normal' | 'queued' | 'sensitive' | 'withheld'

export interface ConsequenceView {
  mode: ConsequenceMode
  /** The evaluation did not complete: say so, never imply the post was cleared. */
  incomplete: boolean
}

export function consequenceView(result: AnalysisResult): ConsequenceView {
  const degraded = degradedModules(result)
  const incomplete = degraded === null || degraded.length > 0
  switch (result.verdict) {
    case 'block':
      return { mode: 'withheld', incomplete }
    case 'nudge':
      return { mode: 'sensitive', incomplete }
    case 'escalate':
    case 'review':
      // A review caused only by degradation is shown as incomplete, not as queued.
      return { mode: incomplete ? 'normal' : 'queued', incomplete }
    default:
      return { mode: 'normal', incomplete }
  }
}

// ---------------------------------------------------------------- modules

export type ModuleState = 'ran' | 'stub' | 'failed' | 'absent'

export function moduleState(result: AnalysisResult, module: ModuleName): ModuleState {
  const entry = degradedModules(result)?.find((d) => d.module === module)
  if (entry) return entry.kinds.includes('stub') ? 'stub' : 'failed'
  if (result.per_module_ms && module in result.per_module_ms) return 'ran'
  return 'absent'
}

/** Status and explanation line for a stage whose module did not run properly. */
function unavailable(state: ModuleState): { status: StatusKey; line: string } {
  switch (state) {
    case 'stub':
      return { status: 'moduleUnavailable', line: copy.stages.moduleStub }
    case 'failed':
      return { status: 'noData', line: copy.stages.moduleFailed }
    default:
      return { status: 'noData', line: copy.stages.noOutput }
  }
}

function moduleDuration(result: AnalysisResult, module: ModuleName): number | null {
  const value = result.per_module_ms?.[module]
  return typeof value === 'number' ? value : null
}

// ---------------------------------------------------------------- stages

interface StageBase {
  number: number
  name: string
  /** null: the stage is a summary, not a check, and shows no status word. */
  status: StatusKey | null
  durationMs: number | null
  /** One line shown when the stage has nothing else to say (4.8: never collapses). */
  line: string | null
}

export interface InputStage extends StageBase {
  kind: 'input'
  text: string
}

export interface PatternStage extends StageBase {
  kind: 'charsafe' | 'obfuscation'
  text: string
  patterns: Array<FormPattern & { active: boolean }>
}

export interface ScorePairView {
  raw: { score: number; fired: boolean | null }
  normalized: { score: number; fired: boolean | null }
}

export interface NormalizationStage extends StageBase {
  kind: 'normalization'
  text: string
  patterns: FormPattern[]
  scorePair: ScorePairView | null
}

export interface ContentRow {
  entry: ContentScore
  /** Label of the active guard that suppressed this code, if any. */
  suppressedBy: GuardResult | null
}

export interface ContentStage extends StageBase {
  kind: 'content'
  rows: ContentRow[]
}

export interface TargetStage extends StageBase {
  kind: 'target'
  text: string
  target: TargetResult | null
}

export interface GuardView {
  guard: GuardResult
  /** Suppressed content entries that carry a span, for the underline inside the guard evidence. */
  suppressedEntries: ContentScore[]
}

export interface GuardsStage extends StageBase {
  kind: 'guards'
  text: string
  active: GuardView[]
}

export interface ThreadStage extends StageBase {
  kind: 'thread'
  thread: ThreadSignal | null
}

export interface ReasonStage extends StageBase {
  kind: 'reason'
  explanation: string
  triggeredStages: string[]
}

export type Stage =
  | InputStage
  | PatternStage
  | NormalizationStage
  | ContentStage
  | TargetStage
  | GuardsStage
  | ThreadStage
  | ReasonStage

const CONTENT_MODULES: ModuleName[] = ['m1_lexicon', 'm3_encoder', 'm4_implicit', 'm5_sarcasm']

function patternStage(
  result: AnalysisResult,
  kind: 'charsafe' | 'obfuscation',
  number: number,
  module: ModuleName,
  belongs: (p: FormPattern) => boolean,
  noneLine: string,
): PatternStage {
  const active = new Set(result.form?.active ?? [])
  const patterns = (result.form?.patterns ?? []).filter(belongs).map((p) => ({ ...p, active: active.has(p.code) }))
  const state = moduleState(result, module)
  const name = kind === 'charsafe' ? copy.stages.charsafe : copy.stages.obfuscation

  let status: StatusKey
  let line: string | null = null
  if (patterns.some((p) => p.active)) status = 'triggered'
  else if (patterns.length > 0) status = 'below'
  else if (state === 'ran') {
    status = 'passed'
    line = noneLine
  } else {
    ;({ status, line } = unavailable(state))
  }
  return { kind, number, name, status, line, durationMs: moduleDuration(result, module), text: result.text, patterns }
}

function normalizationStage(result: AnalysisResult): NormalizationStage {
  const state = moduleState(result, 'm2_deobf')
  const channels = result.signals?.decision?.binary_offensive?.channels
  const raw = channels?.raw
  const normalized = channels?.normalized
  // Rendered only when the API supplies BOTH scores; never computed (4.10).
  const scorePair: ScorePairView | null =
    typeof raw?.score === 'number' && typeof normalized?.score === 'number'
      ? { raw: { score: raw.score, fired: raw.fired }, normalized: { score: normalized.score, fired: normalized.fired } }
      : null

  let status: StatusKey
  let line: string | null = null
  if (scorePair) status = scorePair.normalized.fired === true ? 'triggered' : 'below'
  else if (state === 'ran') {
    status = 'passed'
    line = copy.stages.normalizationNone
  } else {
    ;({ status, line } = unavailable(state))
  }
  return {
    kind: 'normalization',
    number: 4,
    name: copy.stages.normalization,
    status,
    line,
    durationMs: null,
    text: result.text,
    patterns: result.form?.patterns ?? [],
    scorePair,
  }
}

function activeGuards(result: AnalysisResult): GuardResult[] {
  return (result.guards ?? []).filter((g) => g.active === true)
}

function contentStage(result: AnalysisResult): ContentStage {
  const guards = activeGuards(result)
  const rows: ContentRow[] = (result.content ?? []).map((entry) => ({
    entry,
    suppressedBy: guards.find((g) => g.suppressed?.includes(entry.code)) ?? null,
  }))
  // Fired first, then the rest; each group by score, highest first (pages-spec stage 5).
  rows.sort((a, b) => {
    const af = a.entry.fired === true ? 0 : 1
    const bf = b.entry.fired === true ? 0 : 1
    return af - bf || b.entry.score - a.entry.score
  })

  const states = CONTENT_MODULES.map((m) => moduleState(result, m))
  let status: StatusKey
  let line: string | null = null
  if (rows.some((r) => r.entry.fired === true)) status = 'triggered'
  else if (rows.length > 0) status = 'below'
  else if (states.includes('stub')) ({ status, line } = unavailable('stub'))
  else if (states.includes('failed')) ({ status, line } = unavailable('failed'))
  else if (states.includes('ran')) {
    status = 'passed'
    line = copy.stages.contentNone
  } else ({ status, line } = unavailable('absent'))

  return { kind: 'content', number: 5, name: copy.stages.content, status, line, durationMs: null, rows }
}

function targetStage(result: AnalysisResult): TargetStage {
  const state = moduleState(result, 'm6_target')
  const target = result.target ?? null
  let status: StatusKey
  let line: string | null = null
  if (target && target.type !== 'none') status = 'triggered'
  else if (target) {
    status = 'passed'
    line = copy.stages.targetNone
  } else if (state === 'ran') {
    status = 'noData'
    line = copy.stages.noOutput
  } else ({ status, line } = unavailable(state))
  return {
    kind: 'target',
    number: 6,
    name: copy.stages.target,
    status,
    line,
    durationMs: moduleDuration(result, 'm6_target'),
    text: result.text,
    target,
  }
}

function guardsStage(result: AnalysisResult): GuardsStage {
  const active: GuardView[] = activeGuards(result).map((guard) => ({
    guard,
    suppressedEntries: (result.content ?? []).filter((c) => guard.suppressed?.includes(c.code) && c.span !== null),
  }))
  // Guards are produced by m1 today (HANDOVER decision 57).
  const state = moduleState(result, 'm1_lexicon')
  let status: StatusKey
  let line: string | null = null
  if (active.length > 0) status = 'triggered'
  else if ((result.guards ?? []).length > 0 || state === 'ran') {
    status = (result.guards ?? []).length > 0 ? 'below' : 'passed'
    line = copy.stages.guardsNone
  } else ({ status, line } = unavailable(state))
  return { kind: 'guards', number: 7, name: copy.stages.guards, status, line, durationMs: null, text: result.text, active }
}

function threadStage(result: AnalysisResult): ThreadStage {
  const thread = result.thread ?? null
  let status: StatusKey
  let line: string | null = null
  if (!thread) {
    status = 'notApplied'
    line = copy.stages.threadSinglePost
  } else if (thread.fired === true) status = 'triggered'
  else if (thread.fired === false) status = 'below'
  else status = 'noData'
  return { kind: 'thread', number: 8, name: copy.stages.thread, status, line, durationMs: null, thread }
}

export function buildStages(result: AnalysisResult): Stage[] {
  const stages: Stage[] = [
    {
      kind: 'input',
      number: 1,
      name: copy.stages.input,
      status: 'passed',
      line: null,
      durationMs: null,
      text: result.text,
    },
    patternStage(result, 'charsafe', 2, 'm0_charsafe', (p) => p.source === 'm0_charsafe', copy.stages.charsafeNone),
    patternStage(result, 'obfuscation', 3, 'm2_deobf', (p) => p.source !== 'm0_charsafe', copy.stages.obfuscationNone),
    normalizationStage(result),
    contentStage(result),
    targetStage(result),
    guardsStage(result),
    threadStage(result),
  ]

  const triggeredStages = stages.filter((s) => s.status === 'triggered').map((s) => s.name)
  stages.push({
    kind: 'reason',
    number: 9,
    name: copy.stages.reason,
    // Not a second verdict: the verdict is at the top (pages-spec stage 9).
    status: null,
    line: triggeredStages.length === 0 ? copy.stages.reasonNoStage : null,
    durationMs: null,
    explanation: result.explanation,
    triggeredStages,
  })
  return stages
}
