<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from './Icon.vue'
import SystemRail from './SystemRail.vue'
import LiveDock from './LiveDock.vue'
import { routes } from '@/router'
import { copy } from '@/copy'
import { formatCount } from '@/lib/format'
import { useTheme } from '@/composables/useTheme'
import { usePoll } from '@/composables/usePoll'
import { liveOverview, liveOverviewFailed, refreshLiveOverview } from '@/composables/useLiveOverview'
import { representative } from '@/api/representative'

/*
 * The NSosyal-style shell from the ATI-SOSYAL Paneli design: sticky pill
 * sidebar with the gradient CTA and the theme switch, a sticky header with
 * the page title, the page's own tabs (teleported into #page-tabs), search
 * and the operator avatar; the Sistem durumu rail on wide screens; the Canlı
 * Akış dock bottom-right.
 */
const route = useRoute()
const router = useRouter()
const { dark, toggle } = useTheme()

usePoll(refreshLiveOverview, 5000)

const navItems = computed(() =>
  routes
    .filter((r) => 'name' in r && r.meta?.icon)
    .map((r) => ({
      name: r.name as string,
      path: r.path,
      label: r.meta!.title,
      icon: r.meta!.icon!,
      badge: r.name === 'queue' ? liveOverview.value?.queue.pending_detected ?? null : null,
    })),
)

const title = computed(() => route.meta.title ?? '')
const showRail = computed(() => route.meta.rail === true)

const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
watch(
  () => route.query.q,
  (q) => {
    if (route.name === 'history') search.value = typeof q === 'string' ? q : ''
  },
)
function submitSearch() {
  const q = search.value.trim()
  void router.push({ name: 'history', query: q ? { q } : {} })
}
</script>

<template>
  <v-app class="shell">
    <aside class="sidebar">
      <RouterLink to="/" class="sidebar__brand">{{ copy.app.brand }}</RouterLink>

      <nav class="sidebar__nav" :aria-label="copy.app.brand">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="item.path"
          class="nav-item"
          :class="{ 'nav-item--active': route.name === item.name }"
        >
          <span class="nav-item__icon">
            <Icon :name="item.icon" />
            <span v-if="item.badge" class="nav-item__badge num">{{ item.badge > 99 ? '99+' : formatCount(item.badge) }}</span>
          </span>
          <span class="nav-item__label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <RouterLink to="/analiz" class="btn btn--brand sidebar__cta">
        <Icon name="sparkle" :size="20" />
        {{ copy.app.analyzeCta }}
      </RouterLink>

      <div class="sidebar__divider" />

      <div class="nav-item nav-item--static">
        <Icon name="moon" />
        <span class="nav-item__label">{{ copy.app.darkMode }}</span>
        <button
          type="button"
          role="switch"
          class="switch"
          :class="{ 'switch--on': dark }"
          :aria-checked="dark"
          :aria-label="copy.app.darkMode"
          @click="toggle"
        >
          <span class="switch__thumb" />
        </button>
      </div>
    </aside>

    <div class="main">
      <header class="header">
        <h1 class="header__title">{{ title }}</h1>
        <div id="page-tabs" class="header__tabs" />
        <div class="header__right">
          <form class="search" role="search" @submit.prevent="submitSearch">
            <div class="search__inner">
              <Icon name="search" :size="16" :stroke="1.8" class="search__icon" />
              <input
                v-model="search"
                type="search"
                class="search__input"
                :placeholder="copy.app.searchPlaceholder"
                :aria-label="copy.app.searchLabel"
                maxlength="200"
              />
            </div>
          </form>
          <span class="avatar" :title="copy.app.operator">OP</span>
        </div>
      </header>

      <p v-if="liveOverviewFailed" class="offline" role="status">{{ copy.app.unreachable }}</p>

      <div class="body">
        <main class="content">
          <RouterView :key="route.name as string" />
        </main>
        <SystemRail v-if="showRail" class="rail" />
      </div>
    </div>

    <LiveDock />
    <div v-if="representative" class="demo-marker">{{ copy.app.demoMarker }}</div>
  </v-app>
</template>

