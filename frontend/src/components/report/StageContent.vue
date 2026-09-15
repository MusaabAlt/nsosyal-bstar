<script setup lang="ts">
import StageRow from '@/components/ui/StageRow.vue'
import ThresholdBar from '@/components/ui/ThresholdBar.vue'
import { contentLabel, guardLabel } from '@/contract/labels'
import type { ContentStage } from '@/report/model'

/*
 * pages-spec stage 5: one threshold bar per category the API returned, fired
 * first, then the rest, each by score. Sixteen rows never render by default.
 *
 * "Eşik altındaki N kategori gösterilmiyor" is not shown: N is not in the
 * response and the screen computes no totals. Kategoriler lists all sixteen.
 */
defineProps<{ stage: ContentStage }>()
</script>

<template>
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status" :line="stage.line">
    <div v-if="stage.rows.length > 0" class="stage-content">
      <ThresholdBar
        v-for="(row, i) in stage.rows"
        :key="`${row.entry.code}-${row.entry.source}-${i}`"
        :label="contentLabel(row.entry.code)"
        :code="row.entry.code"
        :score="row.entry.score"
        :threshold="row.entry.threshold"
        :fired="row.entry.fired"
        :suppressed-by="row.suppressedBy ? guardLabel(row.suppressedBy.code) : null"
      />
    </div>
  </StageRow>
</template>

<style scoped>
.stage-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
</style>
