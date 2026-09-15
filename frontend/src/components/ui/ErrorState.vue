<script setup lang="ts">
import BaseButton from './BaseButton.vue'

/*
 * design-system 4.18: one line saying what failed in plain terms and one
 * secondary button naming the retry action. No red banner, no dialog, no
 * apology, no error code the operator cannot act on.
 */
defineProps<{ line: string; retryLabel: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="error-state" role="alert">
    <p class="error-state__line">{{ line }}</p>
    <BaseButton variant="secondary" @click="$emit('retry')">{{ retryLabel }}</BaseButton>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  padding: 24px 0;
}
.error-state__line {
  margin: 0;
  max-width: 80ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
</style>
