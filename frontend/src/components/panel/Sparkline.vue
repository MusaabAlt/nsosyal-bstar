<script setup lang="ts">
import { computed } from 'vue'

/* A small count trend. Geometry only: the points are scaled to the drawing, no number is shown. */
const props = defineProps<{ values: number[]; color: string }>()

const points = computed(() => {
  const vals = props.values
  const top = Math.max(1, ...vals)
  const step = vals.length > 1 ? 120 / (vals.length - 1) : 0
  return vals.map((v, i) => `${(i * step).toFixed(1)},${(30 - (v / top) * 26).toFixed(1)}`).join(' ')
})
</script>

<template>
  <svg width="100%" height="32" viewBox="0 0 120 32" preserveAspectRatio="none" fill="none" class="spark" aria-hidden="true">
    <polyline
      v-if="values.length > 1"
      :points="points"
      :stroke="color"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      vector-effect="non-scaling-stroke"
    />
    <line v-else x1="0" y1="30" x2="120" y2="30" :stroke="color" stroke-width="2" vector-effect="non-scaling-stroke" />
  </svg>
</template>

<style scoped>
.spark {
  display: block;
}
</style>
