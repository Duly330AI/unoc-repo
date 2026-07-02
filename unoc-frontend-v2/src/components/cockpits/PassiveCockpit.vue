<template>
    <!-- Passive cockpit: Digital Display style (compact) -->
    <g class="passive-cockpit" transform="scale(1.8)">
        <!-- Outer halo and main frame (status-colored via CSS) -->
        <rect
x="-56" y="-30" rx="10" ry="10" width="112" height="60" fill="none" class="frame-outline" stroke-width="6"
            opacity="0.15" />
        <rect x="-56" y="-30" rx="10" ry="10" width="112" height="60" :fill="bgDark" class="frame" stroke-width="2" />

        <!-- Header: device id left, LEDs right -->
        <text
x="-50" y="-16" text-anchor="start" :fill="headerColor" font-size="10px"
            font-family="var(--font-mono, monospace)">
            {{ deviceId }}
        </text>
        <g transform="translate(36, -22)">
            <circle r="4" cx="-10" cy="0" :fill="ledColor('UP') " :opacity="ledOpacity('UP')" />
            <circle r="4" cx="0" cy="0" :fill="ledColor('DEGRADED')" :opacity="ledOpacity('DEGRADED')" />
            <circle r="4" cx="8" cy="0" :fill="ledColor('DOWN')" :opacity="ledOpacity('DOWN')" />
        </g>

        <!-- Rows: TYPE and LOSS -->
        <g>
            <text
x="-50" y="-4" text-anchor="start" :fill="labelColor" font-size="10px"
                font-family="var(--font-mono, monospace)">TYPE:</text>
            <text
x="50" y="-4" text-anchor="end" :fill="typeColor" font-size="10px"
                font-family="var(--font-mono, monospace)">{{ typeLabel }}</text>

            <text
x="-50" y="12" text-anchor="start" :fill="labelColor" font-size="10px"
                font-family="var(--font-mono, monospace)">LOSS:</text>
            <text
x="50" y="12" text-anchor="end" :fill="lossColor" font-size="10px"
                font-family="var(--font-mono, monospace)">{{ lossText }}</text>
            <!-- Splitter usage badge: [used/total] -->
            <template v-if="isSplitter">
                <text
x="-50" y="28" text-anchor="start" :fill="labelColor" font-size="10px"
                    font-family="var(--font-mono, monospace)">PORTS:</text>
                <text
x="50" y="28" text-anchor="end" :fill="portsColor" font-size="10px"
                    font-family="var(--font-mono, monospace)">{{ portsText }}</text>
            </template>
        </g>
    </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDevicesStore, type DeviceOutX } from '../../stores/devicesStore'

const props = defineProps<{ deviceId: string }>();
const devices = useDevicesStore()

const device = computed(() => devices.byId(props.deviceId) as DeviceOutX | undefined)
const status = computed(() => device.value?.status ?? 'UNKNOWN')

// Visual system colors (match Digital Display)
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

// TYPE and LOSS
const typeLabel = computed(() => {
    const t = String(device.value?.type || 'PASSIVE')
    if (t === 'SPLITTER') return 'SPLITTER'
    if (t === 'ODF') return 'ODF'
    if (t === 'NVT') return 'NVT'
    if (t === 'HOP') return 'HOP'
    return t
})
const typeColor = '#b0bec5'

// Loss: prefer configured insertion loss; fall back to L1 measured loss from
// the optical physics model instead of inventing "0.0 dB" when unset.
const lossNum = computed<number | null>(() => {
    const configured = device.value?.insertion_loss_db
    if (typeof configured === 'number' && Number.isFinite(configured)) return configured
    const params = (device.value?.parameters || {}) as unknown as { optical?: { measured_loss_db?: number } }
    const measured = params?.optical?.measured_loss_db
    if (typeof measured === 'number' && Number.isFinite(measured)) return measured
    return null
})
const lossText = computed(() => (lossNum.value == null ? '—' : `${lossNum.value.toFixed(1)} dB`))
const lossColor = computed(() => ((lossNum.value ?? 0) > 0 ? '#ef5350' : '#90caf9'))

// Splitter usage [used/total]
const isSplitter = computed(() => String(device.value?.type || '') === 'SPLITTER')
const portsText = computed(() => {
    const params = (device.value?.parameters || {}) as unknown as { splitter?: { ports_used?: number; ports_total?: number } }
    const sp = params?.splitter || {}
    const used = Number(sp.ports_used ?? 0)
    const total = Number(sp.ports_total ?? 0)
    if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0) return '-'
    return `[${used}/${total}]`
})
const portsColor = computed(() => '#90caf9')
</script>

<style scoped>
.passive-cockpit {
    pointer-events: all;
}
</style>
