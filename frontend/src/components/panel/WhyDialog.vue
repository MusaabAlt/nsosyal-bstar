<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import Icon from '@/components/Icon.vue'
import CategoryChip from './CategoryChip.vue'
import HighlightedText from './HighlightedText.vue'
import StatusPill from './StatusPill.vue'
import { copy } from '@/copy'
import type { PanelItem } from '@/api/panel'
import type { DegradedModule, ModuleName } from '@/contract/types'
import { categoryMeta, BINARY_OFFENSIVE } from '@/lib/categories'
import { contentLabel, formLabel, guardLabel, targetLabel } from '@/contract/labels'
import { formatAgo, formatMs, formatScore } from '@/lib/format'

/*
 * "Neden?": what the system read in this message and which module put it
 * there. The dashboard shows the verdict; this shows the evidence behind it.
 *
 * Everything on this screen is read from the stored result. No score is
 * compared with a threshold here and no outcome is derived: `fired` and
 * `active` are read as the decision layer wrote them.
 */
const props = defineProps<{ item: PanelItem }>()
const emit = defineEmits<{ close: [] }>()

// Escape closes the panel: on a projector the presenter's hand is on the
// keyboard, not hunting for the corner of a dialog.
function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

const result = computed(() => props.item.result)

const degradedModules = computed<DegradedModule[]>(() => result.value?.signals?.pipeline?.degraded ?? [])

function isDegraded(module: string): boolean {
  return degradedModules.value.some((d) => d.module === module)
}

