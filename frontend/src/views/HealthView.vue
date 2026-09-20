<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import Icon from '@/components/Icon.vue'
import type { IconName } from '@/components/icons'
import KpiTile from '@/components/panel/KpiTile.vue'
import LineChart from '@/components/panel/LineChart.vue'
import { copy } from '@/copy'
import { fetchHealth, fetchMetrics, fetchStats, type Health, type Metrics, type Stats } from '@/api/panel'
import { formatClock, formatCount, formatMs, formatPercent } from '@/lib/format'
import { usePoll } from '@/composables/usePoll'

/* S9 Sistem Sağlığı: live service status and request metrics, all from /api/health, /api/stats and /api/panel/metrics. */
const health = shallowRef<Health | null>(null)
const metrics = shallowRef<Metrics | null>(null)
const stats = shallowRef<Stats | null>(null)
const failed = ref(false)

usePoll(async () => {
  const [h, m, s] = await Promise.all([fetchHealth(), fetchMetrics(), fetchStats()])
  failed.value = !h.ok
  if (h.ok) health.value = h.data
  if (m.ok) metrics.value = m.data
  if (s.ok) stats.value = s.data
}, 5000)

const rpsText = computed(() => {
  const v = metrics.value?.requests_per_second
  return typeof v === 'number' ? new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 1 }).format(v) : null
})
const p95Text = computed(() => {
  const v = formatMs(metrics.value?.latency.p95_ms)
  return v === null ? null : `${v} ms`
})

const labels = computed(() => (metrics.value?.analyses ?? []).map((b) => formatClock(b.start)))
const latencySeries = computed(() => {
  const m = metrics.value
  if (!m) return []
  return [
    { name: copy.health.seriesP50, color: 'var(--accent)', values: m.analyses.map((b) => b.p50_ms) },
    { name: copy.health.seriesP95, color: 'var(--cat-obf)', values: m.analyses.map((b) => b.p95_ms) },
  ]
})
const requestSeries = computed(() => {
  const m = metrics.value
  if (!m) return []
  return [
    { name: copy.health.seriesAll, color: 'var(--text-muted)', values: m.all_requests.map((b) => b.requests) },
    { name: copy.health.seriesAnalyses, color: 'var(--mint)', values: m.analyses.map((b) => b.requests) },
  ]
})

