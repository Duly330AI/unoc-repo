<template>
  <div class="tabs">
    <button
      v-for="t in tabs"
      :key="t"
      class="tab"
      :class="{ active: modelValue === t }"
      @click="$emit('update:modelValue', t)"
    >{{ t }}</button>
  </div>
</template>

<script setup lang="ts">
// Generic tab bar for device details; keeps styling & logic isolated
defineProps<{ tabs: string[]; modelValue: string }>()
defineEmits<{ (e: 'update:modelValue', value: string): void }>()
</script>

<style scoped>
.tabs { display:flex; flex-wrap:wrap; gap:.35rem; min-width:0; }
.tab { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; background:#222; color:#ddd; border:1px solid #3a3a3a; padding:.28rem .6rem; border-radius:6px; font-size:.62rem; cursor:pointer; }
.tab:hover { background:#2a2a2a; color:#fff; border-color:#4a4a4a; }
.tab.active { background:#0f172a; color:#fff; border-color:#334155; }
</style>