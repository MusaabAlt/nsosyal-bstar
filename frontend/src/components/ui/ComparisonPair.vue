<script setup lang="ts">
import { copy } from '@/copy'

/*
 * design-system 4.14: a plain keyword filter and this system, side by side.
 * Not yet built. The space is reserved and both columns render
 * "modül hazır değil" until the baseline filter exists. No baseline verdict
 * is ever fabricated.
 */
const columns = [copy.comparison.keyword, copy.comparison.ours]
</script>

<template>
  <div class="comparison">
    <div v-for="label in columns" :key="label" class="comparison__col">
      <span class="comparison__label">{{ label }}</span>
      <span class="comparison__word">{{ copy.status.moduleUnavailable }}</span>
    </div>
  </div>
</template>

<style scoped>
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border-divider);
}
.comparison__col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 24px 16px 0;
}
.comparison__col + .comparison__col {
  padding-left: 24px;
  border-left: 1px solid var(--border-default);
}
.comparison__label {
  font-size: 14px;
  color: var(--text-muted);
}
/* 4.7: "modül hazır değil" is --status-incomplete, italic. */
.comparison__word {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
  font-style: italic;
  color: var(--status-incomplete);
}
</style>
