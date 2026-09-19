<script setup lang="ts">
import { computed } from 'vue'
import type { Action } from '@/contract/types'
import { moderationStatus } from '@/lib/moderation'

/* The final classification of one analysed message: Temiz, Uyarı, İnceleme, Engellendi. */
const props = defineProps<{ action: Action | string | null | undefined }>()
const status = computed(() => moderationStatus(props.action))
</script>

<template>
  <span class="chip pill" :style="{ background: status.tint, color: status.ink }">
    <span class="chip__dot" />{{ status.label }}
  </span>
</template>

<style scoped>
.pill {
  height: 26px;
  font-size: 13px;
  font-weight: 600;
}
</style>
