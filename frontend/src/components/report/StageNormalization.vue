<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import ScorePair from '@/components/ui/ScorePair.vue'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import { copy } from '@/copy'
import type { NormalizationStage } from '@/report/model'

/*
 * pages-spec stage 4, the most persuasive moment: it gets room.
 *
 * Three elements stacked:
 *   1. the original string, removed or substituted characters highlighted
 *   2. one line stating what changed ("4 ayırıcı karakter kaldırıldı")
 *   3. the recovered string, the recovered characters highlighted
 * then the score pair (raw vs recovered) when the API supplies both scores.
 *
 * The recovered string and its changes come from m2's optional
 * normalization; the counts in the line come from the server. Nothing is
 * reconstructed here.
 */
const props = defineProps<{ stage: NormalizationStage }>()

const originalMarks = computed<Mark[]>(() => {
  const length = codePointLength(props.stage.text)
  const n = props.stage.normalization
  const spans = n ? n.changes.map((c) => c.from_span) : props.stage.patterns.map((p) => p.span)
  return spans.filter((s) => isValidSpan(s, length)).map((span) => ({ span: span!, kind: 'highlight' as const }))
})

const recoveredMarks = computed<Mark[]>(() => {
  const n = props.stage.normalization
  if (!n) return []
  const length = codePointLength(n.text)
  return n.changes
    .map((c) => c.to_span)
    .filter((s) => isValidSpan(s, length))
    .map((span) => ({ span: span!, kind: 'highlight' as const }))
})

const changeLines = computed(() => {
  const s = props.stage.changeSummary
  if (!props.stage.normalization) return []
  if (!s || (s.removed === 0 && s.replaced === 0)) return [copy.stages.noChanges]
  const lines: string[] = []
  if (s.removed > 0) lines.push(copy.stages.removedChars(s.removed))
  if (s.replaced > 0) lines.push(copy.stages.replacedChars(s.replaced))
  return lines
})

const hasBody = computed(() => props.stage.normalization || props.stage.scorePair || originalMarks.value.length > 0)
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :line="stage.normalization ? null : stage.line"
  >
    <div v-if="hasBody" class="stage-normalization">
      <EvidenceText v-if="stage.normalization || originalMarks.length > 0" :text="stage.text" :marks="originalMarks" />
      <template v-if="stage.normalization">
        <p v-for="line in changeLines" :key="line" class="stage-normalization__change">{{ line }}</p>
        <EvidenceText :text="stage.normalization.text" :marks="recoveredMarks" />
      </template>
      <p v-else-if="stage.status !== 'moduleUnavailable'" class="stage-normalization__missing">
        {{ copy.stages.normalizationMissing }}
      </p>
      <ScorePair v-if="stage.scorePair" class="stage-normalization__pair" :pair="stage.scorePair" />
    </div>
  </StageRow>
</template>

<style scoped>
.stage-normalization {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}
.stage-normalization__change {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.stage-normalization__missing {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}
.stage-normalization__pair {
  margin-top: 12px;
}
</style>
