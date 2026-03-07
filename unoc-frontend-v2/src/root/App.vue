<template>
  <AppLayout>
    <header class="topbar">
      <div class="brand">UNOC v3</div>
      <nav class="nav-tabs">
        <button
:class="['tab', { active: viewMode.current === 'topology' }]"
          @click="viewMode.set('topology')">Topologie</button>
        <button
:class="['tab', { active: viewMode.current === 'metrics' }]"
          @click="viewMode.set('metrics')">Metrics</button>
        <button :class="['tab', { active: viewMode.current === 'ipam' }]" @click="viewMode.set('ipam')">IPAM</button>
        <button
:class="['tab', { active: viewMode.current === 'tariffs' }]"
          @click="viewMode.set('tariffs')">Tariffs</button>
        <button
:class="['tab', { active: viewMode.current === 'hardware' }]"
          @click="viewMode.set('hardware')">Hardware</button>
        <button :class="['tab', { active: viewMode.current === 'debug' }]" @click="viewMode.set('debug')">Debug</button>
      </nav>
      <button class="hud-toggle" @click="hud.toggleVisible()">?</button>
    </header>
    <div v-if="viewMode.current === 'topology'" class="workspace">
      <Sidebar />
      <TopologyCanvas />
      <DetailsPanel />
    </div>
    <div v-else-if="viewMode.current === 'tariffs'" class="workspace placeholder">
      <div class="tariffs-wrapper">
        <TariffsPage />
      </div>
    </div>
    <div v-else-if="viewMode.current === 'ipam'" class="workspace placeholder">
      <div class="ipam-wrapper">
        <IpamTab />
      </div>
    </div>
    <div v-else-if="viewMode.current === 'metrics'" class="workspace placeholder">
      <div class="metrics-wrapper">
        <MetricsPage />
      </div>
    </div>
    <div v-else-if="viewMode.current === 'hardware'" class="workspace placeholder">
      <div class="hardware-wrapper">
        <HardwarePage />
      </div>
    </div>
    <div v-else-if="viewMode.current === 'debug'" class="workspace placeholder">
      <div class="debug-wrapper">
        <DebugPage />
      </div>
    </div>
    <div v-else class="workspace placeholder">
      <div class="placeholder-center">Unknown view</div>
    </div>
  </AppLayout>
  <InteractionHud />
  <SpinnerOverlay />
  <Toasts />
  <QuickToolbar />
  <ContextMenuMount />
  <Tooltip />
</template>

<script setup lang="ts">
import AppLayout from '../components/layout/AppLayout.vue'
import Sidebar from '../components/layout/Sidebar.vue'
import DetailsPanel from '../components/layout/DetailsPanel.vue'
import TopologyCanvas from '../components/layout/TopologyCanvas.vue'
import { useViewModeStore } from '../stores/viewModeStore'
import InteractionHud from '../components/ui/InteractionHud.vue'
import SpinnerOverlay from '../components/ui/SpinnerOverlay.vue'
import Toasts from '../components/ui/Toasts.vue'
import QuickToolbar from '../components/ui/QuickToolbar.vue'
import ContextMenuMount from '../components/layout/ContextMenuMount.vue'
import Tooltip from '../components/ui/Tooltip.vue'
import IpamTab from '../components/ipam/IpamTab.vue'
import TariffsPage from '../pages/TariffsPage.vue'
import MetricsPage from '../pages/MetricsPage.vue'
import HardwarePage from '../pages/HardwarePage.vue'
import DebugPage from '../pages/DebugPage.vue'
import { useInteractionHudStore } from '../stores/interactionHudStore'
import { onMounted } from 'vue'
import { useHardwareStore } from '../stores/hardwareStore'
import { useTooltipStore } from '../stores/tooltipStore'

const viewMode = useViewModeStore()
// DEV flag is set in main.ts but not used for tab gating in this hotfix
const hud = useInteractionHudStore()

// Ensure tooltip is reset on app mount to avoid any ghost overlay on initial paint
const tooltip = useTooltipStore()
onMounted(() => {
  tooltip.reset()
  // Load hardware catalog once on app start so device creation and link flows have data
  const hardware = useHardwareStore()
  hardware.init()
})
</script>

<style scoped>
.topbar {
  background: #1e1e1e;
  color: #fff;
  padding: 0 var(--sp-6);
  font-size: var(--fs-md);
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.brand {
  font-weight: 600;
  letter-spacing: .5px;
}

.nav-tabs {
  display: flex;
  gap: .25rem;
}

.tab {
  background: transparent;
  border: 0;
  color: #bbb;
  padding: .45rem .9rem;
  cursor: pointer;
  font-size: .75rem;
  letter-spacing: .6px;
  border-radius: 4px;
  transition: background .15s, color .15s;
}

.tab:hover:not(:disabled) {
  background: #2c2c2c;
  color: #fff;
}

.tab.active {
  background: #424242;
  color: #fff;
}

.tab:disabled {
  opacity: .4;
  cursor: not-allowed;
}

.hud-toggle {
  margin-left: auto;
  background: #333;
  color: #bbb;
  border: 0;
  padding: .4rem .6rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: .75rem;
}

.hud-toggle:hover {
  background: #444;
  color: #fff;
}

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr var(--details-width);
  min-height: 0;
}

.workspace.placeholder {
  /* Override the 3-column layout for placeholder views (e.g., Debug) */
  grid-template-columns: 1fr;
  place-items: start stretch;
  padding: var(--sp-4);
}

/* Ensure single child wrappers (debug/ipam/tariffs) span full width */
.workspace.placeholder>* {
  grid-column: 1 / -1;
  width: 100%;
}

.ipam-wrapper {
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.tariffs-wrapper {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
}

.metrics-wrapper {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.hardware-wrapper {
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
}

/* Debug page wrapper to center content with max width */
.debug-wrapper {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.placeholder-center {
  color: #ccc;
  font-size: .8rem;
}
</style>
