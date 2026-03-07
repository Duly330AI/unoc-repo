/* eslint-disable @typescript-eslint/no-explicit-any */
import * as d3 from 'd3'
import { containerBoundsForce } from './containerBoundsForce.js'

type LayoutEntry = { x: number; y: number; type: string; pinned?: boolean }

type SimNode = {
  id: string
  type: string
  pinned: boolean
  x: number
  y: number
  fx?: number | null
  fy?: number | null
  vx?: number
  vy?: number
}

type SimLink = { source: string | SimNode; target: string | SimNode }

const LAYOUT_CONST = {
  COLLIDE_RADIUS: 150, // 200 → 150 (weniger aggressiv)
  CHARGE_STRENGTH: -300, // -800 → -300 (VIEL sanfter!)
  X_SPREAD_STRENGTH: 0.15, // 0.25 → 0.15 (sanfter horizontal verteilen)
  Y_STRENGTH: 0.6, // 0.9 → 0.6 (sanfter Y-Positionierung)
  LINK_BASE_DISTANCE: 200, // 300 → 200 (realistischer)
  LINK_DISTANCE_PER_DEPTH: 150, // 200 → 150 (moderater Abstand)
  LINK_STRENGTH: 0.4, // 0.15 → 0.4 (stärkere Links für Stabilität!)
  MARGIN: 120, // 150 → 120
  LEVEL_GAP_MIN: 350 // 450 → 350
}

function deviceDepth(type: string): number {
  switch (type) {
    case 'BACKBONE_GATEWAY':
    case 'BACKBONE':
      return 0
    case 'CORE_ROUTER':
    case 'EDGE_ROUTER':
      return 1
    case 'OLT':
      return 2
    case 'ODF': // Zwischen OLT und ONT!
    case 'SPLITTER':
    case 'AON_SWITCH':
      return 3
    case 'ONT':
    case 'BUSINESS_ONT':
    case 'AON_CPE':
      return 4 // Eine Ebene tiefer!
    default:
      return 2
  }
}

