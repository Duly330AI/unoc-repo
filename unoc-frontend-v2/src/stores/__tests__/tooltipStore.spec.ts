import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTooltipStore } from '../../stores/tooltipStore.js'

describe('tooltipStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('is hidden by default and shows after 80ms', () => {
    const store = useTooltipStore()
    expect(store.isVisible).toBe(false)

    store.show('Hello', 10, 20)
    // Not visible immediately (enter delay)
    expect(store.isVisible).toBe(false)
    vi.advanceTimersByTime(79)
    expect(store.isVisible).toBe(false)
    vi.advanceTimersByTime(1)
    expect(store.isVisible).toBe(true)
    expect(store.content).toBe('Hello')
    expect(store.x).toBe(10)
    expect(store.y).toBe(20)
  })

  it('moves only when visible', () => {
    const store = useTooltipStore()
    store.move(100, 100)
    expect(store.x).toBe(0)
    expect(store.y).toBe(0)
    store.show('A', 1, 2)
    vi.advanceTimersByTime(80)
    store.move(100, 100)
    expect(store.x).toBe(100)
    expect(store.y).toBe(100)
  })

  it('hides after 120ms delay and cancels pending show', () => {
    const store = useTooltipStore()
    // Schedule a show, then immediately hide -> show should be cancelled
    store.show('Late', 5, 5)
    store.hide()
    vi.advanceTimersByTime(80)
    expect(store.isVisible).toBe(false)
    expect(store.content).toBeNull()

    // Make visible, then hide with delay
    store.show('Now', 9, 9)
    vi.advanceTimersByTime(80)
    expect(store.isVisible).toBe(true)
    store.hide()
    vi.advanceTimersByTime(119)
    expect(store.isVisible).toBe(true)
    vi.advanceTimersByTime(1)
    expect(store.isVisible).toBe(false)
    expect(store.content).toBeNull()
  })

  it('does not show for empty content and resets state', () => {
    const store = useTooltipStore()
    store.show('   ', 10, 10)
    // no timers should flip visibility when content is empty
    vi.advanceTimersByTime(200)
    expect(store.isVisible).toBe(false)
    expect(store.content).toBeNull()
    expect(store.x).toBe(0)
    expect(store.y).toBe(0)
  })

  it('reset cancels timers and clears state', () => {
    const store = useTooltipStore()
    store.show('Soon', 3, 4)
    // schedule hide as well to ensure both timers get cleared
    store.hide()
    store.reset()
    vi.advanceTimersByTime(500)
    expect(store.isVisible).toBe(false)
    expect(store.content).toBeNull()
    expect(store.x).toBe(0)
    expect(store.y).toBe(0)
  })
})
