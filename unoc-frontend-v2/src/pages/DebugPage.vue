<template>
    <div class="debug-root">
        <div class="toolbar">
            <button :disabled="loading" @click="refresh">{{ loading ? 'Loading…' : 'Refresh' }}</button>
            <span v-if="snapshot" class="meta">tick={{ snapshot.meta?.tick ?? '—' }} • ts={{ snapshot.meta?.ts }}</span>
            <span v-if="error" class="error">{{ error }}</span>
        </div>
        <pre v-if="snapshot" class="json">{{ pretty(snapshot) }}</pre>
        <div v-else class="placeholder">No snapshot yet. Press Refresh.</div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useDebugStore } from '../stores/debugStore.js'

const store = useDebugStore()
const snapshot = computed(() => store.snapshot)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

function refresh() {
    store.refresh()
}

function pretty(obj: unknown) {
    try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
}

onMounted(() => {
    // Auto-load first time
    if (!store.snapshot && !store.loading) store.refresh()
})
</script>

<style scoped>
.debug-root {
    padding: 16px;
    width: 100%;
    height: 100%;
    overflow: auto;
}

.toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 10px;
}

.toolbar button {
    background: #2c2c2c;
    color: #ddd;
    border: 0;
    padding: 6px 10px;
    border-radius: 4px;
    cursor: pointer;
}

.toolbar button:disabled {
    opacity: .5;
    cursor: default;
}

.meta {
    color: #9aa;
    font-size: 12px;
}

.error {
    color: #f88;
    font-size: 12px;
}

.json {
    background: #111;
    color: #cde;
    padding: 14px;
    border-radius: 6px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 12px;
    overflow-x: auto;
}

.placeholder {
    color: #9aa;
    font-size: 13px;
}
</style>
