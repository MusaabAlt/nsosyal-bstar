<script setup lang="ts">
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'
import { formatChange, formatCount } from '@/lib/format'

/* One KPI tile. The value, the share and the change all arrive computed by the server. */
const props = defineProps<{
  icon: IconName
  label: string
  value: number | null | undefined
  /** A preformatted value, used instead of `value` (e.g. "38,0 ms"). */
  text?: string | null
  sub?: string | null
  /** Percent change against the previous stretch; null when there is nothing to compare with. */
  change?: number | null
  /** Text shown instead of the change chip when change is null. */
  noChange?: string
  /** Colour the change chip as good when it goes down (latency, errors). */
  lowerIsBetter?: boolean
}>()

const shown = computed(() => (props.text !== undefined ? props.text : formatCount(props.value)))
const changeText = computed(() => formatChange(props.change))
const good = computed(() => {
  if (typeof props.change !== 'number' || props.change === 0) return false
  return props.lowerIsBetter ? props.change < 0 : props.change > 0
})
</script>

<template>
  <div class="card card--tight kpi">
    <div class="kpi__label">
      <Icon :name="icon" :size="16" :stroke="1.8" />
      <span>{{ label }}</span>
    </div>
    <div class="kpi__value-row">
      <span v-if="shown !== null" class="kpi__value num">{{ shown }}</span>
      <span v-else class="kpi__value unavailable">—</span>
      <span v-if="sub" class="meta">{{ sub }}</span>
    </div>
    <span v-if="changeText !== null" class="chip kpi__change" :class="{ 'kpi__change--good': good }">{{ changeText }}</span>
    <span v-else-if="noChange" class="chip kpi__change">{{ noChange }}</span>
  </div>
</template>

<style scoped>
.kpi__label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 20px;
}
.kpi__value-row {
  margin-top: 12px;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}
.kpi__value {
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--text-heading);
}
.kpi__change {
  margin-top: 12px;
}
.kpi__change--good {
  background: var(--cat-clean-bg);
  color: var(--mint);
}
</style>
