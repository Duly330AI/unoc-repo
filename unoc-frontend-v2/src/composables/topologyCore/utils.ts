/* eslint-disable @typescript-eslint/no-explicit-any */

export function layoutPositions(count: number) {
  const positions: { x: number; y: number }[] = []
  const spacingX = 70,
    spacingY = 70,
    perRow = 10
  for (let i = 0; i < count; i++) {
    const row = Math.floor(i / perRow)
    const col = i % perRow
    positions.push({ x: 50 + col * spacingX, y: 50 + row * spacingY })
  }
  return positions
}

export function colorForType(t: string) {
  switch (t) {
    case 'POP':
      return '#1976d2'
    case 'BACKBONE_GATEWAY':
      return '#512da8'
    case 'CORE_ROUTER':
      return '#388e3c'
    case 'EDGE_ROUTER':
      return '#00796b'
    case 'AON_SWITCH':
      return '#00838f'
    case 'OLT':
      return '#455a64'
    case 'ONT':
      return '#5d4037'
    case 'AON_CPE':
      return '#795548'
    case 'BUSINESS_ONT':
      return '#6e2f2f'
    case 'SPLITTER':
      return '#6d4c41'
    case 'ODF':
      return '#4e342e'
    case 'NVT':
      return '#5e493d'
    case 'HOP':
      return '#546e7a'
    default:
      return '#757575'
  }
}

export function ghostFill(t: string) {
  return colorForType(t) + '66'
}

export function linkStatus(d: any) {
  const s = (d.admin_override_status || d.status || '').toLowerCase()
  if (['up', 'ok', 'active'].includes(s)) return 'up'
  if (['down', 'failed', 'error'].includes(s)) return 'down'
  if (['degraded', 'warn', 'warning'].includes(s)) return 'degraded'
  return 'unknown'
}

export function linkKind(d: any) {
  return (d.kind || 'generic').toLowerCase().replace(/[^a-z0-9_]+/g, '_')
}

export type {}
