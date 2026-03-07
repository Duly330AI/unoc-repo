import { describe, it, expect } from 'vitest'
import * as nodes from '../render/nodes'
import * as containers from '../render/containers'

// Ensure rendering helper modules are covered by light imports and simple invariant checks

describe('topologyCore render smoke', () => {
  it('nodes module loads and exports object', () => {
    expect(nodes).toBeTruthy()
    expect(typeof nodes).toBe('object')
  })

  it('containers module loads and exports object', () => {
    expect(containers).toBeTruthy()
    expect(typeof containers).toBe('object')
  })
})
