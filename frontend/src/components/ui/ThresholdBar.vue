<script setup lang="ts">
import { computed } from 'vue'
import { formatScore } from '@/lib/format'
import { copy } from '@/copy'

/*
 * design-system 4.9: one category against ITS OWN threshold. Never an
 * aggregate, an average or a global threshold.
 *
 *   Above the bar: category label left; score right, in the fill colour.
 *   The bar: 4px track, fill proportional to the score, --status-block when
 *            the category fired, --status-neutral when it did not.
 *   The tick: 2px wide, 10px tall at the threshold's own position.
 *   Under the tick: "eşik 0.62".
 *   Beneath: one sentence, "Skor kendi eşiğini 0.32 puan aşıyor".
 *
 * `fired` is the decision layer's. `margin` (score minus threshold) is
 * computed by the server and only formatted here; this component compares
 * nothing (design-system 6).
 */
const props = defineProps<{
  label: string
  score: number
  threshold: number | null
  fired: boolean | null
  margin: number | null
  /** Set when an active guard suppressed this code. */
  suppressedBy?: string | null
}>()

/** Bar geometry only: the position on a 0-1 track. Not a displayed number. */
function position(value: number): string {
  return `${Math.min(Math.max(value, 0), 1) * 100}%`
}

const scoreText = computed(() => formatScore(props.score))
const thresholdText = computed(() => formatScore(props.threshold))
const sentence = computed(() => {
  if (props.suppressedBy) return copy.stages.suppressedSentence(props.suppressedBy)
  const points = props.margin === null ? null : formatScore(Math.abs(props.margin))
  if (props.fired === true) return points !== null ? copy.stages.marginAbove(points) : copy.stages.firedSentence
  if (props.fired === false) {
    return points !== null && props.margin !== null && props.margin < 0
      ? copy.stages.marginBelow(points)
      : copy.stages.notFiredSentence
  }
  return copy.stages.undecidedSentence
})
</script>

<template>
  <div class="threshold-bar" :class="{ 'threshold-bar--fired': fired === true }">
    <div class="threshold-bar__top">
      <span class="threshold-bar__label">{{ label }}</span>
      <span class="threshold-bar__score">{{ scoreText ?? copy.status.noData }}</span>
    </div>

    <div
      class="threshold-bar__track"
      role="img"
      :aria-label="`${label}: ${scoreText ?? copy.status.noData}, ${copy.stages.thresholdPrefix} ${thresholdText ?? copy.stages.thresholdMissing}`"
    >
      <div class="threshold-bar__fill" :style="{ width: position(score) }" />
      <div v-if="threshold !== null" class="threshold-bar__tick" :style="{ left: position(threshold) }" />
    </div>

    <div class="threshold-bar__caption-row">
      <span
        v-if="thresholdText !== null && threshold !== null"
        class="threshold-bar__caption"
        :style="{ left: position(threshold) }"
      >
        {{ copy.stages.thresholdPrefix }} {{ thresholdText }}
      </span>
      <span v-else class="threshold-bar__caption threshold-bar__caption--missing">{{ copy.stages.thresholdMissing }}</span>
    </div>

    <p class="threshold-bar__sentence">{{ sentence }}</p>
  </div>
</template>

<style scoped>
.threshold-bar {
  --fill: var(--status-neutral);
}
.threshold-bar--fired {
  --fill: var(--status-block);
}
.threshold-bar__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 8px;
}
.threshold-bar__label {
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-primary);
}
.threshold-bar__score {
  font-size: 15px;
  font-weight: 500;
  color: var(--fill);
  font-variant-numeric: tabular-nums;
}
.threshold-bar__track {
  position: relative;
  height: 4px;
  background: var(--surface-hover);
  border-radius: 0;
}
.threshold-bar__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--fill);
}
/* 2px wide, 10px tall, 3px above and below the 4px track: clearly a separate object. */
.threshold-bar__tick {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 10px;
  margin-left: -1px;
  background: var(--text-primary);
}
.threshold-bar__caption-row {
  position: relative;
  height: 20px;
  margin-top: 4px;
}
.threshold-bar__caption {
  position: absolute;
  transform: translateX(-50%);
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.threshold-bar__caption--missing {
  position: static;
  transform: none;
  font-style: italic;
}
.threshold-bar__sentence {
  margin: 4px 0 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-body);
}
</style>
