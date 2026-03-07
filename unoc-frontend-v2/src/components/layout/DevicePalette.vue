<template>
  <div class="device-palette" @dragstart.stop>
    <header>
      <h3>Devices</h3>
      <button :disabled="devices.loading" @click="reload">↻</button>
    </header>
    <div v-if="devices.error" class="error">{{ devices.error }}</div>
    <div v-for="group in grouped" :key="group.label" class="group">
      <h4>{{ group.label }}</h4>
      <ul>
        <li
v-for="entry in group.items" :key="entry.type" draggable="true" @dragstart="onDragType(entry.type, $event)"
          @contextmenu.prevent="openBulk(entry.type, entry.display)">
          <span class="type-pill" :data-type="entry.type">{{ entry.display }}</span>
        </li>
      </ul>
    </div>
    <details>
      <summary>Quick Add</summary>
      <form @submit.prevent="quickCreate">
        <input v-model="newId" placeholder="id" required />
        <input v-model="newName" placeholder="name" required />
        <select v-model="newType">
          <option v-for="t in ALL_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model.number="newHardwareId">
          <option :value="null">(Auto default)</option>
          <option v-for="m in hardware.items.filter(m => m.device_type === newType)" :key="m.id" :value="m.id">{{
            m.catalog_id }}</option>
        </select>
        <button type="submit">Add</button>
      </form>
    </details>
    <template v-if="bulk.open">
      <ModalShell @cancel="cancelBulk">
        <template #title>Bulk Create – {{ bulk.typeLabel }} ({{ bulk.type }})</template>
        <div class="inline">
          <label style="flex:1">
            Anzahl
            <input
v-model.number="bulk.count" type="number" min="1" :max="bulk.limit" autofocus
              @change="validateBulk" />
          </label>
          <label style="flex:1">
            Hardware
            <select v-model.number="bulk.hardware_model_id">
              <option :value="null">(Auto default)</option>
              <option v-for="m in hardware.items.filter(m => m.device_type === bulk.type)" :key="m.id" :value="m.id">{{
                m.catalog_id }}</option>
            </select>
          </label>
          <label v-if="['OLT', 'AON_SWITCH'].includes(bulk.type)" style="flex:1">
            POP Parent (optional)
            <select v-model="bulk.parent" @change="validateBulk">
              <option :value="null">(optional)</option>
              <option v-for="p in devices.devices.filter(d => d.type === 'POP')" :key="p.id" :value="p.id">{{ p.id }}
              </option>
            </select>
          </label>
        </div>
        <div v-for="e in bulk.errors" :key="e" class="error">{{ e }}</div>
        <template #footer>
          <button :disabled="bulk.creating" @click="cancelBulk">Abbrechen</button>
          <button data-primary :disabled="bulk.creating || !!bulk.errors.length" @click="performBulk">{{ bulk.creating ?
            'Erstelle…' : 'Erstellen' }}</button>
        </template>
      </ModalShell>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useDevicesStore } from '../../stores/devicesStore'
import { useToastStore } from '../../stores/toastStore'
import ModalShell from '../ui/ModalShell.vue'
import { generateBulkPositions } from '../../logic/bulkPlacement.js'
import { useHardwareStore } from '../../stores/hardwareStore'

const devices = useDevicesStore()
const toasts = useToastStore()
const hardware = useHardwareStore()
const newId = ref('')
const newName = ref('')
const newType = ref('POP')
const newHardwareId = ref<number | null>(null)
// Architecture-aligned palette groups
type PaletteGroup = { label: string; items: { type: string; display: string }[] }
const GROUPS: PaletteGroup[] = [
  {
    label: 'Backbone & Core', items: [
      { type: 'BACKBONE_GATEWAY', display: 'Backbone Gateway' },
      { type: 'CORE_ROUTER', display: 'Core Router' },
      { type: 'EDGE_ROUTER', display: 'Edge Router' }
    ]
  },
  {
    label: 'Zentrale & POP (Container)', items: [
      { type: 'POP', display: 'POP' },
      { type: 'CORE_SITE', display: 'Core Site' }
    ]
  },
  {
    label: 'Access Network (Aktiv)', items: [
      { type: 'OLT', display: 'OLT' },
      { type: 'AON_SWITCH', display: 'AON Switch' }
    ]
  },
  {
    label: 'Verteilnetz (Passiv)', items: [
      { type: 'ODF', display: 'ODF' },
      { type: 'NVT', display: 'NVt' },
      { type: 'SPLITTER', display: 'Splitter' },
      { type: 'HOP', display: 'HOP' }
    ]
  },
  {
    label: 'Anschlussnetz / Endgeräte', items: [
      { type: 'ONT', display: 'ONT' },
      { type: 'BUSINESS_ONT', display: 'Business ONT' },
      { type: 'AON_CPE', display: 'AON CPE' }
    ]
  }
]
const ALL_TYPES = GROUPS.flatMap(g => g.items.map(i => i.type))
const grouped = computed(() => GROUPS)

function reload() { devices.fetchAll() }
async function quickCreate() {
  await devices.create({ id: newId.value, name: newName.value, type: newType.value, hardware_model_id: newHardwareId.value ?? undefined })
  newId.value = ''; newName.value = ''; newHardwareId.value = null
}

