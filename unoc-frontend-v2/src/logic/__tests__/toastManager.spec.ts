import { describe, it, expect } from 'vitest'
import { createToastManager } from '../toastManager'

describe('toastManager', () => {
    it('pending -> succeed', () => {
        const m = createToastManager(() => 0)
        const id = m.pending('Loading')
        expect(m.state.toasts.find(t => t.id === id)?.variant).toBe('pending')
        m.succeed(id, 'Done')
        expect(m.state.toasts.find(t => t.id === id)?.variant).toBe('success')
    })
})
