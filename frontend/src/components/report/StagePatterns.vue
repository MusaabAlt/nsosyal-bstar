<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import StatusWord from '@/components/ui/StatusWord.vue'
import { formLabel } from '@/contract/labels'
import { formatScore } from '@/lib/format'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import { copy } from '@/copy'
import type { PatternStage } from '@/report/model'

/*
 * pages-spec stages 2 (Karakter güvenliği) and 3 (Gizleme tespiti). One row
 * per detected pattern: Turkish pattern name, the exact substring that
 * triggered it, and the module's confidence to two decimals. Patterns the
 * decision layer marked active show "tetiklendi"; the rest "eşik altında".
 *
 * Stage 2 asks for each character's Unicode name and stage 3 for
 * "Kontrol edilen diğer N kalıpta eşleşme yok": the response carries neither,
 * so neither is shown (design-system 6).
 */
const props = defineProps<{ stage: PatternStage }>()

const marks = computed<Mark[]>(() => {
  const length = codePointLength(props.stage.text)
  return props.stage.patterns
    .filter((p) => isValidSpan(p.span, length))
    .map((p) => ({ span: p.span!, kind: 'highlight' as const }))
})
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :duration-ms="stage.durationMs"
    :line="stage.line"
  >
    <template v-if="stage.patterns.length > 0">
      <EvidenceText v-if="marks.length > 0" :text="stage.text" :marks="marks" />
      <table class="patterns">
        <tbody>
          <tr v-for="(p, i) in stage.patterns" :key="`${p.code}-${i}`">
            <th scope="row" class="patterns__name">{{ formLabel(p.code) }}</th>
            <td class="patterns__evidence">{{ p.evidence }}</td>
            <td class="patterns__confidence">
              {{ formatScore(p.confidence) ?? copy.status.noData }}
              <span class="patterns__unit">{{ copy.stages.confidence }}</span>
            </td>
            <td class="patterns__status"><StatusWord :status="p.active ? 'triggered' : 'below'" /></td>
          </tr>
        </tbody>
      </table>
    </template>
  </StageRow>
</template>

<style scoped>
.patterns {
  width: 100%;
  margin-top: 12px;
  border-collapse: collapse;
}
.patterns tr {
  border-bottom: 1px solid var(--border-divider);
}
.patterns tr:last-child {
  border-bottom: none;
}
.patterns th,
.patterns td {
  padding: 8px 16px 8px 0;
  text-align: left;
  font-size: 14px;
  line-height: 1.5;
  vertical-align: baseline;
}
.patterns__name {
  font-weight: 500;
  color: var(--text-primary);
}
.patterns__evidence {
  color: var(--text-body);
  unicode-bidi: plaintext;
}
.patterns__confidence {
  text-align: right;
  color: var(--text-body);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.patterns__unit {
  font-size: 12px;
  color: var(--text-muted);
}
.patterns__status {
  text-align: right;
  width: 1%;
}
</style>
