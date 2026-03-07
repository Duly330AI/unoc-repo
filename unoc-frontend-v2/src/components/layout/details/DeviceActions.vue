<template>
  <div class="actions">
    <template v-if="!renaming">
      <button class="btn sm" @click="startRename">Rename</button>
      <button class="btn sm danger" @click="deleteDevice">Delete</button>
      <button v-if="canProvision" class="btn sm primary" :disabled="provisioning" @click="emitProvision">{{ provisioning ? '…' : 'Provision' }}</button>
      <span class="spacer"></span>
      <button class="btn sm" :disabled="overrideWorking" @click="forceDown">Force DOWN</button>
      <button class="btn sm secondary" :disabled="overrideWorking || !device?.admin_override_status" @click="clearOverride">Clear Override</button>
    </template>
    <div v-else class="rename-inline">
      <input v-model="newName" @keyup.enter="commitRename" @keyup.esc="cancelRename" />
      <button class="btn sm" @click="commitRename">OK</button>
      <button class="btn sm secondary" @click="cancelRename">Abbruch</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { DeviceOut } from '../../../types/domain'
import { useDevicesStore } from '../../../stores/devicesStore'
import { useSelectionStore } from '../../../stores/selectionStore'
import { useToastStore } from '../../../stores/toastStore'

const props = defineProps<{ device: DeviceOut | null; provisioning: boolean; canProvision: boolean; onProvision?: () => Promise<void> | void }>()

const devices = useDevicesStore()
const selection = useSelectionStore()
const toasts = useToastStore()

// rename state
const renaming = ref(false)
const newName = ref('')
function startRename() { if (!props.device) return; renaming.value = true; newName.value = props.device.name }
async function commitRename() {
  if (!props.device) return
  const trimmed = newName.value.trim()
  if (trimmed && trimmed !== props.device.name) {
    try { await devices.update(props.device.id, { name: trimmed }) } catch (e) { console.warn('Rename failed', e) }
  }
  renaming.value = false
}
function cancelRename() { renaming.value = false }

async function deleteDevice() {
  if (!props.device) return
  if (!confirm(`Gerät wirklich löschen? ${props.device.name || props.device.id}`)) return
  try { await devices.remove(props.device.id); selection.clear() } catch (e) { console.warn('Delete failed', e) }
}

// admin override
const overrideWorking = ref(false)
async function forceDown() {
  if (!props.device) return
  overrideWorking.value = true
  try { await devices.setOverride(props.device.id, 'DOWN'); toasts.push('Override set: DOWN', 'success') } catch (e) {
    toasts.push((e as Error)?.message || 'Override failed', 'error')
  } finally { overrideWorking.value = false }
}
async function clearOverride() {
  if (!props.device) return
  overrideWorking.value = true
  try { await devices.setOverride(props.device.id, null); toasts.push('Override cleared', 'success') } catch (e) {
    toasts.push((e as Error)?.message || 'Override clear failed', 'error')
  } finally { overrideWorking.value = false }
}

function emitProvision() { if (props.onProvision) { void props.onProvision() } }
</script>

<style scoped>
.actions { border-top:1px solid var(--color-border); padding-top:.5rem; display:flex; gap:.4rem; flex-wrap:wrap; }
.btn { background:#2e2e2e; border:1px solid #555; color:#ddd; cursor:pointer; padding:.3rem .55rem; font-size:.6rem; border-radius:4px; }
.btn:hover { background:#424242; color:#fff; }
.btn.danger { background:#7f1d1d; border-color:#a72828; color:#fff; }
.btn.danger:hover { background:#b91c1c; }
.btn.primary { background:#14532d; border-color:#1d7a43; color:#fff; }
.btn.primary:hover { background:#1d7a43; }
.btn.secondary { background:#3a3a3a; }
.btn.secondary:hover { background:#4a4a4a; }
.btn.sm { font-size:.6rem; padding:.25rem .5rem; }
.spacer { display:inline-block; width:.35rem; }
.rename-inline { display:flex; gap:.35rem; align-items:center; flex-wrap:wrap; }
.rename-inline input { background:#222; border:1px solid #444; color:#eee; padding:.25rem .4rem; font-size:.65rem; border-radius:4px; }
</style>