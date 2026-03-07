import { useDevicesStore } from '../devicesStore.js'
import type { Link } from './types.js'
import { confirmCreateLink } from './creator.js'
import { isContainerType, phase1GuardsOk } from './create/selection.js'
import { computeSelections } from './create/selection.js'

type LinksStoreApi = {
  links: Link[]
  hasLinkBetween: (a: string, b: string) => boolean
}

export async function createBetweenDevices(
  store: LinksStoreApi,
  aDeviceId: string,
  bDeviceId: string,
  opts?: { headless?: boolean }
) {
  if (aDeviceId === bDeviceId) return
  const devStore = useDevicesStore()
  // Ensure we have interfaces for intelligent selection
  const needIfaces = !devStore.byId(aDeviceId)?.interfaces || !devStore.byId(bDeviceId)?.interfaces
  if (needIfaces) {
    try {
      await devStore.fetchAllWithInterfaces()
    } catch {
      /* non-fatal: fallback to -if0 */
    }
  }
  const aDev = devStore.byId(aDeviceId)
  const bDev = devStore.byId(bDeviceId)
  if (isContainerType(aDev?.type) || isContainerType(bDev?.type)) {
    console.debug('[linksStore] blocked container link attempt (POP/CORE_SITE)')
    return
  }
  // Strict rule: forbid ODF↔ODF cascades (ODF acts as aggregator; no passive-to-passive chaining)
  if (String(aDev?.type) === 'ODF' && String(bDev?.type) === 'ODF') {
    console.warn('[linksStore] ODF↔ODF links are not supported (cascade forbidden)')
    return
  }
  // Phase 1 GPON (ODF-as-Aggregator) client-side guard (feature-flagged)
  {
    const aTypeS = String(aDev?.type || '')
    const bTypeS = String(bDev?.type || '')
    const ok = phase1GuardsOk(store.links as Link[], devStore, aDeviceId, bDeviceId, aTypeS, bTypeS)
    if (!ok) return
  }

  const orderedDevs = [aDeviceId, bDeviceId].sort()
  if (store.hasLinkBetween(orderedDevs[0], orderedDevs[1])) return

  const { aIface, bIface, aOptions, bOptions } = computeSelections(
    devStore,
    store.links as Link[],
    aDeviceId,
    bDeviceId
  )

  const confirm = async (finalA: string, finalB: string) => {
    await confirmCreateLink(store, finalA, finalB)
  }

  const cancel = () => {
    /* user aborted; no-op */
  }

  if (opts?.headless) {
    await confirm(aIface, bIface)
    return
  }
  window.dispatchEvent(
    new CustomEvent('unoc:openLinkSelector', {
      detail: {
        aDeviceId: aDeviceId,
        bDeviceId: bDeviceId,
        aSelected: aIface,
        bSelected: bIface,
        aOptions,
        bOptions,
        confirm,
        cancel
      }
    })
  )
}
