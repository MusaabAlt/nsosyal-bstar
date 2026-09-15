<script setup lang="ts">
/*
 * design-system 4.16: 2px, full width, --surface-hover track, filled with the
 * NSosyal brand gradient. The only gradient in the application, and the only
 * motion prefers-reduced-motion keeps. No spinners exist in this system.
 */
defineProps<{ label: string }>()
</script>

<template>
  <v-progress-linear
    class="progress-indicator"
    indeterminate
    :height="2"
    :rounded="false"
    role="progressbar"
    :aria-label="label"
  />
</template>

<style scoped>
.progress-indicator {
  background: var(--surface-hover);
}
.progress-indicator :deep(.v-progress-linear__background) {
  background: var(--surface-hover);
  opacity: 1;
}
.progress-indicator :deep(.v-progress-linear__indeterminate) {
  background: transparent;
}
.progress-indicator :deep(.v-progress-linear__indeterminate .long),
.progress-indicator :deep(.v-progress-linear__indeterminate .short) {
  background: var(--progress-gradient);
}
</style>
