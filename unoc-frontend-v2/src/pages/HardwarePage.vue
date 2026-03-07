<template>
    <div class="hardware-page">
        <header class="hp-header">
            <h2>Hardware Catalog</h2>
            <div class="filters">
                <label>
                    Type
                    <select v-model="type">
                        <option value="">All</option>
                        <option v-for="t in DEVICE_TYPES" :key="t" :value="t">{{ t }}</option>
                    </select>
                </label>
                <button :disabled="store.loading" @click="reload">Reload</button>
            </div>
        </header>

        <div v-if="store.error" class="error">{{ store.error }}</div>

        <table class="list">
            <thead>
                <tr>
                    <th>Catalog ID</th>
                    <th>Type</th>
                    <th>Vendor/Model</th>
                    <th>Version</th>
                    <th>Capacity (Gbps)</th>
                    <th>Ports</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="m in store.items" :key="m.id">
                    <td><code>{{ m.catalog_id }}</code></td>
                    <td>{{ m.device_type }}</td>
                    <td>{{ m.vendor || '-' }} / {{ m.model || '-' }}</td>
                    <td>{{ m.version || '-' }}</td>
                    <td class="num">{{ m.capacity_gbps ?? '-' }}</td>
                    <td class="num">{{ m.ports_total ?? '-' }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useHardwareStore } from '../stores/hardwareStore'
import type { DeviceType } from '../types/domain'

const store = useHardwareStore()
const DEVICE_TYPES: DeviceType[] = [
    'AON_CPE', 'AON_SWITCH', 'BACKBONE_GATEWAY', 'BUSINESS_ONT', 'CORE_ROUTER', 'EDGE_ROUTER', 'HOP', 'NVT', 'ODF', 'OLT', 'ONT', 'POP', 'SPLITTER'
]
const type = ref<string>('')

function reload() {
    store.fetchAll(type.value || undefined)
}

onMounted(() => reload())

watch(type, () => reload())
</script>

<style scoped>
.hardware-page {
    display: flex;
    flex-direction: column;
    gap: .75rem;
}

.hp-header {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.filters {
    display: flex;
    align-items: center;
    gap: .5rem;
}

.error {
    color: red;
}

.list {
    width: 100%;
    border-collapse: collapse;
}

.list th,
.list td {
    border-bottom: 1px solid var(--color-border);
    padding: .4rem .5rem;
    font-size: .8rem;
}

.list thead th {
    text-align: left;
    color: var(--color-text-dim);
    font-weight: 600;
}

.num {
    text-align: right;
}

code {
    font-size: .75rem;
}
</style>