function onDragType(t: string, ev: DragEvent) {
  ev.dataTransfer?.setData('application/x-unoc-device-type', t)
  ev.dataTransfer?.setData('text/plain', t)
  ev.dataTransfer!.effectAllowed = 'copy'
}

interface BulkState { open: boolean; type: string; typeLabel: string; count: number; parent: string | null; creating: boolean; limit: number; errors: string[]; hardware_model_id: number | null }
const bulk = reactive<BulkState>({ open: false, type: '', typeLabel: '', count: 10, parent: null, creating: false, limit: 500, errors: [], hardware_model_id: null })

function openBulk(type: string, label: string) {
  bulk.open = true
  bulk.type = type
  bulk.typeLabel = label
  bulk.count = 10
  bulk.parent = null
  bulk.errors = []
  bulk.hardware_model_id = null
  if (['OLT', 'AON_SWITCH'].includes(type)) {
    const pops = devices.devices.filter(d => d.type === 'POP')
    if (pops.length === 1) bulk.parent = pops[0].id
  }
  // Preload hardware models for this device type
  hardware.fetchAll(type)
}

function validateBulk(): boolean {
  const errs: string[] = []
  const c = bulk.count
  if (!Number.isInteger(c) || c < 1) errs.push('Count muss >=1 sein')
  if (c > bulk.limit) errs.push(`Maximal ${bulk.limit}`)
  if (['OLT', 'AON_SWITCH'].includes(bulk.type)) {
    const pops = devices.devices.filter(d => d.type === 'POP')
    // Parent is optional; only warn if user selected a non-existent parent
    if (bulk.parent && !pops.some(p => p.id === bulk.parent)) errs.push('Gewählter POP existiert nicht')
    if (pops.length === 0) errs.push('Kein POP vorhanden')
  }
  bulk.errors = errs
  return errs.length === 0
}

async function performBulk() {
  if (bulk.creating) return
  if (!validateBulk()) return
  bulk.creating = true
  const startTs = Date.now()
  const count = bulk.count
  const type = bulk.type
  const parent = bulk.parent
  const toastId = toasts.pending(`Erstelle ${count} ${type}…`)
  const width = window.innerWidth - 320
  const height = window.innerHeight - 40
  const positions = generateBulkPositions({ count, width, height })
  const createdIds: string[] = []
  let failures = 0
  for (let i = 0; i < count; i++) {
    const idBase = type.toLowerCase()
    let id = `${idBase}_${(i + 1).toString().padStart(3, '0')}`
    let k = 1
    while (devices.devices.some(d => d.id === id) || createdIds.includes(id)) {
      id = `${idBase}_${(i + 1)}_${k++}`
    }
    try {
      await devices.create({ id, name: id, type, parent_container_id: parent || undefined, hardware_model_id: bulk.hardware_model_id ?? undefined })
      createdIds.push(id)
    } catch { failures++ }
  }
  try {
    if (createdIds.length) {
      const posPayload = createdIds.map((cid, idx) => ({ id: cid, x: positions[idx].x, y: positions[idx].y, userPinned: true }))
      await fetch('/api/layout/positions', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ positions: posPayload }) })
    }
  } catch { /* ignore layout position failure in bulk */ }
  const dur = ((Date.now() - startTs) / 1000).toFixed(1)
  toasts.replace(
    toastId,
    failures ? `${createdIds.length} ok, ${failures} Fehler (${dur}s)` : `${createdIds.length} erstellt (${dur}s)`,
    failures ? 'warn' : 'success',
    createdIds.length
      ? { action: { label: 'Undo', run: async () => { for (const id of createdIds) { try { await devices.remove(id) } catch { /* ignore */ } } toasts.push(`${createdIds.length} entfernt (Undo)`, 'info') } } }
      : undefined
  )
  bulk.creating = false
  bulk.open = false
}
function cancelBulk() { if (!bulk.creating) bulk.open = false }

onMounted(() => { devices.fetchAll(); hardware.fetchAll(newType.value) })
watch(newType, (t) => { hardware.fetchAll(t) })
</script>

<style scoped>
.device-palette {
  display: flex;
  flex-direction: column;
  gap: .5rem;
}

header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.group {
  margin-bottom: .25rem;
}

.group h4 {
  margin: .25rem 0 .1rem;
  font-size: .7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .5px;
  color: var(--color-text-dim);
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: .25rem;
}

li {
  cursor: grab;
}

li:active {
  cursor: grabbing;
}

.type-pill {
  background: var(--color-bg-accent);
  border: 1px solid var(--color-border);
  padding: .15rem .35rem;
  border-radius: 3px;
  font-size: .65rem;
}

.error {
  color: red;
  font-size: .8rem;
}

form {
  display: flex;
  gap: .25rem;
  flex-wrap: wrap;
  margin-top: .25rem;
}

input,
select {
  font-size: .7rem;
  padding: .2rem .3rem;
}

button {
  font-size: .7rem;
}

details {
  margin-top: .25rem;
}
</style>