<style scoped>
.shell :deep(.v-application__wrap) {
  display: flex;
  flex-direction: row;
  min-height: 100vh;
}

.sidebar {
  width: var(--sidebar-width);
  flex: none;
  padding: 24px;
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}
.sidebar__brand {
  flex: none;
  height: 48px;
  display: flex;
  align-items: center;
  padding-left: 12px;
  margin-bottom: 24px;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  width: fit-content;
}
.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sidebar__cta {
  flex: none;
  margin-top: 16px;
  width: 100%;
  font-size: 16px;
  font-weight: 400;
}
.sidebar__cta:hover {
  color: var(--text-on-accent);
}
.sidebar__divider {
  flex: none;
  height: 1px;
  background: var(--border-divider);
  margin: 16px 12px;
}

.nav-item {
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  width: 100%;
  padding: 0 10px 0 12px;
  border-radius: var(--radius-full);
  font-size: 15px;
  color: var(--text-primary);
  transition: background-color 0.15s, color 0.15s;
}
.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-nav-hover);
}
.nav-item--static:hover {
  background: transparent;
}
.nav-item--active {
  background: var(--bg-nav-active);
  color: var(--text-heading);
  font-weight: 500;
}
.nav-item--active .nav-item__icon {
  color: var(--accent);
}
.nav-item__icon {
  position: relative;
  display: inline-flex;
}
.nav-item__badge {
  position: absolute;
  top: -5px;
  right: -9px;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: var(--radius-full);
  background: var(--badge);
  color: var(--text-on-accent);
  font-size: 10px;
  font-weight: 600;
  line-height: 17px;
  text-align: center;
}
.nav-item__label {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.switch {
  flex: none;
  width: 36px;
  height: 20px;
  border: 0;
  border-radius: var(--radius-full);
  cursor: pointer;
  padding: 2px;
  display: flex;
  justify-content: flex-start;
  background: var(--btn-neutral);
  transition: background-color 0.15s;
}
.switch--on {
  background: var(--accent);
  justify-content: flex-end;
}
.switch__thumb {
  width: 16px;
  height: 16px;
  border-radius: var(--radius-full);
  background: var(--text-on-accent);
  display: block;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.header {
  position: sticky;
  top: 0;
  z-index: 10;
  height: var(--header-height);
  flex: none;
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-card);
}
.header__title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 28px;
  color: var(--text-heading);
  white-space: nowrap;
}
.header__tabs {
  display: flex;
  align-items: stretch;
  height: var(--header-height);
  min-width: 0;
}
.header__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}
.search {
  width: 280px;
  height: 38px;
  border-radius: var(--radius-full);
  padding: 1px;
  background: var(--brand-gradient);
}
.search__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--bg-page);
  padding: 0 12px;
}
.search__icon {
  color: var(--text-muted);
}
.search__input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.offline {
  margin: 16px 24px 0;
  padding: 10px 16px;
  border-radius: var(--radius-lg);
  background: var(--danger-subtle);
  color: var(--danger);
  font-size: 14px;
}

.body {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 24px 24px 96px;
}
.content {
  flex: 1;
  min-width: 0;
  max-width: var(--content-max);
}
.rail {
  width: var(--rail-width);
  flex: none;
  position: sticky;
  top: calc(var(--header-height) + 24px);
}

.demo-marker {
  position: fixed;
  left: 24px;
  bottom: 24px;
  z-index: 30;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--warning);
  border: 1px solid var(--warning);
  border-radius: var(--radius-full);
  background: var(--bg-page);
}

@media (max-width: 1439px) {
  .rail {
    display: none;
  }
}
@media (max-width: 1279px) {
  .sidebar {
    width: 88px;
    padding: 24px 16px;
  }
  .sidebar__brand,
  .nav-item__label,
  .sidebar__cta {
    font-size: 0;
  }
  .sidebar__brand {
    display: none;
  }
  .nav-item {
    justify-content: center;
    padding: 0;
  }
  .nav-item--static {
    flex-direction: column;
    height: auto;
    gap: 8px;
  }
  .nav-item__label {
    display: none;
  }
  .search {
    width: 200px;
  }
}
</style>
