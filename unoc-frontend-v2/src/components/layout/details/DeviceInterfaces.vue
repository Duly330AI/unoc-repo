<template>
    <div class="interfaces-tab">
        <div class="section-title">Interfaces</div>
        <div class="vrf-banner">
            <label>VRF</label>
            <span class="mono">{{ device?.device_default_vrf_name || '—' }}</span>
        </div>
        <div class="interfaces-list">
            <div v-for="i in interfacesSorted" :key="i.id" class="iface">
                <div class="row">
                    <label>Name</label><span class="mono">{{ i.name }}</span>
                </div>
                <div class="row">
                    <label>Admin</label><span class="badge status" :data-status="i.admin_status">{{ i.admin_status
                        }}</span>
                </div>
                <div class="row">
                    <label>Role</label><span>{{ i.role || '—' }}</span>
                </div>
                <div class="row">
                    <label>MAC</label><span class="mono">{{ i.mac_address || '—' }}</span>
                </div>
                <div class="row addresses">
                    <label>Addresses</label>
                    <span>
                        <span v-if="addressesByIface[i.id] && addressesByIface[i.id].length > 0">
                            <code
v-for="a in addressesByIface[i.id]" :key="a.id"
                                class="addr">{{ a.ip }}/{{ a.prefix_len }}<template v-if="(a as any).prefix_string"> / {{ (a as any).prefix_string }}</template></code>
                        </span>
                        <span v-else>—</span>
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { DeviceOut } from '../../../types/domain.js'

type DeviceWithParent = (DeviceOut & {
    parent_container_id?: string | null
})

type Iface = { id: string; name: string; admin_status: string; role?: string | null; mac_address?: string | null }
type IfAddress = { id: number; interface_id: string; ip: string; prefix_len: number }

const props = defineProps<{ device: DeviceWithParent | null }>()

function naturalCompare(a: string, b: string) {
    return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })
}

const interfacesSorted = computed(() => {
    const d = props.device
    const arr = (d?.interfaces ?? []) as Iface[]
    if (!Array.isArray(arr)) return []
    const roleRank = (r: string | null | undefined) => {
        const key = (r || '').toLowerCase()
        if (key === 'uplink') return 0
        if (key === 'trunk') return 1
        if (key === 'aggregation') return 2
        if (key === 'access') return 3
        if (!key) return 9
        return 8
    }
    const adminRank = (a: string | null | undefined) => (String(a).toLowerCase() === 'up' ? 0 : 1)
    return [...arr].sort((a, b) => {
        const rr = roleRank(a.role) - roleRank(b.role)
        if (rr !== 0) return rr
        const ar = adminRank(a.admin_status) - adminRank(b.admin_status)
        if (ar !== 0) return ar
        return naturalCompare(a.name || '', b.name || '')
    })
})

const addressesByIface = ref<Record<string, IfAddress[]>>({})

async function fetchAddresses(interfaceId: string) {
    try {
        const resp = await fetch(`/api/interfaces/${interfaceId}/addresses`)
        if (!resp.ok) return
        const arr = (await resp.json()) as IfAddress[]
        addressesByIface.value = { ...addressesByIface.value, [interfaceId]: arr }
    } catch {
        /* ignore */
    }
}

// Load addresses when component is mounted and whenever device changes
watch(() => props.device?.id, () => {
    addressesByIface.value = {}
    for (const i of interfacesSorted.value) void fetchAddresses(i.id)
}, { immediate: true })

onMounted(() => {
    for (const i of interfacesSorted.value) void fetchAddresses(i.id)
})
</script>

<style scoped>
/* This component relies on parent styles for .interfaces-tab, .section-title, .interfaces-list, etc. */
</style>
