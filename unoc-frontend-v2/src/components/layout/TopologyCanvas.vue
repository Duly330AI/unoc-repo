<template>
  <div
class="canvas-wrapper"
    :class="{ 'link-tool-active': linkTool.active, 'multi-link-mode': linkTool.active && linkTool.mode === 'multi' }"
    @dragover.prevent @drop="onDrop" @click.self="selection.clear()" @contextmenu.self.prevent="onCanvasContextMenu">
    <svg ref="svgRef" class="topology-canvas" width="100%" height="100%" @contextmenu.prevent="onCanvasContextMenu">
      <defs>
        <radialGradient id="popHalo" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#2196f3" stop-opacity="0.55" />
          <stop offset="60%" stop-color="#1e88e5" stop-opacity="0.25" />
          <stop offset="100%" stop-color="#1976d2" stop-opacity="0" />
        </radialGradient>
      </defs>
      <g ref="zoomRoot">
        <g class="links-layer"></g>
        <g class="halos-layer"></g>
        <g class="nodes-layer"></g>
        <g class="labels-layer"></g>
      </g>
    </svg>
    <svg v-if="ghosts.length" ref="ghostLayerRef" class="ghost-layer" width="100%" height="100%">
      <circle
v-for="g in ghosts" :key="g.localId" class="ghost-device" :cx="g.x" :cy="g.y" r="20"
        :fill="ghostFill(g.type)" />
    </svg>
    <div v-if="selection.items.length" class="selection-hud">
      <span v-if="selection.items.length === 1">1 item selected</span>
      <span v-else>{{ selection.items.length }} items selected</span>
    </div>
    <div v-if="linkTool.active && linkTool.mode !== 'multi'" class="mode-hud">Link Tool aktiv – 1. Knoten klicken, 2.
      Ziel klicken (Esc abbrechen, K beenden)</div>
    <div v-else-if="linkTool.active && linkTool.mode === 'multi'" class="mode-hud">
      Multi-Link Target Mode – Zielgerät klicken, um {{selection.items.filter(i => i.kind === 'device').length}} Links zu
      erstellen (Esc/K beenden)
    </div>
    <button class="force-layout-btn" title="Unpinned automatisch neu anordnen" @click="forceLayout()">Auto
      Layout</button>

    <!-- Hardware selection modal for drag-and-drop -->
    <ModalShell v-if="hw.open" @cancel="onHwCancel">
      <template #title>Hardware auswählen – {{ hw.ctx?.type }}</template>
      <div class="hw-form">
        <div>
          <label>Geräte-ID</label>
          <input :value="hw.ctx?.suggestedId" disabled />
        </div>
        <div>
          <label>Hardware</label>
          <select v-model="hw.selectedRaw">
            <option value="">(Auto default)</option>
            <option v-for="m in hardware.items" :key="m.id" :value="String(m.id)">
              {{ m.catalog_id }} — {{ m.vendor || '-' }} {{ m.model || '' }}
            </option>
          </select>
        </div>
      </div>
      <template #footer>
        <button @click="onHwCancel">Abbrechen</button>
        <button data-primary @click="onHwConfirm">Erstellen</button>
      </template>
    </ModalShell>

    <!-- Link selection modal -->
    <ModalShell v-if="linkSel.open" @cancel="onLinkCancel">
      <template #title>Link erstellen – Ports wählen</template>
      <div class="link-form">
        <div class="row">
          <div class="col">
            <label>Quelle</label>
            <div class="dev-id">{{ linkSel.aDeviceId }}</div>
            <select v-model="linkSel.aSelected">
              <option v-for="o in linkSel.aOptions" :key="o.id" :value="o.id">{{ o.label }}</option>
            </select>
          </div>
          <div class="col">
            <label>Ziel</label>
            <div class="dev-id">{{ linkSel.bDeviceId }}</div>
            <select v-model="linkSel.bSelected">
              <option v-for="o in linkSel.bOptions" :key="o.id" :value="o.id">{{ o.label }}</option>
            </select>
          </div>
        </div>
      </div>
      <template #footer>
        <button @click="onLinkCancel">Abbrechen</button>
        <button data-primary @click="onLinkConfirm">Erstellen</button>
      </template>
    </ModalShell>

    <!-- Container proxy target modal -->
    <LinkProxyModal />
  </div>
</template>

<script setup lang="ts">
/* Slimmed component: heavy logic moved to useTopologyCanvasCore */
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { useDevicesStore } from '../../stores/devicesStore'
import { useSelectionStore } from '../../stores/selectionStore'
import { useLinksStore } from '../../stores/linksStore'
import { useToastStore } from '../../stores/toastStore'
import { useTopologyCanvasCore } from '../../composables/useTopologyCanvasCore'
import ModalShell from '../ui/ModalShell.vue'
import LinkProxyModal from './LinkProxyModal.vue'
import { useHardwareStore } from '../../stores/hardwareStore'

