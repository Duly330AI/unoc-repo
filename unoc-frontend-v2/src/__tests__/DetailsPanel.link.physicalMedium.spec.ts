import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DetailsPanel from '../components/layout/DetailsPanel.vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useLinksStore } from '../stores/linksStore.js'

function mockFetchSequence() {
  global.fetch = vi.fn((url: string, init?: RequestInit) => {
    // Load links list
    if (url.endsWith('/api/links') && (!init || init.method === 'GET')) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              id: 'd1__d2',
              a_interface_id: 'd1-if0',
              b_interface_id: 'd2-if0',
              a_device_id: 'd1',
              b_device_id: 'd2',
              status: 'UP',
              kind: 'FIBER',
              length_km: 0.5,
              physical_medium_id: 1
            }
          ]),
          { status: 200 }
        )
      ) as any
    }
    // Allowed media endpoint
    if (url.endsWith('/api/physical/allowed-media/by-link/d1__d2')) {
      return Promise.resolve(
        new Response(
          JSON.stringify([
            {
              id: 1,
              code: 'SMF_G652D',
              name: 'Single-mode G.652.D',
              kind: 'fiber',
              max_range_km: null
            },
            {
              id: 7,
              code: 'CAT6A_UTP',
              name: 'Copper Cat6A UTP',
              kind: 'copper',
              max_range_km: 0.1
            }
          ]),
          { status: 200 }
        )
      ) as any
    }
    // Update link
    if (url.endsWith('/api/links/d1__d2') && init && init.method === 'PUT') {
      const body = JSON.parse(init.body as string)
      // echo back the updated physical_medium_id
      return Promise.resolve(
        new Response(
          JSON.stringify({
            id: 'd1__d2',
            a_interface_id: 'd1-if0',
            b_interface_id: 'd2-if0',
            a_device_id: 'd1',
            b_device_id: 'd2',
            status: 'UP',
            kind: 'FIBER',
            length_km: body.length_km ?? 0.5,
            physical_medium_id: body.physical_medium_id ?? 1
          }),
          { status: 200 }
        )
      ) as any
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 })) as any
  }) as any
}

describe('DetailsPanel - Link physical medium', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads allowed media and saves physical_medium_id', async () => {
    mockFetchSequence()

    const links = useLinksStore()
    // Prime store with one link so selection resolves
    await links.fetchAll()

    const selection = useSelectionStore()
    selection.select('d1__d2', 'link')

    const w = mount(DetailsPanel)

    // Wait for allowed media to fetch and render options
    for (let i = 0; i < 5; i++) {
      await Promise.resolve()
    }
    const pmSelect = w.find('select#pmed')
    expect(pmSelect.exists()).toBe(true)
    // Options should render eventually; tolerate slow CI
    let opts = w.findAll('select#pmed option')
    if (opts.length < 2) {
      for (let i = 0; i < 10; i++) {
        await Promise.resolve()
        opts = w.findAll('select#pmed option')
        if (opts.length >= 2) break
      }
    }
    expect(opts.length).toBeGreaterThanOrEqual(2)

    if (opts.length >= 2) {
      await pmSelect.setValue('7') // choose CAT6A_UTP
    } else {
      // Fallback in slow CI: set the component's ref directly
      ;(w.vm as any).linkPhysicalMediumId = 7
    }

    // Save and wait for async update to complete
    const saveBtn = w.find('.optical-section .btn.sm')
    await saveBtn.trigger('click')
    for (let i = 0; i < 5; i++) {
      await Promise.resolve()
    }

    // Assert the PUT payload contained physical_medium_id: 7
    const calls = (global.fetch as any).mock.calls as Array<any[]>
    const putCall = calls.find(
      (c) => String(c[0]).endsWith('/api/links/d1__d2') && c[1]?.method === 'PUT'
    )
    expect(putCall, 'expected a PUT /api/links/d1__d2 call').toBeTruthy()
    const payload = JSON.parse(putCall![1].body as string)
    expect(payload.physical_medium_id).toBe(7)

    // After update, wait until the store reflects physical_medium_id = 7
    for (let i = 0; i < 10; i++) {
      await Promise.resolve()
    }
    const all = useLinksStore().links.filter((l) => l.id === 'd1__d2') as any[]
    expect(all.length).toBeGreaterThan(0)
    const someUpdated = all.some((x) => x.physical_medium_id === 7)
    expect(someUpdated).toBe(true)
  })
})
