<script setup lang="ts">
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'

defineProps<{ icon: IconName; title: string; text?: string }>()
</script>

<template>
  <div class="card empty">
    <Icon :name="icon" :size="48" :stroke="1.2" class="empty__icon" />
    <h3 class="card__title">{{ title }}</h3>
    <p v-if="text" class="muted empty__text">{{ text }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: 64px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}
.empty__icon {
  color: var(--text-muted);
}
.empty__text {
  margin: 0;
  max-width: 52ch;
  text-wrap: pretty;
}
</style>
