<template>
  <div class="ip-path-section">
    <!-- IP Path Visualization for active devices -->
    <IPPathVisualization v-if="isActiveDevice(device)" :device-id="device?.id || ''" />
    
    <!-- Transiting IPs for passive devices (splitters only) -->
    <TransitingIPsList v-if="isPassiveDevice(device)" :device-id="device?.id || ''" />
    
    <!-- Fallback for devices without IP path info -->
    <div v-if="!isActiveDevice(device) && !isPassiveDevice(device)" class="placeholder">
      <div class="hint">Keine IP-Routing-Informationen verfügbar für diesen Device-Typ.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DeviceOut } from '../../../types/domain'
import IPPathVisualization from './IPPathVisualization.vue'
import TransitingIPsList from './TransitingIPsList.vue'

defineProps<{ device: DeviceOut | null }>()

/**
 * Active devices have IP addresses and routing capability:
 * - OLT, AON_SWITCH, EDGE_ROUTER, CORE_ROUTER, BACKBONE_GATEWAY
 * - ONT, BUSINESS_ONT (Customer Premise Equipment with IP)
 * - AON_CPE (Active Optical Network Customer Premise Equipment)
 */
function isActiveDevice(device: DeviceOut | null): boolean {
  if (!device) return false
  const activeTypes = [
    'OLT',
    'AON_SWITCH',
    'ONT',
    'BUSINESS_ONT',
    'AON_CPE',
    'EDGE_ROUTER',
    'CORE_ROUTER',
    'BACKBONE_GATEWAY'
  ]
  return activeTypes.includes(device.type)
}

/**
 * Passive devices forward traffic without IP processing:
 * - SPLITTER (optical signal distribution)
 */
function isPassiveDevice(device: DeviceOut | null): boolean {
  if (!device) return false
  return device.type === 'SPLITTER'
}
</script>

<style scoped>
.ip-path-section {
  padding: 1rem;
}

.placeholder {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted, #888);
}

.hint {
  font-size: 0.9rem;
  font-style: italic;
}
</style>
