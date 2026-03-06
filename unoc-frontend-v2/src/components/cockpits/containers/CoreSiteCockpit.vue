<template>
  <g class="container-cockpit" :data-id="deviceId">
    <rect :x="-w / 2" :y="-h / 2" :width="w" :height="h" rx="12" ry="12" class="frame" />
    <text class="title" :x="-w / 2 + 18" :y="-h / 2 + 28">CORE SITE</text>
    <text class="slots" :x="w / 2 - 18" :y="-h / 2 + 28" text-anchor="end">Slots: {{ usedSlots }} / {{ totalSlots }}</text>
    <text class="metric" :x="-w / 2 + 18" :y="-h / 2 + 50">Total Traffic: {{ totalTrafficText }}</text>
    <g class="health" :transform="`translate(${w / 2 - 22}, ${-h / 2 + 46})`">
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
const layout = getContainerLayout('CORE_SITE')!
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
  fill: #0c1014;
  stroke: #4b5563;
  stroke-width: 2.5;
}

.title {
  font: 800 16px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #dbe3ea;
  letter-spacing: 1px;
}

.slots {
  font: 600 12px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #9aa9b2;
}

.metric {
  font: 600 12px/1.2 Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial;
  fill: #b9c6cf;
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
  fill: #dbe3ea;
}
</style>
