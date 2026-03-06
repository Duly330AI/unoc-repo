export interface BulkPlacementConfig {
    count: number
    width: number
    height: number
    padding?: number
    jitter?: number
}

export interface PositionedId { id: string; x: number; y: number }

// Spiral/grid hybrid for deterministic spread with mild jitter.
export function generateBulkPositions(cfg: BulkPlacementConfig): PositionedId[] {
    const { count, width, height } = cfg
    const pad = cfg.padding ?? 80
    const jitter = cfg.jitter ?? 20
    const usableW = Math.max(120, width - pad * 2)
    const usableH = Math.max(120, height - pad * 2)
    const perRow = Math.ceil(Math.sqrt(count))
    const cellW = usableW / perRow
    const cellH = usableH / perRow
    const res: PositionedId[] = []
    for (let i = 0; i < count; i++) {
        const row = Math.floor(i / perRow)
        const col = i % perRow
        let x = pad + cellW * (col + 0.5)
        let y = pad + cellH * (row + 0.5)
        const jx = (Math.sin(i * 12.9898) * 43758.5453) % 1
        const jy = (Math.sin(i * 78.233) * 96234.5453) % 1
        x += (jx - 0.5) * jitter
        y += (jy - 0.5) * jitter
        x = Math.min(width - pad, Math.max(pad, x))
        y = Math.min(height - pad, Math.max(pad, y))
        res.push({ id: `idx_${i}`, x: Math.round(x), y: Math.round(y) })
    }
    return res
}