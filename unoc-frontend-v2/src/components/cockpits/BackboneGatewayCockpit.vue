<template>
  <!-- 2.5x scale for dominance on canvas -->
  <g class="bbgw-cockpit" transform="scale(2.5)">
    <!-- Frame (keeps status-aware colored stroke), sized based on base cockpit geometry -->
    <!-- subtle outer glow stroke for prominence -->
    <rect
x="-70" y="-36" rx="10" ry="10" width="140" height="72" fill="none" class="frame-outline" stroke-width="6"
      opacity="0.15" />
    <rect x="-70" y="-36" rx="10" ry="10" width="140" height="72" fill="#111827" class="frame" stroke-width="2" />

    <!-- Header: left id, right LEDs -->
    <text x="-64" y="-22" text-anchor="start" fill="#eceff1" font-size="10px" font-family="var(--font-mono, monospace)">
      {{ deviceId }}
    </text>
    <g transform="translate(48, -28)">
      <circle r="4" cx="-10" cy="0" :fill="ledColor('UP')" :opacity="ledOpacity('UP')" />
      <circle r="4" cx="0" cy="0" :fill="ledColor('DEGRADED')" :opacity="ledOpacity('DEGRADED')" />
      <circle r="4" cx="8" cy="0" :fill="ledColor('DOWN')" :opacity="ledOpacity('DOWN')" />
    </g>

    <!-- Digital-display rows: label left, value right -->
    <g>
      <!-- Row 1: STATUS -->
      <text
:x="-64" :y="-12" text-anchor="start" fill="#b0bec5" font-size="10px"
        font-family="var(--font-mono, monospace)">STATUS:</text>
      <text
:x="64" :y="-12" text-anchor="end" :fill="statusColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ status }}</text>

      <!-- Row 2: UPSTREAM -->
      <text
:x="-64" :y="2" text-anchor="start" fill="#b0bec5" font-size="10px"
        font-family="var(--font-mono, monospace)">UPSTREAM:</text>
      <text
:x="64" :y="2" text-anchor="end" :fill="upColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ upText }}</text>

      <!-- Row 3: DOWNSTREAM -->
      <text
:x="-64" :y="16" text-anchor="start" fill="#b0bec5" font-size="10px"
        font-family="var(--font-mono, monospace)">DOWNSTREAM:</text>
      <text
:x="64" :y="16" text-anchor="end" :fill="downColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ downText }}</text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDevicesStore } from '../../stores/devicesStore.js'
import { useMetricsStore } from '../../stores/metricsStore.js'
import { formatBps } from '../../composables/useLinkMetricsView.js'

const props = defineProps<{ deviceId: string }>()
const devices = useDevicesStore()
const metrics = useMetricsStore()

interface DeviceLike { status?: string }
interface MetricLike { upstream_bps?: number; downstream_bps?: number; bps: number }

const device = computed<DeviceLike | undefined>(() => devices.byId(props.deviceId) as DeviceLike)
const status = computed<string>(() => device.value?.status ?? 'UNKNOWN')
const metric = computed<MetricLike | undefined>(() => metrics.byId[props.deviceId] as MetricLike | undefined)

const upText = computed(() => {
  const m = metric.value
  if (!m) return '—'
  const v = typeof m.upstream_bps === 'number' ? m.upstream_bps : m.bps / 2
  return formatBps(v)
})
const downText = computed(() => {
  const m = metric.value
  if (!m) return '—'
  const v = typeof m.downstream_bps === 'number' ? m.downstream_bps : m.bps / 2
  return formatBps(v)
})

// LED helpers
function ledColor(key: 'UP' | 'DEGRADED' | 'DOWN') {
  if (key === 'UP') return '#66bb6a'
  if (key === 'DEGRADED') return '#ef6c00'
  if (key === 'DOWN') return '#ef5350'
  return '#90caf9'
}
function ledOpacity(key: 'UP' | 'DEGRADED' | 'DOWN') {
  return status.value === key ? 1.0 : 0.25
}

// Frame color mirrors BaseCockpit logic for consistency
const statusColor = computed(() => {
  if (status.value === 'UP') return '#66bb6a'
  if (status.value === 'DEGRADED') return '#ffd54f'
  if (status.value === 'DOWN') return '#ef5350'
  return '#b0bec5'
})
const upColor = '#64b5f6'
const downColor = '#64b5f6'
</script>

<style scoped>
.bbgw-cockpit {
  pointer-events: all;
}

.frame-outline {
  stroke-width: 6;
  opacity: 0.15;
}

.frame {
  fill: #111827;
  stroke-width: 2;
}
</style>
