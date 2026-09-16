<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import Icon from '@/components/Icon.vue'
import PageTabs from '@/components/panel/PageTabs.vue'
import KpiTile from '@/components/panel/KpiTile.vue'
import Sparkline from '@/components/panel/Sparkline.vue'
import LineChart from '@/components/panel/LineChart.vue'
import DetectionRow from '@/components/panel/DetectionRow.vue'
import StatusDot from '@/components/panel/StatusDot.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import { fetchItems, fetchOverview, type Overview, type PanelItem, type RangeName } from '@/api/panel'
import { categoryMeta } from '@/lib/categories'
import { formatClock, formatCount, formatDayMonth, formatPercent, formatScore } from '@/lib/format'
import { formLabel } from '@/contract/labels'
import { usePoll } from '@/composables/usePoll'

/* S1 Genel Bakış: KPIs, one card per detection engine, the per-category chart, escape patterns and recent detections. */
const range = ref<RangeName>('live')
const overview = shallowRef<Overview | null>(null)
const recent = shallowRef<PanelItem[]>([])
const failed = ref(false)
const now = ref(Date.now())

const tabs = computed(() => (['live', 'today', 'week'] as const).map((key) => ({ key, label: copy.panel.ranges[key]! })))

async function load() {
  const requested = range.value
  const [o, r] = await Promise.all([fetchOverview(requested), fetchItems({ detected: true, limit: 5 })])
  now.value = Date.now()
  if (requested !== range.value) return
  failed.value = !o.ok
  if (o.ok) overview.value = o.data
  if (r.ok) recent.value = r.data.items
}
const poll = usePoll(load, 5000)
watch(range, () => {
  overview.value = null
  void poll.refresh()
})

/** Buckets that have started; later ones are in the future and are not drawn. */
const elapsed = computed(() => {
  const o = overview.value
  if (!o) return 0
  const nowMs = new Date(o.now).getTime()
  return o.bucket_starts.filter((s) => new Date(s).getTime() <= nowMs).length
})

const engines = computed(() =>
  (overview.value?.categories ?? []).map((c) => ({ ...c, meta: categoryMeta(c.code), trend: c.buckets.slice(0, elapsed.value) })),
)
const engineColumns = computed(() => Math.min(5, Math.max(1, engines.value.length)))

const chart = computed(() => {
  const o = overview.value
  if (!o) return null
  const labels = o.bucket_starts.slice(0, elapsed.value).map((s) => (o.range === 'week' ? formatDayMonth(s) : formatClock(s)))
  const series = engines.value.map((e) => ({ name: e.meta.label, color: e.meta.color, values: e.trend }))
  const empty = engines.value.every((e) => e.total === 0)
  return { labels, series, empty }
})

const kpis = computed(() => {
  const o = overview.value
  if (!o) return null
  return {
    analysed: o.analysed,
    detected: { ...o.detected, sub: formatPercent(o.detected.share_pct) },
    automatic: o.automatic,
    pending: { value: o.queue.pending_detected, sub: copy.panel.kpi.pendingTotal(formatCount(o.queue.pending) ?? '0') },
  }
})
</script>

