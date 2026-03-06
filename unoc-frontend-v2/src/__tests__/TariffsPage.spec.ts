import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useTariffsStore } from '../stores/tariffsStore.js'
import TariffsPage from '../pages/TariffsPage.vue'

const list = [
  { id: 1, name: 'A', max_down_mbps: 10, max_up_mbps: 1 },
  { id: 2, name: 'B', max_down_mbps: 20, max_up_mbps: 2 }
]

describe('TariffsPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('lists and opens create modal', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(list), { status: 200 })) as any
    const store = useTariffsStore()
    const w = mount(TariffsPage)
    // deterministically load data via the shared store instance
    const flush = async () => {
      await Promise.resolve()
      await Promise.resolve()
      await nextTick()
    }
    await store.fetchAll()
    await flush()
    await flush()
    expect(w.findAll('tbody tr').length).toBe(2)
    await w.get('button.btn').trigger('click') // New Tariff
    expect(w.findComponent({ name: 'TariffFormModal' }).exists()).toBe(true)
  })
})
