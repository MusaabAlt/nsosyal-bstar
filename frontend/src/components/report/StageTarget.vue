<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import { copy } from '@/copy'
import type { TargetStage } from '@/report/model'

/*
 * pages-spec stage 6: target type in Turkish (birey, grup, insan dışı, yok)
 * and the evidence substring that identified it, highlighted in position.
 */
const props = defineProps<{ stage: TargetStage }>()

const marks = computed<Mark[]>(() => {
  const span = props.stage.target?.span
  return isValidSpan(span, codePointLength(props.stage.text)) ? [{ span, kind: 'highlight' }] : []
})

const word = computed(() => (props.stage.target ? (copy.stages.targetWords[props.stage.target.type] ?? props.stage.target.type) : null))
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :duration-ms="stage.durationMs"
    :line="stage.target ? null : stage.line"
  >
    <template v-if="stage.target">
      <p class="stage-target__type">{{ word }}</p>
      <EvidenceText v-if="marks.length > 0" :text="stage.text" :marks="marks" />
    </template>
  </StageRow>
</template>

<style scoped>
.stage-target__type {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}
</style>
