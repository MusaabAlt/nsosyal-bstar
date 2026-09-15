<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import MockPost from './MockPost.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { consequenceView } from '@/report/model'
import { copy } from '@/copy'
import type { AnalysisResult } from '@/contract/types'

/*
 * pages-spec 2.5: "so what happens to the post". This column contains no
 * numbers; it is where a non-technical juror looks.
 *   Temiz                     the post renders normally
 *   İncele                    a muted line above: queued for review
 *   Hassas içerik             NSosyal's sensitive-content treatment + Göster
 *   Engelle                   the post does not render; one muted line
 *   Değerlendirme tamamlanmadı the post renders with a muted line that it
 *                             was not cleared
 */
const props = defineProps<{ result: AnalysisResult | null }>()

const view = computed(() => (props.result ? consequenceView(props.result) : null))
const revealed = ref(false)
watch(
  () => props.result,
  () => (revealed.value = false),
)
</script>

<template>
  <aside class="consequence" :aria-label="copy.consequence.heading">
    <h2 class="consequence__heading">{{ copy.consequence.heading }}</h2>

    <EmptyState v-if="!result || !view" :line="copy.consequence.idle" />

    <template v-else>
      <p v-if="view.incomplete" class="consequence__note">{{ copy.consequence.incomplete }}</p>
      <p v-else-if="view.mode === 'queued'" class="consequence__note">{{ copy.consequence.queued }}</p>

      <p v-if="view.mode === 'withheld'" class="consequence__note">{{ copy.consequence.withheld }}</p>

      <MockPost v-else :text="result.text">
        <template v-if="view.mode === 'sensitive' && !revealed" #default="{ text }">
          <div class="sensitive">
            <p class="sensitive__text" aria-hidden="true">{{ text }}</p>
            <div class="sensitive__scrim">
              <p class="sensitive__message">{{ copy.consequence.sensitive }}</p>
              <BaseButton variant="secondary" size="sm" @click="revealed = true">{{ copy.consequence.show }}</BaseButton>
            </div>
          </div>
        </template>
      </MockPost>
    </template>
  </aside>
</template>

<style scoped>
.consequence__heading {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-primary);
}
.consequence__note {
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}
.sensitive {
  position: relative;
  min-height: 120px;
}
.sensitive__text {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
  filter: blur(var(--sensitive-blur));
  user-select: none;
  overflow-wrap: anywhere;
}
.sensitive__scrim {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: var(--sensitive-scrim);
}
.sensitive__message {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-body);
}
</style>
