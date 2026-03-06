import type { DeviceOutX } from '../stores/devicesStore.js'
import type { DeviceMetric } from '../stores/metricsStore.js'
import type { DeviceType, Status } from '../types/domain.js'

export type SortBy = 'util' | 'bps' | 'name'

export interface DeviceMetricRow {
  id: string
  name: string
  type: DeviceType
  status: Status
  bps: number
  utilization: number
  upstream_bps?: number
  downstream_bps?: number
}

export function buildDeviceMetricRows(args: {
  devices: DeviceOutX[]
  metricsById: Record<string, DeviceMetric>
  q?: string
  type?: DeviceType | ''
  status?: Status | ''
  utilBucketMin?: number // 0..1 (inclusive). -1 disables.
  sortBy?: SortBy
}): DeviceMetricRow[] {
  const { devices, metricsById } = args
  const q = (args.q || '').trim().toLowerCase()
  const type = args.type || ''
  const status = args.status || ''
  const utilMin =
    typeof args.utilBucketMin === 'number' && args.utilBucketMin >= 0 ? args.utilBucketMin : -1
  const sortBy = args.sortBy || 'util'

  const rows: DeviceMetricRow[] = []
  for (const d of devices) {
    const m = metricsById[d.id]
    if (!m) continue
    if (q && !(d.name?.toLowerCase().includes(q) || d.id.toLowerCase().includes(q))) continue
    if (type && d.type !== type) continue
    if (status && d.status !== status) continue
    if (utilMin >= 0 && !(m.utilization >= utilMin)) continue
    rows.push({
      id: d.id,
      name: d.name,
      type: d.type as DeviceType,
      status: d.status as Status,
      bps: m.bps,
      utilization: m.utilization,
      upstream_bps: m.upstream_bps,
      downstream_bps: m.downstream_bps
    })
  }

  switch (sortBy) {
    case 'bps':
      rows.sort((a, b) => b.bps - a.bps || a.name.localeCompare(b.name))
      break
    case 'name':
      rows.sort((a, b) => a.name.localeCompare(b.name))
      break
    case 'util':
    default:
      rows.sort((a, b) => b.utilization - a.utilization || a.name.localeCompare(b.name))
      break
  }
  return rows
}
