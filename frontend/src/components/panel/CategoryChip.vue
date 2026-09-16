<script setup lang="ts">
import { computed } from 'vue'
import { categoryMeta } from '@/lib/categories'

const props = defineProps<{ code: string }>()
const meta = computed(() => categoryMeta(props.code))
</script>

<template>
  <span class="chip" :style="{ background: meta.tint, color: meta.ink }" :title="code">
    <span class="chip__dot" />{{ meta.label }}
  </span>
</template>
