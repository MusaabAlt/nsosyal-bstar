<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import Icon from '@/components/Icon.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import HighlightedText from '@/components/panel/HighlightedText.vue'
import ModeratorActions from '@/components/panel/ModeratorActions.vue'
import { copy } from '@/copy'
import { analysisSource } from '@/api'
import { fetchCategories, type Category } from '@/api/panel'
import { useAnalysis } from '@/report/useAnalysis'
import { buildStages, degradedModules, moduleState, verdictView, type ContentRow, type ContentStage } from '@/report/model'
import DetectionEvidence from '@/components/panel/DetectionEvidence.vue'
import { categoryMeta, notProducedCount } from '@/lib/categories'
import { barPosition, formatCount, formatMs, formatScore } from '@/lib/format'
import { actionLabel, formLabel } from '@/contract/labels'
import type { ModuleName } from '@/contract/types'

/*
 * S2 Canlı Analiz: type a sentence, see every engine's own decision. Every
 * score, threshold, fired flag and verdict is read from the response; the
 * page only lays them out.
 */
const MAX_CHARS = 5000
const text = ref('')
const { phase, result, extras, errorText, analyze } = useAnalysis(analysisSource)
const categories = shallowRef<Category[]>([])

onMounted(async () => {
  const out = await fetchCategories()
  if (out.ok) categories.value = out.data.categories
})

const busy = computed(() => phase.value === 'analysing')
const canSubmit = computed(() => text.value.trim().length > 0 && !busy.value)
const charCount = computed(() => Array.from(text.value).length)

function submit() {
  if (canSubmit.value) void analyze(text.value)
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit()
}

const report = computed(() => {
  const r = result.value
  if (phase.value !== 'report' || !r) return null
  const x = extras.value
  const rows = (buildStages(r, x).find((s) => s.kind === 'content') as ContentStage | undefined)?.rows ?? []
  const byKey = new Map(rows.map((row) => [row.key, row]))

  type Card = { key: string; row: ContentRow | null; category: Category | null }
  const cards: Card[] = categories.value.map((c) => ({ key: c.code, row: byKey.get(c.code) ?? null, category: c }))
  for (const row of rows) if (!categories.value.some((c) => c.code === row.key)) cards.push({ key: row.key, row, category: null })

  const verdict = verdictView(r, x)
  const changes = x.normalization?.changes ?? []
  const steps = [...new Set([...changes.map((c) => c.code), ...(r.form?.active ?? [])])].map((code) => formLabel(code))
  const m2 = moduleState(r, 'm2_deobf')
  const legend = [...new Set((r.content ?? []).filter((c) => c.fired === true && c.span).map((c) => c.code as string))]

  return {
    result: r,
    commentId: x.commentId,
    verdict,
    notRun: (degradedModules(r) ?? []).map((d) => d.module).join(', '),
    latency: formatMs(r.latency_ms),
    normalized: x.normalization?.text ?? null,
    normalizationNote: m2 === 'stub' ? copy.live.normalizationStub : copy.live.normalizationNone,
    steps,
    legend,
    cards: cards.map((card) => {
      const meta = categoryMeta(card.key)
      const row = card.row
      const fired = row?.fired ?? null
      const module = (card.category?.module ?? '') as ModuleName
      const state = module ? moduleState(r, module) : 'absent'
      const threshold = row ? row.threshold : (card.category?.threshold ?? null)
      return {
        key: card.key,
        meta,
        fired,
        hasRow: row !== null,
        score: row ? formatScore(row.score) : null,
        threshold: formatScore(threshold),
        /** Bar geometry: positions on a 0-1 track, not displayed numbers. */
        fill: row ? barPosition(row.score) : '0%',
        tick: threshold !== null ? barPosition(threshold) : null,
        verdict: !row ? (state === 'stub' ? copy.live.moduleStub : copy.live.noMatch) : fired === true ? copy.live.detected : fired === false ? copy.live.below : copy.live.undecided,
        verdictClass: fired === true ? 'verdict--hit' : '',
        module: card.category?.module ?? null,
        moduleMs: module ? formatMs(r.per_module_ms?.[module]) : null,
        action:
          fired === true && card.category?.action ? copy.live.action(actionLabel(card.category.action)) : copy.live.noAction,
        note: !row ? copy.live.noMatchNote : null,
      }
    }),
  }
})

