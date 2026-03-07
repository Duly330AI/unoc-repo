import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PassiveCockpit from '../components/cockpits/PassiveCockpit.vue'
import { useDevicesStore } from '../stores/devicesStore.js'

describe('PassiveCockpit', () => {
  it('renders insertion loss and type cues for passive devices', async () => {
    setActivePinia(createPinia())
    const devices = useDevicesStore()
    ;(devices as any).devices = [
      { id: 'p1', name: 'SPL-1', type: 'SPLITTER', status: 'UP', insertion_loss_db: 3.5 },
      { id: 'p2', name: 'ODF-1', type: 'ODF', status: 'UP', insertion_loss_db: 0 },
      { id: 'p3', name: 'NVT-1', type: 'NVT', status: 'UP', insertion_loss_db: 1.2 },
      { id: 'p4', name: 'HOP-1', type: 'HOP', status: 'UP', insertion_loss_db: 0.8 }
    ]

    const w1 = mount(PassiveCockpit, { props: { deviceId: 'p1' } })
    expect(w1.text()).toContain('3.5 dB')
    expect(w1.text()).toMatch(/TYPE:\s*SPLITTER/)

    const w2 = mount(PassiveCockpit, { props: { deviceId: 'p2' } })
    expect(w2.text()).toContain('LOSS:')
    expect(w2.text()).toMatch(/TYPE:\s*ODF/)

    const w3 = mount(PassiveCockpit, { props: { deviceId: 'p3' } })
    expect(w3.text()).toMatch(/TYPE:\s*NVT/)

    const w4 = mount(PassiveCockpit, { props: { deviceId: 'p4' } })
    expect(w4.text()).toMatch(/TYPE:\s*HOP/)
  })
})
