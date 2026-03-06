// Centralized color scale & bucket helpers (TASK-089)
// Keeps all semantic colors in one place for cockpit & link rendering.

export const STATUS_COLORS = {
  UP: '#2e7d32',
  DOWN: '#c62828',
  DEGRADED: '#ed6c02',
  UNKNOWN: '#757575'
} as const

// Optical signal status colors (frontend categories)
export const SIGNAL_COLORS = {
  OK: '#1976d2',
  WARNING: '#ffa000',
  CRITICAL: '#d32f2f',
  NO_SIGNAL: '#9e9e9e'
} as const

export type SignalStatus = keyof typeof SIGNAL_COLORS

export function colorForSignalStatus(status: string | undefined | null): string {
  if (!status) return SIGNAL_COLORS.NO_SIGNAL
  const key = String(status).toUpperCase() as SignalStatus
  return SIGNAL_COLORS[key] ?? SIGNAL_COLORS.NO_SIGNAL
}

export function labelForSignalStatus(status: string | undefined | null): string {
  if (!status) return 'NO_SIGNAL'
  const key = String(status).toUpperCase() as SignalStatus
  return Object.prototype.hasOwnProperty.call(SIGNAL_COLORS, key) ? key : 'NO_SIGNAL'
}

export const PORT_OCCUPANCY_COLORS = {
  EMPTY: '#90a4ae',
  PARTIAL: '#42a5f5',
  HIGH: '#1e88e5',
  FULL: '#0d47a1'
} as const

// Utilization bucket thresholds (percent, inclusive upper bounds except last)
// Default fallback; will be overridden at runtime by /api/config via configStore
export const DEFAULT_UTILIZATION_BUCKETS = [50, 70, 90, 100]
export function getUtilBuckets(): number[] {
  try {
    interface GlobalConfigLite {
      metrics?: { UTILIZATION_BUCKETS?: number[] }
    }
    const g = globalThis as unknown as { __unocConfigStore__?: GlobalConfigLite }
    const mod = g.__unocConfigStore__
    const buckets = mod?.metrics?.UTILIZATION_BUCKETS
    if (Array.isArray(buckets) && buckets.length === 4) return buckets
  } catch {
    /* ignore */
  }
  return DEFAULT_UTILIZATION_BUCKETS
}
export const UTIL_BUCKET_COLORS = ['#66bb6a', '#ffee58', '#ffa726', '#ef6c00', '#c62828']
// Distinct color to highlight >=100% overload state (used for pulsing ring)
export const UTIL_OVERLOAD_COLOR = '#8e24aa'

export type UtilBucketIndex = 0 | 1 | 2 | 3 | 4

export function getUtilBucket(utilPercent: number): UtilBucketIndex {
  const UTILIZATION_BUCKETS = getUtilBuckets()
  if (utilPercent <= UTILIZATION_BUCKETS[0]) return 0 // <=50
  if (utilPercent <= UTILIZATION_BUCKETS[1]) return 1 // 51..70
  if (utilPercent <= UTILIZATION_BUCKETS[2]) return 2 // 71..90
  if (utilPercent <= UTILIZATION_BUCKETS[3]) return 3 // 91..100
  return 4 // >100 overload bucket
}

export function colorForUtil(utilPercent: number): string {
  return UTIL_BUCKET_COLORS[getUtilBucket(utilPercent)]
}
