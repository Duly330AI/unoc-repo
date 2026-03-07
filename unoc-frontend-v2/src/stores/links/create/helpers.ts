import { useDevicesStore, type DeviceOutX } from '../../devicesStore.js'

export type IfaceLite = {
  id: string
  name: string
  role?: string | null
  port_role?: 'UPLINK' | 'ACCESS' | 'PON' | 'TRUNK' | string | null
  admin_status?: string
}

export const isMgmt = (i: IfaceLite) => i.name === 'mgmt0' || i.role === 'management'
export const isUp = (i: IfaceLite) => (i.admin_status ?? 'up') === 'up'

export const getPortRole = (i: IfaceLite): 'UPLINK' | 'ACCESS' | 'PON' | 'TRUNK' | null => {
  const pr = (i.port_role || '') as string
  if (pr === 'UPLINK' || pr === 'ACCESS' || pr === 'PON' || pr === 'TRUNK') return pr
  if (i.role === 'p2p_uplink') return 'UPLINK'
  if (i.role === 'access') return 'ACCESS'
  if (i.name?.toLowerCase().startsWith('uplink')) return 'UPLINK'
  return null
}

export const isOntFamily = (t?: string | null) =>
  !!t && (String(t) === 'ONT' || String(t) === 'BUSINESS_ONT')

export const isPassive = (t?: string | null) =>
  !!t && ['ODF', 'SPLITTER', 'NVT', 'HOP'].includes(String(t))

export type LinksStoreLike = { links: Array<{ a_device_id: string; b_device_id: string }> }

export const validateOntPassive = (
  store: LinksStoreLike,
  devStore: ReturnType<typeof useDevicesStore>,
  ontId: string,
  passiveId: string
): boolean => {
  const typeOf = (id: string) => String(devStore.byId(id)?.type || '')
  const passiveSet = new Set(['ODF', 'NVT', 'SPLITTER', 'HOP'])
  const adj = new Map<string, Set<string>>()
  const addEdge = (x: string, y: string) => {
    if (!adj.has(x)) adj.set(x, new Set())
    adj.get(x)!.add(y)
  }
  for (const l of store.links) {
    const da = l.a_device_id
    const db = l.b_device_id
    const ta = typeOf(da)
    const tb = typeOf(db)
    if (passiveSet.has(ta) && passiveSet.has(tb)) {
      addEdge(da, db)
      addEdge(db, da)
    }
  }
  const hasOltNeighbor = (odfId: string): boolean => {
    for (const l of store.links) {
      if (l.a_device_id === odfId || l.b_device_id === odfId) {
        const other = l.a_device_id === odfId ? l.b_device_id : l.a_device_id
        if (typeOf(other) === 'OLT') return true
      }
    }
    return false
  }
  const visited = new Set<string>()
  const q: string[] = []
  q.push(passiveId)
  visited.add(passiveId)
  while (q.length) {
    const cur = q.shift()!
    if (typeOf(cur) === 'ODF' && hasOltNeighbor(cur)) return true
    const nbrs = adj.get(cur)
    if (!nbrs) continue
    for (const nb of nbrs) {
      if (!visited.has(nb)) {
        visited.add(nb)
        q.push(nb)
      }
    }
  }
  return false
}

export const annotatePassiveOptionsViaOlt = (
  store: LinksStoreLike,
  devStore: ReturnType<typeof useDevicesStore>,
  passiveId: string,
  opts: Array<{ id: string; label: string }>
): Array<{ id: string; label: string }> => {
  try {
    const typeOf = (id: string) => String(devStore.byId(id)?.type || '')
    const passiveSet = new Set(['ODF', 'NVT', 'SPLITTER', 'HOP'])
    const adj = new Map<string, Set<string>>()
    const addEdge = (x: string, y: string) => {
      if (!adj.has(x)) adj.set(x, new Set())
      adj.get(x)!.add(y)
    }
    for (const l of store.links) {
      const da = l.a_device_id
      const db = l.b_device_id
      const ta = typeOf(da)
      const tb = typeOf(db)
      if (passiveSet.has(ta) && passiveSet.has(tb)) {
        addEdge(da, db)
        addEdge(db, da)
      }
    }
    const hasOltNeighbor = (odfId: string): string | null => {
      for (const l of store.links) {
        if (l.a_device_id === odfId || l.b_device_id === odfId) {
          const other = l.a_device_id === odfId ? l.b_device_id : l.a_device_id
          if (typeOf(other) === 'OLT') return other
        }
      }
      return null
    }
    const visited = new Set<string>()
    const q: string[] = []
    q.push(passiveId)
    visited.add(passiveId)
    let oltName: string | null = null
    while (q.length && !oltName) {
      const cur = q.shift()!
      if (typeOf(cur) === 'ODF') {
        const oltId = hasOltNeighbor(cur)
        if (oltId) {
          const olt = devStore.byId(oltId) as DeviceOutX | undefined
          oltName = olt?.name || oltId
          break
        }
      }
      const nbrs = adj.get(cur)
      if (!nbrs) continue
      for (const nb of nbrs) {
        if (!visited.has(nb)) {
          visited.add(nb)
          q.push(nb)
        }
      }
    }
    if (!oltName) return opts
    return opts.map((o) => ({ id: o.id, label: `${o.label} • via OLT ${oltName}` }))
  } catch {
    return opts
  }
}
