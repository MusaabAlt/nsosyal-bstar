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
 * Verdict block: the word, and beneath it one sentence naming what produced
 * the outcome (the decision layer's explanation, verbatim).
 *
 * Incomplete block: grey, never green, never "Temiz". In place of the single
 * sentence, a plain list of the parts that did not run, by name, and one
 * line stating how many of the sixteen categories were evaluated. That
 * number comes from the server (display.categories_evaluated); the decision
 * layer's sentence is still shown in stage 9.
 */
const props = defineProps<{ view: VerdictView; latencyMs: number }>()

const latency = computed(() => formatMs(props.latencyMs))
</script>

<template>
  <section class="verdict" :class="`verdict--${view.tone}`" aria-live="polite">
    <div class="verdict__main">
      <h2 class="verdict__word">{{ view.word }}</h2>

      <template v-if="view.tone === 'incomplete'">
        <p v-if="view.evaluated" class="verdict__sentence">
          {{ copy.verdict.evaluated(view.evaluated.total, view.evaluated.n) }}
        </p>
        <ul v-if="view.moduleStatusKnown" class="verdict__list" :aria-label="copy.verdict.notRunHeading">
          <li v-for="item in view.notRun" :key="item.module">{{ item.module }}</li>
        </ul>
        <p v-else class="verdict__sentence">{{ copy.verdict.moduleStatusMissing }}</p>
      </template>

      <p v-else class="verdict__sentence">{{ view.explanation }}</p>
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
.verdict__sentence {
  margin: 12px 0 0;
  max-width: 80ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
}
.verdict__list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
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
