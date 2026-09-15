<script setup lang="ts">
import { STATUS_WORD, type StatusKey } from '@/report/model'

/*
 * design-system 4.7. Status is a word, optionally preceded by a 6px dot;
 * never a dot alone, never a filled pill. "modül hazır değil" and "veri yok"
 * are distinct and never merged.
 */
defineProps<{ status: StatusKey }>()
</script>

<template>
  <span class="status-word" :class="`status-word--${status}`">
    <span class="status-word__dot" aria-hidden="true" />{{ STATUS_WORD[status] }}
  </span>
</template>

<style scoped>
.status-word {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
}
.status-word__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.status-word--passed {
  color: var(--status-clean);
}
.status-word--triggered {
  color: var(--status-block);
}
.status-word--below,
.status-word--notApplied {
  color: var(--status-neutral);
}
.status-word--moduleUnavailable,
.status-word--noData {
  color: var(--status-incomplete);
  font-style: italic;
}
</style>
