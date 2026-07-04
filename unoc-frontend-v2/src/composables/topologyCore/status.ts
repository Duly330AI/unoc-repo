export function normalizeVisualStatus(raw: unknown): string {
  if (typeof raw !== 'string' || !raw) return 'UNKNOWN'
  let s = raw.trim()
  if (s.startsWith('Status.')) s = s.slice('Status.'.length)
  const lower = s.toLowerCase()
  if (lower === 'up') return 'UP'
  if (lower === 'down') return 'DOWN'
  if (lower === 'degraded') return 'DEGRADED'
  if (lower === 'unknown') return 'UNKNOWN'
  if (['active', 'online', 'provisioned'].includes(lower)) return 'UP'
  if (['partial'].includes(lower)) return 'DEGRADED'
  if (['failed', 'unreachable', 'offline'].includes(lower)) return 'DOWN'
  return 'UNKNOWN'
}

export function deriveNodeVisualStatus(
  operational: string,
  signalStatus?: string | null
): string {
  const normalizedOperational = normalizeVisualStatus(operational)
  if (normalizedOperational === 'DOWN') return 'DOWN'
  if (signalStatus === 'WARNING' || signalStatus === 'CRITICAL') return 'DEGRADED'
  return normalizedOperational
}
