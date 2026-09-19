<script setup lang="ts">
import { computed } from 'vue'
import { copy } from '@/copy'
import type { CategoryStatus } from '@/api/panel'

const props = defineProps<{ status: CategoryStatus }>()
const color = computed(() =>
  props.status === 'live' ? 'var(--mint)' : props.status === 'stub' ? 'var(--warning)' : 'var(--text-muted)',
)
</script>

<template>
  <span class="status" :style="{ color }"><span class="chip__dot" />{{ copy.panel.status[status] }}</span>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
</style>
