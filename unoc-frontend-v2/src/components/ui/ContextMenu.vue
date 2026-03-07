<template>
  <teleport to="body">
    <transition name="ctx-fade" appear>
      <div v-if="store.open" class="ctx-overlay" @click="close" @contextmenu.prevent>
        <ul ref="menuEl" class="ctx" :style="styleObj" @click.stop @contextmenu.prevent>
          <li
v-for="(it, idx) in store.items" :key="it.id"
            :class="{ disabled: it.disabled, highlighted: idx === store.highlighted }"
            @mouseenter="store.highlighted = it.disabled ? store.highlighted : idx" @click="onClick(it)">
            <span class="label">{{ it.label }}</span>
            <span v-if="it.disabled && it.reason" class="reason" :title="it.reason">?</span>
          </li>
        </ul>
      </div>
    </transition>
  </teleport>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, type CSSProperties } from 'vue'
import { useContextMenuStore } from '../../stores/contextMenuStore'
import type { ContextMenuItem } from '../../stores/contextMenuStore'
const store = useContextMenuStore()

function close() { store.hide() }
function onClick(it: ContextMenuItem) { if (it.disabled) return; Promise.resolve(it.action()).finally(() => close()) }
function keyHandler(e: KeyboardEvent) {
  if (!store.open) return
  if (e.key === 'Escape') { e.preventDefault(); return close() }
  if (e.key === 'ArrowDown') { e.preventDefault(); return store.moveHighlight(1) }
  if (e.key === 'ArrowUp') { e.preventDefault(); return store.moveHighlight(-1) }
  if (e.key === 'Enter') { e.preventDefault(); return store.activateHighlighted() }
}
onMounted(() => {
  window.addEventListener('keydown', keyHandler)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', keyHandler)
  window.removeEventListener('resize', onResize)
})

const menuEl = ref<HTMLUListElement | null>(null)
function onResize() {
  // Recompute based on actual rendered size if available, else use estimates
  const rect = menuEl.value?.getBoundingClientRect()
  const w = rect?.width ?? 220
  const h = rect ? Math.min(320, rect.height) : 320
  store.repositionWithinViewport(w, h)
}
watch(() => store.open, async (o) => { if (o) { await nextTick(); onResize() } })

const styleObj = computed<CSSProperties>(() => ({ left: store.pos.x + 'px', top: store.pos.y + 'px', maxHeight: '320px', overflowY: 'auto', width: 'auto', minWidth: '180px' }))
</script>
<style scoped>
.ctx-overlay {
  position: fixed;
  inset: 0;
  z-index: 4000;
}

.ctx {
  position: absolute;
  min-width: 180px;
  background: #1f1f1f;
  border: 1px solid #333;
  padding: 4px 0;
  margin: 0;
  list-style: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, .5);
  border-radius: 6px;
  font-size: .65rem;
  max-height: 320px;
  overflow-y: auto;
}

.ctx li {
  padding: 6px 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: .4rem;
}

.ctx li:hover {
  background: #2b2b2b;
}

.ctx li.disabled {
  opacity: .45;
  cursor: default;
}

.ctx li.disabled:hover {
  background: transparent;
}

.ctx li.highlighted:not(.disabled) {
  background: #2b2b2b;
}

.label {
  flex: 1;
}

.reason {
  font-size: .55rem;
  background: #444;
  color: #ddd;
  padding: 0 4px;
  border-radius: 3px;
}

/* Subtle fade for menu appearance/disappearance */
.ctx-fade-enter-active,
.ctx-fade-leave-active {
  transition: opacity .12s ease, transform .12s ease;
}

.ctx-fade-enter-from,
.ctx-fade-leave-to {
  opacity: 0;
  transform: translateY(2px);
}
</style>
