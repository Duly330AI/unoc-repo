import { computed, type ComputedRef } from 'vue'
import { useDevicesStore } from '../stores/devicesStore.js'
import type { DeviceOut } from '../types/domain.js'

type DeviceWithParent = DeviceOut & { parent_container_id?: string | null }

// Device details helpers: parent display and the property list for the sidebar
export function useDeviceProps(activeDevice: ComputedRef<DeviceWithParent | null>) {
  const devices = useDevicesStore()

  // No device types currently require a POP parent (OLT/AON optional)
  const DEVICE_TYPES_REQUIRING_PARENT = new Set<string>([])

  const parentDisplay = computed(() => {
    const d = activeDevice.value
    if (!d) return ''
    const parentId = d.parent_container_id ?? null
    if (parentId) return parentId
    return DEVICE_TYPES_REQUIRING_PARENT.has(d.type) ? 'FEHLT' : '—'
  })

  const deviceProps = computed(() => {
    const d = activeDevice.value
    if (!d) return [] as { key: string; value: string; warn?: boolean }[]
    const { id, name, status, type, role } = d

    // Derive children if POP selected
    let childInfo = ''
    if (type === 'POP') {
      const kids = (devices.devices as DeviceWithParent[]).filter(
        (k) => k.parent_container_id === id
      )
      childInfo = kids.length ? `${kids.length}: ${kids.map((k) => k.id).join(', ')}` : '0'
    }

    const list: { key: string; value: string; warn?: boolean }[] = [
      { key: 'ID', value: id },
      { key: 'Name', value: name },
      { key: 'Status', value: status },
      { key: 'Typ', value: type },
      { key: 'Rolle', value: role },
      { key: 'Parent', value: parentDisplay.value, warn: parentDisplay.value === 'FEHLT' }
    ]
    if (type === 'POP') list.push({ key: 'Children', value: childInfo })

    // Subscriber count semantics from backend (effective is the authoritative display value).
    // When physical/provisioned differ from effective (e.g. AON 1:1 oversubscription),
    // show the breakdown instead of implying all three are equal.
    const cs = (d as { parameters?: { count_semantics?: Record<string, unknown> } }).parameters
      ?.count_semantics
    if (cs && typeof cs === 'object') {
      const eff = Number(cs.effective_count)
      const prov = Number(cs.provisioned_count)
      const phys = Number(cs.physical_count)
      if (Number.isFinite(eff)) {
        const differs =
          (Number.isFinite(prov) && prov !== eff) || (Number.isFinite(phys) && phys !== eff)
        const value = differs
          ? `${eff} effective (${Number.isFinite(prov) ? prov : '?'} provisioned / ${Number.isFinite(phys) ? phys : '?'} physical)`
          : String(eff)
        list.push({ key: 'Subscribers', value, warn: differs })
      }
    }
    return list
  })

  return { parentDisplay, deviceProps }
}
