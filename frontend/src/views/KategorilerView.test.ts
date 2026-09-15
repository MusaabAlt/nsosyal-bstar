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

  it('lists the sixteen categories by family with threshold, action and module status', async () => {
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ ...categoriesJson, representative: true }), { status: 200 }))
    const w = mount(KategorilerView, { global: { plugins: [vuetify] } })
    await flushPromises()

    const headings = w.findAll('.kategoriler__family').map((h) => h.text())
    expect(headings).toEqual(['Açık küfür', 'Sözcük dışı saldırganlık', 'Örtük saldırganlık', 'Aşağılayıcı ironi', 'Temiz'])
    const rows = w.findAll('tbody tr')
    expect(rows).toHaveLength(16)

    const b2 = rows.find((r) => r.find('.code').text() === 'B2')!
    const cells = b2.findAll('td').map((c) => c.text())
    expect(cells).toEqual(['B2', 'Tehdit', 'veri yok', '0.50', 'İncele', 'modül hazır değil'])
    expect(w.text()).toContain('geçicidir') // thresholds.yaml marks every value placeholder
    expect(w.text()).not.toMatch(/skor/i) // no scores on this page
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
