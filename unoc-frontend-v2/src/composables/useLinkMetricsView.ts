import { computed, type ComputedRef } from 'vue'
import { useLinkMetricsStore } from '../stores/linkMetricsStore.js'

export function formatPercent(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—'
  const pct = Math.round(v * 100)
  return `${pct}%`
}

export function formatBps(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)} Gbps`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)} Mbps`
  if (abs >= 1e3) return `${(v / 1e3).toFixed(2)} Kbps`
  return `${v.toFixed(0)} bps`
}

export function useLinkMetricsView(linkId: ComputedRef<string>) {
  const store = useLinkMetricsStore()
  const linkMetric = computed(() => store.byId[linkId.value] || null)
  const linkUtilText = computed(() => formatPercent(linkMetric.value?.utilization))
  const linkBpsText = computed(() => formatBps(linkMetric.value?.bps))

  return {
    linkMetric,
    linkUtilText,
    linkBpsText
  }
}
