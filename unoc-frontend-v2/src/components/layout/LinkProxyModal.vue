<template>
  <ModalShell v-if="state.open" @cancel="onCancel">
    <template #title>Link-Ziel im Container wählen</template>
    <div class="proxy-form">
      <div class="row">
        <div class="col">
          <label>Quelle</label>
          <div class="dev-id">{{ state.sourceId }}</div>
        </div>
        <div class="col">
          <label>Container</label>
          <div class="dev-id">{{ state.containerId }}</div>
        </div>
      </div>
      <div class="row">
        <div class="col">
          <label>Inneres Zielgerät</label>
          <select v-model="state.selected">
            <option v-for="c in state.candidates" :key="c.id" :value="c.id">{{ c.label }}</option>
          </select>
        </div>
      </div>
    </div>
    <template #footer>
      <button @click="onCancel">Abbrechen</button>
      <button data-primary @click="onConfirm">Erstellen</button>
    </template>
  </ModalShell>
</template>

<script setup lang="ts">
import { reactive, onMounted, onUnmounted } from 'vue'
import ModalShell from '../ui/ModalShell.vue'

type Candidate = { id: string; label: string }

type ProxySelDetail = {
  sourceId: string
  containerId: string
  candidates: Candidate[]
  preselectId: string | null
  confirm: (targetId: string | null) => Promise<void>
  cancel: () => void
}

const state = reactive<{
  open: boolean
  sourceId: string
  containerId: string
  candidates: Candidate[]
  selected: string | null
  confirm?: (targetId: string | null) => Promise<void>
  cancel?: () => void
}>({ open: false, sourceId: '', containerId: '', candidates: [], selected: null })

function attachListener() {
  const handler = (e: CustomEvent<ProxySelDetail>) => {
    const d = e.detail
    state.sourceId = d.sourceId
    state.containerId = d.containerId
    state.candidates = d.candidates
    state.selected = d.preselectId
    state.confirm = d.confirm
    state.cancel = d.cancel
    state.open = true
  }
  const listener = (e: Event) => handler(e as CustomEvent<ProxySelDetail>)
  window.addEventListener('unoc:openLinkProxySelector', listener)
  return () => window.removeEventListener('unoc:openLinkProxySelector', listener)
}

function onCancel() {
  if (state.cancel) state.cancel()
  state.open = false
}

async function onConfirm() {
  if (!state.confirm) { state.open = false; return }
  const fn = state.confirm
  const chosen = state.selected
  state.open = false
  await fn(chosen)
}

onMounted(() => { const detach = attachListener(); onUnmounted(() => detach()) })
</script>

<style scoped>
.proxy-form .row { display: flex; gap: 16px; }
.proxy-form .col { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.proxy-form label { font-weight: 600; }
.dev-id { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; opacity: .8; }
</style>
