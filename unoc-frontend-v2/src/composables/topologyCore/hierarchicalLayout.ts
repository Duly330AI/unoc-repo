/**
 * Professional Hierarchical Network Layout Algorithm
 */

import { logger } from '../../utils/logger.js'

type Device = {
  id: string
  type: string
}

type Link = {
  a_device_id: string
  b_device_id: string
}

type Position = {
  x: number
  y: number
}

const LAYOUT_CONFIG = {
  LEVEL_HEIGHT: 500,
  CORE_SPACING: 800,
  MIN_NODE_SPACING: 180,
  BASE_RADIUS: 400,
  MARGIN: 200
}

function getHierarchyLevel(type: string): number {
  const levels: Record<string, number> = {
    BACKBONE_GATEWAY: 0,
    BACKBONE: 0,
    CORE_ROUTER: 1,
    EDGE_ROUTER: 1,
    OLT: 2,
    ODF: 3,
    SPLITTER: 3,
    AON_SWITCH: 3,
    ONT: 4,
    BUSINESS_ONT: 4,
    AON_CPE: 4
  }
  return levels[type] ?? 2
}

function isAggregator(type: string): boolean {
  return ['ODF', 'SPLITTER', 'AON_SWITCH', 'OLT'].includes(type)
}

function isEndpoint(type: string): boolean {
  return ['ONT', 'BUSINESS_ONT', 'AON_CPE'].includes(type)
}

function buildHierarchy(devices: Device[], links: Link[]): Map<string, Set<string>> {
  const children = new Map<string, Set<string>>()
  devices.forEach((d) => children.set(d.id, new Set()))
  links.forEach((link) => {
    const aDev = devices.find((d) => d.id === link.a_device_id)
    const bDev = devices.find((d) => d.id === link.b_device_id)
    if (!aDev || !bDev) return
    const aLevel = getHierarchyLevel(aDev.type)
    const bLevel = getHierarchyLevel(bDev.type)
    if (aLevel < bLevel) children.get(link.a_device_id)!.add(link.b_device_id)
    else if (bLevel < aLevel) children.get(link.b_device_id)!.add(link.a_device_id)
  })
  return children
}

function calculateRadius(childCount: number): number {
  const minCircumference = childCount * LAYOUT_CONFIG.MIN_NODE_SPACING
  const calculatedRadius = minCircumference / (2 * Math.PI)
  return Math.max(LAYOUT_CONFIG.BASE_RADIUS, calculatedRadius)
}

function positionInCircle(center: Position, radius: number, count: number): Position[] {
  const positions: Position[] = []
  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count
    positions.push({
      x: center.x + radius * Math.cos(angle),
      y: center.y + radius * Math.sin(angle)
    })
  }
  return positions
}

