<script setup lang="ts">
import { computed, ref } from 'vue'
import StageRow from '@/components/ui/StageRow.vue'
import EvidenceText from '@/components/ui/EvidenceText.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { codePoints } from '@/lib/spans'
import { copy } from '@/copy'
import type { InputStage } from '@/report/model'

/*
 * pages-spec stage 1: the submitted text exactly as typed, with its character
 * count, so the jury can see what was analysed is what was typed. Past about
 * 600 characters the display truncates with a control to expand; the full
 * string was still submitted and analysed.
 */
const TRUNCATE_AT = 600
const props = defineProps<{ stage: InputStage }>()

const expanded = ref(false)
const chars = computed(() => codePoints(props.stage.text))
const isLong = computed(() => chars.value.length > TRUNCATE_AT)
const shown = computed(() =>
  isLong.value && !expanded.value ? chars.value.slice(0, TRUNCATE_AT).join('') + '…' : props.stage.text,
)
</script>

<template>
  <StageRow :number="stage.number" :name="stage.name" :status="stage.status">
    <EvidenceText :text="shown" />
    <div class="stage-input__meta">
      <span>{{ chars.length }} {{ copy.stages.characters }}</span>
      <BaseButton v-if="isLong" variant="ghost" size="sm" @click="expanded = !expanded">
        {{ expanded ? copy.stages.showLess : copy.stages.showAll }}
      </BaseButton>
    </div>
  </StageRow>
</template>

<style scoped>
.stage-input__meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
