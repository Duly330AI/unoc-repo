<template>
  <div class="modal-backdrop" @click.self="onCancel">
    <div
      ref="modalEl"
      class="modal"
      role="dialog"
  aria-modal="true"
  :aria-labelledby="titleId"
      tabindex="-1"
      @keydown="onKeydown"
    >
      <header class="modal-header">
  <h3 :id="titleId" class="title"><slot name="title" /></h3>
  <button class="close" aria-label="Close" @click="onCancel">×</button>
      </header>
      <section class="modal-body">
        <slot />
      </section>
      <footer class="modal-footer">
        <slot name="footer" />
      </footer>
    </div>
  </div>
 </template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'

const emit = defineEmits(['cancel'])
function onCancel(){ emit('cancel') }

// Accessibility: labelled-by id, focus trap, Enter submits primary action
const titleId = `modal-title-${Math.random().toString(36).slice(2)}`
const modalEl = ref<HTMLElement | null>(null)

function focusFirst(){
  const root = modalEl.value
  if(!root) return
  // Try to focus element with [autofocus], else first focusable, else the dialog itself
  const auto = root.querySelector<HTMLElement>('[autofocus]')
  if(auto){ auto.focus(); return }
  const focusables = getFocusable(root)
  if(focusables.length){ focusables[0].focus(); return }
  root.focus()
}

function getFocusable(root: HTMLElement): HTMLElement[] {
  const selector = [
    'button:not([disabled])',
    '[href]',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',')
  return Array.from(root.querySelectorAll<HTMLElement>(selector))
    .filter(el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length))
}

function onKeydown(e: KeyboardEvent){
  const root = modalEl.value
  if(!root) return
  if(e.key === 'Escape'){
    e.stopPropagation()
    e.preventDefault()
    onCancel()
    return
  }
  if(e.key === 'Tab'){
    const focusables = getFocusable(root)
    if(!focusables.length){ e.preventDefault(); return }
    const current = document.activeElement as HTMLElement | null
    const idx = current ? focusables.indexOf(current) : -1
    const dir = e.shiftKey ? -1 : 1
    let next = idx + dir
    if(next < 0) next = focusables.length - 1
    if(next >= focusables.length) next = 0
    e.preventDefault()
    focusables[next].focus()
    return
  }
  if(e.key === 'Enter'){
    // Trigger primary action if marked, unless already on a button
    if(!(e.target instanceof HTMLButtonElement)){
      const primary = (modalEl.value?.querySelector('[data-primary]') as HTMLElement | null)
      if(primary){
        e.preventDefault()
        primary.click()
      }
    }
  }
}

onMounted(() => {
  // Defer to next tick to ensure slot content rendered
  requestAnimationFrame(() => focusFirst())
})

defineSlots<{
  title?: () => unknown
  footer?: () => unknown
  default?: () => unknown
}>()
</script>
<style scoped>
.modal-backdrop{ position:fixed; inset:0; background:rgba(0,0,0,.55); display:flex; align-items:flex-start; justify-content:center; padding:4rem 1rem 2rem; z-index:5000; }
.modal{ background:#1e1f22; border:1px solid #2c2d30; border-radius:8px; width:420px; max-width:100%; box-shadow:0 6px 28px -4px rgba(0,0,0,.6); display:flex; flex-direction:column; }
.modal-header{ display:flex; align-items:center; justify-content:space-between; padding:.75rem 1rem .5rem; border-bottom:1px solid #2c2d30; }
.title{ font-size:.9rem; margin:0; font-weight:600; letter-spacing:.5px; }
.close{ background:transparent; color:#bbb; border:0; font-size:1.15rem; cursor:pointer; line-height:1; padding:.25rem; }
.close:hover{ color:#fff; }
.modal-body{ padding:1rem; font-size:.75rem; display:flex; flex-direction:column; gap:.65rem; }
.modal-footer{ padding:.65rem 1rem .9rem; display:flex; gap:.5rem; justify-content:flex-end; }
button{ font-size:.7rem; letter-spacing:.4px; cursor:pointer; }
input, select{ background:#26272b; border:1px solid #34363a; color:#ddd; padding:.4rem .5rem; border-radius:4px; font-size:.7rem; width:100%; }
input:focus, select:focus{ outline:1px solid #1976d2; }
label{ display:flex; flex-direction:column; gap:.25rem; font-weight:500; }
.inline{ display:flex; gap:.5rem; }
.error{ color:#ff7961; font-size:.65rem; margin-top:-.25rem; }
</style>