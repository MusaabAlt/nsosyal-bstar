<script setup lang="ts">
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'
import { copy } from '@/copy'
import { formatCount } from '@/lib/format'

/*
 * One moderation class (a content-code family, or the model's general
 * offensive signal) with the count of every category inside it. Each count
 * arrives from the server; the family total is the plain sum of those counts,
 * which is display arithmetic, not a decision.
 */
export interface ClassRow {
  code: string
  label: string
  total: number
}

const props = defineProps<{
  title: string
  icon: IconName
  color: string
  ink: string
  tint: string
  rows: ClassRow[]
}>()

const total = computed(() => {
  let sum = 0
  for (const row of props.rows) sum += row.total
  return sum
})

/** The widest row in this card, so the bars compare inside the class. */
const peak = computed(() => {
  let top = 0
  for (const row of props.rows) if (row.total > top) top = row.total
  return top
})

function width(value: number): string {
  return peak.value > 0 ? `${Math.round((value / peak.value) * 100)}%` : '0%'
}
</script>

<template>
  <section class="card card--tight klass">
    <header class="klass__head">
      <span class="klass__icon" :style="{ background: tint, color: ink }">
        <Icon :name="icon" :size="18" />
      </span>
      <h3 class="klass__title">{{ title }}</h3>
    </header>

    <div class="klass__total num">{{ formatCount(total) }}</div>
    <div class="meta klass__unit">{{ copy.overview.classTotal }}</div>

    <ul class="klass__rows">
      <li v-for="row in rows" :key="row.code" class="klass__row">
        <span class="mono klass__code" :style="{ color: ink }">{{ row.code }}</span>
        <span class="klass__label" :title="row.label">{{ row.label }}</span>
        <span class="num klass__count">{{ formatCount(row.total) }}</span>
        <span class="klass__bar"><span class="klass__fill" :style="{ width: width(row.total), background: color }" /></span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.klass {
  display: flex;
  flex-direction: column;
}
.klass__head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.klass__icon {
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}
.klass__title {
  margin: 0;
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.klass__total {
  margin-top: 14px;
  font-size: 32px;
  line-height: 38px;
  font-weight: 700;
  color: var(--text-heading);
}
.klass__unit {
  font-size: 12px;
}
.klass__rows {
  list-style: none;
  margin: 14px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid var(--border-card);
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex: 1;
}
.klass__row {
  display: grid;
  grid-template-columns: 26px 1fr auto;
  align-items: center;
  column-gap: 8px;
  row-gap: 4px;
}
.klass__code {
  font-size: 12px;
  font-weight: 700;
}
.klass__label {
  font-size: 12px;
  line-height: 16px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.klass__count {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-heading);
}
.klass__bar {
  grid-column: 1 / -1;
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  overflow: hidden;
}
.klass__fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-full);
}
</style>
