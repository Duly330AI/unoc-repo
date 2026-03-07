import { describe, it, expect } from 'vitest'
import { buildDeviceMetricRows } from '../pages/metricsSelectors'
import type { DeviceOut } from '../types/domain.js'

function d(id: string, name: string, type: DeviceOut['type'], status: DeviceOut['status']) {
  return { id, name, type, status, provisioned: true, role: 'active' as const }
}

describe('metricsSelectors.buildDeviceMetricRows', () => {
  const devices = [
    d('d1', 'Core-1', 'CORE_ROUTER', 'UP'),
    d('d2', 'Edge-9', 'EDGE_ROUTER', 'DEGRADED'),
    d('d3', 'OLT-2', 'OLT', 'UP'),
    d('d4', 'ONT-77', 'ONT', 'DOWN')
  ]
  const metricsById = {
    d1: { bps: 1_000_000_000, utilization: 0.25, version: 1 },
    d2: { bps: 5_000_000_000, utilization: 0.92, version: 3 },
    d3: { bps: 200_000_000, utilization: 0.08, version: 2 },
    d4: { bps: 0, utilization: 0.0, version: 1 }
  }

  it('sorts by utilization by default', () => {
    const rows = buildDeviceMetricRows({ devices: devices as any, metricsById })
    expect(rows.map((r) => r.id)).toEqual(['d2', 'd1', 'd3', 'd4'])
  })

  it('filters by search, type, status, and bucket', () => {
    const rows1 = buildDeviceMetricRows({ devices: devices as any, metricsById, q: 'edge' })
    expect(rows1.map((r) => r.id)).toEqual(['d2'])
    const rows2 = buildDeviceMetricRows({ devices: devices as any, metricsById, type: 'OLT' })
    expect(rows2.map((r) => r.id)).toEqual(['d3'])
    const rows3 = buildDeviceMetricRows({ devices: devices as any, metricsById, status: 'UP' })
    expect(rows3.map((r) => r.id)).toEqual(['d1', 'd3'])
    const rows4 = buildDeviceMetricRows({
      devices: devices as any,
      metricsById,
      utilBucketMin: 0.5
    })
    expect(rows4.map((r) => r.id)).toEqual(['d2'])
  })

  it('sorts by bps and by name', () => {
    const byBps = buildDeviceMetricRows({ devices: devices as any, metricsById, sortBy: 'bps' })
    expect(byBps.map((r) => r.id)).toEqual(['d2', 'd1', 'd3', 'd4'])
    const byName = buildDeviceMetricRows({ devices: devices as any, metricsById, sortBy: 'name' })
    expect(byName.map((r) => r.id)).toEqual(['d1', 'd2', 'd3', 'd4'])
  })
})
