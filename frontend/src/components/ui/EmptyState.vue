<script setup lang="ts">
/* design-system 4.17: one line stating plainly what is absent. No illustration, icon or heading. */
defineProps<{ line: string }>()
</script>

<template>
  <div class="empty-state">
    <p class="empty-state__line">{{ line }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty-state__line {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}
.empty-state :slotted(*) {
  margin-top: 12px;
}
</style>
