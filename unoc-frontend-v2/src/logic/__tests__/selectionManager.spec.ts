import { describe, it, expect } from 'vitest'
import { createSelectionManager } from '../selectionManager'

describe('selectionManager', () => {
    it('toggle device', () => {
        const m = createSelectionManager(() => 0)
        m.toggle('d1', 'device')
        expect(m.state.items.length).toBe(1)
        m.toggle('d1', 'device')
        expect(m.state.items.length).toBe(0)
    })
})
