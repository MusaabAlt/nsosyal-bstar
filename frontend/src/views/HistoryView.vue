<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'
import PageTabs from '@/components/panel/PageTabs.vue'
import CategoryChip from '@/components/panel/CategoryChip.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import { fetchEvents, type PanelEvent } from '@/api/panel'
import { BINARY_OFFENSIVE } from '@/lib/categories'
import { dayKey, formatClock, formatDayHeading } from '@/lib/format'
import { actionLabel } from '@/contract/labels'

/*
 * S8 Olay Geçmişi: moderator actions and the system's own detections, newest
 * first, grouped by day. The header search lands here (?q=).
 */
type Kind = 'all' | 'moderator' | 'system'
const route = useRoute()
const router = useRouter()

const kind = ref<Kind>('all')
const q = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const events = shallowRef<PanelEvent[]>([])
const cursor = ref<string | undefined>()
const loading = ref(false)
const failed = ref(false)

const tabs = computed(() => (['all', 'moderator', 'system'] as const).map((key) => ({ key, label: copy.history.tabs[key]! })))

async function load(append = false) {
  loading.value = true
  const out = await fetchEvents({
    kind: kind.value === 'all' ? '' : kind.value,
    q: q.value,
    limit: 50,
    cursor: append ? cursor.value : undefined,
  })
  loading.value = false
  failed.value = !out.ok
  if (!out.ok) return
  events.value = append ? [...events.value, ...out.data.items] : out.data.items
  cursor.value = out.data.next_cursor
}
onMounted(() => load())
watch([kind, q], () => load())

const ICON: Record<string, IconName> = {
  approve: 'check',
  hide: 'viewOff',
  remove: 'userBlock',
  queue: 'inbox',
  false_positive: 'flag',
}

const groups = computed(() => {
  const out: Array<{ key: string; heading: string; rows: Array<PanelEvent & { icon: IconName; line: string }> }> = []
  for (const e of events.value) {
    const key = dayKey(e.created_at)
    let group = out[out.length - 1]
    if (!group || group.key !== key) {
      group = { key, heading: formatDayHeading(e.created_at), rows: [] }
      out.push(group)
    }
    const moderator = e.kind === 'moderator'
    const actionWord = moderator ? copy.panel.actions[e.action ?? ''] ?? e.action : e.action ? actionLabel(e.action) : copy.panel.unavailable
    group.rows.push({
      ...e,
      icon: moderator ? (ICON[e.action ?? ''] ?? 'flag') : 'cpu',
      line: `${moderator ? (e.actor ?? copy.history.unknownActor) : copy.history.system} — ${actionWord} — @${e.author}`,
    })
  }
  return out
})

/** The system event's categories: its fired content codes; the offensive score when nothing else fired. */
function codesOf(e: PanelEvent): string[] {
  return e.fired_types.length ? e.fired_types : e.detected ? [BINARY_OFFENSIVE] : []
}

function exportCsv() {
  const header = ['zaman', 'tür', 'işlem', 'moderatör', 'kullanıcı', 'kategoriler', 'mesaj', 'yorum_id']
  const quote = (v: string) => `"${v.replaceAll('"', '""')}"`
  const lines = events.value.map((e) =>
    [e.created_at, e.kind, e.action ?? '', e.actor ?? '', e.author, e.fired_types.join(' '), e.text, e.comment_id].map(quote).join(','),
  )
  const blob = new Blob(['﻿' + [header.join(','), ...lines].join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `olay-gecmisi-${new Date().toISOString().slice(0, 19).replaceAll(':', '-')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <PageTabs v-model="kind" :tabs="tabs" />

  <div class="stack">
    <div class="toolbar">
      <template v-if="q">
        <span class="toolbar__search">{{ copy.history.searchResults(q) }}</span>
        <button type="button" class="btn btn--ghost" @click="router.push({ name: 'history' })">{{ copy.history.clearSearch }}</button>
      </template>
      <span class="toolbar__spacer" />
      <button type="button" class="btn" :disabled="events.length === 0" @click="exportCsv">
        <Icon name="download" :size="16" :stroke="1.8" />
        {{ copy.history.export }}
      </button>
    </div>

    <p v-if="failed && events.length === 0" class="muted">{{ copy.panel.loadFailed }}</p>

    <section v-for="g in groups" :key="g.key" class="card day">
      <h3 class="card__title day__title">{{ g.heading }}</h3>
      <div v-for="e in g.rows" :key="e.key" class="event">
        <span class="mono event__time">{{ formatClock(e.created_at) }}</span>
        <span class="event__icon" :class="{ 'event__icon--system': e.kind === 'system' }"><Icon :name="e.icon" :size="18" /></span>
        <div class="event__body">
          <div class="event__line">{{ e.line }}</div>
          <p class="event__text">{{ e.text }}</p>
          <div class="event__chips">
            <CategoryChip v-for="c in codesOf(e)" :key="c" :code="c" />
          </div>
        </div>
        <RouterLink :to="{ name: 'queue', query: { id: e.comment_id, all: '1' } }" class="btn btn--ghost event__open">
          {{ copy.history.open }}
          <Icon name="arrowRight" :size="16" :stroke="1.8" />
        </RouterLink>
      </div>
    </section>

    <EmptyState v-if="!loading && !failed && events.length === 0" icon="clock" :title="copy.history.empty" />
    <button v-if="cursor" type="button" class="btn more" :disabled="loading" @click="load(true)">{{ copy.panel.loadMore }}</button>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar__search {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-heading);
}
.toolbar__spacer {
  flex: 1;
}
.day__title {
  margin-bottom: 8px;
}
.event {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid var(--border-divider);
}
.event__time {
  width: 44px;
  flex: none;
  color: var(--text-meta);
  padding-top: 6px;
}
.event__icon {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-subtle);
  color: var(--accent);
}
.event__icon--system {
  color: var(--text-muted);
}
.event__body {
  flex: 1;
  min-width: 0;
}
.event__line {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}
.event__text {
  margin: 2px 0 0;
  font-size: 14px;
  line-height: 20px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event__chips {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.event__open {
  padding-top: 6px;
  font-size: 13px;
}
.more {
  align-self: center;
}
</style>
