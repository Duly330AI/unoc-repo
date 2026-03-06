import { defineStore } from 'pinia';

interface PoolRow { pool_key: string; cidr: string; next_index: number; allocated_count: number; capacity: number; utilization: number }

interface State { pools: PoolRow[]; loading: boolean; error: string | null }

export const useIpamStore = defineStore('ipam', {
    state: (): State => ({ pools: [], loading: false, error: null }),
    getters: {
        utilizationSorted: (s) => [...s.pools].sort((a, b) => b.utilization - a.utilization)
    },
    actions: {
        async fetchPools() {
            if (this.loading) return; this.loading = true; this.error = null;
            try {
                const r = await fetch('/api/ipam/pools');
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                this.pools = await r.json();
            } catch (e: unknown) { this.error = e instanceof Error ? e.message : String(e); }
            finally { this.loading = false; }
        }
    }
});
