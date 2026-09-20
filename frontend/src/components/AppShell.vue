<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
 *
 * On a phone (<= 899px) the same sidebar becomes an off-canvas drawer behind
 * the header's menu button: seven navigation items with long Turkish labels
 * do not survive being squeezed into a rail, and the drawer keeps the labels,
 * the analyse CTA and the theme switch exactly as they are on a desktop. The
 * header then stacks - title row, search row when asked for, tabs strip - so
 * the page itself keeps the full width of the screen.
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

// --------------------------------------------------------- phone chrome

/** The drawer and the expanding search exist on narrow screens only. */
const menuOpen = ref(false)
const searchOpen = ref(false)
const searchInput = ref<HTMLInputElement | null>(null)

// Navigating is the whole point of the drawer, so it closes itself on arrival.
watch(() => route.fullPath, () => (menuOpen.value = false))

function onEscape(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  menuOpen.value = false
  searchOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onEscape))
onBeforeUnmount(() => window.removeEventListener('keydown', onEscape))

async function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (!searchOpen.value) return
  await nextTick()
  searchInput.value?.focus()
}

// ------------------------------------------------------------------ search

const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
watch(
  () => route.query.q,
  (q) => {
    if (route.name === 'history') search.value = typeof q === 'string' ? q : ''
  },
)
function submitSearch() {
  const q = search.value.trim()
  searchOpen.value = false
  void router.push({ name: 'history', query: q ? { q } : {} })
}
</script>

<template>
  <v-app class="shell">
    <!-- Closes the drawer by tapping the page; inert on wide screens. -->
    <div v-if="menuOpen" class="scrim" @click="menuOpen = false" />

    <aside class="sidebar" :class="{ 'sidebar--open': menuOpen }">
      <div class="sidebar__top">
        <RouterLink to="/" class="sidebar__brand">{{ copy.app.brand }}</RouterLink>
        <button
          type="button"
          class="icon-btn sidebar__close"
          :aria-label="copy.app.closeMenu"
          @click="menuOpen = false"
        >
          <Icon name="x" :size="20" :stroke="1.8" />
        </button>
      </div>

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
        <button
          type="button"
          class="icon-btn header__menu"
          :aria-label="copy.app.openMenu"
          :aria-expanded="menuOpen"
          @click="menuOpen = true"
        >
          <Icon name="menu" :size="22" :stroke="1.8" />
        </button>

        <h1 class="header__title">{{ title }}</h1>
        <div v-if="representative" class="demo-marker">{{ copy.app.demoMarker }}</div>

        <div id="page-tabs" class="header__tabs" />

        <div class="header__right">
          <button
            type="button"
            class="icon-btn header__search-toggle"
            :aria-label="copy.app.searchLabel"
            :aria-expanded="searchOpen"
            @click="toggleSearch"
          >
            <Icon :name="searchOpen ? 'x' : 'search'" :size="18" :stroke="1.8" />
          </button>
          <span class="avatar" :title="copy.app.operator">OP</span>
        </div>

        <form class="search" :class="{ 'search--open': searchOpen }" role="search" @submit.prevent="submitSearch">
          <div class="search__inner">
            <Icon name="search" :size="16" :stroke="1.8" class="search__icon" />
            <input
              ref="searchInput"
              v-model="search"
              type="search"
              class="search__input"
              :placeholder="copy.app.searchPlaceholder"
              :aria-label="copy.app.searchLabel"
              maxlength="200"
            />
          </div>
        </form>
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
.sidebar__top {
  display: flex;
  align-items: center;
  gap: 8px;
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
.sidebar__close {
  display: none;
  margin: 0 0 24px auto;
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
  padding: 0 var(--page-gutter);
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-card);
}
.header__menu {
  display: none;
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
.header__search-toggle {
  display: none;
}

.icon-btn {
  width: 38px;
  height: 38px;
  flex: none;
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover {
  background: var(--bg-subtle);
  color: var(--text-primary);
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
  margin: 16px var(--page-gutter) 0;
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
  padding: 24px var(--page-gutter) 96px;
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

.scrim {
  display: none;
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

/* --------------------------------------------- tablet: the icon-only rail */
@media (max-width: 1279px) and (min-width: 900px) {
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

/* ------------------------------------------------ phone: drawer + stacked */
@media (max-width: 899px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    height: 100dvh;
    width: min(300px, 86vw);
    z-index: 70;
    padding: 12px 16px 24px;
    background: var(--bg-page);
    border-right: 1px solid var(--border-card);
    transform: translateX(-101%);
    transition: transform 0.22s ease-out;
    /* Off-canvas is off the page: nothing in here takes a tap or a tab stop. */
    visibility: hidden;
  }
  .sidebar--open {
    transform: translateX(0);
    visibility: visible;
    box-shadow: var(--shadow-float);
  }
  .sidebar__brand {
    margin-bottom: 0;
    height: 44px;
  }
  .sidebar__close {
    display: inline-flex;
    margin: 0 0 0 auto;
  }
  .sidebar__top {
    margin-bottom: 16px;
  }
  .nav-item {
    height: 46px;
  }

  .scrim {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 60;
    background: var(--scrim);
  }

  .header {
    height: auto;
    min-height: var(--header-height);
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 6px var(--page-gutter);
  }
  .header__menu {
    display: inline-flex;
    margin-left: -8px;
  }
  .header__title {
    font-size: 17px;
    line-height: 24px;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .header__right {
    gap: 4px;
  }
  .header__search-toggle {
    display: inline-flex;
  }
  /* Tabs get their own strip under the title; the empty placeholder is not one. */
  .header__tabs {
    order: 3;
    flex-basis: 100%;
    height: auto;
    overflow-x: auto;
    scrollbar-width: none;
    margin: 0 calc(var(--page-gutter) * -1);
    padding: 0 var(--page-gutter);
  }
  .header__tabs::-webkit-scrollbar {
    display: none;
  }
  .header__tabs:empty {
    display: none;
  }
  .search {
    order: 2;
    flex-basis: 100%;
    display: none;
    margin-bottom: 6px;
  }
  .search--open {
    display: block;
    width: auto;
  }
  .avatar {
    width: 32px;
    height: 32px;
    font-size: 13px;
  }

  .body {
    padding: 16px var(--page-gutter) 88px;
  }
  .offline {
    margin: 12px var(--page-gutter) 0;
  }

  /* On a phone the fixed pill would sit on top of the live dock, so the
     honesty marker rides along with the page title instead. */
  .demo-marker {
    position: static;
    padding: 3px 9px;
    font-size: 11px;
    line-height: 16px;
    white-space: nowrap;
  }
}
</style>
