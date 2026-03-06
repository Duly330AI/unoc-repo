<template>
  <aside class="details">
    <header>Details</header>
    <div class="content">
      <!-- Empty selection -->
      <div v-if="deviceCount === 0 && linkCount === 0" class="placeholder empty">Keine Auswahl<br /><small>Wähle ein
          Gerät
          oder eine Verbindung.</small></div>

      <!-- Multi selection summary -->
      <div v-else-if="deviceCount + linkCount > 1" class="placeholder multi">
        <strong>{{ deviceCount }} Gerät{{ deviceCount === 1 ? '' : 'e' }}</strong>
        <span v-if="linkCount > 0">&nbsp;+ {{ linkCount }} Link{{ linkCount === 1 ? '' : 's' }}</span>
        <div class="hint"><small>Mehrfachauswahl – Details erst bei Einzel-Auswahl.</small></div>
      </div>

      <!-- Single link details -->
      <LinkDetails v-else-if="activeLink" :link="activeLink" />

      <!-- Single device loading (id known but data noch nicht geladen) -->
      <div v-else-if="deviceCount === 1 && !activeDevice" class="placeholder loading">Lade Gerät <span class="mono">{{
        singleDeviceId }}</span>…</div>

      <!-- Single device details -->
      <div v-else-if="activeDevice" class="device-details">
        <div class="title-row">
          <span class="name" :title="activeDevice.id">{{ activeDevice.name || activeDevice.id }}</span>
          <span class="badge status" :data-status="activeDevice.status">{{ activeDevice.status }}</span>
          <span
v-if="activeDevice.provisioned" class="badge provisioned"
            title="Provisioned (mgmt0 vorhanden)">PROVISIONED</span>
        </div>
        <div class="meta">
          <div><label>Typ</label><span>{{ activeDevice.type }}</span></div>
          <div><label>Rolle</label><span>{{ activeDevice.role }}</span></div>
          <div><label>ID</label><span class="mono">{{ activeDevice.id }}</span></div>
        </div>
        <DeviceActions :device="activeDevice" :provisioning="provisioning" :can-provision="canProvision" :on-provision="onProvision" />
        <!-- Tabs: Overview | IP Path | Optical -->
        <DeviceTabs v-model="activeTab" :tabs="visibleTabs" />
        <div class="tab-content">
          <!-- Overview tab: existing properties + tariff section -->
          <DeviceOverviewSection v-if="activeTab === 'Overview'" :device="activeDevice" />

          <!-- IP Path tab: IP Communication Path + Transiting IPs -->
          <DeviceIPPathSection v-else-if="activeTab === 'IP Path'" :device="activeDevice" />

          <!-- Optical tab -->
          <DeviceOpticalSection v-else-if="activeTab === 'Optical'" :device="activeDevice" />
        </div>
      </div>

      <!-- Fallback -->
      <div v-else class="placeholder">Keine Daten</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { useSelectionStore } from '../../stores/selectionStore'
import { useDevicesStore } from '../../stores/devicesStore'
import { useLinksStore } from '../../stores/linksStore'
import '../../types/augment-domain.d'
import type { DeviceOut } from '../../types/domain.js'
import { useDeviceProvisioning } from '../../composables/useDeviceProvisioning.js'
import { useSpinnerStore } from '../../stores/spinnerStore.js'
import LinkDetails from './details/LinkDetails.vue'
import DeviceTabs from './details/DeviceTabs.vue'
import DeviceActions from './details/DeviceActions.vue'
import DeviceOverviewSection from './details/DeviceOverviewSection.vue'
import DeviceIPPathSection from './details/DeviceIPPathSection.vue'
import DeviceOpticalSection from './details/DeviceOpticalSection.vue'

type DeviceWithParent = (DeviceOut & {
  parent_container_id?: string | null
  signal_status?: 'OK' | 'WARNING' | 'CRITICAL' | 'NO_SIGNAL' | null
  signal_power_dbm?: number | null
  signal_margin_db?: number | null
  tx_power_dbm?: number | null
  sensitivity_min_dbm?: number | null
  total_path_attenuation_db?: number | null
})

