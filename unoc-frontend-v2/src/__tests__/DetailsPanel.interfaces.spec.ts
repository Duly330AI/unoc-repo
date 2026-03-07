import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DetailsPanel from '../components/layout/DetailsPanel.vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useDevicesStore } from '../stores/devicesStore.js'
import { nextTick } from 'vue'

function iface(
  id: string,
  name: string,
  admin: 'up' | 'down' = 'up',
  role?: string | null,
  mac?: string | null
) {
  return { id, name, admin_status: admin, role: role ?? null, mac_address: mac ?? null }
}

describe('DetailsPanel - Interfaces tab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows interfaces and loads addresses per interface', async () => {
    const devices = useDevicesStore()
    ;(devices as any).devices = [
      {
        id: 'd1',
        name: 'Dev 1',
        type: 'EDGE_ROUTER',
        status: 'UP',
        provisioned: false,
        role: 'active',
        device_default_vrf_name: 'mgmt',
        interfaces: [
          iface('d1-eth0', 'eth0', 'up', 'access', '00:11:22:33:44:55'),
          iface('d1-eth1', 'eth1', 'down')
        ]
      }
    ]
    const selection = useSelectionStore()
    selection.select('d1', 'device')

    // Mock fetch for addresses
    global.fetch = vi.fn((url: string) => {
      if (url.includes('/api/interfaces/d1-eth0/addresses')) {
        return Promise.resolve(
          new Response(
            JSON.stringify([
              {
                id: 1,
                interface_id: 'd1-eth0',
                ip: '10.0.0.10',
                prefix_len: 24,
                prefix_id: 1,
                prefix_string: '10.250.0.0/24'
              }
            ]),
            { status: 200 }
          )
        ) as any
      }
      if (url.includes('/api/interfaces/d1-eth1/addresses')) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 })) as any
      }
      if (url.endsWith('/api/optical/fiber-types')) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 })) as any
      }
      // default devices list
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 })) as any
    }) as any

    const w = mount(DetailsPanel)
    // Switch to Interfaces tab
    await w.findAll('button.tab').at(1)?.trigger('click')
    const flush = async () => {
      await Promise.resolve()
      await Promise.resolve()
      await nextTick()
    }
    await flush()
    await flush()

    // Expect two interface blocks
    const ifaces = w.findAll('.interfaces-tab .iface')
    expect(ifaces.length).toBe(2)

    // VRF banner shows mgmt
    const vrf = w.find('.interfaces-tab .vrf-banner span')
    expect(vrf.exists()).toBe(true)
    expect(vrf.text()).toBe('mgmt')

    // Addresses loaded and rendered for eth0 (wait for async fetch)
    let addrChips = ifaces.at(0)?.findAll('code.addr') || []
    if (addrChips.length === 0) {
      for (let i = 0; i < 5; i++) {
        await flush()
        addrChips = ifaces.at(0)?.findAll('code.addr') || []
        if (addrChips.length > 0) break
      }
    }
    expect(addrChips.length).toBe(1)
    expect(addrChips.at(0)?.text()).toBe('10.0.0.10/24 / 10.250.0.0/24')

    // No addresses for eth1 shows dash
    const addrText = ifaces.at(1)?.find('.row.addresses span')?.text() || ''
    expect(addrText.trim()).toBe('—')
  })
})
