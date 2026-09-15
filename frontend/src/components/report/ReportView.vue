<script setup lang="ts">
import { computed } from 'vue'
import VerdictBlock from '@/components/ui/VerdictBlock.vue'
import ComparisonPair from '@/components/ui/ComparisonPair.vue'
import StageInput from './StageInput.vue'
import StagePatterns from './StagePatterns.vue'
import StageNormalization from './StageNormalization.vue'
import StageContent from './StageContent.vue'
import StageTarget from './StageTarget.vue'
import StageGuards from './StageGuards.vue'
import StageThread from './StageThread.vue'
import StageReason from './StageReason.vue'
import { buildStages, verdictView } from '@/report/model'
import type { AnalysisResult } from '@/contract/types'
import { NO_EXTRAS, type Extras } from '@/api/source'

/*
 * pages-spec 2.3: verdict and latency at the top, then the comparison pair,
 * then the nine stages in the order the pipeline ran.
 */
const props = defineProps<{ result: AnalysisResult; extras?: Extras }>()

const verdict = computed(() => verdictView(props.result, props.extras ?? NO_EXTRAS))
const stages = computed(() => buildStages(props.result, props.extras ?? NO_EXTRAS))
</script>

<template>
  <div class="report">
    <VerdictBlock :view="verdict" :latency-ms="result.latency_ms" />
    <ComparisonPair />
    <div class="report__stages">
      <template v-for="stage in stages" :key="stage.number">
        <StageInput v-if="stage.kind === 'input'" :stage="stage" />
        <StagePatterns v-else-if="stage.kind === 'charsafe' || stage.kind === 'obfuscation'" :stage="stage" />
        <StageNormalization v-else-if="stage.kind === 'normalization'" :stage="stage" />
        <StageContent v-else-if="stage.kind === 'content'" :stage="stage" />
        <StageTarget v-else-if="stage.kind === 'target'" :stage="stage" />
        <StageGuards v-else-if="stage.kind === 'guards'" :stage="stage" />
        <StageThread v-else-if="stage.kind === 'thread'" :stage="stage" />
        <StageReason v-else-if="stage.kind === 'reason'" :stage="stage" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.report {
  display: flex;
  flex-direction: column;
}
.report > .comparison {
  margin-top: 24px;
}
</style>
