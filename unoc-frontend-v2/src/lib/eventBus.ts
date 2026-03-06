// Simple event bus based on a tiny emitter (no external dep to keep it lean)
// We implement a minimal Pub/Sub to avoid bundling an extra library.

type Handler<T = unknown> = (payload: T) => void
type Handlers = Map<string, Set<Handler>>

class EventBus {
  private handlers: Handlers = new Map()

  on<T = unknown>(type: string, handler: Handler<T>) {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler as Handler)
    return () => this.off(type, handler)
  }

  off<T = unknown>(type: string, handler: Handler<T>) {
    const set = this.handlers.get(type)
    if (!set) return
    set.delete(handler as Handler)
    if (set.size === 0) this.handlers.delete(type)
  }

  emit<T = unknown>(type: string, payload: T) {
    const set = this.handlers.get(type)
    if (!set || set.size === 0) return
    for (const h of Array.from(set)) {
      try {
        ;(h as Handler<T>)(payload)
      } catch (e) {
        console.error('[eventBus] handler error', e)
      }
    }
  }
}

export const eventBus = new EventBus()
export type EventEnvelope = {
  type: string
  kind?: string
  payload?: unknown
  topo_version?: number
  correlation_id?: string
  ts?: string
}
