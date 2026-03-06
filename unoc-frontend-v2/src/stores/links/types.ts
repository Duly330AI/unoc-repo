// Shared types and helpers for links store

// Normalization helper to strip enum style prefixes like 'Status.'
export const normalizeStatus = (s: unknown): string | undefined => {
  if (typeof s !== 'string') return undefined
  return s.startsWith('Status.') ? s.slice('Status.'.length) : s
}

export interface Link {
  id: string
  a_interface_id: string
  b_interface_id: string
  a_device_id: string
  b_device_id: string
  status: string
  effective_status?: string
  kind: string
  admin_override_status?: string | null
  // Optical fields
  length_km?: number | null
  // Physical layer (new)
  physical_medium_id?: number | null
}
