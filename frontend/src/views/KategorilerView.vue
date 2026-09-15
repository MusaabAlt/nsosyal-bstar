<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import StatusWord from '@/components/ui/StatusWord.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { dataMode } from '@/api'
import { loadCategories, type Category, type CategoryList } from '@/api/categories'
import { contentLabel, familyLabel } from '@/contract/labels'
import { formatScore } from '@/lib/format'
import { copy } from '@/copy'
import type { Action, Family } from '@/contract/types'

/*
 * pages-spec 3: a static reference listing all sixteen content categories
 * with their thresholds. A table: code, Turkish label, one-line definition,
 * threshold, the action firing it produces, and whether that module is live
 * or still a stub. Grouped by family with a plain heading above each group.
 * No scores appear here.
 *
 * Code and label come from the contract (codes.py); threshold, action and
 * status from GET /api/categories, which reads AI/decision/thresholds.yaml
 * and the model service's health. No Turkish definitions exist yet, so that
 * column renders "veri yok".
 */
const state = ref<'loading' | 'ready' | 'error'>('loading')
const list = ref<CategoryList | null>(null)

const ACTION_WORD: Record<Action, string> = {
  block: copy.verdict.block,
  escalate: copy.verdict.review,
  review: copy.verdict.review,
  nudge: copy.verdict.sensitive,
  clean: copy.verdict.clean,
}

const FAMILY_ORDER: Family[] = ['A', 'B', 'C', 'D', 'CLEAN']

const groups = computed(() =>
  FAMILY_ORDER.map((family) => ({
    family,
    categories: (list.value?.categories ?? []).filter((c: Category) => c.family === family),
  })).filter((g) => g.categories.length > 0),
)

async function load() {
  state.value = 'loading'
  const outcome = await loadCategories(dataMode)
  if (outcome.ok) {
    list.value = outcome.list
    state.value = 'ready'
  } else {
    state.value = 'error'
  }
}

onMounted(load)
</script>

<template>
  <div class="kategoriler">
    <h1 class="kategoriler__title">{{ copy.kategoriler.title }}</h1>

    <ErrorState v-if="state === 'error'" :line="copy.kategoriler.loadError" :retry-label="copy.analiz.retry" @retry="load" />

    <template v-else-if="state === 'ready' && list">
      <p v-if="list.placeholder" class="kategoriler__note">{{ copy.kategoriler.placeholderNote }}</p>

      <section v-for="group in groups" :key="group.family" class="kategoriler__group">
        <h2 class="kategoriler__family">{{ familyLabel(group.family) }}</h2>
        <v-table class="kategoriler__table">
          <!-- Same column widths in every family table, so the groups line up. -->
          <colgroup>
            <col style="width: 8%" />
            <col style="width: 28%" />
            <col style="width: 22%" />
            <col style="width: 12%" />
            <col style="width: 14%" />
            <col style="width: 16%" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">{{ copy.kategoriler.columns.code }}</th>
              <th scope="col">{{ copy.kategoriler.columns.label }}</th>
              <th scope="col">{{ copy.kategoriler.columns.definition }}</th>
              <th scope="col" class="num">{{ copy.kategoriler.columns.threshold }}</th>
              <th scope="col">{{ copy.kategoriler.columns.action }}</th>
              <th scope="col">{{ copy.kategoriler.columns.module }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in group.categories" :key="c.code">
              <td class="code">{{ c.code }}</td>
              <td>{{ contentLabel(c.code) }}</td>
              <td><StatusWord status="noData" /></td>
              <td class="num">
                <template v-if="formatScore(c.threshold) !== null">{{ formatScore(c.threshold) }}</template>
                <StatusWord v-else status="noData" />
              </td>
              <td>
                <template v-if="c.action">{{ ACTION_WORD[c.action] }}</template>
                <StatusWord v-else status="noData" />
              </td>
              <td>
                <span v-if="c.status === 'live'">{{ copy.kategoriler.live }}</span>
                <StatusWord v-else :status="c.status === 'stub' ? 'moduleUnavailable' : 'noData'" />
              </td>
            </tr>
          </tbody>
        </v-table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.kategoriler__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text-primary);
}
.kategoriler__note {
  margin: 0 0 24px;
  max-width: 80ch;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}
.kategoriler__group + .kategoriler__group {
  margin-top: 48px;
}
.kategoriler__family {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-primary);
}

/* design-system 4.15 */
.kategoriler__table {
  background: transparent;
  color: var(--text-body);
  border-radius: 0;
}
.kategoriler__table :deep(table) {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}
.kategoriler__table :deep(thead th) {
  position: sticky;
  top: 0;
  height: 40px;
  padding: 0 16px 0 0;
  background: var(--surface-page);
  border-bottom: 1px solid var(--border-default);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  text-align: left;
}
.kategoriler__table :deep(tbody td) {
  height: 44px;
  padding: 0 16px 0 0;
  border-bottom: 1px solid var(--border-divider);
  font-size: 14px;
  color: var(--text-body);
}
.kategoriler__table :deep(tbody tr:hover > td) {
  background: transparent;
}
.kategoriler__table :deep(.num) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
/* A right-aligned column followed by a left-aligned one needs its own gap. */
.kategoriler__table :deep(.num + th),
.kategoriler__table :deep(.num + td) {
  padding-left: 24px;
}
.kategoriler__table :deep(.code) {
  color: var(--text-primary);
  font-weight: 500;
}
</style>
