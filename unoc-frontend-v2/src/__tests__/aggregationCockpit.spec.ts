import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AggregationCockpit from '../components/cockpits/AggregationCockpit.vue'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useMetricsStore } from '../stores/metricsStore.js'

function makeIf(id: string, up = true) {
  return { id, name: id, admin_status: up ? 'up' : 'down' }
}

describe('AggregationCockpit', () => {
  it('renders a port grid and overflow summary', async () => {
    setActivePinia(createPinia())
    const devices = useDevicesStore()
    const metrics = useMetricsStore()
    ;(devices as any).devices = [
      {
        id: 'agg1',
        name: 'OLT-1',
        type: 'OLT',
        status: 'UP',
        interfaces: [
          ...Array.from({ length: 30 }, (_, i) => makeIf(`p${i + 1}`, i % 2 === 0)),
          makeIf('p31', false),
          makeIf('p32', true),
          makeIf('p33', true) // will overflow
        ]
      }
    ]

    const w = mount(AggregationCockpit, { props: { deviceId: 'agg1' } })
    // 32 visible max
    const cells = w.findAll('rect.port-cell')
    expect(cells.length).toBe(32)
    // overflows by 1
    const overflow = w.find('text.overflow-indicator')
    expect(overflow.exists()).toBe(true)
    expect(overflow.text()).toContain('+1 more')

    // spot check statuses: first cell should be up (green), second down (red)
    expect(cells[0].attributes()['data-status']).toBe('up')
    expect(cells[1].attributes()['data-status']).toBe('down')

    // seed per-port metrics and re-mount to reflect non-zero util
    metrics.portsByDevice = {
      agg1: {
        p1: { bps: 10_000_000, utilization: 0.25, version: 1 },
        p2: { bps: 20_000_000, utilization: 0.5, version: 1 }
      }
    }
    const w2 = mount(AggregationCockpit, { props: { deviceId: 'agg1' } })
    const cells2 = w2.findAll('rect.port-cell')
    expect(cells2[0].attributes()['data-util']).toBe('25')
    expect(cells2[1].attributes()['data-util']).toBe('50')
  })
})
