import { setActivePinia, createPinia } from 'pinia'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useLayoutStore } from '../layoutStore'

describe('layoutStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.restoreAllMocks()
  })

  it('hydrates positions from API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ version: 1, positions: [{ id: 'n1', x: 10, y: 20, userPinned: true }] })
    }) as any
    const store = useLayoutStore()
    await store.hydrate()
    expect(store.byId['n1']).toEqual({ id: 'n1', x: 10, y: 20, userPinned: true })
  })

  it('queues moves and flushes throttled', async () => {
    const patchSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ applied: 1 }) })
    global.fetch = vi.fn().mockImplementation((url: string, init?: any) => {
      if (String(url).includes('/api/layout/positions') && init?.method === 'PATCH') {
        return patchSpy()
      }
      return Promise.resolve({ ok: true, json: async () => ({ version: 0, positions: [] }) })
    }) as any

    const store = useLayoutStore()
    await store.hydrate()
    store.markMoved('a', 1, 2, true)
    store.markMoved('b', 3, 4, true)
    // not flushed yet
    expect(patchSpy).not.toHaveBeenCalled()
    // advance time to trigger timer
    vi.advanceTimersByTime(2100)
    await Promise.resolve()
    expect(patchSpy).toHaveBeenCalledTimes(1)
    // dirty cleared by flush
    expect(store.dirty.size).toBe(0)
  })

  it('flushNow sends all dirty immediately', async () => {
    const patchSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ applied: 2 }) })
    global.fetch = vi.fn().mockImplementation((url: string, init?: any) => {
      if (String(url).includes('/api/layout/positions') && init?.method === 'PATCH') {
        return patchSpy()
      }
      return Promise.resolve({ ok: true, json: async () => ({ version: 0, positions: [] }) })
    }) as any
    const store = useLayoutStore()
    await store.hydrate()
    store.markMoved('x', 9, 9)
    store.markMoved('y', 8, 8)
    await store.flushNow()
    expect(patchSpy).toHaveBeenCalledTimes(1)
    // First arg to fetch is URL, second is init; pick last call (the PATCH)
    const calls = (global.fetch as any).mock.calls
    const init = calls[calls.length - 1][1]
    const body = JSON.parse(init?.body || 'null')
    expect(body.positions.length).toBe(2)
  })
})
