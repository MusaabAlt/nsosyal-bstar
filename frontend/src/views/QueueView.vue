<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import PageTabs from '@/components/panel/PageTabs.vue'
import CategoryChip from '@/components/panel/CategoryChip.vue'
import HighlightedText from '@/components/panel/HighlightedText.vue'
import ModeratorActions from '@/components/panel/ModeratorActions.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import {
  fetchCategories,
  fetchItem,
  fetchItems,
  fetchQueueCounts,
  recordAction,
  type Category,
  type ItemDetail,
  type ModeratorAction,
  type PanelItem,
  type QueueCounts,
} from '@/api/panel'
import { buildStages, type ContentStage } from '@/report/model'
import { categoryMeta, firedCategories } from '@/lib/categories'
import { formatAgo, formatClock, formatCount, formatScore, initials } from '@/lib/format'
import { actionLabel } from '@/contract/labels'
import { usePoll } from '@/composables/usePoll'

/* S3 Moderasyon Kuyruğu: tabs by status, filters, the list, a detail panel with scores, context and history, and bulk actions. */
type Tab = 'pending' | 'reviewed' | 'auto'
const route = useRoute()
const router = useRouter()

const tab = ref<Tab>((['pending', 'reviewed', 'auto'] as const).find((t) => t === route.query.status) ?? 'pending')
const detectedOnly = ref(route.query.all !== '1')
const code = ref(typeof route.query.code === 'string' ? route.query.code : '')
const q = ref('')
const appliedQ = ref('')

const counts = shallowRef<QueueCounts | null>(null)
const categories = shallowRef<Category[]>([])
const items = shallowRef<PanelItem[]>([])
const cursor = ref<string | undefined>()
const loading = ref(false)
const failed = ref(false)
const now = ref(Date.now())

const selectedId = ref<string | null>(typeof route.query.id === 'string' ? route.query.id : null)
const detail = shallowRef<ItemDetail | null>(null)
const detailMissing = ref(false)
const checked = ref<Set<string>>(new Set())
const actionsRef = ref<InstanceType<typeof ModeratorActions> | null>(null)
const bulkBusy = ref(false)
const detailEl = ref<HTMLElement | null>(null)

/*
 * Picking a message. On a wide screen the detail is the column next to the
 * list and nothing needs to move; stacked on a phone it is below thirty list
 * items, so the panel that just changed is brought to the operator rather
 * than left for them to find. Only a deliberate pick scrolls: the first item
 * selects itself when the list loads, and that must not move the page.
 */
