/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi } from 'vitest'
import { fastRefreshNodes as fastRefreshNodesHelper } from '../topologyCore/renderHelpers.js'
import { createDropHandler } from '../topologyCore/drop.js'

function makeSvg() {
  const ns = 'http://www.w3.org/2000/svg'
  const svg = document.createElementNS(ns, 'svg') as unknown as SVGSVGElement
  const g = document.createElementNS(ns, 'g')
  g.setAttribute('class', 'device-node')
  ;(g as any).__data__ = { id: 'dev1' }
  const linksLayer = document.createElementNS(ns, 'g')
  linksLayer.setAttribute('class', 'links-layer')
  const nodesLayer = document.createElementNS(ns, 'g')
  nodesLayer.setAttribute('class', 'nodes-layer')
  nodesLayer.appendChild(g)
  svg.appendChild(linksLayer)
  svg.appendChild(nodesLayer)
  return svg
}

describe('fastRefreshNodes updates g.device-node transform', () => {
  it('moves cockpit wrapper when position changes', () => {
    const svg = makeSvg()
    const layout: any = { dev1: { x: 120, y: 80 } }
    const svgRef = { value: svg }
    fastRefreshNodesHelper(svgRef as any, layout, ['dev1'])
    const node = svg.querySelector('g.device-node')!
    expect(node.getAttribute('transform')).toBe('translate(120,80)')
  })
})

describe('createDropHandler places new device at drop coords', () => {
  it('sets layout cache and queues persist', async () => {
    const ns = 'http://www.w3.org/2000/svg'
    const svg = document.createElementNS(ns, 'svg') as unknown as SVGSVGElement
    // minimal layers required for handler
    svg.appendChild(document.createElementNS(ns, 'g')).setAttribute('class', 'links-layer')
    svg.getBoundingClientRect = () =>
      ({
        left: 10,
        top: 20,
        width: 100,
        height: 100,
        right: 110,
        bottom: 120,
        x: 10,
        y: 20,
        toJSON() {
          return {}
        }
      }) as any

    const layout: any = {}
    const svgRef = { value: svg }
    const getLayout = () => layout
    const devices = {
      devices: [],
      create: vi.fn().mockResolvedValue(undefined)
    }
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

    const dataTransfer = {
      getData: (t: string) => (t === 'application/x-unoc-device-type' ? 'CORE_ROUTER' : '')
    } as any

    const evt = new Event('drop') as any
    ;(evt as any).dataTransfer = dataTransfer
    ;(evt as any).clientX = 60
    ;(evt as any).clientY = 70

    onDrop(evt as DragEvent)
    // wait for devices.create().then(...) to resolve
    await new Promise((r) => setTimeout(r, 0))

    // After create resolves, layout contains new device at (50,50) due to rect offset
    const id = Object.keys(layout)[0]
    expect(layout[id].x).toBe(50)
    expect(layout[id].y).toBe(50)
    expect(layout[id].pinned).toBe(true)
    expect(queuePositions).toHaveBeenCalledWith([id])
    expect(fastRefreshNodes).toHaveBeenCalledWith([id])
    expect(redraw).toHaveBeenCalled()
  })
})
