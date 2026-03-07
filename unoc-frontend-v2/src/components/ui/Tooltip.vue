<template>
    <div v-if="shouldRender" class="tooltip" :style="styleObj" role="tooltip" aria-live="polite">
        <div class="tooltip-content">{{ state.content }}</div>
    </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import { useTooltipStore } from '../../stores/tooltipStore'

const store = useTooltipStore()
const state = storeToRefs(store)
const hasContent = computed(() => ((state.content.value ?? '') as string).trim().length > 0)
const validX = computed(() => Number.isFinite(state.x.value) && state.x.value !== 0)
const validY = computed(() => Number.isFinite(state.y.value) && state.y.value !== 0)
const shouldRender = computed(() => state.isVisible.value && hasContent.value && validX.value && validY.value)
const styleObj = computed(() => ({ left: String((state.x.value + 12)) + 'px', top: String((state.y.value + 12)) + 'px' }))
</script>

<style scoped>
.tooltip {
    position: fixed;
    z-index: 1000;
    pointer-events: none;
    max-width: 320px;
    transform: translateZ(0);
}

.tooltip-content {
    background: rgba(20, 20, 20, 0.95);
    color: #eee;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 12px;
    line-height: 1.2;
    box-shadow: 0 4px 14px rgba(0, 0, 0, .35);
    -webkit-font-smoothing: antialiased;
}
</style>
