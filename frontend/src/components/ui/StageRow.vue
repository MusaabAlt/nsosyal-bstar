<script setup lang="ts">
import { computed } from 'vue'
import StatusWord from './StatusWord.vue'
import { formatMs } from '@/lib/format'
import type { StatusKey } from '@/report/model'

/*
 * design-system 4.8. Full width, no card, no radius, no background, 1px
 * divider beneath. A stage never collapses to nothing: when it has no
 * findings the caller passes `line`, so "ran and found nothing" is always
 * distinguishable from "did not run".
 */
const props = defineProps<{
  number: number
  name: string
  status: StatusKey | null
  durationMs?: number | null
  line?: string | null
  /** Stage 7 carries more visual weight than stage 3 (pages-spec). */
  emphasis?: boolean
}>()

const duration = computed(() => formatMs(props.durationMs))
const headingId = computed(() => `stage-${props.number}-heading`)
</script>

<template>
  <section class="stage-row" :class="{ 'stage-row--emphasis': emphasis }" :aria-labelledby="headingId">
    <header class="stage-row__header">
      <span class="stage-row__number">{{ number }}</span>
      <h3 :id="headingId" class="stage-row__name">{{ name }}</h3>
      <StatusWord v-if="status" :status="status" />
      <span v-if="duration !== null" class="stage-row__duration">
        {{ duration }}<span class="stage-row__unit"> ms</span>
      </span>
    </header>
    <div v-if="line || $slots.default" class="stage-row__body">
      <p v-if="line" class="stage-row__line">{{ line }}</p>
      <slot />
    </div>
  </section>
</template>

<style scoped>
.stage-row {
  padding: 16px 0;
  border-bottom: 1px solid var(--border-divider);
}
.stage-row__header {
  display: grid;
  grid-template-columns: 24px auto auto 1fr;
  align-items: baseline;
  column-gap: 12px;
}
.stage-row__number {
  font-size: 14px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.stage-row__name {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-primary);
}
.stage-row__duration {
  justify-self: end;
  font-size: 13px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.stage-row__body {
  margin-top: 12px;
  padding-left: 36px; /* indented to the stage name: 24px number column + 12px gap */
}
.stage-row__line {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}
.stage-row--emphasis {
  padding: 24px 0;
}
.stage-row--emphasis .stage-row__line {
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
</style>
