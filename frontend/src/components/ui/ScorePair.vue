<script setup lang="ts">
import { formatScore } from '@/lib/format'
import { copy } from '@/copy'
import type { ScorePairView } from '@/report/model'

/*
 * design-system 4.10: the model's score on the raw text and on the recovered
 * text. Rendered only when the API supplies both; never computed. The right
 * number is --status-block when the decision layer marked that channel fired.
 */
defineProps<{ pair: ScorePairView }>()
</script>

<template>
  <div class="score-pair">
    <div class="score-pair__item">
      <span class="score-pair__value score-pair__value--raw">{{ formatScore(pair.raw.score) }}</span>
      <span class="score-pair__label">{{ copy.stages.rawText }}</span>
    </div>
    <span class="score-pair__arrow" aria-hidden="true">→</span>
    <div class="score-pair__item">
      <span class="score-pair__value" :class="{ 'score-pair__value--fired': pair.normalized.fired === true }">
        {{ formatScore(pair.normalized.score) }}
      </span>
      <span class="score-pair__label">{{ copy.stages.recoveredText }}</span>
    </div>
  </div>
</template>

<style scoped>
.score-pair {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}
.score-pair__item {
  display: flex;
  flex-direction: column;
}
.score-pair__value {
  font-size: 32px;
  font-weight: 500;
  line-height: 1.2;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.score-pair__value--raw {
  color: var(--text-muted);
}
.score-pair__value--fired {
  color: var(--status-block);
}
.score-pair__label {
  font-size: 14px;
  color: var(--text-muted);
}
.score-pair__arrow {
  font-size: 24px;
  line-height: 38px;
  color: var(--text-muted);
}
</style>
