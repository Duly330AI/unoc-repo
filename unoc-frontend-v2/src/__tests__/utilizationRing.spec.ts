import { describe, it, expect } from 'vitest'
import { getUtilBucket, colorForUtil, DEFAULT_UTILIZATION_BUCKETS } from '../colorScale'

describe('utilization buckets mapping', () => {
  it('maps thresholds correctly', () => {
    expect(getUtilBucket(0)).toBe(0)
    expect(getUtilBucket(49.9)).toBe(0)
    expect(getUtilBucket(50)).toBe(0)
    expect(getUtilBucket(50.1)).toBe(1)
    expect(getUtilBucket(69.9)).toBe(1)
    expect(getUtilBucket(70)).toBe(1)
    expect(getUtilBucket(70.1)).toBe(2)
    expect(getUtilBucket(89.9)).toBe(2)
    expect(getUtilBucket(90)).toBe(2)
    expect(getUtilBucket(90.1)).toBe(3)
    expect(getUtilBucket(100)).toBe(3)
    expect(getUtilBucket(100.1)).toBe(4)
    expect(getUtilBucket(150)).toBe(4)
  })

  it('color mapping returns a color string', () => {
    for (const p of [0, 10, 55, 80, 95, 120]) {
      const c = colorForUtil(p)
      expect(typeof c).toBe('string')
      expect(c.length).toBeGreaterThan(0)
    }
  })

  it('default constants shape', () => {
    expect(Array.isArray(DEFAULT_UTILIZATION_BUCKETS)).toBe(true)
    expect(DEFAULT_UTILIZATION_BUCKETS).toEqual([50, 70, 90, 100])
  })
})
