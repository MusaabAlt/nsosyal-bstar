<script setup lang="ts">
import { computed } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import ScorePair from '@/components/ui/ScorePair.vue'
import { isValidSpan, codePointLength, type Mark } from '@/lib/spans'
import type { NormalizationStage } from '@/report/model'

/*
 * pages-spec stage 4, the most persuasive moment: it gets room.
 *
 * Shown: the original string with the obfuscated characters highlighted, and
 * the score pair (raw vs recovered) when the API supplies both scores.
 * Not shown: the recovered string and the "4 ayırıcı karakter kaldırıldı"
 * line. The response deliberately leaves the de-obfuscated text out
 * (HANDOVER decision 21), and the screen never reconstructs it.
 */
const props = defineProps<{ stage: NormalizationStage }>()

const marks = computed<Mark[]>(() => {
  const length = codePointLength(props.stage.text)
  return props.stage.patterns
    .filter((p) => isValidSpan(p.span, length))
    .map((p) => ({ span: p.span!, kind: 'highlight' as const }))
})
</script>

<template>
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status" :line="stage.line">
    <div v-if="stage.scorePair || marks.length > 0" class="stage-normalization">
      <EvidenceText v-if="marks.length > 0" :text="stage.text" :marks="marks" />
      <ScorePair v-if="stage.scorePair" :pair="stage.scorePair" />
    </div>
  </StageRow>
</template>

<style scoped>
.stage-normalization {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px 0;
}
</style>
