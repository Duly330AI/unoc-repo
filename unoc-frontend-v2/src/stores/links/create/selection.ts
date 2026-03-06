import { useDevicesStore, type DeviceOutX } from '../../devicesStore.js'
import type { Link } from '../types.js'
import {
  type IfaceLite,
  isMgmt,
  isUp,
  getPortRole,
  isOntFamily,
  isPassive,
  validateOntPassive,
  annotatePassiveOptionsViaOlt
} from './helpers.js'

export type Option = { id: string; label: string }

export const isContainerType = (t: unknown): boolean => t === 'POP' || String(t) === 'CORE_SITE'

export const buildUsedInterfaceSet = (links: Link[]): Set<string> => {
  const used = new Set<string>()
  for (const l of links) {
    if (l?.a_interface_id) used.add(l.a_interface_id)
    if (l?.b_interface_id) used.add(l.b_interface_id)
  }
  return used
}

export const pickInterface = (
  devStore: ReturnType<typeof useDevicesStore>,
  devId: string,
  usedIfaces: Set<string>
): string => {
  const dev = devStore.byId(devId) as DeviceOutX | undefined
  const ifaces = (dev?.interfaces || []) as IfaceLite[]
  const candidates = ifaces.filter((i) => i && !isMgmt(i) && isUp(i) && !usedIfaces.has(i.id))
  const rank = (i: IfaceLite) => {
    const pr = getPortRole(i)
    const unused = !usedIfaces.has(i.id)
    const legacyP2P = i.role === 'p2p_uplink'
    const legacyAccess = i.role === 'access'
    if (unused && pr === 'UPLINK') return 0
    if (unused && pr === 'ACCESS') return 1
    if (unused && pr === 'TRUNK') return 2
    if (unused && (legacyP2P || legacyAccess)) return 3
    if (pr === 'UPLINK') return 4
    if (pr === 'ACCESS') return 5
    if (pr === 'TRUNK') return 6
    if (legacyP2P || legacyAccess) return 7
    return 9
  }
  const sorted = candidates.slice().sort((a, b) => rank(a) - rank(b))
  if (sorted.length) return sorted[0].id
  const if0Id = `${devId}-if0`
  const if0 = ifaces.find((i) => i.id === if0Id && isUp(i) && !usedIfaces.has(i.id))
  if (if0) return if0.id
  if (ifaces.length) {
    const anyAvail = ifaces.find((i) => !isMgmt(i) && isUp(i) && !usedIfaces.has(i.id))
    if (anyAvail) return anyAvail.id
  }
  return if0Id
}

export const pickWithRole = (
  devStore: ReturnType<typeof useDevicesStore>,
  devId: string,
  usedIfaces: Set<string>,
  preferred: 'ACCESS' | 'UPLINK' | 'PON' | 'TRUNK' | null
): string => {
  const dev = devStore.byId(devId) as DeviceOutX | undefined
  const ifaces = (dev?.interfaces || []) as IfaceLite[]
  const base = ifaces.filter((i) => i && !isMgmt(i) && isUp(i) && !usedIfaces.has(i.id))
  const prMatches = preferred ? base.filter((i) => getPortRole(i) === preferred) : []
  if (prMatches.length) return prMatches[0].id
  return pickInterface(devStore, devId, usedIfaces)
}

export const anchorOdfIf0ForOltPair = (
  devStore: ReturnType<typeof useDevicesStore>,
  usedIfaces: Set<string>,
  aType: string | undefined,
  bType: string | undefined,
  aDeviceId: string,
  bDeviceId: string,
  aIface: string,
  bIface: string
): { aIface: string; bIface: string } => {
  const isOltOdf = (x?: string | null, y?: string | null) => x === 'OLT' && y === 'ODF'
  const odfSide = isOltOdf(aType, bType) ? bDeviceId : isOltOdf(bType, aType) ? aDeviceId : null
  if (!odfSide) return { aIface, bIface }
  const dev = devStore.byId(odfSide) as DeviceOutX | undefined
  const list = (dev?.interfaces || []) as Array<{ id: string; name: string; admin_status?: string }>
  const anchorId = `${odfSide}-if0`
  const anchorUp = list.find(
    (i) => i.id === anchorId && (i?.admin_status ?? 'up') === 'up' && !usedIfaces.has(i.id)
  )
  if (anchorUp) {
    if (odfSide === aDeviceId) aIface = anchorId
    else bIface = anchorId
  }
  return { aIface, bIface }
}