const selection = useSelectionStore()
const devices = useDevicesStore()
const links = useLinksStore()

// Lazy init: load lists once a selection occurs
const initialized = ref(false)
function ensureLoaded() {
  if (initialized.value) return
  if (devices.devices.length === 0 && !devices.loading) devices.fetchAll()
  if (links.links.length === 0 && !links.loading && typeof links.fetchAll === 'function') links.fetchAll()
  initialized.value = true
}
onMounted(() => { if (selection.items.length) ensureLoaded() })
watch(() => selection.items.length, (n) => { if (n > 0) ensureLoaded() })

// Derive selection partitions
const selectedDevices = computed(() => selection.items.filter(i => i.kind === 'device'))
const selectedLinks = computed(() => selection.items.filter(i => i.kind === 'link'))
const deviceCount = computed(() => selectedDevices.value.length)
const linkCount = computed(() => selectedLinks.value.length)
const singleDeviceId = computed(() => deviceCount.value === 1 ? selectedDevices.value[0].id : null)

const activeDevice = computed<DeviceWithParent | null>(() => {
  if (deviceCount.value !== 1) return null
  const id = selectedDevices.value[0].id
  return (devices.byId(id) as DeviceWithParent | undefined) ?? null
})
const activeLink = computed(() => {
  if (linkCount.value !== 1) return null
  const id = selectedLinks.value[0].id
  return links.links.find(l => l.id === id) || null
})

// Rename & delete handled by DeviceActions component (legacy refs removed)

// Provisioning via composable
const { provisioning, canProvision, doProvision } = useDeviceProvisioning(activeDevice)

// Wrap provisioning with a simple blocking spinner overlay
const spinner = useSpinnerStore()
async function onProvision() {
  spinner.show('Provisioning...')
  try {
    await doProvision()
  } finally {
    spinner.hide()
  }
}

// Override actions moved to DeviceActions

function isOnt(d: DeviceWithParent | null): boolean {
  if (!d) return false
  return d.type === 'ONT' || d.type === 'BUSINESS_ONT'
}
function isOlt(d: DeviceWithParent | null): boolean { return !!d && d.type === 'OLT' }
function isPassiveOptical(d: DeviceWithParent | null): boolean {
  if (!d) return false
  return d.type === 'SPLITTER' || d.type === 'HOP' || d.type === 'NVT' || d.type === 'ODF'
}

// Optical edit state moved to DeviceOpticalSection

// ---- Tabs & Ports/IPAM sub-view ----
type TabName = 'Overview' | 'IP Path' | 'Optical'
const activeTab = ref<TabName>('Overview')
// Interfaces are rendered via DeviceInterfaces; presence is not required to show the tab

function isActiveDeviceType(d: DeviceWithParent | null): boolean {
  if (!d) return false
  // Passive optical devices should not expose logical ports
  return !(d.type === 'SPLITTER' || d.type === 'HOP' || d.type === 'NVT' || d.type === 'ODF')
}

const visibleTabs = computed<TabName[]>(() => {
  const tabs: TabName[] = ['Overview']
  const d = activeDevice.value
  // IP Path tab for active devices (with IP routing) or passive devices (with transiting IPs)
  if (d && (isActiveDeviceType(d) || isPassiveOptical(d))) tabs.push('IP Path')
  // Optical tab for OLT, ONT, and passive optical devices
  if (d && (isOlt(d) || isOnt(d) || isPassiveOptical(d))) tabs.push('Optical')
  return tabs
})

// If interfaces not loaded yet for this device, fetch expanded list
watch(activeDevice, (d) => {
  activeTab.value = 'Overview'
  if (!d) return
  const maybeIfaces = (d as unknown as { interfaces?: unknown })?.interfaces
  const hasIfaces = Array.isArray(maybeIfaces)
  if (!hasIfaces) {
    // best-effort; ignore errors
    void devices.fetchAllWithInterfaces()
  }
}, { immediate: true })
</script>

<style src="./DetailsPanel.css"></style>
