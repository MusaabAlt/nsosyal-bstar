<script setup lang="ts">
import IconButton from '@/components/ui/IconButton.vue'
import PostIcon, { type PostIconName } from '@/components/icons/PostIcon.vue'
import { copy } from '@/copy'

/*
 * The analysed text as an end user would see it on NSosyal (pages-spec 2.5,
 * nsosyal-design-tokens.md 2 and 5): round 33px avatar, display name, handle,
 * timestamp, body, interaction row. A full-width row with a divider beneath:
 * NSosyal posts are not cards, so no radius and no border box.
 */
defineProps<{ text: string }>()

const actions: Array<{ name: PostIconName; label: string }> = [
  { name: 'comment', label: copy.consequence.actions.comment },
  { name: 'repost', label: copy.consequence.actions.repost },
  { name: 'rocket', label: copy.consequence.actions.rocket },
  { name: 'stats', label: copy.consequence.actions.stats },
  { name: 'bookmark', label: copy.consequence.actions.bookmark },
  { name: 'share', label: copy.consequence.actions.share },
]
</script>

<template>
  <div class="post">
    <div class="post__avatar" aria-hidden="true" />
    <div class="post__main">
      <div class="post__meta">
        <span class="post__name">{{ copy.consequence.displayName }}</span>
        <span class="post__muted">{{ copy.consequence.handle }}</span>
        <span class="post__muted">·</span>
        <span class="post__muted">{{ copy.consequence.timestamp }}</span>
      </div>
      <div class="post__body">
        <slot :text="text">
          <p class="post__text" dir="auto">{{ text }}</p>
        </slot>
      </div>
      <div class="post__actions">
        <IconButton v-for="a in actions" :key="a.name" :label="a.label">
          <PostIcon :name="a.name" />
        </IconButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.post {
  display: flex;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-divider);
}
.post__avatar {
  flex-shrink: 0;
  width: 33px;
  height: 33px;
  border-radius: 50%;
  background: var(--surface-hover);
}
.post__main {
  min-width: 0;
  flex: 1;
}
.post__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  font-size: 14px;
  line-height: 1.4;
}
.post__name {
  font-weight: 500;
  color: var(--text-primary);
}
.post__muted {
  color: var(--text-muted);
}
.post__body {
  margin-top: 4px;
}
.post__text {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: var(--text-body);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  unicode-bidi: plaintext;
  display: -webkit-box;
  -webkit-line-clamp: 12;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.post__actions {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  margin-left: -4px;
}
</style>
