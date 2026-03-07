<template>
  <div class="transiting-ips-list">
    <div class="section-title">Transiting IPs (Passive Device)</div>
    
    <!-- Loading state -->
    <div v-if="loading" class="placeholder-props">Loading transiting IPs...</div>
    
    <!-- Error state -->
    <div v-else-if="error" class="field-error">{{ error }}</div>
    
    <!-- No data state -->
    <div v-else-if="!transitData" class="placeholder-props">No transit data available</div>
    
    <!-- Transiting IPs visualization -->
    <div v-else class="transit-container">
      <!-- Device info -->
      <div class="device-info">
        <span class="device-name">{{ transitData.device_name }}</span>
        <span class="badge">{{ transitData.device_type }}</span>
        <span v-if="transitData.is_passive" class="badge passive">Passive Device</span>
        <span v-else class="badge active">Active Device</span>
      </div>
      
      <!-- IP Pools summary -->
      <div v-if="transitData.ip_pools && transitData.ip_pools.length > 0" class="ip-pools">
        <div class="subsection-title">IP Pools Summary</div>
        <div class="pools-list">
          <div v-for="pool in transitData.ip_pools" :key="pool.subnet" class="pool-entry">
            <span class="mono subnet">{{ pool.subnet }}</span>
            <span class="pool-count">{{ pool.active_count }} active IPs</span>
          </div>
        </div>
      </div>
      
      <!-- Transiting IPs table -->
      <div v-if="transitData.transiting_ips && transitData.transiting_ips.length > 0" class="transiting-ips">
        <div class="subsection-title">
          Transiting IPs ({{ transitData.transiting_ips.length }} total)
        </div>
        <div class="ips-table">
          <div class="table-header">
            <span class="col-ip">IP Address</span>
            <span class="col-source">Source Device</span>
            <span class="col-interface">Via Interface</span>
          </div>
          <div v-for="(ip, idx) in transitData.transiting_ips" :key="idx" class="table-row">
            <span class="col-ip mono">{{ ip.ip }}</span>
            <span class="col-source">{{ ip.source_device_name }}</span>
            <span class="col-interface interface-label">{{ ip.via_interface }}</span>
          </div>
        </div>
      </div>
      
      <!-- Empty state -->
      <div v-else-if="transitData.transiting_ips && transitData.transiting_ips.length === 0" class="empty-state">
        No IPs currently transiting through this device
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

interface TransitingIP {
  ip: string
  source_device_id: string
  source_device_name: string
  via_interface: string
}

interface IPPool {
  subnet: string
  active_count: number
}

interface TransitData {
  device_id: string
  device_name: string
  device_type: string
  is_passive: boolean
  transiting_ips: TransitingIP[]
  ip_pools: IPPool[]
}

const props = defineProps<{
  deviceId: string
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const transitData = ref<TransitData | null>(null)

async function fetchTransitingIPs() {
  if (!props.deviceId) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`/api/devices/${props.deviceId}/transiting-ips`)
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to load transiting IPs')
    }
    transitData.value = await response.json()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load transiting IPs'
    transitData.value = null
  } finally {
    loading.value = false
  }
}

// Load on mount and when deviceId changes
onMounted(() => {
  fetchTransitingIPs()
})

watch(() => props.deviceId, () => {
  fetchTransitingIPs()
})
</script>

<style scoped>
.transiting-ips-list {
  margin-top: 1rem;
}

.section-title {
  font-weight: 600;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.subsection-title {
  font-weight: 500;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.placeholder-props {
  color: var(--text-tertiary);
  font-style: italic;
  padding: 0.5rem 0;
}

.field-error {
  color: var(--status-down);
  padding: 0.5rem;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 4px;
  font-size: 0.9rem;
}

.transit-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Device info */
.device-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem;
  background: var(--bg-surface);
  border-radius: 6px;
  border: 1px solid var(--border-primary);
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.badge.passive {
  background: rgba(156, 163, 175, 0.2);
  color: var(--text-secondary);
}

.badge.active {
  background: rgba(59, 130, 246, 0.2);
  color: rgb(59, 130, 246);
}

/* IP Pools */
.ip-pools {
  padding: 0.75rem;
  background: var(--bg-surface);
  border-radius: 6px;
  border: 1px solid var(--border-primary);
}

.pools-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.pool-entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.6rem;
  background: var(--bg-base);
  border-radius: 4px;
}

.mono {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.subnet {
  font-weight: 500;
}

.pool-count {
  font-size: 0.85rem;
  color: var(--text-tertiary);
}

/* Transiting IPs table */
.transiting-ips {
  padding: 0.75rem;
  background: var(--bg-surface);
  border-radius: 6px;
  border: 1px solid var(--border-primary);
}

.ips-table {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 2fr 2fr 1.5fr;
  gap: 1rem;
  padding: 0.5rem 0.6rem;
  align-items: center;
}

.table-header {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 0.4rem;
}

.table-row {
  background: var(--bg-base);
  border-radius: 4px;
  font-size: 0.9rem;
}

.table-row:hover {
  background: var(--bg-hover);
}

.col-ip {
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-source {
  color: var(--text-primary);
}

.interface-label {
  font-size: 0.85rem;
  color: var(--text-tertiary);
}

/* Empty state */
.empty-state {
  padding: 1.5rem;
  text-align: center;
  color: var(--text-tertiary);
  font-style: italic;
  background: var(--bg-surface);
  border-radius: 6px;
  border: 1px dashed var(--border-primary);
}
</style>
