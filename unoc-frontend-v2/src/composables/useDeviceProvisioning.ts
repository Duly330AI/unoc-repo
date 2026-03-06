import { computed, ref, type ComputedRef } from 'vue'
import { useDevicesStore } from '../stores/devicesStore.js'
import { useToastStore } from '../stores/toastStore.js'
import { portSummaryManager } from './usePortSummaryManager.js'
import type { DeviceOut } from '../types/domain.js'

type DeviceWithParent = DeviceOut & { parent_container_id?: string | null }

// Provision button visibility logic (from Architecture §2 & §3 tables)
const PROVISIONABLE_TYPES = new Set([
  'CORE_ROUTER',
  'EDGE_ROUTER',
  'OLT',
  'AON_SWITCH',
  'ONT',
  'BUSINESS_ONT',
  'AON_CPE'
])

// Parent is optional for OLT/AON_SWITCH now; keep set empty unless a type truly requires a parent
const REQUIRE_POP_PARENT = new Set<string>([])

export function useDeviceProvisioning(activeDevice: ComputedRef<DeviceWithParent | null>) {
  const devices = useDevicesStore()
  const toasts = useToastStore()

  const provisioning = ref(false)

  const canProvision = computed(() => {
    const d = activeDevice.value
    if (!d) return false
    if (d.provisioned) return false
    if (!PROVISIONABLE_TYPES.has(d.type)) return false
    const parentId = d.parent_container_id ?? null
    if (REQUIRE_POP_PARENT.has(d.type) && !parentId) return false
    return true
  })

  async function doProvision() {
    const d = activeDevice.value
    if (!d) return
    provisioning.value = true
    const id = d.id
    let toastId: string | undefined
    try {
      toastId = toasts.pending(`Provisioniere ${id}…`)
      await devices.provision(id)

      // CRITICAL: Trigger immediate port summary refresh after provisioning
      // 1. Refresh parent device (e.g., OLT when provisioning ONT)
      // 2. Refresh provisioned device itself (in case it has links)
      const refreshIds: string[] = []

      const parentId = d.parent_container_id ?? null
      if (parentId) {
        refreshIds.push(parentId)
      }

      // Also refresh the provisioned device itself (might have downstream links)
      refreshIds.push(id)

      if (refreshIds.length > 0) {
        portSummaryManager.triggerRefresh(refreshIds)
      }

      toasts.succeed(toastId, `Provisioniert: ${id}`)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      if (toastId) toasts.fail(toastId, `Provision fehlgeschlagen: ${msg}`)
    } finally {
      provisioning.value = false
    }
  }

  return { provisioning, canProvision, doProvision }
}

export const __provisioningInternals = { PROVISIONABLE_TYPES, REQUIRE_POP_PARENT }