const devices = useDevicesStore()
const selection = useSelectionStore()
const linksStore = useLinksStore()
const toasts = useToastStore()
const hardware = useHardwareStore()

const svgRef = ref<SVGSVGElement | null>(null)
const zoomRoot = ref<SVGGElement | null>(null)
const ghostLayerRef = ref<SVGSVGElement | null>(null)

const core = useTopologyCanvasCore({ svgRef, zoomRoot, ghostLayerRef, devices, linksStore, selection, toasts })
const { ghosts, linkTool, onDrop, forceLayout, ghostFill, init, destroy, onCanvasContextMenu } = core

// Hardware selection modal state and handlers
type HwCtx = { type: string; suggestedId: string; screen: { x: number; y: number }; graph: { x: number; y: number }; parentId: string | null }
type HwEventDetail = { ctx: HwCtx; confirm: (id: number | null) => Promise<void>; cancel: () => void }
const hw = reactive<{ open: boolean; ctx: HwCtx | null; selectedRaw: string; confirm?: (id: number | null) => Promise<void>; cancel?: () => void }>({ open: false, ctx: null, selectedRaw: '' })

function attachHwListener() {
  const handler = async (e: CustomEvent<HwEventDetail>) => {
    const detail = e.detail
    hw.ctx = detail.ctx
    hw.confirm = detail.confirm
    hw.cancel = detail.cancel
    hw.selectedRaw = ''
    hw.open = true
    // Load models for this type and preselect default if present
    await hardware.fetchAll(hw.ctx.type)
    // Keep blank selection to let backend auto-assign default. If API later exposes default, preselect that here.
  }
  const listener = (e: Event) => handler(e as CustomEvent<HwEventDetail>)
  window.addEventListener('unoc:openHardwareSelector', listener)
  return () => window.removeEventListener('unoc:openHardwareSelector', listener)
}

async function onHwConfirm() {
  if (!hw.confirm) { hw.open = false; return }
  const id = hw.selectedRaw ? Number(hw.selectedRaw) : null
  const confirm = hw.confirm
  hw.open = false
  try {
    await confirm(id)
  } catch (e) {
    const msg = (e as Error)?.message || 'Geräteerstellung fehlgeschlagen'
    toasts.push(msg, 'error')
  }
}
function onHwCancel() {
  if (hw.cancel) hw.cancel()
  hw.open = false
}

onMounted(() => { init(); const detach = attachHwListener(); onUnmounted(() => detach()) })
onUnmounted(() => destroy())

// Link selection modal state and handlers
type LinkSelDetail = {
  aDeviceId: string
  bDeviceId: string
  aSelected: string
  bSelected: string
  aOptions: Array<{ id: string; label: string }>
  bOptions: Array<{ id: string; label: string }>
  confirm: (a: string, b: string) => Promise<void>
  cancel: () => void
}
const linkSel = reactive<{
  open: boolean
  aDeviceId: string
  bDeviceId: string
  aSelected: string
  bSelected: string
  aOptions: Array<{ id: string; label: string }>
  bOptions: Array<{ id: string; label: string }>
  confirm?: (a: string, b: string) => Promise<void>
  cancel?: () => void
}>({ open: false, aDeviceId: '', bDeviceId: '', aSelected: '', bSelected: '', aOptions: [], bOptions: [] })

function attachLinkListener() {
  const handler = (e: CustomEvent<LinkSelDetail>) => {
    const d = e.detail
    linkSel.aDeviceId = d.aDeviceId
    linkSel.bDeviceId = d.bDeviceId
    linkSel.aSelected = d.aSelected
    linkSel.bSelected = d.bSelected
    linkSel.aOptions = d.aOptions
    linkSel.bOptions = d.bOptions
    linkSel.confirm = d.confirm
    linkSel.cancel = d.cancel
    linkSel.open = true
  }
  const listener = (e: Event) => handler(e as CustomEvent<LinkSelDetail>)
  window.addEventListener('unoc:openLinkSelector', listener)
  return () => window.removeEventListener('unoc:openLinkSelector', listener)
}

async function onLinkConfirm() {
  if (!linkSel.confirm) { linkSel.open = false; return }
  const confirm = linkSel.confirm
  const a = linkSel.aSelected
  const b = linkSel.bSelected
  linkSel.open = false
  try {
    await confirm(a, b)
    toasts.push('Link erstellt', 'success')
  } catch (e) {
    const msg = (e as Error)?.message || 'Link-Erstellung fehlgeschlagen'
    toasts.push(msg, 'error')
  }
}
function onLinkCancel() {
  if (linkSel.cancel) linkSel.cancel()
  linkSel.open = false
}

