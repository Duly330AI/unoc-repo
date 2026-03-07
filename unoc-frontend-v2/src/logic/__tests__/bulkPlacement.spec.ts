import { describe, it, expect } from 'vitest'
import { generateBulkPositions } from '../bulkPlacement'

describe('bulk placement generator', () => {
    it('generates positions within bounds', () => {
        const width = 1200, height = 800, count = 50
        const pos = generateBulkPositions({ count, width, height })
        expect(pos).toHaveLength(count)
        for (const p of pos) {
            expect(p.x).toBeGreaterThanOrEqual(0)
            expect(p.y).toBeGreaterThanOrEqual(0)
            expect(p.x).toBeLessThanOrEqual(width)
            expect(p.y).toBeLessThanOrEqual(height)
        }
    })
})