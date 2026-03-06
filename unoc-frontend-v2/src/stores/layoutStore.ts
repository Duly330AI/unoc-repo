import { defineStore } from 'pinia'
import { reactive } from 'vue'

export interface LayoutPosition {
  id: string
  x: number
  y: number
  userPinned?: boolean | null
  systemPinned?: boolean | null
}

interface State {
  byId: Record<string, LayoutPosition>
  dirty: Set<string>
  loading: boolean
  error: string | null
  _timer: number | null
  _throttleMs: number
}

export const useLayoutStore = defineStore('layout', {
  state: (): State => ({
    byId: reactive({} as Record<string, LayoutPosition>),
    dirty: new Set<string>(),
    loading: false,
    error: null,
    _timer: null,
    _throttleMs: 2000
  }),
  getters: {
    get: (state) => (id: string) => state.byId[id]
  },
  actions: {
    async hydrate() {
      this.loading = true
      this.error = null
      try {
        const resp = await fetch('/api/layout/positions')
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const body = (await resp.json()) as { version: number; positions: LayoutPosition[] }
        for (const p of body.positions || []) {
          this.byId[p.id] = { ...p }
        }
      } catch (e) {
        this.error = (e as Error).message
      } finally {
        this.loading = false
      }
    },
    markMoved(id: string, x: number, y: number, userPinned: boolean | null = true) {
      const cur = this.byId[id]
      if (!cur) this.byId[id] = { id, x, y, userPinned: userPinned ?? undefined }
      else {
        cur.x = x
        cur.y = y
        if (userPinned != null) cur.userPinned = userPinned
      }
      this.dirty.add(id)
      this._schedule()
    },
    setPinned(id: string, pinned: boolean) {
      const cur = this.byId[id]
      if (!cur) return
      cur.userPinned = pinned
      this.dirty.add(id)
      this._schedule()
    },
    _schedule() {
      if (this._timer != null) return
      this._timer = window.setTimeout(() => {
        this._timer = null
        this.flushNow().catch(() => {
          /* error stored in action */
        })
      }, this._throttleMs)
    },
    async flushNow() {
      if (this.dirty.size === 0) return { applied: 0 }
      const ids = Array.from(this.dirty)
      // Clear early so state reflects intent immediately; re-add on failure.
      this.dirty.clear()
      const payload = {
        positions: ids.map((id) => {
          const p = this.byId[id]
          return { id: p.id, x: p.x, y: p.y, userPinned: p.userPinned ?? undefined }
        })
      }
      try {
        const resp = await fetch('/api/layout/positions', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        const j = await resp.json()
        return j
      } catch (e) {
        // Restore dirty ids so they can be retried later
        ids.forEach((id) => this.dirty.add(id))
        this.error = (e as Error).message
        throw e
      }
    }
  }
})
