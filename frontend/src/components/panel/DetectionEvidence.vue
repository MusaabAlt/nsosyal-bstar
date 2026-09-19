<script setup lang="ts">
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import { copy } from '@/copy'
import type { AnalysisResult, Span } from '@/contract/types'
import type { Extras } from '@/api/source'
import { NO_EXTRAS } from '@/api/source'
import {
  buildStages,
  STATUS_WORD,
  type GuardsStage,
  type PatternStage,
  type TargetStage,
} from '@/report/model'
import { formLabel, guardLabel } from '@/contract/labels'
import { formatScore } from '@/lib/format'
import { codePointLength, isValidSpan, segment, sliceSpan } from '@/lib/spans'

/*
 * The evidence the three rule-based modules produce, as pages-spec 2.3
 * describes it: stage 3 Gizleme tespiti (m2_deobf), stage 6 Hedef (m6_target)
 * and stage 7 Koruyucu kontroller (m1_lexicon's negative controls). All three
 * landed on 2026-09-17; before that they were stubs and the page had nothing
 * to show, which is why it showed nothing.
 *
 * Stage 7 deliberately carries the most weight - "a stage that looks empty
 * here undersells half the system" - so it gets a full-width panel and a
 * sentence, never a bare chip.
 *
 * Nothing is computed here. Which pattern is active, which guard fired and
 * what it suppressed all come from report/model.ts, which only reads the
 * decision layer's own fields (AMIN_BRIEF 6).
 */
const props = withDefaults(defineProps<{ result: AnalysisResult; extras?: Extras }>(), {
  extras: () => NO_EXTRAS,
})

const stages = computed(() => buildStages(props.result, props.extras))

const obfuscation = computed(() => stages.value.find((s) => s.kind === 'obfuscation') as PatternStage)
const target = computed(() => stages.value.find((s) => s.kind === 'target') as TargetStage)
const guards = computed(() => stages.value.find((s) => s.kind === 'guards') as GuardsStage)

const patterns = computed(() =>
  obfuscation.value.patterns.map((p, i) => ({
    key: `${p.code}:${p.span?.[0] ?? -1}:${i}`,
    label: formLabel(p.code),
    /** The exact substring the module reported; never re-sliced from the text. */
    evidence: p.evidence,
    confidence: formatScore(p.confidence),
    active: p.active,
  })),
)

/** The target's evidence in position: the whole text with its span highlighted. */
const targetSegments = computed(() => {
  const t = target.value.target
  const text = target.value.text
  if (!t || !isValidSpan(t.span, codePointLength(text))) return null
  return segment(text, [{ span: t.span, kind: 'highlight' }])
})

const targetWord = computed(() => {
  const t = target.value.target
  return t ? (copy.stages.targetWords[t.type] ?? t.type) : null
})

/*
 * One active guard, ready to render. `word` is the containing word the guard
 * matched on, with the suppressed span underlined inside it - the
 * substring-collision moment pages-spec stage 7 asks for by name. The
 * underline appears only when the guard and the score it suppressed both
 * carry a span (ADR-001); otherwise the word still shows, unmarked.
 */
const guardViews = computed(() =>
  guards.value.active.map((view, i) => {
    const { guard } = view
    const text = props.result.text
    const length = codePointLength(text)
    const placed = isValidSpan(guard.span, length)
    const word = placed ? sliceSpan(text, guard.span as Span) : guard.evidence
    const offset = placed ? (guard.span as Span)[0] : 0
    const inner = placed
      ? view.suppressedEntries
          .map((c) => c.span)
          .filter((s): s is Span => isValidSpan(s, length))
          // Re-based on the guard's own span so the underline lands inside `word`.
          .map((s) => ({ span: [s[0] - offset, s[1] - offset] as Span, kind: 'underline' as const }))
      : []
    const codes = guard.suppressed ?? []
    return {
      key: `${guard.code}:${guard.span?.[0] ?? -1}:${i}`,
      label: guardLabel(guard.code),
      word,
      segments: word ? segment(word, inner) : [],
      // The named sentence when the decision layer said what was suppressed;
      // otherwise the general one, which is true of every active guard.
      sentence: codes.length
        ? copy.stages.guardPrevented(guardLabel(guard.code), codes.join(', '))
        : copy.stages.guardDeliberate,
    }
  }),
)
</script>

