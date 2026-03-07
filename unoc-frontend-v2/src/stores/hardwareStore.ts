import { defineStore } from 'pinia'

export type HardwareModel = {
  id: number
  catalog_id: string
  device_type: string
  vendor?: string | null
  model?: string | null
  version?: string | null
  capacity_gbps?: number | null
  ports_total?: number | null
}

interface State {
  items: HardwareModel[]
  loading: boolean
  error: string | null
}

export const useHardwareStore = defineStore('hardware', {
  state: (): State => ({ items: [], loading: false, error: null }),
  actions: {
    async init() {
      // Avoid refetching if already loaded or currently loading
      if (this.items.length > 0 || this.loading) return
      await this.fetchAll()
    },
    async fetchAll(type?: string) {
      if (this.loading) return
      this.loading = true
      this.error = null
      try {
        const url = type
          ? `/api/catalog/hardware?type=${encodeURIComponent(type)}`
          : '/api/catalog/hardware'
        const r = await fetch(url)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        this.items = (await r.json()) as HardwareModel[]
      } catch (e) {
        const err = e as Error
        this.error = err.message || String(e)
      } finally {
        this.loading = false
      }
    }
  }
})