/**
 * How many of the contract's content codes the AI does not produce at all.
 *
 * The line beside it counts what was evaluated out of what CAN be produced
 * today, so on its own it reads as if nothing was missing - "8 kategoriden
 * 8'i değerlendirildi" under a verdict that says the evaluation did not
 * complete. This is the rest of that picture.
 *
 * Counted the way Genel Bakış counts it (OverviewView classes): the contract
 * minus what the server reports. It is NOT the degraded module's doing - A4,
 * B5 and C1-C5 are unbuilt and belong to no degraded list; only D1 is owned by
 * the stub the block names - so the two facts are kept in separate sentences.
 * When /api/categories has not answered there is nothing to compare, and the
 * screen claims nothing.
 */
const notProduced = computed(() => notProducedCount(categories.value.map((c) => c.code)))

const TONE_COLOR: Record<string, string> = {
  block: 'var(--danger)',
  review: 'var(--warning)',
  clean: 'var(--mint)',
  incomplete: 'var(--text-muted)',
}
</script>

<template>
  <div class="stack">
    <div class="card composer">
      <span class="composer__avatar">OP</span>
      <div class="composer__main">
        <textarea
          v-model="text"
          class="composer__input"
          :placeholder="copy.live.placeholder"
          :aria-label="copy.live.inputLabel"
          :maxlength="MAX_CHARS * 2"
          @keydown="onKeydown"
        />
        <div v-if="busy" class="progress" aria-hidden="true"><div class="progress__bar" /></div>
        <div class="composer__presets" role="group" :aria-label="copy.live.presets">
          <button
            v-for="preset in analysisSource.presets"
            :key="preset.label"
            type="button"
            class="btn composer__preset"
            :class="{ 'btn--active': text === preset.text }"
            @click="text = preset.text"
          >
            <Icon name="quote" :size="14" />
            {{ preset.label }}
          </button>
        </div>
        <div class="composer__bar">
          <button type="button" class="composer__tool" :title="copy.live.clear" :aria-label="copy.live.clear" @click="text = ''">
            <Icon name="refresh" :size="20" />
          </button>
          <span class="meta">{{ copy.live.language }}</span>
          <span class="meta num" :class="{ 'composer__count--over': charCount > MAX_CHARS }">
            {{ copy.live.characters(String(charCount)) }}
          </span>
          <span class="composer__spacer" />
          <button type="button" class="btn btn--brand" :disabled="!canSubmit || charCount > MAX_CHARS" @click="submit">
            {{ busy ? copy.live.submitting : copy.live.submit }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="phase === 'error'" class="card error">
      <Icon name="alert" :size="20" class="error__icon" />
      <span>{{ errorText }}</span>
      <span class="composer__spacer" />
      <button type="button" class="btn" :disabled="!canSubmit" @click="submit">{{ copy.panel.retry }}</button>
    </div>

    <template v-else-if="report">
      <div class="card norm">
        <div class="norm__pair">
          <span class="muted">{{ copy.live.input }}</span>
          <code class="mono norm__code">{{ report.result.text }}</code>
        </div>
        <Icon name="arrowRight" :size="20" :stroke="1.8" class="norm__arrow" />
        <div class="norm__pair">
          <span class="muted">{{ copy.live.normalized }}</span>
          <code v-if="report.normalized !== null" class="mono norm__code norm__code--out">{{ report.normalized }}</code>
          <span v-else class="unavailable norm__missing">{{ report.normalizationNote }}</span>
        </div>
        <div class="norm__steps">
          <span v-for="s in report.steps" :key="s" class="chip">{{ s }}</span>
          <span v-if="report.normalized !== null && report.steps.length === 0" class="chip">{{ copy.live.noChanges }}</span>
        </div>
      </div>

      <div class="results" :style="{ gridTemplateColumns: `repeat(${Math.min(5, Math.max(2, report.cards.length))}, minmax(0, 1fr))` }">
        <div v-for="card in report.cards" :key="card.key" class="card card--tight result">
          <span
            class="chip result__chip"
            :style="card.fired === true ? { background: card.meta.tint, color: card.meta.ink } : undefined"
          >
            <Icon :name="card.meta.icon" :size="14" :stroke="1.8" />
            {{ card.meta.label }}
          </span>
          <div>
            <div class="result__score-row">
              <span v-if="card.score !== null" class="result__score num" :style="card.fired === true ? { color: card.meta.ink } : undefined">
                {{ card.score }}
              </span>
              <span v-else class="result__score unavailable">—</span>
              <span class="mono result__threshold">
                {{ card.threshold !== null ? copy.panel.threshold(card.threshold) : copy.panel.noThreshold }}
              </span>
            </div>
            <div class="result__track">
              <div class="result__fill" :style="{ width: card.fill, background: card.fired === true ? card.meta.color : 'var(--text-muted)' }" />
              <div v-if="card.tick" class="result__tick" :style="{ left: card.tick }" />
            </div>
          </div>
          <div class="result__foot">
            <span class="chip" :class="card.verdictClass">{{ card.verdict }}</span>
            <span v-if="card.moduleMs !== null" class="mono result__ms">{{ card.moduleMs }} ms</span>
          </div>
          <div class="result__meta">
            <div class="muted">{{ card.action }}</div>
            <div v-if="card.module" class="mono result__module">{{ card.module }}</div>
            <div v-if="card.note" class="meta">{{ card.note }}</div>
          </div>
        </div>
      </div>

      <DetectionEvidence :result="report.result" :extras="extras" />

      <div class="card explain">
        <div class="explain__body">
          <h3 class="card__title">{{ copy.live.explanation }}</h3>
          <p class="explain__text"><HighlightedText :result="report.result" /></p>
          <div class="explain__reason">
            <Icon name="info" :size="20" class="explain__info" />
            <p class="muted explain__sentence">{{ report.result.explanation }}</p>
          </div>
          <div v-if="report.legend.length" class="explain__legend">
            <span v-for="code in report.legend" :key="code" class="explain__legend-item">
              <span class="explain__swatch" :style="{ background: categoryMeta(code).ink }" />{{ categoryMeta(code).label }}
            </span>
          </div>
          <p v-else class="meta explain__nospans">{{ copy.live.noSpans }}</p>
        </div>
        <div class="decision">
          <div class="decision__main">
            <span class="decision__word" :style="{ color: TONE_COLOR[report.verdict.tone] }">
              <Icon :name="report.verdict.tone === 'incomplete' ? 'info' : report.verdict.tone === 'clean' ? 'check' : 'alert'" :size="20" :stroke="1.8" />
              {{ copy.live.finalDecision(report.verdict.word) }}
            </span>
            <span v-if="report.verdict.evaluated" class="mono decision__meta">
              {{ copy.verdict.evaluated(report.verdict.evaluated.total, report.verdict.evaluated.n) }}
            </span>
            <span v-if="notProduced > 0" class="mono decision__meta">
              {{ copy.verdict.notProduced(formatCount(notProduced)!) }}
            </span>
            <span v-if="report.latency !== null" class="mono decision__meta">{{ report.latency }} ms</span>
            <span v-if="report.verdict.tone === 'incomplete' && report.notRun" class="meta decision__notrun">
              {{ copy.live.notRun(report.notRun) }}
            </span>
          </div>
          <ModeratorActions
            :key="report.commentId ?? ''"
            :comment-ids="report.commentId ? [report.commentId] : []"
            :actions="['false_positive', 'queue']"
          />
        </div>
      </div>
    </template>

    <EmptyState v-else-if="phase === 'idle'" icon="scan" :title="copy.live.emptyTitle" :text="copy.live.emptyText" />
  </div>
</template>

<style scoped>
.composer {
  display: flex;
  gap: 12px;
}
.composer__avatar {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}
.composer__main {
  flex: 1;
  min-width: 0;
}
.composer__input {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  border: 0;
  background: transparent;
  font-size: 16px;
  line-height: 24px;
  color: var(--text-primary);
  outline: none;
  padding: 8px 0;
}
.composer__input:focus-visible {
  box-shadow: none;
}
.composer__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 0;
}
.composer__preset {
  height: 28px;
  font-size: 13px;
  padding: 0 12px;
}
.composer__bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-divider);
}
.composer__tool {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s, color 0.15s;
}
.composer__tool:hover {
  background: var(--bg-subtle);
  color: var(--accent);
}
.composer__count--over {
  color: var(--danger);
}
.composer__spacer {
  flex: 1;
}

