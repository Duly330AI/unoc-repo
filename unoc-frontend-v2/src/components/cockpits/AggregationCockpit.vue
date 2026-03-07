<template>
    <g class="aggregation-cockpit">
        <BaseCockpit :device-id="deviceId" />
        <!-- Port matrix -->
        <g :transform="`translate(${-matrixWidth / 2}, 10)`">
            <template v-for="(p, idx) in visiblePorts" :key="p.id">
                <rect
                    class="port-cell"
                    :x="cellX(idx)"
                    :y="cellY(idx)"
                    :width="CELL"
                    :height="CELL"
                    rx="1"
                    ry="1"
                    :fill="p.admin_status === 'up' ? '#26a69a' : '#ef5350'"
                    stroke="#263238"
                    stroke-width="0.5"
                    :data-status="p.admin_status"
                    :data-util="utilFor(p)"
                />
                <!-- Utilization overlay bar (future-ready; defaults to 0%) -->
                <rect
                    class="port-util"
                    :x="cellX(idx)"
                    :y="cellY(idx) + CELL - 1"
                    :width="Math.max(0.5, Math.min(CELL, (utilFor(p) / 100) * CELL))"
                    :height="1"
                    :fill="utilColor(utilFor(p))"
                />
            </template>
            <template v-if="overflowCount > 0">
                <text
                    class="overflow-indicator"
                    :x="matrixWidth / 2"
                    :y="rows * (CELL + GAP) + 8"
                    text-anchor="middle"
                    fill="#b0bec5"
                    font-size="7px"
                    font-family="var(--font-mono, monospace)"
                >
                    +{{ overflowCount }} more
                </text>
            </template>
        </g>
    </g>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import BaseCockpit from './BaseCockpit.vue'
import { useDevicesStore, type DeviceOutX } from '../../stores/devicesStore.js'
import type { InterfaceOut } from '../../types/domain.js'
import { colorForUtil } from '../../colorScale.js'
import { useMetricsStore } from '../../stores/metricsStore.js'

const props = defineProps<{ deviceId: string }>()
const devices = useDevicesStore()
const metrics = useMetricsStore()

type PortLite = { id: string; name: string; admin_status: 'up' | 'down' }
const device = computed<DeviceOutX | undefined>(() => devices.byId(props.deviceId) as DeviceOutX)
const ports = computed<PortLite[]>(() => {
    const ifaces = (device.value?.interfaces ?? []) as InterfaceOut[]
    return ifaces.map((i) => ({ id: i.id, name: i.name, admin_status: i.admin_status }))
})

// Per-port utilization map (percent 0..100) from metrics store
const perPortUtilization = computed<Record<string, number>>(() => {
    const map: Record<string, number> = {}
    const devPorts = metrics.portsByDevice[props.deviceId] || {}
    for (const p of ports.value) {
        const m = devPorts[p.id]
        const utilRatio = typeof m?.utilization === 'number' ? m.utilization : 0
        const percent = Math.max(0, Math.min(100, Math.round(utilRatio * 100)))
        map[p.id] = percent
    }
    return map
})

function utilFor(p: PortLite): number {
    const v = perPortUtilization.value[p.id]
    return typeof v === 'number' && isFinite(v) && v >= 0 ? Math.min(100, v) : 0
}
function utilColor(utilPercent: number): string {
    return colorForUtil(utilPercent)
}

// Attempt to fetch interfaces if missing (undefined). Zero-length is allowed and won't fetch.
onMounted(() => {
    if (device.value && !('interfaces' in device.value)) {
        void devices.fetchAllWithInterfaces?.()
    }
})

// Layout constants
const COLS = 8
const CELL = 6
const GAP = 2
const MAX_CELLS = 32

const visiblePorts = computed(() => ports.value.slice(0, MAX_CELLS))
const overflowCount = computed(() => Math.max(0, ports.value.length - visiblePorts.value.length))

const rows = computed(() => Math.ceil(visiblePorts.value.length / COLS))
const matrixWidth = computed(() => COLS * CELL + (COLS - 1) * GAP)

function cellX(idx: number) {
    const col = idx % COLS
    return col * (CELL + GAP)
}
function cellY(idx: number) {
    const row = Math.floor(idx / COLS)
    return row * (CELL + GAP)
}

// expose for template bindings
// eslint-disable-next-line @typescript-eslint/no-explicit-any
; (globalThis as any).__AGG__ = { CELL, GAP }
</script>

<style scoped>
.aggregation-cockpit {
    pointer-events: all;
}

.port-cell {
    opacity: 0.95
}

.port-util {
    opacity: 0.9
}

.overflow-indicator {
    opacity: 0.9
}
</style>