function uptime(seconds: number | undefined): string | null {
  if (typeof seconds !== 'number') return null
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h} sa ${m} dk` : `${m} dk`
}

interface Service {
  key: string
  name: string
  icon: IconName
  ok: boolean
  status: string
  facts: Array<{ label: string; value: string | null; mono?: boolean }>
}

const services = computed<Service[]>(() => {
  const h = health.value
  if (!h) return []
  const cache = stats.value?.cache
  return [
    {
      key: 'go',
      name: copy.health.go,
      icon: 'server',
      ok: h.go.status === 'ok',
      status: copy.health.ok,
      facts: [
        { label: copy.health.uptime, value: uptime(h.go.uptime_seconds) },
        { label: copy.health.goroutines, value: formatCount(h.go.goroutines) },
        { label: copy.health.cache, value: cache ? `${formatCount(cache.hits)} / ${formatCount(cache.misses)}` : null },
      ],
    },
    {
      key: 'postgres',
      name: copy.health.postgres,
      icon: 'database',
      ok: h.postgres.status === 'ok',
      status: h.postgres.status === 'ok' ? copy.health.ok : copy.health.down,
      facts: [
        { label: copy.health.ping, value: formatMs(h.postgres.latency_ms) === null ? null : `${formatMs(h.postgres.latency_ms)} ms` },
        { label: copy.health.written, value: formatCount(h.writer.analyses_written) },
        { label: copy.health.dropped, value: formatCount(h.writer.analyses_dropped + h.writer.metrics_dropped) },
      ],
    },
    {
      key: 'python',
      name: copy.health.python,
      icon: 'brain',
      ok: h.python.status === 'ok',
      status: copy.health.pythonStatus[h.python.status] ?? h.python.status,
      facts: [
        { label: copy.health.artifact, value: h.python.artifact_hash ? h.python.artifact_hash.slice(0, 12) : null, mono: true },
        { label: copy.health.breaker, value: h.python.breaker, mono: true },
        {
          label: copy.health.degradedModules,
          value: h.python.degraded_modules?.length ? h.python.degraded_modules.join(', ') : copy.health.none,
          mono: true,
        },
      ],
    },
    {
      key: 'queue',
      name: copy.health.queue,
      icon: 'layers',
      ok: h.queue.queue_len < h.queue.queue_capacity,
      status: copy.health.ok,
      facts: [
        { label: copy.health.queueDepth, value: `${formatCount(h.queue.queue_len)} / ${formatCount(h.queue.queue_capacity)}` },
        { label: copy.health.rejected, value: formatCount(h.queue.rejected) },
        { label: copy.health.batches, value: formatCount(h.queue.batches) },
      ],
    },
  ]
})
</script>

<template>
  <div class="stack">
    <div v-if="health?.status === 'degraded' || failed" class="alert">
      <Icon name="alert" :size="20" />
      {{ copy.health.alertDegraded }}
    </div>
    <div v-if="metrics?.slow" class="alert alert--warn">
      <Icon name="activity" :size="20" />
      {{ copy.health.alertSlow(String(metrics.slow_p95_ms)) }}
    </div>

    <div class="kpis">
      <KpiTile icon="wifi" :label="copy.health.devices" :value="metrics?.active_devices" />
      <KpiTile icon="bolt" :label="copy.health.rps" :value="null" :text="rpsText" />
      <KpiTile icon="clock" :label="copy.health.latency" :value="null" :text="p95Text" />
      <KpiTile icon="alert" :label="copy.health.errors" :value="null" :text="formatPercent(metrics?.error_rate_pct)" />
    </div>

    <div class="charts">
      <div class="card">
        <div class="card__head">
          <h3 class="card__title">{{ copy.health.latencyChart }}</h3>
          <span class="muted">{{ copy.health.last30 }}</span>
        </div>
        <LineChart class="chart" :series="latencySeries" :labels="labels" :height="180" />
      </div>
      <div class="card">
        <div class="card__head">
          <h3 class="card__title">{{ copy.health.requestsChart }}</h3>
          <span class="muted">{{ copy.health.last30 }}</span>
        </div>
        <LineChart class="chart" :series="requestSeries" :labels="labels" :height="180" />
      </div>
    </div>

    <div class="card">
      <h3 class="card__title">{{ copy.health.services }}</h3>
      <div v-for="s in services" :key="s.key" class="service">
        <span class="service__icon"><Icon :name="s.icon" /></span>
        <div class="service__main">
          <div class="service__name">{{ s.name }}</div>
          <span class="service__status" :style="{ color: s.ok ? 'var(--mint)' : 'var(--danger)' }">
            <span class="chip__dot" />{{ s.ok ? s.status : copy.health.down }}
          </span>
        </div>
        <dl class="service__facts">
          <div v-for="f in s.facts" :key="f.label" class="service__fact">
            <dt>{{ f.label }}</dt>
            <dd :class="{ mono: f.mono }">
              <template v-if="f.value !== null">{{ f.value }}</template>
              <span v-else class="unavailable">{{ copy.panel.unavailable }}</span>
            </dd>
          </div>
        </dl>
      </div>
      <p v-if="health?.python.error" class="meta">{{ health.python.error }}</p>
    </div>
  </div>
</template>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  background: var(--danger-subtle);
  color: var(--danger);
  font-size: 14px;
  font-weight: 500;
}
.alert--warn {
  background: var(--warning-subtle);
  color: var(--warning);
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}
.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.chart {
  margin-top: 20px;
}
.service {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  border-top: 1px solid var(--border-divider);
}
.service:first-of-type {
  margin-top: 8px;
}
.service__icon {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.service__main {
  width: 180px;
  flex: none;
}
.service__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-heading);
}
.service__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
}
.service__facts {
  flex: 1;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.service__fact dt {
  font-size: 12px;
  color: var(--text-meta);
}
.service__fact dd {
  margin: 2px 0 0;
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-word;
}
@media (max-width: 1279px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .charts {
    grid-template-columns: 1fr;
  }
}

/* ------------------------------------------------------------------ phone */
@media (max-width: 599px) {
  .kpis,
  .charts {
    gap: 12px;
  }
  .chart {
    margin-top: 14px;
  }
  /* The service name and its three facts stack instead of sharing one line. */
  .service {
    flex-wrap: wrap;
    gap: 12px;
    padding: 14px 0;
  }
  .service__icon {
    width: 34px;
    height: 34px;
  }
  .service__main {
    width: auto;
    flex: 1;
  }
  .service__facts {
    flex-basis: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 16px;
  }
  .service__fact dd {
    overflow-wrap: anywhere;
  }
}
</style>
