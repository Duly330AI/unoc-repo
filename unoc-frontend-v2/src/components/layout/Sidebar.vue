<template>
  <aside class="sidebar">
    <header>Palette</header>
    <div class="content">
      <DevicePalette />
      <slot />
    </div>
  </aside>
</template>

<script setup lang="ts">
import DevicePalette from './DevicePalette.vue';
</script>

<style scoped>
.sidebar { background:var(--color-bg-alt); border-right:1px solid var(--color-border); padding:var(--sp-4); display:flex; flex-direction:column; gap:var(--sp-4); }
.sidebar header { font-weight:600; font-size:var(--fs-sm); text-transform:uppercase; letter-spacing:.5px; color:var(--color-text-dim); }
.content { flex:1; overflow:auto; }
</style>
