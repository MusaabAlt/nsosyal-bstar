<script setup lang="ts">
import { onMounted } from 'vue'
import NavItem from '@/components/ui/NavItem.vue'
import DemoMarker from '@/components/ui/DemoMarker.vue'
import { dataMode } from '@/api'
import { loadRepresentative } from '@/api/httpSource'
import { representative, setRepresentative } from '@/api/representative'
import { copy } from '@/copy'

/*
 * pages-spec 1 and design-system 3: fixed 220px sidebar with a plain-text
 * heading (no logo, version, avatar or settings icon) and two routes; the
 * content column is max 1280px, centred, 32px side padding.
 *
 * The Temsili veri marker (4.19) is shown while sample data is rendered: in
 * sample mode always, against the API whenever the model service says its
 * data is representative (the mock inference service).
 */
onMounted(() => {
  if (dataMode === 'mock') setRepresentative(true)
  else void loadRepresentative()
})
</script>

<template>
  <v-app class="shell">
    <nav class="shell__sidebar" :aria-label="copy.app.sidebarHeading">
      <p class="shell__heading">{{ copy.app.sidebarHeading }}</p>
      <NavItem to="/" :label="copy.app.navAnaliz" />
      <NavItem to="/kategoriler" :label="copy.app.navKategoriler" />
    </nav>
    <main class="shell__main">
      <div class="shell__content">
        <RouterView />
      </div>
    </main>
    <DemoMarker v-if="representative" />
  </v-app>
</template>

<style scoped>
.shell :deep(.v-application__wrap) {
  display: block;
  min-height: 100vh;
}
.shell__sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--sidebar-width);
  padding-top: 32px;
  background: var(--surface-raised);
  border-right: 1px solid var(--border-default);
}
.shell__heading {
  margin: 0 0 24px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--text-muted);
}
.shell__main {
  margin-left: var(--sidebar-width);
  min-height: 100vh;
}
.shell__content {
  max-width: var(--content-max);
  margin: 0 auto;
  padding: 32px;
}
</style>
