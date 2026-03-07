<template>
  <div class="optical-section">
    <div class="section-title">Optical</div>

    <!-- Status chips -->
    <div class="meta-list">
      <div class="row">
        <label>Status</label>
        <span>
          <span class="chip signal" :data-signal="deviceEx.signal_status || 'NO_SIGNAL'">
            {{ deviceEx.signal_status || 'NO_SIGNAL' }}
          </span>
        </span>
      </div>
      <div class="row"><label>Power</label><span>{{ fmtDbm(deviceEx.signal_power_dbm) }}</span></div>
      <div class="row"><label>Margin</label><span>{{ fmtDb(deviceEx.signal_margin_db) }}</span></div>
      <div class="row"><label>Attenuation</label><span>{{ fmtDb(deviceEx.total_path_attenuation_db) }}</span></div>
    </div>

    <!-- Editable params -->
  <div v-if="canUpdate" class="form-grid">
      <!-- OLT: TX Power -->
      <template v-if="isOlt(device)">
        <label for="tx">TX Power</label>
  <input id="tx" v-model.number="txPower" type="number" step="0.1" placeholder="dBm" />
      </template>

      <!-- ONT: Sensitivity -->
      <template v-if="isOnt(device)">
        <label for="sens">Sensitivity (min)</label>
  <input id="sens" v-model.number="sensitivity" type="number" step="0.1" placeholder="dBm" />
      </template>

      <!-- Passive Optical: Insertion loss -->
      <template v-if="isPassiveOptical(device)">
        <label for="il">Insertion loss</label>
  <input id="il" v-model.number="insertionLoss" type="number" step="0.1" placeholder="dB" />
        <div v-if="insertionLossInvalid" class="field-error">Insertion loss must be ≥ 0</div>
      </template>

      <div></div>
      <div>
        <button class="btn sm" :disabled="saving || insertionLossInvalid" @click="save">Save</button>
      </div>
      <div v-if="error" class="field-error">{{ error }}</div>
    </div>
  </div>
  
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DeviceOut } from '../../../types/domain'
import { useDevicesStore } from '../../../stores/devicesStore'
import { useToastStore } from '../../../stores/toastStore'

const props = defineProps<{ device: DeviceOut | null }>()
const devices = useDevicesStore()
const toasts = useToastStore()

type DeviceWithOptical = DeviceOut & {
  signal_status?: 'OK' | 'WARNING' | 'CRITICAL' | 'NO_SIGNAL' | null
  signal_power_dbm?: number | null
  signal_margin_db?: number | null
  tx_power_dbm?: number | null
  sensitivity_min_dbm?: number | null
  total_path_attenuation_db?: number | null
  insertion_loss_db?: number | null
}

const deviceEx = computed(() => (props.device ?? {}) as DeviceWithOptical)
const canUpdate = computed(() => !!props.device)

function isOnt(d: DeviceOut | null): boolean { return !!d && (d.type === 'ONT' || d.type === 'BUSINESS_ONT') }
function isOlt(d: DeviceOut | null): boolean { return !!d && d.type === 'OLT' }
function isPassiveOptical(d: DeviceOut | null): boolean {
  return !!d && (d.type === 'SPLITTER' || d.type === 'HOP' || d.type === 'NVT' || d.type === 'ODF')
}

function fmtDbm(v?: number | null) { return v == null ? '—' : `${v.toFixed(2)} dBm` }
function fmtDb(v?: number | null) { return v == null ? '—' : `${v.toFixed(2)} dB` }

// Local edit state
const txPower = ref<number | null>(null)
const sensitivity = ref<number | null>(null)
const insertionLoss = ref<number | null>(null)
const saving = ref(false)
const error = ref('')
const insertionLossInvalid = computed(() => insertionLoss.value != null && insertionLoss.value < 0)

watch(() => props.device, (d) => {
  txPower.value = (d as DeviceWithOptical | null)?.tx_power_dbm ?? null
  sensitivity.value = (d as DeviceWithOptical | null)?.sensitivity_min_dbm ?? null
  insertionLoss.value = (d as DeviceWithOptical | null)?.insertion_loss_db ?? null
  error.value = ''
}, { immediate: true })

async function save() {
  const d = props.device
  if (!d) return
  const patch: Record<string, unknown> = {}
  if (isOlt(d) && txPower.value != null) patch.tx_power_dbm = txPower.value
  if (isOnt(d) && sensitivity.value != null) patch.sensitivity_min_dbm = sensitivity.value
  if (isPassiveOptical(d) && insertionLoss.value != null) patch.insertion_loss_db = insertionLoss.value
  if (Object.keys(patch).length === 0) return
  saving.value = true
  error.value = ''
  try {
    await devices.update(d.id, patch as { tx_power_dbm?: number; sensitivity_min_dbm?: number; insertion_loss_db?: number })
    toasts.push('Optical parameters saved', 'success')
  } catch (e) {
    error.value = (e as Error)?.message || 'Save failed'
    toasts.push(error.value, 'error')
  } finally {
    saving.value = false
  }
}
</script>

<!-- styles provided by parent DetailsPanel.css -->