<template>
  <div class="evidence">
    <div class="evidence__pair">
      <!-- Stage 3 -->
      <section class="card evidence__panel">
        <header class="evidence__head">
          <Icon name="viewOff" :size="20" :stroke="1.8" />
          <h3 class="card__title">{{ copy.stages.obfuscation }}</h3>
          <span class="chip evidence__status">{{ STATUS_WORD[obfuscation.status!] }}</span>
        </header>

        <ul v-if="patterns.length" class="evidence__list">
          <li v-for="p in patterns" :key="p.key" class="pattern" :class="{ 'pattern--off': !p.active }">
            <span class="pattern__name">{{ p.label }}</span>
            <code class="mono pattern__evidence">{{ p.evidence }}</code>
            <span v-if="p.confidence !== null" class="mono meta">{{ p.confidence }}</span>
          </li>
        </ul>
        <p v-else-if="obfuscation.line" class="muted evidence__line">{{ obfuscation.line }}</p>

        <p v-if="obfuscation.checkedOther !== null" class="meta evidence__foot">
          {{ copy.stages.patternsCheckedOther(obfuscation.checkedOther) }}
        </p>
      </section>

      <!-- Stage 6 -->
      <section class="card evidence__panel">
        <header class="evidence__head">
          <Icon name="userBlock" :size="20" :stroke="1.8" />
          <h3 class="card__title">{{ copy.stages.target }}</h3>
          <span class="chip evidence__status">{{ STATUS_WORD[target.status!] }}</span>
        </header>

        <template v-if="target.target && targetWord">
          <div class="target__type">
            <span class="target__word">{{ targetWord }}</span>
            <span v-if="formatScore(target.target.confidence) !== null" class="mono meta">
              {{ formatScore(target.target.confidence) }}
            </span>
          </div>
          <p v-if="targetSegments" class="target__text">
            <span v-for="(s, i) in targetSegments" :key="i" :class="{ target__mark: s.highlight }">{{ s.text }}</span>
          </p>
          <p v-else-if="target.target.evidence" class="target__text">
            <span class="target__mark">{{ target.target.evidence }}</span>
          </p>
        </template>
        <p v-else-if="target.line" class="muted evidence__line">{{ target.line }}</p>
      </section>
    </div>

    <!-- Stage 7: the widest panel on purpose (pages-spec stage 7). -->
    <section class="card evidence__panel">
      <header class="evidence__head">
        <Icon name="check" :size="20" :stroke="1.8" />
        <h3 class="card__title">{{ copy.stages.guards }}</h3>
        <span class="chip evidence__status">{{ STATUS_WORD[guards.status!] }}</span>
      </header>

      <ul v-if="guardViews.length" class="evidence__list">
        <li v-for="g in guardViews" :key="g.key" class="guard">
          <div class="guard__head">
            <span class="guard__name">{{ g.label }}</span>
            <code v-if="g.word" class="mono guard__word">
              <span v-for="(s, i) in g.segments" :key="i" :class="{ guard__inner: s.underline }">{{ s.text }}</span>
            </code>
          </div>
          <p class="muted guard__sentence">{{ g.sentence }}</p>
        </li>
      </ul>
      <p v-else class="muted evidence__line">{{ guards.line ?? copy.stages.guardsNone }}</p>
    </section>
  </div>
</template>

<style scoped>
.evidence {
  display: grid;
  gap: 20px;
}
.evidence__pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.evidence__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.evidence__head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}
.evidence__head .card__title {
  flex: 1;
  margin: 0;
}
.evidence__status {
  font-size: 12px;
}
.evidence__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}
.evidence__line,
.evidence__foot {
  margin: 0;
}
.evidence__foot {
  margin-top: auto;
  padding-top: 4px;
}
.pattern {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.pattern--off {
  opacity: 0.6;
}
.pattern__name {
  font-size: 14px;
  color: var(--text-primary);
}
.pattern__evidence {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--text-secondary);
}
.target__type {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.target__word {
  font-size: 18px;
  line-height: 26px;
  font-weight: 600;
  color: var(--text-heading);
}
.target__text {
  margin: 0;
  font-size: 15px;
  line-height: 22px;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.target__mark {
  border-radius: 4px;
  padding: 1px 2px;
  background: var(--cat-bully-bg);
  border-bottom: 2px solid var(--cat-bully);
}
.guard {
  display: grid;
  gap: 4px;
}
.guard__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.guard__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.guard__word {
  color: var(--text-primary);
  overflow-wrap: anywhere;
}
.guard__inner {
  text-decoration: underline wavy var(--warning);
  text-underline-offset: 3px;
}
.guard__sentence {
  margin: 0;
  font-size: 14px;
  line-height: 20px;
}
@media (max-width: 1279px) {
  .evidence__pair {
    grid-template-columns: 1fr;
  }
}
</style>
