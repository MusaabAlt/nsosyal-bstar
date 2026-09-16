<script setup lang="ts">
import { ref, watch } from 'vue'
import { copy } from '@/copy'
import { recordAction, type ModeratorAction } from '@/api/panel'

/*
 * Moderator action buttons. Each click is stored on the server; the buttons
 * then show what was recorded. `latest` is the last action the server
 * already knows for this comment.
 */
const props = withDefaults(
  defineProps<{
    commentIds: string[]
    actions?: ModeratorAction[]
    latest?: ModeratorAction | null
    size?: 'sm' | 'md'
  }>(),
  { actions: () => ['approve', 'hide', 'remove'], latest: null, size: 'sm' },
)
const emit = defineEmits<{ done: [action: ModeratorAction] }>()

const busy = ref<ModeratorAction | null>(null)
const recorded = ref<ModeratorAction | null>(props.latest)
const failed = ref(false)
watch(
  () => [props.latest, props.commentIds.join(',')],
  () => {
    recorded.value = props.latest
    failed.value = false
  },
)

const VARIANT: Record<ModeratorAction, string> = {
  approve: '',
  hide: 'btn--secondary',
  remove: 'btn--danger',
  queue: 'btn--solid',
  false_positive: 'btn--secondary',
}

async function act(action: ModeratorAction) {
  if (busy.value || props.commentIds.length === 0) return
  busy.value = action
  failed.value = false
  const out = await recordAction(props.commentIds, action)
  busy.value = null
  if (out.ok) {
    recorded.value = action
    emit('done', action)
  } else {
    failed.value = true
  }
}

defineExpose({ act })
</script>

<template>
  <div class="actions" :class="`actions--${size}`">
    <span v-if="failed" class="actions__note actions__note--error" role="status">{{ copy.panel.actionFailed }}</span>
    <span v-else-if="recorded" class="actions__note" role="status">{{ copy.panel.actionDone[recorded] }}</span>
    <button
      v-for="action in actions"
      :key="action"
      type="button"
      class="btn"
      :class="[VARIANT[action], { 'btn--current': recorded === action }]"
      :disabled="busy !== null || commentIds.length === 0"
      @click="act(action)"
    >
      {{ copy.panel.actions[action] }}
    </button>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.actions--md .btn {
  height: 36px;
  padding: 0 18px;
}
.actions__note {
  font-size: 13px;
  color: var(--mint);
  margin-right: 4px;
}
.actions__note--error {
  color: var(--danger);
}
.btn--current {
  box-shadow: 0 0 0 2px var(--accent);
}
</style>
