import { eventBus, type EventEnvelope } from './eventBus.js'

type Options = {
  url?: string
  maxBackoffMs?: number
  baseBackoffMs?: number
  heartbeatMs?: number
}

class WsClient {
  private ws: WebSocket | null = null
  private readonly url: string
  private readonly maxBackoff: number
  private readonly baseBackoff: number
  private backoff: number
  private reconnectTimer: number | null = null
  private heartbeatTimer: number | null = null
  private readonly heartbeatMs: number
  private closedByUser = false

  constructor(opts: Options = {}) {
    const loc = window.location
    // Prefer same-origin WS under Vite proxy; if running on dev server (port != 5001),
    // fall back to directly hitting the backend WS on 5001 to guarantee realtime works
    const sameOriginUrl = `${loc.protocol === 'https:' ? 'wss' : 'ws'}://${loc.host}/api/ws`
    const directBackendUrl = `${loc.protocol === 'https:' ? 'wss' : 'ws'}://${loc.hostname}:5001/api/ws`
    const defaultUrl = loc.port && loc.port !== '5001' ? directBackendUrl : sameOriginUrl
    this.url = opts.url || defaultUrl
    this.maxBackoff = opts.maxBackoffMs ?? 10_000
    this.baseBackoff = opts.baseBackoffMs ?? 500
    this.backoff = this.baseBackoff
    this.heartbeatMs = opts.heartbeatMs ?? 15_000
  }

  start() {
    this.closedByUser = false
    this.connect()
  }

  stop() {
    this.closedByUser = true
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer)
    if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer)
    this.reconnectTimer = null
    this.heartbeatTimer = null
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.close()
      } catch {
        /* noop */
      }
    }
    this.ws = null
  }

  private connect() {
    try {
      this.ws = new WebSocket(this.url)
    } catch (e) {
      console.error('[wsClient] WS construct failed', e)
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      // eslint-disable-next-line no-console
      console.debug('[wsClient] connected', this.url)
      eventBus.emit('ws:status', { status: 'connected' })
      this.backoff = this.baseBackoff
      if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = window.setInterval(() => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
        try {
          this.ws.send(JSON.stringify({ type: '__pong__' }))
        } catch {
          /* noop */
        }
      }, this.heartbeatMs) as unknown as number
    }

    this.ws.onclose = () => {
      // eslint-disable-next-line no-console
      console.debug('[wsClient] closed')
      eventBus.emit('ws:status', { status: 'disconnected' })
      if (!this.closedByUser) this.scheduleReconnect()
    }

    this.ws.onerror = (ev) => {
      console.debug('[wsClient] error', ev)
      // errors typically followed by onclose; rely on reconnect cycle
    }

    this.ws.onmessage = (ev) => {
      const data = ev.data
      // Backend may send raw string "__ping__"; we answer with __pong__ in heartbeat loop.
      if (typeof data === 'string') {
        if (data === '__ping__') {
          // handled by heartbeat interval
          return
        }
        try {
          const obj = JSON.parse(data) as EventEnvelope
          if (obj && obj.type) {
            if (import.meta.env?.DEV) {
              // eslint-disable-next-line no-console
              const anyObj: unknown = obj
              const payload =
                anyObj && typeof anyObj === 'object' && 'payload' in anyObj
                  ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    (anyObj as Record<string, any>).payload
                  : undefined
              const keys =
                payload && typeof payload === 'object'
                  ? Object.keys(payload as Record<string, unknown>)
                  : []
              console.debug('[wsClient] recv', obj.type, keys)
            }
            eventBus.emit('ws:event', obj)
            eventBus.emit(obj.type, obj)
          }
        } catch {
          // ignore non-JSON messages
        }
        return
      }
      // Non-string payloads not expected; ignore
    }
  }

  private scheduleReconnect() {
    if (this.closedByUser) return
    const jitter = Math.random() * this.backoff * 0.25
    const delay = Math.min(this.backoff + jitter, this.maxBackoff)
    eventBus.emit('ws:status', { status: 'reconnecting', delayMs: Math.round(delay) })
    this.reconnectTimer = window.setTimeout(() => {
      this.connect()
      this.backoff = Math.min(this.backoff * 2, this.maxBackoff)
    }, delay) as unknown as number
  }
}

export const wsClient = new WsClient()
