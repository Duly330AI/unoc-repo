import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DetailsPanel from '../components/layout/DetailsPanel.vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'

function iface(id: string, name: string, admin: 'up' | 'down', role?: string | null) {
  return { id, name, admin_status: admin, role: role ?? null }
}

describe('DetailsPanel - Interfaces sorting', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('sorts by role precedence, admin up first, then natural name', async () => {
    const devices = useDevicesStore()
    ;(devices as any).devices = [
      {
        id: 'd1',
        name: 'Dev 1',
        type: 'EDGE_ROUTER',
        status: 'UP',
        role: 'active',
        device_default_vrf_name: 'mgmt',
        interfaces: [
          iface('i1', 'eth10', 'up', 'access'),
          iface('i2', 'eth2', 'up', 'uplink'),
          iface('i3', 'eth1', 'down', 'uplink'),
          iface('i4', 'eth02', 'up', null),
          iface('i5', 'eth9', 'down', 'access')
        ]
      }
    ]
    const selection = useSelectionStore()
    selection.select('d1', 'device')

    const w = mount(DetailsPanel)
    // Switch to Interfaces tab
    await w.findAll('button.tab').at(1)?.trigger('click')

    const ifaces = w.findAll('.interfaces-tab .iface .row:first-child .mono')
    const names = ifaces.map((n) => n.text())

    // Expected order:
    // - role uplink first: eth2 (up), then eth1 (down)
    // - then role access: eth10 (up), eth9 (down)
    // - then others (no role): eth02
    expect(names).toEqual(['eth2', 'eth1', 'eth10', 'eth9', 'eth02'])
  })
})