export function createSimulationController(args: {
  svgRef: any
  devices: { devices: Array<{ id: string; type: string }> }
  linksStore: { links: Array<{ a_device_id: string; b_device_id: string }> }
  layoutCache: Record<string, LayoutEntry>
  fastRefreshNodes: (ids: string[]) => void
  queuePositions: (ids: string[]) => void
}) {
  const { svgRef, devices, linksStore, layoutCache, fastRefreshNodes, queuePositions } = args
  let simulation: any | null = null

  function buildSimulation() {
    const devs = devices.devices
    const nodeById = new Map<string, SimNode>()
    const nodes: SimNode[] = devs.map((d) => {
      const lc = layoutCache[d.id]
      const n: SimNode = {
        id: d.id,
        type: d.type,
        pinned: !!lc?.pinned,
        x: lc?.x ?? 0,
        y: lc?.y ?? 0,
        fx: lc?.pinned ? lc.x : null,
        fy: lc?.pinned ? lc.y : null
      }
      nodeById.set(d.id, n)
      return n
    })
    const links: SimLink[] = (linksStore.links || []).map((l: any) => ({
      source: l.a_device_id,
      target: l.b_device_id
    }))
    const svg = svgRef.value as SVGSVGElement | null
    const rect = svg?.getBoundingClientRect?.()
    const width = rect?.width || 1200
    const height = rect?.height || 800
    const depthLevels = [0, 1, 2, 3]
    const levelCount = depthLevels.length
    const levelGap = Math.max(height / (levelCount + 1), LAYOUT_CONST.LEVEL_GAP_MIN)
    const yFor = (n: SimNode) => (deviceDepth(n.type) + 1) * levelGap
    const byDepth = new Map<number, SimNode[]>()
    nodes.forEach((n) => {
      const d = deviceDepth(n.type)
      if (!byDepth.has(d)) byDepth.set(d, [])
      byDepth.get(d)!.push(n)
    })
    const targetXById = new Map<string, number>()
    const innerLeft = LAYOUT_CONST.MARGIN
    const innerRight = Math.max(LAYOUT_CONST.MARGIN + 1, width - LAYOUT_CONST.MARGIN)
    byDepth.forEach((arr) => {
      arr.sort((a, b) => a.id.localeCompare(b.id))
      if (arr.length === 1) {
        targetXById.set(arr[0].id, width / 2)
      } else {
        // Calculate required width for all nodes with proper spacing
        const minSpacing = 250 // Minimum 250px between nodes
        const requiredWidth = arr.length * minSpacing
        const actualLeft = Math.max(innerLeft, (width - requiredWidth) / 2)
        const actualRight = Math.min(innerRight, actualLeft + requiredWidth)

        const scale = (d3 as any)
          .scalePoint()
          .domain(arr.map((n) => n.id))
          .range([actualLeft, actualRight])
          .padding(0.5)
        arr.forEach((n) => targetXById.set(n.id, scale(n.id)))
      }
    })

    simulation = (d3 as any)
      .forceSimulation(nodes as any)
      .alphaDecay(0.02) // 0.005 → 0.02 (schneller stoppen)
      .velocityDecay(0.4) // 0.2 → 0.4 (VIEL mehr Dämpfung! Sanfter!)
      .force(
        'link',
        (d3 as any)
          .forceLink(links as any)
          .id((d: any) => d.id)
          .distance((l: any) => {
            const s = typeof l.source === 'string' ? nodeById.get(l.source)! : (l.source as SimNode)
            const t =
              typeof l.target === 'string'
                ? nodeById.get(l.target as string)!
                : (l.target as SimNode)
            const dd = Math.abs(deviceDepth(s.type) - deviceDepth(t.type))
            return LAYOUT_CONST.LINK_BASE_DISTANCE + dd * LAYOUT_CONST.LINK_DISTANCE_PER_DEPTH
          })
          .strength(LAYOUT_CONST.LINK_STRENGTH)
      )
      // Keep children inside their containers and provide a weak drift toward slot anchors
      .force(
        'containerBounds',
        containerBoundsForce({
          getLayoutCache: () => layoutCache as any,
          getDevices: () => devices.devices as any,
          padding: 10,
          slotAttraction: 0.015,
          velocityDamping: 0.8
        })
      )
      .force('charge', (d3 as any).forceManyBody().strength(LAYOUT_CONST.CHARGE_STRENGTH))
      .force(
        'collide',
        (d3 as any).forceCollide().radius(LAYOUT_CONST.COLLIDE_RADIUS).strength(0.95)
      )
      .force(
        'xSpread',
        (d3 as any)
          .forceX((n: any) => targetXById.get(n.id) ?? width / 2)
          .strength(LAYOUT_CONST.X_SPREAD_STRENGTH)
      )
      .force(
        'yDepth',
        (d3 as any)
          .forceY()
          .y((n: any) => yFor(n))
          .strength(LAYOUT_CONST.Y_STRENGTH)
      )
      .on('tick', () => {
        nodes.forEach((n) => {
          if (n.pinned) {
            n.x = (n.fx as number) ?? n.x
            n.y = (n.fy as number) ?? n.y
            n.vx = 0
            n.vy = 0
          }
          n.x = Math.max(LAYOUT_CONST.MARGIN, Math.min(width - LAYOUT_CONST.MARGIN, n.x))
          n.y = Math.max(40, Math.min(height - 40, n.y))
          const lc = layoutCache[n.id]
          if (lc) {
            lc.x = n.x
            lc.y = n.y
          }
        })
        fastRefreshNodes(nodes.map((n) => n.id))
      })
      .on('end', () => {
        queuePositions(nodes.filter((n) => !n.pinned).map((n) => n.id))
      })
  }

  function startForceLayout() {
    console.log('[AUTO LAYOUT] startForceLayout called!')

    // NICHT die Simulation neu bauen! Das entfernt alle Event Handler!
    // Stattdessen: bestehende Simulation nutzen oder initial bauen
    if (!simulation) {
      buildSimulation()
    }

    if (!simulation) {
      console.error('[AUTO LAYOUT] buildSimulation failed - no simulation created!')
      return
    }

    const nodes = simulation.nodes() as SimNode[]
    console.log(`[AUTO LAYOUT] Starting with ${nodes.length} nodes`)

    // WICHTIG: Auto Layout ent-pinnt ALLE Nodes!
    // Ignore das pinned Flag - Auto Layout soll alle Nodes neu anordnen
    nodes.forEach((n) => {
      const lc = layoutCache[n.id]
      // Entferne pinned Flag aus layoutCache
      if (lc) {
        lc.pinned = false
      }
      // Entferne fixed position constraints
      n.pinned = false
      n.fx = null
      n.fy = null
      console.log(`[AUTO LAYOUT] Unpinned node ${n.id}, current pos: (${n.x}, ${n.y})`)
    })

    console.log('[AUTO LAYOUT] Starting simulation with alpha=1')
    simulation.alpha(1).restart()
    console.log('[AUTO LAYOUT] Current alpha:', simulation.alpha())

    let ticks = 0
    const maxTicks = 300 // 80 → 300 (viel mehr Ticks für stärkere Kräfte)

    const stopIfDone = () => {
      ticks++

      // WICHTIG: Manuell simulation tick aufrufen und UI updaten!
      simulation?.tick()

      // Update UI bei jedem Frame für flüssige Animation
      nodes.forEach((n) => {
        const lc = layoutCache[n.id]
        if (lc) {
          lc.x = n.x
          lc.y = n.y
        }
      })
      fastRefreshNodes(nodes.map((n) => n.id))

      if (ticks >= maxTicks || (simulation && simulation.alpha() < 0.001)) {
        // 0.005 → 0.001 (noch niedrigerer Threshold - länger laufen!)
        console.log(`[AUTO LAYOUT] Stopped after ${ticks} ticks, alpha=${simulation?.alpha()}`)
        simulation?.stop()
        queuePositions(nodes.filter((n) => !n.pinned).map((n) => n.id))
      } else {
        requestAnimationFrame(stopIfDone)
      }
    }
    requestAnimationFrame(stopIfDone)
  }

  function forceLayout() {
    // USE PROFESSIONAL HIERARCHICAL LAYOUT instead of force simulation!
    console.log('[AUTO LAYOUT] Using professional hierarchical layout!')

    import('./hierarchicalLayout.js')
      .then(({ computeHierarchicalLayout }) => {
        const devs = devices.devices
        const links = linksStore.links || []
        const svg = svgRef.value as SVGSVGElement | null
        const rect = svg?.getBoundingClientRect?.()
        const width = rect?.width || 1920
        const height = rect?.height || 1080

        // Compute deterministic positions
        const newPositions = computeHierarchicalLayout(devs, links, width, height)

        console.log(`[AUTO LAYOUT] Computed ${newPositions.size} positions`)

        // Store start positions for animation
        const startPositions = new Map<string, { x: number; y: number }>()
        devs.forEach((d) => {
          const lc = layoutCache[d.id]
          if (lc) startPositions.set(d.id, { x: lc.x, y: lc.y })
        })

        // Animate to target positions (smooth 1s animation)
        const startTime = Date.now()
        const duration = 1000

        const animate = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic

          devs.forEach((d) => {
            const start = startPositions.get(d.id)
            const target = newPositions.get(d.id)
            const lc = layoutCache[d.id]

            if (!start || !target || !lc) return

            lc.x = start.x + (target.x - start.x) * eased
            lc.y = start.y + (target.y - start.y) * eased
            lc.pinned = false
          })

          fastRefreshNodes(devs.map((d) => d.id))

          if (progress < 1) {
            requestAnimationFrame(animate)
          } else {
            queuePositions(devs.map((d) => d.id))
          }
        }

        requestAnimationFrame(animate)
      })
      .catch((err) => {
        console.error('[AUTO LAYOUT] Hierarchical layout failed:', err)
        // Fallback to force layout
        startForceLayout()
      })
  }

  return { forceLayout }
}
