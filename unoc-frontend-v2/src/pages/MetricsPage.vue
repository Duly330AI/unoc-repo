<template>
    <div class="metrics-page">
        <div class="toolbar">
            <h3>Metrics</h3>
            <div class="filters">
                <input v-model="q" class="inp" type="text" placeholder="Search name or id" />
                <select v-model="type" class="inp">
                    <option value="">All types</option>
                    <option v-for="t in deviceTypes" :key="t" :value="t">{{ t }}</option>
                </select>
                <select v-model="status" class="inp">
                    <option value="">All status</option>
                    <option value="UP">UP</option>
                    <option value="DEGRADED">DEGRADED</option>
                    <option value="DOWN">DOWN</option>
                    <option value="BLOCKING">BLOCKING</option>
                </select>
                <select v-model.number="bucket" class="inp">
                    <option :value="-1">All utilization</option>
                    <option v-for="b in utilizationBuckets" :key="b" :value="b">≥ {{ Math.round(b * 100) }}%</option>
                </select>
                <select v-model="sortBy" class="inp">
                    <option value="util">Sort: Utilization</option>
                    <option value="bps">Sort: Bps</option>
                    <option value="name">Sort: Name</option>
                </select>
            </div>
            <button class="btn" :disabled="loading" @click="reload">Reload snapshot</button>
        </div>

        <div class="summary">
            <div class="card">Devices: <b>{{ rows.length }}</b></div>
            <div class="card">Overloaded (≥90%): <b>{{ overloadedCount }}</b></div>
            <div v-if="topPreview.length" class="card">Top by util: <b>{{topPreview.map(r => r.name).join(', ')}}</b>
            </div>
        </div>

        <div ref="listWrap" class="table-wrap" @scroll="onScroll">
            <table class="tbl">
                <thead>
                    <tr>
                        <th class="name">Name</th>
                        <th class="type">Type</th>
                        <th class="status">Status</th>
                        <th class="num">Util (%)</th>
                        <th class="num">Bps</th>
                        <th class="num">Up Bps</th>
                        <th class="num">Down Bps</th>
                    </tr>
                </thead>
                <tbody :style="tbodyStyle">
                    <tr v-for="r in visibleRows" :key="r.id" class="row" :style="{ top: (r._pos) + 'px' }">
                        <td class="name">{{ r.name }}</td>
                        <td class="type">{{ r.type }}</td>
                        <td class="status" :data-status="r.status">{{ r.status }}</td>
                        <td class="num" :data-util="Math.round(r.utilization * 100)">{{ (r.utilization * 100).toFixed(0)
                        }}
                        </td>
                        <td class="num">{{ formatBps(r.bps) }}</td>
                        <td class="num">{{ r.upstream_bps != null ? formatBps(r.upstream_bps) : '—' }}</td>
                        <td class="num">{{ r.downstream_bps != null ? formatBps(r.downstream_bps) : '—' }}</td>
                    </tr>
                </tbody>
            </table>
            <div v-if="!rows.length && !loading" class="empty">No metrics yet</div>
        </div>
    </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useMetricsStore } from '../stores/metricsStore.js'
import { buildDeviceMetricRows, type DeviceMetricRow, type SortBy } from './metricsSelectors'
import type { DeviceType, Status } from '../types/domain.js'

const devices = useDevicesStore()
const metrics = useMetricsStore()

const q = ref('')
const type = ref('')
const status = ref('')
const bucket = ref(-1)
const sortBy = ref<SortBy>(
    (typeof sessionStorage !== 'undefined' && (sessionStorage.getItem('metrics:sortBy') as SortBy | null)) || 'util'
)

watch(sortBy, v => { try { sessionStorage.setItem('metrics:sortBy', v) } catch { /* ignore */ } })

const deviceTypes = computed(() => Array.from(new Set(devices.devices.map(d => d.type))).sort())
const utilizationBuckets = computed(() => {
    const g = (globalThis as unknown as { __unocConfigStore__?: { metrics?: { UTILIZATION_BUCKETS?: number[] } } }).__unocConfigStore__
    return g?.metrics?.UTILIZATION_BUCKETS || [0.5, 0.7, 0.85, 0.9]
})

const loading = ref(false)
async function reload() {
    loading.value = true
    try {
        const resp = await fetch('/api/metrics/snapshot')
        if (resp.ok) { metrics.applySnapshot(await resp.json()) }
    } finally { loading.value = false }
}

onMounted(async () => {
    // if no metrics loaded yet, hydrate from snapshot
    if (!metrics.lastTick || Object.keys(metrics.byId).length === 0) { await reload() }
    // ensure devices are available for names/types
    if (devices.devices.length === 0) { await devices.fetchAll() }
})

