/* eslint-disable @typescript-eslint/no-explicit-any */
import { watch } from 'vue'
import { useMetricsStore } from '../../stores/metricsStore.js'
import { useLinkMetricsStore } from '../../stores/linkMetricsStore.js'

export function attachCanvasWatchers(
  devices: any,
  linksStore: any,
  selection: any,
  redraw: () => void,
  redrawSelection: () => void
) {
  const metrics = useMetricsStore()
  const linkMetrics = useLinkMetricsStore()
  watch(
    () => metrics.lastTick,
    () => redraw()
  )
  watch(
    () => Object.keys(metrics.byId).join(','),
    () => redraw()
  )
  watch(
    () => linkMetrics.lastTick,
    () => redraw()
  )
  watch(
    () => Object.keys(linkMetrics.byId).join(','),
    () => redraw()
  )
  watch(
    () => devices.devices.length,
    () => redraw()
  )
  watch(
    () =>
      devices.devices
        .map((d: any) => `${d.id}:${d.status || ''}:${d.signal_status || ''}`)
        .join(','),
    () => redraw()
  )
  watch(
    () => linksStore.links.length,
    () => redraw()
  )
  watch(
    () => linksStore.links.map((l: any) => l.id).join(','),
    () => redraw()
  )
  // IMPORTANT: Previously, link override/effective status changes performed an in-place splice
  // replacement of a single element (immutably) which does NOT change the array length nor the
  // ordered list of ids. As a result, no watcher above fired and topology colors / animations
  // stayed stale until another global trigger (metrics tick, device status change, manual refresh)
  // invoked a redraw. We concatenate the small set of reactive fields that influence visual
  // styling (status, effective_status, admin_override_status) so that any change schedules a
  // redraw deterministically.
  watch(
    () =>
      linksStore.links
        .map(
          (l: any) =>
            `${l.id}:${l.status || ''}:${l.effective_status || ''}:${l.admin_override_status || ''}`
        )
        .join(','),
    () => redraw()
  )
  watch(
    () => selection.lastUpdated,
    () => redrawSelection()
  )
  watch(
    () =>
      devices.devices
        .map(
          (d: any) =>
            `${d.id}:${d.status || ''}:${d.effective_status || ''}:${d.admin_override_status || ''}:${d.signal_status || ''}`
        )
        .join(','),
    () => redraw()
  )
}
