<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import { targetLabel } from '@/contract/labels'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import type { TargetStage } from '@/report/model'

/* pages-spec stage 6: target type in Turkish and the evidence highlighted in position. */
const props = defineProps<{ stage: TargetStage }>()

const marks = computed<Mark[]>(() => {
  const span = props.stage.target?.span
  return isValidSpan(span, codePointLength(props.stage.text)) ? [{ span, kind: 'highlight' }] : []
})
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :duration-ms="stage.durationMs"
    :line="stage.line"
  >
    <template v-if="stage.target && stage.target.type !== 'none'">
      <p class="stage-target__type">{{ targetLabel(stage.target.type) }}</p>
      <EvidenceText v-if="marks.length > 0" :text="stage.text" :marks="marks" />
      <p v-else class="stage-target__evidence">{{ stage.target.evidence }}</p>
    </template>
  </StageRow>
</template>

<style scoped>
.stage-target__type {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}
.stage-target__evidence {
  margin: 0;
  font-size: 14px;
  color: var(--text-body);
}
</style>
