import { defineStore } from 'pinia'

export interface ContextMenuItem {
    id: string
    label: string
    disabled?: boolean
    reason?: string
    action: () => void | Promise<void>
}

interface Position { x: number; y: number }

export const useContextMenuStore = defineStore('contextMenu', {
    state: () => ({
        open: false as boolean,
        pos: { x: 0, y: 0 } as Position,
        items: [] as ContextMenuItem[],
        source: { kind: null as null | 'device' | 'canvas', id: null as string | null },
        highlighted: -1 as number
    }),
    actions: {
        show(x: number, y: number, items: ContextMenuItem[], source: { kind: 'device' | 'canvas'; id: string | null }) {
            // Clamp to viewport (basic; UI will also auto-size)
            const vw = (typeof window !== 'undefined' && window.innerWidth) ? window.innerWidth : 1920
            const vh = (typeof window !== 'undefined' && window.innerHeight) ? window.innerHeight : 1080
            const menuW = 220
            const menuH = Math.min(320, 28 + items.length * 28)
            const clampedX = Math.max(0, Math.min(x, vw - menuW))
            const clampedY = Math.max(0, Math.min(y, vh - menuH))
            this.pos = { x: clampedX, y: clampedY }
            this.items = items
            this.source = source
            this.highlighted = items.findIndex(i => !i.disabled)
            this.open = true
        },
        hide() { this.open = false; this.highlighted = -1 },
        moveHighlight(delta: number) {
            if (!this.open || !this.items.length) return
            const n = this.items.length
            let idx = this.highlighted
            for (let step = 0; step < n; step++) {
                idx = (idx + delta + n) % n
                if (!this.items[idx]?.disabled) { this.highlighted = idx; break }
            }
        },
        activateHighlighted() {
            if (!this.open) return
            const it = this.items[this.highlighted]
            if (!it || it.disabled) return
            Promise.resolve(it.action()).finally(() => this.hide())
        },
        repositionWithinViewport(estimatedWidth = 220, estimatedHeight = 320) {
            const vw = (typeof window !== 'undefined' && window.innerWidth) ? window.innerWidth : 1920
            const vh = (typeof window !== 'undefined' && window.innerHeight) ? window.innerHeight : 1080
            const clampedX = Math.max(0, Math.min(this.pos.x, vw - estimatedWidth))
            const clampedY = Math.max(0, Math.min(this.pos.y, vh - estimatedHeight))
            this.pos = { x: clampedX, y: clampedY }
        }
    }
})
