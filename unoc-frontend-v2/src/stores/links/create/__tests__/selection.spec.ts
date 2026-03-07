import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  computeSelections,
  buildUsedInterfaceSet,
  filterPONForOLT,
  phase1GuardsOk
} from '../selection'

// Minimal device store stub
function makeDevStore(devices: Record<string, any>) {
  return {
    byId: (id: string) => devices[id],
    fetchAllWithInterfaces: vi.fn()
  } as any
}

function iface(id: string, name: string, extra: any = {}) {
  return { id, name, admin_status: 'up', ...extra }
}

describe('links/create selection helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('buildUsedInterfaceSet collects a/b interface ids', () => {
    const used = buildUsedInterfaceSet([
      { a_interface_id: 'd1-if0', b_interface_id: 'd2-if0' } as any,
      { a_interface_id: 'd3-if1', b_interface_id: 'd4-if2' } as any
    ])
    expect(used.has('d1-if0')).toBe(true)
    expect(used.has('d2-if0')).toBe(true)
    expect(used.has('d3-if1')).toBe(true)
    expect(used.has('d4-if2')).toBe(true)
  })

  it('computeSelections prefers ACCESS on AON_SWITCH side and PON on OLT side', () => {
    const devices = {
      sw: {
        id: 'sw',
        type: 'AON_SWITCH',
        interfaces: [
          iface('sw-if0', 'if0', { port_role: 'UPLINK' }),
          iface('sw-if1', 'if1', { port_role: 'ACCESS' })
        ]
      },
      cpe: { id: 'cpe', type: 'AON_CPE', interfaces: [iface('cpe-if0', 'if0')] },
      olt: {
        id: 'olt',
        type: 'OLT',
        interfaces: [
          iface('olt-if0', 'if0', { port_role: 'PON' }),
          iface('olt-if1', 'if1', { port_role: 'UPLINK' })
        ]
      },
      odf: {
        id: 'odf',
        type: 'ODF',
        interfaces: [iface('odf-if0', 'if0'), iface('odf-if1', 'if1')]
      }
    }
    const devStore = makeDevStore(devices)
    const links: any[] = []

    // AON pair
    let sel = computeSelections(devStore as any, links as any, 'cpe', 'sw')
    expect(sel.aType).toBe('AON_CPE')
    expect(sel.bType).toBe('AON_SWITCH')
    // sw side should choose ACCESS (sw-if1)
    expect([sel.aIface, sel.bIface]).toContain('sw-if1')

    // OLT ↔ ODF: anchor ODF if0 and OLT side should prefer PON
    sel = computeSelections(devStore as any, links as any, 'olt', 'odf')
    expect(sel.aIface === 'olt-if0' || sel.bIface === 'olt-if0').toBe(true)
    expect(sel.aIface === 'odf-if0' || sel.bIface === 'odf-if0').toBe(true)
  })

  it('filterPONForOLT filters out already linked PON ports', () => {
    const devices = {
      olt: {
        id: 'olt',
        type: 'OLT',
        interfaces: [
          iface('olt-if0', 'if0', { port_role: 'PON' }),
          iface('olt-if1', 'if1', { port_role: 'PON' })
        ]
      }
    }
    const devStore = makeDevStore(devices)
    const links = [
      { a_device_id: 'olt', a_interface_id: 'olt-if0', b_device_id: 'x', b_interface_id: 'x-if0' }
    ] as any
    const opts = [
      { id: 'olt-if0', label: 'if0' },
      { id: 'olt-if1', label: 'if1' }
    ]
    const filtered = filterPONForOLT(links as any, devStore as any, 'olt', opts)
    expect(filtered.map((o) => o.id)).toEqual(['olt-if1'])
  })

  it('phase1GuardsOk blocks OLT↔ONT and enforces OLT↔ODF', () => {
    const devices = {
      olt: { id: 'olt', type: 'OLT' },
      ont: { id: 'ont', type: 'ONT' },
      odf: { id: 'odf', type: 'ODF' }
    }
    const devStore = makeDevStore(devices)
    ;(globalThis as any).UNOC_FLAGS = { GPON_ODF_AGG_PHASE1: '1' }

    // OLT↔ONT should be blocked
    let ok = phase1GuardsOk([] as any, devStore as any, 'olt', 'ont', 'OLT', 'ONT')
    expect(ok).toBe(false)

    // OLT must connect to ODF
    ok = phase1GuardsOk([] as any, devStore as any, 'olt', 'odf', 'OLT', 'ODF')
    expect(ok).toBe(true)
  })
})
