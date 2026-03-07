import { defineStore } from 'pinia'

export const useSpinnerStore = defineStore('spinner', {
  state: () => ({ visible: false, message: '' as string | null }),
  actions: {
    show(msg?: string) {
      this.visible = true
      this.message = msg ?? null
    },
    hide() {
      this.visible = false
      this.message = null
    }
  }
})
