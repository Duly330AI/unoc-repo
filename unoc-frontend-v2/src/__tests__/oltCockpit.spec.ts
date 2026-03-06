import { describe, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OLTCockpit from '../components/cockpits/OLTCockpit.vue'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useLinksStore } from '../stores/linksStore.js'
import { useMetricsStore } from '../stores/metricsStore.js'

function makeIf(id: string, role: string = 'PON') {
  return { id, name: id, admin_status: 'up', status: 'UP', role: null, port_role: role }
}

describe('OLTCockpit', () => {
  it('renders digital rows and a PON port matrix', async () => {
    setActivePinia(createPinia())
    const devices = useDevicesStore()
    const links = useLinksStore()
    const metrics = useMetricsStore()
    ;(devices as any).devices = [
      {
        id: 'olt1',
        name: 'OLT-1',
        type: 'OLT',
        status: 'UP',
        interfaces: [makeIf('olt1-p1'), makeIf('olt1-p2')]
      },
      {
        id: 'ont1',
        name: 'ONT-1',
        type: 'ONT',
        status: 'UP',
        interfaces: [makeIf('ont1-if0', 'ACCESS')]
      },
      {
        id: 'ont2',
        name: 'ONT-2',
        type: 'ONT',
        status: 'DOWN',
        interfaces: [makeIf('ont2-if0', 'ACCESS')]
      },
      {
        id: 'spl1',
        name: 'SPL',
        type: 'SPLITTER',
        status: 'UP',
        interfaces: [makeIf('spl1-a', 'ACCESS'), makeIf('spl1-b', 'ACCESS')]
      }
    ]
    ;(links as any).links = [
      // p1 -> splitter a; splitter b -> ont1
      {
        id: 'L1',
        a_interface_id: 'olt1-p1',
        b_interface_id: 'spl1-a',
        a_device_id: 'olt1',
        b_device_id: 'spl1',
        status: 'UP',
        kind: 'FIBER'
      },
      {
        id: 'L2',
        a_interface_id: 'spl1-b',
        b_interface_id: 'ont1-if0',
        a_device_id: 'spl1',
        b_device_id: 'ont1',
        status: 'UP',
        kind: 'FIBER'
      },
      // p2 -> ont2 directly (down)
      {
        id: 'L3',
        a_interface_id: 'olt1-p2',
        b_interface_id: 'ont2-if0',
        a_device_id: 'olt1',
        b_device_id: 'ont2',
        status: 'UP',
        kind: 'FIBER'
      }
    ]
    ;(metrics as any).byId = {
      olt1: { bps: 0, utilization: 0, version: 1, upstream_bps: 100, downstream_bps: 300 }
    }

    // Mock per-port summary API
    ;(globalThis as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 'olt1-p1',
          name: 'pon-1',
          port_role: 'PON',
          effective_status: 'UP',
          occupancy: 1,
          capacity: 64
        },
        {
          id: 'olt1-p2',
          name: 'pon-2',
          port_role: 'PON',
          effective_status: 'DOWN',
          occupancy: 1,
          capacity: 64
        }
      ]
    })

    const w = mount(OLTCockpit, { props: { deviceId: 'olt1' } })
    // wait for async fetch to be invoked and DOM update (micro + macro tasks)
    const flush = async () => {
      await Promise.resolve()
      await nextTick()
      await new Promise((r) => setTimeout(r, 0))
      await nextTick()
    }
    // wait until our mock fetch gets called at least once
    for (let i = 0; i < 10; i++) {
      const mock = (globalThis as any).fetch as ReturnType<typeof vi.fn>
      if (mock && (mock as any).mock?.calls?.length > 0) break
      await flush()
    }
    await flush()
    // Digital rows present
    expect(w.text()).toContain('STATUS:')
    expect(w.text()).toContain('TOTAL TRAFFIC:')
    expect(w.text()).toContain('SUBSCRIBERS:')
    // Cells for 2 PON ports
    // wait for cells to render
    let cells = w.findAll('rect.pon-cell')
    for (let i = 0; i < 10 && cells.length === 0; i++) {
      await flush()
      cells = w.findAll('rect.pon-cell')
    }
    expect(cells.length).toBe(2)
    // First port sees ONT-1 UP via splitter -> state UP
    expect(cells[0].attributes()['data-state']).toBe('UP')
    // Second port sees ONT-2 DOWN -> state DOWN
    expect(cells[1].attributes()['data-state']).toBe('DOWN')
  })
})
