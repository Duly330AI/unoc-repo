import { defineStore } from 'pinia'
import type { DebugSnapshot } from '../lib/apiDebug.js'
import { fetchFullSnapshot } from '../lib/apiDebug.js'

interface State {
  snapshot: DebugSnapshot | null
  loading: boolean
  error: string | null
}

export const useDebugStore = defineStore('debug', {
  state: (): State => ({ snapshot: null, loading: false, error: null }),
  actions: {
    async refresh() {
      this.loading = true
      this.error = null
      try {
        const snap = await fetchFullSnapshot()
        this.snapshot = snap
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    }
  }
})
