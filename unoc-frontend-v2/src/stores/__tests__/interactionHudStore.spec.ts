import { describe, it, expect } from 'vitest'
import { createHudManager } from '../../logic/hudManager'

describe('interactionHudStore (via manager)', () => {
    it('base entries contain link-mode and selection', () => {
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
