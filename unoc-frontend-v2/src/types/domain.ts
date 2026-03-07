// AUTO-GENERATED FILE – DO NOT EDIT
// Hash: 97dbfeef0155
// Source: tools/gen_ts_types.py

/* eslint-disable */
export type DeviceType =
  | 'AON_CPE'
  | 'AON_SWITCH'
  | 'BACKBONE_GATEWAY'
  | 'BUSINESS_ONT'
  | 'CORE_ROUTER'
  | 'EDGE_ROUTER'
  | 'HOP'
  | 'NVT'
  | 'ODF'
  | 'OLT'
  | 'ONT'
  | 'POP'
  | 'SPLITTER'

export type LinkType = 'FIBER' | 'MGMT' | 'P2P'

export type Status = 'BLOCKING' | 'DEGRADED' | 'DOWN' | 'UP'

export type DeviceRole = 'active' | 'always_online' | 'passive'

export type InterfaceRole = 'access' | 'management' | 'p2p_uplink'

export type AdminStatus = 'down' | 'up'

export interface DeviceOut {
  admin_override_status?: any
  device_default_vrf_name?: any
  hardware_model_id?: any
  id: string
  insertion_loss_db?: any
  interfaces?: any
  name: string
  parameters?: any
  parent_container_id?: any
  slot_id?: any
  provisioned: boolean
  role: DeviceRole
  sensitivity_min_dbm?: any
  signal_margin_db?: any
  signal_power_dbm?: any
  signal_status?: any
  status: Status
  tariff_id?: any
  tx_power_dbm?: any
  type: DeviceType
}

export interface InterfaceOut {
  admin_status: AdminStatus
  capacity?: any
  device_id: string
  id: string
  mac_address?: any
  name: string
  role?: any
  status: Status
}

export interface LinkOut {
  a_interface_id: string
  admin_override_status?: any
  b_interface_id: string
  id: string
  kind: LinkType
  length_km?: any
  physical_medium_id?: any
  protection_mode?: any
  status: Status
}

export interface LinkResolvedOut {
  a_device_id: string
  a_interface_id: string
  admin_override_status?: any
  b_device_id: string
  b_interface_id: string
  id: string
  kind: LinkType
  length_km?: any
  physical_medium_id?: any
  protection_mode?: any
  rule_id?: any
  status: Status
}

export interface TariffOut {
  id: number
  max_down_mbps: number
  max_up_mbps: number
  name: string
}
