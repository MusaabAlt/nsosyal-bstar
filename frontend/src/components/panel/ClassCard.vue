<script setup lang="ts">
import { computed } from 'vue'
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'
import { copy } from '@/copy'
import { formatCount } from '@/lib/format'

/*
 * One moderation class (a content-code family) with every category the
 * contract defines inside it.
 *
 * A row's total is null when the AI does not produce that code yet
 * (AI/serving/capabilities.py does not list it), which is not the same as
 * zero: zero means the code was looked for and not found. Those rows show a
 * dash, carry no bar and are left out of the class total, so the card never
 * claims a measurement that was never taken.
 *
 * Each count arrives from the server; the class total is the plain sum of the
 * measured counts, which is display arithmetic, not a decision.
 */
export interface ClassRow {
  code: string
  label: string
  /** null: the AI does not produce this code today. */
  total: number | null
}

const props = defineProps<{
  title: string
  icon: IconName
  color: string
  ink: string
  tint: string
  rows: ClassRow[]
}>()

const measured = computed(() => props.rows.filter((row) => row.total !== null))
const pending = computed(() => props.rows.length - measured.value.length)

/** null when no code in this class is produced yet: there is nothing to total. */
const total = computed(() => {
  if (measured.value.length === 0) return null
  let sum = 0
  for (const row of measured.value) sum += row.total!
  return sum
})

/** The widest measured row in this card, so the bars compare inside the class. */
const peak = computed(() => {
  let top = 0
  for (const row of measured.value) if (row.total! > top) top = row.total!
  return top
})

function width(value: number): string {
  return peak.value > 0 ? `${Math.round((value / peak.value) * 100)}%` : '0%'
}
</script>

<template>
  <section class="card card--tight klass" :class="{ 'klass--pending': total === null }">
    <header class="klass__head">
      <span class="klass__icon" :style="{ background: tint, color: ink }">
        <Icon :name="icon" :size="18" />
      </span>
      <h3 class="klass__title">{{ title }}</h3>
    </header>

    <div v-if="total !== null" class="klass__total num">{{ formatCount(total) }}</div>
    <div v-else class="klass__total klass__total--pending">—</div>
    <div class="meta klass__unit">{{ total === null ? copy.overview.classPending : copy.overview.classTotal }}</div>

    <ul class="klass__rows">
      <li
        v-for="row in rows"
        :key="row.code"
        class="klass__row"
        :class="{ 'klass__row--pending': row.total === null }"
      >
        <span class="mono klass__code" :style="row.total === null ? undefined : { color: ink }">{{ row.code }}</span>
        <span class="klass__label" :title="row.label">{{ row.label }}</span>
        <span v-if="row.total !== null" class="num klass__count">{{ formatCount(row.total) }}</span>
        <span v-else class="klass__count klass__count--pending" :title="copy.overview.classPendingRow">—</span>
        <span v-if="row.total !== null" class="klass__bar">
          <span class="klass__fill" :style="{ width: width(row.total), background: color }" />
        </span>
      </li>
    </ul>

    <p v-if="total === null" class="meta klass__note">{{ copy.overview.classPendingNote }}</p>
    <p v-else-if="pending > 0" class="meta klass__note">{{ copy.overview.classPartial(formatCount(pending)!) }}</p>
  </section>
</template>

<style scoped>
.klass {
  display: flex;
  flex-direction: column;
}
.klass--pending .klass__icon {
  opacity: 0.55;
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
.klass__total--pending {
  color: var(--text-meta);
  font-weight: 500;
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
.klass__row--pending .klass__code,
.klass__row--pending .klass__label {
  color: var(--text-meta);
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
.klass__count--pending {
  color: var(--text-meta);
  font-weight: 500;
  cursor: help;
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
