import { defineStore } from 'pinia'

export interface MetricsConfig {
  EPSILON_METRICS_DELTA: number
  UTILIZATION_BUCKETS: number[]
}

export interface AppConfig {
  metrics: MetricsConfig
  flags: Record<string, boolean>
}

interface State {
  config: AppConfig | null
}

export const useConfigStore = defineStore('config', {
  state: (): State => ({ config: null }),
  actions: {
    async load() {
      try {
        const resp = await fetch('/api/config')
        if (resp.ok) {
          const js = (await resp.json()) as AppConfig
          if (js && js.metrics && Array.isArray(js.metrics.UTILIZATION_BUCKETS)) {
            this.config = js
          }
        }
      } catch (e) {
        // Non-fatal; defaults will apply in colorScale
        // eslint-disable-next-line no-console
        console.warn('[configStore] failed to load /api/config', e)
      }
    }
  }
})