// Attach both listeners on mount
onMounted(() => { const detachLink = attachLinkListener(); onUnmounted(() => detachLink()) })
</script>

<style scoped>
.canvas-wrapper {
  position: relative;
  background: var(--color-bg);
  width: 100%;
  height: 100%;
}

.link-form .row { display: flex; gap: 16px; }
.link-form .col { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.link-form label { font-weight: 600; }
.link-form .dev-id { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; opacity: .8; }


.canvas-wrapper.link-tool-active {
  cursor: crosshair;
}

.canvas-wrapper.multi-link-mode {
  cursor: copy;
}

.topology-canvas {
  width: 100%;
  height: 100%;
  background: var(--color-bg-accent);
  user-select: none;
}

:deep(line.link) {
  stroke: #999;
  stroke-width: 2;
  opacity: .9;
  transition: stroke .2s, stroke-dasharray .2s, filter .2s;
  cursor: pointer;
}

:deep(line.link.hover),
:deep(line.link:hover) {
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, .25));
}

:deep(line.link[data-selected='1']) {
  stroke: #ffb300 !important;
  filter: drop-shadow(0 0 4px rgba(255, 179, 0, .55));
}

line.link-status-up {
  stroke: #4caf50;
}

line.link-status-down {
  stroke: #d32f2f;
  stroke-dasharray: 4 4;
}

line.link-status-degraded {
  stroke: #ff9800;
  stroke-dasharray: 6 4;
}

line.link-status-unknown {
  stroke: #9e9e9e;
  stroke-dasharray: 2 6;
}

:deep(line.link-kind-backbone) {
  stroke-width: 3;
}

:deep(line.link-kind-access) {
  stroke-width: 2;
}

:deep(line.link-kind-cpe) {
  stroke: #607d8b;
}

:deep(line.link-preview) {
  stroke: #42a5f5;
  stroke-width: 2;
  stroke-dasharray: 4 4;
  opacity: .8;
}

g.device-node {
  cursor: pointer;
  transition: filter .15s;
}

/* Back-compat attribute selector + new class-based selection highlight */
/* Use :deep so rules apply to D3-created nodes that don't get the Vue scope attribute */
:deep(g.device-node[data-selected='1']),
:deep(g.device-node.selected) {
  filter: drop-shadow(0 0 6px rgba(255, 193, 7, .85)) drop-shadow(0 0 2px rgba(255, 193, 7, .6));
}

/* Stronger effect when multi-select is active */
:deep(g.device-node.selected[data-multi='1']),
:deep(g.device-node[data-selected='1'][data-multi='1']) {
  filter: drop-shadow(0 0 8px rgba(255, 193, 7, .95)) drop-shadow(0 0 4px rgba(255, 193, 7, .75));
}

.node-label[data-pinned='1'] {
  font-weight: 600;
}

.node-label {
  font-family: var(--font-mono, monospace);
}

.cockpit-root,
.cockpit-root * {
  pointer-events: all;
}

.ghost-layer {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
}

circle.ghost-device {
  stroke: #555;
  stroke-width: 2;
  stroke-dasharray: 4 4;
  fill-opacity: .4;
}

circle.device[data-selected='1'][data-multi='1'] {
  stroke-width: 4;
}

.selection-hud {
  position: absolute;
  top: .35rem;
  left: .4rem;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  font-size: .65rem;
  padding: .25rem .4rem;
  border-radius: 4px;
  pointer-events: none;
  letter-spacing: .5px;
}

.mode-hud {
  position: absolute;
  top: 0.35rem;
  right: 0.5rem;
  background: rgba(66, 66, 66, .75);
  color: #fff;
  font-size: .6rem;
  padding: .25rem .5rem;
  border-radius: 4px;
  letter-spacing: .5px;
  pointer-events: none;
}

.force-layout-btn {
  position: absolute;
  bottom: .5rem;
  left: .5rem;
  background: #263238;
  color: #ddd;
  border: 1px solid #37474f;
  font-size: .6rem;
  padding: .35rem .55rem;
  border-radius: 4px;
  cursor: pointer;
  letter-spacing: .5px;
}

.force-layout-btn:hover {
  background: #37474f;
  color: #fff;
}

.hw-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .75rem;
}

.hw-form label {
  display: block;
  font-size: .75rem;
  color: var(--color-text-dim);
  margin-bottom: .25rem;
}

.hw-form input,
.hw-form select {
  width: 100%;
  padding: .3rem .4rem;
  font-size: .8rem;
}

/* Cockpit now renders halos/rings internally when needed */
</style>
