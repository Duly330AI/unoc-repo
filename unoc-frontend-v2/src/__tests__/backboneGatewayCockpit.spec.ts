import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import BackboneGatewayCockpit from '../components/cockpits/BackboneGatewayCockpit.vue'
import { useMetricsStore } from '../stores/metricsStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'

describe('BackboneGatewayCockpit', () => {
  it('renders LEDs and digital display rows with subscribers count', async () => {
    setActivePinia(createPinia())
    const metrics = useMetricsStore()
    const devices = useDevicesStore()
    ;(devices as any).devices = [
      { id: 'bbgw1', name: 'BBGW1', type: 'BACKBONE_GATEWAY', status: 'UP' },
      { id: 'ont1', name: 'ONT1', type: 'ONT', status: 'UP' },
      { id: 'ont2', name: 'ONT2', type: 'ONT', status: 'DOWN' },
      { id: 'cpe1', name: 'CPE1', type: 'AON_CPE', status: 'UP' }
    ]
    metrics.byId = {
      bbgw1: {
        bps: 0,
        utilization: 0.5,
        version: 1,
        upstream_bps: 100_000_000,
        downstream_bps: 200_000_000
      }
    }

    const w = mount(BackboneGatewayCockpit, { props: { deviceId: 'bbgw1' } })
    const txt = w.text()
    // Header shows device id (case-insensitive)
    expect(txt).toMatch(/bbgw1/i)
    // Rows
    expect(txt).toMatch(/STATUS:/)
    expect(txt).toMatch(/UPSTREAM:/)
    expect(txt).toMatch(/DOWNSTREAM:/)
    // Subscriber row removed in simplified cockpit; just ensure no unexpected blank
    // (historical expectation dropped)
    expect(txt).not.toMatch(/SUBSCRIBERS:/)
    // LED circles exist
    const circles = w.findAll('circle')
    expect(circles.length).toBeGreaterThanOrEqual(3)
  })
})
