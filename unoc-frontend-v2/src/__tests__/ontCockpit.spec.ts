import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ONTCockpit from '../components/cockpits/ONTCockpit.vue'
import { useMetricsStore } from '../stores/metricsStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useTariffsStore } from '../stores/tariffsStore.js'

describe('ONTCockpit', () => {
  it('renders status, RX power, traffic and tariff', async () => {
    setActivePinia(createPinia())
    const metrics = useMetricsStore()
    const devices = useDevicesStore()
    const tariffs = useTariffsStore()
    // seed stores
    ;(devices as any).devices = [
      {
        id: 'ont1',
        name: 'ONT-1',
        type: 'ONT',
        status: 'UP',
        signal_status: 'OK',
        signal_power_dbm: -20.4,
        tariff_id: 1
      }
    ]
    metrics.byId = {
      ont1: {
        bps: 40_000_000,
        utilization: 0.4,
        version: 1,
        upstream_bps: 10_000_000,
        downstream_bps: 30_000_000
      }
    }
    tariffs.byId = { 1: { id: 1, name: '100/20', max_up_mbps: 20, max_down_mbps: 100 } }

    const w = mount(ONTCockpit, { props: { deviceId: 'ont1' } })
    const txt = w.text()
    // Digital rows
    expect(txt).toContain('STATUS:')
    expect(txt).toContain('RX POWER:')
    // Value formatting
    expect(txt).toContain('-20.4 dBm')
    // Tariff shown below frame
    expect(txt).toContain('100/20')
    // Should render frame rects
    const rects = w.findAll('rect')
    expect(rects.length).toBeGreaterThan(0)
  })
})
