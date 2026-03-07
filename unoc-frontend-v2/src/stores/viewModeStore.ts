import { defineStore } from 'pinia'

export type ViewMode = 'topology' | 'metrics' | 'ipam' | 'tariffs' | 'hardware' | 'debug'

interface State {
  current: ViewMode
}

const STORAGE_KEY = 'unoc:viewMode'
function isDev(): boolean {
  try {
    // gate via global debug flag set in main.ts
    return (globalThis as unknown as { __UNOC_DEBUG__?: boolean }).__UNOC_DEBUG__ === true
  } catch {
    return false
  }
}

function loadInitial(): ViewMode {
  if (typeof window === 'undefined') return 'topology'
  const saved = window.localStorage.getItem(STORAGE_KEY)
  const allowed: ViewMode[] = ['topology', 'metrics', 'ipam', 'tariffs', 'hardware']
  if (isDev()) allowed.push('debug')
  return (allowed as string[]).includes(saved || '') ? (saved as ViewMode) : 'topology'
}

export const useViewModeStore = defineStore('viewMode', {
  state: (): State => ({ current: loadInitial() }),
  actions: {
    set(mode: ViewMode) {
      // prevent switching to debug in non-dev
      if (mode === 'debug' && !isDev()) {
        this.current = 'topology'
        return
      }
      this.current = mode
      try {
        window.localStorage.setItem(STORAGE_KEY, mode)
      } catch {
        /* ignore */
      }
    }
  }
})
