import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DetailsPanel from '../components/layout/DetailsPanel.vue'
import { useSelectionStore } from '../stores/selectionStore.js'
import { useLinksStore } from '../stores/linksStore.js'
import { useLinkMetricsStore } from '../stores/linkMetricsStore.js'

function mockFetchLinksOnce() {
  global.fetch = vi.fn((url: string, init?: RequestInit) => {
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
              kind: 'FIBER'
            }
          ]),
          { status: 200 }
        )
      ) as any
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 })) as any
  }) as any
}

describe('DetailsPanel - Link utilization metrics', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders utilization % and bps from linkMetricsStore', async () => {
    mockFetchLinksOnce()

    const links = useLinksStore()
    await links.fetchAll()

    const selection = useSelectionStore()
    selection.select('d1__d2', 'link')

    const linkMetrics = useLinkMetricsStore()
    // Prime metrics store with one entry
    linkMetrics.applySnapshot({
      links: {
        d1__d2: { bps: 123456789, utilization: 0.37, version: 1 }
      },
      lastTick: 1
    })

    const w = mount(DetailsPanel)
    // flush microtasks
    for (let i = 0; i < 5; i++) await Promise.resolve()

    const meta = w.find('.link-details .meta-list')
    expect(meta.exists()).toBe(true)
    expect(meta.text()).toContain('Utilization')
    expect(meta.text()).toContain('37%')
    expect(meta.text()).toContain('Throughput')
    // bps formatter should yield Mbps or Gbps string; check it contains unit
    const txt = meta.text()
    const hasUnit = /Gbps|Mbps|Kbps|bps/.test(txt)
    expect(hasUnit).toBe(true)
  })
})
