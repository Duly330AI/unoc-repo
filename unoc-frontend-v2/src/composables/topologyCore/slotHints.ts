import * as d3 from 'd3'
import { getContainerLayout } from '../../config/containerLayouts.js'

export function ensureSlotHintsLayer(svgEl: SVGSVGElement) {
  const svg = d3.select(svgEl)
  const linksLayer = svg.select('g.links-layer')
  let parentGroup
  if (!linksLayer.empty()) {
    parentGroup = d3.select((linksLayer.node() as SVGGElement).parentNode as SVGGElement)
  } else {
    parentGroup = svg.append('g')
  }
  let layer = parentGroup.select('g.slot-hints-layer')
  if (layer.empty()) {
    layer = parentGroup.append('g').attr('class', 'slot-hints-layer')
  }
  return layer
}

export function clearSlotHints(svgEl?: SVGSVGElement | null) {
  if (!svgEl) return
  const svg = d3.select(svgEl)
  const linksLayer = svg.select('g.links-layer')
  let parentGroup
  if (!linksLayer.empty()) {
    parentGroup = d3.select((linksLayer.node() as SVGGElement).parentNode as SVGGElement)
    parentGroup.select('g.slot-hints-layer').selectAll('*').remove()
  } else {
    svg.select('g.slot-hints-layer').selectAll('*').remove()
  }
}

export function findContainerAtPoint(
  gx: number,
  gy: number,
  layoutCache: Record<string, { x: number; y: number; type?: string }>,
  svgRef?: { value: SVGSVGElement | null }
) {
  const svgEl = svgRef?.value
  for (const [id, lc] of Object.entries(layoutCache)) {
    const type = lc.type
    if (type !== 'POP' && type !== 'CORE_SITE') continue
    const layout = getContainerLayout(type)
    if (!layout) continue
    let minX: number, minY: number, maxX: number, maxY: number
    if (svgEl) {
      const el = (svgEl.ownerDocument || document).getElementById(`container-${id}`)
      if (el) {
        try {
          const bb = (el as unknown as SVGGElement).getBBox()
          minX = lc.x + bb.x
          minY = lc.y + bb.y
          maxX = minX + bb.width
          maxY = minY + bb.height
        } catch {
          const halfW = layout.size.width / 2
          const halfH = layout.size.height / 2
          minX = lc.x - halfW
          maxX = lc.x + halfW
          minY = lc.y - halfH
          maxY = lc.y + halfH
        }
      } else {
        const halfW = layout.size.width / 2
        const halfH = layout.size.height / 2
        minX = lc.x - halfW
        maxX = lc.x + halfW
        minY = lc.y - halfH
        maxY = lc.y + halfH
      }
    } else {
      const halfW = layout.size.width / 2
      const halfH = layout.size.height / 2
      minX = lc.x - halfW
      maxX = lc.x + halfW
      minY = lc.y - halfH
      maxY = lc.y + halfH
    }
    if (gx >= minX && gx <= maxX && gy >= minY && gy <= maxY) {
      return { id, type, layout, cx: lc.x, cy: lc.y }
    }
  }
  return null
}
