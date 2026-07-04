import { describe, expect, it } from 'vitest'
import { deriveNodeVisualStatus } from '../status.js'

describe('topologyCore status helpers', () => {
  it('derives visual status from operational and optical signal state', () => {
    expect(deriveNodeVisualStatus('UP', 'OK')).toBe('UP')
    expect(deriveNodeVisualStatus('UP', 'WARNING')).toBe('DEGRADED')
    expect(deriveNodeVisualStatus('UP', 'CRITICAL')).toBe('DEGRADED')
    expect(deriveNodeVisualStatus('DOWN', 'WARNING')).toBe('DOWN')
    expect(deriveNodeVisualStatus('Status.DOWN', 'CRITICAL')).toBe('DOWN')
    expect(deriveNodeVisualStatus('online', null)).toBe('UP')
  })
})
