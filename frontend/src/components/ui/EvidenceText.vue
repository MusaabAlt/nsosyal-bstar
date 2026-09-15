<script setup lang="ts">
import { computed } from 'vue'
import { segment, type Mark } from '@/lib/spans'

/*
 * design-system 4.13: the only permitted monospace, because character-level
 * alignment carries meaning. Highlighted characters get a 20% --status-block
 * background with the text unchanged. Underline is reserved for exactly one
 * purpose: a profane substring inside an innocent word that a guard
 * suppressed, 1px in --status-clean.
 *
 * Offsets are code points (see lib/spans.ts), so emoji never shift a highlight.
 */
const props = defineProps<{ text: string; marks?: Mark[] }>()

const segments = computed(() => segment(props.text, props.marks ?? []))
</script>

<template>
  <p class="evidence" dir="auto">
    <template v-for="(part, i) in segments" :key="i">
      <mark v-if="part.highlight || part.underline" :class="{ 'evidence__hl': part.highlight, 'evidence__ul': part.underline }">{{
        part.text
      }}</mark>
      <template v-else>{{ part.text }}</template>
    </template>
  </p>
</template>

<style scoped>
.evidence {
  margin: 0;
  padding: 12px;
  background: var(--surface-raised);
  border-radius: var(--radius-control);
  font-family: var(--font-family-mono);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-body);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  unicode-bidi: plaintext;
}
mark {
  background: transparent;
  color: inherit;
}
.evidence__hl {
  background: var(--highlight-block);
}
.evidence__ul {
  text-decoration: underline 1px var(--status-clean);
  text-underline-offset: 3px;
}
</style>