const rows = computed<DeviceMetricRow[]>(() =>
    buildDeviceMetricRows({
        devices: devices.devices,
        metricsById: metrics.byId,
        q: q.value,
        type: (type.value || '') as DeviceType | '',
        status: (status.value || '') as Status | '',
        utilBucketMin: bucket.value,
        sortBy: sortBy.value
    })
)

const overloadedCount = computed(() => rows.value.filter(r => r.utilization >= 0.9).length)
const topPreview = computed(() => rows.value.slice(0, 5))

// Lightweight virtualization
const ROW_H = 28
const listWrap = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const viewportH = ref(420)

function onScroll() { if (listWrap.value) { scrollTop.value = listWrap.value.scrollTop } }

onMounted(() => { if (listWrap.value) { viewportH.value = listWrap.value.clientHeight } })

const startIdx = computed(() => Math.max(0, Math.floor(scrollTop.value / ROW_H) - 10))
const endIdx = computed(() => Math.min(rows.value.length, Math.ceil((scrollTop.value + viewportH.value) / ROW_H) + 10))
const visibleRows = computed(() => rows.value.slice(startIdx.value, endIdx.value).map((r, i) => ({ ...r, _pos: (startIdx.value + i) * ROW_H })))
const tbodyStyle = computed<CSSProperties>(() => ({ height: (rows.value.length * ROW_H) + 'px', position: 'relative' }))

function formatBps(v: number) {
    if (v == null) return ''
    const abs = Math.abs(v)
    if (abs >= 1e9) return (v / 1e9).toFixed(2) + ' Gbps'
    if (abs >= 1e6) return (v / 1e6).toFixed(2) + ' Mbps'
    if (abs >= 1e3) return (v / 1e3).toFixed(2) + ' Kbps'
    return v + ' bps'
}
</script>
<style scoped>
.metrics-page {
    padding: 1rem;
    color: #eee;
    font-size: .8rem;
}

.toolbar {
    display: flex;
    align-items: center;
    gap: .5rem;
    margin-bottom: .5rem;
}

.filters {
    display: flex;
    gap: .4rem;
    align-items: center;
}

.inp {
    background: #2a2a2a;
    color: #ddd;
    border: 1px solid #3a3a3a;
    padding: .3rem .45rem;
    border-radius: 4px;
}

.btn {
    background: #333;
    color: #ccc;
    border: 0;
    padding: .35rem .7rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn:hover {
    background: #444;
    color: #fff;
}

.summary {
    display: flex;
    gap: .5rem;
    margin: .5rem 0;
}

.card {
    background: #262626;
    border: 1px solid #333;
    padding: .4rem .6rem;
    border-radius: 4px;
}

.table-wrap {
    position: relative;
    height: calc(100vh - 230px);
    overflow: auto;
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    /* Reserve space for scrollbar to keep header/body widths aligned */
    scrollbar-gutter: stable both-edges;
}

.tbl {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    table-layout: fixed;
}

.tbl thead th {
    position: sticky;
    top: 0;
    background: #1e1e1e;
    z-index: 1;
    text-align: left;
    /* remove horizontal padding; use row padding for consistent grid like tbody */
    padding: .35rem 0;
    border-bottom: 1px solid #2d2d2d;
}

/* Ensure thead aligns with tbody grid columns */
.tbl thead {
    display: block;
}

.tbl thead tr {
    display: grid;
    grid-template-columns: 1.8fr .8fr .8fr .6fr .8fr .8fr .8fr;
    /* match tbody row horizontal padding */
    padding: 0 .5rem;
}

.tbl thead th.num {
    text-align: right;
}

.tbl thead th.name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tbl tbody {
    display: block;
    position: relative;
}

.tbl .row {
    position: absolute;
    left: 0;
    right: 0;
    height: 28px;
    display: grid;
    grid-template-columns: 1.8fr .8fr .8fr .6fr .8fr .8fr .8fr;
    align-items: center;
    padding: 0 .5rem;
    border-bottom: 1px solid #242424;
}

.tbl td {
    padding: 0;
    /* rely on row/grid padding for consistent alignment */
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tbl td.status[data-status="DOWN"],
.tbl td.status[data-status="BLOCKING"] {
    color: #f87171
}

.tbl td.status[data-status="DEGRADED"] {
    color: #f59e0b
}

.tbl td.status[data-status="UP"] {
    color: #34d399
}

/* Subtle badge styling for status cells */
.tbl td.status {
    font-weight: 600;
    letter-spacing: .2px;
}

.tbl td.status::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
    background: currentColor;
}

.tbl td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.empty {
    opacity: .6;
    font-style: italic;
    padding: 1rem;
}

.metrics-wrapper {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
}
</style>
