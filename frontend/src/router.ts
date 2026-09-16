import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { copy } from '@/copy'
import type { IconName } from '@/components/icons'

declare module 'vue-router' {
  interface RouteMeta {
    title: string
    icon?: IconName
    /** Show the Sistem durumu rail beside the page (wide screens only). */
    rail?: boolean
  }
}

/*
 * The panel's pages (ATI-SOSYAL Paneli). Genel Bakış is the default. Pages
 * without real data behind them (sözlük, değerlendirme, ayarlar) are not
 * built.
 */
export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'overview', component: () => import('@/views/OverviewView.vue'), meta: { title: copy.app.nav.overview, icon: 'dashboard', rail: true } },
  { path: '/analiz', name: 'live', component: () => import('@/views/LiveAnalysisView.vue'), meta: { title: copy.app.nav.live, icon: 'scan', rail: true } },
  { path: '/kuyruk', name: 'queue', component: () => import('@/views/QueueView.vue'), meta: { title: copy.app.nav.queue, icon: 'inbox' } },
  { path: '/motorlar', name: 'engines', component: () => import('@/views/EnginesView.vue'), meta: { title: copy.app.nav.engines, icon: 'brain', rail: true } },
  { path: '/kurallar', name: 'rules', component: () => import('@/views/RulesView.vue'), meta: { title: copy.app.nav.rules, icon: 'sliders', rail: true } },
  { path: '/gecmis', name: 'history', component: () => import('@/views/HistoryView.vue'), meta: { title: copy.app.nav.history, icon: 'clock', rail: true } },
  { path: '/saglik', name: 'health', component: () => import('@/views/HealthView.vue'), meta: { title: copy.app.nav.health, icon: 'activity' } },
  { path: '/kategoriler', redirect: '/kurallar' },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
