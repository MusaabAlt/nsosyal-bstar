<script setup lang="ts">
import StageRow from '@/components/ui/StageRow.vue'
import { copy } from '@/copy'
import type { ReasonStage } from '@/report/model'

/*
 * pages-spec stage 9: not a second verdict. It names the stages above that
 * produced the outcome, so the conclusion is traceable to something visible,
 * and repeats the decision layer's sentence verbatim.
 */
defineProps<{ stage: ReasonStage }>()
</script>

<template>
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status" :line="stage.line">
    <p v-if="stage.triggeredStages.length > 0" class="stage-reason__text">
      {{ copy.stages.reasonStages }}: {{ stage.triggeredStages.join(', ') }}.
    </p>
    <p class="stage-reason__text">{{ stage.explanation }}</p>
  </StageRow>
</template>

<style scoped>
.stage-reason__text {
  margin: 0;
  max-width: 80ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.stage-reason__text + .stage-reason__text {
  margin-top: 8px;
}
</style>
