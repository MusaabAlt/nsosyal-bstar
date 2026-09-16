import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import KategorilerView from './KategorilerView.vue'
import categoriesJson from '@/api/mocks/categories.json'
import { accusative } from '@/copy'

const vuetify = createVuetify({ components })

describe('Kategoriler', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists only what the AI detects, with threshold, action and module status', async () => {
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ ...categoriesJson, representative: true }), { status: 200 }))
    const w = mount(KategorilerView, { global: { plugins: [vuetify] } })
    await flushPromises()

    const headings = w.findAll('.kategoriler__family').map((h) => h.text())
    expect(headings).toEqual(['Açık küfür', 'Genel'])
    const rows = w.findAll('tbody tr').map((r) => r.findAll('td').map((c) => c.text()))
    expect(rows).toEqual([
      ['A1', 'Hedefsiz küfür', 'veri yok', '0.50', 'Hassas içerik', 'canlı'],
      ['', 'Genel saldırganlık', 'veri yok', '0.32', 'İncele', 'canlı'],
    ])
    // A1's threshold is still a placeholder; the offensive score's was derived on dev.
    expect(w.find('.kategoriler__note').text()).toContain('Hedefsiz küfür')
    expect(w.find('.kategoriler__note').text()).not.toContain('Genel saldırganlık')
    expect(w.text()).not.toMatch(/skor/i) // no scores on this page
  })

  it('says so when the AI service reports nothing', async () => {
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ source: 'x', categories: [] }), { status: 200 }))
    const w = mount(KategorilerView, { global: { plugins: [vuetify] } })
    await flushPromises()
    expect(w.text()).toContain('hiçbir kategori bildirmiyor')
    expect(w.find('table').exists()).toBe(false)
  })

  it('a failed load is a readable error state with retry', async () => {
    vi.stubGlobal('fetch', async () => new Response('', { status: 503 }))
    const w = mount(KategorilerView, { global: { plugins: [vuetify] } })
    await flushPromises()
    expect(w.text()).toContain('Kategori listesi alınamadı.')
    expect(w.find('button').text()).toBe('Tekrar dene')
  })
})

describe('Turkish number suffix', () => {
  it.each([
    [0, "'ı"],
    [1, "'i"],
    [2, "'si"],
    [3, "'ü"],
    [4, "'ü"],
    [5, "'i"],
    [6, "'sı"],
    [9, "'u"],
    [10, "'u"],
    [12, "'si"],
    [16, "'sı"],
    [40, "'ı"],
    [100, "'ü"],
  ])('%i%s', (n, suffix) => {
    expect(accusative(n)).toBe(suffix)
  })
})
