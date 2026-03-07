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
    return list
  })

  return { parentDisplay, deviceProps }
}
