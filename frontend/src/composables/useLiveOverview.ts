import { shallowRef } from 'vue'
import { fetchOverview, type Overview } from '@/api/panel'

/*
 * The live overview the shell keeps fresh for the sidebar badge and the
 * Sistem durumu rail. One shared copy, so every part of the shell reads the
 * same numbers.
 */
export const liveOverview = shallowRef<Overview | null>(null)
export const liveOverviewFailed = shallowRef(false)

export async function refreshLiveOverview(): Promise<void> {
  const out = await fetchOverview('live')
  if (out.ok) {
    liveOverview.value = out.data
    liveOverviewFailed.value = false
  } else {
    liveOverviewFailed.value = true
  }
}
