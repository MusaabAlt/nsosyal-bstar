<script setup lang="ts">
/*
 * Inline SVG icons for the NSosyal interaction row, left to right: comment,
 * repost, rocket (NSosyal's "like", not a heart), analytics, bookmark, share
 * (nsosyal-design-tokens.md 5). Drawn here, so nothing is fetched (9.2).
 */
export type PostIconName = 'comment' | 'repost' | 'rocket' | 'stats' | 'bookmark' | 'share'
defineProps<{ name: PostIconName }>()
</script>

<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="name === 'comment'">
      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12Z" />
    </template>
    <template v-else-if="name === 'repost'">
      <path d="M17 2.5 20.5 6 17 9.5" />
      <path d="M3.5 11V9.5A3.5 3.5 0 0 1 7 6h13.5" />
      <path d="M7 21.5 3.5 18 7 14.5" />
      <path d="M20.5 13v1.5A3.5 3.5 0 0 1 17 18H3.5" />
    </template>
    <template v-else-if="name === 'rocket'">
      <path d="M12 15.5 8.5 12c1.8-5 5.2-8.3 11.5-9 -.7 6.3-4 9.7-8 12.5Z" />
      <path d="M8.5 12 5 11.5l2.5-3.5h4" />
      <path d="M12 15.5l.5 3.5 3.5-2.5v-4" />
      <path d="M6.5 15.5c-1.5.5-2.5 2.5-2.5 4.5 2 0 4-1 4.5-2.5" />
    </template>
    <template v-else-if="name === 'stats'">
      <path d="M4 20h16" />
      <path d="M7 16v-5" />
      <path d="M12 16V6" />
      <path d="M17 16v-8" />
    </template>
    <template v-else-if="name === 'bookmark'">
      <path d="M6.5 3.5h11v17L12 16.5l-5.5 4Z" />
    </template>
    <template v-else>
      <path d="M12 3.5v12" />
      <path d="M7.5 8 12 3.5 16.5 8" />
      <path d="M4.5 13v5.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V13" />
    </template>
  </svg>
</template>
