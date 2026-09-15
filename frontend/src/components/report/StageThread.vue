<script setup lang="ts">
import StageRow from '@/components/ui/StageRow.vue'
import { copy } from '@/copy'
import type { ThreadStage } from '@/report/model'

/*
 * pages-spec stage 8. The API accepts no thread block today, so for a single
 * post the status is "uygulanmadı" with one line explaining it. When a thread
 * signal exists, the repeat count is shown exactly as the payload carries it.
 */
defineProps<{ stage: ThreadStage }>()
</script>

<template>
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status" :line="stage.line">
    <p v-if="stage.thread" class="stage-thread__count">
      {{ copy.stages.repeatCount }}: <span class="stage-thread__value">{{ stage.thread.repeat_count }}</span>
    </p>
  </StageRow>
</template>

<style scoped>
.stage-thread__count {
  margin: 0;
  font-size: 14px;
  color: var(--text-body);
}
.stage-thread__value {
  font-weight: 500;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
</style>
