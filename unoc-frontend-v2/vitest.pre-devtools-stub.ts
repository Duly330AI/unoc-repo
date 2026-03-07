// Ensure Vue devtools hook exists before any library evaluation
// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface DevtoolsHook { on: (...args: any[]) => void; off: (...args: any[]) => void; emit: (...args: any[]) => void; once: (...args: any[]) => void }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const hook: DevtoolsHook = { on: () => { }, off: () => { }, emit: () => { }, once: () => { } }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ; (globalThis as any).__VUE_DEVTOOLS_GLOBAL_HOOK__ = hook
if (typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ; (window as any).__VUE_DEVTOOLS_GLOBAL_HOOK__ = hook
}
