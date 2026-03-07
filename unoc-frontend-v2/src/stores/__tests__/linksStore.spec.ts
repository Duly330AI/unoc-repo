import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDevicesStore } from '../devicesStore.js'
import { useLinksStore } from '../linksStore.js'

describe('linksStore (ODF↔ODF guard)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('blocks ODF to ODF linking attempts early', async () => {
    const devices = useDevicesStore()
    // Seed two ODF devices with minimal interfaces
    devices.devices = [
      {
        id: 'odfA',
        name: 'ODF A',
        type: 'ODF',
        status: 'UP',
        role: 'passive',
        provisioned: false,
        interfaces: [
          {
            id: 'odfA-if0',
            device_id: 'odfA',
            id2: 'odfA-if0',
            name: 'if0',
            admin_status: 'up',
            status: 'UP'
          } as unknown as any
        ]
      } as unknown as any,
      {
        id: 'odfB',
        name: 'ODF B',
        type: 'ODF',
        status: 'UP',
        role: 'passive',
        provisioned: false,
        interfaces: [
          {
            id: 'odfB-if0',
            device_id: 'odfB',
            name: 'if0',
            admin_status: 'up',
            status: 'UP'
          } as unknown as any
        ]
      } as unknown as any
    ]

    const links = useLinksStore()
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    await links.createBetweenDevices('odfA', 'odfB')

    expect(dispatchSpy).not.toHaveBeenCalled()
    expect(warnSpy).toHaveBeenCalled()

    dispatchSpy.mockRestore()
    warnSpy.mockRestore()
  })
})
