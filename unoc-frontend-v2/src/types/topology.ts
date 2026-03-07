// Domain types for topology canvas & related composables

export interface Device {
  id: string
  name: string
  type: string
  parent_container_id?: string
  slot_id?: string
  status?: string
  admin_override_status?: string
  // Optical
  signal_status?: 'OK' | 'WARNING' | 'CRITICAL' | 'NO_SIGNAL' | null
  signal_power_dbm?: number | null
  signal_margin_db?: number | null
  tx_power_dbm?: number | null
  sensitivity_min_dbm?: number | null
}

export interface LinkRecord {
  id: string
  a_device_id: string
  b_device_id: string
  kind?: string
  status?: string
  admin_override_status?: string
}

export interface LayoutEntry {
  x: number
  y: number
  type: string
  pinned?: boolean
}

export interface LayoutSnapshotEntry {
  id: string
  x: number
  y: number
  userPinned?: boolean
}

export interface DragState {
  id: string | null
  offsetX: number
  offsetY: number
  origX: number
  origY: number
  active: boolean
  moved: boolean
  throttleAt: number
  multi: boolean
  others: string[]
  lastPersistAt: number
}

export interface LinkToolState {
  active: boolean
  startDevice: string | null
  hoverDevice: string | null
  mode?: 'single' | 'multi'
  sources?: string[]
}

export interface LayoutStacksDetail {
  undo: number
  redo: number
}
