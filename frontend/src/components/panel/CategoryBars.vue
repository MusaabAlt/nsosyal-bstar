<script setup lang="ts">
import { computed } from 'vue'
import { formatCount, formatPercent } from '@/lib/format'

/*
 * The distribution of detected categories as horizontal bars. A bar chart,
 * not a pie: fifteen categories and a projector at the back of a room.
 * Every count comes from the server; the share is the bar's length only and
 * is shown as a number the server can confirm (count / total of the bars).
 */
export interface BarDatum {
  code: string
  label: string
  value: number
  color: string
  ink: string
}

const props = defineProps<{ data: BarDatum[] }>()

const peak = computed(() => {
  let top = 0
  for (const d of props.data) if (d.value > top) top = d.value
  return top
})

const total = computed(() => {
  let sum = 0
  for (const d of props.data) sum += d.value
  return sum
})

function width(value: number): string {
  return peak.value > 0 ? `${Math.max(1.5, (value / peak.value) * 100)}%` : '0%'
}

function share(value: number): string | null {
  return total.value > 0 ? formatPercent((value / total.value) * 100) : null
}
</script>

<template>
  <ul class="bars">
    <li v-for="d in data" :key="d.code" class="bar">
      <span class="mono bar__code" :style="{ color: d.ink }">{{ d.code }}</span>
      <span class="bar__label" :title="d.label">{{ d.label }}</span>
      <span class="bar__track">
        <span class="bar__fill" :style="{ width: width(d.value), background: d.color }" />
      </span>
      <span class="num bar__value">{{ formatCount(d.value) }}</span>
      <span class="num bar__share">{{ share(d.value) }}</span>
    </li>
  </ul>
</template>

<style scoped>
.bars {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.bar {
  display: grid;
  grid-template-columns: 30px minmax(0, 150px) 1fr 52px 54px;
  align-items: center;
  gap: 10px;
}
.bar__code {
  font-size: 12px;
  font-weight: 700;
}
.bar__label {
  font-size: 13px;
  line-height: 18px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bar__track {
  height: 10px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  overflow: hidden;
}
.bar__fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.4s ease-out;
}
.bar__value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
  text-align: right;
}
.bar__share {
  font-size: 12px;
  color: var(--text-meta);
  text-align: right;
}
@media (max-width: 1279px) {
  .bar {
    grid-template-columns: 28px minmax(0, 110px) 1fr 46px;
  }
  .bar__share {
    display: none;
  }
}
</style>