.error {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--danger);
}
.error__icon {
  color: var(--danger);
}

.norm {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.norm__pair {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.norm__code {
  background: var(--bg-subtle);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  color: var(--text-primary);
  word-break: break-word;
}
.norm__code--out {
  background: var(--cat-obf-bg);
  color: var(--cat-obf-ink);
  font-weight: 500;
}
.norm__missing {
  font-size: 14px;
}
.norm__arrow {
  color: var(--text-muted);
}
.norm__steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.results {
  display: grid;
  gap: 20px;
}
.result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.result__chip {
  align-self: flex-start;
}
.result__score-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.result__score {
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--text-heading);
}
.result__threshold {
  font-size: 12px;
  color: var(--text-meta);
}
.result__track {
  position: relative;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  margin-top: 8px;
}
.result__fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 6px;
  border-radius: var(--radius-full);
}
.result__tick {
  position: absolute;
  top: -4px;
  width: 2px;
  height: 14px;
  border-radius: 1px;
  background: var(--text-heading);
}
.result__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border-card);
}
.verdict--hit {
  background: var(--danger-subtle);
  color: var(--danger);
}
.result__ms {
  font-size: 12px;
  color: var(--text-meta);
}
.result__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.result__module {
  font-size: 12px;
  color: var(--text-meta);
}

