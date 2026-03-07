/* eslint-disable @typescript-eslint/no-explicit-any */
import { useTooltipStore } from '../../stores/tooltipStore.js'
import * as d3 from 'd3'
import { useDevicesStore } from '../../stores/devicesStore.js'
import { ensureSlotHintsLayer, clearSlotHints, findContainerAtPoint } from './slotHints.js'

export interface DragState {
  id: string | null
  origX: number
  origY: number
  offsetX: number
  offsetY: number
  active: boolean
  moved: boolean
  multi: boolean
  others: string[]
  othersStart: Record<string, { x: number; y: number }>
  lastX: number
  lastY: number
}

export function createDragController(
  getLayoutCache: () => Record<string, any>,
  selection: any,
  pushUndo: (ids: string[]) => void,
  queuePositions: (ids: string[]) => void,
  fastRefreshNodes: (ids: string[]) => void,
  svgRef?: { value: SVGSVGElement | null }
) {
  const dragState: DragState = {
    id: null,
    origX: 0,
    origY: 0,
    offsetX: 0,
    offsetY: 0,
    active: false,
    moved: false,
    multi: false,
    others: [],
    othersStart: {},
    lastX: 0,
    lastY: 0
  }

  // Helpers moved to slotHints.ts

  function dragMove(ev: MouseEvent) {
    if (!dragState.active || !dragState.id) return
    const layoutCache = getLayoutCache()
    const id = dragState.id
    const devices = useDevicesStore()
    const lc = layoutCache[id]
    // Convert mouse to graph coords using inverse zoom transform
    const svgEl = svgRef?.value
    const t = svgEl ? d3.zoomTransform(svgEl as unknown as Element) : ({ x: 0, y: 0, k: 1 } as any)
    const rect = svgEl ? svgEl.getBoundingClientRect() : ({ left: 0, top: 0 } as any)
    const sx = ev.clientX - rect.left
    const sy = ev.clientY - rect.top
    const gx = (sx - t.x) / (t.k || 1)
    const gy = (sy - t.y) / (t.k || 1)
    let newX = gx - dragState.offsetX
    let newY = gy - dragState.offsetY
    // Compute deltas since drag start for multi-drag
    const dxFromStart = newX - dragState.origX
    const dyFromStart = newY - dragState.origY
    // Update primary
    lc.x = newX
    lc.y = newY
    // Update others based on their baseline positions captured at drag start
    if (dragState.multi) {
      dragState.others.forEach((o) => {
        const oLc = layoutCache[o]
        const base = dragState.othersStart[o]
        if (oLc && base) {
          oLc.x = base.x + dxFromStart
          oLc.y = base.y + dyFromStart
        }
      })
    }
    dragState.moved = true
    dragState.lastX = newX
    fastRefreshNodes([id, ...dragState.others])

    // Highlight available slots when hovering over a valid container for certain device types
    if (svgEl) {
      const cont = findContainerAtPoint(gx, gy, layoutCache)
      const draggingDev = devices.byId(id)
      const canNest =
        draggingDev &&
        (draggingDev.type === 'OLT' ||
          draggingDev.type === 'AON_SWITCH' ||
          draggingDev.type === 'CORE_ROUTER' ||
          draggingDev.type === 'EDGE_ROUTER' ||
          draggingDev.type === 'BACKBONE_GATEWAY')
      if (cont && canNest) {
        const layer = ensureSlotHintsLayer(svgEl)
        const children = devices.devices.filter((d: any) => d.parent_container_id === cont.id)
        const occupiedSlotIds = new Set<string>(
          children
            .map((c: any) => c.slot_id)
            .filter((sid: any) => typeof sid === 'string' && sid.length > 0)
        )
        const hintW = Math.max(24, Math.round((cont.layout.slotBox.width || 240) * 0.18))
        const hintH = Math.max(16, Math.round((cont.layout.slotBox.height || 140) * 0.18))
        const slots = cont.layout.slots.map((s: any) => ({
          id: s.id as string,
          x: cont.cx - cont.layout.size.width / 2 + cont.layout.slotOffset.x + (s.x as number),
          y: cont.cy - cont.layout.size.height / 2 + cont.layout.slotOffset.y + (s.y as number),
          free: !occupiedSlotIds.has(String(s.id)),
          hintW,
          hintH
        }))
        // Determine nearest free slot to cursor
        let nearestIdx = -1
        let nearestDist = Infinity
        slots.forEach((s: any, idx: number) => {
          if (!s.free) return
          const dx = s.x - gx
          const dy = s.y - gy
          const d2 = dx * dx + dy * dy
          if (d2 < nearestDist) {
            nearestDist = d2
            nearestIdx = idx
          }
        })
        const sel = layer
          .selectAll('rect.slot-hint')
          .data(slots as any, (d: any) => `${cont.id}_${d.id}`)
        sel.exit().remove()
        sel
          .enter()
          .append('rect')
          .attr('class', 'slot-hint')
          .attr('width', (d: any) => d.hintW)
          .attr('height', (d: any) => d.hintH)
          .attr('rx', 3)
          .attr('ry', 3)
          .attr('fill', 'none')
          .attr('pointer-events', 'none')
          .merge(sel as any)
          .attr('x', (d: any) => d.x - d.hintW / 2)
          .attr('y', (d: any) => d.y - d.hintH / 2)
          .attr('stroke-width', (d: any, i: number) => (i === nearestIdx ? 3 : 1.5))
          .attr('stroke', (d: any, i: number) => {
            if (!d.free) return '#9e9e9e'
            return i === nearestIdx ? '#2e7d32' : '#66bb6a'
          })
        // Visually snap while hovering over container to nearest free slot
        if (nearestIdx >= 0) {
          lc.x = slots[nearestIdx].x
          lc.y = slots[nearestIdx].y
          newX = lc.x
          newY = lc.y
          dragState.lastX = newX
          dragState.lastY = newY
          fastRefreshNodes([id, ...dragState.others])
        }
      } else {
        clearSlotHints(svgEl)
      }
    }
  }

  async function dragEnd() {
    if (dragState.active && dragState.moved && dragState.id) {
      const all = [dragState.id, ...dragState.others]
      const layoutCache = getLayoutCache()
      all.forEach((id) => (layoutCache[id].pinned = true))
      // If dragging a container, only persist container position; children are slot-anchored
      const devicesStore2 = useDevicesStore()
      const dragged = devicesStore2.byId(dragState.id)
      const isContainer = !!(
        dragged &&
        ((dragged as any).type === 'POP' || (dragged as any).type === 'CORE_SITE')
      )
      queuePositions(isContainer ? [dragState.id] : all)

      // Snap into container if applicable and update parent_container_id
      const svgEl = svgRef?.value
      try {
        if (svgEl && dragState.id) {
          const t = d3.zoomTransform(svgEl as unknown as Element)
          const rect = svgEl.getBoundingClientRect()
          const sx = (dragState.lastX + dragState.offsetX) * (t.k || 1) + t.x + rect.left
          const sy = (dragState.lastY + dragState.offsetY) * (t.k || 1) + t.y + rect.top
          const gx = (sx - rect.left - t.x) / (t.k || 1)
          const gy = (sy - rect.top - t.y) / (t.k || 1)
          const cont = findContainerAtPoint(gx, gy, layoutCache)
          const draggingDev = devicesStore2.byId(dragState.id)
          const canNest =
            draggingDev &&
            (draggingDev.type === 'OLT' ||
              draggingDev.type === 'AON_SWITCH' ||
              draggingDev.type === 'CORE_ROUTER' ||
              draggingDev.type === 'EDGE_ROUTER' ||
              draggingDev.type === 'BACKBONE_GATEWAY')
          if (cont && canNest) {
            const children = devicesStore2.devices.filter(
              (d: any) => d.parent_container_id === cont.id
            )
            const occupiedSlotIds = new Set<string>(
              children
                .map((c: any) => c.slot_id)
                .filter((sid: any) => typeof sid === 'string' && sid.length > 0)
            )
            // Pick nearest free slot to drop point (gx, gy)
            let best: any = null
            let bestD2 = Infinity
            for (const s of cont.layout.slots) {
              const sid = String(s.id)
              if (occupiedSlotIds.has(sid)) continue
              const sx =
                cont.cx - cont.layout.size.width / 2 + cont.layout.slotOffset.x + (s.x as number)
              const sy =
                cont.cy - cont.layout.size.height / 2 + cont.layout.slotOffset.y + (s.y as number)
              const dx = sx - gx
              const dy = sy - gy
              const d2 = dx * dx + dy * dy
              if (d2 < bestD2) {
                bestD2 = d2
                best = { ...s, absx: sx, absy: sy, sid }
              }
            }
            const slot = best || cont.layout.slots[0]
            const px = best
              ? best.absx
              : cont.cx - cont.layout.size.width / 2 + cont.layout.slotOffset.x + (slot.x as number)
            const py = best
              ? best.absy
              : cont.cy -
                cont.layout.size.height / 2 +
                cont.layout.slotOffset.y +
                (slot.y as number)
            const lc = layoutCache[dragState.id]
            lc.x = px
            lc.y = py
            fastRefreshNodes([dragState.id])
            // Persist parent for all supported child device types so they "stick" to containers
            const allowedChild =
              draggingDev.type === 'OLT' ||
              draggingDev.type === 'AON_SWITCH' ||
              draggingDev.type === 'CORE_ROUTER' ||
              draggingDev.type === 'EDGE_ROUTER' ||
              draggingDev.type === 'BACKBONE_GATEWAY'
            if (allowedChild) {
              await devicesStore2.update(dragState.id, {
                parent_container_id: cont.id as any,
                slot_id: (best ? best.sid : String(slot.id)) as any
              })
            }
          } else if (canNest && draggingDev && (draggingDev as any).parent_container_id) {
            // Dropped outside any container: explicitly clear parent/slot so device detaches
            try {
              await devicesStore2.update(dragState.id, {
                parent_container_id: null as any,
                slot_id: null as any
              })
            } catch {
              /* non-fatal */
            }
          }
        }
      } catch {
        /* non-fatal */
      } finally {
        clearSlotHints(svgEl)
      }
    }
    dragState.active = false
    dragState.id = null
    window.removeEventListener('mousemove', dragMove as any)
    window.dispatchEvent(new CustomEvent('unoc:dragState', { detail: { active: false } }))
  }

  function prepareDrag(ev: MouseEvent, id: string) {
    if (ev.button !== 0) return
    ev.stopPropagation()
    // Hide tooltip at the beginning of drag to avoid stuck overlays
    try {
      useTooltipStore().hide()
    } catch {
      /* noop */
    }
    const layoutCache = getLayoutCache()
    const lc = layoutCache[id]
    const multiSelIds = selection.items
      .filter((i: any) => i.kind === 'device')
      .map((i: any) => i.id)
    const devicesStore = useDevicesStore()
    const dragged = devicesStore.byId(id)
    const isContainer = !!(
      dragged &&
      ((dragged as any).type === 'POP' || (dragged as any).type === 'CORE_SITE')
    )
    const children = isContainer
      ? (devicesStore.devices as any[])
          .filter((d: any) => d.parent_container_id === id)
          .map((d) => d.id)
      : []
    dragState.multi = (multiSelIds.includes(id) && multiSelIds.length > 1) || isContainer
    dragState.others = isContainer
      ? children
      : dragState.multi
        ? multiSelIds.filter((i: string) => i !== id)
        : []
    // Only push undo for the primary id to avoid large stacks
    pushUndo([id])
    dragState.id = id
    // Establish offsets in graph space
    const svgEl = svgRef?.value
    const t = svgEl ? d3.zoomTransform(svgEl as unknown as Element) : ({ x: 0, y: 0, k: 1 } as any)
    const rect = svgEl ? svgEl.getBoundingClientRect() : ({ left: 0, top: 0 } as any)
    const sx = ev.clientX - rect.left
    const sy = ev.clientY - rect.top
    const gx = (sx - t.x) / (t.k || 1)
    const gy = (sy - t.y) / (t.k || 1)
    dragState.origX = lc.x
    dragState.origY = lc.y
    dragState.offsetX = gx - lc.x
    dragState.offsetY = gy - lc.y
    dragState.lastX = lc.x
    dragState.lastY = lc.y
    // Capture baseline positions for others
    dragState.othersStart = {}
    if (dragState.multi) {
      const layoutCache = getLayoutCache()
      dragState.others.forEach((o) => {
        const oLc = layoutCache[o]
        if (oLc) dragState.othersStart[o] = { x: oLc.x, y: oLc.y }
      })
    }
    dragState.active = true
    dragState.moved = false
    ;(window as any).addEventListener('mousemove', dragMove)
    ;(window as any).addEventListener('mouseup', dragEnd, { once: true })
    window.dispatchEvent(
      new CustomEvent('unoc:dragState', {
        detail: {
          active: true,
          id,
          multi: dragState.multi,
          count: dragState.multi ? dragState.others.length + 1 : 1
        }
      })
    )
  }

  return { dragState, dragMove, dragEnd, prepareDrag }
}
