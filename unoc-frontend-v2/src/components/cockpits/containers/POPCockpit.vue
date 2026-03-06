<template>
  <g class="container-cockpit" :data-id="deviceId">
    <rect :x="-w / 2" :y="-h / 2" :width="w" :height="h" rx="10" ry="10" class="frame" />
    <text class="title" :x="-w / 2 + 16" :y="-h / 2 + 26">POP</text>
    <text class="slots" :x="w / 2 - 16" :y="-h / 2 + 26" text-anchor="end">Slots: {{ usedSlots }} / {{ totalSlots }}</text>
    <text class="metric" :x="-w / 2 + 16" :y="-h / 2 + 48">Total Traffic: {{ totalTrafficText }}</text>
    <g class="health" :transform="`translate(${w / 2 - 20}, ${-h / 2 + 44})`">
      <circle :r="8" :class="['dot', healthClass]" />
      <text class="badge" x="12" y="4">{{ healthText }}</text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getContainerLayout } from '../../../config/containerLayouts.js'
import { useDevicesStore } from '../../../stores/devicesStore.js'
import { useMetricsStore } from '../../../stores/metricsStore.js'
import { formatBps } from '../../../composables/useLinkMetricsView.js'

const props = defineProps<{ deviceId: string }>()
const layout = getContainerLayout('POP')!
const w = layout.size.width
const h = layout.size.height

const devices = useDevicesStore()
const metrics = useMetricsStore()
const children = computed(() => devices.devices.filter((d) => d.parent_container_id === props.deviceId))
const usedSlots = computed(() => children.value.length)
const totalSlots = layout.slots.length

const totalTraffic = computed(() => {
  let sum = 0
  for (const d of children.value) {
    const m = metrics.byId[d.id]
    if (!m) continue
    sum += typeof m.bps === 'number' ? m.bps : 0
  }
  return sum
})
const totalTrafficText = computed(() => formatBps(totalTraffic.value))

const healthLevel = computed<'UP' | 'DEGRADED' | 'DOWN'>(() => {
  let hasDegraded = false
  for (const d of children.value) {
    const st = d.status || 'UP'
    if (st === 'DOWN') return 'DOWN'
    if (st === 'DEGRADED') hasDegraded = true
  }
  return hasDegraded ? 'DEGRADED' : 'UP'
})
const healthText = computed(() => healthLevel.value)
const healthClass = computed(() => (healthLevel.value === 'DOWN' ? 'down' : healthLevel.value === 'DEGRADED' ? 'degraded' : 'up'))
</script>

<style scoped>
.frame {
  fill: #0e1116;
  stroke: #3e4a56;
  stroke-width: 2;
}

.title {
  font: 700 16px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #cfd8dc;
}

.slots {
  font: 600 12px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #90a4ae;
}

.metric {
  font: 600 12px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #b0bec5;
}

.health .dot.up {
  fill: #2e7d32;
}

.health .dot.degraded {
  fill: #f9a825;
}

.health .dot.down {
  fill: #c62828;
}

.health .badge {
  font: 700 11px/1 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #cfd8dc;
}
</style>
