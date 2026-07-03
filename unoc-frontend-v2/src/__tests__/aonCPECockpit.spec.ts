import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AONCPECockpit from '../components/cockpits/AONCPECockpit.vue'
import { useMetricsStore } from '../stores/metricsStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useTariffsStore } from '../stores/tariffsStore.js'

describe('AONCPECockpit', () => {
  it('renders status/traffic/tariff and omits RX POWER', async () => {
    setActivePinia(createPinia())
    const metrics = useMetricsStore()
    const devices = useDevicesStore()
    const tariffs = useTariffsStore()

    ;(devices as any).devices = [
      {
        id: 'cpe1',
        name: 'CPE-1',
        type: 'AON_CPE',
        status: 'UP',
        tariff_id: 1
      }
    ]
    metrics.byId = {
      cpe1: {
        bps: 20_000_000,
        utilization: 0.2,
        version: 1,
        upstream_bps: 5_000_000,
        downstream_bps: 15_000_000
      }
    }
    tariffs.byId = { 1: { id: 1, name: '50/10', max_up_mbps: 10, max_down_mbps: 50 } }

    const w = mount(AONCPECockpit, { props: { deviceId: 'cpe1' } })
    const txt = w.text()
    expect(txt).toContain('STATUS:')
    expect(txt).toContain('UPSTREAM:')
    expect(txt).toContain('DOWNSTREAM:')
    expect(txt).toContain('TARIFF:')
    expect(txt).toContain('50/10')
    expect(txt).not.toContain('RX POWER:')
  })

  it('shows delivered / requested when a direction is throttled by shaping', async () => {
    setActivePinia(createPinia())
    const metrics = useMetricsStore()
    const devices = useDevicesStore()
    const tariffs = useTariffsStore()

    ;(devices as any).devices = [
      { id: 'cpe1', name: 'CPE-1', type: 'AON_CPE', status: 'UP', tariff_id: 1 }
    ]
    metrics.byId = {
      cpe1: {
        bps: 396_000_000,
        utilization: 0.33,
        version: 1,
        upstream_bps: 100_000_000,
        downstream_bps: 330_000_000,
        demand_up_bps: 100_000_000,
        demand_down_bps: 500_000_000,
        scale_up: 1.0,
        scale_down: 0.66,
        throttled: true
      }
    }
    tariffs.byId = { 1: { id: 1, name: '500/100', max_up_mbps: 100, max_down_mbps: 500 } }

    const w = mount(AONCPECockpit, { props: { deviceId: 'cpe1' } })
    const txt = w.text()
    // Downstream is throttled: compact "delivered / requested"
    expect(txt).toContain('330M / 500M')
    // Upstream is not throttled: plain delivered value
    expect(txt).toContain('100.00 Mbps')
    expect(txt).not.toContain('100M / 100M')
  })
})
