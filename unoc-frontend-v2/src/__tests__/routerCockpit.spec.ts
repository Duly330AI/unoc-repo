import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RouterCockpit from '../components/cockpits/RouterCockpit.vue'
import { useMetricsStore } from '../stores/metricsStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'

describe('RouterCockpit', () => {
  it('renders digital display rows from stores', async () => {
    setActivePinia(createPinia())
    const metrics = useMetricsStore()
    const devices = useDevicesStore()
    // seed
    ;(devices as any).devices = [
      {
        id: 'r1',
        name: 'R1',
        type: 'CORE_ROUTER',
        status: 'UP',
        parameters: { effective_capacity_mbps: 10000 }
      }
    ]
    metrics.byId = {
      r1: {
        bps: 50_000_000,
        utilization: 0.5,
        version: 1,
        upstream_bps: 30_000_000,
        downstream_bps: 20_000_000
      }
    }

    const w = mount(RouterCockpit, { props: { deviceId: 'r1' } })
    const txt = w.text()
    expect(txt).toMatch(/STATUS:/)
    expect(txt).toMatch(/UPSTREAM:/)
    expect(txt).toMatch(/DOWNSTREAM:/)
    // Label text updated in component to concise form
    expect(txt).toMatch(/TotCap \(Gbps\):/)
  })
})
