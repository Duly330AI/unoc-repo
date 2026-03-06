<template>
  <div class="ipam-tab">
    <div class="toolbar">
      <h3>IPAM Pools</h3>
      <div class="sort-group">
        <label>Sort:
          <select v-model="sortKey">
            <option value="pool_key">Pool</option>
            <option value="utilization">Utilization</option>
            <option value="allocated_count">Allocated</option>
            <option value="capacity">Capacity</option>
          </select>
        </label>
        <button :disabled="loading" @click="toggleDir">{{ sortDir==='asc' ? 'Asc' : 'Desc' }}</button>
      </div>
  <button :disabled="loading" @click="reload">Reload</button>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
  <table v-if="sortedPools.length" class="pools">
      <thead>
        <tr>
          <th>Pool</th><th>CIDR</th><th>Allocated</th><th>Capacity</th><th>Utilization</th>
        </tr>
      </thead>
      <tbody>
  <tr v-for="p in sortedPools" :key="p.pool_key">
          <td>{{ p.pool_key }}</td>
          <td>{{ p.cidr }}</td>
          <td>{{ p.allocated_count }}</td>
          <td>{{ p.capacity }}</td>
          <td>
            <div class="u-bar" :class="warnClass(p.utilization)">
              <div class="fill" :style="{width: (p.utilization*100).toFixed(1)+'%'}"></div>
              <span>{{ (p.utilization*100).toFixed(1) }}%</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  <div v-else-if="!loading && !error" class="empty">Keine Pools</div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, computed, onBeforeUnmount } from 'vue';
import { useIpamStore } from '../../stores/ipamStore';

const store = useIpamStore();
const reload = ()=>store.fetchPools();
// reactive store reference already typed via ipamStore; no separate pools variable needed
const sortKey = ref<'pool_key'|'utilization'|'allocated_count'|'capacity'>('pool_key');
const sortDir = ref<'asc'|'desc'>('asc');
function toggleDir(){ sortDir.value = sortDir.value==='asc' ? 'desc' : 'asc'; }
interface PoolRow { pool_key: string; cidr: string; allocated_count: number; capacity: number; utilization: number }
const sortedPools = computed(()=>{
  const arr: PoolRow[] = [...store.pools];
  arr.sort((a,b)=>{
    const k = sortKey.value;
    const av = a[k]; const bv = b[k];
    if(av===bv) return 0;
    if(av>bv) return sortDir.value==='asc'?1:-1;
    return sortDir.value==='asc'?-1:1;
  });
  return arr;
});
const loading = store.$state.loading;
const error = store.$state.error;

function warnClass(u:number){
  if(u>=0.9) return 'crit';
  if(u>=0.8) return 'warn';
  return '';
}

let ws: WebSocket | null = null;
onMounted(()=>{
  store.fetchPools();
  try {
    // Backend FastAPI is mounted under /api, and ws router has prefix /ws => full path /api/ws
    // Allow override via VITE_BACKEND_WS_ORIGIN (e.g. ws://localhost:5001) for cross-origin dev.
  // Optional override injected globally (define in index.html or before app init): window.VITE_BACKEND_WS_ORIGIN
  interface WsEnv { VITE_BACKEND_WS_ORIGIN?: string }
  const originOverride: string | undefined = (globalThis as unknown as WsEnv).VITE_BACKEND_WS_ORIGIN;
    const proto = (originOverride?.startsWith('wss://') || originOverride?.startsWith('ws://'))
      ? ''
      : (location.protocol === 'https:' ? 'wss://' : 'ws://');
    const base = originOverride || location.host;
    const url = proto ? `${proto}${base}/api/ws` : `${base}/api/ws`;
    ws = new WebSocket(url);
    ws.onmessage = (ev)=> {
      const data = typeof ev.data === 'string' ? ev.data : '';
      if(/device\.provisioned|link\.(created|deleted)|device\.optical\.updated/.test(data)){
        store.fetchPools();
      }
    };
  } catch { /* ignore ws errors */ }
});
onBeforeUnmount(()=>{ if(ws){ try{ ws.close(); }catch{ /* ignore close error */ } } });
</script>
<style scoped>
.ipam-tab { padding:1rem; font-size:.75rem; color:#eee; }
.toolbar { display:flex; align-items:center; gap:1rem; margin-bottom:.5rem; }
.sort-group { display:flex; align-items:center; gap:.5rem; }
select { background:#222; color:#ddd; border:1px solid #444; padding:.3rem .4rem; border-radius:4px; font-size:.65rem; }
select:focus { outline:1px solid #555; }
button { background:#333; color:#ccc; border:0; padding:.35rem .7rem; border-radius:4px; cursor:pointer; }
button:disabled { opacity:.4; cursor:not-allowed; }
button:hover:not(:disabled){ background:#444; color:#fff; }
.pools { width:100%; border-collapse:collapse; }
.pools th, .pools td { padding:.4rem .5rem; border-bottom:1px solid #2d2d2d; text-align:left; }
.u-bar { position:relative; background:#222; border:1px solid #333; border-radius:3px; height:14px; min-width:120px; }
.u-bar .fill { position:absolute; left:0; top:0; bottom:0; background:linear-gradient(90deg,#2563eb,#1d4ed8); border-radius:2px; }
.u-bar.warn .fill { background:linear-gradient(90deg,#d97706,#b45309); }
.u-bar.crit .fill { background:linear-gradient(90deg,#dc2626,#b91c1c); }
.u-bar span { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); font-size:.6rem; color:#fff; text-shadow:0 1px 2px rgba(0,0,0,.6); }
.empty { opacity:.6; font-style:italic; }
.error { color:#f87171; margin:.5rem 0; }
</style>