export const preferNonIf0ForOdfIfOntPassive = (
  devStore: ReturnType<typeof useDevicesStore>,
  usedIfaces: Set<string>,
  aType: string | undefined,
  bType: string | undefined,
  aDeviceId: string,
  bDeviceId: string,
  aIface: string,
  bIface: string
): { aIface: string; bIface: string } => {
  const odfDeviceId =
    isPassive(aType) && isOntFamily(bType)
      ? aDeviceId
      : isPassive(bType) && isOntFamily(aType)
        ? bDeviceId
        : null
  if (!odfDeviceId) return { aIface, bIface }
  const dev = devStore.byId(odfDeviceId) as DeviceOutX | undefined
  const ifaces = (
    (dev?.interfaces || []) as Array<{ id: string; name: string; admin_status?: string }>
  ).filter((i) => (i?.admin_status ?? 'up') === 'up' && !usedIfaces.has(i.id))
  const nonIf0 = ifaces.find((i) => i.id !== `${odfDeviceId}-if0`)
  if (nonIf0) {
    if (odfDeviceId === aDeviceId) aIface = nonIf0.id
    else bIface = nonIf0.id
  }
  return { aIface, bIface }
}

export const getOptions = (
  devStore: ReturnType<typeof useDevicesStore>,
  devId: string,
  selectedId: string,
  usedIfaces: Set<string>
): Option[] => {
  const dev = devStore.byId(devId) as DeviceOutX | undefined
  const list = (dev?.interfaces || []) as IfaceLite[]
  const sel = list.find((i) => i.id === selectedId)
  const selectedPortRole = sel ? getPortRole(sel) : null
  const avail = list.filter((i) => i && !isMgmt(i) && isUp(i) && !usedIfaces.has(i.id))
  let filtered = avail.filter((i) => getPortRole(i) === selectedPortRole)
  if (!filtered.length && sel?.role) {
    filtered = avail.filter((i) => i.role === sel.role)
  }
  if (!filtered.length) filtered = avail.slice()
  if (!filtered.length) {
    const if0 = list.find((i) => i.id === `${devId}-if0` && isUp(i) && !usedIfaces.has(i.id))
    if (if0) filtered = [if0]
  }
  const opts: Option[] = filtered.map((i) => ({ id: i.id, label: i.name }))
  if (sel && !opts.find((o) => o.id === sel.id)) {
    if (!isMgmt(sel) && isUp(sel) && !usedIfaces.has(sel.id)) {
      opts.unshift({ id: sel.id, label: sel.name })
    }
  }
  if (!opts.length) {
    const if0 = `${devId}-if0`
    opts.push({ id: if0, label: 'if0' })
  }
  return opts
}

export const filterPONForOLT = (
  links: Link[],
  devStore: ReturnType<typeof useDevicesStore>,
  devId: string,
  opts: Option[]
): Option[] => {
  const dev = devStore.byId(devId) as DeviceOutX | undefined
  const ifaces = (dev?.interfaces || []) as Array<{
    id: string
    name: string
    port_role?: string | null
  }>
  const ponPorts = (ifaces || []).filter((i) => (i.port_role || '') === 'PON').map((i) => i.id)
  const linkedPon = new Set<string>()
  for (const l of links) {
    const isFromThisOlt = l.a_device_id === devId || l.b_device_id === devId
    if (!isFromThisOlt) continue
    if (l.a_device_id === devId && ponPorts.includes(l.a_interface_id))
      linkedPon.add(l.a_interface_id)
    if (l.b_device_id === devId && ponPorts.includes(l.b_interface_id))
      linkedPon.add(l.b_interface_id)
  }
  const ponSet = new Set(ponPorts.filter((iid) => !linkedPon.has(iid)))
  if (!ponSet.size) return opts
  return opts.filter((o) => ponSet.has(o.id))
}

