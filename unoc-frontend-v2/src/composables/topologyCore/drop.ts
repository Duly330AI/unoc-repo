/* eslint-disable @typescript-eslint/no-explicit-any */
import type { Device } from '../../types/topology.js'
import * as d3 from 'd3'
import { getContainerLayout } from '../../config/containerLayouts.js'

export function toGraphCoords(
  t: { x: number; y: number; k: number | undefined },
  sx: number,
  sy: number
) {
  const k = t.k || 1
  return { gx: (sx - t.x) / k, gy: (sy - t.y) / k }
}

export function createDropHandler(
  svgRef: { value: SVGSVGElement | null },
  getLayoutCache: () => Record<string, any>,
  devices: any,
  selection: any,
  ghosts: Array<any>,
  toasts: any,
  redraw: () => void,
  queuePositions: (ids: string[]) => void,
  fastRefreshNodes: (ids: string[]) => void,
  openHardwareSelector: (
    ctx: {
      type: string
      suggestedId: string
      screen: { x: number; y: number }
      graph: { x: number; y: number }
      parentId: string | null
    },
    confirm: (hardwareModelId: number | null) => Promise<void>,
    cancel: () => void
  ) => void = (ctx, confirm) => confirm(null)
) {
  function detectContainer(x: number, y: number) {
    const layoutCache = getLayoutCache() as Record<string, { x: number; y: number; type?: string }>
    const svgEl = svgRef.value
    for (const [id, info] of Object.entries(layoutCache)) {
      const inf: any = info
      if (inf.type === 'POP' || inf.type === 'CORE_SITE') {
        const layout = getContainerLayout(inf.type)
        if (!layout) continue
        let minX: number, minY: number, maxX: number, maxY: number
        if (svgEl) {
          const el = (svgEl.ownerDocument || document).getElementById(`container-${id}`)
          if (el) {
            try {
              const bb = (el as unknown as SVGGElement).getBBox()
              minX = inf.x + bb.x
              minY = inf.y + bb.y
              maxX = minX + bb.width
              maxY = minY + bb.height
            } catch {
              const halfW = layout.size.width / 2
              const halfH = layout.size.height / 2
              minX = inf.x - halfW
              maxX = inf.x + halfW
              minY = inf.y - halfH
              maxY = inf.y + halfH
            }
          } else {
            const halfW = layout.size.width / 2
            const halfH = layout.size.height / 2
            minX = inf.x - halfW
            maxX = inf.x + halfW
            minY = inf.y - halfH
            maxY = inf.y + halfH
          }
        } else {
          const halfW = layout.size.width / 2
          const halfH = layout.size.height / 2
          minX = inf.x - halfW
          maxX = inf.x + halfW
          minY = inf.y - halfH
          maxY = inf.y + halfH
        }
        if (x >= minX && x <= maxX && y >= minY && y <= maxY) return id
      }
    }
    return null
  }

  function resolveParentFor(type: string, hitParent: string | null) {
    // Hardened rule: Only assign a parent when the cursor is strictly over a container
    // Parentable types: OLT, AON_SWITCH. Others are always standalone on creation.
    if (type === 'OLT' || type === 'AON_SWITCH') return hitParent
    return null
  }

  function onDrop(ev: DragEvent) {
    const type =
      ev.dataTransfer?.getData('application/x-unoc-device-type') ||
      ev.dataTransfer?.getData('text/plain')
    if (!type) return
    const svgEl = svgRef.value
    if (!svgEl) return
    const rect = svgEl.getBoundingClientRect()
    // Screen-space coordinates relative to the SVG viewport
    const sx = ev.clientX - rect.left
    const sy = ev.clientY - rect.top
    // Current zoom/pan transform (applied to the zoom root via d3)
    const t = d3.zoomTransform(svgEl as unknown as Element)
    // Convert to graph-space coordinates by inverting the transform
    const { gx, gy } = toGraphCoords(t as unknown as { x: number; y: number; k: number }, sx, sy)
    const hitParent = detectContainer(gx, gy)
    const parentId = resolveParentFor(type, hitParent)
    const base = type.toLowerCase().replace(/[^a-z0-9]+/g, '_')
    let id = base
    let counter = 1
    while (devices.devices.some((d: any) => d.id === id) || ghosts.some((g) => g.baseId === id)) {
      id = `${base}_${counter++}`
    }
    const localGhostId = `ghost_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    // Keep ghost in screen space so it visually matches the cursor
    ghosts.push({ localId: localGhostId, x: sx, y: sy, type, baseId: id })
    const confirm = async (hardwareModelId: number | null) => {
      try {
        await devices.create({
          id,
          name: id,
          type,
          parent_container_id: parentId || undefined,
          hardware_model_id: hardwareModelId ?? undefined
        })
        const idx = ghosts.findIndex((g) => g.localId === localGhostId)
        if (idx >= 0) ghosts.splice(idx, 1)
        const layoutCache = getLayoutCache()
        // If created inside or over a container, compute nearest free slot
        if (
          (parentId && (type === 'OLT' || type === 'AON_SWITCH')) ||
          (hitParent && type !== 'OLT' && type !== 'AON_SWITCH')
        ) {
          const parentLikeId = parentId || hitParent
          const parentInfo2: any = layoutCache[parentLikeId as string]
          const layout = getContainerLayout(parentInfo2?.type)
          if (parentInfo2 && layout) {
            const children = (devices.devices as Device[]).filter(
              (x: any) => (x as any).parent_container_id === parentLikeId
            )
            const occupied = new Set<string>(
              (children as any[])
                .map((c: any) => c.slot_id)
                .filter((sid: any) => typeof sid === 'string' && sid.length > 0)
            )
            let best: any = null
            let bestD2 = Infinity
            for (const s of layout.slots) {
              const sid = String(s.id)
              if (occupied.has(sid)) continue
              const sx2 = parentInfo2.x - layout.size.width / 2 + s.x
              const sy2 = parentInfo2.y - layout.size.height / 2 + s.y
              const dx2 = sx2 - gx
              const dy2 = sy2 - gy
              const d2 = dx2 * dx2 + dy2 * dy2
              if (d2 < bestD2) {
                bestD2 = d2
                best = { ...s, sid, absx: sx2, absy: sy2 }
              }
            }
            const target = best || layout.slots[0]
            const px = best ? best.absx : parentInfo2.x - layout.size.width / 2 + target.x
            const py = best ? best.absy : parentInfo2.y - layout.size.height / 2 + target.y
            layoutCache[id] = { x: px, y: py, type, pinned: true }
            // If parenting is required, persist slot_id immediately
            if (parentId && (type === 'OLT' || type === 'AON_SWITCH')) {
              try {
                await devices.update(id, {
                  parent_container_id: parentId as any,
                  slot_id: (best ? best.sid : String(target.id)) as any
                })
              } catch {
                /* ignore */
              }
            }
          } else {
            layoutCache[id] = { x: gx, y: gy, type, pinned: true }
          }
        } else {
          layoutCache[id] = { x: gx, y: gy, type, pinned: true }
        }
        fastRefreshNodes([id])
        queuePositions([id])
        redraw()
      } catch (err: any) {
        const idx = ghosts.findIndex((g) => g.localId === localGhostId)
        if (idx >= 0) ghosts.splice(idx, 1)
        toasts.push(`Device create failed: ${err?.message || err}`, 'error')
      }
    }
    const cancel = () => {
      const idx = ghosts.findIndex((g) => g.localId === localGhostId)
      if (idx >= 0) ghosts.splice(idx, 1)
    }
    openHardwareSelector(
      { type, suggestedId: id, screen: { x: sx, y: sy }, graph: { x: gx, y: gy }, parentId },
      confirm,
      cancel
    )
  }

  return { onDrop }
}
