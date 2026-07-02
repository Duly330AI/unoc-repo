<template>
  <!-- OLT cockpit: Digital Display with PON Port Matrix -->
  <g class="olt-cockpit">
    <g transform="scale(2)">
      <!-- Frame (status-aware via CSS) -->
      <rect
x="-84" y="-34" rx="10" ry="10" width="168" height="68" fill="none" class="frame-outline" stroke-width="6"
        opacity="0.15" />
      <rect x="-84" y="-34" rx="10" ry="10" width="168" height="68" :fill="bgDark" class="frame" stroke-width="2" />

      <!-- Header: id + LEDs -->
      <text
x="-72" y="-20" text-anchor="start" :fill="headerColor" font-size="10px"
        font-family="var(--font-mono, monospace)">{{ deviceId }}</text>
      <g transform="translate(62, -26)">
        <circle r="4" cx="-10" cy="0" :fill="ledColor('UP') " :opacity="ledOpacity('UP')" />
        <circle r="4" cx="0" cy="0" :fill="ledColor('DEGRADED')" :opacity="ledOpacity('DEGRADED')" />
        <circle r="4" cx="8" cy="0" :fill="ledColor('DOWN')" :opacity="ledOpacity('DOWN')" />
      </g>

      <!-- Digital rows: STATUS, TOTAL TRAFFIC, SUBSCRIBERS -->
      <g>
        <text
x="-72" y="-10" text-anchor="start" :fill="labelColor" font-size="10px"
          font-family="var(--font-mono, monospace)">STATUS:</text>
        <text
x="80" y="-10" text-anchor="end" :fill="statusColor" font-size="10px"
          font-family="var(--font-mono, monospace)">{{ status }}</text>

        <text
x="-72" y="4" text-anchor="start" :fill="labelColor" font-size="10px"
          font-family="var(--font-mono, monospace)">TOTAL TRAFFIC:</text>
        <text
x="80" y="4" text-anchor="end" :fill="trafficColor" font-size="10px"
          font-family="var(--font-mono, monospace)">{{ totalTrafficText }}</text>

        <text
x="-72" y="18" text-anchor="start" :fill="labelColor" font-size="10px"
          font-family="var(--font-mono, monospace)">SUBSCRIBERS:</text>
        <text
x="80" y="18" text-anchor="end" :fill="subsColor" font-size="10px"
          font-family="var(--font-mono, monospace)">{{ subscribersText }}</text>
      </g>
    </g>

    <!-- Port Matrix: rendered below the digital display frame -->
    <g :transform="`translate(${-matrixWidth / 2}, 46)`">
      <template v-for="(cell, idx) in visibleCells" :key="cell.id">
        <rect
class="pon-cell" :x="cellX(idx)" :y="cellY(idx)" :width="CELL" :height="CELL" rx="1" ry="1"
          :fill="fillFor(cell.state)" stroke="#263238" stroke-width="0.5" :data-state="cell.state"
          :data-onts="String(cell.ontCount)" />
      </template>
      <!-- Pagination controls for large OLTs -->
      <template v-if="totalPages > 1">
        <g :transform="`translate(${matrixWidth / 2}, ${rows * (CELL + GAP) + 10})`">
          <text
class="pager" text-anchor="end" x="-4" y="0" :opacity="page > 0 ? 1 : 0.35" fill="#90caf9"
            font-size="7px" font-family="var(--font-mono, monospace)" @click="prevPage">
            ◀ Prev
          </text>
          <text
class="pager" text-anchor="middle" x="0" y="0" fill="#b0bec5" font-size="7px"
            font-family="var(--font-mono, monospace)">
            {{ page + 1 }} / {{ totalPages }}
          </text>
          <text
class="pager" text-anchor="start" x="4" y="0" :opacity="page < totalPages - 1 ? 1 : 0.35" fill="#90caf9"
            font-size="7px" font-family="var(--font-mono, monospace)" @click="nextPage">
            Next ▶
          </text>
        </g>
      </template>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed, ref, watch, toRef } from 'vue'
import { useDevicesStore, type DeviceOutX } from '../../stores/devicesStore.js'
import { useMetricsStore } from '../../stores/metricsStore.js'
import { formatBps } from '../../composables/useLinkMetricsView.js'
import { usePortSummaryManaged } from '../../composables/usePortSummaryManager'

