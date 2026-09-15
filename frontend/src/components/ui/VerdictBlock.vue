<script setup lang="ts">
import { computed } from 'vue'
import { formatMs } from '@/lib/format'
import { copy } from '@/copy'
import type { VerdictView } from '@/report/model'

/*
 * design-system 4.11 (verdict block) and 4.12 (incomplete evaluation block).
 * The verdict and the latency are the largest elements on screen and sit at
 * the top (pages-spec 2.3). No left accent bar.
 *
 * Incomplete: grey, never green, never "Temiz". In place of the single
 * sentence it lists the parts that did not run, by name. The line
 * "16 kategoriden N'i değerlendirildi" from 4.12 is not shown: the response
 * does not carry N, and the screen computes no totals (design-system 6).
 * The explanation is kept beneath the list, verbatim, because under
 * degradation a more severe verdict can still stand and only the decision
 * layer's sentence says so.
 */
const props = defineProps<{ view: VerdictView; latencyMs: number }>()

const latency = computed(() => formatMs(props.latencyMs))
</script>

<template>
  <section class="verdict" :class="`verdict--${view.tone}`" aria-live="polite">
    <div class="verdict__main">
      <h2 class="verdict__word">{{ view.word }}</h2>

      <template v-if="view.tone === 'incomplete'">
        <template v-if="view.moduleStatusKnown">
          <p class="verdict__list-heading">{{ copy.verdict.notRunHeading }}</p>
          <ul class="verdict__list">
            <li v-for="item in view.notRun" :key="item.module">
              {{ item.module }} <span class="verdict__kinds">{{ item.kinds.join(', ') }}</span>
            </li>
          </ul>
        </template>
        <p v-else class="verdict__sentence">{{ copy.verdict.moduleStatusMissing }}</p>
      </template>

      <p class="verdict__sentence">{{ view.explanation }}</p>
    </div>

    <div class="verdict__metric" :aria-label="copy.verdict.latencyLabel">
      <template v-if="latency !== null">
        <span class="verdict__metric-value">{{ latency }}</span>
        <span class="verdict__metric-unit">ms</span>
      </template>
      <span v-else class="verdict__metric-missing">{{ copy.status.noData }}</span>
    </div>
  </section>
</template>

<style scoped>
.verdict {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  padding: 24px;
  border: 1px solid var(--tone);
  border-radius: var(--radius-control);
  background: var(--tone-bg);
}
.verdict--block {
  --tone: var(--status-block);
  --tone-bg: var(--status-block-bg);
}
.verdict--review {
  --tone: var(--status-review);
  --tone-bg: var(--status-review-bg);
}
.verdict--clean {
  --tone: var(--status-clean);
  --tone-bg: var(--status-clean-bg);
}
.verdict--incomplete {
  --tone: var(--status-incomplete);
  --tone-bg: var(--status-incomplete-bg);
}
.verdict__main {
  min-width: 0;
}
.verdict__word {
  margin: 0;
  font-size: 40px;
  font-weight: 600;
  line-height: 1.15;
  color: var(--tone);
}
.verdict__sentence,
.verdict__list-heading {
  margin: 12px 0 0;
  max-width: 80ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.verdict__list {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.verdict__kinds {
  color: var(--text-muted);
}
.verdict__metric {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}
.verdict__metric-value {
  font-size: 32px;
  font-weight: 500;
  line-height: 1.2;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.verdict__metric-unit {
  font-size: 14px;
  color: var(--text-muted);
}
.verdict__metric-missing {
  font-size: 13px;
  font-style: italic;
  color: var(--status-incomplete);
}
</style>
