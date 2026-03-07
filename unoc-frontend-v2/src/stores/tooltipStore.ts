import { defineStore } from 'pinia'

export interface TooltipState {
  isVisible: boolean
  content: string | null
  x: number
  y: number
}

let showTimer: number | null = null
let hideTimer: number | null = null

export const useTooltipStore = defineStore('tooltip', {
  state: (): TooltipState => ({
    isVisible: false,
    content: null,
    x: 0,
    y: 0
  }),
  actions: {
    show(content: string, x: number, y: number) {
      // cancel pending hide
      if (hideTimer) {
        window.clearTimeout(hideTimer)
        hideTimer = null
      }
      if (showTimer) window.clearTimeout(showTimer)
      // Defensive: do not show empty content
      if (!content || content.trim() === '') {
        this.isVisible = false
        this.content = null
        this.x = 0
        this.y = 0
        return
      }
      showTimer = window.setTimeout(() => {
        this.content = content
        this.x = x
        this.y = y
        this.isVisible = true
        showTimer = null
      }, 80) // enter delay ~80ms
    },
    move(x: number, y: number) {
      if (!this.isVisible) return
      this.x = x
      this.y = y
    },
    hide() {
      if (showTimer) {
        window.clearTimeout(showTimer)
        showTimer = null
      }
      if (hideTimer) window.clearTimeout(hideTimer)
      hideTimer = window.setTimeout(() => {
        this.isVisible = false
        this.content = null
        hideTimer = null
      }, 120) // leave delay ~120ms
    },
    reset() {
      // Cancel any pending timers and fully reset state
      if (showTimer) {
        window.clearTimeout(showTimer)
        showTimer = null
      }
      if (hideTimer) {
        window.clearTimeout(hideTimer)
        hideTimer = null
      }
      this.isVisible = false
      this.content = null
      this.x = 0
      this.y = 0
    }
  }
})
