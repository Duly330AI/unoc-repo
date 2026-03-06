import { defineStore } from 'pinia'
import { createToastManager } from '../logic/toastManager.js'
// Re-export Toast type for convenient importing from components
export type { Toast } from '../logic/toastManager.js'

const manager = createToastManager()
manager.startAutoGc?.(400)

export const useToastStore = defineStore('toasts', {
  state: () => ({
    get toasts() {
      return manager.state.toasts
    }
  }),
  actions: {
    push: manager.push,
    pending: manager.pending,
    succeed: manager.succeed,
    fail: manager.fail,
    replace: manager.replace,
    remove: manager.remove,
    clear: manager.clear,
    startAutoGc: manager.startAutoGc,
    stopAutoGc: manager.stopAutoGc
  }
})
