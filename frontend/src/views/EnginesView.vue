<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import Icon from '@/components/Icon.vue'
import Sparkline from '@/components/panel/Sparkline.vue'
import StatusDot from '@/components/panel/StatusDot.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import { fetchOverview, type Overview } from '@/api/panel'
import { categoryMeta } from '@/lib/categories'
import { formatCount, formatScore } from '@/lib/format'
import { actionLabel } from '@/contract/labels'
import { usePoll } from '@/composables/usePoll'

/*
 * S4 Tespit Motorları: one card per category the AI detects today, with its
 * module, status, own threshold and action, and today's detections.
 */
const overview = shallowRef<Overview | null>(null)
const failed = ref(false)

usePoll(async () => {
  const out = await fetchOverview('today')
  failed.value = !out.ok
  if (out.ok) overview.value = out.data
}, 10000)

const elapsed = computed(() => {
  const o = overview.value
  if (!o) return 0
  const nowMs = new Date(o.now).getTime()
  return o.bucket_starts.filter((s) => new Date(s).getTime() <= nowMs).length
})

const cards = computed(() =>
  (overview.value?.categories ?? []).map((c) => ({
    ...c,
    meta: categoryMeta(c.code),
    trend: c.buckets.slice(0, elapsed.value),
    thresholdText: formatScore(c.threshold),
  })),
)
</script>

<template>
  <div class="stack">
    <p class="muted intro">{{ copy.panel.enginesNote }}.</p>
    <p v-if="failed && !overview" class="muted">{{ copy.panel.loadFailed }}</p>

    <div v-if="cards.length" class="grid">
      <div v-for="c in cards" :key="c.code" class="card engine">
        <div class="engine__head">
          <span class="engine__icon" :style="{ background: c.meta.tint, color: c.meta.ink }">
            <Icon :name="c.meta.icon" :size="22" />
          </span>
          <div class="engine__title">
            <div class="engine__name">{{ c.meta.label }}</div>
            <div class="meta">{{ c.meta.family }} · <span class="mono">{{ c.code }}</span></div>
          </div>
          <StatusDot :status="c.status" />
        </div>

        <div class="engine__stats">
          <div>
            <div class="engine__count num">{{ formatCount(c.total) }}</div>
            <div class="meta">{{ copy.engines.today }}</div>
          </div>
          <Sparkline class="engine__spark" :values="c.trend" :color="c.meta.color" />
        </div>

        <dl class="facts">
          <div class="fact">
            <dt>{{ copy.engines.module }}</dt>
            <dd class="mono">{{ c.module }}</dd>
          </div>
          <div class="fact">
            <dt>{{ copy.rules.columns.threshold }}</dt>
            <dd class="mono">{{ c.thresholdText ?? copy.panel.noThreshold }}</dd>
          </div>
          <div class="fact">
            <dt>{{ copy.engines.action }}</dt>
            <dd>{{ c.action ? actionLabel(c.action) : copy.panel.unavailable }}</dd>
          </div>
          <div class="fact">
            <dt>{{ copy.engines.thresholdSource }}</dt>
            <dd :class="{ 'fact--warn': !c.derived }">{{ c.derived ? copy.engines.derived : copy.engines.placeholder }}</dd>
          </div>
        </dl>

        <div class="engine__foot">
          <RouterLink :to="{ name: 'queue', query: { code: c.code, all: '1' } }" class="btn">{{ copy.engines.queue }}</RouterLink>
          <RouterLink :to="{ name: 'live' }" class="btn btn--secondary">{{ copy.engines.test }}</RouterLink>
        </div>
      </div>
    </div>
    <EmptyState v-else-if="overview" icon="brain" :title="overview.categories_error ?? copy.panel.enginesEmpty" />
  </div>
</template>

<style scoped>
.intro {
  margin: 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
.engine__head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.engine__icon {
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}
.engine__title {
  flex: 1;
  min-width: 0;
}
.engine__name {
  font-size: 16px;
  line-height: 24px;
  font-weight: 600;
  color: var(--text-heading);
}
.engine__stats {
  margin-top: 20px;
  display: flex;
  align-items: flex-end;
  gap: 24px;
}
.engine__count {
  font-size: 28px;
  line-height: 36px;
  font-weight: 700;
  color: var(--text-heading);
}
.engine__spark {
  flex: 1;
}
.facts {
  margin: 20px 0 0;
  padding-top: 16px;
  border-top: 1px solid var(--border-card);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 20px;
}
.fact dt {
  font-size: 12px;
  color: var(--text-meta);
}
.fact dd {
  margin: 2px 0 0;
  font-size: 14px;
  color: var(--text-primary);
}
.fact--warn {
  color: var(--warning) !important;
}
.engine__foot {
  margin-top: 20px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
@media (max-width: 1279px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
