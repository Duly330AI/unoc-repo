// Delegated to logic/toastManager.spec.ts; keeping placeholder to avoid duplicate logic.
import { describe, it, expect } from 'vitest'
import { createToastManager } from '../../logic/toastManager'

describe('toastStore (via manager)', () => {
    it('pending -> succeed', () => {
        const m = createToastManager(() => 0)
        const id = m.pending('Loading')
        expect(m.state.toasts.find(t => t.id === id)?.variant).toBe('pending')
        m.succeed(id, 'Done')
        expect(m.state.toasts.find(t => t.id === id)?.variant).toBe('success')
    })
})
