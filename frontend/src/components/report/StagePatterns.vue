<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import { formLabel } from '@/contract/labels'
import { formatScore } from '@/lib/format'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import { copy } from '@/copy'
import type { PatternStage } from '@/report/model'

/*
 * pages-spec stage 2 (Karakter güvenliği):
 *   Found: each character rendered in position within the string,
 *   highlighted, with its Unicode name beside it. m0's evidence carries the
 *   Unicode names ("removed 1x [ZERO WIDTH SPACE] ...") and is shown verbatim.
 *   None: "Şüpheli karakter bulunamadı".
 *
 * pages-spec stage 3 (Gizleme tespiti):
 *   One row per detected pattern: the Turkish pattern name, the exact
 *   substring that triggered it, and the module's confidence to two decimals.
 *   Beneath the list: "Kontrol edilen diğer N kalıpta eşleşme yok", N from
 *   the server.
 */
const props = defineProps<{ stage: PatternStage }>()

const marks = computed<Mark[]>(() => {
  const length = codePointLength(props.stage.text)
  return props.stage.patterns
    .filter((p) => isValidSpan(p.span, length))
    .map((p) => ({ span: p.span!, kind: 'highlight' as const }))
})

const checkedLine = computed(() =>
  props.stage.kind === 'obfuscation' && props.stage.checkedOther !== null
    ? copy.stages.patternsCheckedOther(props.stage.checkedOther)
    : null,
)
</script>

<template>
  <StageRow
    :number="stage.number"
    :name="stage.name"
    :status="stage.status"
    :duration-ms="stage.durationMs"
    :line="stage.patterns.length > 0 ? checkedLine : (checkedLine ?? stage.line)"
  >
    <template v-if="stage.patterns.length > 0">
      <EvidenceText v-if="marks.length > 0" :text="stage.text" :marks="marks" />

      <table v-if="stage.kind === 'obfuscation'" class="patterns">
        <tbody>
          <tr v-for="(p, i) in stage.patterns" :key="`${p.code}-${i}`">
            <th scope="row" class="patterns__name">{{ formLabel(p.code) }}</th>
            <td class="patterns__evidence">{{ p.evidence }}</td>
            <td class="patterns__confidence">{{ formatScore(p.confidence) ?? copy.status.noData }}</td>
          </tr>
        </tbody>
      </table>

      <ul v-else class="characters">
        <li v-for="(p, i) in stage.patterns" :key="`${p.code}-${i}`">
          <span class="characters__name">{{ formLabel(p.code) }}</span>
          <span class="characters__evidence">{{ p.evidence }}</span>
        </li>
      </ul>
    </template>
  </StageRow>
</template>

<style scoped>
.patterns {
  width: 100%;
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
  width: 1%;
  padding-right: 0;
  text-align: right;
  color: var(--text-body);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.characters {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.characters li {
  display: flex;
  gap: 16px;
  font-size: 14px;
  line-height: 1.5;
}
.characters__name {
  flex-shrink: 0;
  font-weight: 500;
  color: var(--text-primary);
}
.characters__evidence {
  color: var(--text-body);
  overflow-wrap: anywhere;
}
</style>
