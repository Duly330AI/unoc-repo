<template>
  <g>
    <g transform="translate(-18, 0)">
      <rect :width="barWidth(upMbps)" height="3" :fill="upColor" rx="1" ry="1" />
      <text x="0" y="-1" font-size="6px" :fill="upLabelColor">UP</text>
    </g>
    <g transform="translate(-18, 6)">
      <rect :width="barWidth(downMbps)" height="3" :fill="downColor" rx="1" ry="1" />
      <text x="0" y="-1" font-size="6px" :fill="downLabelColor">DN</text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  upstreamBps?: number
  downstreamBps?: number
  maxMbps?: number
  upColor?: string
  downColor?: string
  upLabelColor?: string
  downLabelColor?: string
}>(), {
  upstreamBps: 0,
  downstreamBps: 0,
  maxMbps: 100,
  upColor: '#42a5f5',
  downColor: '#26a69a',
  upLabelColor: '#90caf9',
  downLabelColor: '#80cbc4'
})

const upMbps = computed(() => Math.round((props.upstreamBps ?? 0) / 1_000_000))
const downMbps = computed(() => Math.round((props.downstreamBps ?? 0) / 1_000_000))

const barWidth = (mbps: number) => Math.max(1, Math.min(32, Math.round((mbps / (props.maxMbps || 1)) * 32)))
</script>

<style scoped>
</style>
