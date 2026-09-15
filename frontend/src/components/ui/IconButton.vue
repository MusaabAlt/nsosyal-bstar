<script setup lang="ts">
/*
 * design-system 4.2: 28x28, transparent, inline SVG icon at 16px, requires
 * aria-label. Used only in the mock social post interaction row.
 */
defineProps<{ label: string }>()
</script>

<template>
  <button type="button" class="icon-button" :aria-label="label">
    <slot />
  </button>
</template>

<style scoped>
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background-color var(--motion-fast);
}
.icon-button:hover {
  background: var(--surface-hover);
}
.icon-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.icon-button :slotted(svg) {
  width: 16px;
  height: 16px;
}
</style>
