import { reactive } from 'vue'
import type { DragState, LayoutEntry } from '../types/topology.js'

export function createDragState(): DragState {
    return reactive<DragState>({
        id: null,
        offsetX: 0,
        offsetY: 0,
        origX: 0,
        origY: 0,
        active: false,
        moved: false,
        throttleAt: 0,
        multi: false,
        others: [],
        lastPersistAt: 0
    })
}

export function applyDrag(
    ev: MouseEvent,
    drag: DragState,
    layout: Record<string, LayoutEntry>,
    fastRefresh: (ids: string[]) => void
) {
    if (!drag.active || !drag.id) return
    const lc = layout[drag.id]
    const newX = ev.clientX - drag.offsetX
    const newY = ev.clientY - drag.offsetY
    const dx = newX - lc.x
    const dy = newY - lc.y
    lc.x = newX
    lc.y = newY
    lc.pinned = true
    if (drag.multi) {
        drag.others.forEach((id: string) => {
            const o = layout[id]; if (!o) return; o.x += dx; o.y += dy; o.pinned = true
        })
    }
    drag.moved = true
    fastRefresh([drag.id, ...drag.others])
}

export function endDrag(
    drag: DragState,
    queuePersist: (ids: string[]) => void
) {
    if (!drag.id) { drag.active = false; return }
    if (drag.moved) queuePersist([drag.id, ...drag.others])
    drag.id = null
    drag.active = false
}
