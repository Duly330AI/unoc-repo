import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Tooltip from '../components/ui/Tooltip.vue'
import { useTooltipStore } from '../stores/tooltipStore.js'

describe('Tooltip.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('renders hidden by default (not in DOM), then visible with content and offset', async () => {
    const w = mount(Tooltip)
    const store = useTooltipStore()

    // hidden initially -> state says not visible
    expect(store.isVisible).toBe(false)

    // show and advance timers
    store.show('Link A (72%)', 100, 200)
    vi.advanceTimersByTime(80)
    await w.vm.$nextTick()

    const root = w.get('.tooltip')
    expect(root.isVisible()).toBe(true)
    const content = w.get('.tooltip-content')
    expect(content.text()).toBe('Link A (72%)')
    // style includes +12 offset
    const style = root.attributes('style') || ''
    expect(style).toContain('left: 112px')
    expect(style).toContain('top: 212px')

    // hide after 120ms delay -> element removed from DOM
    store.hide()
    vi.advanceTimersByTime(120)
    await w.vm.$nextTick()
    expect(store.isVisible).toBe(false)
  })
})
