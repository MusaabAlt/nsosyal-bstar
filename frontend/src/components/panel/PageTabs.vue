<script setup lang="ts">
/* Header tabs (the NSosyal "Akış / Medya" style), rendered into the shell header. */
defineProps<{ tabs: Array<{ key: string; label: string }>; modelValue: string }>()
defineEmits<{ 'update:modelValue': [key: string] }>()
</script>

<template>
  <Teleport defer to="#page-tabs">
    <div class="tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        class="tab"
        :class="{ 'tab--active': tab.key === modelValue }"
        :aria-selected="tab.key === modelValue"
        @click="$emit('update:modelValue', tab.key)"
      >
        {{ tab.label }}
        <span class="tab__bar" />
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.tabs {
  display: flex;
  align-items: stretch;
  height: var(--header-height);
}
.tab {
  position: relative;
  height: var(--header-height);
  padding: 0 20px;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-muted);
  white-space: nowrap;
  transition: color 0.15s;
}
.tab:hover {
  color: var(--text-primary);
}
.tab--active {
  font-weight: 600;
  color: var(--accent);
}
.tab__bar {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  width: 50%;
  height: 3px;
  border-radius: var(--radius-full);
  background: transparent;
}
.tab--active .tab__bar {
  background: var(--accent);
}
</style>
