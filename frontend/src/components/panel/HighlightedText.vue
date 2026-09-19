<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisResult } from '@/contract/types'
import { segmentByKey, type KeyedMark } from '@/lib/spans'
import { categoryMeta } from '@/lib/categories'

/*
 * The analysed text with the span of every fired content code highlighted in
 * that category's colour. Spans are code-point offsets (lib/spans).
 */
const props = defineProps<{ result: AnalysisResult }>()

const segments = computed(() => {
  const marks: KeyedMark[] = (props.result.content ?? [])
    .filter((c) => c.fired === true && c.span)
    .map((c) => ({ span: c.span!, key: c.code }))
  return segmentByKey(props.result.text, marks).map((s) => {
    const meta = s.key ? categoryMeta(s.key) : null
    return { text: s.text, style: meta ? { background: meta.tint, borderBottom: `2px solid ${meta.color}` } : null }
  })
})
</script>

<template>
  <span class="hl"><span v-for="(s, i) in segments" :key="i" :class="{ hl__mark: s.style }" :style="s.style ?? undefined">{{ s.text }}</span></span>
</template>

<style scoped>
.hl {
  white-space: pre-wrap;
  word-break: break-word;
}
.hl__mark {
  border-radius: 4px;
  padding: 1px 2px;
}
</style>
