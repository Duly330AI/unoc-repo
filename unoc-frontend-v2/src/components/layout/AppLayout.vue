<template>
  <div class="app-layout">
    <div class="theme-toggle">
      <button @click="toggleDark">{{ isDark ? 'Light' : 'Dark' }}</button>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
// Wrapper for global providers later (theme, hotkeys, etc.)
const isDark = ref(false)
function apply(){
  const root = document.documentElement
  if (isDark.value) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}
function toggleDark(){ isDark.value = !isDark.value; localStorage.setItem('themeDark', isDark.value? '1':'0'); apply() }
onMounted(()=>{ isDark.value = localStorage.getItem('themeDark')==='1'; apply() })
</script>

<style scoped>
.app-layout { height:100vh; display:flex; flex-direction:column; }
</style>
