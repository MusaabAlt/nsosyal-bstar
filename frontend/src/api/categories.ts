import type { Action, ContentCode, Family } from '@/contract/types'
import categoriesJson from './mocks/categories.json'
import { setRepresentative } from './representative'

/*
 * The Kategoriler page's data (pages-spec 3): GET /api/categories, served by
 * the Go backend from AI/decision/thresholds.yaml and the model service's
 * health. It lists only what the AI can detect today. In sample mode, categories.json holds the same response, written
 * by the backend's own code (go test ./internal/categories -update).
 */

export type CategoryStatus = 'live' | 'stub' | 'unknown'

/** The decision layer's channel-level offensive score: detected, but not a ContentCode. */
export const BINARY_OFFENSIVE = 'binary_offensive'

export interface Category {
  code: ContentCode | typeof BINARY_OFFENSIVE
  /** Content code family; "" for binary_offensive. */
  family: Family | ''
  threshold: number | null
  action: Action | null
  /** false while thresholds.yaml still marks this threshold as a placeholder. */
  derived: boolean
  status: CategoryStatus
  module: string
}

/** Only what the AI can detect today, as the inference service reports it. */
export interface CategoryList {
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
