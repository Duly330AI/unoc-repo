import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useContextMenuStore } from '../contextMenuStore'

describe('contextMenuStore', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
    })

    it('sets position and items on show', () => {
        const store = useContextMenuStore()
        store.show(100, 150, [{ id: 'a', label: 'A', action: () => { } }], { kind: 'canvas', id: null })
        expect(store.open).toBe(true)
        expect(store.pos.x).toBeGreaterThanOrEqual(0)
        expect(store.pos.y).toBeGreaterThanOrEqual(0)
        expect(store.items.length).toBe(1)
    })

    it('clamps position to viewport', () => {
        const store = useContextMenuStore()
        // Use very large coordinates; store clamps to window.innerWidth/innerHeight minus menu size
        store.show(100000, 100000, new Array(20).fill(0).map((_, i) => ({ id: 'it' + i, label: 'Item ' + i, action: () => { } })), { kind: 'canvas', id: null })
        const vw = window.innerWidth
        const vh = window.innerHeight
        expect(store.pos.x).toBeLessThanOrEqual(vw)
        expect(store.pos.y).toBeLessThanOrEqual(vh)
    })
})
