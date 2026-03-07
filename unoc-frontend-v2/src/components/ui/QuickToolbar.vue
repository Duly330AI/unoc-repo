<template>
  <div class="quick-toolbar">
    <button :disabled="undo === 0" title="Undo (Ctrl+Z)" @click="emit('unoc:layoutUndo')">↺</button>
    <button :disabled="redo === 0" title="Redo (Ctrl+Y)" @click="emit('unoc:layoutRedo')">↻</button>
    <button :class="{ active: linkActive }" title="Link Tool (K)" @click="emit('unoc:toggleLinkTool')">🔗</button>
    <button title="Auto Layout" @click="emit('unoc:forceLayout')">⟳</button>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface LayoutStacksDetail { undo: number; redo: number }
interface LinkToolStateDetail { active: boolean }

const undo = ref(0)
const redo = ref(0)
const linkActive = ref(false)

function emit(name: string) { window.dispatchEvent(new CustomEvent(name)) }
function stacks(e: Event) { const ev = e as CustomEvent<LayoutStacksDetail>; undo.value = ev.detail.undo; redo.value = ev.detail.redo }
function link(e: Event) { const ev = e as CustomEvent<LinkToolStateDetail>; linkActive.value = !!ev.detail.active }

onMounted(() => { window.addEventListener('unoc:layoutStacks', stacks); window.addEventListener('unoc:linkToolState', link) })
onUnmounted(() => { window.removeEventListener('unoc:layoutStacks', stacks); window.removeEventListener('unoc:linkToolState', link) })
</script>
<style scoped>
.quick-toolbar {
  position: fixed;
  bottom: 3.3rem;
  left: .6rem;
  display: flex;
  gap: .35rem;
  background: rgba(30, 30, 30, .65);
  border: 1px solid #444;
  padding: .35rem .45rem;
  border-radius: 6px;
  z-index: 3600;
  backdrop-filter: blur(4px);
}

.quick-toolbar button {
  background: #2e2e2e;
  color: #ddd;
  border: 1px solid #555;
  padding: .3rem .5rem;
  font-size: .7rem;
  border-radius: 4px;
  cursor: pointer;
  min-width: 2rem;
}

.quick-toolbar button:hover:not(:disabled) {
  background: #424242;
  color: #fff;
}

.quick-toolbar button:disabled {
  opacity: .35;
  cursor: not-allowed;
}

.quick-toolbar button.active {
  background: #1976d2;
  border-color: #2196f3;
  color: #fff;
}
</style>
