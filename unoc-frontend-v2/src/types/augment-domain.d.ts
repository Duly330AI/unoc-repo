// Augment auto-generated domain types with fields currently returned by backend
// (Avoid editing domain.ts directly – it is generated.)
import './domain'

declare module './domain' {
  interface DeviceOut {
    parent_container_id?: string | null
    // Optical fields (TASK-035)
    signal_status?: 'OK' | 'WARNING' | 'CRITICAL' | 'NO_SIGNAL' | null
    signal_power_dbm?: number | null
    signal_margin_db?: number | null
    tx_power_dbm?: number | null
    sensitivity_min_dbm?: number | null
    // Non-schema UI helper (carried in events):
    total_path_attenuation_db?: number | null
    interfaces?: Array<{
      id: string
      name: string
      status: string
      role?: string | null
      ip_address?: string | null
    }>
  }
}
