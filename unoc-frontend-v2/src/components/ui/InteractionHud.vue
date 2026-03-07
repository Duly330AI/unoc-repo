<template>
  <transition name="hud-fade">
    <div v-if="store.visible" class="interaction-hud" @mouseenter="hover=true" @mouseleave="hover=false">
      <header class="hud-head">
        <span>Interaktionen</span>
        <button class="close" @click="store.toggleVisible(false)">×</button>
      </header>
      <ul class="hud-list">
        <li v-for="e in store.entries" :key="e.id">
          <strong>{{ e.label }}</strong>
          <em v-if="e.detail">{{ e.detail }}</em>
        </li>
      </ul>
      <footer class="hud-foot">
        <span class="hint">Autom. Ausblenden in {{ remaining }}s</span>
        <button class="mini" @click="store.ensureBaseEntries()">Refresh</button>
      </footer>
    </div>
  </transition>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useInteractionHudStore, installInteractionHudGlobal } from '../../stores/interactionHudStore'

const store = useInteractionHudStore()
const hover = ref(false)
const remaining = computed(()=> {
  const delta = store.autoHideMs - (Date.now() - store.lastActivity)
  return Math.max(0, Math.round(delta/1000))
})
let timer: number | null = null

function tick(){
  if(!store.visible) return
  if(!hover.value && Date.now() - store.lastActivity > store.autoHideMs){
    store.visible = false
  }
  timer = window.setTimeout(tick, 500)
}

onMounted(()=>{ installInteractionHudGlobal(); timer = window.setTimeout(tick, 500) })
onUnmounted(()=>{ if(timer) window.clearTimeout(timer) })
</script>
<style scoped>
.interaction-hud { position:fixed; right:1rem; bottom:1rem; background:#1e1e1f; color:#ddd; font-size:11px; line-height:1.25; width:220px; border:1px solid #333; border-radius:6px; box-shadow:0 4px 18px -4px rgba(0,0,0,.55); backdrop-filter:blur(4px); display:flex; flex-direction:column; }
.hud-head { font-weight:600; font-size:11px; letter-spacing:.5px; padding:.4rem .6rem; display:flex; justify-content:space-between; align-items:center; background:#262627; border-bottom:1px solid #333; }
.hud-head .close { background:transparent; color:#888; border:0; cursor:pointer; font-size:14px; line-height:1; }
.hud-head .close:hover { color:#fff; }
.hud-list { list-style:none; margin:0; padding:.4rem .6rem; flex:1; overflow:auto; }
.hud-list li { display:flex; flex-direction:column; margin-bottom:.3rem; }
.hud-list li strong { font-weight:500; color:#fafafa; }
.hud-list li em { font-style:normal; color:#8ab4f8; font-size:10px; }
.hud-foot { padding:.3rem .6rem .5rem; border-top:1px solid #333; display:flex; justify-content:space-between; align-items:center; font-size:10px; color:#777; }
.hint { opacity:.8; }
button.mini { background:#333; color:#bbb; border:0; border-radius:3px; padding:.15rem .4rem; cursor:pointer; font-size:10px; }
button.mini:hover { background:#3f3f40; color:#fff; }
.hud-fade-enter-active,.hud-fade-leave-active { transition:opacity .18s ease, transform .18s ease; }
.hud-fade-enter-from,.hud-fade-leave-to { opacity:0; transform:translateY(6px); }
</style>
