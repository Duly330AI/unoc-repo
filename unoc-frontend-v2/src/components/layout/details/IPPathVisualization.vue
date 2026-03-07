<template>
  <div class="ip-path-section">
    <div class="section-title">IP Communication Path</div>
    
    <!-- Loading state -->
    <div v-if="loading" class="placeholder-props">Loading IP path...</div>
    
    <!-- Error state -->
    <div v-else-if="error" class="field-error">{{ error }}</div>
    
    <!-- No data state -->
    <div v-else-if="!pathData" class="placeholder-props">No path data available</div>
    
    <!-- Path visualization -->
    <div v-else>
      <!-- Own IPs section - using meta-list structure -->
      <div v-if="pathData.own_ips && pathData.own_ips.length > 0" class="meta-list">
        <div class="subsection-title">Device IPs</div>
        <div v-for="(ipEntry, idx) in pathData.own_ips" :key="idx" class="row">
          <label>{{ ipEntry.interface }}</label>
          <span class="mono">{{ ipEntry.ip }}</span>
        </div>
      </div>
      
      <!-- Path to Gateway - using meta-list structure -->
      <div class="meta-list" style="margin-top: 1rem;">
        <div class="subsection-title">
          Path to Backbone Gateway
        </div>
        <div class="row">
          <label>Status</label>
          <span>
            <span v-if="pathData.reachable" class="chip signal" data-signal="OK">✓ REACHABLE</span>
            <span v-else class="chip signal" data-signal="CRITICAL">✗ UNREACHABLE</span>
          </span>
        </div>
        
        <!-- Unreachable reason -->
        <div v-if="!pathData.reachable && pathData.reason" class="row">
          <label>Reason</label>
          <span class="field-error">{{ pathData.reason }}</span>
        </div>
      </div>
      
      <!-- Hop-by-hop path -->
      <div v-if="pathData.path_to_gateway && pathData.path_to_gateway.length > 0" class="hops-section">
        <div class="subsection-title">Hops</div>
        <div v-for="hop in pathData.path_to_gateway" :key="hop.hop" class="hop-card">
          <div class="hop-header">
            <span class="hop-number">Hop {{ hop.hop }}</span>
            <span class="device-type-badge">{{ hop.device_type }}</span>
          </div>
          <div class="hop-body">
            <div class="hop-row">
              <label>Device</label>
              <span class="device-name">{{ hop.device_name }}</span>
            </div>
            <div v-if="hop.ip" class="hop-row">
              <label>IP</label>
              <span class="mono">{{ hop.ip }}</span>
            </div>
            <div v-if="hop.interface" class="hop-row">
              <label>Interface</label>
              <span>{{ hop.interface }}</span>
            </div>
            <div v-if="!hop.ip" class="hop-row">
              <label>IP</label>
              <span class="no-ip-label">No IP address</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

interface IPPathData {
  device_id: string
  device_name: string
  device_type: string
  own_ips: Array<{ interface: string; ip: string }>
  path_to_gateway: Array<{
    hop: number
    device_id: string
    device_name: string
    device_type: string
    ip: string | null
    interface: string | null
  }>
  reachable: boolean
  reason?: string
}

const props = defineProps<{
  deviceId: string
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const pathData = ref<IPPathData | null>(null)

async function fetchIPPath() {
  if (!props.deviceId) return
  
  loading.value = true
  error.value = null
  
  try {
    const response = await fetch(`/api/devices/${props.deviceId}/ip-trace`)
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to load IP path')
    }
    pathData.value = await response.json()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Failed to load IP path'
    pathData.value = null
  } finally {
    loading.value = false
  }
}

// Load on mount and when deviceId changes
onMounted(() => {
  fetchIPPath()
})

watch(() => props.deviceId, () => {
  fetchIPPath()
})
</script>

<style scoped>
/* Match Overview/Optical Section styling */
.ip-path-section {
  border-top: 1px solid var(--color-border);
  padding-top: 0.6rem;
  font-size: 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.section-title {
  font-weight: 600;
  font-size: 0.7rem;
  color: var(--color-text-dim);
  margin-bottom: 0.25rem;
}

.subsection-title {
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-dim);
  margin-bottom: 0.4rem;
}

/* Meta list - same as Overview/Optical */
.meta-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.65rem;
}

.meta-list .row {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 0.35rem;
}

.meta-list label {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 0.55rem;
  color: var(--color-text-dim);
}

/* Signal chip - same as Optical */
.chip.signal {
  display: inline-block;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-size: 0.55rem;
  font-weight: 600;
  text-transform: uppercase;
}

.chip.signal[data-signal="OK"] {
  background: #1b5e20;
  color: #fff;
}

.chip.signal[data-signal="CRITICAL"] {
  background: #b71c1c;
  color: #fff;
}

/* Hops section */
.hops-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.hop-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.hop-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-bottom: 0.3rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.hop-number {
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.device-type-badge {
  font-size: 0.5rem;
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
  background: #333;
  color: #aaa;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.hop-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.hop-row {
  display: grid;
  grid-template-columns: 70px 1fr;
  gap: 0.35rem;
  font-size: 0.6rem;
}

.hop-row label {
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  font-size: 0.52rem;
  color: var(--color-text-dim);
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
}

.no-ip-label {
  font-style: italic;
  color: var(--color-text-dim);
  opacity: 0.7;
}

/* Monospace for IPs */
.mono {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
}

/* Placeholder and error states */
.placeholder-props {
  padding: 1rem;
  text-align: center;
  color: var(--color-text-dim);
  font-size: 0.65rem;
}

.field-error {
  color: #ef9a9a;
  font-size: 0.6rem;
}
</style>
