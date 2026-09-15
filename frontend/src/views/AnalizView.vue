<script setup lang="ts">
import { computed, ref } from 'vue'
import TextArea from '@/components/ui/TextArea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ProgressIndicator from '@/components/ui/ProgressIndicator.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import ReportView from '@/components/report/ReportView.vue'
import ConsequenceColumn from '@/components/report/ConsequenceColumn.vue'
import { analysisSource } from '@/api'
import { useAnalysis } from '@/report/useAnalysis'
import { copy } from '@/copy'

/*
 * pages-spec 2. Idle: text area, counter, primary button, presets beneath;
 * nothing else on the page. Analysing: button disabled with its progressive
 * label, progress indicator under the text area. Report: text area stays
 * editable above, report beneath in two columns.
 */
const text = ref('')
const { phase, result, errorText, analyze } = useAnalysis(analysisSource)

const canSubmit = computed(() => text.value.trim() !== '' && phase.value !== 'analysing')

function submit() {
  if (canSubmit.value) void analyze(text.value)
}

/** A preset fills the text area and does not submit: the judge sees the action. */
function usePreset(presetText: string) {
  text.value = presetText
}
</script>

<template>
  <div class="analiz">
    <h1 class="analiz__title">{{ copy.analiz.title }}</h1>

    <div class="analiz__input">
      <TextArea
        v-model="text"
        :placeholder="copy.analiz.placeholder"
        :label="copy.analiz.inputLabel"
        @submit="submit"
      >
        <template #actions>
          <BaseButton variant="primary" :disabled="!canSubmit" @click="submit">
            {{ phase === 'analysing' ? copy.analiz.submitting : copy.analiz.submit }}
          </BaseButton>
        </template>
      </TextArea>

      <ProgressIndicator v-if="phase === 'analysing'" class="analiz__progress" :label="copy.analiz.submitting" />

      <div class="analiz__presets" role="group" :aria-label="copy.analiz.presetsLabel">
        <BaseButton
          v-for="preset in analysisSource.presets"
          :key="preset.label"
          variant="secondary"
          @click="usePreset(preset.text)"
        >
          {{ preset.label }}
        </BaseButton>
      </div>
    </div>

    <div v-if="phase === 'report' || phase === 'error'" class="analiz__result">
      <div class="analiz__report">
        <ReportView v-if="phase === 'report' && result" :result="result" />
        <ErrorState v-else :line="errorText" :retry-label="copy.analiz.retry" @retry="submit" />
      </div>
      <ConsequenceColumn class="analiz__consequence" :result="phase === 'report' ? result : null" />
    </div>
  </div>
</template>

<style scoped>
.analiz__title {
  margin: 0 0 24px;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text-primary);
}
.analiz__progress {
  margin-top: 12px;
}
.analiz__presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
/* 3: report column flexible, consequence column fixed 360px, 32px gutter; 48px between major regions. */
.analiz__result {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--consequence-width);
  column-gap: 32px;
  margin-top: 48px;
  align-items: start;
}
.analiz__consequence {
  position: sticky;
  top: 32px;
}
</style>
