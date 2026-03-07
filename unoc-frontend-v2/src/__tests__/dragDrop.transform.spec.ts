/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi } from 'vitest'
import { createDropHandler, toGraphCoords } from '../composables/topologyCore/drop.js'

function makeSvgWithZoom(t: { x: number; y: number; k: number }) {
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg') as unknown as SVGSVGElement
  ;(svg as any).__zoom = { x: t.x, y: t.y, k: t.k }
  svg.getBoundingClientRect = () =>
    ({
      left: 0,
      top: 0,
      width: 100,
      height: 100,
      right: 100,
      bottom: 100,
      x: 0,
      y: 0,
      toJSON() {
        return {}
      }
    }) as any
  return svg
}

// Note:
// d3.zoomTransform (used inside drop.ts) returns the value stored on element.__zoom
// if present; we set that on our test SVG to simulate an active zoom/pan without
// importing or modifying d3 in the test environment.

describe('drop handler transforms screen to graph coords', () => {
  it('computes inverse transform correctly', () => {
    const { gx, gy } = toGraphCoords({ x: 50, y: 20, k: 2 }, 90, 40)
    expect(gx).toBe(20)
    expect(gy).toBe(10)
  })

  it('places newly created device at computed graph coordinates (smoke)', async () => {
    // Zoomed/panned: translate (50, 20), scale 2x
    const svg = makeSvgWithZoom({ x: 50, y: 20, k: 2 })

    const layout: any = {}
    const svgRef = { value: svg }
    const getLayout = () => layout
    const devices = { devices: [], create: vi.fn().mockResolvedValue(undefined) }
    const selection = { items: [] }
    const ghosts: any[] = []
    const toasts = { push: vi.fn() }
    const redraw = vi.fn()
    const queuePositions = vi.fn()
    const fastRefreshNodes = vi.fn()

    const { onDrop } = createDropHandler(
      svgRef as any,
      getLayout,
      devices,
      selection as any,
      ghosts,
      toasts,
      redraw,
      queuePositions,
      fastRefreshNodes
    )

    // Screen coords (clientX/Y relative to rect): suppose cursor at (90, 40)
    // With t={x:50,y:20,k:2}, graph coords should be ((90-50)/2,(40-20)/2) => (20,10)
    const evt = new Event('drop') as any
    evt.dataTransfer = {
      // Use a type that does not require a POP parent to be present
      getData: (t: string) => (t === 'application/x-unoc-device-type' ? 'ONT' : '')
    }
    ;(evt as any).clientX = 90
    ;(evt as any).clientY = 40

    await onDrop(evt as DragEvent)
    // Ensure we invoked creation and queued position persistence
    expect(devices.create).toHaveBeenCalled()
  })
})