.explain {
  padding: 0;
  overflow: hidden;
}
.explain__body {
  padding: 24px;
}
.explain__text {
  margin: 16px 0 0;
  font-size: 16px;
  line-height: 26px;
  color: var(--text-primary);
}
.explain__reason {
  margin-top: 16px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.explain__info {
  color: var(--text-muted);
  margin-top: 2px;
}
.explain__sentence {
  margin: 0;
  text-wrap: pretty;
}
.explain__legend {
  margin-top: 16px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.explain__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 16px;
  color: var(--text-secondary);
}
.explain__swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}
.explain__nospans {
  margin: 16px 0 0;
}
.decision {
  border-top: 1px solid var(--border-card);
  background: var(--bg-subtle);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.decision__main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.decision__word {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.decision__meta {
  color: var(--text-secondary);
}
.decision__notrun {
  flex-basis: 100%;
}
@media (max-width: 1279px) {
  .results {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}

/* ------------------------------------------------------------------ phone */
/*
 * One score card at a time, and the input -> normalized pair reads downwards
 * with the arrow turned to match, instead of two code blocks fighting for a
 * 360px line.
 */
@media (max-width: 599px) {
  .results {
    grid-template-columns: 1fr !important;
    gap: 12px;
  }
  .composer {
    gap: 0;
  }
  .composer__avatar {
    display: none;
  }
  .composer__input {
    min-height: 84px;
    padding-top: 0;
  }
  .composer__presets {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    margin: 0 calc(var(--page-gutter) * -1);
    padding: 12px var(--page-gutter);
  }
  .composer__presets::-webkit-scrollbar {
    display: none;
  }
  .composer__preset {
    flex: none;
    height: 34px;
  }
  .composer__bar {
    flex-wrap: wrap;
    gap: 8px 12px;
    padding-top: 12px;
  }
  .composer__spacer {
    display: none;
  }
  .composer__bar .btn--brand {
    flex-basis: 100%;
  }

  .norm {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .norm__pair {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .norm__code {
    width: 100%;
  }
  .norm__arrow {
    align-self: center;
    transform: rotate(90deg);
  }
  .norm__steps {
    margin-left: 0;
  }

  .result__score {
    font-size: 26px;
    line-height: 32px;
  }
  .explain__body {
    padding: 16px;
  }
  .explain__text {
    font-size: 15px;
    line-height: 24px;
  }
  .decision {
    padding: 14px 16px;
    gap: 12px;
  }
  .decision__main {
    gap: 8px 12px;
  }
  .error {
    flex-wrap: wrap;
  }
}
</style>