export const lockOdfOptionsForOltPair = (
  aType: string | undefined,
  bType: string | undefined,
  aDeviceId: string,
  bDeviceId: string,
  aIface: string,
  bIface: string,
  aOptions: Option[],
  bOptions: Option[]
): { aIface: string; bIface: string; aOptions: Option[]; bOptions: Option[] } => {
  const isOltOdf = (x?: string | null, y?: string | null) => x === 'OLT' && y === 'ODF'
  const odfSide = isOltOdf(aType, bType) ? bDeviceId : isOltOdf(bType, aType) ? aDeviceId : null
  if (!odfSide) return { aIface, bIface, aOptions, bOptions }
  const anchor = `${odfSide}-if0`
  if (odfSide === aDeviceId) {
    aIface = anchor
    aOptions = [{ id: anchor, label: 'if0' }]
  } else {
    bIface = anchor
    bOptions = [{ id: anchor, label: 'if0' }]
  }
  return { aIface, bIface, aOptions, bOptions }
}

export const phase1GuardsOk = (
  links: Link[],
  devStore: ReturnType<typeof useDevicesStore>,
  aDeviceId: string,
  bDeviceId: string,
  aType: string | undefined,
  bType: string | undefined
): boolean => {
  const phase1Flag =
    (globalThis as unknown as { UNOC_FLAGS?: Record<string, unknown> })?.UNOC_FLAGS?.[
      'GPON_ODF_AGG_PHASE1'
    ] ||
    (import.meta as unknown as { env?: Record<string, unknown> })?.env?.['VITE_GPON_ODF_AGG_PHASE1']
  const isPhase1Enabled =
    String(phase1Flag).toLowerCase() === '1' || String(phase1Flag).toLowerCase() === 'true'
  if (!isPhase1Enabled) return true

  const aIsOlt = aType === 'OLT'
  const bIsOlt = bType === 'OLT'
  const aIsOnt = isOntFamily(aType)
  const bIsOnt = isOntFamily(bType)
  if ((aIsOlt && bIsOnt) || (bIsOlt && aIsOnt)) {
    console.warn('[linksStore] Phase1: direct OLT↔ONT not allowed; connect via ODF')
    return false
  }
  if ((aIsOlt && bType !== 'ODF') || (bIsOlt && aType !== 'ODF')) {
    console.warn('[linksStore] Phase1: OLT must connect to ODF (peer type invalid)')
    return false
  }
  const isPassiveType = (t?: string | null) =>
    !!t && ['ODF', 'NVT', 'SPLITTER', 'HOP'].includes(String(t))
  if (aIsOnt && !isPassiveType(bType)) {
    console.warn('[linksStore] Phase1: ONT must connect to a passive device (ODF/NVT/SPLITTER/HOP)')
    return false
  }
  if (bIsOnt && !isPassiveType(aType)) {
    console.warn('[linksStore] Phase1: ONT must connect to a passive device (ODF/NVT/SPLITTER/HOP)')
    return false
  }
  if (aIsOnt && isPassiveType(bType) && bType !== 'ODF') {
    const ok = validateOntPassive({ links }, devStore, aDeviceId, bDeviceId)
    if (!ok) {
      console.warn(
        '[linksStore] ONT↔passive allowed only within an ODF-headed path (no upstream ODF→OLT found)'
      )
      return false
    }
  }
  if (bIsOnt && isPassiveType(aType) && aType !== 'ODF') {
    const ok = validateOntPassive({ links }, devStore, bDeviceId, aDeviceId)
    if (!ok) {
      console.warn(
        '[linksStore] ONT↔passive allowed only within an ODF-headed path (no upstream ODF→OLT found)'
      )
      return false
    }
  }
  return true
}

