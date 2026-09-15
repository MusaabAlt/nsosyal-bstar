import { createRouter, createWebHistory } from 'vue-router'
import AnalizView from '@/views/AnalizView.vue'
import KategorilerView from '@/views/KategorilerView.vue'

/*
 * Two routes (pages-spec 1). Analiz is the default: the operator opens the
 * console and is one keystroke from analysing. No history, settings,
 * accounts or charts.
 */
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'analiz', component: AnalizView },
    { path: '/kategoriler', name: 'kategoriler', component: KategorilerView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
