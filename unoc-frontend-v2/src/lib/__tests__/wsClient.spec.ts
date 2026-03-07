import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { wsClient } from '../wsClient.js'
import { eventBus } from '../eventBus.js'

// Basic smoke test for wsClient wiring without real server

describe('wsClient', () => {
  const origWebSocket = globalThis.WebSocket
  let messages: any[] = []

  beforeEach(() => {
    messages = []
    // Mock WebSocket
    class MockWS {
      readyState = 1
      onopen: (() => void) | null = null
      onclose: (() => void) | null = null
      onmessage: ((ev: MessageEvent) => void) | null = null
      onerror: ((ev: Event) => void) | null = null
      constructor(public url: string) {
        setTimeout(() => {
          if (this.onopen) this.onopen()
        }, 0)
      }
      send(data: unknown) {
        messages.push(data)
      }
      close() {
        if (this.onclose) this.onclose()
      }
    }
    globalThis.WebSocket = MockWS as unknown as typeof WebSocket
  })

  afterEach(() => {
    wsClient.stop()
    globalThis.WebSocket = origWebSocket!
  })

  it('emits status and forwards events', async () => {
    const status: any[] = []
    const events: any[] = []
    const unsub1 = eventBus.on('ws:status', (s) => status.push(s))
    const unsub2 = eventBus.on('device.status.changed', (e) => events.push(e))
    wsClient.start()
    await new Promise((r) => setTimeout(r, 5))
    expect(status.some((s) => s.status === 'connected')).toBe(true)
    // Fake message
    const ws = (wsClient as unknown as { ws: { onmessage: (ev: MessageEvent) => void } }).ws
    ws.onmessage!({
      data: JSON.stringify({ type: 'device.status.changed', payload: { id: 'd1', status: 'UP' } })
    } as MessageEvent)
    await new Promise((r) => setTimeout(r, 0))
    expect(events.length).toBe(1)
    unsub1()
    unsub2()
  })
})