const props = defineProps<{ deviceId: string }>()
const devices = useDevicesStore()
const metrics = useMetricsStore()

const device = computed<DeviceOutX | undefined>(() => devices.byId(props.deviceId) as DeviceOutX)
const status = computed(() => device.value?.status ?? 'UNKNOWN')

// Styling/colors
const headerColor = '#cfd8dc'
const labelColor = '#eceff1'
const bgDark = '#111827'
const subsColor = '#e91e63'
const trafficColor = '#64b5f6'
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

// Metrics: prefer combined upstream+downstream, fallback to total bps
const metric = computed(() => metrics.byId[props.deviceId])
const totalTrafficText = computed(() => {
  const m = metric.value
  if (!m) return '—'
  const up = typeof m.upstream_bps === 'number' ? m.upstream_bps : m.bps / 2
  const down = typeof m.downstream_bps === 'number' ? m.downstream_bps : m.bps / 2
  return formatBps(up + down)
})

// New: consume backend per-port summary
const { interfaces: portIfaces } = usePortSummaryManaged(toRef(props, 'deviceId'))

type PortState = 'unused' | 'UP' | 'DEGRADED' | 'DOWN'
type PonCell = { id: string; name: string; state: PortState; ontCount: number }

const ponCells = computed<PonCell[]>(() => {
  const list = portIfaces.value.filter((i) => String(i.port_role || '').toUpperCase() === 'PON')
  console.log('[OLTCockpit] portIfaces:', portIfaces.value.length, '| PON ports:', list.length)
  return list.map((i, idx) => {
    const occ = Number(i.occupancy ?? 0)
    const eff = String(i.effective_status || '')
    const state: PortState = occ === 0 ? 'unused' : (eff === 'UP' || eff === 'DEGRADED' || eff === 'DOWN' ? (eff as PortState) : 'UP')
    if (idx === 0) console.log('[OLTCockpit] First PON:', i.name, 'occupancy:', occ)
    return { id: i.id || i.name || `pon-${idx}`, name: i.name || `pon-${idx + 1}`, state, ontCount: occ }
  })
})

const subscriberCount = computed(() => {
  const value = device.value?.subscribers
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const params = device.value?.parameters as { subscribers?: { total?: number } } | undefined
  const total = params?.subscribers?.total
  return typeof total === 'number' && Number.isFinite(total) ? total : null
})

const subscribersText = computed(() => {
  const totalONTs = subscriberCount.value
  console.log('[OLTCockpit] subscribersText:', totalONTs, '| ponCells:', ponCells.value.length)
  return totalONTs == null ? '—' : String(totalONTs)
})

// Grid layout
const COLS = 8
const CELL = 6
const GAP = 2
const PAGE_SIZE = 32
const page = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(ponCells.value.length / PAGE_SIZE)))
watch(ponCells, () => { if (page.value >= totalPages.value) page.value = totalPages.value - 1 })
const visibleCells = computed(() => {
  const start = page.value * PAGE_SIZE
  const end = start + PAGE_SIZE
  return ponCells.value.slice(start, end)
})
const rows = computed(() => Math.ceil(visibleCells.value.length / COLS))
const matrixWidth = computed(() => COLS * CELL + (COLS - 1) * GAP)

function cellX(idx: number) {
  const col = idx % COLS
  return col * (CELL + GAP)
}
function cellY(idx: number) {
  const row = Math.floor(idx / COLS)
  return row * (CELL + GAP)
}
function fillFor(state: PortState): string {
  if (state === 'UP') return '#26a69a'
  if (state === 'DEGRADED') return '#ef6c00'
  if (state === 'DOWN') return '#ef5350'
  return '#374151'
}

// expose constants for tests/debug
// eslint-disable-next-line @typescript-eslint/no-explicit-any
; (globalThis as any).__OLT__ = { CELL, GAP }

function prevPage() {
  if (page.value > 0) page.value -= 1
}
function nextPage() {
  if (page.value < totalPages.value - 1) page.value += 1
}
</script>

<style scoped>
.olt-cockpit {
  pointer-events: all;
}

.pon-cell {
  opacity: 0.95
}

.overflow-indicator {
  opacity: 0.9
}

.pager {
  cursor: pointer;
}
</style>
