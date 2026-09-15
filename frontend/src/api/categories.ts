import type { Action, ContentCode, Family } from '@/contract/types'
import categoriesJson from './mocks/categories.json'
import { setRepresentative } from './representative'

/*
 * The Kategoriler page's data (pages-spec 3): GET /api/categories, served by
 * the Go backend from AI/decision/thresholds.yaml and the model service's
 * health. In sample mode, categories.json holds the same response, written
 * by the backend's own code (go test ./internal/categories -update).
 */

export type CategoryStatus = 'live' | 'stub' | 'unknown'

export interface Category {
  code: ContentCode
  family: Family
  threshold: number | null
  action: Action | null
  status: CategoryStatus
}

export interface CategoryList {
  /** true while thresholds.yaml marks every value as a placeholder. */
  placeholder: boolean
  source: string
  categories: Category[]
}

export type CategoriesOutcome = { ok: true; list: CategoryList } | { ok: false }

export async function loadCategories(mode: 'api' | 'mock'): Promise<CategoriesOutcome> {
  if (mode === 'mock') {
    setRepresentative(true)
    return { ok: true, list: JSON.parse(JSON.stringify(categoriesJson)) as CategoryList }
  }
  try {
    const response = await fetch('/api/categories')
    if (!response.ok) return { ok: false }
    const body = (await response.json()) as CategoryList & { representative?: boolean }
    setRepresentative(body.representative)
    return { ok: true, list: body }
  } catch {
    return { ok: false }
  }
}
