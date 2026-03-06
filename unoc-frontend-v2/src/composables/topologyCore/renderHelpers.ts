/* eslint-disable @typescript-eslint/no-explicit-any */
import * as d3 from 'd3'
import type { Device } from '../../types/topology.js'

export function fastRefreshNodes(
  svgRef: { value: SVGSVGElement | null },
  layoutCache: Record<string, any>,
  ids: string[]
) {
  if (!svgRef.value) return
  const svg = d3.select(svgRef.value)
  ids.forEach((id) => {
    const lc = layoutCache[id]
    // Move the full device group (Vue cockpit wrapper)
    svg
      .selectAll('g.device-node')
      .filter((d: Device) => d.id === id)
      .attr('transform', `translate(${lc.x},${lc.y})`)
      .attr('data-pinned', '1')
    // Move container groups as well for immediate visual feedback
    svg
      .selectAll('g.container-node')
      .filter((d: Device) => d.id === id)
      .attr('transform', `translate(${lc.x},${lc.y})`)
  })
  svg.selectAll('line.link').each(function (this: SVGLineElement, d: any) {
    if (ids.includes(d.a_device_id)) {
      const lc = layoutCache[d.a_device_id]
      d3.select(this).attr('x1', lc.x).attr('y1', lc.y)
    }
    if (ids.includes(d.b_device_id)) {
      const lc = layoutCache[d.b_device_id]
      d3.select(this).attr('x2', lc.x).attr('y2', lc.y)
    }
  })
  svg.selectAll('line.parent-tether').each(function (this: SVGLineElement, d: any) {
    if (ids.includes(d.parent) || ids.includes(d.child)) {
      const p = layoutCache[d.parent]
      const c = layoutCache[d.child]
      if (p && c) {
        d3.select(this).attr('x1', p.x).attr('y1', p.y).attr('x2', c.x).attr('y2', c.y)
      }
    }
  })
}

export function redrawSelection(svgRef: { value: SVGSVGElement | null }, selection: any) {
  if (!svgRef.value) return
  const svg = d3.select(svgRef.value)
  svg
    .selectAll('g.device-node')
    .classed('selected', (d: Device) => !!selection.isSelected(d.id, 'device'))
    .attr('data-selected', (d: Device) => (selection.isSelected(d.id, 'device') ? '1' : '0'))
    .attr('data-multi', selection.items.length > 1 ? '1' : '0')
  svg
    .selectAll('line.link')
    .attr('data-selected', (d: any) => (selection.isSelected(d.id, 'link') ? '1' : '0'))
}
