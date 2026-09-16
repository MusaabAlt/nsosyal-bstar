<script setup lang="ts">
import StageRow from '@/components/ui/StageRow.vue'
import ThresholdBar from '@/components/ui/ThresholdBar.vue'
import { guardLabel } from '@/contract/labels'
import { copy } from '@/copy'
import type { ContentStage } from '@/report/model'

/*
 * pages-spec stage 5: one threshold bar per category the API returned, fired
 * first, then near-misses, each by score descending. The BERTurk offensive
 * score (Genel saldırganlık) has its own bar against its own threshold. Sixteen rows never
 * render by default. Beneath the list, one line accounting for the rest,
 * "Eşik altındaki N kategori gösterilmiyor", linking to Kategoriler. N comes
 * from the server.
 */
defineProps<{ stage: ContentStage }>()
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :line="stage.rows.length > 0 ? null : stage.line"
  >
    <div v-if="stage.rows.length > 0" class="stage-content">
      <ThresholdBar
        v-for="(row, i) in stage.rows"
        :key="`${row.key}-${i}`"
        :label="row.label"
        :score="row.score"
        :threshold="row.threshold"
        :fired="row.fired"
        :margin="row.margin"
        :suppressed-by="row.suppressedBy ? guardLabel(row.suppressedBy.code) : null"
      />
    </div>
    <p v-if="stage.hidden !== null && stage.hidden > 0" class="stage-content__hidden">
      <RouterLink to="/kategoriler" class="stage-content__link">{{ copy.stages.hiddenCategories(stage.hidden) }}</RouterLink>
    </p>
  </StageRow>
</template>

<style scoped>
.stage-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.stage-content__hidden {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}
.stage-content__link {
  color: var(--text-muted);
  text-decoration: none;
  transition: color var(--motion-fast);
}
.stage-content__link:hover {
  color: var(--text-body);
}
.stage-content__link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
