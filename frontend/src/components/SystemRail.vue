<script setup lang="ts">
import { computed } from 'vue'
import Icon from './Icon.vue'
import type { IconName } from './icons'
import { copy } from '@/copy'
import { formatCount, formatMs } from '@/lib/format'
import { liveOverview } from '@/composables/useLiveOverview'

/* Sistem durumu: model version, recent latency, active devices and live engines, all from the live overview. */
const rows = computed<Array<{ icon: IconName; label: string; value: string | null }>>(() => {
  const s = liveOverview.value?.system
  const p95 = formatMs(s?.latency_p95_ms)
  return [
    { icon: 'cpu', label: copy.panel.system.model, value: s?.artifact_hash ? s.artifact_hash.slice(0, 8) : null },
    { icon: 'activity', label: copy.panel.system.latency, value: p95 === null ? null : `${p95} ms` },
    { icon: 'wifi', label: copy.panel.system.devices, value: formatCount(s?.active_devices) },
    {
      icon: 'brain',
      label: copy.panel.system.engines,
      value: s ? `${s.live_categories} / ${s.total_categories}` : null,
    },
  ]
})
</script>

<template>
  <aside class="card">
    <h3 class="card__title rail__title">{{ copy.app.systemStatus }}</h3>
    <div v-for="row in rows" :key="row.label" class="rail__row">
      <Icon :name="row.icon" class="rail__icon" />
      <span class="rail__label">{{ row.label }}</span>
      <span v-if="row.value !== null" class="mono num rail__value">{{ row.value }}</span>
      <span v-else class="rail__value unavailable">{{ copy.panel.unavailable }}</span>
    </div>
  </aside>
</template>

<style scoped>
.rail__title {
  margin-bottom: 4px;
}
.rail__row {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 50px;
  border-bottom: 1px solid var(--border-divider);
}
.rail__row:last-child {
  border-bottom: 0;
}
.rail__icon {
  color: var(--text-muted);
}
.rail__label {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rail__value {
  color: var(--text-heading);
  font-size: 13px;
}
</style>
