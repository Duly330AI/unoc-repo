export type ToastVariant = 'info' | 'success' | 'error' | 'warn' | 'pending'

export interface ToastAction {
  label: string
  run: () => void
}
export interface Toast {
  id: string
  message: string
  variant: ToastVariant
  createdAt: number
  ttl: number
  dismissible: boolean
  action?: ToastAction
}

export interface ToastManagerState {
  toasts: Toast[]
}

export function createToastManager(now: () => number = () => Date.now()) {
  const state: ToastManagerState = { toasts: [] }
  function makeId() {
    return Math.random().toString(36).slice(2, 10)
  }
  function push(
    message: string,
    variant: ToastVariant = 'info',
    opts?: { ttl?: number; dismissible?: boolean; action?: ToastAction }
  ): string {
    const id = makeId()
    const ttl = opts?.ttl ?? 4200
    const dismissible = opts?.dismissible ?? true
    state.toasts.push({
      id,
      message,
      variant,
      createdAt: now(),
      ttl,
      dismissible,
      action: opts?.action
    })
    return id
  }
  function pending(msg: string) {
    return push(msg, 'pending', { ttl: 10000 })
  }
  function replace(
    id: string,
    message: string,
    variant: ToastVariant,
    opts?: { action?: ToastAction }
  ) {
    const t = state.toasts.find((t) => t.id === id)
    if (t) {
      t.message = message
      t.variant = variant
      t.createdAt = now()
      t.ttl = 4200
      t.action = opts?.action
    }
  }
  function succeed(id: string, message: string) {
    replace(id, message, 'success')
  }
  function fail(id: string, message: string) {
    replace(id, message, 'error')
  }
  function remove(id: string) {
    state.toasts = state.toasts.filter((t) => t.id !== id)
  }
  function clear() {
    state.toasts = []
  }
  // Auto-GC for expired toasts (based on ttl). Returns a function to stop the interval.
  let gcTimer: number | undefined
  function startAutoGc(intervalMs = 400) {
    if (gcTimer !== undefined) return () => stopAutoGc()
    // Using setInterval returns NodeJS.Timer in Node and number in browsers; cast to number for browser builds
    gcTimer = setInterval(() => {
      const nowTs = now()
      // Keep toasts that are not expired or not dismissible? Expiration applies to all with ttl
      state.toasts = state.toasts.filter((t) => nowTs - t.createdAt < t.ttl)
    }, intervalMs) as unknown as number
    return () => stopAutoGc()
  }
  function stopAutoGc() {
    if (gcTimer !== undefined) {
      clearInterval(gcTimer as unknown as number)
      gcTimer = undefined
    }
  }
  return { state, push, pending, succeed, fail, replace, remove, clear, startAutoGc, stopAutoGc }
}
