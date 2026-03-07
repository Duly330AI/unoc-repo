/* eslint-disable @typescript-eslint/no-explicit-any */
import { getContainerLayout } from '../../config/containerLayouts.js'

export type ForceNode = {
  id: string
  type: string
  x: number
  y: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
}

export function containerBoundsForce(opts: {
  getLayoutCache: () => Record<string, { x: number; y: number; type?: string }>
  getDevices: () => Array<{ id: string; type: string; parent_container_id?: string | null }>
  padding?: number
  slotAttraction?: number
  velocityDamping?: number
}) {
  const padding = opts.padding ?? 8
  const slotAttraction = opts.slotAttraction ?? 0.02 // very weak pull
  const velocityDamping = opts.velocityDamping ?? 0.85 // damp when clamped

  let nodes: ForceNode[] = []
  let nodeById: Map<string, ForceNode> = new Map()

  function force() {
    const layoutCache = opts.getLayoutCache()
    const devs = opts.getDevices()
    const devById = new Map(devs.map((d) => [d.id, d]))

    for (const n of nodes) {
      const dev = devById.get(n.id)
      if (!dev) continue
      const parentId = (dev as any).parent_container_id as string | null | undefined
      if (!parentId) continue
      const parentNode = nodeById.get(parentId)
      const parentLc = layoutCache[parentId]
      const parentX = parentNode?.x ?? parentLc?.x
      const parentY = parentNode?.y ?? parentLc?.y
      const parentType = (parentLc as any)?.type as string | undefined
      if (parentX == null || parentY == null || !parentType) continue
      const layout = getContainerLayout(parentType)
      if (!layout) continue

      const halfW = layout.size.width / 2
      const halfH = layout.size.height / 2
      const minX = parentX - halfW + padding
      const maxX = parentX + halfW - padding
      const minY = parentY - halfH + padding
      const maxY = parentY + halfH - padding

      let clamped = false
      if (n.x < minX) {
        n.x = minX
        clamped = true
      } else if (n.x > maxX) {
        n.x = maxX
        clamped = true
      }
      if (n.y < minY) {
        n.y = minY
        clamped = true
      } else if (n.y > maxY) {
        n.y = maxY
        clamped = true
      }

      if (clamped) {
        // damp velocity to avoid bouncing out repeatedly
        n.vx = (n.vx || 0) * velocityDamping
        n.vy = (n.vy || 0) * velocityDamping
      }

      // tiny pull to nearest slot anchor, but never override user pin (fx/fy)
      if (n.fx == null && n.fy == null) {
        // derive index by sorted children order for deterministic target
        const siblings = devs
          .filter((d) => (d as any).parent_container_id === parentId)
          .slice()
          .sort((a, b) => a.id.localeCompare(b.id))
        const idx = Math.max(
          0,
          siblings.findIndex((d) => d.id === n.id)
        )
        const slot = layout.slots[idx % layout.slots.length]
        const targetX = parentX - halfW + slot.x
        const targetY = parentY - halfH + slot.y
        // apply very small drift toward target
        n.vx = (n.vx || 0) + (targetX - n.x) * slotAttraction
        n.vy = (n.vy || 0) + (targetY - n.y) * slotAttraction
      }
    }
  }

  force.initialize = function (_nodes: ForceNode[]) {
    nodes = _nodes
    nodeById = new Map(nodes.map((n) => [n.id, n]))
  }

  return force as any
}