/** A module's own signals block, if the response carried one. */
function signalsOf(module: string): Record<string, unknown> {
  const value = result.value?.signals?.[module]
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function numberOf(module: string, key: string): number | null {
  const value = signalsOf(module)[key]
  return typeof value === 'number' ? value : null
}

const offensive = computed(() => result.value?.signals?.decision?.binary_offensive ?? null)

/** One line per module: what it contributed to this decision, in words. */
interface ModuleLine {
  name: ModuleName | string
  label: string
  detail: string
  /** true when this module put something into the decision. */
  contributed: boolean
  degraded: boolean
  ms: number | null
}

const modules = computed<ModuleLine[]>(() => {
  const r = result.value
  const ms = (name: string) => {
    const value = r?.per_module_ms?.[name]
    return typeof value === 'number' ? value : null
  }
  const lines: ModuleLine[] = []

  const removed = numberOf('m0_charsafe', 'invisible_removed') ?? 0
  const mapped = numberOf('m0_charsafe', 'homoglyphs_mapped') ?? 0
  lines.push({
    name: 'm0_charsafe',
    label: copy.overview.modules.m0_charsafe!,
    detail: removed + mapped > 0 ? copy.overview.charsafeChanged(removed, mapped) : copy.overview.charsafeClean,
    contributed: removed + mapped > 0,
    degraded: isDegraded('m0_charsafe'),
    ms: ms('m0_charsafe'),
  })

  const guards = (r?.guards ?? []).filter((g) => g.active === true)
  const lexiconHit = signalsOf('m1_lexicon')['lexicon_hit'] === true
  lines.push({
    name: 'm1_lexicon',
    label: copy.overview.modules.m1_lexicon!,
    detail: guards.length
      ? guards.map((g) => guardLabel(g.code)).join(', ')
      : lexiconHit
        ? copy.overview.lexiconHit
        : copy.overview.lexiconMiss,
    contributed: guards.length > 0 || lexiconHit,
    degraded: isDegraded('m1_lexicon'),
    ms: ms('m1_lexicon'),
  })

  const patterns = r?.form?.active ?? []
  lines.push({
    name: 'm2_deobf',
    label: copy.overview.modules.m2_deobf!,
    detail: patterns.length ? patterns.map((p) => formLabel(p)).join(', ') : copy.overview.deobfNone,
    contributed: patterns.length > 0,
    degraded: isDegraded('m2_deobf'),
    ms: ms('m2_deobf'),
  })

  const raw = offensive.value?.channels?.raw
  const threshold = offensive.value?.threshold
  lines.push({
    name: 'm3_encoder',
    label: copy.overview.modules.m3_encoder!,
    detail:
      typeof raw?.score === 'number'
        ? copy.overview.offensiveLine(formatScore(raw.score)!, formatScore(threshold) ?? copy.stages.thresholdMissing)
        : copy.overview.moduleNoSignal,
    contributed: offensive.value?.fired === true,
    degraded: isDegraded('m3_encoder'),
    ms: ms('m3_encoder'),
  })

  for (const [name, family] of [
    ['m4_implicit', 'C'],
    ['m5_sarcasm', 'D'],
  ] as const) {
    const own = (r?.content ?? []).filter((c) => c.fired === true && c.code.startsWith(family))
    lines.push({
      name,
      label: copy.overview.modules[name]!,
      detail: own.length ? own.map((c) => contentLabel(c.code)).join(', ') : copy.overview.moduleNoSignal,
      contributed: own.length > 0,
      degraded: isDegraded(name),
      ms: ms(name),
    })
  }

  const target = r?.target
  lines.push({
    name: 'm6_target',
    label: copy.overview.modules.m6_target!,
    detail: target
      ? copy.overview.targetLine(targetLabel(target.type), formatScore(target.confidence) ?? '—')
      : copy.stages.targetNone,
    contributed: Boolean(target) && target?.type !== 'none',
    degraded: isDegraded('m6_target'),
    ms: ms('m6_target'),
  })

  return lines
})

/** Every category the encoder scored, the ones that fired first. */
const scores = computed(() => {
  const rows = (result.value?.content ?? []).map((c) => ({
    code: c.code as string,
    label: contentLabel(c.code),
    score: c.score,
    threshold: c.threshold,
    fired: c.fired,
    meta: categoryMeta(c.code),
  }))
  const bo = offensive.value
  const raw = bo?.channels?.raw
  if (bo && typeof raw?.score === 'number') {
    rows.push({
      code: BINARY_OFFENSIVE,
      label: copy.stages.binaryOffensive,
      score: raw.score,
      threshold: bo.threshold,
      fired: bo.fired,
      meta: categoryMeta(BINARY_OFFENSIVE),
    })
  }
  rows.sort((a, b) => Number(b.fired === true) - Number(a.fired === true) || b.score - a.score)
  return rows
})

const guards = computed(() => result.value?.guards ?? [])

/**
 * The codes an active guard cleared. A suppressed code did not fire, but it
 * did not stay under its threshold either, so it must not be reported as if
 * it had: the guard is the reason, and the guard is what the screen says.
 */
const suppressed = computed(() => {
  const codes = new Set<string>()
  for (const g of guards.value) {
    if (g.active !== true) continue
    for (const code of g.suppressed ?? []) codes.add(code)
  }
  return codes
})

function outcome(code: string, fired: boolean | null | undefined): string {
  if (fired === true) return copy.overview.whyFired
  if (suppressed.value.has(code)) return copy.overview.whySuppressed
  if (fired === false) return copy.overview.whyNotFired
  return copy.overview.whyUndecided
}
</script>

<template>
  <div class="scrim" role="presentation" @click.self="$emit('close')">
    <section class="sheet card" role="dialog" aria-modal="true" :aria-label="copy.overview.whyTitle">
      <header class="sheet__head">
        <h2 class="card__title">{{ copy.overview.whyTitle }}</h2>
        <button type="button" class="btn btn--ghost sheet__close" :aria-label="copy.overview.whyClose" @click="$emit('close')">
          <Icon name="x" :size="20" />
        </button>
      </header>

      <div class="sheet__body">
        <article class="quote">
          <div class="quote__head">
            <span class="quote__name">{{ item.nickname }}</span>
            <span class="meta">@{{ item.nickname }} · {{ formatAgo(item.created_at) }}</span>
          </div>
          <p class="quote__text"><HighlightedText :result="item.result" /></p>
        </article>

        <div class="verdict">
          <span class="meta verdict__label">{{ copy.overview.whyVerdict }}</span>
          <StatusPill :action="item.final_action" />
          <p class="verdict__text">{{ item.explanation }}</p>
        </div>

        <section class="block">
          <h3 class="block__title">{{ copy.overview.whyModules }}</h3>
          <ul class="modules">
            <li v-for="m in modules" :key="m.name" class="module" :class="{ 'module--on': m.contributed }">
              <span class="module__mark">
                <Icon :name="m.degraded ? 'alert' : m.contributed ? 'bolt' : 'check'" :size="15" :stroke="1.8" />
              </span>
              <span class="module__name">{{ m.label }}</span>
              <span class="module__detail">{{ m.degraded ? copy.overview.moduleDegraded : m.detail }}</span>
              <span class="mono module__ms">{{ m.ms !== null ? `${formatMs(m.ms)} ms` : '' }}</span>
            </li>
          </ul>
        </section>

        <section class="block">
          <h3 class="block__title">{{ copy.overview.whyScores }}</h3>
          <table v-if="scores.length" class="scores">
            <thead>
              <tr>
                <th>{{ copy.queue.category }}</th>
                <th class="right">{{ copy.queue.score }}</th>
                <th class="right">{{ copy.queue.threshold }}</th>
                <th>{{ copy.queue.outcome }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in scores" :key="`${row.code}-${row.score}`">
                <td>
                  <span class="mono score__code" :style="{ color: row.meta.ink }">{{ row.code }}</span>
                  <span class="score__label">{{ row.label }}</span>
                </td>
                <td class="mono right">{{ formatScore(row.score) }}</td>
                <td class="mono right muted-cell">{{ formatScore(row.threshold) ?? copy.stages.thresholdMissing }}</td>
                <td>
                  <span
                    class="chip"
                    :class="{ 'chip--fired': row.fired === true, 'chip--guarded': row.fired !== true && suppressed.has(row.code) }"
                  >
                    {{ outcome(row.code, row.fired) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">{{ copy.overview.whyNoScores }}</p>
        </section>

        <section class="block">
          <h3 class="block__title">{{ copy.overview.whyGuards }}</h3>
          <ul v-if="guards.length" class="guards">
            <li v-for="g in guards" :key="g.code" class="guard">
              <Icon name="check" :size="16" :stroke="1.8" class="guard__icon" :class="{ 'guard__icon--on': g.active }" />
              <span class="guard__name">{{ guardLabel(g.code) }}</span>
              <span class="mono guard__score">{{ formatScore(g.score) }}</span>
              <span v-if="g.suppressed.length" class="guard__suppressed">
                <CategoryChip v-for="code in g.suppressed" :key="code" :code="code" />
              </span>
            </li>
          </ul>
          <p v-else class="muted">{{ copy.overview.whyNoGuards }}</p>
        </section>
      </div>
    </section>
  </div>
</template>

<style scoped>
.scrim {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: var(--scrim);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
}
.sheet {
  width: min(760px, 100%);
  max-height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  box-shadow: var(--shadow-float);
}
.sheet__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-card);
}
.sheet__close {
  color: var(--text-muted);
}
.sheet__body {
  padding: 20px 24px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quote {
  background: var(--bg-subtle);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
}
.quote__head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}
.quote__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.quote__text {
  margin: 6px 0 0;
  font-size: 16px;
  line-height: 24px;
}

.verdict {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.verdict__label {
  font-size: 13px;
}
.verdict__text {
  margin: 0;
  flex: 1 1 260px;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
}

.block__title {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}

.modules {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.module {
  display: grid;
  grid-template-columns: 24px minmax(0, 170px) 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-divider);
  color: var(--text-muted);
}
.module:last-child {
  border-bottom: 0;
}
.module__mark {
  display: flex;
  color: var(--text-meta);
}
.module--on {
  color: var(--text-primary);
}
.module--on .module__mark {
  color: var(--accent);
}
.module__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.module--on .module__name {
  color: var(--text-heading);
}
.module__detail {
  font-size: 13px;
  line-height: 18px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.module__ms {
  font-size: 12px;
  color: var(--text-meta);
}

.scores {
  width: 100%;
  border-collapse: collapse;
}
.scores th {
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-meta);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-divider);
}
.scores td {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 13px;
}
.scores tr:last-child td {
  border-bottom: 0;
}
.right {
  text-align: right;
  padding-right: 12px;
}
.muted-cell {
  color: var(--text-meta);
}
.score__code {
  font-weight: 700;
  margin-right: 8px;
}
.score__label {
  color: var(--text-secondary);
}
.chip--fired {
  background: var(--cat-direct-bg);
  color: var(--cat-direct-ink);
}
.chip--guarded {
  background: var(--cat-clean-bg);
  color: var(--cat-clean-ink);
}

.guards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.guard {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}
.guard__icon {
  color: var(--text-meta);
}
.guard__icon--on {
  color: var(--mint);
}
.guard__name {
  color: var(--text-secondary);
}
.guard__score {
  color: var(--text-meta);
}
.guard__suppressed {
  display: flex;
  gap: 6px;
}

/* ------------------------------------------------------------------ phone */
/*
 * A bottom sheet, not a centred dialog: it opens where the thumb already is
 * and uses the full width for the module and score tables.
 */
@media (max-width: 599px) {
  .scrim {
    align-items: flex-end;
    padding: 0;
  }
  .sheet {
    width: 100%;
    max-height: 92dvh;
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    border-bottom: 0;
  }
  .sheet__head {
    padding: 14px 16px;
  }
  .sheet__body {
    padding: 16px 16px 24px;
    gap: 16px;
  }
  /* Name and timing on the first line, the detail sentence under the name
     instead of being cut. Placed explicitly: auto-placement would push the
     timing onto a third row and break "0.1 ms" across two lines. */
  .module {
    grid-template-columns: 20px 1fr auto;
    column-gap: 8px;
    row-gap: 2px;
  }
  .module__mark {
    grid-area: 1 / 1;
  }
  .module__name {
    grid-area: 1 / 2;
  }
  .module__ms {
    grid-area: 1 / 3;
    white-space: nowrap;
  }
  .module__detail {
    grid-area: 2 / 2 / 3 / -1;
    white-space: normal;
    overflow: visible;
  }
  .quote__text {
    font-size: 15px;
    line-height: 23px;
  }
}
</style>
