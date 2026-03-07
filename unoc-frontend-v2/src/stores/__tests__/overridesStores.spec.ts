import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from '../../test/pinia-shim'
import { useDevicesStore } from '../devicesStore.js'
import { useLinksStore } from '../linksStore.js'

describe('override actions in stores', () => {
  const origFetch = globalThis.fetch
  beforeEach(() => {
    setActivePinia(createPinia())
    ;(globalThis as unknown as { fetch: unknown }).fetch = vi.fn()
  })
  afterEach(() => {
    ;(globalThis as unknown as { fetch: unknown }).fetch =
      origFetch as unknown as typeof globalThis.fetch
    vi.restoreAllMocks()
  })

  it('devicesStore.setOverride updates state', async () => {
    const store = useDevicesStore()
    store.devices = [
      {
        id: 'd1',
        name: 'd1',
        type: 'CORE_ROUTER' as any,
        status: 'UP' as any,
        role: 'active',
        provisioned: false as any,
        admin_override_status: null
      }
    ]
    const updated = { ...store.devices[0], admin_override_status: 'DOWN' }
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => updated
    })
    const resp = await store.setOverride('d1', 'DOWN')
    expect(resp.admin_override_status).toBe('DOWN')
    expect(store.byId('d1')?.admin_override_status).toBe('DOWN')
  })

  it('linksStore.setOverride updates state', async () => {
    const store = useLinksStore()
    store.links = [
      {
        id: 'L1',
        a_interface_id: 'A-if0',
        b_interface_id: 'B-if0',
        a_device_id: 'A',
        b_device_id: 'B',
        status: 'UP',
        kind: 'FIBER',
        admin_override_status: null
      }
    ]
    const updated = { ...store.links[0], admin_override_status: 'DOWN' }
    ;(globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => updated
    })
    const resp = await store.setOverride('L1', 'DOWN')
    expect(resp.admin_override_status).toBe('DOWN')
    expect(store.links.find((l) => l.id === 'L1')?.admin_override_status).toBe('DOWN')
  })
})