function select(id: string) {
  const moved = selectedId.value !== id
  selectedId.value = id
  if (!moved || !window.matchMedia('(max-width: 899px)').matches) return
  void nextTick(() => detailEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const tabs = computed(() => {
  const c = counts.value
  const n = (key: Tab) => {
    if (!c) return ''
    const value = key === 'pending' ? (detectedOnly.value ? c.pending_detected : c.pending) : key === 'reviewed' ? c.reviewed : c.auto
    return ` (${formatCount(value)})`
  }
  return (['pending', 'reviewed', 'auto'] as const).map((key) => ({ key, label: `${copy.queue.tabs[key]}${n(key)}` }))
})

async function loadList(append = false) {
  loading.value = true
  const out = await fetchItems({
    status: tab.value,
    detected: detectedOnly.value,
    code: code.value,
    q: appliedQ.value,
    limit: 30,
    cursor: append ? cursor.value : undefined,
  })
  loading.value = false
  now.value = Date.now()
  failed.value = !out.ok
  if (!out.ok) return
  items.value = append ? [...items.value, ...out.data.items] : out.data.items
  cursor.value = out.data.next_cursor
  if (!selectedId.value && items.value[0]) selectedId.value = items.value[0].id
}

async function loadCounts() {
  const out = await fetchQueueCounts()
  if (out.ok) counts.value = out.data
}

async function loadDetail() {
  const id = selectedId.value
  if (!id) {
    detail.value = null
    return
  }
  const out = await fetchItem(id)
  if (id !== selectedId.value) return
  detailMissing.value = !out.ok && out.status === 404
  detail.value = out.ok ? out.data : null
}

usePoll(loadCounts, 5000)
onMounted(async () => {
  void loadList()
  const out = await fetchCategories()
  if (out.ok) categories.value = out.data.categories
})

watch([tab, detectedOnly, code, appliedQ], () => {
  checked.value = new Set()
  selectedId.value = null
  void router.replace({
    query: { status: tab.value, ...(code.value ? { code: code.value } : {}), ...(detectedOnly.value ? {} : { all: '1' }) },
  })
  void loadList()
})
watch(selectedId, () => void loadDetail(), { immediate: true })

function afterAction() {
  void loadCounts()
  void loadList()
  void loadDetail()
}

function toggleCheck(id: string) {
  const next = new Set(checked.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  checked.value = next
}

async function bulk(action: ModeratorAction) {
  if (checked.value.size === 0) return
  bulkBusy.value = true
  const out = await recordAction([...checked.value], action)
  bulkBusy.value = false
  if (out.ok) {
    checked.value = new Set()
    afterAction()
  }
}

const detailView = computed(() => {
  const d = detail.value
  if (!d) return null
  const r = d.item.result
  const rows = (buildStages(r).find((s) => s.kind === 'content') as ContentStage | undefined)?.rows ?? []
  return {
    ...d,
    rows: rows.map((row) => ({
      ...row,
      meta: categoryMeta(row.key),
      score: formatScore(row.score),
      threshold: formatScore(row.threshold),
      outcome: row.fired === true ? copy.live.detected : row.fired === false ? copy.live.below : copy.live.undecided,
    })),
  }
})

const KEYS: Record<string, ModeratorAction> = { a: 'approve', h: 'hide', r: 'remove' }
function onKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null
  if (e.ctrlKey || e.metaKey || e.altKey || target?.closest('input, textarea, select')) return
  const action = KEYS[e.key.toLowerCase()]
  if (action && detail.value) {
    e.preventDefault()
    void actionsRef.value?.act(action)
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <PageTabs v-model="tab" :tabs="tabs" />

  <div class="queue">
    <div class="filters">
      <div class="filters__chips">
        <button type="button" class="btn" :class="{ 'btn--active': detectedOnly }" @click="detectedOnly = !detectedOnly">
          {{ copy.queue.detectedOnly }}
        </button>
        <button type="button" class="btn" :class="{ 'btn--active': code === '' }" @click="code = ''">{{ copy.queue.allCategories }}</button>
        <button
          v-for="c in categories"
          :key="c.code"
          type="button"
          class="btn"
          :style="code === c.code ? { background: categoryMeta(c.code).tint, color: categoryMeta(c.code).ink } : undefined"
          @click="code = code === c.code ? '' : c.code"
        >
          {{ categoryMeta(c.code).label }}
        </button>
      </div>
      <form class="filters__search" role="search" @submit.prevent="appliedQ = q.trim()">
        <input v-model="q" type="search" class="input" :placeholder="copy.queue.search" :aria-label="copy.queue.search" maxlength="200" />
      </form>
    </div>

    <div v-if="checked.size" class="bulk">
      <span class="bulk__count">{{ copy.queue.selected(formatCount(checked.size)!) }}</span>
      <button type="button" class="btn btn--ghost" @click="checked = new Set()">{{ copy.queue.clearSelection }}</button>
      <span class="bulk__spacer" />
      <button type="button" class="btn" :disabled="bulkBusy" @click="bulk('approve')">{{ copy.panel.actions.approve }}</button>
      <button type="button" class="btn btn--secondary" :disabled="bulkBusy" @click="bulk('hide')">{{ copy.panel.actions.hide }}</button>
      <button type="button" class="btn btn--danger" :disabled="bulkBusy" @click="bulk('remove')">{{ copy.panel.actions.remove }}</button>
    </div>

    <div class="split">
      <div class="card list">
        <p v-if="failed && items.length === 0" class="muted">{{ copy.panel.loadFailed }}</p>
        <div
          v-for="item in items"
          :key="item.id"
          class="item"
          :class="{ 'item--selected': item.id === selectedId }"
          @click="select(item.id)"
        >
          <input
            type="checkbox"
            class="item__check"
            :checked="checked.has(item.id)"
            :aria-label="copy.queue.selectLabel"
            @click.stop
            @change="toggleCheck(item.id)"
          />
          <span class="item__avatar">{{ initials(item.nickname) }}</span>
          <div class="item__body">
            <div class="item__head">
              <span class="item__name">{{ item.nickname }}</span>
              <span class="meta">· {{ formatAgo(item.created_at, now) }}</span>
              <span class="item__spacer" />
              <span v-if="item.latest_action" class="chip">{{ copy.panel.actionDone[item.latest_action] }}</span>
            </div>
            <p class="item__text">{{ item.text }}</p>
            <div class="item__chips">
              <CategoryChip v-for="f in firedCategories(item.result)" :key="f.code" :code="f.code" />
              <span v-if="!item.detected" class="chip">{{ copy.panel.noDetection }}</span>
            </div>
          </div>
        </div>
        <EmptyState v-if="!loading && !failed && items.length === 0" icon="inbox" :title="copy.queue.empty" class="list__empty" />
        <button v-if="cursor" type="button" class="btn list__more" :disabled="loading" @click="loadList(true)">{{ copy.panel.loadMore }}</button>
      </div>

      <aside ref="detailEl" class="card detail">
        <template v-if="detailView">
          <div class="detail__head">
            <h3 class="card__title">{{ copy.queue.detail }}</h3>
            <span class="chip">{{ copy.queue.status[detailView.item.status] }}</span>
          </div>
          <div class="detail__author">
            <span class="item__avatar">{{ initials(detailView.item.nickname) }}</span>
            <div>
              <div class="item__name">{{ detailView.item.nickname }}</div>
              <div class="meta">@{{ detailView.item.nickname }} · {{ formatClock(detailView.item.created_at, true) }}</div>
            </div>
          </div>
          <p class="detail__text"><HighlightedText :result="detailView.item.result" /></p>

          <ModeratorActions
            ref="actionsRef"
            :comment-ids="[detailView.item.id]"
            :latest="detailView.item.latest_action"
            size="md"
            @done="afterAction"
          />
          <p class="meta detail__keys">{{ copy.queue.keyboard }}</p>

          <h4 class="detail__section">{{ copy.queue.scores }}</h4>
          <table v-if="detailView.rows.length" class="table table--stack">
            <thead>
              <tr>
                <th>{{ copy.queue.category }}</th>
                <th>{{ copy.queue.score }}</th>
                <th>{{ copy.queue.threshold }}</th>
                <th>{{ copy.queue.outcome }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in detailView.rows" :key="row.key">
                <td>{{ row.meta.label }}</td>
                <td class="mono num" :data-label="copy.queue.score" :style="row.fired === true ? { color: row.meta.ink } : undefined">{{ row.score }}</td>
                <td class="mono num" :data-label="copy.queue.threshold">{{ row.threshold ?? copy.panel.noThreshold }}</td>
                <td :data-label="copy.queue.outcome" :class="{ 'detail__hit': row.fired === true }">{{ row.outcome }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">{{ copy.stages.contentNone }}</p>

          <h4 class="detail__section">{{ copy.queue.decision }}</h4>
          <p class="muted detail__explain">
            <span v-if="detailView.item.final_action" class="chip detail__verdict">{{ actionLabel(detailView.item.final_action) }}</span>
            {{ detailView.item.explanation }}
          </p>

          <h4 class="detail__section">{{ copy.queue.context }}</h4>
          <div v-for="p in detailView.previous" :key="p.id" class="context" @click="select(p.id)">
            <span class="meta">{{ formatAgo(p.created_at, now) }}</span>
            <span class="context__text">{{ p.text }}</span>
          </div>
          <p v-if="detailView.previous.length === 0" class="muted">{{ copy.queue.noContext }}</p>

          <h4 class="detail__section">{{ copy.queue.history }}</h4>
          <div v-for="(a, i) in detailView.actions" :key="i" class="history">
            <Icon name="flag" :size="16" class="history__icon" />
            <span>{{ a.nickname ?? copy.history.unknownActor }} — {{ copy.panel.actions[a.action] }}</span>
            <span class="meta history__time">{{ formatClock(a.created_at) }}</span>
          </div>
          <p v-if="detailView.actions.length === 0" class="muted">{{ copy.queue.noHistory }}</p>
        </template>
        <p v-else-if="detailMissing" class="muted">{{ copy.queue.notFound }}</p>
        <p v-else class="muted">{{ copy.queue.selectHint }}</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.queue {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filters__chips {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.filters__search {
  margin-left: auto;
}
.filters__search .input {
  width: 260px;
}
.bulk {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--radius-full);
  background: var(--bg-nav-active);
  border: 1px solid var(--border-card);
  position: sticky;
  top: calc(var(--header-height) + 12px);
  z-index: 5;
}
.bulk__count {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.bulk__spacer {
  flex: 1;
}
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 480px;
  gap: 20px;
  align-items: start;
}
.list {
  padding: 8px;
}
.list__empty {
  border: 0;
}
.list__more {
  margin: 12px auto;
  display: flex;
}
.item {
  display: flex;
  gap: 12px;
  padding: 14px 12px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background-color 0.15s;
}
.item:hover {
  background: var(--bg-nav-hover);
}
.item--selected {
  background: var(--bg-nav-active);
  box-shadow: inset 3px 0 0 var(--accent);
}
.item__check {
  margin-top: 12px;
  accent-color: var(--accent);
}
.item__avatar {
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.item__body {
  flex: 1;
  min-width: 0;
}
.item__head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.item__spacer {
  flex: 1;
}
.item__name {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}
.item__text {
  margin: 2px 0 0;
  font-size: 15px;
  line-height: 22px;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.item__chips {
  margin-top: 8px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.detail {
  position: sticky;
  top: calc(var(--header-height) + 24px);
  max-height: calc(100vh - var(--header-height) - 48px);
  overflow-y: auto;
}
.detail__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.detail__author {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.detail__text {
  margin: 12px 0 16px;
  font-size: 16px;
  line-height: 26px;
}
.detail__keys {
  margin: 8px 0 0;
}
.detail__section {
  margin: 24px 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-heading);
}
.detail__hit {
  color: var(--danger) !important;
}
.detail__explain {
  margin: 0;
}
.detail__verdict {
  margin-right: 6px;
}
.context {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-card);
  cursor: pointer;
}
.context__text {
  font-size: 14px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 14px;
}
.history__icon {
  color: var(--accent);
}
.history__time {
  margin-left: auto;
}
@media (max-width: 1279px) {
  .split {
    grid-template-columns: 1fr;
  }
  .detail {
    position: static;
    max-height: none;
  }
}

/* ------------------------------------------------------------------ phone */
/*
 * The filter row becomes a single sideways strip instead of four stacked
 * lines of wrapped pills, the search takes the full width under it, and the
 * bulk bar wraps rather than pushing its buttons off the screen.
 */
@media (max-width: 599px) {
  .queue {
    gap: 12px;
  }
  .filters {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  /* One sideways strip: eight category pills stacked would push the list
     itself below the fold before a single message is read. */
  .filters__chips {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
    margin: 0 calc(var(--page-gutter) * -1);
    padding: 2px var(--page-gutter);
  }
  .filters__chips::-webkit-scrollbar {
    display: none;
  }
  .filters__chips .btn {
    flex: none;
  }
  .filters__search {
    margin-left: 0;
  }
  .filters__search .input {
    width: 100%;
  }
  .bulk {
    flex-wrap: wrap;
    border-radius: var(--radius-lg);
    padding: 10px 12px;
  }
  .bulk__spacer {
    flex-basis: 100%;
    height: 0;
  }
  .bulk .btn {
    flex: 1;
  }
  .item {
    padding: 12px 8px;
    gap: 10px;
  }
  .item__avatar {
    width: 32px;
    height: 32px;
  }
  /* The name, the age and the "already acted on" chip wrap as whole words
     instead of the time being split around the chip. */
  .item__head {
    flex-wrap: wrap;
    gap: 4px 6px;
  }
  .item__head .meta {
    white-space: nowrap;
  }
  .item__spacer {
    display: none;
  }
  .item__text {
    font-size: 14px;
    line-height: 21px;
  }
  .detail__text {
    font-size: 15px;
    line-height: 24px;
  }
  .detail__hit {
    color: var(--danger) !important;
  }
  .context__text {
    white-space: normal;
  }
  .history {
    flex-wrap: wrap;
  }
  .history__time {
    margin-left: 24px;
  }
}
</style>