export const computeSelections = (
  devStore: ReturnType<typeof useDevicesStore>,
  links: Link[],
  aDeviceId: string,
  bDeviceId: string
): {
  aType: string | undefined
  bType: string | undefined
  aIface: string
  bIface: string
  aOptions: Option[]
  bOptions: Option[]
} => {
  const aType = String(devStore.byId(aDeviceId)?.type || '') || undefined
  const bType = String(devStore.byId(bDeviceId)?.type || '') || undefined
  const usedIfaces = buildUsedInterfaceSet(links)
  const pickInterfaceLocal = (devId: string) => pickInterface(devStore, devId, usedIfaces)
  const pickWithRoleLocal = (
    devId: string,
    preferred: 'ACCESS' | 'UPLINK' | 'PON' | 'TRUNK' | null
  ) => pickWithRole(devStore, devId, usedIfaces, preferred)

  let aIface: string
  let bIface: string
  if (
    (aType === 'AON_CPE' && bType === 'AON_SWITCH') ||
    (bType === 'AON_CPE' && aType === 'AON_SWITCH')
  ) {
    aIface =
      aType === 'AON_SWITCH'
        ? pickWithRoleLocal(aDeviceId, 'ACCESS')
        : pickInterfaceLocal(aDeviceId)
    bIface =
      bType === 'AON_SWITCH'
        ? pickWithRoleLocal(bDeviceId, 'ACCESS')
        : pickInterfaceLocal(bDeviceId)
  } else if (
    (aType === 'OLT' &&
      ['ONT', 'BUSINESS_ONT', 'SPLITTER', 'HOP', 'NVT', 'ODF'].includes(String(bType))) ||
    (bType === 'OLT' &&
      ['ONT', 'BUSINESS_ONT', 'SPLITTER', 'HOP', 'NVT', 'ODF'].includes(String(aType)))
  ) {
    aIface = aType === 'OLT' ? pickWithRoleLocal(aDeviceId, 'PON') : pickInterfaceLocal(aDeviceId)
    bIface = bType === 'OLT' ? pickWithRoleLocal(bDeviceId, 'PON') : pickInterfaceLocal(bDeviceId)
  } else {
    aIface = pickInterfaceLocal(aDeviceId)
    bIface = pickInterfaceLocal(bDeviceId)
  }

  ;({ aIface, bIface } = anchorOdfIf0ForOltPair(
    devStore,
    usedIfaces,
    aType,
    bType,
    aDeviceId,
    bDeviceId,
    aIface,
    bIface
  ))
  ;({ aIface, bIface } = preferNonIf0ForOdfIfOntPassive(
    devStore,
    usedIfaces,
    aType,
    bType,
    aDeviceId,
    bDeviceId,
    aIface,
    bIface
  ))

  let aOptions: Option[] = getOptions(devStore, aDeviceId, aIface, usedIfaces)
  let bOptions: Option[] = getOptions(devStore, bDeviceId, bIface, usedIfaces)

  ;({ aIface, bIface, aOptions, bOptions } = lockOdfOptionsForOltPair(
    aType,
    bType,
    aDeviceId,
    bDeviceId,
    aIface,
    bIface,
    aOptions,
    bOptions
  ))

  const isOntOrPassive = (t?: string) =>
    !!t && ['ONT', 'BUSINESS_ONT', 'SPLITTER', 'HOP', 'NVT', 'ODF'].includes(String(t))
  const isOltOntOrPassive =
    (aType === 'OLT' && isOntOrPassive(bType)) || (bType === 'OLT' && isOntOrPassive(aType))
  if (isOltOntOrPassive) {
    if (aType === 'OLT') aOptions = filterPONForOLT(links, devStore, aDeviceId, aOptions)
    if (bType === 'OLT') bOptions = filterPONForOLT(links, devStore, bDeviceId, bOptions)
    if (aType === 'OLT' && aOptions.length && !aOptions.find((o) => o.id === aIface)) {
      aIface = aOptions[0].id
    }
    if (bType === 'OLT' && bOptions.length && !bOptions.find((o) => o.id === bIface)) {
      bIface = bOptions[0].id
    }
  }

  if (isPassive(aType) && isOntFamily(bType)) {
    aOptions = annotatePassiveOptionsViaOlt({ links }, devStore, aDeviceId, aOptions)
  } else if (isPassive(bType) && isOntFamily(aType)) {
    bOptions = annotatePassiveOptionsViaOlt({ links }, devStore, bDeviceId, bOptions)
  }

  return { aType, bType, aIface, bIface, aOptions, bOptions }
}
