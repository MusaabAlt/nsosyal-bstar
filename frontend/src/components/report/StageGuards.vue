<script setup lang="ts">
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import { contentLabel, guardLabel } from '@/contract/labels'
import { codePointLength, isValidSpan, sliceSpan, type Mark } from '@/lib/spans'
import { copy } from '@/copy'
import type { GuardView, GuardsStage } from '@/report/model'

/*
 * pages-spec stage 7, moment B: the deliberate silence. It carries more
 * visual weight than stage 3. For each active guard: its Turkish name and a
 * sentence naming what it prevented. For substring collision, the innocent
 * word is rendered in evidence text with the suppressed substring underlined
 * inside it, and a sentence says the system recognised the containing word
 * and chose not to flag it.
 *
 * Everything comes from the payload: the guard's span and evidence, and the
 * span of each suppressed content entry.
 */
defineProps<{ stage: GuardsStage }>()

interface Word {
  text: string
  marks: Mark[]
}

/** The guard's own span as the word, with suppressed spans underlined relative to it. */
function containingWord(view: GuardView, text: string): Word | null {
  const span = view.guard.span
  if (!isValidSpan(span, codePointLength(text))) return null
  const marks: Mark[] = []
  // Underline is reserved for a profane substring inside an innocent word (4.13).
  if (view.guard.code !== 'SUBSTRING_COLLISION') return { text: sliceSpan(text, span), marks }
  for (const entry of view.suppressedEntries) {
    const inner = entry.span
    if (inner && inner[0] >= span[0] && inner[1] <= span[1]) {
      marks.push({ span: [inner[0] - span[0], inner[1] - span[0]], kind: 'underline' })
    }
  }
  return { text: sliceSpan(text, span), marks }
}

function suppressedList(view: GuardView): string {
  return view.guard.suppressed.map((code) => `'${contentLabel(code)}' (${code})`).join(', ')
}
</script>

<template>
  <!-- Stage 7 carries more visual weight than stage 3: even its "none" line is body text, not a muted note. -->
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status">
    <p v-if="stage.active.length === 0 && stage.line" class="stage-guards__sentence">{{ stage.line }}</p>
    <div v-if="stage.active.length > 0" class="stage-guards">
      <article v-for="(view, i) in stage.active" :key="`${view.guard.code}-${i}`" class="stage-guards__item">
        <h4 class="stage-guards__name">{{ guardLabel(view.guard.code) }}</h4>
        <p class="stage-guards__sentence">
          {{ copy.stages.guardPrevented(guardLabel(view.guard.code), suppressedList(view)) }}
        </p>
        <div v-if="containingWord(view, stage.text)" class="stage-guards__word">
          <EvidenceText
            :text="containingWord(view, stage.text)!.text"
            :marks="containingWord(view, stage.text)!.marks"
          />
        </div>
        <p v-else-if="view.guard.evidence" class="stage-guards__sentence">{{ view.guard.evidence }}</p>
        <p v-if="view.guard.code === 'SUBSTRING_COLLISION'" class="stage-guards__sentence">
          {{ copy.stages.guardDeliberate }}
        </p>
      </article>
    </div>
  </StageRow>
</template>

<style scoped>
.stage-guards {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.stage-guards__item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stage-guards__name {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text-primary);
}
.stage-guards__sentence {
  margin: 0;
  max-width: 80ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.stage-guards__word {
  align-self: flex-start;
}
</style>
