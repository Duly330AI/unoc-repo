import { createApp } from 'vue'
import { getActivePinia } from 'pinia'
// Use shared Pinia singleton across root app and cockpit sub-apps
import { pinia } from './stores/pinia.js'
import App from './root/App.vue'
import './styles/theme.css'
import './styles/topology-status.css'
import { wsClient } from './lib/wsClient.js'
import { useDevicesStore } from './stores/devicesStore.js'
import { useLinksStore } from './stores/linksStore.js'
import { useMetricsStore } from './stores/metricsStore.js'
import { useLinkMetricsStore } from './stores/linkMetricsStore.js'
import { useConfigStore } from './stores/configStore.js'
import { useLayoutStore } from './stores/layoutStore.js'

const app = createApp(App)
app.use(pinia)
app.mount('#app')
;(async () => {
  // Dev-only: verify shared Pinia instance is active
  if (import.meta.env.DEV) {
    const active = getActivePinia()
    // eslint-disable-next-line no-console
    console.debug('[main] pinia singleton attached?', active === pinia)
    // Turn on optional debug logs in cockpits without relying on import.meta in SFCs
    interface DebugGlobal {
      __UNOC_DEBUG__?: boolean
    }
    ;(globalThis as unknown as DebugGlobal).__UNOC_DEBUG__ = true
  }
  // Load runtime config, then start realtime & stores
  const configStore = useConfigStore()
  await configStore.load()
  // Expose minimal readonly snapshot for modules needing buckets without importing Pinia
  ;(
    globalThis as unknown as {
      __unocConfigStore__?: { metrics?: { UTILIZATION_BUCKETS?: number[] } }
    }
  ).__unocConfigStore__ = {
    metrics: { UTILIZATION_BUCKETS: configStore.config?.metrics?.UTILIZATION_BUCKETS }
  }

  // Start WebSocket client after app mounts
  wsClient.start()

  // Subscribe stores to WS event bus
  const devicesStore = useDevicesStore()
  devicesStore.initRealtime()
  const linksStore = useLinksStore()
  linksStore.initRealtime()
  const linkMetricsStore = useLinkMetricsStore()
  linkMetricsStore.initRealtime()
  // Device metrics realtime (was missing)
  const metricsStore = useMetricsStore()
  metricsStore.initRealtime()

  // Hydrate saved layout positions
  const layoutStore = useLayoutStore()
  try {
    await layoutStore.hydrate()
  } catch {
    // non-fatal
  }

  // Fetch initial metrics snapshot on app load
  // Reuse same metricsStore for snapshot
  try {
    const resp = await fetch('/api/metrics/snapshot')
    if (resp.ok) {
      const js = await resp.json()
      // Expect shape: { lastTick, devices, links }
      if (js && typeof js === 'object' && js.devices && typeof js.lastTick === 'number') {
        metricsStore.applySnapshot(js)
        // Also apply link metrics snapshot if present
        if (js.links) {
          linkMetricsStore.applySnapshot(js)
        }
      }
    }
  } catch (e) {
    // Non-fatal on startup; realtime deltas will still populate
    // eslint-disable-next-line no-console
    console.warn('[main] metrics snapshot load failed', e)
  }
})()
