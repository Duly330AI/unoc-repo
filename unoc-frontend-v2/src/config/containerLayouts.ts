// Lightweight FE copy of docs/container-layouts.json for rendering containers and slots
// Coordinates are relative to the container's top-left corner. Slots represent anchor centers.

export type ContainerLayout = {
  // New schema
  headerHeight: number
  contentPadding: { top: number; right: number; bottom: number; left: number }
  slotBox: { width: number; height: number }
  slots: { id: string; x: number; y: number }[]
  // Offset to translate slot centers so that the left/top slotBox edges align
  // with the content area inside the container (accounts for header/padding and
  // slotBox half sizes). Consumers should add this to slot centers when
  // converting to absolute SVG coordinates.
  slotOffset: { x: number; y: number }
  // Back-compat: computed overall size used by renderer/physics/hittesting
  size: { width: number; height: number }
}

type RawLayout = {
  headerHeight: number
  contentPadding: { top: number; right: number; bottom: number; left: number }
  slotBox: { width: number; height: number }
  slots: { id: string; x: number; y: number }[]
  slotInsetX?: number
  slotInsetY?: number
}

function computeBounds(raw: RawLayout): {
  width: number
  height: number
  minX: number
  minY: number
  halfW: number
  halfH: number
} {
  if (!raw.slots.length) {
    // Minimal size when no slots are defined
    const minW = raw.contentPadding.left + 320 + raw.contentPadding.right
    const minH = raw.headerHeight + raw.contentPadding.top + 160 + raw.contentPadding.bottom
    return { width: minW, height: minH, minX: 0, minY: 0, halfW: 0, halfH: 0 }
  }
  const halfW = raw.slotBox.width / 2
  const halfH = raw.slotBox.height / 2
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const s of raw.slots) {
    minX = Math.min(minX, s.x - halfW)
    maxX = Math.max(maxX, s.x + halfW)
    minY = Math.min(minY, s.y - halfH)
    maxY = Math.max(maxY, s.y + halfH)
  }
  const contentW = Math.max(0, maxX - minX)
  const contentH = Math.max(0, maxY - minY)
  const width = raw.contentPadding.left + contentW + raw.contentPadding.right
  const height = raw.headerHeight + raw.contentPadding.top + contentH + raw.contentPadding.bottom
  return { width, height, minX, minY, halfW, halfH }
}

const baseLayoutsRaw: Record<string, RawLayout> = {
  POP: {
    headerHeight: 56,
    contentPadding: { top: 28, right: 36, bottom: 28, left: 36 },
    // Increase slot box further to cover widest child cockpits (Router ~400px @ scale 2)
    // Use 440x240 to give a small visual margin around the cockpit frame
    slotBox: { width: 440, height: 240 },
    // Nudge all slots slightly right to ensure extra left margin inside content area
    slotInsetX: 16,
    // 2x3 grid, placed entirely in content area below header
    // Keep centers stable to preserve visual alignment; container grows around them
    slots: [
      { id: 'top-left', x: 174, y: 170 },
      // Widen horizontal spacing so two routers (400px wide) do not overlap; push right column further right
      { id: 'top-right', x: 720, y: 170 },
      { id: 'mid-left', x: 174, y: 358 },
      { id: 'mid-right', x: 720, y: 358 },
      { id: 'bottom-left', x: 174, y: 546 },
      { id: 'bottom-right', x: 720, y: 546 }
    ]
  },
  CORE_SITE: {
    headerHeight: 56,
    contentPadding: { top: 28, right: 36, bottom: 28, left: 36 },
    // Mirror POP sizing
    slotBox: { width: 440, height: 240 },
    slotInsetX: 16,
    slots: [
      { id: 'top-left', x: 174, y: 170 },
      { id: 'top-right', x: 720, y: 170 },
      { id: 'mid-left', x: 174, y: 358 },
      { id: 'mid-right', x: 720, y: 358 },
      { id: 'bottom-left', x: 174, y: 546 },
      { id: 'bottom-right', x: 720, y: 546 }
    ]
  }
}

export const containerLayouts: Record<string, ContainerLayout> = Object.fromEntries(
  Object.entries(baseLayoutsRaw).map(([k, raw]) => {
    const b = computeBounds(raw)
    // Align the left-most/top-most slotBox edges with the container's content area
    const insetX = raw.slotInsetX ?? 0
    const insetY = raw.slotInsetY ?? 0
    const slotOffsetX = raw.contentPadding.left - b.minX + insetX
    const slotOffsetY = raw.headerHeight + raw.contentPadding.top - b.minY + insetY
    const layout: ContainerLayout = {
      headerHeight: raw.headerHeight,
      contentPadding: raw.contentPadding,
      slotBox: raw.slotBox,
      slots: raw.slots,
      slotOffset: { x: slotOffsetX, y: slotOffsetY },
      size: { width: b.width, height: b.height }
    }
    return [k, layout]
  })
) as Record<string, ContainerLayout>

export function getContainerLayout(type: string): ContainerLayout | undefined {
  return containerLayouts[type]
}
