<script setup lang="ts">
import { computed } from 'vue'
import CategoryChip from './CategoryChip.vue'
import HighlightedText from './HighlightedText.vue'
import ModeratorActions from './ModeratorActions.vue'
import { copy } from '@/copy'
import type { PanelItem } from '@/api/panel'
import { firedCategories } from '@/lib/categories'
import { formatAgo, formatScore, initials } from '@/lib/format'

/* One analysed message: author, highlighted text, the categories that fired with their scores, and the moderator actions. */
const props = withDefaults(defineProps<{ item: PanelItem; now?: number; showActions?: boolean }>(), {
  now: () => Date.now(),
  showActions: true,
})
defineEmits<{ acted: [] }>()

const fired = computed(() => firedCategories(props.item.result))
</script>

<template>
  <article class="row">
    <span class="row__avatar">{{ initials(item.nickname) }}</span>
    <div class="row__body">
      <div class="row__head">
        <span class="row__name">{{ item.nickname }}</span>
        <span class="meta">@{{ item.nickname }} · {{ formatAgo(item.created_at, now) }}</span>
      </div>
      <p class="row__text"><HighlightedText :result="item.result" /></p>
      <div class="row__foot">
        <template v-for="f in fired" :key="f.code">
          <CategoryChip :code="f.code" />
          <span class="mono row__score">{{ copy.panel.score }} {{ formatScore(f.score) }}</span>
        </template>
        <span v-if="fired.length === 0" class="chip">{{ copy.panel.noDetection }}</span>
        <span class="row__spacer" />
        <ModeratorActions v-if="showActions" :comment-ids="[item.id]" :latest="item.latest_action" @done="$emit('acted')" />
      </div>
    </div>
  </article>
</template>

<style scoped>
.row {
  display: flex;
  gap: 12px;
  padding: 20px 0;
  border-top: 1px solid var(--border-divider);
}
.row__avatar {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}
.row__body {
  min-width: 0;
  flex: 1;
}
.row__head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}
.row__name {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}
.row__text {
  margin: 4px 0 0;
  font-size: 15px;
  line-height: 22px;
  color: var(--text-primary);
}
.row__foot {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.row__score {
  color: var(--text-secondary);
}
.row__spacer {
  flex: 1;
}
</style>
