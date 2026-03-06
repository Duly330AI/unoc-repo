<template>
    <g class="base-cockpit" :data-type="deviceType">
        <!-- integrated halo for POP/backbone styles -->
        <circle v-if="deviceType === 'POP'" r="36" fill="url(#popHalo)" opacity="0.85" />
        <!-- signal dot for ONT types -->
        <circle v-if="isOnt" r="4" :fill="signalColor" cx="-48" cy="-28" />
        <rect x="-70" y="-36" rx="8" ry="8" width="140" height="72" :fill="bg" class="frame" stroke-width="2" />
        <!-- Use foreignObject to layout text with CSS to prevent overlap -->
        <foreignObject x="-66" y="-30" width="132" height="60">
            <div xmlns="http://www.w3.org/1999/xhtml" class="cockpit-box">
                <div class="name" :title="deviceName">{{ deviceName }}</div>
                <div class="status" :data-status="statusText">{{ statusText }}</div>
            </div>
        </foreignObject>
    </g>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useDevicesStore } from '../../stores/devicesStore'

const props = defineProps<{ deviceId: string }>()
const devices = useDevicesStore()

const device = computed(() => devices.byId(props.deviceId))
const deviceName = computed(() => device.value?.name ?? props.deviceId)
const deviceType = computed(() => device.value?.type ?? 'UNKNOWN')
const status = computed(() => device.value?.status ?? 'UNKNOWN')
const statusText = computed(() => String(status.value))
// utilization used by RouterCockpit; base renders status/name only
const isOnt = computed(() => ['ONT', 'BUSINESS_ONT', 'AON_CPE'].includes(deviceType.value))
type SigDev = { signal_status?: 'OK' | 'WARNING' | 'CRITICAL' | 'NO_SIGNAL' | null }
const signalColor = computed(() => {
    const s = (device.value as SigDev | undefined)?.signal_status
    if (s === 'OK') return '#4caf50'
    if (s === 'WARNING') return '#ff9800'
    if (s === 'CRITICAL') return '#d32f2f'
    if (s === 'NO_SIGNAL') return '#9e9e9e'
    return '#b0bec5'
})

const bg = '#263238'

// Optional lightweight debug for cockpit mounting; uses global flag set elsewhere if desired
onMounted(() => {
    interface DebugGlobal { __UNOC_DEBUG__?: boolean }
    const g = globalThis as unknown as DebugGlobal
    if (g && g.__UNOC_DEBUG__) {
        // eslint-disable-next-line no-console
        console.debug('[BaseCockpit] mounted', props.deviceId)
    }
})
</script>

<style scoped>
.base-cockpit {
    pointer-events: all;
}

.cockpit-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    padding: 2px 4px;
}

.cockpit-box .name {
    font-family: var(--font-mono, monospace);
    font-size: 12px;
    color: #e0e0e0;
    text-align: center;
    line-height: 1.2;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cockpit-box .status {
    font-family: var(--font-mono, monospace);
    font-size: 10px;
    text-align: center;
    line-height: 1.2;
    color: #bdbdbd;
}

.cockpit-box .status[data-status="UP"] {
    color: #66bb6a;
}

.cockpit-box .status[data-status="DOWN"] {
    color: #ef5350;
}

.cockpit-box .status[data-status="DEGRADED"] {
    color: #ef6c00;
}
</style>
