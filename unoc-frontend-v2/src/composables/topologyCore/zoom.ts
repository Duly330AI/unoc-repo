/* eslint-disable @typescript-eslint/no-explicit-any */
import * as d3 from 'd3'

export function applyZoom(svgRef: any, zoomRoot: any, onZoomStart?: () => void) {
  if (!svgRef?.value || !zoomRoot?.value) return
  const zr = d3.select(zoomRoot.value)
  d3.select(svgRef.value).call(
    (d3 as any)
      .zoom()
      .scaleExtent([0.1, 2.0])
      .on('start', () => {
        try {
          onZoomStart?.()
        } catch {
          /* optional */
        }
      })
      .on('zoom', (event: any) => {
        zr.attr('transform', event.transform)
      })
  )
}
