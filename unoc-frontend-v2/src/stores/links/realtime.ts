import { eventBus, type EventEnvelope } from '../../lib/eventBus.js'
import { useDevicesStore } from '../devicesStore.js'
import { normalizeStatus, type Link } from './types.js'

type LinksStoreApi = {
  links: Link[]
  _lastTopoByLink: Record<string, number>
}

export function registerLinkRealtime(store: LinksStoreApi) {
  // link.created → add if not exists
  eventBus.on<EventEnvelope>('link.created', (env) => {
    const p = (env?.payload || {}) as Partial<Link> & { id: string }
    if (!p?.id) return
    const topo = typeof env?.topo_version === 'number' ? (env.topo_version as number) : null
    if (topo != null) {
      const last = store._lastTopoByLink[p.id]
      if (typeof last === 'number' && topo < last) {
        if (import.meta.env?.DEV) console.debug('[linksStore] drop stale link.created', p.id)
        return
      }
    }
    if (store.links.find((l) => l.id === p.id)) return
    // Derive device id from interface id robustly: strip trailing `-if<digits>` if present
    const deriveDev = (iid?: string) => {
      if (!iid) return ''
      const m = iid.match(/^(.*)-if\d+$/)
      if (m && m[1]) return m[1]
      if (iid.endsWith('-if0')) return iid.slice(0, -4)
      return ''
    }
    const devicesStore = useDevicesStore()
    const lookupDevByIface = (iid?: string) => {
      if (!iid) return ''
      try {
        const all = devicesStore.devices || []
        for (const d of all) {
          const ifaces = (d as unknown as { interfaces?: Array<{ id: string }> })?.interfaces
          if (Array.isArray(ifaces) && ifaces.some((i) => i.id === iid)) return d.id
        }
      } catch {
        /* ignore */
      }
      return ''
    }
    const link: Link = {
      id: p.id,
      a_interface_id: p.a_interface_id || '',
      b_interface_id: p.b_interface_id || '',
      a_device_id:
        (p as Partial<Link> & { a_device_id?: string }).a_device_id ||
        deriveDev(p.a_interface_id) ||
        lookupDevByIface(p.a_interface_id),
      b_device_id:
        (p as Partial<Link> & { b_device_id?: string }).b_device_id ||
        deriveDev(p.b_interface_id) ||
        lookupDevByIface(p.b_interface_id),
      status: normalizeStatus(p.status) || 'UP',
      effective_status: normalizeStatus(p.effective_status) || normalizeStatus(p.status) || 'UP',
      kind: p.kind || 'FIBER',
      admin_override_status: normalizeStatus(p.admin_override_status) ?? null,
      length_km: typeof p.length_km === 'number' ? p.length_km : null,
      physical_medium_id:
        typeof p.physical_medium_id === 'number' ? p.physical_medium_id : undefined
    }
    // Never store links without both device endpoints resolved
    if (!link.a_device_id || !link.b_device_id) {
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.debug('[linksStore] skip link.created without device ids', link)
      }
      return
    }
    store.links.push(link)
    if (topo != null) store._lastTopoByLink[p.id] = topo
  })

  // link.deleted → remove
  eventBus.on<EventEnvelope>('link.deleted', (env) => {
    const p = env?.payload as { id: string }
    if (!p?.id) return
    const topo = typeof env?.topo_version === 'number' ? (env.topo_version as number) : null
    if (topo != null) {
      const last = store._lastTopoByLink[p.id]
      if (typeof last === 'number' && topo < last) {
        if (import.meta.env?.DEV) console.debug('[linksStore] drop stale link.deleted', p.id)
        return
      }
      store._lastTopoByLink[p.id] = topo
    }
    store.links = store.links.filter((l) => l.id !== p.id)
  })

  // link.override.changed → merge update
  eventBus.on<EventEnvelope>('link.override.changed', (env) => {
    const p = (env?.payload || {}) as Partial<Link> & { id?: string }
    if (!p?.id) return
    const idx = store.links.findIndex((l) => l.id === p.id)
    if (idx === -1) return // we have not seen the link yet
    const existing = store.links[idx]
    const merged: Link = {
      ...existing,
      ...(typeof p.status === 'string'
        ? { status: normalizeStatus(p.status) || existing.status }
        : {}),
      ...(typeof p.effective_status === 'string'
        ? { effective_status: normalizeStatus(p.effective_status) || existing.effective_status }
        : {}),
      ...('admin_override_status' in p
        ? { admin_override_status: normalizeStatus(p.admin_override_status) ?? null }
        : {}),
      ...(typeof p.length_km === 'number' ? { length_km: p.length_km } : {}),
      ...(typeof p.physical_medium_id === 'number'
        ? { physical_medium_id: p.physical_medium_id }
        : {})
    }
    const keysToCheck: Array<keyof Link> = [
      'status',
      'effective_status',
      'admin_override_status',
      'length_km',
      'physical_medium_id'
    ]
    let changed = false
    for (const k of keysToCheck) {
      if (merged[k] !== (existing as Link)[k]) {
        changed = true
        break
      }
    }
    if (changed) {
      store.links.splice(idx, 1, merged)
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.debug('[linksStore] override changed → replaced link', p.id, {
          status: merged.status,
          effective_status: merged.effective_status,
          admin_override_status: merged.admin_override_status
        })
      }
    }
  })

  // link.status.changed → mirror override merge (covers downstream cascades)
  eventBus.on<EventEnvelope>('link.status.changed', (env) => {
    const p = (env?.payload || {}) as Partial<Link> & { id?: string }
    if (!p?.id) return
    const idx = store.links.findIndex((l) => l.id === p.id)
    if (idx === -1) return
    const existing = store.links[idx]
    const merged: Link = {
      ...existing,
      ...(typeof p.status === 'string'
        ? { status: normalizeStatus(p.status) || existing.status }
        : {}),
      ...(typeof p.effective_status === 'string'
        ? { effective_status: normalizeStatus(p.effective_status) || existing.effective_status }
        : {}),
      ...('admin_override_status' in p
        ? { admin_override_status: normalizeStatus(p.admin_override_status) ?? null }
        : {})
    }
    if (
      merged.status !== existing.status ||
      merged.effective_status !== existing.effective_status ||
      merged.admin_override_status !== existing.admin_override_status
    ) {
      store.links.splice(idx, 1, merged)
      if (import.meta.env?.DEV) {
        // eslint-disable-next-line no-console
        console.debug('[linksStore] link.status.changed applied', p.id, {
          status: merged.status,
          effective_status: merged.effective_status,
          admin_override_status: merged.admin_override_status
        })
      }
    }
  })
}