export function computeHierarchicalLayout(
  devices: Device[],
  links: Link[],
  canvasWidth: number,
  _canvasHeight: number
): Map<string, Position> {
  const positions = new Map<string, Position>()
  const children = buildHierarchy(devices, links)

  // Calculate minimum required canvas width for aggregators
  const aggregators = devices.filter((d) => getHierarchyLevel(d.type) === 3 && isAggregator(d.type))
  if (aggregators.length > 0) {
    const radii = aggregators.map((dev) => {
      const childCount = children.get(dev.id)?.size || 0
      return childCount > 0 ? calculateRadius(childCount) : LAYOUT_CONFIG.BASE_RADIUS
    })
    const totalDiameter = radii.reduce((sum, r) => sum + r * 2, 0)
    const gaps = (aggregators.length - 1) * 700
    const minCanvasWidth = totalDiameter + gaps + 2 * LAYOUT_CONFIG.MARGIN

    logger.debug(
      `[LAYOUT] Minimum canvas width needed: ${minCanvasWidth.toFixed(0)}px, actual: ${canvasWidth}px`
    )

    // Use larger canvas width if needed
    canvasWidth = Math.max(canvasWidth, minCanvasWidth)
    logger.debug(`[LAYOUT] Using canvas width: ${canvasWidth}px`)
  }

  const levels = new Map<number, Device[]>()
  devices.forEach((d) => {
    const level = getHierarchyLevel(d.type)
    if (!levels.has(level)) levels.set(level, [])
    levels.get(level)!.push(d)
  })

  const sortedLevels = Array.from(levels.keys()).sort((a, b) => a - b)

  sortedLevels.forEach((levelNum) => {
    const devicesAtLevel = levels.get(levelNum)!
    const y = LAYOUT_CONFIG.MARGIN + levelNum * LAYOUT_CONFIG.LEVEL_HEIGHT

    if (levelNum <= 1) {
      const spacing = LAYOUT_CONFIG.CORE_SPACING
      const totalWidth = spacing * (devicesAtLevel.length - 1)
      const startX = (canvasWidth - totalWidth) / 2
      devicesAtLevel.forEach((dev, i) => {
        positions.set(dev.id, { x: startX + i * spacing, y: y })
      })
    } else if (levelNum === 3 && devicesAtLevel.some((d) => isAggregator(d.type))) {
      const aggregatorsWithRadii = devicesAtLevel.map((dev) => {
        const childCount = children.get(dev.id)?.size || 0
        const radius = childCount > 0 ? calculateRadius(childCount) : LAYOUT_CONFIG.BASE_RADIUS
        return { dev, radius, diameter: radius * 2 }
      })

      const maxRowWidth = canvasWidth - 2 * LAYOUT_CONFIG.MARGIN
      const avgRadius =
        aggregatorsWithRadii.reduce((sum, agg) => sum + agg.radius, 0) / aggregatorsWithRadii.length
      const gap = Math.max(700, avgRadius * 0.5)

      logger.debug(
        `[LAYOUT DEBUG] canvasWidth=${canvasWidth}, maxRowWidth=${maxRowWidth}, gap=${gap.toFixed(0)}px`
      )

      // Calculate total width needed if all in one row
      const totalWidthNeeded =
        aggregatorsWithRadii.reduce((sum, agg) => sum + agg.diameter, 0) +
        (aggregatorsWithRadii.length - 1) * gap

      logger.debug(
        `[LAYOUT DEBUG] totalWidthNeeded=${totalWidthNeeded.toFixed(0)}px, available=${maxRowWidth.toFixed(0)}px`
      )

      // If nodes are too big for canvas, SCALE THEM DOWN!
      let scaleFactor = 1.0
      if (totalWidthNeeded > maxRowWidth) {
        scaleFactor = maxRowWidth / totalWidthNeeded
        logger.debug(`[LAYOUT DEBUG] Nodes too big! Scaling down by ${scaleFactor.toFixed(2)}`)

        // Scale all radii and diameters
        aggregatorsWithRadii.forEach((agg) => {
          agg.radius *= scaleFactor
          agg.diameter = agg.radius * 2
        })
      }

      const scaledGap = gap * scaleFactor

      const rows: (typeof aggregatorsWithRadii)[] = []
      let currentRow: typeof aggregatorsWithRadii = []
      let currentRowWidth = 0

      aggregatorsWithRadii.forEach((agg) => {
        const neededWidth = agg.diameter + (currentRow.length > 0 ? scaledGap : 0)
        logger.debug(
          `[LAYOUT DEBUG] ${agg.dev.id}: diameter=${agg.diameter.toFixed(0)}, neededWidth=${neededWidth.toFixed(0)}, currentRowWidth=${currentRowWidth.toFixed(0)}, fits=${currentRowWidth + neededWidth <= maxRowWidth}`
        )

        if (currentRowWidth + neededWidth > maxRowWidth && currentRow.length > 0) {
          logger.debug(
            `[LAYOUT DEBUG] Starting new row! Current row has ${currentRow.length} items`
          )
          rows.push(currentRow)
          currentRow = [agg]
          currentRowWidth = agg.diameter
        } else {
          currentRow.push(agg)
          currentRowWidth += neededWidth
        }
      })

      if (currentRow.length > 0) rows.push(currentRow)

      logger.debug(
        `[LAYOUT] Level ${levelNum}: ${aggregatorsWithRadii.length} aggregators → ${rows.length} rows, scaledGap=${scaledGap.toFixed(0)}px, scaleFactor=${scaleFactor.toFixed(2)}`
      )

      rows.forEach((row, rowIndex) => {
        const rowWidth =
          row.reduce((sum, agg) => sum + agg.diameter, 0) + (row.length - 1) * scaledGap
        let currentX = (canvasWidth - rowWidth) / 2
        const rowY = y + rowIndex * 1400

        row.forEach(({ dev, radius }) => {
          positions.set(dev.id, { x: currentX + radius, y: rowY })
          logger.debug(
            `[LAYOUT] ${dev.id}: row ${rowIndex} (${row.length} items), x=${(currentX + radius).toFixed(0)}, y=${rowY}, radius=${radius.toFixed(0)}, diameter=${(radius * 2).toFixed(0)}`
          )
          currentX += radius * 2 + scaledGap
        })
      })
    } else {
      devicesAtLevel.forEach((dev) => {
        const parent = devices.find((p) => children.get(p.id)?.has(dev.id))
        if (!parent) {
          positions.set(dev.id, { x: canvasWidth / 2, y })
          return
        }
        const parentPos = positions.get(parent.id)
        if (!parentPos) return
        const siblings = Array.from(children.get(parent.id) || [])
        const siblingIndex = siblings.indexOf(dev.id)

        if (isAggregator(parent.type) && isEndpoint(dev.type)) {
          const radius = calculateRadius(siblings.length)
          logger.debug(
            `[LAYOUT] ${parent.id} has ${siblings.length} children → radius ${radius.toFixed(0)}px`
          )
          const circle = positionInCircle(parentPos, radius, siblings.length)
          positions.set(dev.id, circle[siblingIndex])
        } else {
          const offset = (siblingIndex - siblings.length / 2) * 300
          positions.set(dev.id, { x: parentPos.x + offset, y: y })
        }
      })
    }
  })

  return positions
}
