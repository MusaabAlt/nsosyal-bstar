<script setup lang="ts">
import { copy } from '@/copy'

/*
 * design-system 4.19: shown while mock data is rendered. Removed by one flag
 * (AnalysisSource.representative) when real data is wired.
 */
</script>

<template>
  <div class="demo-marker" role="status">{{ copy.app.demoMarker }}</div>
</template>

<style scoped>
.demo-marker {
  position: fixed;
  right: 32px;
  bottom: 32px;
  z-index: 10;
  padding: 8px;
  border: 1px solid var(--status-review);
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--status-review);
  font-size: 12px;
  line-height: 1.4;
}
</style>
