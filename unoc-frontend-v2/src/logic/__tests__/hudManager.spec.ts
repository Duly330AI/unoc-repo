import { describe, it, expect } from 'vitest'
import { createHudManager } from '../hudManager'

describe('hudManager', () => {
    it('generates base entries including link-mode & selection', () => {
        const mgr = createHudManager(() => [
            { id: 'd1', kind: 'device' },
            { id: 'l1', kind: 'link' }
        ])
        mgr.toggleVisible(true)
        const ids = mgr.state.entries.map(e => e.id)
        expect(ids).toContain('link-mode')
        expect(ids).toContain('selection')
    })
})
