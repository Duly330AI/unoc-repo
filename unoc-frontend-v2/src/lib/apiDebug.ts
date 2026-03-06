export interface DebugSnapshotMeta {
  ts: number
  tick: number | null
  sections: string[]
  counts: Record<string, number>
}

export interface DebugSnapshot {
  meta: DebugSnapshotMeta
  // plus arbitrary sections
  [key: string]: unknown
}

export async function fetchFullSnapshot(params?: {
  sections?: string[]
  pretty?: boolean
  maxItems?: number
  includeDeltas?: boolean
}): Promise<DebugSnapshot> {
  const q = new URLSearchParams()
  if (params?.sections?.length) q.set('sections', params.sections.join(','))
  if (params?.pretty) q.set('pretty', '1')
  if (params?.maxItems) q.set('maxItems', String(params.maxItems))
  if (params?.includeDeltas === false) q.set('includeDeltas', '0')
  const res = await fetch(`/api/debug/full-snapshot?${q.toString()}`)
  if (!res.ok) throw new Error(`Snapshot fetch failed: ${res.status}`)
  return await res.json()
}
