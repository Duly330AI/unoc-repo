<template>
  <div class="ports-table">
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Role</th>
          <th>Status</th>
          <th>Type/Speed</th>
          <th>MAC Address</th>
          <th>IP Addresses</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td colspan="6" class="empty">No ports</td>
        </tr>
        <tr v-for="r in rows" :key="r.id || r.name">
          <td class="mono">{{ r.name || '—' }}</td>
          <td>{{ r.role || '—' }}</td>
          <td>
            <span class="badge status" :data-status="r.status" :title="r.status">{{ r.status || '—' }}</span>
          </td>
          <td>{{ r.typeDisplay || '—' }}</td>
          <td class="mono">{{ r.mac || '—' }}</td>
          <td class="addr-list">
            <template v-if="r.addrs.length > 0">
              <code v-for="(a, idx) in r.addrs" :key="idx" class="addr">{{ a }}</code>
            </template>
            <span v-else>—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  
</template>

<script setup lang="ts">
import { computed } from 'vue'

type IfaceAddress = { ip?: string; prefix_len?: number; cidr?: string; prefix_string?: string }
type PortProfile = { type?: string | null; kind?: string | null; speed?: string | number | null; display?: string | null }
type IfaceIn = {
  id?: string
  name?: string
  port_role?: string | null
  role?: string | null
  effective_status?: string | null
  admin_status?: string | null
  mac_address?: string | null
  addresses?: IfaceAddress[] | null
  port_profile?: PortProfile | null
}

const props = defineProps<{ interfaces: IfaceIn[] | undefined }>()

function displayForProfile(p?: PortProfile | null): string | null {
  if (!p) return null
  if (p.display && String(p.display).trim()) return String(p.display)
  const parts: string[] = []
  const speed = p.speed != null ? String(p.speed) : ''
  const type = p.type || p.kind || ''
  if (speed) parts.push(speed)
  if (type) parts.push(type)
  if (parts.length === 0) return null
  return parts.join(' ')
}

function toCidr(addr: IfaceAddress): string | null {
  if (addr.cidr) return addr.cidr
  if (addr.ip && (addr.prefix_len ?? null) != null) return `${addr.ip}/${addr.prefix_len}`
  return addr.prefix_string || null
}

const rows = computed(() => {
  const ifs = Array.isArray(props.interfaces) ? props.interfaces : []
  return ifs.map((i) => {
    const status = (i.effective_status || i.admin_status || '') as string
    const addrsRaw = Array.isArray(i.addresses) ? i.addresses : []
    const addrs = addrsRaw
      .map(toCidr)
      .filter((x): x is string => !!x && x.trim().length > 0)
    return {
      id: i.id || undefined,
      name: i.name || '',
      role: (i.port_role || i.role || '') as string,
      status: status || '—',
      typeDisplay: displayForProfile(i.port_profile),
      mac: i.mac_address || '',
      addrs,
    }
  })
})
</script>

<style scoped>
.ports-table {
  border-top: 1px solid var(--color-border);
  padding-top: .6rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: .62rem;
}

th, td {
  text-align: left;
  padding: .3rem .4rem;
  border-bottom: 1px solid #2a2a2a;
  vertical-align: top;
}

th {
  font-weight: 600;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: .4px;
  font-size: .55rem;
}

.mono {
  font-family: var(--font-mono, monospace);
}

.addr-list {
  display: flex;
  flex-wrap: wrap;
  gap: .25rem .35rem;
}

.addr {
  display: inline-block;
  max-width: 100%;
  overflow-wrap: anywhere;
}

.badge.status {
  font-size: .6rem;
  padding: .15rem .4rem;
  border-radius: 999px;
  background: #444;
  text-transform: uppercase;
  letter-spacing: .5px;
}

.badge.status[data-status="UP"] {
  background: #1b5e20;
  color: #fff;
}

.badge.status[data-status="DOWN"] {
  background: #b71c1c;
  color: #fff;
}

.badge.status[data-status="DEGRADED"] {
  background: #ef6c00;
  color: #fff;
}

.empty {
  text-align: center;
  color: var(--color-text-dim);
}
</style>
