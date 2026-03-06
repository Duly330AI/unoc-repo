<template>
  <!-- Router cockpit: Digital Display style at ~2.0x scale (slightly smaller than Backbone at 2.5x) -->
  <g class="router-cockpit" transform="scale(2)">
    <!-- Outer glow and main frame now styled via parent g.device-node[data-status] CSS -->
    <rect
x="-100" y="-37" rx="10" ry="10" width="200" height="74" fill="none" class="frame-outline" stroke-width="6"
      opacity="0.15" />
    <rect x="-100" y="-37" rx="10" ry="10" width="200" height="74" :fill="bgDark" class="frame" stroke-width="2" />

    <!-- Header: device id left, LEDs right -->
    <text
x="-94" y="-20" text-anchor="start" :fill="headerColor" font-size="10px"
      font-family="var(--font-mono, monospace)">
      {{ deviceId }}
    </text>
    <g transform="translate(70, -26)">
      <circle r="4" cx="-10" cy="0" :fill="ledColor('UP')" :opacity="ledOpacity('UP')" />
      <circle r="4" cx="0" cy="0" :fill="ledColor('DEGRADED')" :opacity="ledOpacity('DEGRADED')" />
      <circle r="4" cx="8" cy="0" :fill="ledColor('DOWN')" :opacity="ledOpacity('DOWN')" />
    </g>

    <!-- Digital-display rows -->
    <g>
      <!-- Row 1: STATUS -->
      <text
:x="-94" :y="-10" text-anchor="start" :fill="labelColor" font-size="10px"
        font-family="var(--font-mono, monospace)">STATUS:</text>
      <text
:x="94" :y="-10" text-anchor="end" :fill="statusColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ status }}</text>

      <!-- Row 2: UPSTREAM -->
      <text
:x="-94" :y="4" text-anchor="start" :fill="labelColor" font-size="10px"
        font-family="var(--font-mono, monospace)">UPSTREAM:</text>
      <text
:x="94" :y="4" text-anchor="end" :fill="upColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ upstreamText }}</text>

      <!-- Row 3: DOWNSTREAM -->
      <text
:x="-94" :y="18" text-anchor="start" :fill="labelColor" font-size="10px"
        font-family="var(--font-mono, monospace)">DOWNSTREAM:</text>
      <text
:x="94" :y="18" text-anchor="end" :fill="downColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ downstreamText }}</text>

      <!-- Row 4: TotCap (current up+down / effective max) -->
      <text
:x="-94" :y="32" text-anchor="start" :fill="labelColor" font-size="10px"
        font-family="var(--font-mono, monospace)">TotCap (Gbps):</text>
      <text
:x="94" :y="32" text-anchor="end" :fill="capColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ capacityCombinedText }}</text>
    </g>
  </g>

</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDevicesStore, type DeviceOutX } from '../../stores/devicesStore.js'
import { useMetricsStore } from '../../stores/metricsStore.js'
import { formatBps } from '../../composables/useLinkMetricsView.js'

const props = defineProps<{ deviceId: string }>()
const devices = useDevicesStore()
const metrics = useMetricsStore()

const device = computed(() => devices.byId(props.deviceId))
const status = computed(() => device.value?.status ?? 'UNKNOWN')

// Colors and frame consistent with Backbone cockpit
const headerColor = '#cfd8dc'
const labelColor = '#eceff1'
const bgDark = '#111827'
function ledColor(key: 'UP' | 'DEGRADED' | 'DOWN') {
  if (key === 'UP') return '#66bb6a'
  if (key === 'DEGRADED') return '#ef6c00'
  if (key === 'DOWN') return '#ef5350'
  return '#90caf9'
}
function ledOpacity(key: 'UP' | 'DEGRADED' | 'DOWN') {
  return status.value === key ? 1.0 : 0.25
}
const statusColor = computed(() => {
  if (status.value === 'UP') return '#66bb6a'
  if (status.value === 'DEGRADED') return '#ffd54f'
  if (status.value === 'DOWN') return '#ef5350'
  return '#b0bec5'
})
const upColor = '#64b5f6'
const downColor = '#ffa726'
const capColor = '#b0bec5'

// Metrics
const metric = computed(() => metrics.byId[props.deviceId])
const upstreamText = computed(() => {
  const m = metric.value
  if (!m) return '—'
  const v = typeof m.upstream_bps === 'number' ? m.upstream_bps : m.bps / 2
  return formatBps(v)
})
const downstreamText = computed(() => {
  const m = metric.value
  if (!m) return '—'
  const v = typeof m.downstream_bps === 'number' ? m.downstream_bps : m.bps / 2
  return formatBps(v)
})
const capacityCombinedText = computed(() => {
  const dev = device.value as DeviceOutX | undefined
  const params = (dev?.parameters || {}) as { effective_capacity_mbps?: number }
  const capMbps = typeof params.effective_capacity_mbps === 'number' ? params.effective_capacity_mbps : null
  const m = metric.value
  // current throughput = upstream + downstream (fallback to bps split if only total is present)
  const up = m ? (typeof m.upstream_bps === 'number' ? m.upstream_bps : (typeof m.bps === 'number' ? m.bps / 2 : 0)) : 0
  const down = m ? (typeof m.downstream_bps === 'number' ? m.downstream_bps : (typeof m.bps === 'number' ? m.bps / 2 : 0)) : 0
  const currentBps = up + down
  // Show current as rounded integer Gbps (no decimals) as requested.
  const currentGbps = currentBps / 1_000_000_000
  const currentTxt = `${Math.round(currentGbps)} Gbps`
  if (capMbps == null) return `${currentTxt} / —`
  // Round max capacity to integer Gbps to avoid long decimals like "800.00 Gbps".
  // If capacity is < 1 Gbps (unlikely for routers), fall back to integer Mbps.
  let maxTxt: string
  if (capMbps >= 1000) {
    const gbps = capMbps / 1000
    maxTxt = `${Math.round(gbps)} Gbps`
  } else {
    maxTxt = `${Math.round(capMbps)} Mbps`
  }
  return `${currentTxt} / ${maxTxt}`
})
</script>

<style scoped>
.router-cockpit {
  pointer-events: all;
}
</style>
