<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import Icon from './Icon.vue'
import { copy } from '@/copy'
import { fetchItems, type PanelItem } from '@/api/panel'
import { categoryMeta, firedCategories } from '@/lib/categories'
import { formatAgo } from '@/lib/format'
import { usePoll } from '@/composables/usePoll'

/*
 * Canlı Akış: the newest analysed messages, whatever their outcome.
 *
 * It opens itself on a desktop, where it costs a corner. On a phone it is a
 * full-width strip along the bottom edge and an open one would cover the page,
 * so it starts collapsed and the operator opens it when they want it.
 */
const open = ref(typeof window === 'undefined' || window.innerWidth >= 900)
const items = shallowRef<PanelItem[]>([])
const now = ref(Date.now())

usePoll(async () => {
  const out = await fetchItems({ limit: 4 })
  now.value = Date.now()
  if (out.ok) items.value = out.data.items
}, 3000)

const rows = computed(() =>
  items.value.map((item) => {
    const first = firedCategories(item.result)[0]
    const meta = first ? categoryMeta(first.code) : null
    return {
      id: item.id,
      color: meta ? meta.ink : 'var(--text-muted)',
      label: `${meta ? meta.label : copy.panel.noDetection} · @${item.nickname}`,
      time: formatAgo(item.created_at, now.value),
    }
  }),
)
</script>

<template>
  <section class="dock" :aria-label="copy.app.liveFeed">
    <button type="button" class="dock__head" :aria-expanded="open" @click="open = !open">
      <span class="dock__live" />
      <span class="dock__title">{{ copy.app.liveFeed }}</span>
      <Icon :name="open ? 'chevronDown' : 'chevronUp'" :size="16" :stroke="1.8" class="dock__chevron" />
    </button>
    <div v-if="open" class="dock__body">
      <RouterLink
        v-for="row in rows"
        :key="row.id"
        :to="{ name: 'queue', query: { id: row.id } }"
        class="dock__row"
      >
        <span class="dock__dot" :style="{ background: row.color }" />
        <span class="dock__label">{{ row.label }}</span>
        <span class="mono dock__time">{{ row.time }}</span>
      </RouterLink>
      <p v-if="rows.length === 0" class="muted dock__empty">{{ copy.app.liveFeedEmpty }}</p>
    </div>
  </section>
</template>

<style scoped>
.dock {
  position: fixed;
  right: 16px;
  bottom: 16px;
  width: 260px;
  background: var(--bg-raised);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-float);
  overflow: hidden;
  z-index: 20;
}
.dock__head {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.dock__body {
  padding: 8px 16px 12px;
  border-top: 1px solid var(--border-card);
}
.dock__live {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--mint);
  flex: none;
}
.dock__title {
  flex: 1;
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}
.dock__chevron {
  color: var(--text-muted);
}
.dock__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}
.dock__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex: none;
}
.dock__label {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dock__time {
  font-size: 12px;
  color: var(--text-meta);
}
.dock__empty {
  margin: 8px 0;
}

/* ------------------------------------------------------------------ phone */
@media (max-width: 899px) {
  .dock {
    left: 12px;
    right: 12px;
    bottom: 12px;
    width: auto;
    /* Collapsed it is a 44px bar; open it never grows past half the screen. */
    max-height: 56dvh;
    overflow-y: auto;
  }
  .dock__head {
    height: 46px;
  }
  .dock__row {
    padding: 10px 0;
  }
}
</style>
