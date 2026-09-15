<script setup lang="ts">
import { computed } from 'vue'
import { codePointLength } from '@/lib/spans'

/*
 * design-system 4.3. The counter never blocks submission: input up to 5000
 * characters is accepted, and past 1000 the counter turns --status-review as
 * information, not as an error.
 */
const props = defineProps<{
  modelValue: string
  placeholder: string
  label: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; submit: [] }>()

// Code points, so the count matches what the backend counts.
const count = computed(() => codePointLength(props.modelValue))

function onKeydown(event: KeyboardEvent) {
  // Ctrl/Cmd+Enter submits; the operator is one keystroke from analysing.
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault()
    emit('submit')
  }
}
</script>

<template>
  <div class="text-area">
    <textarea
      class="text-area__field"
      :value="modelValue"
      :placeholder="placeholder"
      :aria-label="label"
      maxlength="5000"
      spellcheck="false"
      dir="auto"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      @keydown="onKeydown"
    />
    <!-- pages-spec 2.2: the progress indicator appears directly beneath the text area. -->
    <slot name="below" />
    <div class="text-area__footer">
      <span class="text-area__counter" :class="{ 'text-area__counter--long': count > 1000 }">{{ count }}</span>
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.text-area__field {
  display: block;
  width: 100%;
  min-height: 120px;
  resize: vertical;
  padding: 16px;
  background: var(--surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-control);
  color: var(--text-body);
  font-family: var(--font-family-sans);
  font-size: 16px;
  line-height: 1.6;
  transition: border-color var(--motion-fast);
  unicode-bidi: plaintext;
}
.text-area__field::placeholder {
  color: var(--text-muted);
}
.text-area__field:focus {
  border-color: var(--accent);
}
.text-area__field:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.text-area__footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
}
.text-area__counter {
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.text-area__counter--long {
  color: var(--status-review);
}
</style>
