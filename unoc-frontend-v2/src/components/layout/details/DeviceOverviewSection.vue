<template>
  <div class="properties">
    <div class="meta-list">
      <div v-for="p in deviceProps" :key="p.key" class="row" :class="{ warn: p.warn }">
        <label>{{ p.key }}</label><span>{{ p.value }}</span>
      </div>
    </div>
    <div v-if="device && device.type === 'SPLITTER'" class="splitter-usage">
      <div class="section-title">Splitter</div>
      <div class="meta-list">
        <div class="row"><label>Ports</label><span>{{ splitterPortsText }}</span></div>
      </div>
    </div>
    <div v-if="showPortsSection" class="ports-section">
      <div class="section-title">Ports</div>
      <div v-if="portsLoading" class="placeholder-props">Lade Ports…</div>
      <div v-else-if="portsError" class="field-error">{{ portsError }}</div>
      <div v-else class="ports-list">
        <template v-for="group in portGroups" :key="group.role">
          <div class="port-role">{{ group.role }}</div>
          <div v-if="group.ports.length === 0" class="port-empty">—</div>
          <div v-for="p in group.ports" :key="p.id || p.name" class="port-entry" :data-status="p.effective_status">
            <span class="port-name mono">{{ p.name || 'port' }}</span>
            <span class="port-occupancy">[{{ p.used }} / {{ p.capacity === -1 ? '?' : p.capacity }}]</span>
            <span class="badge status" :data-status="p.effective_status">{{ p.effective_status }}</span>
            <span v-if="p.mac" class="port-mac mono">{{ p.mac }}</span>
          </div>
        </template>
      </div>
    </div>
    <div v-if="isLeaf(device)" class="tariff-section">
      <div class="section-title">Tariff</div>
      <div class="form-grid">
        <label for="tariff">Assigned Tariff</label>
        <select id="tariff" v-model.number="selectedTariffId" :disabled="savingTariff || tariffsLoading || filteredTariffs.length === 0">
          <option :value="0">None</option>
          <option v-for="t in filteredTariffs" :key="t.id" :value="t.id">{{ t.name }} ({{ t.max_down_mbps }}/{{ t.max_up_mbps }})</option>
        </select>
        <div></div>
        <div><button class="btn sm" :disabled="savingTariff" @click="saveTariff">Save</button></div>
      </div>
      <div v-if="tariffError" class="field-error">{{ tariffError }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import type { DeviceOut } from '../../../types/domain'
import { useDeviceProps } from '../../../composables/useDeviceProps'
import { usePortSummary } from '../../../composables/usePortSummary'
import { useTariffsStore } from '../../../stores/tariffsStore'
import { useDevicesStore } from '../../../stores/devicesStore'
import { useToastStore } from '../../../stores/toastStore'

const props = defineProps<{ device: DeviceOut | null }>()
const devices = useDevicesStore()
const toasts = useToastStore()

// properties
const { deviceProps } = useDeviceProps(computed(() => props.device))

// ports - SIMPLIFIED: Direct fetch without manager/polling/caching complexity
const showPortsSection = computed(() => {
  const d = props.device
  if (!d) return false
  return ['OLT','AON_SWITCH','CORE_ROUTER','EDGE_ROUTER'].includes(String(d.type))
})
const deviceIdForPorts = computed(() => props.device?.id || '')
const { interfaces: portIfaces, loading: portsLoading, error: portsError } = usePortSummary(deviceIdForPorts)

// Enrich port summary with MAC addresses from device.interfaces
const deviceInterfaces = computed(() => {
  return Array.isArray(props.device?.interfaces) ? props.device.interfaces : []
})

type PortEntry = { id?: string; name?: string; role?: string; used: number; capacity: number; effective_status: string; mac?: string }
type PortGroup = { role: string; ports: PortEntry[] }
const portGroups = computed<PortGroup[]>(() => {
  if (!showPortsSection.value) return []
  const list = portIfaces.value
  const groups = new Map<string, PortEntry[]>()
  
  // Build MAC lookup from device interfaces
  const macLookup = new Map<string, string>()
  for (const iface of deviceInterfaces.value) {
    if (iface.id && iface.mac_address) {
      macLookup.set(iface.id, iface.mac_address)
    }
  }
  
  for (const i of list) {
    const role = String(i.port_role || 'OTHER').toUpperCase()
    if (!groups.has(role)) groups.set(role, [])
    groups.get(role)!.push({
      id: i.id || undefined,
      name: i.name || '',
      role,
      used: Number(i.occupancy ?? 0),
      capacity: i.capacity !== null && i.capacity !== undefined ? Number(i.capacity) : -1, // -1 = no fixed capacity
      effective_status: String(i.effective_status || 'UNKNOWN'),
      mac: i.id ? macLookup.get(i.id) : undefined,
    })
  }
  return Array.from(groups.entries()).map(([role, ports]) => ({ role, ports }))
})

// splitter usage
const splitterPortsText = computed(() => {
  const d = props.device as unknown as { parameters?: { splitter?: { ports_used?: number; ports_total?: number } } } | null
  const sp = d?.parameters?.splitter || {}
  const used = Number(sp.ports_used ?? 0)
  const total = Number(sp.ports_total ?? 0)
  if (!Number.isFinite(used) || !Number.isFinite(total) || total <= 0) return '-'
  return `[${used}/${total}]`
})

// tariffs
const tariffsStore = useTariffsStore()
const tariffs = computed(() => tariffsStore.allSorted)
const filteredTariffs = computed(() => {
  const d = props.device
  const all = tariffs.value
  if (!d) return all
  const t = d.type as string
  let tech: 'GPON' | 'AON' | null = null
  if (t === 'AON_CPE') tech = 'AON'
  if (t === 'ONT' || t === 'BUSINESS_ONT') tech = 'GPON'
  if (!tech) return all
  return all.filter(x => (x.technology ?? null) === tech)
})
const tariffsLoading = computed(() => tariffsStore.$state.loading)
const selectedTariffId = ref<number>(0)
const savingTariff = ref(false)
const tariffError = ref('')
watch(() => props.device, (d) => {
  const current = (d ? (d as Partial<DeviceOut>).tariff_id : null) as number | null | undefined
  selectedTariffId.value = current ?? 0
}, { immediate: true })
onMounted(() => { void tariffsStore.fetchAll() })
async function saveTariff() {
  const d = props.device
  if (!d) return
  savingTariff.value = true
  tariffError.value = ''
  try {
    const newId = selectedTariffId.value || null
    await devices.updateTariffOnly(d.id, newId)
    toasts.push('Tariff saved', 'success')
  } catch (e) {
    tariffError.value = (e as Error).message || 'Save failed'
    toasts.push(tariffError.value, 'error')
  } finally { savingTariff.value = false }
}

function isLeaf(d: DeviceOut | null): boolean {
  if (!d) return false
  return d.type === 'ONT' || d.type === 'BUSINESS_ONT' || d.type === 'AON_CPE'
}
</script>

<style scoped>
.properties { border-top:1px solid var(--color-border); padding-top:.6rem; font-size:.6rem; display:flex; flex-direction:column; gap:.6rem; }
.meta-list { display:flex; flex-direction:column; gap:.25rem; font-size:.65rem; }
.meta-list .row { display:grid; grid-template-columns:90px 1fr; gap:.35rem; }
.meta-list label { font-weight:600; text-transform:uppercase; letter-spacing:.4px; font-size:.55rem; color:var(--color-text-dim); }
.meta-list .row.warn span { color:#ffb74d; font-weight:600; }
.section-title { font-weight:600; font-size:.7rem; color:var(--color-text-dim); margin-bottom:.25rem; }
.ports-list { display:flex; flex-direction:column; gap:.3rem; }
.port-role { font-size:.55rem; font-weight:600; text-transform:uppercase; letter-spacing:.5px; opacity:.8; margin-top:.4rem; }
.port-entry { display:flex; gap:.35rem; align-items:center; font-size:.55rem; }
.port-name { font-weight:500; }
.port-occupancy { opacity:.75; }
.port-mac { opacity:.6; font-size:.5rem; }
.badge.status { font-size:.55rem; padding:.15rem .4rem; border-radius:999px; background:#333; }
.badge.status[data-status="UP"] { background:#1b5e20; color:#fff; }
.badge.status[data-status="DOWN"] { background:#b71c1c; color:#fff; }
.badge.status[data-status="DEGRADED"] { background:#ef6c00; color:#fff; }
.form-grid { display:grid; grid-template-columns:150px 1fr; gap:.35rem .5rem; margin-top:.4rem; }
.form-grid input, .form-grid select { background:#222; border:1px solid #444; color:#eee; padding:.25rem .4rem; font-size:.65rem; border-radius:4px; box-sizing:border-box; width:100%; max-width:100%; }
.btn { background:#2e2e2e; border:1px solid #555; color:#ddd; cursor:pointer; padding:.3rem .55rem; font-size:.6rem; border-radius:4px; }
.btn:hover { background:#424242; color:#fff; }
.btn.sm { font-size:.6rem; padding:.25rem .5rem; }
.field-error { grid-column:2 / span 1; color:#ef9a9a; font-size:.55rem; margin-top:-.2rem; }
</style>