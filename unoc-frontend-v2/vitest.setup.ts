// Global test setup for Pinia/Vue related unit tests
// Early devtools hook stub (guards against libraries expecting it)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
if (!(globalThis as any).__VUE_DEVTOOLS_GLOBAL_HOOK__) {
  const hook = { on() {}, off() {}, emit() {}, once() {} }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(globalThis as any).__VUE_DEVTOOLS_GLOBAL_HOOK__ = hook
  if (typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(window as any).__VUE_DEVTOOLS_GLOBAL_HOOK__ = hook
  }
}

// For current tests we exercise only pure logic managers, stores are thin wrappers so no Pinia mocking needed.

// Explicitly import vitest to ensure ESM resolution and globals registration
import 'vitest'
