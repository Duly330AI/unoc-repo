import { describe, it, expect } from 'vitest'
import { validateOntPassive, annotatePassiveOptionsViaOlt } from '../helpers'

function makeDevStore(devices: Record<string, any>) {
  return {
    byId: (id: string) => devices[id]
  } as any
}

describe('links/create helpers (BFS over passive graph)', () => {
  it('validateOntPassive returns true when passive chain has ODF→OLT upstream', () => {
    const devices = {
      olt: { id: 'olt', type: 'OLT', name: 'OLT-1' },
      odf: { id: 'odf', type: 'ODF', name: 'ODF-A' },
      spl: { id: 'spl', type: 'SPLITTER', name: 'SPL-1' },
      ont: { id: 'ont', type: 'ONT', name: 'ONT-1' }
    }
    const devStore = makeDevStore(devices)
    const store = {
      links: [
        { a_device_id: 'odf', b_device_id: 'olt' },
        { a_device_id: 'odf', b_device_id: 'spl' }
      ]
    }
    const ok = validateOntPassive(store as any, devStore as any, 'ont', 'spl')
    expect(ok).toBe(true)
  })

  it('validateOntPassive returns false when no upstream ODF→OLT exists', () => {
    const devices = {
      spl: { id: 'spl', type: 'SPLITTER' },
      nvt: { id: 'nvt', type: 'NVT' }
    }
    const devStore = makeDevStore(devices)
    const store = {
      links: [{ a_device_id: 'spl', b_device_id: 'nvt' }]
    }
    const ok = validateOntPassive(store as any, devStore as any, 'ont', 'spl')
    expect(ok).toBe(false)
  })

  it('annotatePassiveOptionsViaOlt appends OLT name to labels when reachable', () => {
    const devices = {
      olt: { id: 'olt', type: 'OLT', name: 'OLT-Alpha' },
      odf: { id: 'odf', type: 'ODF', name: 'ODF-Z' },
      hop: { id: 'hop', type: 'HOP', name: 'HOP-1' }
    }
    const devStore = makeDevStore(devices)
    const store = {
      links: [
        { a_device_id: 'odf', b_device_id: 'olt' },
        { a_device_id: 'odf', b_device_id: 'hop' }
      ]
    }
    const opts = [
      { id: 'hop-if1', label: 'if1' },
      { id: 'hop-if2', label: 'if2' }
    ]
    const out = annotatePassiveOptionsViaOlt(store as any, devStore as any, 'hop', opts)
    expect(out[0].label).toContain('• via OLT OLT-Alpha')
    expect(out[1].label).toContain('• via OLT OLT-Alpha')
  })
})
