import { describe, it, expect } from 'vitest'
import { createSelectionManager } from '../../logic/selectionManager'

describe('selectionStore (via manager)', () => {
    it('toggle link', () => {
        const m = createSelectionManager(() => 0)
        m.toggle('l1', 'link')
        expect(m.state.items.length).toBe(1)
        m.toggle('l1', 'link')
        expect(m.state.items.length).toBe(0)
    })
})