<template>
  <PageTabs v-model="range" :tabs="tabs" />

  <div class="stack">
    <p v-if="failed && !overview" class="muted">{{ copy.panel.loadFailed }}</p>

    <div class="kpis">
      <KpiTile
        icon="message"
        :label="copy.panel.kpi.analysed"
        :value="kpis?.analysed.value"
        :change="kpis?.analysed.change_pct"
        :no-change="kpis ? copy.panel.kpi.noPrevious : undefined"
      />
      <KpiTile
        icon="alert"
        :label="copy.panel.kpi.detected"
        :value="kpis?.detected.value"
        :sub="kpis?.detected.sub"
        :change="kpis?.detected.change_pct"
        :no-change="kpis ? copy.panel.kpi.noPrevious : undefined"
        lower-is-better
      />
      <KpiTile
        icon="bolt"
        :label="copy.panel.kpi.automatic"
        :value="kpis?.automatic.value"
        :change="kpis?.automatic.change_pct"
        :no-change="kpis ? copy.panel.kpi.noPrevious : undefined"
      />
      <KpiTile icon="clock" :label="copy.panel.kpi.pending" :value="kpis?.pending.value" :sub="kpis?.pending.sub" />
    </div>

    <section>
      <div class="section-head">
        <h2 class="section-title">{{ copy.panel.engines }}</h2>
        <span class="muted">{{ copy.panel.enginesNote }}</span>
      </div>
      <div v-if="engines.length" class="engines" :style="{ gridTemplateColumns: `repeat(${engineColumns}, minmax(0, 1fr))` }">
        <RouterLink v-for="e in engines" :key="e.code" :to="{ name: 'queue', query: { code: e.code } }" class="card card--tight engine">
          <div class="engine__head">
            <span class="engine__icon" :style="{ background: e.meta.tint, color: e.meta.ink }">
              <Icon :name="e.meta.icon" :size="20" />
            </span>
            <span class="engine__name">{{ e.meta.label }}</span>
          </div>
          <div class="engine__count num">{{ formatCount(e.total) }}</div>
          <div class="meta">{{ copy.panel.rangeCount[overview?.range ?? 'live'] }}</div>
          <Sparkline class="engine__spark" :values="e.trend" :color="e.meta.color" />
          <div class="engine__foot">
            <span class="mono engine__threshold">
              {{ e.threshold !== null ? copy.panel.threshold(formatScore(e.threshold)!) : copy.panel.noThreshold }}
            </span>
            <StatusDot :status="e.status" />
          </div>
        </RouterLink>
      </div>
      <p v-else-if="overview" class="muted">{{ overview.categories_error ?? copy.panel.enginesEmpty }}</p>
    </section>

    <div class="split">
      <div class="card">
        <div class="card__head">
          <h3 class="card__title">{{ copy.panel.chartTitle }}</h3>
          <span class="muted">{{ copy.panel.rangeWindow[range] }}</span>
        </div>
        <div v-if="chart" class="chart-wrap">
          <LineChart :series="chart.series" :labels="chart.labels" />
          <p v-if="chart.empty" class="muted chart-wrap__empty">{{ copy.panel.chartEmpty }}</p>
        </div>
      </div>

      <div class="card">
        <h3 class="card__title">{{ copy.panel.patterns }}</h3>
        <div class="patterns">
          <div v-for="p in overview?.patterns ?? []" :key="p.code" class="pattern">
            <Icon name="hash" class="pattern__icon" />
            <div class="pattern__text">
              <div class="pattern__title">{{ formLabel(p.code) }}</div>
              <div class="meta">{{ copy.panel.patternCount(formatCount(p.count)!) }}</div>
            </div>
          </div>
          <p v-if="overview && overview.patterns.length === 0" class="muted">{{ copy.panel.patternsEmpty }}</p>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card__head recent__head">
        <h3 class="card__title">{{ copy.panel.recent }}</h3>
        <RouterLink :to="{ name: 'queue' }" class="btn btn--ghost">
          {{ copy.panel.goQueue }}
          <Icon name="arrowRight" :size="16" :stroke="1.8" />
        </RouterLink>
      </div>
      <DetectionRow v-for="item in recent" :key="item.id" :item="item" :now="now" @acted="poll.refresh()" />
      <EmptyState v-if="overview && recent.length === 0" icon="check" :title="copy.panel.recentEmpty" class="recent__empty" />
    </div>
  </div>
</template>

<style scoped>
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}
.section-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.engines {
  display: grid;
  gap: 20px;
}
.engine {
  display: block;
  color: inherit;
  transition: border-color 0.15s;
}
.engine:hover {
  color: inherit;
  border-color: var(--accent);
}
.engine__head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.engine__icon {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}
.engine__name {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
}
.engine__count {
  margin-top: 16px;
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--text-heading);
}
.engine__spark {
  margin-top: 12px;
}
.engine__foot {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-card);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.engine__threshold {
  color: var(--text-secondary);
}
.split {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  align-items: start;
}
.chart-wrap {
  position: relative;
  margin-top: 20px;
}
.chart-wrap__empty {
  position: absolute;
  top: 90px;
  left: 0;
  right: 0;
  text-align: center;
  margin: 0;
}
.patterns {
  margin-top: 8px;
}
.pattern {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 56px;
  border-bottom: 1px solid var(--border-divider);
}
.pattern:last-child {
  border-bottom: 0;
}
.pattern__icon {
  color: var(--accent);
}
.pattern__text {
  min-width: 0;
  flex: 1;
}
.pattern__title {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--text-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.recent__head {
  align-items: center;
  margin-bottom: 8px;
}
.recent__empty {
  border: 0;
  padding: 32px 0 8px;
}
@media (max-width: 1279px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .split {
    grid-template-columns: 1fr;
  }
}
</style>
