<script setup lang="ts">
/*
 * design-system 4.6: 40px, full sidebar width, radius 0. Selected: surface
 * background, primary text and a 2px accent bar on the left edge, the only
 * left accent bar permitted anywhere in the system.
 */
defineProps<{ to: string; label: string }>()
</script>

<template>
  <RouterLink v-slot="{ href, navigate, isActive }" :to="to" custom>
    <a
      :href="href"
      class="nav-item"
      :class="{ 'nav-item--selected': isActive }"
      :aria-current="isActive ? 'page' : undefined"
      @click="navigate"
    >
      {{ label }}
    </a>
  </RouterLink>
</template>

<style scoped>
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  text-decoration: none;
  border-radius: 0;
  transition:
    background-color var(--motion-fast),
    color var(--motion-fast);
}
.nav-item:hover {
  background: var(--surface-hover);
  color: var(--text-body);
}
.nav-item--selected,
.nav-item--selected:hover {
  background: var(--surface-selected);
  color: var(--text-primary);
}
.nav-item--selected::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 2px;
  background: var(--accent);
}
.nav-item:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
</style>
