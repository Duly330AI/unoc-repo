<template>
  <div class="toasts">
    <div v-for="t in store.toasts" :key="t.id" :data-variant="t.variant" class="toast" @click="onClick(t)">
      <span v-if="t.variant === 'pending'" class="spinner"></span>
      <span class="msg">{{ t.message }}</span>
      <button v-if="t.action" class="action" @click.stop="runAction(t)">{{ t.action.label }}</button>
      <button v-if="t.dismissible" class="close" @click.stop="store.remove(t.id)">x</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useToastStore, type Toast } from '../../stores/toastStore'
const store = useToastStore()
function onClick(t: Toast) { if (!t.dismissible) return; store.remove(t.id) }
function runAction(t: Toast) { try { t.action?.run() } finally { store.remove(t.id) } }
</script>

<style scoped>
.toasts {
  position: fixed;
  bottom: .75rem;
  right: .75rem;
  display: flex;
  flex-direction: column;
  gap: .5rem;
  z-index: 4000;
}

.toast {
  min-width: 180px;
  max-width: 320px;
  background: #2c2c2e;
  color: #fff;
  padding: .55rem .75rem .5rem;
  border-radius: 6px;
  font-size: .65rem;
  line-height: 1.25;
  box-shadow: 0 2px 6px rgba(0, 0, 0, .35);
  display: flex;
  gap: .65rem;
  align-items: center;
  position: relative;
  border: 1px solid #3a3a3c;
  cursor: pointer;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, .3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .8s linear infinite;
  flex: 0 0 auto;
  margin-top: 1px;
}

@keyframes spin {
  to {
    transform: rotate(360deg)
  }
}

.toast[data-variant='success'] {
  background: #1b5e20;
  border-color: #2e7d32;
}

.toast[data-variant='error'] {
  background: #b71c1c;
  border-color: #c62828;
}

.toast[data-variant='warn'] {
  background: #e65100;
  border-color: #ef6c00;
}

.toast[data-variant='info'] {
  background: #1565c0;
  border-color: #1976d2;
}

.toast[data-variant='pending'] {
  background: #424242;
  border-color: #616161;
}

.toast .close {
  background: transparent;
  border: 0;
  color: #fff;
  font-size: .9rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 .25rem;
  position: absolute;
  top: .15rem;
  right: .3rem;
}

.toast .action {
  background: rgba(255, 255, 255, .15);
  border: 0;
  color: #fff;
  font-size: .6rem;
  padding: .25rem .4rem;
  border-radius: 3px;
  cursor: pointer;
}

.toast .action:hover {
  background: rgba(255, 255, 255, .25);
}

.toast .close:hover {
  opacity: .85;
}

.msg {
  flex: 1;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all .25s ease;
}

.toast-fade-enter-from,
.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(6px) scale(.96);
}
</style>
