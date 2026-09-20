<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'
import Icon from '@/components/Icon.vue'
import StatusDot from '@/components/panel/StatusDot.vue'
import EmptyState from '@/components/panel/EmptyState.vue'
import { copy } from '@/copy'
import { fetchCategories, type CategoryList } from '@/api/panel'
import { categoryMeta } from '@/lib/categories'
import { formatScore } from '@/lib/format'
import { actionLabel } from '@/contract/labels'

/*
 * S5 Kurallar & Eşikler, read-only: every category's own threshold and
 * action as the decision layer is configured. Editing lives in the AI
 * configuration, not in this panel.
 */
const list = shallowRef<CategoryList | null>(null)
const failed = ref(false)

async function load() {
  const out = await fetchCategories()
  failed.value = !out.ok
  if (out.ok) list.value = out.data
}
onMounted(load)
</script>

<template>
  <div class="stack">
    <div class="card note">
      <Icon name="info" :size="20" class="note__icon" />
      <div>
        <p class="note__text">{{ copy.rules.note }}</p>
        <p v-if="list" class="meta note__source">{{ copy.rules.source(list.source) }}</p>
      </div>
    </div>

    <div v-if="failed" class="card failed">
      <span class="muted">{{ copy.panel.loadFailed }}</span>
      <button type="button" class="btn" @click="load">{{ copy.panel.retry }}</button>
    </div>

    <div v-else-if="list && list.categories.length" class="card">
      <table class="table table--stack">
        <thead>
          <tr>
            <th>{{ copy.rules.columns.category }}</th>
            <th>{{ copy.rules.columns.code }}</th>
            <th>{{ copy.rules.columns.family }}</th>
            <th>{{ copy.rules.columns.threshold }}</th>
            <th>{{ copy.rules.columns.action }}</th>
            <th>{{ copy.rules.columns.module }}</th>
            <th>{{ copy.rules.columns.source }}</th>
            <th>{{ copy.rules.columns.status }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in list.categories" :key="c.code">
            <td>
              <span class="cat">
                <span class="cat__dot" :style="{ background: categoryMeta(c.code).color }" />
                {{ categoryMeta(c.code).label }}
              </span>
            </td>
            <td class="mono" :data-label="copy.rules.columns.code">{{ c.code }}</td>
            <td :data-label="copy.rules.columns.family">{{ categoryMeta(c.code).family }}</td>
            <td class="mono num" :data-label="copy.rules.columns.threshold">
              <template v-if="c.threshold !== null">{{ formatScore(c.threshold) }}</template>
              <span v-else class="unavailable">{{ copy.panel.unavailable }}</span>
            </td>
            <td :data-label="copy.rules.columns.action">
              <template v-if="c.action">{{ actionLabel(c.action) }}</template>
              <span v-else class="unavailable">{{ copy.panel.unavailable }}</span>
            </td>
            <td class="mono" :data-label="copy.rules.columns.module">{{ c.module }}</td>
            <td :data-label="copy.rules.columns.source" :class="{ warn: !c.derived }">{{ c.derived ? copy.engines.derived : copy.engines.placeholder }}</td>
            <td :data-label="copy.rules.columns.status"><StatusDot :status="c.status" /></td>
          </tr>
        </tbody>
      </table>
    </div>
    <EmptyState v-else-if="list" icon="sliders" :title="copy.panel.enginesEmpty" />
  </div>
</template>

<style scoped>
.note {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.note__icon {
  color: var(--accent);
  margin-top: 2px;
}
.note__text {
  margin: 0;
  font-size: 15px;
  line-height: 24px;
  color: var(--text-primary);
  max-width: 80ch;
}
.note__source {
  margin: 8px 0 0;
}
.failed {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cat {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}
.cat__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}
.warn {
  color: var(--warning) !important;
}

/* ------------------------------------------------------------------ phone */
@media (max-width: 599px) {
  .note {
    gap: 10px;
  }
  .note__text {
    font-size: 14px;
    line-height: 22px;
  }
  .failed {
    flex-wrap: wrap;
    gap: 12px;
  }
  /* The category name is the card's heading, so its colour dot leads it. */
  .cat {
    font-weight: 600;
  }
}
</style>
