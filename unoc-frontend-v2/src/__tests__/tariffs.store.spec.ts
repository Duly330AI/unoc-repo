import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTariffsStore } from '../stores/tariffsStore.js'

const sample = [
  { id: 1, name: 'Alpha', max_down_mbps: 100, max_up_mbps: 20 },
  { id: 2, name: 'Zeta', max_down_mbps: 50, max_up_mbps: 10 }
]

describe('tariffs store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fetchAll sorts by name', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(sample), { status: 200 })) as any
    const s = useTariffsStore()
    await s.fetchAll()
    expect(s.allSorted.map((t) => t.name)).toEqual(['Alpha', 'Zeta'])
  })

  it('create/update/delete happy paths', async () => {
    const s = useTariffsStore()
    // create
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(sample[0]), { status: 201 })) as any
    const created = await s.create({ name: 'Alpha', max_down_mbps: 100, max_up_mbps: 20 })
    expect(created.id).toBe(1)
    expect(Object.keys(s.$state.byId)).toContain('1')
    // update
    const upd = { ...sample[0], name: 'Alpha+', max_down_mbps: 120 }
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(upd), { status: 200 })) as any
    const updated = await s.update(1, { name: 'Alpha+', max_down_mbps: 120 })
    expect(updated.name).toBe('Alpha+')
    // delete
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 })) as any
    await s.remove(1)
    expect(s.$state.byId[1]).toBeUndefined()
  })

  it('surfaces 409 conflict message', async () => {
    const s = useTariffsStore()
    const body = JSON.stringify({ detail: 'TARIFF_NAME_EXISTS' })
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(body, { status: 409, headers: { 'Content-Type': 'application/json' } })
      ) as any
    await expect(s.create({ name: 'dup', max_down_mbps: 1, max_up_mbps: 1 })).rejects.toThrow(
      'TARIFF_NAME_EXISTS'
    )
  })

  it('fetchAll sets error on HTTP failure and respects loading guard', async () => {
    const s = useTariffsStore()
    // First call fails
    global.fetch = vi.fn().mockResolvedValue(new Response('nope', { status: 500 })) as any
    await s.fetchAll()
    expect(s.error).toContain('HTTP 500')
    // While loading, second call should be ignored
    s.$state.loading = true
    await s.fetchAll()
    // Ensure fetch was not called again while loading (still 1 call)
    expect((global.fetch as any).mock.calls.length).toBe(1)
    s.$state.loading = false
  })

  it('create throws generic error when no JSON detail', async () => {
    const s = useTariffsStore()
    global.fetch = vi.fn().mockResolvedValue(new Response('oops', { status: 400 })) as any
    await expect(s.create({ name: 'bad', max_down_mbps: 1, max_up_mbps: 1 })).rejects.toThrow(
      'Create failed 400'
    )
  })

  it('update/remove error paths', async () => {
    const s = useTariffsStore()
    // update error with no JSON
    global.fetch = vi.fn().mockResolvedValue(new Response('nope', { status: 500 })) as any
    await expect(s.update(123, { name: 'x' })).rejects.toThrow('Update failed 500')
    // remove error
    global.fetch = vi.fn().mockResolvedValue(new Response('nope', { status: 500 })) as any
    await expect(s.remove(123)).rejects.toThrow('Delete failed 500')
  })
})
